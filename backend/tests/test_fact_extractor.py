import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.fact_extractor import FactExtractor
from app.models.schemas import PageData

class TestFactExtractorValidation(unittest.TestCase):
    def setUp(self):
        # Force NLP fallback mode by passing api_key=None
        self.extractor = FactExtractor(api_key=None)

    def test_cin_not_headquarters_or_founded(self):
        text = "DELHIVERY LIMITED CORPORATE IDENTITY NUMBER: U63090DL2011PLC221234 REGISTERED OFFICE: Gurgaon"
        pages = [PageData(page_number=1, text=text)]
        facts = self.extractor.extract_facts("doc1", "Delhivery_Prospectus.pdf", pages)
        
        # Verify 63090 is NOT extracted as headquarters or founded
        for f in facts:
            if f.predicate in ["headquarters", "founded"]:
                self.assertNotEqual(str(f.value.raw).strip(), "63090")
                self.assertNotIn("63090", str(f.value.amount or ""))

    def test_date_fragment_not_founded(self):
        text = "3. As of December 31, 2021. 4. Since inception."
        pages = [PageData(page_number=1, text=text)]
        facts = self.extractor.extract_facts("doc1", "Report.pdf", pages)
        
        # Verify "31," is NOT extracted as founded year
        for f in facts:
            if f.predicate == "founded":
                self.assertNotEqual(str(f.value.raw).strip(), "31")
                self.assertNotEqual(str(f.value.raw).strip(), "31,")
                self.assertNotEqual(f.value.amount, 31.0)

    def test_pin_code_not_business_metric(self):
        text = "Registered office located at Plot 5, Sector 44, PIN code 122002."
        pages = [PageData(page_number=1, text=text)]
        facts = self.extractor.extract_facts("doc1", "Report.pdf", pages)
        
        for f in facts:
            if f.predicate in ["revenue", "ebitda", "employees", "workforce", "active customers"]:
                self.assertNotEqual(f.value.amount, 122002.0)

    def test_valid_headquarters_extracted(self):
        text = "The corporate headquarters of Delhivery is located in Gurgaon, Haryana."
        pages = [PageData(page_number=1, text=text)]
        facts = self.extractor.extract_facts("doc1", "Report.pdf", pages)
        
        hq_facts = [f for f in facts if f.predicate == "headquarters"]
        self.assertTrue(len(hq_facts) > 0, "Valid headquarters claim should be extracted")
        self.assertIn("gurgaon", str(hq_facts[0].value.raw).lower())

    def test_valid_founding_year_extracted(self):
        text = "The company was incorporated in 2011 and has grown rapidly since."
        pages = [PageData(page_number=1, text=text)]
        facts = self.extractor.extract_facts("doc1", "Report.pdf", pages)
        
        founded_facts = [f for f in facts if f.predicate == "founded"]
        self.assertTrue(len(founded_facts) > 0, "Valid founding-year claim should be extracted")
        self.assertEqual(founded_facts[0].value.amount, 2011.0)

    def test_loss_number_not_revenue(self):
        text = "the loss for FY24 stood at ₹ 2,491.86 million as against ₹10,077.79 million for FY23, a reduction of loss by 75.27%."
        pages = [PageData(page_number=1, text=text)]
        facts = self.extractor.extract_facts("doc1", "Report.pdf", pages)
        
        # Verify loss amounts are not extracted as revenue
        rev_facts = [f for f in facts if f.predicate == "revenue"]
        self.assertEqual(len(rev_facts), 0, "Loss statement must not be extracted as revenue")

    def test_bps_margin_change_not_net_profit(self):
        text = "net profit margin increased by 1,048 bps in FY24 primarily on account of improvement in operating margins."
        pages = [PageData(page_number=1, text=text)]
        facts = self.extractor.extract_facts("doc1", "Report.pdf", pages)
        
        # Verify 1,048 bps is not extracted as net profit / loss
        pat_facts = [f for f in facts if f.predicate in ["net profit / loss", "profit", "pat"]]
        self.assertEqual(len(pat_facts), 0, "Bps margin change must not be extracted as net profit/loss")

    def test_flattened_table_fragment_rejected(self):
        text = "38,382.91 29,886.29 16,948.74 Restated loss for the period/year"
        pages = [PageData(page_number=1, text=text)]
        facts = self.extractor.extract_facts("doc1", "Report.pdf", pages)
        
        # Multiple adjacent unassociated column numbers should be rejected
        self.assertEqual(len(facts), 0, "Flattened table fragment without column association must be rejected")

    def test_valid_revenue_extracted(self):
        text = "AlphaCorp recorded revenue of $1.2 billion in FY2024, demonstrating solid growth."
        pages = [PageData(page_number=1, text=text)]
        facts = self.extractor.extract_facts("doc1", "Report.pdf", pages)
        
        rev_facts = [f for f in facts if f.predicate == "revenue"]
        self.assertTrue(len(rev_facts) > 0, "Valid revenue claim should be extracted")
        self.assertEqual(rev_facts[0].value.amount, 1_200_000_000.0)

    def test_valid_net_profit_extracted(self):
        text = "In FY24, the company achieved first PAT profitability of ₹117 million."
        pages = [PageData(page_number=1, text=text)]
        facts = self.extractor.extract_facts("doc1", "Report.pdf", pages)
        
        pat_facts = [f for f in facts if f.predicate in ["net profit / loss", "profit", "pat"]]
        self.assertTrue(len(pat_facts) > 0, "Valid PAT claim should be extracted")
        self.assertEqual(pat_facts[0].value.amount, 117_000_000.0)

if __name__ == "__main__":
    unittest.main()

