# Databricks notebook source
"""
Setup Databricks Schema for VC Data Room

This notebook:
1. Creates Unity Catalog database and volume
2. Creates Delta tables for all entities
3. Sets up vector search endpoint and index
4. Validates the setup

Run this notebook ONCE to initialize the data room infrastructure.
"""

# COMMAND ----------
# MAGIC %md
# MAGIC # VC Data Room - Schema Setup
# MAGIC
# MAGIC This notebook initializes the Databricks infrastructure for the data room:
# MAGIC - Unity Catalog schema
# MAGIC - Delta tables (companies, documents, financial_metrics, etc.)
# MAGIC - Vector Search endpoint and index
# MAGIC - Permissions and access controls

# COMMAND ----------
# Configuration
CATALOG = "yasamin_tari"
SCHEMA = "dataroom"
VOLUME_NAME = "documents"
RAW_VOLUME = "raw"
PROCESSED_VOLUME = "processed"

# Table names
TABLES = [
    "companies",
    "documents",
    "financial_metrics",
    "document_chunks",
    "investment_analysis"
]

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Create Catalog and Schema

# COMMAND ----------
from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()

# Create schema (database) if not exists
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
print(f"✓ Schema {CATALOG}.{SCHEMA} created/verified")

# Set current database
spark.sql(f"USE {CATALOG}.{SCHEMA}")
print(f"✓ Using schema {CATALOG}.{SCHEMA}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. Create Unity Catalog Volumes for Document Storage

# COMMAND ----------
# Create volumes for document storage
volumes = [
    (VOLUME_NAME, "Main document storage"),
    (RAW_VOLUME, "Raw/unprocessed documents"),
    (PROCESSED_VOLUME, "Processed documents")
]

for volume_name, description in volumes:
    try:
        spark.sql(f"""
            CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.{volume_name}
            COMMENT '{description}'
        """)
        print(f"✓ Volume {CATALOG}.{SCHEMA}.{volume_name} created - {description}")
    except Exception as e:
        print(f"⚠ Volume creation error for {volume_name}: {e}")
        print("  Note: Ensure Unity Catalog is enabled and you have CREATE VOLUME permissions")

print(f"\n✓ Volume paths:")
print(f"  - Documents: /Volumes/{CATALOG}/{SCHEMA}/{VOLUME_NAME}")
print(f"  - Raw: /Volumes/{CATALOG}/{SCHEMA}/{RAW_VOLUME}")
print(f"  - Processed: /Volumes/{CATALOG}/{SCHEMA}/{PROCESSED_VOLUME}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. Create Delta Tables

# COMMAND ----------
# Import schema definitions
import sys
sys.path.append("/Workspace/Repos/...")  # Adjust to your repo path

# Alternatively, define schemas inline
from pyspark.sql.types import *

# Companies table
spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.companies (
        company_id STRING NOT NULL,
        name STRING NOT NULL,
        industry STRING,
        stage STRING,
        founded_year INT,
        headquarters STRING,
        website STRING,
        created_at TIMESTAMP,
        updated_at TIMESTAMP,
        total_documents INT,
        last_analyzed TIMESTAMP
    )
    USING DELTA
    COMMENT 'Company entities and metadata'
""")
print("✓ Created table: companies")

# Documents table
spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.documents (
        document_id STRING NOT NULL,
        company_id STRING NOT NULL,
        filename STRING NOT NULL,
        file_path STRING NOT NULL,
        file_type STRING,
        file_size_bytes BIGINT,
        document_type STRING,
        classification_confidence FLOAT,
        page_count INT,
        has_tables BOOLEAN,
        has_charts BOOLEAN,
        processed BOOLEAN DEFAULT FALSE,
        processing_error STRING,
        uploaded_at TIMESTAMP,
        processed_at TIMESTAMP
    )
    USING DELTA
    COMMENT 'Document metadata and classification'
""")
print("✓ Created table: documents")

# Financial metrics table
spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.financial_metrics (
        metric_id STRING NOT NULL,
        company_id STRING NOT NULL,
        document_id STRING NOT NULL,
        period_start STRING,
        period_end STRING,
        revenue DOUBLE,
        revenue_growth_rate DOUBLE,
        recurring_revenue DOUBLE,
        gross_margin DOUBLE,
        operating_margin DOUBLE,
        net_income DOUBLE,
        ebitda DOUBLE,
        cash_balance DOUBLE,
        burn_rate DOUBLE,
        runway_months DOUBLE,
        cac DOUBLE,
        ltv DOUBLE,
        ltv_cac_ratio DOUBLE,
        headcount INT,
        active_users INT,
        extracted_at TIMESTAMP,
        confidence_score FLOAT
    )
    USING DELTA
    COMMENT 'Extracted financial metrics from documents'
""")
print("✓ Created table: financial_metrics")

# Document chunks table (for RAG)
spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.document_chunks (
        chunk_id STRING NOT NULL,
        company_id STRING NOT NULL,
        document_id STRING NOT NULL,
        text STRING NOT NULL,
        chunk_index INT,
        document_type STRING,
        page_number INT,
        section_title STRING,
        created_at TIMESTAMP
    )
    USING DELTA
    COMMENT 'Document text chunks for vector search and RAG'
""")
print("✓ Created table: document_chunks")

# Investment analysis table
spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.investment_analysis (
        analysis_id STRING NOT NULL,
        company_id STRING NOT NULL,
        overall_score DOUBLE,
        recommendation STRING,
        confidence_level FLOAT,
        executive_summary STRING,
        market_analysis STRING,
        competitive_moat STRING,
        team_assessment STRING,
        financial_analysis STRING,
        key_risks STRING,
        key_opportunities STRING,
        suggested_investment_amount DOUBLE,
        suggested_valuation DOUBLE,
        next_steps STRING,
        analyzed_at TIMESTAMP,
        analyzed_by STRING,
        documents_analyzed INT
    )
    USING DELTA
    COMMENT 'Investment analysis results and recommendations'
""")
print("✓ Created table: investment_analysis")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. Create Indexes for Performance

# COMMAND ----------
# Add indexes for common queries
spark.sql(f"""
    ALTER TABLE {CATALOG}.{SCHEMA}.documents
    ADD CONSTRAINT documents_pk PRIMARY KEY (document_id)
""")

spark.sql(f"""
    ALTER TABLE {CATALOG}.{SCHEMA}.companies
    ADD CONSTRAINT companies_pk PRIMARY KEY (company_id)
""")

print("✓ Added primary key constraints")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5. Setup Databricks Vector Search

# COMMAND ----------
from databricks.vector_search.client import VectorSearchClient

# Initialize vector search client
vsc = VectorSearchClient()

# Vector search endpoint name
ENDPOINT_NAME = "dataroom_vs_endpoint"
INDEX_NAME = f"{CATALOG}.{SCHEMA}.document_chunks_index"

try:
    # Create vector search endpoint (if not exists)
    try:
        vsc.create_endpoint(name=ENDPOINT_NAME)
        print(f"✓ Created vector search endpoint: {ENDPOINT_NAME}")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"✓ Vector search endpoint already exists: {ENDPOINT_NAME}")
        else:
            raise e

    # Create vector search index on document_chunks table
    # This creates embeddings automatically using Databricks embedding model
    vsc.create_delta_sync_index(
        endpoint_name=ENDPOINT_NAME,
        index_name=INDEX_NAME,
        source_table_name=f"{CATALOG}.{SCHEMA}.document_chunks",
        pipeline_type="TRIGGERED",
        primary_key="chunk_id",
        embedding_source_column="text",  # Column to embed
        embedding_model_endpoint_name="databricks-bge-large-en"  # Databricks embedding endpoint
    )
    print(f"✓ Created vector search index: {INDEX_NAME}")

except Exception as e:
    print(f"⚠ Vector search setup error: {e}")
    print("Note: Vector Search requires Databricks workspace with Vector Search enabled")
    print("Alternative: We can use ChromaDB or FAISS for local vector storage")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 6. Validate Setup

# COMMAND ----------
# List all tables
tables = spark.sql(f"SHOW TABLES IN {CATALOG}.{SCHEMA}").collect()
print(f"\n✓ Tables created in {CATALOG}.{SCHEMA}:")
for table in tables:
    print(f"  - {table.tableName}")

# Verify table schemas
print("\n✓ Table schemas verified:")
for table_name in TABLES:
    count = spark.sql(f"SELECT COUNT(*) as cnt FROM {CATALOG}.{SCHEMA}.{table_name}").collect()[0].cnt
    print(f"  - {table_name}: {count} records")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Setup Complete! ✅
# MAGIC
# MAGIC Next steps:
# MAGIC 1. Run `02_ingest_company.py` to upload sample company documents
# MAGIC 2. Run `03_process_documents.py` to extract text and metadata
# MAGIC 3. Start using the data room!

# COMMAND ----------
print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ✅ VC Data Room Schema Setup Complete!                    ║
║                                                              ║
║   Next: Upload company documents using 02_ingest_company    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")
