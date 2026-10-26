import re
from typing import List, Tuple, Dict, Any, Set
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.models.schemas import Fact

class FactMatcher:
    def __init__(self, similarity_threshold: float = 0.35):
        self.similarity_threshold = similarity_threshold

    @staticmethod
    def _fact_text(fact: Fact) -> str:
        parts = [
            fact.subject,
            fact.predicate,
            fact.context.time or "",
            fact.context.geography or "",
            fact.context.scope or "",
            str(fact.value.unit or "")
        ]
        return " ".join([p for p in parts if p]).lower()

    @staticmethod
    def _subjects_match(subj_a: str, subj_b: str) -> bool:
        a = subj_a.lower().strip()
        b = subj_b.lower().strip()
        if a == b or a in b or b in a:
            return True
        # Check token intersection
        tokens_a = set(re.findall(r'\w+', a))
        tokens_b = set(re.findall(r'\w+', b))
        stop_words = {'the', 'a', 'an', 'inc', 'corp', 'company', 'ltd', 'llc'}
        tokens_a -= stop_words
        tokens_b -= stop_words
        return len(tokens_a.intersection(tokens_b)) > 0

    @staticmethod
    def _predicates_match(pred_a: str, pred_b: str) -> bool:
        a = pred_a.lower().strip()
        b = pred_b.lower().strip()
        if a == b or a in b or b in a:
            return True
        
        # Synonyms and related terminology
        synonym_groups = [
            {'revenue', 'sales', 'turnover', 'earnings', 'top-line', 'top line', 'gross revenue', 'annual revenue', 'revenue from services', 'revenue from operations', 'revenue from contract with customers'},
            {'ebitda', 'service ebitda', 'adjusted ebitda', 'adj. ebitda', 'operating profit', 'operating ebitda'},
            {'profit', 'net income', 'operating profit', 'net profit', 'net profit / loss', 'pat', 'profit after tax', 'restated loss', 'net loss'},
            {'operating margin', 'ebitda margin', 'service ebitda margin', 'adj. ebitda margin'},
            {'express parcel shipments', 'parcels shipped', 'shipments', 'parcel volume', 'shipments volume', 'express parcels shipped'},
            {'ptl freight tonnage', 'part-truckload freight', 'freight tonnage', 'tonnes delivered', 'ptl freight delivered'},
            {'pincode reach', 'pin codes covered', 'pin codes', 'pincodes', 'pin-code reach', 'pin codes reach'},
            {'employees', 'headcount', 'workforce', 'staff', 'workers', 'team size', 'workforce strength'},
            {'active customers', 'customer base', 'no. of active customers'},
            {'fleet size', 'daily average fleet', 'tractors', 'vehicles', 'fleet'},
            {'gateways', 'automated sort centers', 'facilities', 'delivery centers', 'delivery centres'},
            {'infrastructure area', 'logistics area', 'million sq ft', 'sq ft'},
            {'founded', 'established', 'created', 'started', 'incorporation', 'founding year', 'inception'},
            {'ceo', 'chief executive officer', 'managing director', 'leader', 'executive'},
            {'headquarters', 'hq', 'base', 'office location', 'based in', 'registered office'},
            {'market share', 'market portion', 'share of market'}
        ]
        for group in synonym_groups:
            if any(term in a for term in group) and any(term in b for term in group):
                return True
        return False

    def find_candidate_pairs(self, facts: List[Fact]) -> List[Tuple[Fact, Fact, float]]:
        """
        Finds pairs of related facts across different documents.
        Returns List of (fact_a, fact_b, similarity_score).
        """
        if len(facts) < 2:
            return []

        # Filter cross-document pairs
        corpus = [self._fact_text(f) for f in facts]
        
        try:
            vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
            tfidf_matrix = vectorizer.fit_transform(corpus)
            sim_matrix = cosine_similarity(tfidf_matrix)
        except Exception:
            sim_matrix = np.zeros((len(facts), len(facts)))

        pairs_by_doc_combo: Dict[Tuple[str, str], List[Tuple[Fact, Fact, float]]] = {}
        seen_pairs: Set[Tuple[str, str]] = set()

        for i in range(len(facts)):
            for j in range(i + 1, len(facts)):
                fact_a = facts[i]
                fact_b = facts[j]

                # Primarily match cross-document
                if fact_a.evidence.document_id == fact_b.evidence.document_id:
                    continue

                pair_key = tuple(sorted([fact_a.id, fact_b.id]))
                if pair_key in seen_pairs:
                    continue

                sim_score = float(sim_matrix[i, j]) if sim_matrix.size > 0 else 0.0
                subj_match = self._subjects_match(fact_a.subject, fact_b.subject)
                pred_match = self._predicates_match(fact_a.predicate, fact_b.predicate)

                # Metric dimension compatibility check (e.g., % vs raw numeric count/currency)
                unit_a = (fact_a.value.unit or "").strip()
                unit_b = (fact_b.value.unit or "").strip()
                is_pct_a = (unit_a == "%" or "%" in fact_a.value.raw)
                is_pct_b = (unit_b == "%" or "%" in fact_b.value.raw)
                if is_pct_a != is_pct_b:
                    continue

                # Require compatible subject AND compatible predicate (Phase 3 requirement 1 & 2)
                if subj_match and pred_match:
                    boosted_score = sim_score
                    if subj_match and pred_match:
                        boosted_score = max(sim_score, 0.88)
                    elif pred_match:
                        boosted_score = max(sim_score, 0.72)

                    # Boost candidate score if facts have rich context (time or scope)
                    has_ctx_a = bool(fact_a.context.time or fact_a.context.scope)
                    has_ctx_b = bool(fact_b.context.time or fact_b.context.scope)
                    if has_ctx_a and has_ctx_b:
                        boosted_score += 0.08
                    elif has_ctx_a or has_ctx_b:
                        boosted_score += 0.03

                    doc_combo = tuple(sorted([fact_a.evidence.document_id, fact_b.evidence.document_id]))
                    if doc_combo not in pairs_by_doc_combo:
                        pairs_by_doc_combo[doc_combo] = []
                    pairs_by_doc_combo[doc_combo].append((fact_a, fact_b, round(boosted_score, 3)))
                    seen_pairs.add(pair_key)

        candidate_pairs: List[Tuple[Fact, Fact, float]] = []
        for combo, combo_pairs in pairs_by_doc_combo.items():
            combo_pairs.sort(key=lambda x: x[2], reverse=True)
            # Take top 20 candidate pairs per document pair
            candidate_pairs.extend(combo_pairs[:20])

        candidate_pairs.sort(key=lambda x: x[2], reverse=True)
        return candidate_pairs[:300]
