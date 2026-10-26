import os
import fitz  # PyMuPDF
from typing import Dict, List, Tuple
from app.models.schemas import DemoCaseInfo, RelationshipType

DEMO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "demos")

DEMO_CASES: List[DemoCaseInfo] = [
    DemoCaseInfo(
        id="case_1",
        title="Case 1: Corroboration ($1.2B vs $1,200M)",
        case_type=RelationshipType.CORROBORATES,
        description="Two corporate reports express the exact same financial metric using different numerical notations.",
        document_a_name="AlphaCorp_Annual_Report_FY24.pdf",
        document_b_name="AlphaCorp_Investor_Presentation_2024.pdf",
        expected_outcome="CORROBORATES: $1.2 billion in Doc A and $1,200 million in Doc B normalize to the identical canonical value 1,200,000,000 USD.",
        why_it_matters="Demonstrates deterministic mathematical normalization without requiring LLM arithmetic hallucination."
    ),
    DemoCaseInfo(
        id="case_2",
        title="Case 2: Genuine Contradiction (Founded 2012 vs 2015)",
        case_type=RelationshipType.CONTRADICTS,
        description="Two profiling documents make irreconcilable claims regarding the founding year of TechVanguard.",
        document_a_name="TechVanguard_Company_Profile.pdf",
        document_b_name="TechVanguard_Industry_Overview.pdf",
        expected_outcome="CONTRADICTS: Doc A claims TechVanguard was founded in 2012, whereas Doc B claims 2015. There is no reconciling timeframe.",
        why_it_matters="Demonstrates genuine conflict identification when context and entity match but values clash."
    ),
    DemoCaseInfo(
        id="case_3",
        title="Case 3: Apparent Contradiction (Scope & Time Reconciliation)",
        case_type=RelationshipType.CONTEXTUALIZES,
        description="Two workforce statements appear to conflict on employee count (5,000 vs 3,800), but contextual scopes explain the difference.",
        document_a_name="GlobalDynamics_Global_Report.pdf",
        document_b_name="GlobalDynamics_India_Division.pdf",
        expected_outcome="CONTEXTUALIZES: 5,000 represents worldwide workforce, while 3,800 is specific to India division. Not a contradiction.",
        why_it_matters="Prevents false-alarm contradictions by elevating contextual dimensions (geography, scope, timeframe) over raw figures."
    ),
    DemoCaseInfo(
        id="case_4",
        title="Case 4: Failure & Uncertainty (Missing Context)",
        case_type=RelationshipType.UNCERTAIN,
        description="Two market commentary snippets report conflicting market shares (35% vs 18%) without specifying the year or region.",
        document_a_name="ApexAI_Market_Brief_A.pdf",
        document_b_name="ApexAI_Market_Brief_B.pdf",
        expected_outcome="UNCERTAIN: System reports lack of explicit temporal and geographical scope, refusing to hallucinate a conclusion.",
        why_it_matters="Demonstrates system humility and honest auditability when source evidence is underspecified."
    )
]

def create_pdf(file_path: str, title: str, paragraphs: List[str]):
    if os.path.exists(file_path):
        return
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    doc = fitz.open()
    page = doc.new_page(width=595, height=842) # A4
    
    # Title
    page.insert_text((50, 60), title, fontsize=18, fontname="helv", color=(0.1, 0.1, 0.3))
    page.draw_line((50, 75), (545, 75), color=(0.2, 0.4, 0.8), width=1.5)
    
    # Content
    y = 110
    for p in paragraphs:
        rect = fitz.Rect(50, y, 545, y + 100)
        rc = page.insert_textbox(rect, p, fontsize=11, fontname="helv", color=(0.15, 0.15, 0.15))
        y += 75
        if y > 750:
            page = doc.new_page(width=595, height=842)
            y = 60

    doc.save(file_path)
    doc.close()

def generate_all_demo_pdfs():
    """Generates the 8 demonstration PDFs for the 4 canonical cases."""
    os.makedirs(DEMO_DIR, exist_ok=True)

    # Case 1: Corroboration
    p1 = os.path.join(DEMO_DIR, "AlphaCorp_Annual_Report_FY24.pdf")
    create_pdf(p1, "AlphaCorp Annual Financial Report FY2024", [
        "Executive Summary:",
        "AlphaCorp generated revenue of $1.2 billion in FY2024, representing solid growth across all core operations.",
        "The organization maintains strong operational margins and continues expansion into key enterprise markets.",
        "Headquartered in Bangalore, the company continues to invest in engineering talent."
    ])

    p2 = os.path.join(DEMO_DIR, "AlphaCorp_Investor_Presentation_2024.pdf")
    create_pdf(p2, "AlphaCorp Investor Presentation - Q4 2024", [
        "Performance Highlights:",
        "AlphaCorp recorded revenue of $1,200 million in FY2024, matching consensus market estimates.",
        "The company maintains headquarters in Bangalore and serves enterprise clients internationally.",
        "CEO is John Smith, who guided the executive team through FY2024 expansion."
    ])

    # Case 2: Genuine Contradiction
    p3 = os.path.join(DEMO_DIR, "TechVanguard_Company_Profile.pdf")
    create_pdf(p3, "TechVanguard Corporate Profile", [
        "Origins and Vision:",
        "TechVanguard was founded in 2012 by a cohort of computer vision researchers in California.",
        "Since its initial inception, the company has delivered advanced autonomous navigation solutions worldwide.",
        "The company reported revenue of $45 million in 2023."
    ])

    p4 = os.path.join(DEMO_DIR, "TechVanguard_Industry_Overview.pdf")
    create_pdf(p4, "TechVanguard Industry Research Report", [
        "Company Background:",
        "TechVanguard was founded in 2015 following a restructuring of its predecessor lab.",
        "The venture focuses exclusively on commercial robotic systems for industrial automation.",
        "The company has a workforce of 250 employees."
    ])

    # Case 3: Apparent Contradiction (Contextualization)
    p5 = os.path.join(DEMO_DIR, "GlobalDynamics_Global_Report.pdf")
    create_pdf(p5, "GlobalDynamics Worldwide Organizational Review", [
        "Global Workforce Distribution:",
        "GlobalDynamics has 5,000 employees worldwide across its international subsidiaries and technology centers.",
        "The enterprise recorded total revenue of $850 million in FY2023.",
        "Global operations span North America, Europe, and Asia-Pacific."
    ])

    p6 = os.path.join(DEMO_DIR, "GlobalDynamics_India_Division.pdf")
    create_pdf(p6, "GlobalDynamics India Operations Summary", [
        "Regional Hub Overview:",
        "GlobalDynamics has 3,800 employees in India supporting cloud architecture and platform engineering.",
        "The Bangalore tech park serves as the primary regional software development center.",
        "The division was established in 2019 to accelerate engineering delivery."
    ])

    # Case 4: Failure & Uncertainty (Missing context)
    p7 = os.path.join(DEMO_DIR, "ApexAI_Market_Brief_A.pdf")
    create_pdf(p7, "ApexAI Market Briefing - Analyst Note", [
        "Competitive Landscape:",
        "ApexAI reported market share of 35% in enterprise search solutions according to early vendor surveys.",
        "The vendor highlights rapid adoption among mid-market firms.",
        "No audit timeframe was specified in the initial whitepaper."
    ])

    p8 = os.path.join(DEMO_DIR, "ApexAI_Market_Brief_B.pdf")
    create_pdf(p8, "ApexAI Industry Commentary", [
        "Market Sizing Report:",
        "ApexAI captured market share of 18% in search deployments among surveyed enterprise clients.",
        "Sample methodology and regional coverage were omitted from the summary tables.",
        "The vendor notes strong competitive pressure from legacy database providers."
    ])

    return DEMO_CASES
