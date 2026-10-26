import re
from typing import List, Dict, Any, Optional
from app.models.schemas import Fact, Relationship, RelationshipType
from app.models.qa_schemas import (
    ClaimItem, CitationItem, CriticIssue, CriticIssueType,
    CriticIssueSeverity, CriticReport
)

class Critic:
    """
    Adversary Agent that actively challenges draft answers.
    Evaluates:
    1. Direct contradictions across passages/facts
    2. Ungrounded assertions (missing citations)
    3. Citation validity (mismatch between claim & cited text)
    4. Context mismatches (comparing different time/geography)
    5. Staleness & Supersession (older policy vs newer amendment)
    """

    def evaluate(
        self,
        draft_answer: str,
        claims: List[ClaimItem],
        citations: List[CitationItem],
        facts: List[Fact],
        relationships: List[Relationship],
        round_number: int = 1
    ) -> CriticReport:
        issues: List[CriticIssue] = []

        citations_map = {c.citation_id: c for c in citations}
        
        # 1. Check for Ungrounded Claims
        for claim in claims:
            if not claim.citation_ids:
                issues.append(CriticIssue(
                    issue_type=CriticIssueType.UNGROUNDED_CLAIM,
                    severity=CriticIssueSeverity.HIGH,
                    description=f"Claim '{claim.text[:80]}...' contains no supporting citation.",
                    affected_claim_id=claim.claim_id,
                    recommendation="Attach source citation or remove the ungrounded claim."
                ))
            else:
                for cit_id in claim.citation_ids:
                    if cit_id not in citations_map:
                        issues.append(CriticIssue(
                            issue_type=CriticIssueType.INVALID_CITATION,
                            severity=CriticIssueSeverity.HIGH,
                            description=f"Claim references non-existent citation ID '{cit_id}'.",
                            affected_claim_id=claim.claim_id
                        ))

        # 2. Check Citation Validity (Token Overlap Verification)
        for claim in claims:
            for cit_id in claim.citation_ids:
                cit = citations_map.get(cit_id)
                if not cit:
                    continue

                claim_tokens = set(re.findall(r"\w{3,}", claim.text.lower()))
                quote_tokens = set(re.findall(r"\w{3,}", cit.quote_text.lower()))

                overlap = len(claim_tokens.intersection(quote_tokens))
                if claim_tokens and overlap == 0 and claim.claim_type != "inference":
                    issues.append(CriticIssue(
                        issue_type=CriticIssueType.INVALID_CITATION,
                        severity=CriticIssueSeverity.MEDIUM,
                        description=(
                            f"Cited text in {cit.document_name} (p. {cit.page}) does not exhibit "
                            f"verifiable semantic overlap with claim: '{claim.text[:60]}...'"
                        ),
                        affected_claim_id=claim.claim_id,
                        counter_evidence=cit,
                        recommendation="Verify exact quote boundaries and page alignment."
                    ))

        # 3. Check for Direct Contradictions in Corpus
        # If any known CONTRADICTS relationship exists between facts in the active documents
        relevant_doc_ids = set(c.document_id for c in citations)
        for rel in relationships:
            if rel.type == RelationshipType.CONTRADICTS:
                # Check if this contradiction relates to the active documents
                if rel.fact_a and rel.fact_b:
                    doc_a_id = rel.fact_a.evidence.document_id
                    doc_b_id = rel.fact_b.evidence.document_id
                    if doc_a_id in relevant_doc_ids or doc_b_id in relevant_doc_ids:
                        # Does the draft acknowledge the contradiction or pick one side?
                        subj = rel.fact_a.subject.lower()
                        pred = rel.fact_a.predicate.lower()
                        if subj in draft_answer.lower() or pred in draft_answer.lower():
                            # Check if both values are stated
                            val_a = rel.fact_a.value.raw.lower()
                            val_b = rel.fact_b.value.raw.lower()
                            if not (val_a in draft_answer.lower() and val_b in draft_answer.lower()):
                                issues.append(CriticIssue(
                                    issue_type=CriticIssueType.CONTRADICTION,
                                    severity=CriticIssueSeverity.HIGH,
                                    description=(
                                        f"Direct contradiction detected between '{rel.fact_a.evidence.document_name}' "
                                        f"({val_a}) and '{rel.fact_b.evidence.document_name}' ({val_b}) for {subj} {pred}. "
                                        f"The draft currently states only one version without acknowledging the opposing claim."
                                    ),
                                    counter_evidence=CitationItem(
                                        citation_id="contra_cit",
                                        document_id=doc_b_id,
                                        document_name=rel.fact_b.evidence.document_name,
                                        page=rel.fact_b.evidence.page,
                                        quote_text=rel.fact_b.evidence.text
                                    ),
                                    recommendation="Disclose both competing positions side-by-side with source provenance."
                                ))

        # 4. Check for Staleness & Supersession
        # Detect if any citation comes from an older document when a newer version/amendment exists
        for c1 in citations:
            eff_1 = c1.effective_date or c1.publication_date
            for c2 in citations:
                eff_2 = c2.effective_date or c2.publication_date
                if eff_1 and eff_2 and eff_1 != eff_2:
                    y1 = re.search(r"\b(20\d{2}|19\d{2})\b", eff_1)
                    y2 = re.search(r"\b(20\d{2}|19\d{2})\b", eff_2)
                    if y1 and y2 and int(y2.group(1)) > int(y1.group(1)):
                        if c1.document_id != c2.document_id:
                            issues.append(CriticIssue(
                                issue_type=CriticIssueType.STALE_VERSION,
                                severity=CriticIssueSeverity.MEDIUM,
                                description=(
                                    f"Document '{c1.document_name}' ({eff_1}) may be superseded by "
                                    f"newer document '{c2.document_name}' ({eff_2})."
                                ),
                                counter_evidence=c2,
                                recommendation="Apply source precedence to favor the newer document or note the revision timeline."
                            ))
                            break

        # 5. Check Context Mismatch
        for claim in claims:
            # Detect temporal mixing (e.g. using FY2023 number as current without qualification)
            time_matches = re.findall(r"\b(20\d{2}|FY\d{2,4}|Q[1-4]\s*20\d{2})\b", claim.text, re.I)
            if len(time_matches) > 1 and " vs " not in claim.text and "compared" not in claim.text:
                issues.append(CriticIssue(
                    issue_type=CriticIssueType.CONTEXT_MISMATCH,
                    severity=CriticIssueSeverity.LOW,
                    description=f"Multiple distinct timeframes ({', '.join(time_matches)}) referenced in a single claim without explicit temporal reconciliation.",
                    affected_claim_id=claim.claim_id,
                    recommendation="Clarify temporal boundary for each metric."
                ))

        high_severity_count = sum(1 for i in issues if i.severity == CriticIssueSeverity.HIGH)
        passed = high_severity_count == 0

        summary = (
            f"Adversary verification passed cleanly with no critical flaws."
            if passed and not issues
            else f"Adversary detected {len(issues)} finding(s) ({high_severity_count} critical). Revision advised."
            if not passed
            else f"Adversary noted {len(issues)} non-critical contextual finding(s)."
        )

        return CriticReport(
            round_number=round_number,
            passed=passed,
            issues=issues,
            summary=summary
        )
