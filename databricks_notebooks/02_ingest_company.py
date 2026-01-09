# Databricks notebook source
"""
Ingest Company Documents

This notebook demonstrates how to:
1. Ingest documents from local folders (preserving folder structure)
2. Download documents from web URLs
3. Automatically classify documents
4. Register in Delta tables

Use this for each company you want to add to the data room.
"""

# COMMAND ----------
# MAGIC %md
# MAGIC # Document Ingestion
# MAGIC
# MAGIC This notebook ingests company documents into the data room.
# MAGIC
# MAGIC ## Two methods:
# MAGIC 1. **Local folder**: Upload company folder with nested structure
# MAGIC 2. **Web URLs**: Provide list of URLs to download

# COMMAND ----------
# Configuration
CATALOG = "yasamin_tari"
SCHEMA = "dataroom"
STORAGE_PATH = "/Volumes/yasamin_tari/dataroom/raw"

# COMMAND ----------
# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------
import sys
import os

# Add src to path (adjust based on your setup)
sys.path.append("/Workspace/Repos/.../dataroom/src")  # Update this path

# Alternatively, install as package
# %pip install -e /Workspace/Repos/.../dataroom

from processors.document_ingestion import DocumentIngestion, ingest_company_from_folder
from processors.document_classifier import classify_document

# COMMAND ----------
# Initialize ingestion client
ingestion = DocumentIngestion(
    storage_path=STORAGE_PATH,
    spark_session=spark,
    catalog=CATALOG,
    schema=SCHEMA
)

print("✓ Document ingestion initialized")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Method 1: Ingest from Local Folder
# MAGIC
# MAGIC Upload your company folder to DBFS first, then ingest.
# MAGIC
# MAGIC Example folder structure:
# MAGIC ```
# MAGIC /dbfs/sample_companies/acme_corp/
# MAGIC ├── financials/
# MAGIC │   ├── Q1_2024_P&L.xlsx
# MAGIC │   └── balance_sheet_2024.xlsx
# MAGIC ├── pitch_deck/
# MAGIC │   └── Series_A_Pitch.pdf
# MAGIC ├── technical/
# MAGIC │   └── Architecture_Overview.pdf
# MAGIC └── legal/
# MAGIC     └── Cap_Table.xlsx
# MAGIC ```

# COMMAND ----------
# Example: Ingest a single company folder

company_name = "Acme Corp"
folder_path = "/dbfs/sample_companies/acme_corp"  # Update this path

# Optional: Add company metadata
company_metadata = {
    "industry": "SaaS",
    "stage": "series_a",
    "founded_year": 2020,
    "headquarters": "San Francisco, CA",
    "website": "https://acme-corp.example.com"
}

# Ingest
summary = ingestion.ingest_company_folder(
    company_name=company_name,
    folder_path=folder_path,
    company_metadata=company_metadata
)

print(f"\n{'='*60}")
print(f"Ingestion Summary for {company_name}")
print(f"{'='*60}")
print(f"Company ID: {summary['company_id']}")
print(f"Documents found: {summary['documents_found']}")
print(f"Documents registered: {summary['documents_registered']}")
print(f"\nDocument types:")
for doc_type, count in summary['document_types'].items():
    print(f"  - {doc_type}: {count}")
print(f"{'='*60}\n")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Method 2: Download from URLs
# MAGIC
# MAGIC Provide a list of publicly accessible URLs to download documents.

# COMMAND ----------
# Example: Download documents from URLs

company_name = "TechStart Inc"
company_id = "techstart_demo"  # Or generate automatically

# List of document URLs
document_urls = [
    "https://example.com/techstart_pitch_deck.pdf",
    "https://example.com/techstart_financials.xlsx",
    "https://example.com/techstart_technical_overview.pdf",
    # Add more URLs...
]

# Register company first
ingestion.register_company(
    company_id=company_id,
    company_name=company_name,
    industry="AI/ML",
    stage="seed"
)

# Download documents
documents = []
for url in document_urls:
    doc = ingestion.download_from_url(url, company_id)
    if doc:
        documents.append(doc)

# Register in Delta
ingestion.register_documents_in_delta(documents)

print(f"✓ Downloaded and registered {len(documents)} documents for {company_name}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Method 3: Batch Ingest Multiple Companies

# COMMAND ----------
# Batch ingest multiple companies from folders

companies_base_path = "/dbfs/sample_companies"

companies = [
    {
        "name": "Company A",
        "folder": "company_a",
        "metadata": {"industry": "FinTech", "stage": "seed"}
    },
    {
        "name": "Company B",
        "folder": "company_b",
        "metadata": {"industry": "HealthTech", "stage": "series_a"}
    },
    # Add more companies...
]

summaries = []
for company in companies:
    folder_path = os.path.join(companies_base_path, company["folder"])

    if os.path.exists(folder_path):
        summary = ingestion.ingest_company_folder(
            company_name=company["name"],
            folder_path=folder_path,
            company_metadata=company["metadata"]
        )
        summaries.append(summary)
        print(f"✓ Ingested {company['name']}: {summary['documents_found']} documents")
    else:
        print(f"✗ Folder not found: {folder_path}")

print(f"\n✓ Batch ingestion complete: {len(summaries)} companies processed")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Verify Ingestion

# COMMAND ----------
# Check companies table
companies_df = spark.sql(f"""
    SELECT
        company_id,
        name,
        industry,
        stage,
        created_at,
        total_documents
    FROM {CATALOG}.{SCHEMA}.companies
    ORDER BY created_at DESC
""")

display(companies_df)

# COMMAND ----------
# Check documents table
documents_df = spark.sql(f"""
    SELECT
        d.company_id,
        c.name as company_name,
        d.filename,
        d.document_type,
        d.classification_confidence,
        d.file_size_bytes,
        d.uploaded_at
    FROM {CATALOG}.{SCHEMA}.documents d
    LEFT JOIN {CATALOG}.{SCHEMA}.companies c
        ON d.company_id = c.company_id
    ORDER BY d.uploaded_at DESC
""")

display(documents_df)

# COMMAND ----------
# Document type distribution
type_distribution = spark.sql(f"""
    SELECT
        document_type,
        COUNT(*) as count,
        AVG(classification_confidence) as avg_confidence
    FROM {CATALOG}.{SCHEMA}.documents
    GROUP BY document_type
    ORDER BY count DESC
""")

display(type_distribution)

# COMMAND ----------
# MAGIC %md
# MAGIC ## Sample: Read Your Document Links File
# MAGIC
# MAGIC If you have a text file with URLs (one per line), use this:

# COMMAND ----------
# Read URLs from file
urls_file = "/dbfs/dataroom/document_links.txt"

if os.path.exists(urls_file):
    with open(urls_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"Found {len(urls)} URLs to download")

    # You can now download them for a specific company
    # company_id = "your_company_id"
    # for url in urls:
    #     ingestion.download_from_url(url, company_id)
else:
    print(f"URLs file not found: {urls_file}")
    print("Create this file with one URL per line to batch download documents")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Next Steps
# MAGIC
# MAGIC ✅ Documents ingested and classified
# MAGIC
# MAGIC Next: Run `03_process_documents.py` to:
# MAGIC - Extract text from documents
# MAGIC - Extract financial metrics
# MAGIC - Create vector embeddings for RAG

# COMMAND ----------
print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ✅ Document Ingestion Complete!                           ║
║                                                              ║
║   Next: Run 03_process_documents.py                         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")
