"""
Document processing pipeline with type-specific extractors.

Supports:
- PDF text extraction (PyMuPDF)
- Word document parsing (python-docx)
- Excel file reading (pandas/openpyxl)
- Table extraction from PDFs (pdfplumber)
- Text chunking for RAG
- Metadata extraction
"""

import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# PDF processing
import fitz  # PyMuPDF
import pdfplumber

# Word documents
try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None

# Excel files
import pandas as pd

# Web links
import requests
from bs4 import BeautifulSoup


class DocumentProcessor:
    """Process documents and extract text, tables, and metadata."""

    def __init__(self):
        """Initialize document processor."""
        self.supported_types = {
            '.pdf': self._process_pdf,
            '.docx': self._process_word,
            '.doc': self._process_word,
            '.xlsx': self._process_excel,
            '.xls': self._process_excel,
            '.csv': self._process_csv,
            '.txt': self._process_text,
            '.md': self._process_text,
        }

    def process_document(self, file_path: str, document_id: str) -> Dict:
        """
        Process a document and extract all content.

        Args:
            file_path: Path to document file
            document_id: Document identifier

        Returns:
            Dict with extracted content and metadata
        """
        file_ext = Path(file_path).suffix.lower()

        if file_ext not in self.supported_types:
            return {
                "document_id": document_id,
                "success": False,
                "error": f"Unsupported file type: {file_ext}"
            }

        try:
            processor_func = self.supported_types[file_ext]
            result = processor_func(file_path, document_id)
            result["success"] = True
            return result

        except Exception as e:
            return {
                "document_id": document_id,
                "success": False,
                "error": str(e)
            }

    def _process_pdf(self, file_path: str, document_id: str) -> Dict:
        """Extract text, tables, and metadata from PDF."""
        # Extract text with PyMuPDF
        doc = fitz.open(file_path)
        pages_text = []
        page_count = len(doc)

        for page_num, page in enumerate(doc):
            text = page.get_text()
            pages_text.append({
                "page": page_num + 1,
                "text": text
            })

        doc.close()

        # Extract tables with pdfplumber
        tables = []
        has_charts = False

        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Extract tables
                    page_tables = page.extract_tables()
                    if page_tables:
                        for table_idx, table in enumerate(page_tables):
                            tables.append({
                                "page": page_num + 1,
                                "table_index": table_idx,
                                "data": table,
                                "rows": len(table),
                                "cols": len(table[0]) if table else 0
                            })

                    # Check for images (potential charts)
                    if len(page.images) > 0:
                        has_charts = True

        except Exception as e:
            print(f"Warning: Table extraction failed for {file_path}: {e}")

        # Combine all text
        full_text = "\n\n".join([p["text"] for p in pages_text])

        return {
            "document_id": document_id,
            "file_type": "pdf",
            "page_count": page_count,
            "full_text": full_text,
            "pages": pages_text,
            "tables": tables,
            "has_tables": len(tables) > 0,
            "has_charts": has_charts,
            "metadata": {
                "page_count": page_count,
                "table_count": len(tables),
                "char_count": len(full_text)
            }
        }

    def _process_word(self, file_path: str, document_id: str) -> Dict:
        """Extract text from Word document."""
        if not DocxDocument:
            raise ImportError("python-docx not installed")

        doc = DocxDocument(file_path)

        # Extract paragraphs
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        full_text = "\n\n".join(paragraphs)

        # Extract tables
        tables = []
        for table_idx, table in enumerate(doc.tables):
            table_data = []
            for row in table.rows:
                row_data = [cell.text for cell in row.cells]
                table_data.append(row_data)

            tables.append({
                "table_index": table_idx,
                "data": table_data,
                "rows": len(table_data),
                "cols": len(table_data[0]) if table_data else 0
            })

        return {
            "document_id": document_id,
            "file_type": "word",
            "page_count": len(doc.sections),  # Approximate
            "full_text": full_text,
            "paragraphs": paragraphs,
            "tables": tables,
            "has_tables": len(tables) > 0,
            "has_charts": False,  # Would need additional processing
            "metadata": {
                "paragraph_count": len(paragraphs),
                "table_count": len(tables),
                "char_count": len(full_text)
            }
        }

    def _process_excel(self, file_path: str, document_id: str) -> Dict:
        """Extract data from Excel file."""
        # Read all sheets
        xlsx = pd.ExcelFile(file_path)
        sheets = {}
        all_text = []

        for sheet_name in xlsx.sheet_names:
            df = pd.read_excel(xlsx, sheet_name=sheet_name)

            # Convert to text representation
            sheet_text = f"Sheet: {sheet_name}\n"
            sheet_text += df.to_string(index=False)
            all_text.append(sheet_text)

            # Store structured data
            sheets[sheet_name] = {
                "name": sheet_name,
                "rows": len(df),
                "cols": len(df.columns),
                "columns": list(df.columns),
                "data": df.to_dict('records')  # For programmatic access
            }

        full_text = "\n\n".join(all_text)

        return {
            "document_id": document_id,
            "file_type": "excel",
            "page_count": len(sheets),  # Count sheets as pages
            "full_text": full_text,
            "sheets": sheets,
            "tables": list(sheets.values()),  # Treat sheets as tables
            "has_tables": True,
            "has_charts": False,
            "metadata": {
                "sheet_count": len(sheets),
                "total_rows": sum(s["rows"] for s in sheets.values()),
                "char_count": len(full_text)
            }
        }

    def _process_csv(self, file_path: str, document_id: str) -> Dict:
        """Extract data from CSV file."""
        df = pd.read_csv(file_path)

        # Convert to text
        full_text = df.to_string(index=False)

        # Structured data
        table_data = {
            "rows": len(df),
            "cols": len(df.columns),
            "columns": list(df.columns),
            "data": df.to_dict('records')
        }

        return {
            "document_id": document_id,
            "file_type": "csv",
            "page_count": 1,
            "full_text": full_text,
            "tables": [table_data],
            "has_tables": True,
            "has_charts": False,
            "metadata": {
                "row_count": len(df),
                "col_count": len(df.columns),
                "char_count": len(full_text)
            }
        }

    def _process_text(self, file_path: str, document_id: str) -> Dict:
        """Extract text from plain text or markdown file."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            full_text = f.read()

        return {
            "document_id": document_id,
            "file_type": "text",
            "page_count": 1,
            "full_text": full_text,
            "tables": [],
            "has_tables": False,
            "has_charts": False,
            "metadata": {
                "line_count": full_text.count('\n') + 1,
                "char_count": len(full_text)
            }
        }

    def chunk_text(
        self,
        text: str,
        chunk_size: int = 800,
        chunk_overlap: int = 200,
        document_id: str = None,
        document_type: str = None,
        metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Split text into chunks for vector search and RAG.

        Args:
            text: Full text to chunk
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks
            document_id: Document identifier
            document_type: Document classification
            metadata: Additional metadata to include

        Returns:
            List of chunk dicts
        """
        if not text or len(text) < chunk_size:
            return [{
                "chunk_id": str(uuid.uuid4()),
                "document_id": document_id,
                "text": text,
                "chunk_index": 0,
                "document_type": document_type,
                **(metadata or {})
            }]

        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            # Extract chunk
            end = start + chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings near the end of chunk
                sentence_ends = ['. ', '.\n', '! ', '!\n', '? ', '?\n']
                best_break = end

                for i in range(max(end - 100, start), min(end + 100, len(text))):
                    if any(text[i:i+2] == se for se in sentence_ends):
                        best_break = i + 1
                        break

                end = best_break

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append({
                    "chunk_id": str(uuid.uuid4()),
                    "document_id": document_id,
                    "text": chunk_text,
                    "chunk_index": chunk_index,
                    "document_type": document_type,
                    "char_count": len(chunk_text),
                    **(metadata or {})
                })

            # Move to next chunk with overlap
            start = end - chunk_overlap
            chunk_index += 1

            # Safety check to prevent infinite loops
            if chunk_index > 1000:
                print(f"Warning: Excessive chunks ({chunk_index}) for document {document_id}")
                break

        return chunks


# Convenience functions
def process_document(file_path: str, document_id: str) -> Dict:
    """Process a single document."""
    processor = DocumentProcessor()
    return processor.process_document(file_path, document_id)


def chunk_document(
    file_path: str,
    document_id: str,
    document_type: str = None,
    chunk_size: int = 800,
    chunk_overlap: int = 200
) -> List[Dict]:
    """
    Process document and return chunks ready for vector indexing.

    Args:
        file_path: Path to document
        document_id: Document ID
        document_type: Document classification
        chunk_size: Chunk size in characters
        chunk_overlap: Overlap between chunks

    Returns:
        List of document chunks
    """
    processor = DocumentProcessor()

    # Process document
    result = processor.process_document(file_path, document_id)

    if not result.get("success"):
        print(f"Error processing {file_path}: {result.get('error')}")
        return []

    # Extract text
    full_text = result.get("full_text", "")

    # Chunk text
    chunks = processor.chunk_text(
        text=full_text,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        document_id=document_id,
        document_type=document_type,
        metadata={
            "page_count": result.get("page_count", 0),
            "has_tables": result.get("has_tables", False)
        }
    )

    return chunks
