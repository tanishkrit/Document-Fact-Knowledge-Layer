import sqlite3
import json
import os
from typing import List, Optional, Dict, Any
from app.models.schemas import Document, Fact, Relationship, RelationshipType, PageData, Evidence, FactValue, FactContext

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "knowledge.db")

class Storage:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                upload_time TEXT NOT NULL,
                page_count INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                file_hash TEXT,
                processing_status TEXT DEFAULT 'pending',
                extracted_facts_count INTEGER DEFAULT 0,
                pages_json TEXT
            );
            """)

            # Ensure file_hash column exists for existing DBs
            cursor.execute("PRAGMA table_info(documents);")
            columns = [r["name"] for r in cursor.fetchall()]
            if "file_hash" not in columns:
                cursor.execute("ALTER TABLE documents ADD COLUMN file_hash TEXT;")

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                value_json TEXT NOT NULL,
                context_json TEXT NOT NULL,
                qualification TEXT,
                confidence REAL,
                evidence_json TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id TEXT PRIMARY KEY,
                fact_a_id TEXT NOT NULL,
                fact_b_id TEXT NOT NULL,
                type TEXT NOT NULL,
                confidence REAL,
                reason TEXT NOT NULL,
                context_diff_json TEXT,
                value_diff_json TEXT,
                FOREIGN KEY (fact_a_id) REFERENCES facts (id) ON DELETE CASCADE,
                FOREIGN KEY (fact_b_id) REFERENCES facts (id) ON DELETE CASCADE
            );
            """)
            conn.commit()

        self._deduplicate_database()

    def _deduplicate_database(self):
        """Populates missing file_hash values and cleans up any existing duplicate documents."""
        import hashlib
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, filename, file_path, file_hash FROM documents")
            rows = cursor.fetchall()
            
            # Step 1: Fill missing file hashes
            for r in rows:
                doc_id, filename, file_path, current_hash = r["id"], r["filename"], r["file_path"], r["file_hash"]
                if not current_hash and os.path.exists(file_path):
                    try:
                        hasher = hashlib.sha256()
                        with open(file_path, "rb") as f:
                            for chunk in iter(lambda: f.read(65536), b""):
                                hasher.update(chunk)
                        computed_hash = hasher.hexdigest()
                        cursor.execute("UPDATE documents SET file_hash = ? WHERE id = ?", (computed_hash, doc_id))
                    except Exception as e:
                        print(f"[Storage] Hash computation failed for {file_path}: {e}")

            conn.commit()

            # Step 2: Identify duplicate documents by file_hash or identical filename + hash
            cursor.execute("SELECT id, filename, file_path, file_hash, upload_time FROM documents ORDER BY upload_time ASC")
            all_docs = cursor.fetchall()
            
            seen_hashes = {} # file_hash -> canonical doc_id
            seen_filenames = {} # (filename, file_hash) -> canonical doc_id
            docs_to_remove = []

            for doc in all_docs:
                d_id = doc["id"]
                fname = doc["filename"]
                fhash = doc["file_hash"]

                key = fhash if fhash else (fname, doc["file_path"])
                if key in seen_hashes:
                    canonical_id = seen_hashes[key]
                    docs_to_remove.append((d_id, canonical_id))
                else:
                    seen_hashes[key] = d_id

            # Merge/remove duplicates
            for dup_id, canonical_id in docs_to_remove:
                print(f"[Storage] Deduplicating duplicate document {dup_id} -> canonical {canonical_id}")
                # Reassign facts pointing to dup_id to canonical_id if canonical has fewer facts
                cursor.execute("UPDATE OR IGNORE facts SET document_id = ? WHERE document_id = ?", (canonical_id, dup_id))
                cursor.execute("DELETE FROM facts WHERE document_id = ?", (dup_id,))
                cursor.execute("DELETE FROM documents WHERE id = ?", (dup_id,))

            conn.commit()

    def clear_all(self):
        """Clears all data for clean resets."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM relationships;")
            cursor.execute("DELETE FROM facts;")
            cursor.execute("DELETE FROM documents;")
            conn.commit()

    # --- Document operations ---
    def save_document(self, doc: Document):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if document with same file_hash already exists
            if doc.file_hash:
                cursor.execute("SELECT id FROM documents WHERE file_hash = ? AND id != ?", (doc.file_hash, doc.id))
                existing = cursor.fetchone()
                if existing:
                    # Update existing record ID to doc.id or update existing record content
                    doc_id_to_use = existing["id"]
                    pages_json = json.dumps([p.model_dump() for p in doc.pages]) if doc.pages else None
                    cursor.execute("""
                    UPDATE documents 
                    SET filename = ?, upload_time = ?, page_count = ?, file_path = ?, file_hash = ?, processing_status = ?, extracted_facts_count = ?, pages_json = ?
                    WHERE id = ?
                    """, (
                        doc.filename, doc.upload_time, doc.page_count,
                        doc.file_path, doc.file_hash, doc.processing_status, doc.extracted_facts_count, pages_json, doc_id_to_use
                    ))
                    conn.commit()
                    return

            pages_json = json.dumps([p.model_dump() for p in doc.pages]) if doc.pages else None
            cursor.execute("""
            INSERT OR REPLACE INTO documents 
            (id, filename, upload_time, page_count, file_path, file_hash, processing_status, extracted_facts_count, pages_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc.id, doc.filename, doc.upload_time, doc.page_count,
                doc.file_path, doc.file_hash, doc.processing_status, doc.extracted_facts_count, pages_json
            ))
            conn.commit()

    def update_document_status(self, doc_id: str, status: str, facts_count: int = 0):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE documents SET processing_status = ?, extracted_facts_count = ? WHERE id = ?
            """, (status, facts_count, doc_id))
            conn.commit()

    def get_document_by_hash(self, file_hash: str) -> Optional[Document]:
        if not file_hash:
            return None
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE file_hash = ? ORDER BY upload_time ASC", (file_hash,))
            r = cursor.fetchone()
            if not r:
                return None
            pages = None
            if r["pages_json"]:
                raw_pages = json.loads(r["pages_json"])
                pages = [PageData(**p) for p in raw_pages]

            return Document(
                id=r["id"],
                filename=r["filename"],
                upload_time=r["upload_time"],
                page_count=r["page_count"],
                file_path=r["file_path"],
                file_hash=r["file_hash"],
                processing_status=r["processing_status"],
                extracted_facts_count=r["extracted_facts_count"],
                pages=pages
            )

    def get_documents(self) -> List[Document]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, filename, upload_time, page_count, file_path, file_hash, processing_status, extracted_facts_count FROM documents ORDER BY upload_time DESC")
            rows = cursor.fetchall()
            
            seen_hashes = set()
            docs = []
            for r in rows:
                fhash = r["file_hash"]
                doc_id = r["id"]
                dedup_key = fhash if fhash else doc_id
                if dedup_key in seen_hashes:
                    continue
                seen_hashes.add(dedup_key)
                docs.append(Document(
                    id=r["id"],
                    filename=r["filename"],
                    upload_time=r["upload_time"],
                    page_count=r["page_count"],
                    file_path=r["file_path"],
                    file_hash=r["file_hash"],
                    processing_status=r["processing_status"],
                    extracted_facts_count=r["extracted_facts_count"]
                ))
            return docs

    def get_document(self, doc_id: str) -> Optional[Document]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
            r = cursor.fetchone()
            if not r:
                return None
            pages = None
            if r["pages_json"]:
                raw_pages = json.loads(r["pages_json"])
                pages = [PageData(**p) for p in raw_pages]

            return Document(
                id=r["id"],
                filename=r["filename"],
                upload_time=r["upload_time"],
                page_count=r["page_count"],
                file_path=r["file_path"],
                file_hash=r["file_hash"],
                processing_status=r["processing_status"],
                extracted_facts_count=r["extracted_facts_count"],
                pages=pages
            )

    def delete_document(self, doc_id: str) -> bool:
        """Deletes a document, its extracted facts, orphaned relationships, and physical file."""
        doc = self.get_document(doc_id)
        if not doc:
            return False

        # Try to delete physical file if inside uploads directory
        try:
            if os.path.exists(doc.file_path) and "uploads" in doc.file_path:
                os.remove(doc.file_path)
        except Exception as e:
            print(f"[Storage] Warning: could not delete file {doc.file_path}: {e}")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Delete facts associated with document
            cursor.execute("SELECT id FROM facts WHERE document_id = ?", (doc_id,))
            fact_ids = [r["id"] for r in cursor.fetchall()]
            
            if fact_ids:
                placeholders = ','.join(['?'] * len(fact_ids))
                cursor.execute(f"DELETE FROM relationships WHERE fact_a_id IN ({placeholders}) OR fact_b_id IN ({placeholders})", fact_ids * 2)
                cursor.execute(f"DELETE FROM facts WHERE id IN ({placeholders})", fact_ids)

            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.commit()
        return True

    # --- Fact operations ---
    def save_facts(self, facts: List[Fact]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for f in facts:
                cursor.execute("""
                INSERT OR REPLACE INTO facts
                (id, document_id, subject, predicate, value_json, context_json, qualification, confidence, evidence_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f.id,
                    f.evidence.document_id,
                    f.subject,
                    f.predicate,
                    f.value.model_dump_json(),
                    f.context.model_dump_json(),
                    f.qualification,
                    f.confidence,
                    f.evidence.model_dump_json()
                ))
            conn.commit()

    def get_facts(self, document_id: Optional[str] = None, document_ids: Optional[List[str]] = None) -> List[Fact]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if document_ids and len(document_ids) > 0:
                placeholders = ','.join(['?'] * len(document_ids))
                cursor.execute(f"SELECT * FROM facts WHERE document_id IN ({placeholders})", document_ids)
            elif document_id:
                cursor.execute("SELECT * FROM facts WHERE document_id = ?", (document_id,))
            else:
                cursor.execute("SELECT * FROM facts")
            rows = cursor.fetchall()
            facts = []
            for r in rows:
                val = FactValue(**json.loads(r["value_json"]))
                ctx = FactContext(**json.loads(r["context_json"]))
                ev = Evidence(**json.loads(r["evidence_json"]))
                facts.append(Fact(
                    id=r["id"],
                    subject=r["subject"],
                    predicate=r["predicate"],
                    value=val,
                    context=ctx,
                    qualification=r["qualification"],
                    confidence=r["confidence"],
                    evidence=ev
                ))
            return facts

    def get_fact(self, fact_id: str) -> Optional[Fact]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM facts WHERE id = ?", (fact_id,))
            r = cursor.fetchone()
            if not r:
                return None
            return Fact(
                id=r["id"],
                subject=r["subject"],
                predicate=r["predicate"],
                value=FactValue(**json.loads(r["value_json"])),
                context=FactContext(**json.loads(r["context_json"])),
                qualification=r["qualification"],
                confidence=r["confidence"],
                evidence=Evidence(**json.loads(r["evidence_json"]))
            )

    # --- Relationship operations ---
    def save_relationships(self, relationships: List[Relationship]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for rel in relationships:
                cursor.execute("""
                INSERT OR REPLACE INTO relationships
                (id, fact_a_id, fact_b_id, type, confidence, reason, context_diff_json, value_diff_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rel.id,
                    rel.fact_a_id,
                    rel.fact_b_id,
                    rel.type.value if hasattr(rel.type, 'value') else str(rel.type),
                    rel.confidence,
                    rel.reason,
                    json.dumps(rel.context_diff) if rel.context_diff else None,
                    json.dumps(rel.value_diff) if rel.value_diff else None
                ))
            conn.commit()

    def get_relationships(self, rel_type: Optional[str] = None, document_ids: Optional[List[str]] = None) -> List[Relationship]:
        all_facts_dict = {f.id: f for f in self.get_facts()}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if rel_type:
                cursor.execute("SELECT * FROM relationships WHERE type = ?", (rel_type,))
            else:
                cursor.execute("SELECT * FROM relationships")
            rows = cursor.fetchall()
            relationships = []
            doc_filter_set = set(document_ids) if document_ids and len(document_ids) > 0 else None

            for r in rows:
                f_a = all_facts_dict.get(r["fact_a_id"])
                f_b = all_facts_dict.get(r["fact_b_id"])

                # If filtering by specific document IDs, both facts must belong to the selected documents
                if doc_filter_set:
                    if not f_a or not f_b:
                        continue
                    if f_a.evidence.document_id not in doc_filter_set or f_b.evidence.document_id not in doc_filter_set:
                        continue

                relationships.append(Relationship(
                    id=r["id"],
                    fact_a_id=r["fact_a_id"],
                    fact_b_id=r["fact_b_id"],
                    fact_a=f_a,
                    fact_b=f_b,
                    type=RelationshipType(r["type"]),
                    confidence=r["confidence"],
                    reason=r["reason"],
                    context_diff=json.loads(r["context_diff_json"]) if r["context_diff_json"] else None,
                    value_diff=json.loads(r["value_diff_json"]) if r["value_diff_json"] else None
                ))
            return relationships
