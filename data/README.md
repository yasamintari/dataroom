# Sample Company Data

Place your sample company documents here for testing.

## Folder Structure

Organize documents by company, with subfolders for different document types:

```
data/
└── sample_companies/
    ├── company_a/
    │   ├── financials/
    │   │   ├── Q1_2024_P&L.xlsx
    │   │   ├── Q2_2024_P&L.xlsx
    │   │   └── Balance_Sheet_2024.xlsx
    │   ├── pitch_deck/
    │   │   └── Series_A_Pitch.pdf
    │   ├── technical/
    │   │   ├── Architecture_Diagram.pdf
    │   │   └── Technical_Spec.docx
    │   ├── legal/
    │   │   ├── Cap_Table.xlsx
    │   │   └── Terms_of_Service.pdf
    │   └── product/
    │       └── Product_Roadmap.pdf
    └── company_b/
        └── ... (similar structure)
```

## Document Types

The system automatically classifies documents into these categories:

1. **financial**: P&L statements, balance sheets, cash flow, budgets, financial models
2. **pitch_deck**: Investor presentations, company overviews
3. **technical**: Architecture docs, technical specifications, engineering docs
4. **legal**: Contracts, agreements, cap tables, incorporation documents
5. **product**: Product specs, roadmaps, user stories
6. **other**: Any document that doesn't fit above categories

## Classification

Documents are classified using:
1. **Folder names**: `/financials/` folder → financial documents
2. **Filenames**: `pitch_deck.pdf` → pitch_deck
3. **File extensions**: `.xlsx` files are likely financial
4. **Content analysis**: Text analysis (optional, if LLM is available)

The system uses weighted voting to determine the best classification.

## Alternative: URLs File

If you have public URLs to documents, create a file:

```
data/document_links.txt
```

With one URL per line:
```
https://example.com/company_a_pitch.pdf
https://example.com/company_a_financials.xlsx
https://example.com/company_b_overview.pdf
...
```

Then use the `02_ingest_company.py` notebook to download and ingest them.

## Getting Started

1. Create company folders: `mkdir -p data/sample_companies/my_company/{financials,pitch_deck,technical,legal,product}`
2. Add your documents to appropriate folders
3. Run `02_ingest_company.py` notebook in Databricks
4. Documents will be uploaded, classified, and registered automatically
