"""
Document ingestion module for downloading, classifying, and storing documents.

Supports:
- Downloading from web URLs (PDFs, Word docs, Excel files)
- Reading from local folders
- Automatic document classification
- Upload to Databricks storage (DBFS or Unity Catalog Volumes)
- Registration in Delta tables
"""

import os
import uuid
import hashlib
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, unquote
import shutil

from .document_classifier import classify_document


class DocumentIngestion:
    """Handle document ingestion from various sources."""

    def __init__(
        self,
        storage_path: str = "/Volumes/yasamin_tari/dataroom/raw",
        spark_session=None,
        catalog: str = "yasamin_tari",
        schema: str = "dataroom"
    ):
        """
        Initialize document ingestion.

        Args:
            storage_path: Base path for document storage (DBFS or Volume path)
            spark_session: PySpark session for Delta table operations
            catalog: Unity Catalog name
            schema: Schema/database name
        """
        self.storage_path = storage_path
        self.spark = spark_session
        self.catalog = catalog
        self.schema = schema

        # Create storage directory if not exists
        os.makedirs(storage_path, exist_ok=True)

    def download_from_url(self, url: str, company_id: str) -> Optional[Dict]:
        """
        Download document from URL and store it.

        Args:
            url: Document URL
            company_id: Company identifier

        Returns:
            Document metadata dict or None if failed
        """
        try:
            # Download file
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            # Extract filename from URL or Content-Disposition header
            filename = self._extract_filename_from_url(url, response.headers)

            # Save file
            file_path, doc_id = self._save_file(
                response.content,
                filename,
                company_id
            )

            # Get file metadata
            file_size = os.path.getsize(file_path)
            file_type = Path(filename).suffix.lower()

            # Classify document
            doc_type, confidence = classify_document(
                filename=filename,
                file_path=file_path
            )

            # Create document metadata
            doc_metadata = {
                "document_id": doc_id,
                "company_id": company_id,
                "filename": filename,
                "file_path": file_path,
                "file_type": file_type,
                "file_size_bytes": file_size,
                "document_type": doc_type,
                "classification_confidence": confidence,
                "source_url": url,
                "uploaded_at": datetime.utcnow(),
                "processed": False
            }

            print(f"✓ Downloaded: {filename} ({doc_type}, {confidence:.2f})")
            return doc_metadata

        except Exception as e:
            print(f"✗ Failed to download {url}: {e}")
            return None

    def ingest_from_folder(
        self,
        folder_path: str,
        company_id: str,
        recursive: bool = True
    ) -> List[Dict]:
        """
        Ingest documents from a local folder structure.

        Args:
            folder_path: Path to folder containing documents
            company_id: Company identifier
            recursive: Whether to traverse subfolders

        Returns:
            List of document metadata dicts
        """
        documents = []
        folder = Path(folder_path)

        if not folder.exists():
            print(f"✗ Folder not found: {folder_path}")
            return documents

        # Supported file extensions
        supported_extensions = {
            ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv",
            ".pptx", ".ppt", ".txt", ".md"
        }

        # Find all documents
        pattern = "**/*" if recursive else "*"
        for file_path in folder.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                doc_metadata = self._ingest_local_file(file_path, company_id, folder_path)
                if doc_metadata:
                    documents.append(doc_metadata)

        print(f"✓ Ingested {len(documents)} documents from {folder_path}")
        return documents

    def _ingest_local_file(
        self,
        file_path: Path,
        company_id: str,
        base_folder: str
    ) -> Optional[Dict]:
        """Ingest a single local file."""
        try:
            # Read file
            with open(file_path, 'rb') as f:
                content = f.read()

            # Get relative path for classification (preserves folder structure)
            relative_path = str(file_path.relative_to(base_folder))

            # Save to storage
            storage_path, doc_id = self._save_file(
                content,
                file_path.name,
                company_id,
                relative_path=relative_path
            )

            # Get file metadata
            file_size = len(content)
            file_type = file_path.suffix.lower()

            # Classify document using folder structure
            doc_type, confidence = classify_document(
                filename=file_path.name,
                file_path=relative_path  # Use relative path for folder-based classification
            )

            # Create document metadata
            doc_metadata = {
                "document_id": doc_id,
                "company_id": company_id,
                "filename": file_path.name,
                "file_path": storage_path,
                "file_type": file_type,
                "file_size_bytes": file_size,
                "document_type": doc_type,
                "classification_confidence": confidence,
                "uploaded_at": datetime.utcnow(),
                "processed": False,
                "original_path": str(file_path),
                "relative_path": relative_path
            }

            print(f"✓ Ingested: {relative_path} ({doc_type}, {confidence:.2f})")
            return doc_metadata

        except Exception as e:
            print(f"✗ Failed to ingest {file_path}: {e}")
            return None

    def _save_file(
        self,
        content: bytes,
        filename: str,
        company_id: str,
        relative_path: str = None
    ) -> Tuple[str, str]:
        """
        Save file to storage and return path and document ID.

        Args:
            content: File content bytes
            filename: Original filename
            company_id: Company ID
            relative_path: Optional relative path to preserve folder structure

        Returns:
            Tuple of (storage_path, document_id)
        """
        # Generate unique document ID
        doc_id = str(uuid.uuid4())

        # Create company folder
        company_folder = os.path.join(self.storage_path, company_id)
        os.makedirs(company_folder, exist_ok=True)

        # Preserve folder structure if relative_path is provided
        if relative_path:
            # Create subfolder structure
            subfolder = os.path.dirname(relative_path)
            if subfolder:
                full_folder = os.path.join(company_folder, subfolder)
                os.makedirs(full_folder, exist_ok=True)
                file_path = os.path.join(full_folder, filename)
            else:
                file_path = os.path.join(company_folder, filename)
        else:
            file_path = os.path.join(company_folder, filename)

        # Handle duplicate filenames
        if os.path.exists(file_path):
            base, ext = os.path.splitext(filename)
            file_path = os.path.join(
                os.path.dirname(file_path),
                f"{base}_{doc_id[:8]}{ext}"
            )

        # Write file
        with open(file_path, 'wb') as f:
            f.write(content)

        return file_path, doc_id

    def _extract_filename_from_url(self, url: str, headers: Dict) -> str:
        """Extract filename from URL or Content-Disposition header."""
        # Try Content-Disposition header first
        content_disp = headers.get('Content-Disposition', '')
        if 'filename=' in content_disp:
            filename = content_disp.split('filename=')[-1].strip('"\'')
            return unquote(filename)

        # Extract from URL
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)

        if filename:
            return unquote(filename)

        # Fallback to generic name
        return f"document_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"

    def register_documents_in_delta(self, documents: List[Dict]) -> int:
        """
        Register documents in Delta table.

        Args:
            documents: List of document metadata dicts

        Returns:
            Number of documents registered
        """
        if not self.spark or not documents:
            return 0

        try:
            from pyspark.sql import Row

            # Convert to DataFrame
            rows = [Row(**doc) for doc in documents]
            df = self.spark.createDataFrame(rows)

            # Write to Delta table
            table_name = f"{self.catalog}.{self.schema}.documents"
            df.write.format("delta").mode("append").saveAsTable(table_name)

            print(f"✓ Registered {len(documents)} documents in {table_name}")
            return len(documents)

        except Exception as e:
            print(f"✗ Failed to register documents in Delta: {e}")
            return 0

    def register_company(self, company_id: str, company_name: str, **kwargs) -> bool:
        """
        Register company in Delta table.

        Args:
            company_id: Unique company identifier
            company_name: Company name
            **kwargs: Additional company metadata (industry, stage, etc.)

        Returns:
            True if successful
        """
        if not self.spark:
            return False

        try:
            from pyspark.sql import Row

            company_data = {
                "company_id": company_id,
                "name": company_name,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "total_documents": 0,
                **kwargs
            }

            # Create DataFrame
            df = self.spark.createDataFrame([Row(**company_data)])

            # Write to Delta table (merge to avoid duplicates)
            table_name = f"{self.catalog}.{self.schema}.companies"
            df.write.format("delta").mode("append").saveAsTable(table_name)

            print(f"✓ Registered company: {company_name} ({company_id})")
            return True

        except Exception as e:
            print(f"✗ Failed to register company: {e}")
            return False

    def ingest_company_folder(
        self,
        company_name: str,
        folder_path: str,
        company_metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Ingest an entire company's document folder.

        Args:
            company_name: Company name
            folder_path: Path to company's document folder
            company_metadata: Optional additional company metadata

        Returns:
            Dict with ingestion summary
        """
        # Generate company ID
        company_id = hashlib.md5(company_name.encode()).hexdigest()[:16]

        # Register company
        metadata = company_metadata or {}
        self.register_company(company_id, company_name, **metadata)

        # Ingest documents
        documents = self.ingest_from_folder(folder_path, company_id, recursive=True)

        # Register documents in Delta
        registered = self.register_documents_in_delta(documents)

        summary = {
            "company_id": company_id,
            "company_name": company_name,
            "documents_found": len(documents),
            "documents_registered": registered,
            "document_types": self._count_document_types(documents)
        }

        return summary

    def _count_document_types(self, documents: List[Dict]) -> Dict[str, int]:
        """Count documents by type."""
        type_counts = {}
        for doc in documents:
            doc_type = doc.get("document_type", "other")
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
        return type_counts


# Convenience functions
def ingest_company_from_folder(
    company_name: str,
    folder_path: str,
    storage_path: str = "/Volumes/yasamin_tari/dataroom/raw",
    spark_session=None,
    company_metadata: Optional[Dict] = None
) -> Dict:
    """
    Convenience function to ingest a company's documents from a folder.

    Args:
        company_name: Company name
        folder_path: Path to company's document folder
        storage_path: Databricks storage path
        spark_session: PySpark session
        company_metadata: Optional company metadata

    Returns:
        Ingestion summary dict
    """
    ingestion = DocumentIngestion(storage_path, spark_session)
    return ingestion.ingest_company_folder(company_name, folder_path, company_metadata)


def download_documents_from_urls(
    company_id: str,
    urls: List[str],
    storage_path: str = "/Volumes/yasamin_tari/dataroom/raw",
    spark_session=None
) -> List[Dict]:
    """
    Download multiple documents from URLs.

    Args:
        company_id: Company identifier
        urls: List of document URLs
        storage_path: Databricks storage path
        spark_session: PySpark session

    Returns:
        List of document metadata dicts
    """
    ingestion = DocumentIngestion(storage_path, spark_session)
    documents = []

    for url in urls:
        doc = ingestion.download_from_url(url, company_id)
        if doc:
            documents.append(doc)

    # Register in Delta
    ingestion.register_documents_in_delta(documents)

    return documents
