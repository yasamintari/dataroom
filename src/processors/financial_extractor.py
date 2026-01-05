"""
Financial data extraction from documents.

Extracts structured financial metrics:
- Revenue, growth rates
- Profitability metrics (margins, EBITDA)
- Cash metrics (burn rate, runway)
- Unit economics (CAC, LTV)
- Other KPIs

Uses:
- Table parsing for structured data
- LLM-based extraction for unstructured text
- Pattern matching for common financial terms
"""

import re
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd


class FinancialExtractor:
    """Extract financial metrics from documents."""

    def __init__(self, llm_client=None):
        """
        Initialize financial extractor.

        Args:
            llm_client: Optional LLM client for intelligent extraction
        """
        self.llm_client = llm_client

        # Financial term patterns (regex)
        self.patterns = {
            "revenue": r"(?:revenue|sales|top\s+line)[\s:]+\$?([\d,]+(?:\.\d+)?)\s*([KMB])?",
            "burn_rate": r"(?:burn\s+rate|monthly\s+burn)[\s:]+\$?([\d,]+(?:\.\d+)?)\s*([KMB])?",
            "runway": r"(?:runway)[\s:]+(\d+(?:\.\d+)?)\s*(months?|years?)",
            "cash": r"(?:cash\s+balance|cash\s+on\s+hand)[\s:]+\$?([\d,]+(?:\.\d+)?)\s*([KMB])?",
            "gross_margin": r"(?:gross\s+margin)[\s:]+(\d+(?:\.\d+)?)\s*%",
            "cac": r"(?:CAC|customer\s+acquisition\s+cost)[\s:]+\$?([\d,]+(?:\.\d+)?)",
            "ltv": r"(?:LTV|lifetime\s+value)[\s:]+\$?([\d,]+(?:\.\d+)?)",
        }

    def extract_from_tables(
        self,
        tables: List[Dict],
        document_id: str,
        company_id: str
    ) -> List[Dict]:
        """
        Extract financial metrics from structured tables.

        Args:
            tables: List of table dicts from document processor
            document_id: Source document ID
            company_id: Company ID

        Returns:
            List of financial metric records
        """
        metrics = []

        for table in tables:
            # Convert table to DataFrame for easier processing
            table_data = table.get("data", [])
            if not table_data or len(table_data) < 2:
                continue

            try:
                df = pd.DataFrame(table_data[1:], columns=table_data[0])
                df_metrics = self._extract_from_dataframe(df, document_id, company_id)
                metrics.extend(df_metrics)

            except Exception as e:
                print(f"Warning: Failed to parse table in {document_id}: {e}")
                continue

        return metrics

    def _extract_from_dataframe(
        self,
        df: pd.DataFrame,
        document_id: str,
        company_id: str
    ) -> List[Dict]:
        """Extract metrics from a pandas DataFrame."""
        metrics = []

        # Detect financial statement type
        columns_lower = [str(c).lower() for c in df.columns]

        # Look for time period columns (Q1 2024, FY23, etc.)
        period_columns = self._detect_period_columns(df.columns)

        # Look for metric rows
        if not df.empty:
            # Try to find revenue row
            for idx, row in df.iterrows():
                row_label = str(row.iloc[0]).lower() if len(row) > 0 else ""

                # Check if this row contains a financial metric
                metric_type = self._classify_metric_row(row_label)

                if metric_type:
                    # Extract values for each period
                    for period_col in period_columns:
                        try:
                            value = self._parse_financial_value(row[period_col])

                            if value is not None:
                                metric_record = {
                                    "metric_id": f"{document_id}_{idx}_{period_col}",
                                    "company_id": company_id,
                                    "document_id": document_id,
                                    "period_start": period_col,
                                    "period_end": period_col,
                                    metric_type: value,
                                    "extracted_at": datetime.utcnow(),
                                    "confidence_score": 0.8
                                }
                                metrics.append(metric_record)

                        except Exception as e:
                            continue

        return metrics

    def _detect_period_columns(self, columns: List[str]) -> List[str]:
        """Detect columns that represent time periods."""
        period_patterns = [
            r"Q[1-4]\s*\d{4}",  # Q1 2024
            r"FY\s*\d{2,4}",     # FY24, FY2024
            r"\d{4}",            # 2024
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*\d{4}",
            r"YTD",
            r"TTM"
        ]

        period_columns = []
        for col in columns:
            col_str = str(col)
            for pattern in period_patterns:
                if re.search(pattern, col_str, re.IGNORECASE):
                    period_columns.append(col)
                    break

        return period_columns

    def _classify_metric_row(self, row_label: str) -> Optional[str]:
        """Classify what type of financial metric this row represents."""
        classifications = {
            "revenue": ["revenue", "sales", "top line", "total revenue", "arr", "mrr"],
            "gross_margin": ["gross margin", "gross profit margin", "gp margin"],
            "operating_margin": ["operating margin", "ebitda margin"],
            "net_income": ["net income", "net profit", "bottom line", "earnings"],
            "ebitda": ["ebitda", "adjusted ebitda"],
            "cash_balance": ["cash", "cash balance", "cash on hand", "cash & equivalents"],
            "burn_rate": ["burn rate", "monthly burn", "cash burn"],
            "headcount": ["headcount", "employees", "team size", "fte"],
            "active_users": ["active users", "mau", "dau", "users"],
        }

        for metric_type, keywords in classifications.items():
            for keyword in keywords:
                if keyword in row_label:
                    return metric_type

        return None

    def _parse_financial_value(self, value: Any) -> Optional[float]:
        """Parse a financial value from various formats."""
        if pd.isna(value):
            return None

        value_str = str(value).strip()

        # Remove currency symbols and commas
        value_str = value_str.replace("$", "").replace("€", "").replace("£", "")
        value_str = value_str.replace(",", "")
        value_str = value_str.replace("(", "-").replace(")", "")  # Negatives in parentheses

        # Handle percentage
        if "%" in value_str:
            value_str = value_str.replace("%", "")
            try:
                return float(value_str) / 100.0
            except:
                return None

        # Handle K, M, B suffixes
        multiplier = 1
        if value_str.endswith("K") or value_str.endswith("k"):
            multiplier = 1_000
            value_str = value_str[:-1]
        elif value_str.endswith("M") or value_str.endswith("m"):
            multiplier = 1_000_000
            value_str = value_str[:-1]
        elif value_str.endswith("B") or value_str.endswith("b"):
            multiplier = 1_000_000_000
            value_str = value_str[:-1]

        # Parse number
        try:
            return float(value_str) * multiplier
        except:
            return None

    def extract_from_text(
        self,
        text: str,
        document_id: str,
        company_id: str
    ) -> List[Dict]:
        """
        Extract financial metrics from unstructured text using patterns.

        Args:
            text: Document text
            document_id: Document ID
            company_id: Company ID

        Returns:
            List of financial metrics
        """
        metrics = []

        for metric_name, pattern in self.patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)

            for match in matches:
                try:
                    # Parse value
                    value_str = match.group(1).replace(",", "")
                    value = float(value_str)

                    # Apply multiplier if present
                    if match.lastindex >= 2 and match.group(2):
                        multiplier_map = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
                        multiplier = multiplier_map.get(match.group(2).upper(), 1)
                        value *= multiplier

                    # Create metric record
                    metric_record = {
                        "metric_id": f"{document_id}_{metric_name}",
                        "company_id": company_id,
                        "document_id": document_id,
                        metric_name: value,
                        "extracted_at": datetime.utcnow(),
                        "confidence_score": 0.6  # Lower confidence for text extraction
                    }
                    metrics.append(metric_record)

                except Exception as e:
                    continue

        return metrics

    def extract_with_llm(
        self,
        text: str,
        document_id: str,
        company_id: str
    ) -> List[Dict]:
        """
        Use LLM to extract financial metrics from text.

        Args:
            text: Document text
            document_id: Document ID
            company_id: Company ID

        Returns:
            List of financial metrics
        """
        if not self.llm_client:
            return []

        prompt = f"""Extract financial metrics from the following text. Return a JSON object with these fields (use null if not found):

{{
  "revenue": <number>,
  "revenue_growth_rate": <percentage as decimal>,
  "gross_margin": <percentage as decimal>,
  "operating_margin": <percentage as decimal>,
  "net_income": <number>,
  "ebitda": <number>,
  "cash_balance": <number>,
  "burn_rate": <monthly burn in dollars>,
  "runway_months": <number>,
  "cac": <customer acquisition cost>,
  "ltv": <lifetime value>,
  "headcount": <number of employees>,
  "active_users": <number>
}}

All monetary values should be in dollars (not K, M, B). Margins should be decimals (0.25 for 25%).

Text:
{text[:2000]}

JSON:"""

        try:
            response = self.llm_client.generate(prompt)
            # Parse JSON response
            import json
            data = json.loads(response)

            # Create metric record
            metric_record = {
                "metric_id": f"{document_id}_llm",
                "company_id": company_id,
                "document_id": document_id,
                "extracted_at": datetime.utcnow(),
                "confidence_score": 0.7,
                **{k: v for k, v in data.items() if v is not None}
            }

            return [metric_record] if any(v is not None for v in data.values()) else []

        except Exception as e:
            print(f"LLM extraction error: {e}")
            return []

    def calculate_derived_metrics(self, metrics: Dict) -> Dict:
        """Calculate derived metrics from extracted base metrics."""
        derived = {}

        # LTV/CAC ratio
        if metrics.get("ltv") and metrics.get("cac"):
            derived["ltv_cac_ratio"] = metrics["ltv"] / metrics["cac"]

        # Runway calculation
        if metrics.get("cash_balance") and metrics.get("burn_rate"):
            derived["runway_months"] = metrics["cash_balance"] / metrics["burn_rate"]

        # Revenue growth rate (if we have multiple periods)
        # This would require comparing different time periods

        return derived


# Convenience function
def extract_financial_metrics(
    processed_doc: Dict,
    document_id: str,
    company_id: str,
    llm_client=None
) -> List[Dict]:
    """
    Extract all financial metrics from a processed document.

    Args:
        processed_doc: Output from DocumentProcessor
        document_id: Document ID
        company_id: Company ID
        llm_client: Optional LLM client

    Returns:
        List of financial metric records
    """
    extractor = FinancialExtractor(llm_client)
    all_metrics = []

    # Extract from tables (highest confidence)
    if processed_doc.get("tables"):
        table_metrics = extractor.extract_from_tables(
            processed_doc["tables"],
            document_id,
            company_id
        )
        all_metrics.extend(table_metrics)

    # Extract from text (medium confidence)
    if processed_doc.get("full_text"):
        text_metrics = extractor.extract_from_text(
            processed_doc["full_text"],
            document_id,
            company_id
        )
        all_metrics.extend(text_metrics)

    # Extract with LLM (if available)
    if llm_client and processed_doc.get("full_text"):
        llm_metrics = extractor.extract_with_llm(
            processed_doc["full_text"],
            document_id,
            company_id
        )
        all_metrics.extend(llm_metrics)

    return all_metrics
