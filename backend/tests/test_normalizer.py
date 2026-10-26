import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.normalizer import (
    normalize_number_value,
    normalize_time_context,
    normalize_geography,
    normalize_scope,
    extract_qualification
)
from app.models.schemas import FactValueType

class TestNormalizer(unittest.TestCase):
    def test_number_normalization_scales(self):
        val1 = normalize_number_value("$1.2 billion")
        self.assertEqual(val1.type, FactValueType.NUMBER)
        self.assertEqual(val1.amount, 1_200_000_000.0)
        self.assertEqual(val1.currency, "USD")

        val2 = normalize_number_value("$1,200 million")
        self.assertEqual(val2.type, FactValueType.NUMBER)
        self.assertEqual(val2.amount, 1_200_000_000.0)
        self.assertEqual(val2.currency, "USD")

        self.assertEqual(val1.amount, val2.amount)

    def test_employee_normalization(self):
        v1 = normalize_number_value("5,000 employees")
        self.assertEqual(v1.amount, 5000.0)
        self.assertEqual(v1.unit, "employees")

        v2 = normalize_number_value("5k employees")
        self.assertEqual(v2.amount, 5000.0)
        self.assertEqual(v2.unit, "employees")

    def test_percentage_normalization(self):
        v = normalize_number_value("12%")
        self.assertEqual(v.amount, 12.0)
        self.assertEqual(v.unit, "%")

    def test_time_normalization(self):
        self.assertEqual(normalize_time_context("FY2024"), "2024-FY")
        self.assertEqual(normalize_time_context("Fiscal Year 2024"), "2024-FY")
        self.assertEqual(normalize_time_context("Q1 2025"), "2025-Q1")
        self.assertEqual(normalize_time_context("2012"), "2012")

    def test_scope_normalization(self):
        self.assertEqual(normalize_scope("worldwide"), "All / Global")
        self.assertEqual(normalize_scope("all employees"), "All / Global")
        self.assertEqual(normalize_scope("in India"), "in India")

    def test_qualification_extraction(self):
        q, cleaned = extract_qualification("approximately 5,000")
        self.assertEqual(q, "approximately")
        self.assertTrue("5,000" in cleaned)

if __name__ == "__main__":
    unittest.main()
