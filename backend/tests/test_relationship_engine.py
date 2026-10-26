import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.relationship_engine import RelationshipEngine
from app.models.schemas import Fact, FactValue, FactValueType, FactContext, Evidence, RelationshipType

class TestRelationshipEngine(unittest.TestCase):
    def setUp(self):
        self.engine = RelationshipEngine()

    def test_corroboration_case(self):
        # Doc A: Revenue $1.2B in FY2024
        fact_a = Fact(
            id="f1",
            subject="AlphaCorp",
            predicate="revenue",
            value=FactValue(type=FactValueType.NUMBER, raw="$1.2 billion", amount=1_200_000_000.0, unit="USD", currency="USD"),
            context=FactContext(time="FY2024", time_normalized="2024-FY"),
            evidence=Evidence(id="e1", document_id="doc_a", document_name="Report_A.pdf", page=12, text="AlphaCorp revenue was $1.2 billion in FY2024.")
        )

        # Doc B: Revenue $1,200M in FY2024
        fact_b = Fact(
            id="f2",
            subject="AlphaCorp",
            predicate="revenue",
            value=FactValue(type=FactValueType.NUMBER, raw="$1,200 million", amount=1_200_000_000.0, unit="USD", currency="USD"),
            context=FactContext(time="FY2024", time_normalized="2024-FY"),
            evidence=Evidence(id="e2", document_id="doc_b", document_name="Report_B.pdf", page=8, text="AlphaCorp recorded revenue of $1,200 million in FY2024.")
        )

        rel = self.engine.evaluate_relationship(fact_a, fact_b)
        self.assertEqual(rel.type, RelationshipType.CORROBORATES)
        self.assertTrue("corroborates" in rel.reason.lower() or "compatible" in rel.reason.lower())

    def test_genuine_contradiction_case(self):
        # Doc A: Founded in 2012
        fact_a = Fact(
            id="f1",
            subject="TechVanguard",
            predicate="founded",
            value=FactValue(type=FactValueType.DATE, raw="2012", amount=2012.0, unit="year"),
            context=FactContext(),
            evidence=Evidence(id="e1", document_id="doc_a", document_name="Profile_A.pdf", page=3, text="TechVanguard was founded in 2012.")
        )

        # Doc B: Founded in 2015
        fact_b = Fact(
            id="f2",
            subject="TechVanguard",
            predicate="founded",
            value=FactValue(type=FactValueType.DATE, raw="2015", amount=2015.0, unit="year"),
            context=FactContext(),
            evidence=Evidence(id="e2", document_id="doc_b", document_name="Profile_B.pdf", page=7, text="TechVanguard was founded in 2015.")
        )

        rel = self.engine.evaluate_relationship(fact_a, fact_b)
        self.assertEqual(rel.type, RelationshipType.CONTRADICTS)
        self.assertTrue("contradiction" in rel.reason.lower())

    def test_apparent_contradiction_scope_context(self):
        # Doc A: 5,000 employees worldwide
        fact_a = Fact(
            id="f1",
            subject="GlobalDynamics",
            predicate="employees",
            value=FactValue(type=FactValueType.NUMBER, raw="5,000 employees", amount=5000.0, unit="employees"),
            context=FactContext(scope="All / Global", geography="Global"),
            evidence=Evidence(id="e1", document_id="doc_a", document_name="Doc_A.pdf", page=1, text="GlobalDynamics has 5,000 employees worldwide.")
        )

        # Doc B: 3,800 employees in India
        fact_b = Fact(
            id="f2",
            subject="GlobalDynamics",
            predicate="employees",
            value=FactValue(type=FactValueType.NUMBER, raw="3,800 employees", amount=3800.0, unit="employees"),
            context=FactContext(scope="in India", geography="India"),
            evidence=Evidence(id="e2", document_id="doc_b", document_name="Doc_B.pdf", page=2, text="GlobalDynamics has 3,800 employees in India.")
        )

        rel = self.engine.evaluate_relationship(fact_a, fact_b)
        self.assertEqual(rel.type, RelationshipType.CONTEXTUALIZES)
        self.assertTrue("context" in rel.reason.lower())

    def test_apparent_contradiction_time_context(self):
        # FY23 $800M vs FY24 $1.1B
        fact_a = Fact(
            id="f1",
            subject="Company",
            predicate="revenue",
            value=FactValue(type=FactValueType.NUMBER, raw="$800 million", amount=800_000_000.0, unit="USD"),
            context=FactContext(time="FY2023", time_normalized="2023-FY"),
            evidence=Evidence(id="e1", document_id="doc_a", document_name="Doc_A.pdf", page=1, text="FY2023 Revenue was $800M.")
        )

        fact_b = Fact(
            id="f2",
            subject="Company",
            predicate="revenue",
            value=FactValue(type=FactValueType.NUMBER, raw="$1.1 billion", amount=1_100_000_000.0, unit="USD"),
            context=FactContext(time="FY2024", time_normalized="2024-FY"),
            evidence=Evidence(id="e2", document_id="doc_b", document_name="Doc_B.pdf", page=1, text="FY2024 Revenue reached $1.1B.")
        )

        rel = self.engine.evaluate_relationship(fact_a, fact_b)
        self.assertEqual(rel.type, RelationshipType.CONTEXTUALIZES)

    def test_uncertain_relationship_missing_context(self):
        # Doc A: Market share 35% without year/region
        fact_a = Fact(
            id="f1",
            subject="ApexAI",
            predicate="market share",
            value=FactValue(type=FactValueType.NUMBER, raw="35%", amount=35.0, unit="%"),
            context=FactContext(), # No time or scope
            evidence=Evidence(id="e1", document_id="doc_a", document_name="Brief_A.pdf", page=1, text="ApexAI market share is 35%.")
        )

        # Doc B: Market share 18% without year/region
        fact_b = Fact(
            id="f2",
            subject="ApexAI",
            predicate="market share",
            value=FactValue(type=FactValueType.NUMBER, raw="18%", amount=18.0, unit="%"),
            context=FactContext(), # No time or scope
            evidence=Evidence(id="e2", document_id="doc_b", document_name="Brief_B.pdf", page=1, text="ApexAI market share stands at 18%.")
        )

        rel = self.engine.evaluate_relationship(fact_a, fact_b)
        self.assertEqual(rel.type, RelationshipType.UNCERTAIN)
        self.assertTrue("uncertain" in rel.reason.lower())

if __name__ == "__main__":
    unittest.main()
