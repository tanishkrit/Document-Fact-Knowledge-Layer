import uuid
from typing import Optional, Dict, Any, Tuple
from app.models.schemas import Fact, Relationship, RelationshipType, FactValueType

class RelationshipEngine:
    """
    Hybrid Reasoning Engine to classify relationships between candidate facts:
    CORROBORATES, CONTRADICTS, CONTEXTUALIZES, RELATED, UNCERTAIN
    """

    @staticmethod
    def _compare_values(val_a, val_b) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Compares two FactValue objects.
        Returns: (are_equal, comparison_note, diff_dict)
        """
        diff = {
            "val_a_raw": val_a.raw,
            "val_b_raw": val_b.raw,
            "val_a_normalized": val_a.amount if val_a.amount is not None else val_a.raw,
            "val_b_normalized": val_b.amount if val_b.amount is not None else val_b.raw,
            "unit_a": val_a.unit or val_a.currency,
            "unit_b": val_b.unit or val_b.currency,
        }

        # Both numerical or dates
        if val_a.amount is not None and val_b.amount is not None:
            # Check unit compatibility
            unit_a = (val_a.currency or val_a.unit or "").lower()
            unit_b = (val_b.currency or val_b.unit or "").lower()
            
            # If units exist and conflict
            if unit_a and unit_b and unit_a != unit_b:
                diff["unit_mismatch"] = True
                return False, f"Unit difference ({unit_a} vs {unit_b})", diff

            # For dates or years: MUST be exact match (e.g., 2012 != 2015)
            is_date_or_year = (
                val_a.type == FactValueType.DATE or 
                val_b.type == FactValueType.DATE or 
                unit_a in ["year", "years"] or 
                unit_b in ["year", "years"] or
                (1900 <= val_a.amount <= 2099 and 1900 <= val_b.amount <= 2099 and not val_a.currency and not val_b.currency and not val_a.unit and not val_b.unit)
            )
            if is_date_or_year:
                if val_a.amount == val_b.amount:
                    return True, f"Year/Date matches: {int(val_a.amount)}", diff
                else:
                    return False, f"Different years: {int(val_a.amount)} vs {int(val_b.amount)}", diff

            # For general quantities: allow float rounding tolerance
            diff_abs = abs(val_a.amount - val_b.amount)
            max_val = max(abs(val_a.amount), abs(val_b.amount), 1e-9)
            relative_diff = diff_abs / max_val

            if relative_diff < 0.0005 or diff_abs < 0.01:
                return True, f"Normalized amounts match: {val_a.amount:g}", diff

            # 0.8% rounding tolerance applies specifically to scaled financial metrics (e.g., ₹8,142 Cr vs ₹81,415 Mn)
            is_scaled_financial = bool(
                val_a.currency or val_b.currency or 
                (unit_a and any(u in unit_a for u in ['usd', 'inr', 'rs', 'eur', 'cr', 'crore', 'mn', 'bn', 'units']))
            )
            if is_scaled_financial and relative_diff < 0.008:
                return True, f"Normalized amounts match within rounding tolerance: {val_a.amount:g} vs {val_b.amount:g}", diff
            else:
                return False, f"Amounts differ: {val_a.amount:g} vs {val_b.amount:g}", diff

        # String or categorical comparison
        str_a = val_a.raw.strip().lower()
        str_b = val_b.raw.strip().lower()
        if str_a == str_b:
            return True, f"Exact match: '{val_a.raw}'", diff

        # Partial token overlap
        tokens_a = set(str_a.split())
        tokens_b = set(str_b.split())
        if tokens_a == tokens_b or (len(tokens_a.intersection(tokens_b)) >= max(1, len(tokens_a) // 2)):
            return True, f"Semantic match: '{val_a.raw}' ≈ '{val_b.raw}'", diff

        return False, f"Values differ: '{val_a.raw}' vs '{val_b.raw}'", diff

    @staticmethod
    def _analyze_context_difference(ctx_a, ctx_b, fact_a: Optional[Fact] = None, fact_b: Optional[Fact] = None) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Analyzes if context (time, geography, scope, unit scale) differs significantly.
        Returns: (has_context_difference, explanation, diff_dict)
        """
        diff = {}
        explanations = []

        # Time analysis
        time_a = (ctx_a.time_normalized or ctx_a.time or "").strip().lower()
        time_b = (ctx_b.time_normalized or ctx_b.time or "").strip().lower()
        if time_a and time_b and time_a != time_b:
            diff["time"] = {"a": ctx_a.time, "b": ctx_b.time}
            explanations.append(f"Different time periods ({ctx_a.time} vs {ctx_b.time})")

        # Geography analysis
        geo_a = (ctx_a.geography or "").strip().lower()
        geo_b = (ctx_b.geography or "").strip().lower()
        if geo_a and geo_b and geo_a != geo_b:
            diff["geography"] = {"a": ctx_a.geography, "b": ctx_b.geography}
            explanations.append(f"Different geographies ({ctx_a.geography} vs {ctx_b.geography})")

        # Scope analysis
        scope_a = (ctx_a.scope or "").strip().lower()
        scope_b = (ctx_b.scope or "").strip().lower()
        if scope_a and scope_b and scope_a != scope_b:
            diff["scope"] = {"a": ctx_a.scope, "b": ctx_b.scope}
            explanations.append(f"Different scopes ({ctx_a.scope} vs {ctx_b.scope})")

        # Unit / Metric scale mismatch
        if fact_a and fact_b:
            unit_a = (fact_a.value.unit or fact_a.value.currency or "").strip().lower()
            unit_b = (fact_b.value.unit or fact_b.value.currency or "").strip().lower()
            if unit_a and unit_b and unit_a != unit_b:
                diff["unit"] = {"a": unit_a, "b": unit_b}
                explanations.append(f"Different metric units ({unit_a} vs {unit_b})")

        has_diff = len(explanations) > 0
        explanation_str = "; ".join(explanations) if has_diff else None
        return has_diff, explanation_str, diff

    @staticmethod
    def _calculate_confidence(
        rel_type: RelationshipType,
        fact_a: Fact,
        fact_b: Fact,
        values_equal: bool,
        has_context_diff: bool,
        val_diff: Dict[str, Any],
        is_timeless: bool = False
    ) -> float:
        """
        Dynamically computes confidence based on:
        - Source extraction confidences of both facts
        - Presence and explicitness of temporal, geographic, and scope context
        - Exact numeric alignment vs fuzzy or rounding differences
        - Value precision and magnitude
        """
        base_conf = (fact_a.confidence + fact_b.confidence) / 2.0

        has_time_a = bool(fact_a.context.time or fact_a.context.time_normalized)
        has_time_b = bool(fact_b.context.time or fact_b.context.time_normalized)
        has_scope_a = bool(fact_a.context.scope)
        has_scope_b = bool(fact_b.context.scope)

        is_num_a = fact_a.value.amount is not None
        is_num_b = fact_b.value.amount is not None

        if rel_type == RelationshipType.CORROBORATES:
            conf = base_conf + (0.04 if (is_num_a and is_num_b) else 0.01)
            if has_time_a and has_time_b:
                conf += 0.02
            return round(min(0.97, max(0.72, conf)), 2)

        elif rel_type == RelationshipType.CONTRADICTS:
            if is_timeless:
                conf = base_conf + 0.03
            elif has_time_a and has_time_b:
                # Discrepancy in the exact same identified timeframe
                conf = base_conf + 0.02
            elif has_time_a or has_time_b:
                # One claim has timeframe, other lacks explicit timeframe
                conf = base_conf - 0.06
            else:
                conf = base_conf - 0.12
            return round(min(0.96, max(0.70, conf)), 2)

        elif rel_type == RelationshipType.CONTEXTUALIZES:
            diff_boost = 0.03 if (has_time_a and has_time_b) else (0.01 if (has_scope_a or has_scope_b) else -0.02)
            conf = base_conf * 0.94 + diff_boost
            return round(min(0.94, max(0.74, conf)), 2)

        elif rel_type == RelationshipType.UNCERTAIN:
            penalty = 0.28
            if not has_time_a and not has_time_b:
                penalty += 0.06
            conf = base_conf - penalty
            return round(min(0.68, max(0.40, conf)), 2)

        else:  # RELATED
            conf = base_conf - 0.14
            return round(min(0.85, max(0.60, conf)), 2)

    def evaluate_relationship(self, fact_a: Fact, fact_b: Fact) -> Relationship:
        rel_id = f"rel_{uuid.uuid4().hex[:8]}"

        # Compare values
        values_equal, val_note, val_diff = self._compare_values(fact_a.value, fact_b.value)

        # Compare context
        has_context_diff, context_note, context_diff = self._analyze_context_difference(fact_a.context, fact_b.context, fact_a, fact_b)

        TIMELESS_PREDICATES = {'founded', 'established', 'created', 'started', 'incorporated', 'origin', 'born'}
        is_timeless = (
            fact_a.predicate.lower() in TIMELESS_PREDICATES or 
            fact_b.predicate.lower() in TIMELESS_PREDICATES
        )

        # For timeless predicates like 'founded', different years represents a genuine contradiction
        if is_timeless:
            has_context_diff = False
            context_note = None
            context_diff = {}

        # Check for missing critical context (for time-sensitive metrics like revenue, market share)
        missing_context_a = not fact_a.context.time and not fact_a.context.scope and not is_timeless
        missing_context_b = not fact_b.context.time and not fact_b.context.scope and not is_timeless

        # Case 1: Corroboration
        # Values match and no conflicting context
        if values_equal and not has_context_diff:
            doc_a_name = fact_a.evidence.document_name
            doc_b_name = fact_b.evidence.document_name
            reason = (
                f"Both documents report compatible claims for '{fact_a.subject}' {fact_a.predicate}. "
                f"After canonical normalization, both values evaluate to equivalent representation ({val_note}). "
                f"Document '{doc_a_name}' (p. {fact_a.evidence.page}) corroborates Document '{doc_b_name}' (p. {fact_b.evidence.page})."
            )
            conf = self._calculate_confidence(
                RelationshipType.CORROBORATES, fact_a, fact_b, values_equal, has_context_diff, val_diff, is_timeless
            )
            return Relationship(
                id=rel_id,
                fact_a_id=fact_a.id,
                fact_b_id=fact_b.id,
                fact_a=fact_a,
                fact_b=fact_b,
                type=RelationshipType.CORROBORATES,
                confidence=conf,
                reason=reason,
                context_diff=context_diff,
                value_diff=val_diff
            )

        # Values differ: Analyze alignment
        if not values_equal:
            # Case 2A: Timeless properties (e.g. founded, CEO, headquarters) -> Genuine Contradiction
            if is_timeless:
                time_str = f" in {fact_a.context.time}" if fact_a.context.time else ""
                reason = (
                    f"Genuine contradiction detected for '{fact_a.subject}' {fact_a.predicate}{time_str}. "
                    f"Document '{fact_a.evidence.document_name}' states '{val_diff['val_a_raw']}', whereas "
                    f"Document '{fact_b.evidence.document_name}' claims '{val_diff['val_b_raw']}'. "
                    f"Both statements refer to the same underlying entity and property without reconciling context."
                )
                conf = self._calculate_confidence(
                    RelationshipType.CONTRADICTS, fact_a, fact_b, values_equal, has_context_diff, val_diff, is_timeless
                )
                return Relationship(
                    id=rel_id,
                    fact_a_id=fact_a.id,
                    fact_b_id=fact_b.id,
                    fact_a=fact_a,
                    fact_b=fact_b,
                    type=RelationshipType.CONTRADICTS,
                    confidence=conf,
                    reason=reason,
                    context_diff=context_diff,
                    value_diff=val_diff
                )

            # Case 2B: Missing context on either side -> UNCERTAIN
            if missing_context_a or missing_context_b:
                missing_part = []
                if missing_context_a:
                    missing_part.append(f"Document '{fact_a.evidence.document_name}' lacks explicit temporal or scope context")
                if missing_context_b:
                    missing_part.append(f"Document '{fact_b.evidence.document_name}' lacks explicit temporal or scope context")
                
                missing_desc = " and ".join(missing_part)
                reason = (
                    f"Relationship between claims '{val_diff['val_a_raw']}' and '{val_diff['val_b_raw']}' is UNCERTAIN. "
                    f"{missing_desc}. Without verified timeframe or scope, the system cannot decisively declare a contradiction or corroboration."
                )
                conf = self._calculate_confidence(
                    RelationshipType.UNCERTAIN, fact_a, fact_b, values_equal, has_context_diff, val_diff, is_timeless
                )
                return Relationship(
                    id=rel_id,
                    fact_a_id=fact_a.id,
                    fact_b_id=fact_b.id,
                    fact_a=fact_a,
                    fact_b=fact_b,
                    type=RelationshipType.UNCERTAIN,
                    confidence=conf,
                    reason=reason,
                    context_diff=context_diff,
                    value_diff=val_diff
                )

            # Case 2C: Identical explicit context -> Genuine Contradiction
            if not has_context_diff:
                time_str = f" in {fact_a.context.time}" if fact_a.context.time else ""
                reason = (
                    f"Genuine contradiction detected for '{fact_a.subject}' {fact_a.predicate}{time_str}. "
                    f"Document '{fact_a.evidence.document_name}' states '{val_diff['val_a_raw']}', whereas "
                    f"Document '{fact_b.evidence.document_name}' claims '{val_diff['val_b_raw']}'. "
                    f"Both statements refer to the same underlying entity and property without reconciling context."
                )
                conf = self._calculate_confidence(
                    RelationshipType.CONTRADICTS, fact_a, fact_b, values_equal, has_context_diff, val_diff, is_timeless
                )
                return Relationship(
                    id=rel_id,
                    fact_a_id=fact_a.id,
                    fact_b_id=fact_b.id,
                    fact_a=fact_a,
                    fact_b=fact_b,
                    type=RelationshipType.CONTRADICTS,
                    confidence=conf,
                    reason=reason,
                    context_diff=context_diff,
                    value_diff=val_diff
                )

            # Case 2D: Apparent Contradiction -> CONTEXTUALIZES
            # Both sides have explicit, distinct context (time, scope, geography) that explains the difference
            if has_context_diff:
                reason = (
                    f"Apparent contradiction in '{fact_a.subject}' {fact_a.predicate} ({val_diff['val_a_raw']} vs {val_diff['val_b_raw']}) "
                    f"is resolved by context: {context_note}. "
                    f"The claims describe different scopes, timeframes, or geographical boundaries and do not genuinely conflict."
                )
                conf = self._calculate_confidence(
                    RelationshipType.CONTEXTUALIZES, fact_a, fact_b, values_equal, has_context_diff, val_diff, is_timeless
                )
                return Relationship(
                    id=rel_id,
                    fact_a_id=fact_a.id,
                    fact_b_id=fact_b.id,
                    fact_a=fact_a,
                    fact_b=fact_b,
                    type=RelationshipType.CONTEXTUALIZES,
                    confidence=conf,
                    reason=reason,
                    context_diff=context_diff,
                    value_diff=val_diff
                )

        # Default fallback: RELATED
        conf = self._calculate_confidence(
            RelationshipType.RELATED, fact_a, fact_b, values_equal, has_context_diff, val_diff, is_timeless
        )
        return Relationship(
            id=rel_id,
            fact_a_id=fact_a.id,
            fact_b_id=fact_b.id,
            fact_a=fact_a,
            fact_b=fact_b,
            type=RelationshipType.RELATED,
            confidence=conf,
            reason=f"Claims share subject '{fact_a.subject}' and related topic, but address distinct attributes.",
            context_diff=context_diff,
            value_diff=val_diff
        )
