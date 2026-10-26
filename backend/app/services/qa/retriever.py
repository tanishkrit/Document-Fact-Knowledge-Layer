import re
from typing import List, Dict, Any, Optional, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.models.schemas import Document, Fact, PageData
from app.models.qa_schemas import CitationItem

class Retriever:
    """
    Evidence-first retriever that searches both raw document passages and
    extracted facts, identifying relevant quotes, page numbers, and temporal metadata.
    """

    DATE_PATTERNS = [
        re.compile(r"(?:effective(?:\s+date)?[:\s]+)([A-Za-z]+ \d{1,2},? \d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4})", re.IGNORECASE),
        re.compile(r"(?:published(?:\s+date)?[:\s]+)([A-Za-z]+ \d{1,2},? \d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4})", re.IGNORECASE),
        re.compile(r"(?:amends|supersedes)\s+([^\.\n]+)", re.IGNORECASE),
        re.compile(r"(?:version|v)[\s\.:]*(\d+(?:\.\d+)?)", re.IGNORECASE),
        re.compile(r"\b(20\d{2}|19\d{2})\b")
    ]

    def __init__(self, relevance_threshold: float = 0.12):
        self.relevance_threshold = relevance_threshold

    def _extract_metadata_from_text(self, text: str) -> Dict[str, Optional[str]]:
        """Extracts effective date, publication date, version, and supersession hints."""
        meta = {
            "effective_date": None,
            "publication_date": None,
            "version": None,
            "amends_or_supersedes": None
        }

        # Effective date
        eff_match = re.search(r"effective(?:\s+date)?[:\s]+([A-Za-z]+ \d{1,2},? \d{4}|\d{4})", text, re.I)
        if eff_match:
            meta["effective_date"] = eff_match.group(1).strip()

        # Published date
        pub_match = re.search(r"(?:published|date)[:\s]+([A-Za-z]+ \d{1,2},? \d{4}|\d{4})", text, re.I)
        if pub_match:
            meta["publication_date"] = pub_match.group(1).strip()

        # Version
        ver_match = re.search(r"(?:version|v)[\s\.:]*(\d+(?:\.\d+)?)", text, re.I)
        if ver_match:
            meta["version"] = ver_match.group(1).strip()

        # Amendment / supersedes
        super_match = re.search(r"(?:amends|supersedes|replaces)\s+([^,;\.\n]+)", text, re.I)
        if super_match:
            meta["amends_or_supersedes"] = super_match.group(1).strip()

        # Fallback year search
        if not meta["effective_date"] and not meta["publication_date"]:
            years = re.findall(r"\b(20\d{2}|19\d{2})\b", text)
            if years:
                meta["publication_date"] = years[0]

        return meta

    def chunk_documents(self, documents: List[Document]) -> List[Dict[str, Any]]:
        """
        Splits documents into coherent candidate passages preserving page boundaries.
        Uses blocks when available, otherwise paragraphs/sentences.
        """
        chunks = []
        for doc in documents:
            if not doc.pages:
                continue

            for page in doc.pages:
                if page.blocks and len(page.blocks) > 0:
                    for b in page.blocks:
                        text = b.get("text", "").strip()
                        if len(text) < 15:
                            continue
                        meta = self._extract_metadata_from_text(text)
                        chunks.append({
                            "chunk_id": f"{doc.id}_p{page.page_number}_b{b.get('block_no', 0)}_{len(chunks)}",
                            "document_id": doc.id,
                            "document_name": doc.filename,
                            "page": page.page_number,
                            "text": text,
                            "location": {"bbox": b.get("bbox"), "block_no": b.get("block_no")},
                            "metadata": meta
                        })
                else:
                    # Fallback: split page text by double newlines or sentences
                    paragraphs = [p.strip() for p in page.text.split("\n\n") if len(p.strip()) > 15]
                    if not paragraphs and page.text.strip():
                        paragraphs = [page.text.strip()]

                    for idx, para in enumerate(paragraphs):
                        meta = self._extract_metadata_from_text(para)
                        chunks.append({
                            "chunk_id": f"{doc.id}_p{page.page_number}_para{idx}",
                            "document_id": doc.id,
                            "document_name": doc.filename,
                            "page": page.page_number,
                            "text": para,
                            "location": None,
                            "metadata": meta
                        })
        return chunks

    def retrieve(
        self,
        question: str,
        documents: List[Document],
        facts: List[Fact],
        top_k: int = 8
    ) -> Tuple[List[Dict[str, Any]], List[Fact], bool, float]:
        """
        Retrieves top relevant passages and relevant facts for a question.
        Returns: (top_passages, matching_facts, has_sufficient_evidence, max_score)
        """
        chunks = self.chunk_documents(documents)
        if not chunks:
            return [], [], False, 0.0

        corpus_texts = [c["text"] for c in chunks]

        # TF-IDF Retrieval
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        try:
            tfidf_matrix = vectorizer.fit_transform(corpus_texts)
            q_vector = vectorizer.transform([question])
            sim_scores = cosine_similarity(q_vector, tfidf_matrix).flatten()
        except Exception:
            sim_scores = [0.0] * len(chunks)

        # Meaningful keyword booster (excluding stop words)
        STOP_WORDS = {
            "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
            "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
            "can", "could", "did", "do", "does", "doing", "down", "during", "each", "few", "for", "from",
            "further", "had", "has", "have", "having", "he", "her", "here", "hers", "him", "his", "how",
            "i", "if", "in", "into", "is", "it", "its", "me", "more", "most", "my", "no", "nor", "not",
            "of", "off", "on", "once", "only", "or", "other", "ought", "our", "out", "over", "own", "same",
            "she", "should", "so", "some", "such", "than", "that", "the", "their", "theirs", "them", "then",
            "there", "these", "they", "this", "those", "through", "to", "too", "under", "until", "up",
            "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why",
            "with", "would", "you", "your", "yours"
        }
        q_tokens = set(w for w in re.findall(r"\w+", question.lower()) if len(w) > 2 and w not in STOP_WORDS)
        scored_chunks = []
        for idx, chunk in enumerate(chunks):
            base_score = float(sim_scores[idx]) if idx < len(sim_scores) else 0.0
            chunk_tokens = set(w for w in re.findall(r"\w+", chunk["text"].lower()) if len(w) > 2 and w not in STOP_WORDS)
            overlap = len(q_tokens.intersection(chunk_tokens))
            bonus = min(0.4, overlap * 0.12) if overlap > 0 else 0.0
            final_score = base_score + bonus
            scored_chunks.append((final_score, chunk, overlap, base_score))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        max_score = scored_chunks[0][0] if scored_chunks else 0.0

        # Filter by threshold
        selected_passages = []
        for score, chunk, overlap, base_score in scored_chunks[:top_k]:
            if score >= self.relevance_threshold and (base_score > 0.04 or overlap >= 1):
                chunk_copy = dict(chunk)
                chunk_copy["relevance_score"] = round(score, 4)
                selected_passages.append(chunk_copy)

        # Retrieve relevant extracted facts
        matching_facts = []
        for fact in facts:
            fact_text = f"{fact.subject} {fact.predicate} {fact.value.raw} {fact.context.time or ''} {fact.context.geography or ''}".lower()
            fact_tokens = set(w for w in re.findall(r"\w+", fact_text) if len(w) > 2 and w not in STOP_WORDS)
            if len(q_tokens.intersection(fact_tokens)) >= 1:
                matching_facts.append(fact)

        has_sufficient_evidence = len(selected_passages) > 0 and max_score >= self.relevance_threshold

        return selected_passages, matching_facts, has_sufficient_evidence, max_score
