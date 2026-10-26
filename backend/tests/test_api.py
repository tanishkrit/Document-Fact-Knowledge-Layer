import unittest
import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app
from app.models.schemas import RelationshipType

client = TestClient(app)

class TestAPIEndpoints(unittest.TestCase):
    def test_root_endpoint(self):
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["service"], "Fact Knowledge Layer")

    def test_get_demo_cases(self):
        response = client.get("/api/demo/cases")
        self.assertEqual(response.status_code, 200)
        cases = response.json()
        self.assertEqual(len(cases), 4)
        case_ids = [c["id"] for c in cases]
        self.assertIn("case_1", case_ids)
        self.assertIn("case_2", case_ids)
        self.assertIn("case_3", case_ids)
        self.assertIn("case_4", case_ids)

    def test_load_demo_case_1_corroboration(self):
        client.post("/api/clear")

        res = client.post("/api/demo/load/case_1")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(data["facts_extracted"], 2)

        rel_res = client.get("/api/relationships")
        self.assertEqual(rel_res.status_code, 200)
        rels = rel_res.json()
        self.assertGreaterEqual(len(rels), 1)
        corrob_rels = [r for r in rels if r["type"] == RelationshipType.CORROBORATES]
        self.assertGreaterEqual(len(corrob_rels), 1)
        self.assertTrue("corroborates" in corrob_rels[0]["reason"].lower() or "compatible" in corrob_rels[0]["reason"].lower())

    def test_load_demo_case_2_contradiction(self):
        client.post("/api/clear")
        res = client.post("/api/demo/load/case_2")
        self.assertEqual(res.status_code, 200)

        rel_res = client.get("/api/relationships")
        rels = rel_res.json()
        contradict_rels = [r for r in rels if r["type"] == RelationshipType.CONTRADICTS]
        self.assertGreaterEqual(len(contradict_rels), 1)
        self.assertTrue("contradiction" in contradict_rels[0]["reason"].lower())

    def test_load_demo_case_3_contextualization(self):
        client.post("/api/clear")
        res = client.post("/api/demo/load/case_3")
        self.assertEqual(res.status_code, 200)

        rel_res = client.get("/api/relationships")
        rels = rel_res.json()
        context_rels = [r for r in rels if r["type"] == RelationshipType.CONTEXTUALIZES]
        self.assertGreaterEqual(len(context_rels), 1)
        self.assertTrue("context" in context_rels[0]["reason"].lower())

    def test_load_demo_case_4_uncertainty(self):
        client.post("/api/clear")
        res = client.post("/api/demo/load/case_4")
        self.assertEqual(res.status_code, 200)

        rel_res = client.get("/api/relationships")
        rels = rel_res.json()
        uncertain_rels = [r for r in rels if r["type"] == RelationshipType.UNCERTAIN]
        self.assertGreaterEqual(len(uncertain_rels), 1)
        self.assertTrue("uncertain" in uncertain_rels[0]["reason"].lower())

    def test_delete_document(self):
        client.post("/api/clear")
        load_res = client.post("/api/demo/load/case_1")
        self.assertEqual(load_res.status_code, 200)
        
        docs_res = client.get("/api/documents")
        docs = docs_res.json()
        self.assertEqual(len(docs), 2)
        doc_to_delete = docs[0]["id"]
        
        del_res = client.delete(f"/api/documents/{doc_to_delete}")
        self.assertEqual(del_res.status_code, 200)
        
        get_res = client.get(f"/api/documents/{doc_to_delete}")
        self.assertEqual(get_res.status_code, 404)

        docs_after = client.get("/api/documents").json()
        self.assertEqual(len(docs_after), 1)

        del_404 = client.delete("/api/documents/non_existent_doc")
        self.assertEqual(del_404.status_code, 404)

    def test_analyze_selected_documents(self):
        client.post("/api/clear")
        load_res = client.post("/api/demo/load/case_1")
        self.assertEqual(load_res.status_code, 200)
        
        docs = client.get("/api/documents").json()
        doc_ids = [d["id"] for d in docs]
        self.assertEqual(len(doc_ids), 2)

        analyze_res = client.post("/api/documents/analyze-selected", json={"document_ids": doc_ids})
        self.assertEqual(analyze_res.status_code, 200)
        data = analyze_res.json()
        self.assertGreaterEqual(data["relationships_count"], 1)

        filtered_rels = client.get(f"/api/relationships?document_ids={doc_ids[0]}&document_ids={doc_ids[1]}").json()
        self.assertGreaterEqual(len(filtered_rels), 1)

        bad_req = client.post("/api/documents/analyze-selected", json={"document_ids": [doc_ids[0]]})
        self.assertEqual(bad_req.status_code, 400)

        fake_six = [f"fake_{i}" for i in range(6)]
        too_many = client.post("/api/documents/analyze-selected", json={"document_ids": fake_six})
        self.assertEqual(too_many.status_code, 400)
        self.assertIn("maximum of 5 documents", too_many.json()["detail"])

        matrix_res = client.post("/api/consensus/matrix", json={"document_ids": doc_ids})
        self.assertEqual(matrix_res.status_code, 200)
        matrix_data = matrix_res.json()
        self.assertIn("consensus_points", matrix_data)
        self.assertIn("total_points", matrix_data)
        self.assertGreaterEqual(matrix_data["total_points"], 1)

        too_many_matrix = client.post("/api/consensus/matrix", json={"document_ids": fake_six})
        self.assertEqual(too_many_matrix.status_code, 400)

if __name__ == "__main__":
    unittest.main()
