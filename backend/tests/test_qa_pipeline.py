import pytest
from app.models.schemas import Document, PageData, Fact, FactValue, FactValueType, FactContext, Evidence, Relationship, RelationshipType
from app.models.qa_schemas import QAVerdict, ClaimType, CriticIssueType
from app.services.qa.retriever import Retriever
from app.services.qa.synthesizer import Synthesizer
from app.services.qa.critic import Critic
from app.services.qa.precedence import ConflictPrecedenceResolver
from app.services.qa.orchestrator import QAOrchestrator

@pytest.fixture
def sample_documents():
    doc_a = Document(
        id="doc_test_1",
        filename="Report_2024.pdf",
        upload_time="2026-10-23",
        page_count=2,
        file_path="dummy_path_1.pdf",
        processing_status="completed",
        pages=[
            PageData(
                page_number=1,
                text="The company generated revenue of $1.2 billion in FY2024. Published: March 2025. Effective Date: January 1, 2025.",
                blocks=[{
                    "bbox": [50.0, 100.0, 400.0, 150.0],
                    "text": "The company generated revenue of $1.2 billion in FY2024. Published: March 2025. Effective Date: January 1, 2025.",
                    "block_no": 1
                }]
            )
        ]
    )

    doc_b = Document(
        id="doc_test_2",
        filename="Report_2023.pdf",
        upload_time="2026-10-23",
        page_count=1,
        file_path="dummy_path_2.pdf",
        processing_status="completed",
        pages=[
            PageData(
                page_number=1,
                text="The company reported revenue of $800 million for FY2023. Published: March 2024.",
                blocks=[{
                    "bbox": [50.0, 100.0, 400.0, 150.0],
                    "text": "The company reported revenue of $800 million for FY2023. Published: March 2024.",
                    "block_no": 1
                }]
            )
        ]
    )

    return [doc_a, doc_b]

@pytest.fixture
def sample_facts():
    f1 = Fact(
        id="fact_1",
        subject="Company",
        predicate="revenue",
        value=FactValue(type=FactValueType.NUMBER, raw="$1.2 billion", amount=1200000000.0, currency="USD"),
        context=FactContext(time="FY2024"),
        evidence=Evidence(
            id="ev_1",
            document_id="doc_test_1",
            document_name="Report_2024.pdf",
            page=1,
            text="The company generated revenue of $1.2 billion in FY2024."
        )
    )
    return [f1]

def test_retriever_relevant_query(sample_documents, sample_facts):
    retriever = Retriever()
    passages, facts, has_evidence, score = retriever.retrieve(
        question="What was the revenue in FY2024?",
        documents=sample_documents,
        facts=sample_facts
    )
    assert has_evidence is True
    assert len(passages) > 0
    assert "1.2 billion" in passages[0]["text"]
    assert passages[0]["metadata"]["effective_date"] is not None

def test_retriever_insufficient_evidence(sample_documents, sample_facts):
    retriever = Retriever()
    passages, facts, has_evidence, score = retriever.retrieve(
        question="What is the diameter of Mars in nautical miles?",
        documents=sample_documents,
        facts=sample_facts
    )
    assert has_evidence is False

def test_synthesizer_claim_decomposition(sample_documents, sample_facts):
    retriever = Retriever()
    passages, facts, _, _ = retriever.retrieve("revenue FY2024", sample_documents, sample_facts)
    synth = Synthesizer()
    res = synth.synthesize("What was the revenue in FY2024?", passages, facts)

    assert res["verdict"] == QAVerdict.VERIFIED
    assert len(res["claims"]) > 0
    assert res["claims"][0].claim_type == ClaimType.DIRECTLY_SUPPORTED
    assert len(res["citations"]) > 0

def test_critic_adversary_detects_contradiction():
    critic = Critic()
    fact_a = Fact(
        id="f_a",
        subject="Acme Corp",
        predicate="founded",
        value=FactValue(type=FactValueType.DATE, raw="2012"),
        context=FactContext(),
        evidence=Evidence(id="e_a", document_id="doc_a", document_name="Doc_A.pdf", page=1, text="Acme was founded in 2012.")
    )
    fact_b = Fact(
        id="f_b",
        subject="Acme Corp",
        predicate="founded",
        value=FactValue(type=FactValueType.DATE, raw="2015"),
        context=FactContext(),
        evidence=Evidence(id="e_b", document_id="doc_b", document_name="Doc_B.pdf", page=1, text="Acme was established in 2015.")
    )
    contra_rel = Relationship(
        id="rel_1",
        fact_a_id="f_a",
        fact_b_id="f_b",
        fact_a=fact_a,
        fact_b=fact_b,
        type=RelationshipType.CONTRADICTS,
        reason="Conflicting founding years."
    )

    from app.models.qa_schemas import CitationItem, ClaimItem
    cit_a = CitationItem(citation_id="c1", document_id="doc_a", document_name="Doc_A.pdf", page=1, quote_text="Acme was founded in 2012.")
    claim = ClaimItem(claim_id="cl_1", text="Acme Corp was founded in 2012.", claim_type=ClaimType.DIRECTLY_SUPPORTED, citation_ids=["c1"])

    report = critic.evaluate(
        draft_answer="Acme Corp was founded in 2012.",
        claims=[claim],
        citations=[cit_a],
        facts=[fact_a, fact_b],
        relationships=[contra_rel]
    )

    assert report.passed is False
    contradiction_issues = [i for i in report.issues if i.issue_type == CriticIssueType.CONTRADICTION]
    assert len(contradiction_issues) > 0

def test_source_precedence_explicit_amendment():
    resolver = ConflictPrecedenceResolver()
    fact_old = Fact(
        id="f_old",
        subject="Policy",
        predicate="travel_limit",
        value=FactValue(type=FactValueType.STRING, raw="$50/day"),
        context=FactContext(),
        evidence=Evidence(id="e_old", document_id="doc_old", document_name="Policy_2022.pdf", page=1, text="Travel limit is $50/day.")
    )
    fact_new = Fact(
        id="f_new",
        subject="Policy",
        predicate="travel_limit",
        value=FactValue(type=FactValueType.STRING, raw="$100/day"),
        context=FactContext(),
        evidence=Evidence(id="e_new", document_id="doc_new", document_name="Policy_2024.pdf", page=1, text="This policy amends and supersedes Policy 2022. Travel limit is $100/day.")
    )
    contra_rel = Relationship(
        id="rel_2",
        fact_a_id="f_old",
        fact_b_id="f_new",
        fact_a=fact_old,
        fact_b=fact_new,
        type=RelationshipType.CONTRADICTS,
        reason="Conflicting travel limits."
    )

    from app.models.qa_schemas import CitationItem
    cit_old = CitationItem(citation_id="co", document_id="doc_old", document_name="Policy_2022.pdf", page=1, quote_text="Travel limit is $50/day.", publication_date="2022")
    cit_new = CitationItem(citation_id="cn", document_id="doc_new", document_name="Policy_2024.pdf", page=1, quote_text="This policy amends and supersedes Policy 2022. Travel limit is $100/day.", publication_date="2024")

    res = resolver.evaluate_conflicts(
        relationships=[contra_rel],
        citations=[cit_old, cit_new],
        facts=[fact_old, fact_new]
    )

    assert res is not None
    assert res.is_superseded is True
    assert res.preferred_position.claimed_value == "$100/day"

def test_qa_orchestrator_end_to_end(sample_documents, sample_facts):
    orchestrator = QAOrchestrator()
    response = orchestrator.process_question(
        question="What was the revenue in FY2024?",
        documents=sample_documents,
        facts=sample_facts,
        relationships=[]
    )

    assert response.verdict == QAVerdict.VERIFIED
    assert len(response.claims) > 0
    assert len(response.citations) > 0
    assert len(response.critic_history) >= 1
