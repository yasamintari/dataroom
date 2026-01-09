# Databricks Setup Guide

This guide explains how to set up the VC Data Room in your Databricks workspace.

## 🎯 What Will Be Created

When you run `01_setup_schema.py`, the following will be created in your Databricks workspace:

### Unity Catalog Structure

```
yasamin_tari (Catalog)
└── dataroom (Schema)
    ├── Volumes/
    │   ├── documents/     # Main document storage
    │   ├── raw/          # Raw/unprocessed documents
    │   └── processed/    # Processed documents
    │
    ├── Tables/
    │   ├── companies              # Company metadata
    │   ├── documents              # Document metadata and classification
    │   ├── financial_metrics      # Extracted financial data
    │   ├── document_chunks        # Text chunks for RAG
    │   └── investment_analysis    # Analysis results
    │
    └── Vector Search/
        └── document_chunks_index  # Vector index for semantic search
```

### Volume Paths

After setup, you can access volumes at:
- **Documents**: `/Volumes/yasamin_tari/dataroom/documents`
- **Raw**: `/Volumes/yasamin_tari/dataroom/raw`
- **Processed**: `/Volumes/yasamin_tari/dataroom/processed`

---

## 📋 Prerequisites

Before running the setup:

1. **Databricks Workspace** with Unity Catalog enabled
2. **Permissions**:
   - `CREATE CATALOG` (if catalog doesn't exist)
   - `CREATE SCHEMA`
   - `CREATE VOLUME`
   - `CREATE TABLE`
   - `USE CATALOG`
   - `USE SCHEMA`

3. **Check if catalog exists**:
   ```sql
   SHOW CATALOGS LIKE 'yasamin_tari';
   ```

4. **Create catalog if needed**:
   ```sql
   CREATE CATALOG IF NOT EXISTS yasamin_tari;
   GRANT USE CATALOG ON CATALOG yasamin_tari TO <your_user>;
   GRANT CREATE SCHEMA ON CATALOG yasamin_tari TO <your_user>;
   ```

---

## 🚀 Setup Steps

### Step 1: Upload Notebooks to Databricks

1. Go to your Databricks workspace
2. Navigate to **Workspace** → **Users** → your user
3. Create a folder (e.g., `dataroom`)
4. Upload the notebooks:
   - `databricks_notebooks/01_setup_schema.py`
   - `databricks_notebooks/02_ingest_company.py`
   - `databricks_notebooks/03_process_documents.py`

### Step 2: Run Setup Notebook

Open and run `01_setup_schema.py`:

```python
# This will create:
# - Schema: yasamin_tari.dataroom
# - 3 Volumes (documents, raw, processed)
# - 5 Delta tables
# - Vector Search endpoint and index
```

**Expected output:**
```
✓ Schema yasamin_tari.dataroom created/verified
✓ Using schema yasamin_tari.dataroom
✓ Volume yasamin_tari.dataroom.documents created - Main document storage
✓ Volume yasamin_tari.dataroom.raw created - Raw/unprocessed documents
✓ Volume yasamin_tari.dataroom.processed created - Processed documents
✓ Created table: companies
✓ Created table: documents
✓ Created table: financial_metrics
✓ Created table: document_chunks
✓ Created table: investment_analysis
✓ Created vector search endpoint: dataroom_vs_endpoint
✓ Created vector search index: yasamin_tari.dataroom.document_chunks_index
```

### Step 3: Verify Setup

Run these SQL queries to verify:

```sql
-- Check schema
USE CATALOG yasamin_tari;
SHOW SCHEMAS;

-- Check volumes
SHOW VOLUMES IN yasamin_tari.dataroom;

-- Check tables
USE yasamin_tari.dataroom;
SHOW TABLES;

-- Check tables are empty
SELECT COUNT(*) FROM companies;
SELECT COUNT(*) FROM documents;
```

---

## 📁 Uploading Sample Data

### Option 1: Upload Files via Databricks UI

1. Go to **Data** → **Volumes**
2. Navigate to `yasamin_tari` → `dataroom` → `raw`
3. Click **Upload**
4. Create company folders (e.g., `company_a/`)
5. Upload documents to company folders

### Option 2: Upload via Databricks CLI

```bash
# Install Databricks CLI
pip install databricks-cli

# Configure
databricks configure --token

# Upload folder
databricks fs cp -r ./data/sample_companies/company_a dbfs:/Volumes/yasamin_tari/dataroom/raw/company_a
```

### Option 3: Mount Local Folder (for development)

```python
# In a Databricks notebook
dbutils.fs.mount(
    source="<your-local-path>",
    mount_point="/mnt/dataroom",
    extra_configs={}
)
```

---

## 🔧 Configuration

All settings are centralized in `config/config.yaml`:

```yaml
databricks:
  catalog: "yasamin_tari"
  schema: "dataroom"
  volume_path: "/Volumes/yasamin_tari/dataroom/documents"

storage:
  raw_documents: "/Volumes/yasamin_tari/dataroom/raw"
  processed_documents: "/Volumes/yasamin_tari/dataroom/processed"
```

---

## 🧪 Testing Setup

### Quick Test - Create Sample Company

Run this in a Databricks notebook:

```python
from pyspark.sql import Row
from datetime import datetime

# Test company creation
company_data = Row(
    company_id="test_company",
    name="Test Company",
    industry="SaaS",
    stage="seed",
    created_at=datetime.utcnow(),
    updated_at=datetime.utcnow(),
    total_documents=0
)

spark.createDataFrame([company_data]).write \
    .format("delta") \
    .mode("append") \
    .saveAsTable("yasamin_tari.dataroom.companies")

# Verify
spark.sql("SELECT * FROM yasamin_tari.dataroom.companies").show()
```

---

## 🐛 Troubleshooting

### Error: "Catalog not found"

Create the catalog first:
```sql
CREATE CATALOG yasamin_tari;
```

### Error: "Permission denied"

Request permissions from your Databricks admin:
```sql
GRANT USE CATALOG ON CATALOG yasamin_tari TO <your_user>;
GRANT CREATE SCHEMA ON CATALOG yasamin_tari TO <your_user>;
```

### Error: "Volume creation failed"

Ensure Unity Catalog is enabled:
1. Check workspace admin settings
2. Verify metastore is attached
3. Contact Databricks support if needed

### Error: "Vector Search not available"

Vector Search requires specific workspace configuration:
1. Check if enabled for your workspace
2. Use ChromaDB as alternative (see code comments)
3. Contact Databricks to enable Vector Search

### Tables showing as empty

This is expected after setup! Tables populate when you:
1. Run `02_ingest_company.py` (adds documents)
2. Run `03_process_documents.py` (processes and extracts data)

---

## 📊 Expected Table Schemas

### companies
```
company_id: STRING
name: STRING
industry: STRING
stage: STRING
founded_year: INT
headquarters: STRING
website: STRING
created_at: TIMESTAMP
updated_at: TIMESTAMP
total_documents: INT
last_analyzed: TIMESTAMP
```

### documents
```
document_id: STRING
company_id: STRING
filename: STRING
file_path: STRING
file_type: STRING
file_size_bytes: BIGINT
document_type: STRING (financial, pitch_deck, technical, legal, product, other)
classification_confidence: FLOAT
page_count: INT
has_tables: BOOLEAN
has_charts: BOOLEAN
processed: BOOLEAN
processing_error: STRING
uploaded_at: TIMESTAMP
processed_at: TIMESTAMP
```

### financial_metrics
```
metric_id: STRING
company_id: STRING
document_id: STRING
period_start: STRING
period_end: STRING
revenue: DOUBLE
revenue_growth_rate: DOUBLE
... (all financial metrics)
extracted_at: TIMESTAMP
confidence_score: FLOAT
```

---

## 🔄 Cleanup (Optional)

To remove everything and start fresh:

```sql
-- Drop tables
DROP TABLE IF EXISTS yasamin_tari.dataroom.investment_analysis;
DROP TABLE IF EXISTS yasamin_tari.dataroom.document_chunks;
DROP TABLE IF EXISTS yasamin_tari.dataroom.financial_metrics;
DROP TABLE IF EXISTS yasamin_tari.dataroom.documents;
DROP TABLE IF EXISTS yasamin_tari.dataroom.companies;

-- Drop volumes (removes data!)
DROP VOLUME IF EXISTS yasamin_tari.dataroom.documents;
DROP VOLUME IF EXISTS yasamin_tari.dataroom.raw;
DROP VOLUME IF EXISTS yasamin_tari.dataroom.processed;

-- Drop schema
DROP SCHEMA IF EXISTS yasamin_tari.dataroom CASCADE;
```

---

## ✅ Next Steps

After setup is complete:
1. ✅ Schema and volumes created
2. ➡️ Upload sample data (see above)
3. ➡️ Run `02_ingest_company.py` to process uploads
4. ➡️ Run `03_process_documents.py` to extract data
5. ➡️ Use Q&A and analysis features!

---

## 📝 Notes

- **Unity Catalog Volumes** are recommended over DBFS for better governance
- **Vector Search** may take a few minutes to index documents
- **First-time setup** takes ~2-5 minutes depending on workspace
- **Storage costs** apply to volumes (similar to S3/cloud storage)

Need help? Check the main [README](../README.md) or open an issue.
