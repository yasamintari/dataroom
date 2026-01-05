"""
VC Due Diligence Data Room - Streamlit UI

Main application providing:
- Company selection and overview
- Document viewing
- Q&A interface
- Investment analysis dashboard
"""

import streamlit as st
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Page configuration
st.set_page_config(
    page_title="VC Data Room",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .score-excellent {
        color: #28a745;
        font-weight: bold;
    }
    .score-good {
        color: #17a2b8;
        font-weight: bold;
    }
    .score-warning {
        color: #ffc107;
        font-weight: bold;
    }
    .score-poor {
        color: #dc3545;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'selected_company' not in st.session_state:
    st.session_state.selected_company = None
if 'qa_history' not in st.session_state:
    st.session_state.qa_history = []


def main():
    """Main application."""

    # Header
    st.markdown('<p class="main-header">📊 VC Due Diligence Data Room</p>', unsafe_allow_html=True)
    st.markdown("---")

    # Sidebar
    with st.sidebar:
        st.header("Navigation")

        page = st.radio(
            "Select Page",
            ["🏠 Home", "📁 Companies", "❓ Q&A", "📊 Analysis", "⚙️ Settings"],
            label_visibility="collapsed"
        )

        st.markdown("---")

        # Company selector
        st.subheader("Select Company")

        # Mock company list (replace with actual database query)
        companies = get_companies()

        if companies:
            company_options = {f"{c['name']} ({c['industry']})": c['company_id'] for c in companies}
            selected = st.selectbox(
                "Company",
                options=list(company_options.keys()),
                label_visibility="collapsed"
            )

            if selected:
                st.session_state.selected_company = company_options[selected]
        else:
            st.info("No companies found. Please ingest data first.")

        st.markdown("---")
        st.caption("VC Data Room v0.1.0")

    # Main content
    if page == "🏠 Home":
        show_home_page()
    elif page == "📁 Companies":
        show_companies_page()
    elif page == "❓ Q&A":
        show_qa_page()
    elif page == "📊 Analysis":
        show_analysis_page()
    elif page == "⚙️ Settings":
        show_settings_page()


def show_home_page():
    """Home page with overview and quick stats."""

    st.header("Welcome to the VC Data Room")
    st.write("AI-powered due diligence platform for venture capital")

    # Quick stats
    col1, col2, col3, col4 = st.columns(4)

    stats = get_system_stats()

    with col1:
        st.metric("Companies", stats.get('total_companies', 0))

    with col2:
        st.metric("Documents", stats.get('total_documents', 0))

    with col3:
        st.metric("Processed", f"{stats.get('processed_pct', 0):.0f}%")

    with col4:
        st.metric("Analyses", stats.get('total_analyses', 0))

    st.markdown("---")

    # Recent activity
    st.subheader("Recent Activity")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Recently Added Companies**")
        recent_companies = get_recent_companies(limit=5)

        if recent_companies:
            for company in recent_companies:
                st.write(f"- {company['name']} ({company['industry']})")
        else:
            st.info("No companies yet")

    with col2:
        st.write("**Recent Analyses**")
        recent_analyses = get_recent_analyses(limit=5)

        if recent_analyses:
            for analysis in recent_analyses:
                st.write(f"- {analysis['company_name']}: {analysis['recommendation'].upper()}")
        else:
            st.info("No analyses yet")

    # Quick start guide
    st.markdown("---")
    st.subheader("Quick Start")

    st.write("""
    1. **Ingest Data**: Run `02_ingest_company.py` to upload company documents
    2. **Process Documents**: Run `03_process_documents.py` to extract data
    3. **Ask Questions**: Use the Q&A page to query company documents
    4. **Run Analysis**: Generate investment analyses in the Analysis page
    """)


def show_companies_page():
    """Companies page with document lists."""

    if not st.session_state.selected_company:
        st.warning("Please select a company from the sidebar")
        return

    company_id = st.session_state.selected_company
    company = get_company_details(company_id)

    if not company:
        st.error("Company not found")
        return

    # Company header
    col1, col2 = st.columns([3, 1])

    with col1:
        st.header(company['name'])
        st.write(f"**Industry**: {company.get('industry', 'N/A')}")
        st.write(f"**Stage**: {company.get('stage', 'N/A')}")

    with col2:
        if st.button("Run Analysis", type="primary"):
            st.info("Analysis feature - see Analysis page")

    st.markdown("---")

    # Documents
    st.subheader("Documents")

    documents = get_company_documents(company_id)

    if documents:
        # Group by type
        doc_types = {}
        for doc in documents:
            doc_type = doc.get('document_type', 'other')
            if doc_type not in doc_types:
                doc_types[doc_type] = []
            doc_types[doc_type].append(doc)

        # Display by type
        for doc_type, docs in doc_types.items():
            with st.expander(f"📁 {doc_type.replace('_', ' ').title()} ({len(docs)})"):
                for doc in docs:
                    col1, col2, col3 = st.columns([3, 1, 1])

                    with col1:
                        st.write(doc['filename'])

                    with col2:
                        status = "✅ Processed" if doc.get('processed') else "⏳ Pending"
                        st.write(status)

                    with col3:
                        size_mb = doc.get('file_size_bytes', 0) / 1024 / 1024
                        st.write(f"{size_mb:.1f} MB")
    else:
        st.info("No documents found for this company")


def show_qa_page():
    """Q&A page with chat interface."""

    if not st.session_state.selected_company:
        st.warning("Please select a company from the sidebar")
        return

    company_id = st.session_state.selected_company
    company = get_company_details(company_id)

    st.header(f"Ask about {company['name']}")

    st.write("Ask questions about the company using natural language:")

    # Question input
    question = st.text_input(
        "Your question",
        placeholder="What is the company's revenue growth rate?",
        label_visibility="collapsed"
    )

    if st.button("Ask", type="primary") and question:
        with st.spinner("Searching documents..."):
            # Mock Q&A (replace with actual implementation)
            answer = get_answer(question, company_id)

            # Add to history
            st.session_state.qa_history.append({
                "question": question,
                "answer": answer.get('answer', ''),
                "sources": answer.get('sources', [])
            })

    # Display history
    st.markdown("---")
    st.subheader("Conversation History")

    for i, qa in enumerate(reversed(st.session_state.qa_history[-10:])):
        with st.expander(f"Q: {qa['question'][:100]}...", expanded=(i==0)):
            st.write("**Answer:**")
            st.write(qa['answer'])

            if qa.get('sources'):
                st.write("**Sources:**")
                for source in qa['sources'][:3]:
                    st.caption(f"- {source.get('document_type', 'document')}: {source.get('text', '')[:100]}...")


def show_analysis_page():
    """Investment analysis page."""

    if not st.session_state.selected_company:
        st.warning("Please select a company from the sidebar")
        return

    company_id = st.session_state.selected_company
    company = get_company_details(company_id)

    st.header(f"Investment Analysis: {company['name']}")

    # Check if analysis exists
    existing_analysis = get_latest_analysis(company_id)

    if existing_analysis:
        # Display existing analysis
        display_analysis(existing_analysis)

        # Re-run button
        if st.button("🔄 Re-run Analysis"):
            with st.spinner("Running comprehensive analysis..."):
                # Mock analysis (replace with actual implementation)
                new_analysis = run_analysis(company_id)
                display_analysis(new_analysis)
    else:
        st.info("No analysis available for this company yet.")

        if st.button("▶️ Run Analysis", type="primary"):
            with st.spinner("Running comprehensive analysis... This may take a few minutes."):
                # Mock analysis (replace with actual implementation)
                analysis = run_analysis(company_id)
                display_analysis(analysis)


def display_analysis(analysis: dict):
    """Display investment analysis results."""

    # Overall score
    score = analysis.get('overall_score', 0)
    recommendation = analysis.get('recommendation', 'unknown').upper()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Overall Score", f"{score:.1f}/10")

    with col2:
        st.metric("Recommendation", recommendation)

    with col3:
        confidence = analysis.get('confidence_level', 0) * 100
        st.metric("Confidence", f"{confidence:.0f}%")

    st.markdown("---")

    # Executive Summary
    st.subheader("Executive Summary")
    st.write(analysis.get('executive_summary', 'N/A'))

    st.markdown("---")

    # Dimension scores
    st.subheader("Analysis Dimensions")

    dimensions = analysis.get('dimensions', [])

    for dim in dimensions:
        with st.expander(f"{dim['dimension'].replace('_', ' ').title()}: {dim['score']:.1f}/10"):
            st.write(dim.get('reasoning', ''))

            if dim.get('key_findings'):
                st.write("**Key Findings:**")
                for finding in dim['key_findings']:
                    st.write(f"- {finding}")

    # Detailed sections
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Key Opportunities")
        opportunities = analysis.get('key_opportunities', [])
        for opp in opportunities:
            st.write(f"✅ {opp}")

    with col2:
        st.subheader("Key Risks")
        risks = analysis.get('key_risks', [])
        for risk in risks:
            st.write(f"⚠️ {risk}")

    # Next steps
    st.markdown("---")
    st.subheader("Recommended Next Steps")
    next_steps = analysis.get('next_steps', [])
    for i, step in enumerate(next_steps, 1):
        st.write(f"{i}. {step}")


def show_settings_page():
    """Settings page."""

    st.header("Settings")

    st.subheader("Database Configuration")
    catalog = st.text_input("Catalog", value="main")
    schema = st.text_input("Schema", value="dataroom")

    st.subheader("Model Configuration")
    analysis_model = st.selectbox(
        "Analysis Model",
        ["databricks-dbrx-instruct", "databricks-meta-llama-3-1-70b-instruct", "databricks-mixtral-8x7b-instruct"]
    )

    st.subheader("Processing Configuration")
    chunk_size = st.slider("Chunk Size", 400, 1200, 800)
    chunk_overlap = st.slider("Chunk Overlap", 50, 400, 200)

    if st.button("Save Settings"):
        st.success("Settings saved!")


# Helper functions (mock implementations - replace with actual database queries)

def get_companies():
    """Get list of companies."""
    # Mock data - replace with Spark SQL query
    return [
        {"company_id": "company_1", "name": "Acme Corp", "industry": "SaaS"},
        {"company_id": "company_2", "name": "TechStart Inc", "industry": "AI/ML"},
    ]


def get_company_details(company_id: str):
    """Get company details."""
    companies = {
        "company_1": {"company_id": "company_1", "name": "Acme Corp", "industry": "SaaS", "stage": "Series A"},
        "company_2": {"company_id": "company_2", "name": "TechStart Inc", "industry": "AI/ML", "stage": "Seed"},
    }
    return companies.get(company_id)


def get_company_documents(company_id: str):
    """Get documents for a company."""
    # Mock data
    return [
        {"filename": "Q1_2024_Financials.xlsx", "document_type": "financial", "processed": True, "file_size_bytes": 1024000},
        {"filename": "Pitch_Deck.pdf", "document_type": "pitch_deck", "processed": True, "file_size_bytes": 2048000},
    ]


def get_system_stats():
    """Get system statistics."""
    return {
        "total_companies": 5,
        "total_documents": 42,
        "processed_pct": 85,
        "total_analyses": 3
    }


def get_recent_companies(limit: int = 5):
    """Get recently added companies."""
    return get_companies()[:limit]


def get_recent_analyses(limit: int = 5):
    """Get recent analyses."""
    return [
        {"company_name": "Acme Corp", "recommendation": "buy"},
        {"company_name": "TechStart Inc", "recommendation": "hold"},
    ]


def get_answer(question: str, company_id: str):
    """Get answer to question (mock)."""
    return {
        "answer": "Based on the financial documents, the company's revenue growth rate is approximately 150% year-over-year.",
        "sources": [
            {"document_type": "financial", "text": "Q1 2024 revenue: $5M, Q1 2023 revenue: $2M"}
        ]
    }


def get_latest_analysis(company_id: str):
    """Get latest analysis for company."""
    # Mock - return None to trigger new analysis
    return None


def run_analysis(company_id: str):
    """Run investment analysis (mock)."""
    return {
        "overall_score": 7.5,
        "recommendation": "buy",
        "confidence_level": 0.75,
        "executive_summary": "Strong market opportunity with solid team execution. Revenue growth is impressive but burn rate needs monitoring.",
        "dimensions": [
            {
                "dimension": "market_opportunity",
                "score": 8.5,
                "reasoning": "Large TAM with growing demand. Market validated by multiple competitors.",
                "key_findings": ["$10B TAM", "30% annual market growth", "Clear product-market fit"]
            },
            {
                "dimension": "competitive_moat",
                "score": 7.0,
                "reasoning": "Proprietary technology provides differentiation but market is competitive.",
                "key_findings": ["Patents pending", "Network effects", "High switching costs"]
            },
        ],
        "key_opportunities": ["Market expansion", "Enterprise upsell", "International growth"],
        "key_risks": ["High burn rate", "Competition", "Regulatory uncertainty"],
        "next_steps": ["Schedule founder meeting", "Request detailed financial model", "Conduct customer references"]
    }


if __name__ == "__main__":
    main()
