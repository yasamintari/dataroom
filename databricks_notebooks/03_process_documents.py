# Databricks notebook source
"""
Process Documents

This notebook:
1. Processes all ingested documents (extract text, tables, metadata)
2. Extracts financial metrics from financial documents
3. Chunks documents for vector search
4. Updates Delta tables with processed data

Run this after ingesting documents with 02_ingest_company.py
"""

# COMMAND ----------
# MAGIC %md
# MAGIC # Document Processing Pipeline
# MAGIC
# MAGIC This notebook processes documents and extracts:
# MAGIC - Text content (for RAG/search)
# MAGIC - Financial metrics (from tables and text)
# MAGIC - Document metadata (page count, tables, etc.)
# MAGIC - Text chunks for vector indexing

# COMMAND ----------
# Configuration
CATALOG = "main"
SCHEMA = "dataroom"
STORAGE_PATH = "/dbfs/dataroom/raw"
CHUNK_SIZE = 800  # characters
CHUNK_OVERLAP = 200

# COMMAND ----------
# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------
import sys
sys.path.append("/Workspace/Repos/.../dataroom/src")

from processors.document_processor import DocumentProcessor, chunk_document
from processors.financial_extractor import extract_financial_metrics

# Initialize processors
doc_processor = DocumentProcessor()

print("✓ Document processors initialized")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Load Unprocessed Documents

# COMMAND ----------
# Get documents that haven't been processed yet
unprocessed_docs = spark.sql(f"""
    SELECT
        document_id,
        company_id,
        filename,
        file_path,
        document_type,
        file_type
    FROM {CATALOG}.{SCHEMA}.documents
    WHERE processed = FALSE
    ORDER BY uploaded_at
""").collect()

print(f"Found {len(unprocessed_docs)} unprocessed documents")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Process Documents

# COMMAND ----------
from pyspark.sql import Row
from datetime import datetime

processed_count = 0
chunk_records = []
financial_records = []

for doc in unprocessed_docs:
    document_id = doc.document_id
    company_id = doc.company_id
    file_path = doc.file_path
    document_type = doc.document_type

    print(f"\nProcessing: {doc.filename} ({document_type})")

    try:
        # 1. Process document (extract text, tables, metadata)
        result = doc_processor.process_document(file_path, document_id)

        if not result.get("success"):
            print(f"  ✗ Failed: {result.get('error')}")

            # Update document with error
            spark.sql(f"""
                UPDATE {CATALOG}.{SCHEMA}.documents
                SET processing_error = '{result.get('error')}'
                WHERE document_id = '{document_id}'
            """)
            continue

        # 2. Extract metadata
        page_count = result.get("page_count", 0)
        has_tables = result.get("has_tables", False)
        has_charts = result.get("has_charts", False)

        print(f"  ✓ Extracted: {page_count} pages, {len(result.get('tables', []))} tables")

        # 3. Extract financial metrics (if financial document)
        if document_type == "financial":
            metrics = extract_financial_metrics(
                result,
                document_id,
                company_id,
                llm_client=None  # Can add LLM client here if needed
            )

            financial_records.extend(metrics)
            print(f"  ✓ Extracted {len(metrics)} financial metrics")

        # 4. Chunk document for RAG
        chunks = doc_processor.chunk_text(
            text=result.get("full_text", ""),
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            document_id=document_id,
            document_type=document_type,
            metadata={
                "company_id": company_id,
                "page_count": page_count
            }
        )

        chunk_records.extend(chunks)
        print(f"  ✓ Created {len(chunks)} chunks")

        # 5. Update document status
        spark.sql(f"""
            UPDATE {CATALOG}.{SCHEMA}.documents
            SET
                processed = TRUE,
                processed_at = current_timestamp(),
                page_count = {page_count},
                has_tables = {has_tables},
                has_charts = {has_charts}
            WHERE document_id = '{document_id}'
        """)

        processed_count += 1

    except Exception as e:
        print(f"  ✗ Error processing {doc.filename}: {e}")

        # Log error
        error_msg = str(e).replace("'", "''")  # Escape quotes for SQL
        spark.sql(f"""
            UPDATE {CATALOG}.{SCHEMA}.documents
            SET processing_error = '{error_msg}'
            WHERE document_id = '{document_id}'
        """)

print(f"\n{'='*60}")
print(f"Processing Complete:")
print(f"  - Documents processed: {processed_count}/{len(unprocessed_docs)}")
print(f"  - Chunks created: {len(chunk_records)}")
print(f"  - Financial metrics extracted: {len(financial_records)}")
print(f"{'='*60}\n")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Save Chunks to Delta

# COMMAND ----------
if chunk_records:
    # Convert to DataFrame
    chunks_df = spark.createDataFrame([Row(**chunk) for chunk in chunk_records])

    # Write to Delta table
    chunks_df.write \
        .format("delta") \
        .mode("append") \
        .saveAsTable(f"{CATALOG}.{SCHEMA}.document_chunks")

    print(f"✓ Saved {len(chunk_records)} chunks to {CATALOG}.{SCHEMA}.document_chunks")
else:
    print("No chunks to save")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Save Financial Metrics to Delta

# COMMAND ----------
if financial_records:
    # Convert to DataFrame
    # First, flatten the metrics (each record may have multiple metric fields)
    flattened_metrics = []
    for record in financial_records:
        flattened_metrics.append(record)

    metrics_df = spark.createDataFrame([Row(**metric) for metric in flattened_metrics])

    # Write to Delta table
    metrics_df.write \
        .format("delta") \
        .mode("append") \
        .saveAsTable(f"{CATALOG}.{SCHEMA}.financial_metrics")

    print(f"✓ Saved {len(financial_records)} financial metrics to {CATALOG}.{SCHEMA}.financial_metrics")
else:
    print("No financial metrics to save")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Sync Vector Search Index
# MAGIC
# MAGIC This triggers the vector search index to create embeddings for all chunks.

# COMMAND ----------
from databricks.vector_search.client import VectorSearchClient

try:
    vsc = VectorSearchClient()

    # Trigger index sync
    INDEX_NAME = f"{CATALOG}.{SCHEMA}.document_chunks_index"

    # Check if index exists
    try:
        index = vsc.get_index(index_name=INDEX_NAME)
        print(f"✓ Vector search index found: {INDEX_NAME}")

        # Sync index (create embeddings for new chunks)
        index.sync()
        print(f"✓ Vector search index sync triggered")
        print("  Note: Embedding generation may take a few minutes")

    except Exception as e:
        print(f"⚠ Vector search index not found: {INDEX_NAME}")
        print("  Run 01_setup_schema.py to create the vector search index")

except Exception as e:
    print(f"⚠ Vector search not available: {e}")
    print("  Alternative: Use ChromaDB or FAISS for local vector storage")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Verification & Statistics

# COMMAND ----------
# Processing statistics by document type
processing_stats = spark.sql(f"""
    SELECT
        document_type,
        COUNT(*) as total_documents,
        SUM(CASE WHEN processed THEN 1 ELSE 0 END) as processed,
        SUM(CASE WHEN processing_error IS NOT NULL THEN 1 ELSE 0 END) as errors,
        AVG(page_count) as avg_pages
    FROM {CATALOG}.{SCHEMA}.documents
    GROUP BY document_type
    ORDER BY total_documents DESC
""")

display(processing_stats)

# COMMAND ----------
# Sample chunks
sample_chunks = spark.sql(f"""
    SELECT
        c.company_id,
        co.name as company_name,
        c.document_type,
        c.text,
        c.chunk_index,
        c.created_at
    FROM {CATALOG}.{SCHEMA}.document_chunks c
    LEFT JOIN {CATALOG}.{SCHEMA}.companies co
        ON c.company_id = co.company_id
    ORDER BY c.created_at DESC
    LIMIT 10
""")

display(sample_chunks)

# COMMAND ----------
# Financial metrics summary
if financial_records:
    financial_summary = spark.sql(f"""
        SELECT
            company_id,
            COUNT(*) as metric_count,
            AVG(revenue) as avg_revenue,
            AVG(burn_rate) as avg_burn_rate,
            AVG(runway_months) as avg_runway
        FROM {CATALOG}.{SCHEMA}.financial_metrics
        GROUP BY company_id
    """)

    display(financial_summary)

# COMMAND ----------
# MAGIC %md
# MAGIC ## Next Steps
# MAGIC
# MAGIC ✅ Documents processed and chunked
# MAGIC ✅ Financial metrics extracted
# MAGIC ✅ Vector embeddings created (or in progress)
# MAGIC
# MAGIC Next: Run `04_query_and_analysis.py` to:
# MAGIC - Ask questions about companies
# MAGIC - Run investment analysis
# MAGIC - Generate investment memos

# COMMAND ----------
print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ✅ Document Processing Complete!                          ║
║                                                              ║
║   Next: Run 04_query_and_analysis.py or use the UI         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")
