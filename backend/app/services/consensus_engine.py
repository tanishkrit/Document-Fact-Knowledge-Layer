import uuid
from typing import List, Dict, Any, Optional
from app.models.schemas import Fact, Document, RelationshipType
from app.services.relationship_engine import RelationshipEngine
from app.services.matcher import FactMatcher

class ConsensusEngine:
    """
    Synthesizes multi-document consensus across 2 to 5 files for singular points.
    Aligns claims sharing the same subject and predicate across documents and determines
    whether the group exhibits unanimous corroboration, contradiction, or context drift.
    """

    @staticmethod
    def _normalize_predicate_key(pred: str) -> str:
        p = pred.lower().strip()
        synonym_map = {
            'sales': 'revenue',
            'turnover': 'revenue',
            'top-line': 'revenue',
            'top line': 'revenue',
            'revenue from operations': 'revenue',
            'revenue from contract with customers': 'revenue',
            'revenue from services': 'revenue',
            'service ebitda': 'ebitda',
            'adjusted ebitda': 'ebitda',
            'operating profit': 'ebitda',
            'net income': 'net profit / loss',
            'net profit': 'net profit / loss',
            'restated loss': 'net profit / loss',
            'pat': 'net profit / loss',
            'profit after tax': 'net profit / loss',
            'headcount': 'workforce',
            'employees': 'workforce',
            'workers': 'workforce',
            'staff': 'workforce',
            'pin codes': 'pincode reach',
            'pincodes': 'pincode reach',
            'pin codes covered': 'pincode reach',
            'pin-code reach': 'pincode reach',
            'tractors': 'fleet size',
            'vehicles': 'fleet size',
            'delivery centers': 'gateways',
            'automated sort centers': 'gateways',
            'facilities': 'gateways',
            'registered office': 'headquarters',
            'hq': 'headquarters',
            'office location': 'headquarters',
            'inception': 'founded',
            'incorporation': 'founded',
            'founding year': 'founded'
        }
        return synonym_map.get(p, p)

    @classmethod
    def compute_consensus_matrix(cls, facts: List[Fact], documents: List[Document]) -> Dict[str, Any]:
        doc_map = {d.id: d for d in documents}
        selected_doc_ids = [d.id for d in documents]

        # Group facts by canonical subject and predicate
        groups: Dict[str, List[Fact]] = {}
        for f in facts:
            if f.evidence.document_id not in doc_map:
                continue
            norm_subj = f.subject.strip().title()
            norm_pred = cls._normalize_predicate_key(f.predicate)
            
            # Group key
            key = f"{norm_subj}::{norm_pred}"
            if key not in groups:
                groups[key] = []
            groups[key].append(f)

        consensus_points: List[Dict[str, Any]] = []

        for key, group_facts in groups.items():
            subj, pred = key.split("::", 1)
            
            # Count distinct documents with facts for this point
            facts_by_doc: Dict[str, List[Fact]] = {}
            for f in group_facts:
                d_id = f.evidence.document_id
                if d_id not in facts_by_doc:
                    facts_by_doc[d_id] = []
                facts_by_doc[d_id].append(f)

            # Must appear in at least 2 distinct documents to form a consensus comparison
            if len(facts_by_doc) < 2:
                continue

            # Pick the most prominent/relevant fact for each document
            rep_claims_by_doc: Dict[str, Fact] = {}
            for d_id, d_facts in facts_by_doc.items():
                sorted_facts = sorted(
                    d_facts,
                    key=lambda x: (
                        1 if x.value.amount is not None else 0,
                        len(x.evidence.text or ""),
                        x.confidence
                    ),
                    reverse=True
                )
                rep_claims_by_doc[d_id] = sorted_facts[0]

            # Compare pairwise across all participating documents
            participating_doc_ids = list(rep_claims_by_doc.keys())
            pairwise_results = []

            for i in range(len(participating_doc_ids)):
                for j in range(i + 1, len(participating_doc_ids)):
                    f_a = rep_claims_by_doc[participating_doc_ids[i]]
                    f_b = rep_claims_by_doc[participating_doc_ids[j]]

                    vals_match, val_note, val_diff = RelationshipEngine._compare_values(f_a.value, f_b.value)
                    has_ctx_diff, ctx_note, ctx_diff = RelationshipEngine._analyze_context_difference(f_a.context, f_b.context)

                    if vals_match:
                        pair_status = "CORROBORATES"
                    elif has_ctx_diff:
                        pair_status = "CONTEXTUALIZES"
                    else:
                        pair_status = "CONTRADICTS"

                    pairwise_results.append({
                        "doc_a": f_a.evidence.document_id,
                        "doc_b": f_b.evidence.document_id,
                        "status": pair_status,
                        "val_note": val_note,
                        "ctx_note": ctx_note
                    })

            # Determine overall multi-way consensus verdict
            has_contradiction = any(p["status"] == "CONTRADICTS" for p in pairwise_results)
            has_contextualize = any(p["status"] == "CONTEXTUALIZES" for p in pairwise_results)
            all_corroborate = all(p["status"] == "CORROBORATES" for p in pairwise_results)

            if all_corroborate:
                overall_verdict = "CORROBORATES"
                verdict_label = "Unanimous Corroboration"
                summary = f"All {len(participating_doc_ids)} reporting documents state compatible and normalized claims for '{subj}' {pred}."
            elif has_contradiction:
                overall_verdict = "CONTRADICTS"
                verdict_label = "Conflict Across Filings"
                summary = f"Conflict detected among the {len(participating_doc_ids)} documents for '{subj}' {pred}. Values differ without reconciling context."
            elif has_contextualize:
                overall_verdict = "CONTEXTUALIZES"
                verdict_label = "Temporal / Scope Context Drift"
                summary = f"Values differ across the {len(participating_doc_ids)} documents for '{subj}' {pred}, but differences in reporting time periods or scopes explain the drift."
            else:
                overall_verdict = "UNCERTAIN"
                verdict_label = "Uncertain Relationship"
                summary = f"Information reported across {len(participating_doc_ids)} documents lacks explicit timeframe or scope context."

            # Calculate mean confidence
            avg_conf = round(sum(f.confidence for f in rep_claims_by_doc.values()) / len(rep_claims_by_doc), 2)

            # Build formatted claims map
            formatted_claims = []
            for d_id in selected_doc_ids:
                if d_id in rep_claims_by_doc:
                    fact_item = rep_claims_by_doc[d_id]
                    doc_obj = doc_map.get(d_id)
                    formatted_claims.append({
                        "document_id": d_id,
                        "document_name": doc_obj.filename if doc_obj else d_id,
                        "has_claim": True,
                        "fact_id": fact_item.id,
                        "page": fact_item.evidence.page,
                        "raw_value": fact_item.value.raw,
                        "amount": fact_item.value.amount,
                        "unit": fact_item.value.unit or fact_item.value.currency,
                        "time": fact_item.context.time,
                        "scope": fact_item.context.scope,
                        "geography": fact_item.context.geography,
                        "evidence_quote": fact_item.evidence.text
                    })
                else:
                    doc_obj = doc_map.get(d_id)
                    formatted_claims.append({
                        "document_id": d_id,
                        "document_name": doc_obj.filename if doc_obj else d_id,
                        "has_claim": False,
                        "fact_id": None,
                        "page": None,
                        "raw_value": "—",
                        "amount": None,
                        "unit": None,
                        "time": None,
                        "scope": None,
                        "geography": None,
                        "evidence_quote": None
                    })

            consensus_points.append({
                "id": f"cp_{uuid.uuid4().hex[:8]}",
                "subject": subj,
                "predicate": pred,
                "verdict": overall_verdict,
                "verdict_label": verdict_label,
                "confidence": avg_conf,
                "participating_count": len(participating_doc_ids),
                "total_selected": len(selected_doc_ids),
                "summary": summary,
                "claims": formatted_claims
            })

        # Sort: first points with highest participation count, then contradictions/corroborations
        verdict_order = {"CONTRADICTS": 0, "CORROBORATES": 1, "CONTEXTUALIZES": 2, "UNCERTAIN": 3}
        consensus_points.sort(
            key=lambda cp: (-cp["participating_count"], verdict_order.get(cp["verdict"], 9))
        )

        formatted_docs = [
            {
                "id": d.id,
                "filename": d.filename,
                "page_count": d.page_count,
                "extracted_facts_count": d.extracted_facts_count
            }
            for d in documents
        ]

        return {
            "document_ids": selected_doc_ids,
            "documents": formatted_docs,
            "total_points": len(consensus_points),
            "consensus_points": consensus_points
        }
