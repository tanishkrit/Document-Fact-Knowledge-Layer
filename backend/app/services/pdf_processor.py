import fitz  # PyMuPDF
import uuid
import os
import hashlib
from typing import Optional, List, Dict, Any, Tuple
from app.models.schemas import Document, PageData, EvidenceLocation

class PDFProcessor:
    @staticmethod
    def process_pdf(file_path: str, document_id: Optional[str] = None, original_filename: Optional[str] = None) -> Tuple[Document, List[PageData]]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        doc_id = document_id or f"doc_{uuid.uuid4().hex[:8]}"
        filename = original_filename or os.path.basename(file_path)

        doc = fitz.open(file_path)
        page_count = len(doc)
        pages: List[PageData] = []

        for page_idx in range(page_count):
            page = doc[page_idx]
            page_num = page_idx + 1
            raw_text = page.get_text("text")

            # Extract blocks with coordinates
            # block format: (x0, y0, x1, y1, "text", block_no, block_type)
            blocks_raw = page.get_text("blocks")
            blocks_structured = []
            for b in blocks_raw:
                if len(b) >= 5 and b[4].strip():
                    blocks_structured.append({
                        "bbox": [round(b[0], 2), round(b[1], 2), round(b[2], 2), round(b[3], 2)],
                        "text": b[4].strip(),
                        "block_no": b[5] if len(b) > 5 else 0
                    })

            pages.append(PageData(
                page_number=page_num,
                text=raw_text.strip(),
                blocks=blocks_structured
            ))

        doc.close()

        # Compute SHA-256 file hash for stable deduplication
        file_hash = None
        if os.path.exists(file_path):
            hasher = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    hasher.update(chunk)
            file_hash = hasher.hexdigest()

        document = Document(
            id=doc_id,
            filename=filename,
            upload_time=fitz.get_pdf_now(),
            page_count=page_count,
            file_path=file_path,
            file_hash=file_hash,
            processing_status="ingested",
            pages=pages
        )

        return document, pages

    @staticmethod
    def find_evidence_location(pages: List[PageData], target_text: str, preferred_page: Optional[int] = None) -> Tuple[int, EvidenceLocation]:
        """Locates exact page and bounding box for an evidence quote."""
        target_lower = target_text.lower().strip()
        
        # If preferred page given, search it first
        candidate_pages = pages
        if preferred_page and 1 <= preferred_page <= len(pages):
            candidate_pages = [pages[preferred_page - 1]] + [p for p in pages if p.page_number != preferred_page]

        for p in candidate_pages:
            p_text_lower = p.text.lower()
            if target_lower in p_text_lower or any(word in p_text_lower for word in target_lower.split()[:4]):
                # Find matching block
                if p.blocks:
                    for b in p.blocks:
                        b_text_lower = b["text"].lower()
                        if target_lower[:30] in b_text_lower or any(word in b_text_lower for word in target_lower.split()[:3]):
                            return p.page_number, EvidenceLocation(
                                bbox=b["bbox"],
                                block_no=b.get("block_no", 0),
                                char_start=p_text_lower.find(target_lower) if target_lower in p_text_lower else None,
                                char_end=p_text_lower.find(target_lower) + len(target_text) if target_lower in p_text_lower else None
                            )
                return p.page_number, EvidenceLocation(
                    char_start=p_text_lower.find(target_lower) if target_lower in p_text_lower else None
                )

        # Fallback to page 1
        return 1, EvidenceLocation()
