import os
import re
import json
import uuid
from typing import List, Dict, Any, Tuple, Optional
from app.models.schemas import Fact
from app.models.qa_schemas import (
    ClaimItem, CitationItem, ClaimType, QAVerdict, QAVerificationResponse
)

class Synthesizer:
    """
    Evidence-grounded Synthesizer that drafts answers from retrieved passages
    and facts, categorizing individual claims as directly supported or inferred,
    and binding exact citations.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

    def build_insufficient_evidence_response(self, question: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Returns structured response when documents lack required evidence."""
        explanation = reason or (
            f"The uploaded document corpus does not contain sufficient factual evidence to reliably answer "
            f"the question: \"{question}\". To avoid hallucination, no speculative claims have been made."
        )
        return {
            "verdict": QAVerdict.INSUFFICIENT_EVIDENCE,
            "final_answer": explanation,
            "draft_answer": explanation,
            "claims": [
                ClaimItem(
                    claim_id="claim_insufficient",
                    text="Corpus lacks direct evidence for the inquired subject.",
                    claim_type=ClaimType.UNSUPPORTED,
                    citation_ids=[],
                    confidence=1.0,
                    provenance_note="Insufficient evidence cutoff triggered."
                )
            ],
            "citations": [],
            "insufficient_evidence_reason": explanation
        }

    def synthesize(
        self,
        question: str,
        passages: List[Dict[str, Any]],
        facts: List[Fact],
        critique_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Drafts a candidate answer with discrete claim decomposition and exact citations.
        """
        if not passages and not facts:
            return self.build_insufficient_evidence_response(question)

        # Build citations table
        citations: List[CitationItem] = []
        for idx, p in enumerate(passages):
            cit_id = f"cit_{idx + 1}"
            citations.append(CitationItem(
                citation_id=cit_id,
                document_id=p["document_id"],
                document_name=p["document_name"],
                page=p["page"],
                quote_text=p["text"],
                location=p.get("location"),
                publication_date=p.get("metadata", {}).get("publication_date"),
                effective_date=p.get("metadata", {}).get("effective_date")
            ))

        # Try LLM synthesis if API key is present
        llm_result = None
        if self.api_key:
            try:
                llm_result = self._synthesize_with_gemini(question, citations, facts, critique_notes)
            except Exception as e:
                print(f"[Synthesizer] Gemini synthesis failed, using deterministic fallback: {e}")

        if llm_result:
            return llm_result

        # Deterministic Rule-Based Fallback
        return self._synthesize_deterministic(question, citations, facts, critique_notes)

    def _synthesize_deterministic(
        self,
        question: str,
        citations: List[CitationItem],
        facts: List[Fact],
        critique_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Deterministic synthesis that quotes source evidence and extracts claims with provenance.
        """
        claims: List[ClaimItem] = []
        answer_parts: List[str] = []

        # Find best matching citations
        q_lower = question.lower()
        key_citations = citations[:3] if citations else []

        for idx, cit in enumerate(key_citations):
            claim_id = f"claim_{idx + 1}"
            # Extract most relevant sentence
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cit.quote_text) if len(s.strip()) > 10]
            best_sentence = sentences[0] if sentences else cit.quote_text[:120]
            for s in sentences:
                if any(w in s.lower() for w in q_lower.split() if len(w) > 3):
                    best_sentence = s
                    break

            claims.append(ClaimItem(
                claim_id=claim_id,
                text=best_sentence,
                claim_type=ClaimType.DIRECTLY_SUPPORTED,
                citation_ids=[cit.citation_id],
                confidence=0.92,
                provenance_note=f"Extracted verbatim from {cit.document_name}, p. {cit.page}"
            ))

            answer_parts.append(f"{best_sentence} [{cit.document_name}, p. {cit.page}]")

        # Synthesize synthesis statement
        if len(claims) > 1:
            inference_claim_id = f"claim_{len(claims) + 1}"
            all_cit_ids = [c.citation_id for c in key_citations]
            doc_names = list(set(c.document_name for c in key_citations))
            inference_text = (
                f"Across {len(doc_names)} source document(s) ({', '.join(doc_names)}), "
                f"the evidence collectively establishes these reported figures."
            )
            claims.append(ClaimItem(
                claim_id=inference_claim_id,
                text=inference_text,
                claim_type=ClaimType.INFERENCE,
                citation_ids=all_cit_ids,
                confidence=0.88,
                provenance_note="Synthesized conclusion from multiple cross-document passages."
            ))

        final_text = " ".join(answer_parts)
        if not final_text:
            return self.build_insufficient_evidence_response(question)

        return {
            "verdict": QAVerdict.VERIFIED,
            "draft_answer": final_text,
            "final_answer": final_text,
            "claims": claims,
            "citations": citations
        }

    def _synthesize_with_gemini(
        self,
        question: str,
        citations: List[CitationItem],
        facts: List[Fact],
        critique_notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Invokes Gemini 2.5 Flash to generate structured claim synthesis."""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)

        evidence_payload = [
            {
                "citation_id": c.citation_id,
                "document": c.document_name,
                "page": c.page,
                "text": c.quote_text
            }
            for c in citations[:6]
        ]

        facts_payload = [
            {
                "subject": f.subject,
                "predicate": f.predicate,
                "value": f.value.raw,
                "context": f.context.dict()
            }
            for f in facts[:8]
        ]

        critique_instruction = ""
        if critique_notes:
            critique_instruction = f"\nPREVIOUS ADVERSARY CRITIQUE (You must revise your answer to address these flaws):\n{critique_notes}\n"

        prompt = f"""
You are the TruthGuard Synthesizer Agent.
Task: Answer the user's question STRICTLY based on the provided evidence.

CRITICAL RULES:
1. Every material claim MUST cite a specific citation_id (e.g., ["cit_1"]).
2. Classify each claim as either "directly_supported" (stated directly in text) or "inference" (logical deduction).
3. Do NOT extrapolate or introduce external facts.
4. If there is a contradiction in the evidence, state both claims clearly. Never silently blend them.
5. If evidence is insufficient, state that clearly.
{critique_instruction}
User Question: "{question}"

Evidence Passages:
{json.dumps(evidence_payload, indent=2)}

Structured Facts:
{json.dumps(facts_payload, indent=2)}

Respond with a JSON object conforming exactly to this structure:
{{
  "answer": "Complete answer narrative with citation tags like [Doc A, p.1]",
  "claims": [
    {{
      "claim_id": "claim_1",
      "text": "Specific assertion sentence",
      "claim_type": "directly_supported" or "inference",
      "citation_ids": ["cit_1"],
      "confidence": 0.95
    }}
  ]
}}
"""
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        data = json.loads(response.text)
        claims = []
        for c in data.get("claims", []):
            claims.append(ClaimItem(
                claim_id=c.get("claim_id", f"claim_{uuid.uuid4().hex[:4]}"),
                text=c.get("text", ""),
                claim_type=ClaimType(c.get("claim_type", "directly_supported")),
                citation_ids=c.get("citation_ids", []),
                confidence=float(c.get("confidence", 0.9))
            ))

        return {
            "verdict": QAVerdict.VERIFIED,
            "draft_answer": data.get("answer", ""),
            "final_answer": data.get("answer", ""),
            "claims": claims,
            "citations": citations
        }
