import uuid
from typing import List, Optional, Dict, Any
from app.models.schemas import Document, Fact, Relationship
from app.models.qa_schemas import (
    QAVerificationResponse, QAVerdict, QARequest,
    CriticReport, ConflictResolutionStatus
)
from app.services.qa.retriever import Retriever
from app.services.qa.synthesizer import Synthesizer
from app.services.qa.critic import Critic
from app.services.qa.precedence import ConflictPrecedenceResolver

class QAOrchestrator:
    """
    Coordinates Multi-Agent Verification Workflow:
    Retriever -> Synthesizer -> Critic (Adversary) -> Bounded Revision Loop -> Conflict Precedence Resolver
    """

    def __init__(self, api_key: Optional[str] = None):
        self.retriever = Retriever()
        self.synthesizer = Synthesizer(api_key=api_key)
        self.critic = Critic()
        self.resolver = ConflictPrecedenceResolver()

    def process_question(
        self,
        question: str,
        documents: List[Document],
        facts: List[Fact],
        relationships: List[Relationship],
        max_passages: int = 8
    ) -> QAVerificationResponse:
        qid = f"qa_{uuid.uuid4().hex[:8]}"
        clean_q = question.strip()

        # Step 1: Retrieval
        passages, matching_facts, has_sufficient_evidence, max_score = self.retriever.retrieve(
            question=clean_q,
            documents=documents,
            facts=facts,
            top_k=max_passages
        )

        # Insufficient Evidence Gate
        if not has_sufficient_evidence or not passages:
            res = self.synthesizer.build_insufficient_evidence_response(clean_q)
            return QAVerificationResponse(
                question_id=qid,
                question=clean_q,
                verdict=QAVerdict.INSUFFICIENT_EVIDENCE,
                final_answer=res["final_answer"],
                draft_answer=res["draft_answer"],
                claims=res["claims"],
                citations=[],
                critic_history=[
                    CriticReport(
                        round_number=1,
                        passed=False,
                        issues=[],
                        summary="Retriever found no relevant evidence passages meeting the confidence cutoff."
                    )
                ],
                iterations_run=1,
                retrieved_passages_count=len(passages),
                insufficient_evidence_reason=res.get("insufficient_evidence_reason")
            )

        # Step 2: Initial Synthesis (Draft)
        synth_res = self.synthesizer.synthesize(
            question=clean_q,
            passages=passages,
            facts=matching_facts
        )

        draft_answer = synth_res.get("draft_answer", "")
        claims = synth_res.get("claims", [])
        citations = synth_res.get("citations", [])

        # Step 3: Bounded Critic Cycle (Round 1)
        critic_history: List[CriticReport] = []
        report_r1 = self.critic.evaluate(
            draft_answer=draft_answer,
            claims=claims,
            citations=citations,
            facts=facts,
            relationships=relationships,
            round_number=1
        )
        critic_history.append(report_r1)

        iterations = 1
        final_answer = draft_answer

        # Step 4: Revision Loop (If Critical Flaws Found, Max 1 Revision)
        if not report_r1.passed:
            iterations += 1
            critique_guidance = "\n".join([f"- {issue.issue_type.value}: {issue.description}" for issue in report_r1.issues])
            
            # Re-synthesize with adversary guidance
            revised_synth = self.synthesizer.synthesize(
                question=clean_q,
                passages=passages,
                facts=matching_facts,
                critique_notes=critique_guidance
            )
            final_answer = revised_synth.get("final_answer", draft_answer)
            claims = revised_synth.get("claims", claims)

            # Critic Round 2 (Re-evaluating revised draft)
            report_r2 = self.critic.evaluate(
                draft_answer=final_answer,
                claims=claims,
                citations=citations,
                facts=facts,
                relationships=relationships,
                round_number=2
            )
            critic_history.append(report_r2)

        # Step 5: Conflict Resolution & Source Precedence
        conflict_res = self.resolver.evaluate_conflicts(
            relationships=relationships,
            citations=citations,
            facts=facts
        )

        # Determine Verdict
        verdict = QAVerdict.VERIFIED
        if conflict_res:
            if conflict_res.status == ConflictResolutionStatus.UNRESOLVED_CONFLICT:
                verdict = QAVerdict.CONFLICT_DETECTED
                # Append explicit dual-position explanation if not already in final answer
                pos_a = conflict_res.positions[0]
                pos_b = conflict_res.positions[1]
                dual_clarification = (
                    f"\n\n[TruthGuard Conflict Advisory]: An unresolved factual contradiction exists. "
                    f"{pos_a.document_name} asserts '{pos_a.claimed_value}' (p. {pos_a.page}), whereas "
                    f"{pos_b.document_name} asserts '{pos_b.claimed_value}' (p. {pos_b.page}). "
                    f"Neither source contains superseding authority; both claims are retained."
                )
                if pos_a.claimed_value not in final_answer or pos_b.claimed_value not in final_answer:
                    final_answer = final_answer + dual_clarification
            elif conflict_res.status == ConflictResolutionStatus.RESOLVED_BY_PRECEDENCE:
                verdict = QAVerdict.VERIFIED

        return QAVerificationResponse(
            question_id=qid,
            question=clean_q,
            verdict=verdict,
            final_answer=final_answer,
            draft_answer=draft_answer,
            claims=claims,
            citations=citations,
            critic_history=critic_history,
            iterations_run=iterations,
            conflict_resolution=conflict_res,
            retrieved_passages_count=len(passages)
        )
