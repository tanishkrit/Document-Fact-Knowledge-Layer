import re
from typing import List, Optional, Tuple, Dict, Any
from app.models.schemas import Fact, Relationship, RelationshipType
from app.models.qa_schemas import (
    CitationItem, ConflictPosition, ConflictResolution,
    ConflictResolutionStatus
)

class ConflictPrecedenceResolver:
    """
    Evaluates source precedence, version metadata, effective dates, and explicit amendments.
    Strictly preserves competing claims rather than silently blending them.
    """

    @staticmethod
    def _parse_year_or_date(date_str: Optional[str]) -> Optional[int]:
        if not date_str:
            return None
        match = re.search(r"\b(20\d{2}|19\d{2})\b", str(date_str))
        if match:
            return int(match.group(1))
        return None

    def evaluate_conflicts(
        self,
        relationships: List[Relationship],
        citations: List[CitationItem],
        facts: List[Fact]
    ) -> Optional[ConflictResolution]:
        """
        Scans for contradictions among active facts/citations and evaluates whether
        source precedence can resolve the conflict or if dual positions must be preserved.
        """
        contradictions = [r for r in relationships if r.type == RelationshipType.CONTRADICTS]
        
        # Filter to contradictions involving our retrieved documents
        active_doc_ids = set(c.document_id for c in citations)
        relevant_contradictions = []
        for rel in contradictions:
            if rel.fact_a and rel.fact_b:
                if rel.fact_a.evidence.document_id in active_doc_ids and rel.fact_b.evidence.document_id in active_doc_ids:
                    relevant_contradictions.append(rel)

        if not relevant_contradictions:
            return None

        # Analyze the primary relevant contradiction
        rel = relevant_contradictions[0]
        fact_a, fact_b = rel.fact_a, rel.fact_b

        # Retrieve citations/metadata for both
        cit_a = next((c for c in citations if c.document_id == fact_a.evidence.document_id), None)
        cit_b = next((c for c in citations if c.document_id == fact_b.evidence.document_id), None)

        date_a = cit_a.effective_date or cit_a.publication_date if cit_a else fact_a.context.time
        date_b = cit_b.effective_date or cit_b.publication_date if cit_b else fact_b.context.time

        year_a = self._parse_year_or_date(date_a)
        year_b = self._parse_year_or_date(date_b)

        # Check explicit supersession / amendment keywords in quotes
        quote_a = (cit_a.quote_text if cit_a else fact_a.evidence.text).lower()
        quote_b = (cit_b.quote_text if cit_b else fact_b.evidence.text).lower()

        is_b_amendment = any(kw in quote_b for kw in ["amends", "supersedes", "revised policy", "replaces", "updated policy"])
        is_a_amendment = any(kw in quote_a for kw in ["amends", "supersedes", "revised policy", "replaces", "updated policy"])

        pos_a = ConflictPosition(
            document_id=fact_a.evidence.document_id,
            document_name=fact_a.evidence.document_name,
            effective_date=date_a,
            claimed_value=fact_a.value.raw,
            evidence_text=fact_a.evidence.text,
            page=fact_a.evidence.page,
            authority="Authoritative Primary Document"
        )

        pos_b = ConflictPosition(
            document_id=fact_b.evidence.document_id,
            document_name=fact_b.evidence.document_name,
            effective_date=date_b,
            claimed_value=fact_b.value.raw,
            evidence_text=fact_b.evidence.text,
            page=fact_b.evidence.page,
            authority="Authoritative Primary Document"
        )

        # Precedence Rule 1: Explicit Amendment
        if is_b_amendment and not is_a_amendment:
            rationale = (
                f"Document '{fact_b.evidence.document_name}' explicitly amends or supersedes previous policies. "
                f"Its claim '{fact_b.value.raw}' takes legal/operational precedence over '{fact_a.value.raw}'."
            )
            return ConflictResolution(
                status=ConflictResolutionStatus.RESOLVED_BY_PRECEDENCE,
                rationale=rationale,
                preferred_position=pos_b,
                positions=[pos_a, pos_b],
                is_superseded=True,
                superseding_document_name=fact_b.evidence.document_name
            )

        if is_a_amendment and not is_b_amendment:
            rationale = (
                f"Document '{fact_a.evidence.document_name}' explicitly amends or supersedes previous policies. "
                f"Its claim '{fact_a.value.raw}' takes precedence over '{fact_b.value.raw}'."
            )
            return ConflictResolution(
                status=ConflictResolutionStatus.RESOLVED_BY_PRECEDENCE,
                rationale=rationale,
                preferred_position=pos_a,
                positions=[pos_a, pos_b],
                is_superseded=True,
                superseding_document_name=fact_a.evidence.document_name
            )

        # Precedence Rule 2: Temporal Recency with equal organizational authority
        if year_a and year_b and year_a != year_b:
            if year_b > year_a:
                rationale = (
                    f"Document '{fact_b.evidence.document_name}' has a newer effective date ({year_b}) "
                    f"than '{fact_a.evidence.document_name}' ({year_a}). Document '{fact_b.evidence.document_name}' "
                    f"is favored under chronological precedence, while retaining the historical record."
                )
                return ConflictResolution(
                    status=ConflictResolutionStatus.RESOLVED_BY_PRECEDENCE,
                    rationale=rationale,
                    preferred_position=pos_b,
                    positions=[pos_a, pos_b],
                    is_superseded=True,
                    superseding_document_name=fact_b.evidence.document_name
                )
            else:
                rationale = (
                    f"Document '{fact_a.evidence.document_name}' has a newer effective date ({year_a}) "
                    f"than '{fact_b.evidence.document_name}' ({year_b}). Chronological precedence favors '{fact_a.evidence.document_name}'."
                )
                return ConflictResolution(
                    status=ConflictResolutionStatus.RESOLVED_BY_PRECEDENCE,
                    rationale=rationale,
                    preferred_position=pos_a,
                    positions=[pos_a, pos_b],
                    is_superseded=True,
                    superseding_document_name=fact_a.evidence.document_name
                )

        # Precedence Rule 3: Unresolved Conflict (Never blend incompatible claims)
        rationale = (
            f"Genuine contradiction detected for '{fact_a.subject}' {fact_a.predicate}. "
            f"'{fact_a.evidence.document_name}' states '{fact_a.value.raw}', while '{fact_b.evidence.document_name}' "
            f"claims '{fact_b.value.raw}'. Neither document contains explicit supersession metadata or unambiguous "
            f"date precedence. Both positions are presented without arbitrary resolution."
        )

        return ConflictResolution(
            status=ConflictResolutionStatus.UNRESOLVED_CONFLICT,
            rationale=rationale,
            preferred_position=None,
            positions=[pos_a, pos_b],
            is_superseded=False
        )
