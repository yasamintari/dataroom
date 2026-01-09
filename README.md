# VC Due Diligence Data Room

AI-powered data room for venture capital due diligence with multi-company support, automatic document processing, and investment analysis.

##  Features

- **Multi-company document management** with nested folder structures
- **Automatic document categorization** (financials, pitch decks, technical docs, legal, etc.)
- **Intelligent data extraction** from PDFs, Excel, Word, and web links
- **Company-specific Q&A** using RAG (Retrieval Augmented Generation)
- **Investment analysis** across 7 key dimensions:
  - Market opportunity and size
  - Competitive moat and differentiation
  - Team quality and experience
  - Financial health and metrics
  - Product differentiation
  - Growth potential
  - Risk factors
- **Financial metrics extraction** (revenue, burn rate, runway, CAC, LTV, etc.)
- **Automated investment memo generation**
- **Web UI** for easy interaction

##  Architecture

### Technology Stack

**100% Open-source + Databricks Native:**

- **Storage & Processing**: Databricks (Delta Lake, Unity Catalog, PySpark)
- **Vector Search**: Databricks Vector Search
- **LLMs**: Databricks Foundation Models
  - DBRX Instruct (analysis and reasoning)
  - Llama 3.1 70B (general purpose)
  - Mixtral 8x7B (fast classification)
- **Embeddings**: BGE-large (sentence-transformers)
- **Document Processing**:
  - PyMuPDF (fitz) - PDF extraction
  - pdfplumber - Table extraction
  - python-docx - Word documents
  - pandas/openpyxl - Excel files
- **RAG Framework**: LangChain (open source)
- **UI**: Streamlit

### Data Model

```
Company
├── Metadata (industry, stage, funding round)
├── Documents/
│   ├── Financials/ (P&L, balance sheets, cash flow)
│   ├── Pitch Deck/
│   ├── Product & Technical/
│   ├── Legal/ (contracts, cap table)
│   └── Other/
├── Extracted Data
│   ├── Financial metrics (revenue, burn, runway, etc.)
│   ├── Document chunks (for RAG)
│   └── Metadata
└── Analysis Results
    ├── Investment memo
    ├── Dimension scores
    └── Recommendations
```

##  Getting Started

### Prerequisites

- Databricks workspace with Unity Catalog enabled
- Databricks Runtime 13.0+ (includes PySpark, MLflow)
- Python 3.9+

### Installation

1. **Clone or upload this repo to Databricks Workspace**

```bash
# In Databricks Repos or upload as folder
```

2. **Install dependencies**

```bash
%pip install -r requirements.txt
```

3. **Configure environment**

Copy `.env.example` to `.env` and update:

```bash
cp .env.example .env
# Edit .env with your Databricks settings
```

### Setup Steps

#### Step 1: Initialize Schema

Run the setup notebook to create Delta tables and vector search index:

```python
# Run: databricks_notebooks/01_setup_schema.py
```

This creates:
- Unity Catalog schema (`main.dataroom`)
- Delta tables (companies, documents, financial_metrics, etc.)
- Databricks Vector Search endpoint and index

#### Step 2: Ingest Company Documents

**Option A: From local folders**

Organize your documents:

```
data/sample_companies/
└── company_name/
    ├── financials/
    │   ├── Q1_2024_PL.xlsx
    │   └── balance_sheet.xlsx
    ├── pitch_deck/
    │   └── Series_A_Pitch.pdf
    ├── technical/
    │   └── Architecture.pdf
    └── legal/
        └── Cap_Table.xlsx
```

Then run:

```python
# Run: databricks_notebooks/02_ingest_company.py
# Modify the company_name and folder_path variables
```

**Option B: From web URLs**

Create a file with URLs:

```
data/document_links.txt
```

With one URL per line, then use the ingestion notebook to download them.

#### Step 3: Process Documents

Extract text, tables, and financial metrics:

```python
# Run: databricks_notebooks/03_process_documents.py
```

This:
- Extracts text from all documents
- Extracts tables and financial metrics
- Chunks documents for vector search
- Creates embeddings (via Databricks Vector Search)

#### Step 4: Use the System

**Option A: Streamlit UI**

```bash
cd ui
streamlit run app.py
```

**Option B: Python API**

```python
from rag.company_qa import create_company_qa_system
from analysis.investment_analyzer import InvestmentAnalyzer

# Create Q&A system
qa = create_company_qa_system()

# Ask questions
response = qa.ask("What is the company's revenue?", company_id="acme_corp")
print(response["answer"])

# Run investment analysis
analyzer = InvestmentAnalyzer(qa, spark, llm_client)
analysis = analyzer.analyze_company("acme_corp")

print(f"Score: {analysis['overall_score']}/10")
print(f"Recommendation: {analysis['recommendation']}")
```

##  Usage Examples

### Ingesting a Company

```python
from processors.document_ingestion import ingest_company_from_folder

summary = ingest_company_from_folder(
    company_name="Acme Corp",
    folder_path="/dbfs/sample_companies/acme_corp",
    spark_session=spark,
    company_metadata={
        "industry": "SaaS",
        "stage": "series_a",
        "founded_year": 2020
    }
)

print(f"Ingested {summary['documents_found']} documents")
```

### Asking Questions

```python
from rag.company_qa import create_company_qa_system

qa = create_company_qa_system()

# Ask about market
response = qa.ask(
    "What is the total addressable market?",
    company_id="acme_corp"
)

print(response["answer"])
print(f"Sources: {len(response['sources'])}")
```

### Running Investment Analysis

```python
from analysis.investment_analyzer import analyze_company
from rag.company_qa import create_company_qa_system, LLMClient

qa = create_company_qa_system()
llm = LLMClient("databricks-dbrx-instruct")

analysis = analyze_company("acme_corp", qa, spark, llm)

print(f"Overall Score: {analysis['overall_score']:.1f}/10")
print(f"Recommendation: {analysis['recommendation'].upper()}")
print(f"\nExecutive Summary:\n{analysis['executive_summary']}")
```

##  Project Structure

```
dataroom/
├── databricks_notebooks/       # Databricks notebooks for setup and processing
│   ├── 01_setup_schema.py     # Initialize database and vector search
│   ├── 02_ingest_company.py   # Ingest company documents
│   └── 03_process_documents.py # Process and extract data
├── src/                        # Python source code
│   ├── models/                 # Data models and schemas
│   │   └── schema.py
│   ├── processors/             # Document processors
│   │   ├── document_classifier.py
│   │   ├── document_ingestion.py
│   │   ├── document_processor.py
│   │   └── financial_extractor.py
│   ├── rag/                    # RAG implementation
│   │   └── company_qa.py
│   └── analysis/               # Investment analysis
│       └── investment_analyzer.py
├── ui/                         # Streamlit UI
│   └── app.py
├── config/                     # Configuration files
│   └── config.yaml
├── data/                       # Sample company data
│   └── sample_companies/
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

##  Key Components

### Document Classification

Documents are automatically classified using:
1. **Folder structure**: `/financials/` → financial documents
2. **Filename patterns**: `pitch_deck.pdf` → pitch deck
3. **File extensions**: `.xlsx` → likely financial
4. **Content analysis**: Text keyword matching

### Financial Extraction

Extracts metrics from:
- **Tables** in PDFs and Excel (highest confidence)
- **Text patterns** using regex (medium confidence)
- **LLM extraction** for unstructured text (when needed)

Metrics extracted:
- Revenue, revenue growth rate
- Gross margin, operating margin, EBITDA
- Cash balance, burn rate, runway
- CAC, LTV, LTV/CAC ratio
- Headcount, active users

### RAG (Retrieval Augmented Generation)

1. **Retrieval**: Query Databricks Vector Search with company filter
2. **Ranking**: Return top-k most relevant document chunks
3. **Generation**: Pass context to LLM (DBRX/Llama) for answer generation

### Investment Analysis

Analyzes companies across 7 dimensions:
1. Market opportunity (20% weight)
2. Competitive moat (20%)
3. Team quality (15%)
4. Financial health (15%)
5. Product differentiation (15%)
6. Growth potential (10%)
7. Risk factors (5%)

Generates:
- Overall score (0-10)
- Recommendation (Strong Buy / Buy / Hold / Pass)
- Executive summary
- Detailed analysis per dimension
- Key risks and opportunities
- Next steps for diligence

##  Configuration

Edit `config/config.yaml` to customize:

- Database settings (catalog, schema)
- Model selection (DBRX, Llama, Mixtral)
- Embedding model and dimensions
- Chunk size and overlap
- Document classification keywords
- Analysis weights and thresholds

##  Performance Tips

1. **Batch Processing**: Process multiple companies in parallel
2. **Incremental Updates**: Only process new/updated documents
3. **Caching**: Use Databricks caching for repeated queries
4. **Model Selection**:
   - Use Mixtral for classification (fast)
   - Use DBRX for analysis (best quality)
5. **Vector Search**: Use filters to reduce search space

##  Troubleshooting

### Vector Search Not Available

If Databricks Vector Search is not enabled:
- Use ChromaDB or FAISS as alternatives (see code comments)
- Contact Databricks to enable Vector Search for your workspace

### LLM Generation Errors

Check:
1. Model endpoint is accessible
2. Databricks token is valid
3. Model name is correct for your workspace

### Document Processing Failures

Check:
1. File format is supported
2. File is not corrupted
3. Sufficient memory for large files

##  Security Considerations

- Documents are stored in Databricks DBFS/Unity Catalog (secure by default)
- Use Unity Catalog for fine-grained access control
- API tokens should be stored securely (use Databricks Secrets)
- Consider data retention policies for sensitive documents

##  Next Steps

1. **Add more document types**: PowerPoint, images (OCR), audio transcripts
2. **Enhance financial extraction**: Support more complex tables and calculations
3. **Comparative analysis**: Compare multiple companies side-by-side
4. **Custom scoring**: Allow users to define custom analysis dimensions
5. **Collaboration**: Add comments, sharing, and team features
6. **Integrations**: Connect to deal flow systems, CRM, data rooms (DocSend, etc.)

##  License

MIT License - feel free to use and modify for your needs.

##  Contributing

Contributions welcome! Areas for improvement:
- Additional document processors
- Enhanced financial extraction algorithms
- UI/UX improvements
- More analysis dimensions
- Performance optimizations

##  Support

For issues or questions:
- Check documentation in `docs/`
- Review code comments
- Open an issue on GitHub

---

Built with ❤️ using Databricks and open-source tools.
