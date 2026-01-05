"""
Document type classification using keyword matching and LLM-based classification.

Automatically categorizes documents into:
- Financial documents (P&L, balance sheets, etc.)
- Pitch decks
- Technical documentation
- Legal documents
- Product documents
- Other
"""

import os
import re
from typing import Dict, Tuple
from pathlib import Path

# Document type keywords from config
DOCUMENT_TYPE_KEYWORDS = {
    "financial": {
        "keywords": [
            "financial", "p&l", "profit", "loss", "balance sheet",
            "cash flow", "income statement", "revenue", "expenses",
            "quarterly", "annual report", "10-k", "10-q", "budget",
            "forecast", "projection", "cap table", "capitalization"
        ],
        "extensions": [".xlsx", ".xls", ".csv"]
    },
    "pitch_deck": {
        "keywords": [
            "pitch", "deck", "presentation", "overview",
            "company presentation", "investor deck", "fundraising",
            "series a", "series b", "seed round", "investment opportunity"
        ],
        "extensions": [".pdf", ".pptx", ".ppt"]
    },
    "technical": {
        "keywords": [
            "technical", "architecture", "system design", "api",
            "documentation", "engineering", "infrastructure", "tech stack",
            "scalability", "database", "backend", "frontend", "devops"
        ],
        "extensions": [".pdf", ".md", ".docx", ".doc"]
    },
    "legal": {
        "keywords": [
            "legal", "contract", "agreement", "terms", "cap table",
            "incorporation", "shareholder", "term sheet", "nda",
            "confidentiality", "intellectual property", "patent",
            "license", "compliance"
        ],
        "extensions": [".pdf", ".docx", ".doc"]
    },
    "product": {
        "keywords": [
            "product", "roadmap", "features", "user", "customer",
            "requirements", "specification", "user story", "backlog",
            "product brief", "market fit", "mvp"
        ],
        "extensions": [".pdf", ".docx", ".doc", ".md"]
    }
}


class DocumentClassifier:
    """Classify documents by type using filename, path, and content analysis."""

    def __init__(self, llm_client=None):
        """
        Initialize document classifier.

        Args:
            llm_client: Optional LLM client for content-based classification
        """
        self.llm_client = llm_client
        self.keyword_config = DOCUMENT_TYPE_KEYWORDS

    def classify_from_filename(self, filename: str, file_path: str = None) -> Tuple[str, float]:
        """
        Classify document based on filename and path.

        Args:
            filename: Document filename
            file_path: Full file path (optional, for folder-based classification)

        Returns:
            Tuple of (document_type, confidence_score)
        """
        filename_lower = filename.lower()
        path_lower = file_path.lower() if file_path else ""
        file_ext = Path(filename).suffix.lower()

        # Score each document type
        scores = {}

        for doc_type, config in self.keyword_config.items():
            score = 0.0

            # Check keywords in filename and path
            for keyword in config["keywords"]:
                if keyword in filename_lower:
                    score += 0.3  # Filename match is strong signal
                if keyword in path_lower:
                    score += 0.2  # Path match is moderate signal

            # Check file extension
            if file_ext in config["extensions"]:
                score += 0.1  # Extension match is weak signal

            scores[doc_type] = min(score, 1.0)  # Cap at 1.0

        # Get highest scoring type
        if scores and max(scores.values()) > 0:
            best_type = max(scores, key=scores.get)
            confidence = scores[best_type]
            return best_type, confidence
        else:
            return "other", 0.0

    def classify_from_content(self, content_preview: str, filename: str) -> Tuple[str, float]:
        """
        Classify document using content analysis with LLM.

        Args:
            content_preview: First page or preview of document content
            filename: Document filename for context

        Returns:
            Tuple of (document_type, confidence_score)
        """
        if not self.llm_client:
            # Fallback to keyword matching in content
            return self._classify_content_keywords(content_preview)

        # Use LLM for classification
        prompt = f"""Classify this document into one of these categories:
- financial: Financial statements, P&L, balance sheets, cash flow, budgets
- pitch_deck: Investor pitch deck or company presentation
- technical: Technical documentation, architecture, engineering docs
- legal: Legal contracts, agreements, terms, IP documents
- product: Product specifications, roadmaps, requirements
- other: If it doesn't fit the above categories

Filename: {filename}

Content preview:
{content_preview[:1000]}

Respond with ONLY the category name (one word)."""

        try:
            response = self.llm_client.generate(prompt)
            doc_type = response.strip().lower().replace("_", " ")

            # Map variations to standard types
            type_mapping = {
                "financial": "financial",
                "pitch deck": "pitch_deck",
                "pitch": "pitch_deck",
                "technical": "technical",
                "legal": "legal",
                "product": "product",
            }

            doc_type = type_mapping.get(doc_type, "other")
            return doc_type, 0.8  # High confidence for LLM classification

        except Exception as e:
            print(f"LLM classification error: {e}")
            return self._classify_content_keywords(content_preview)

    def _classify_content_keywords(self, content: str) -> Tuple[str, float]:
        """Fallback keyword matching in content."""
        content_lower = content.lower()
        scores = {}

        for doc_type, config in self.keyword_config.items():
            score = 0.0
            keyword_matches = 0

            for keyword in config["keywords"]:
                if keyword in content_lower:
                    keyword_matches += 1

            # Score based on keyword density
            if keyword_matches > 0:
                score = min(keyword_matches * 0.15, 1.0)

            scores[doc_type] = score

        if scores and max(scores.values()) > 0:
            best_type = max(scores, key=scores.get)
            confidence = scores[best_type]
            return best_type, confidence
        else:
            return "other", 0.0

    def classify_folder_structure(self, file_path: str) -> Tuple[str, float]:
        """
        Classify based on folder structure (e.g., /financials/Q1_2024.pdf).

        Args:
            file_path: Full file path with folders

        Returns:
            Tuple of (document_type, confidence_score)
        """
        path_parts = Path(file_path).parts
        path_lower = [p.lower() for p in path_parts]

        # Check if any folder name matches a document type
        for doc_type in self.keyword_config.keys():
            # Check for plural and variations
            variations = [doc_type, doc_type + "s", doc_type.replace("_", " ")]

            for variation in variations:
                if any(variation in part for part in path_lower):
                    return doc_type, 0.9  # High confidence for folder-based classification

        return "other", 0.0

    def classify(
        self,
        filename: str,
        file_path: str = None,
        content_preview: str = None
    ) -> Tuple[str, float]:
        """
        Classify document using multiple signals (filename, path, content).

        Args:
            filename: Document filename
            file_path: Full file path (optional)
            content_preview: Preview of document content (optional)

        Returns:
            Tuple of (document_type, confidence_score)
        """
        classifications = []

        # 1. Folder structure classification (highest confidence)
        if file_path:
            folder_type, folder_conf = self.classify_folder_structure(file_path)
            if folder_conf > 0.5:
                classifications.append((folder_type, folder_conf, 0.4))  # 40% weight

        # 2. Filename classification
        filename_type, filename_conf = self.classify_from_filename(filename, file_path)
        classifications.append((filename_type, filename_conf, 0.3))  # 30% weight

        # 3. Content classification (if available)
        if content_preview:
            content_type, content_conf = self.classify_from_content(content_preview, filename)
            classifications.append((content_type, content_conf, 0.3))  # 30% weight

        # Weighted voting
        type_scores = {}
        for doc_type, confidence, weight in classifications:
            if doc_type not in type_scores:
                type_scores[doc_type] = 0
            type_scores[doc_type] += confidence * weight

        if type_scores:
            best_type = max(type_scores, key=type_scores.get)
            final_confidence = min(type_scores[best_type], 1.0)
            return best_type, final_confidence
        else:
            return "other", 0.0


# Convenience function
def classify_document(
    filename: str,
    file_path: str = None,
    content_preview: str = None,
    llm_client=None
) -> Tuple[str, float]:
    """
    Classify a document and return its type and confidence.

    Args:
        filename: Document filename
        file_path: Full path including folders
        content_preview: Optional content preview for better classification
        llm_client: Optional LLM client for content analysis

    Returns:
        Tuple of (document_type, confidence_score)
    """
    classifier = DocumentClassifier(llm_client)
    return classifier.classify(filename, file_path, content_preview)
