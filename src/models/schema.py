"""
Data models and schema definitions for the VC Data Room.

These models define the structure for:
- Company metadata
- Documents and their categorization
- Extracted financial metrics
- Analysis results
"""

from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Document category types"""
    FINANCIAL = "financial"
    PITCH_DECK = "pitch_deck"
    TECHNICAL = "technical"
    LEGAL = "legal"
    PRODUCT = "product"
    OTHER = "other"


class CompanyStage(str, Enum):
    """Company funding stage"""
    PRE_SEED = "pre_seed"
    SEED = "seed"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    SERIES_C_PLUS = "series_c_plus"
    GROWTH = "growth"


class InvestmentRecommendation(str, Enum):
    """Investment decision recommendation"""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    PASS = "pass"


# ==================== Company Model ====================
class Company(BaseModel):
    """Company entity with metadata"""
    company_id: str = Field(..., description="Unique company identifier")
    name: str = Field(..., description="Company name")
    industry: Optional[str] = Field(None, description="Industry/sector")
    stage: Optional[CompanyStage] = Field(None, description="Funding stage")
    founded_year: Optional[int] = Field(None, description="Year founded")
    headquarters: Optional[str] = Field(None, description="HQ location")
    website: Optional[str] = Field(None, description="Company website")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Summary fields (populated by analysis)
    total_documents: int = Field(default=0)
    last_analyzed: Optional[datetime] = None

    class Config:
        use_enum_values = True


# ==================== Document Model ====================
class Document(BaseModel):
    """Document metadata and classification"""
    document_id: str = Field(..., description="Unique document identifier")
    company_id: str = Field(..., description="Parent company ID")

    # File information
    filename: str = Field(..., description="Original filename")
    file_path: str = Field(..., description="Storage path (DBFS/Volume)")
    file_type: str = Field(..., description="File extension (.pdf, .xlsx, etc)")
    file_size_bytes: int = Field(..., description="File size")

    # Classification
    document_type: DocumentType = Field(..., description="Classified document type")
    classification_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    # Content metadata
    page_count: Optional[int] = None
    has_tables: bool = False
    has_charts: bool = False

    # Processing status
    processed: bool = False
    processing_error: Optional[str] = None

    # Timestamps
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


# ==================== Financial Metrics Model ====================
class FinancialMetrics(BaseModel):
    """Extracted financial metrics from documents"""
    metric_id: str = Field(..., description="Unique metric record ID")
    company_id: str = Field(..., description="Company ID")
    document_id: str = Field(..., description="Source document ID")

    # Time period
    period_start: Optional[str] = None  # e.g., "2023-Q1" or "2023"
    period_end: Optional[str] = None

    # Revenue metrics
    revenue: Optional[float] = None
    revenue_growth_rate: Optional[float] = None
    recurring_revenue: Optional[float] = None

    # Profitability
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_income: Optional[float] = None
    ebitda: Optional[float] = None

    # Cash metrics
    cash_balance: Optional[float] = None
    burn_rate: Optional[float] = None
    runway_months: Optional[float] = None

    # Unit economics
    cac: Optional[float] = None  # Customer Acquisition Cost
    ltv: Optional[float] = None  # Lifetime Value
    ltv_cac_ratio: Optional[float] = None

    # Other metrics
    headcount: Optional[int] = None
    active_users: Optional[int] = None

    # Metadata
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    confidence_score: float = Field(default=0.0)


# ==================== Document Chunk Model (for RAG) ====================
class DocumentChunk(BaseModel):
    """Text chunks for vector search and RAG"""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    company_id: str = Field(..., description="Company ID")
    document_id: str = Field(..., description="Source document ID")

    # Content
    text: str = Field(..., description="Chunk text content")
    chunk_index: int = Field(..., description="Position in document")

    # Metadata for retrieval
    document_type: DocumentType
    page_number: Optional[int] = None
    section_title: Optional[str] = None

    # Vector embedding (stored separately in vector DB)
    # embedding: List[float]  # Handled by Databricks Vector Search

    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


# ==================== Analysis Result Model ====================
class AnalysisDimension(BaseModel):
    """Individual analysis dimension score and reasoning"""
    dimension: str = Field(..., description="Analysis dimension name")
    score: float = Field(..., ge=0.0, le=10.0, description="Score out of 10")
    reasoning: str = Field(..., description="Explanation for the score")
    key_findings: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)


class InvestmentAnalysis(BaseModel):
    """Complete investment analysis for a company"""
    analysis_id: str = Field(..., description="Unique analysis ID")
    company_id: str = Field(..., description="Company ID")

    # Overall assessment
    overall_score: float = Field(..., ge=0.0, le=10.0)
    recommendation: InvestmentRecommendation
    confidence_level: float = Field(..., ge=0.0, le=1.0)

    # Dimension scores
    dimensions: List[AnalysisDimension] = Field(default_factory=list)

    # Investment memo
    executive_summary: str = Field(..., description="High-level summary")
    market_analysis: str = Field(default="")
    competitive_moat: str = Field(default="")
    team_assessment: str = Field(default="")
    financial_analysis: str = Field(default="")
    key_risks: List[str] = Field(default_factory=list)
    key_opportunities: List[str] = Field(default_factory=list)

    # Recommendations
    suggested_investment_amount: Optional[float] = None
    suggested_valuation: Optional[float] = None
    next_steps: List[str] = Field(default_factory=list)

    # Metadata
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    analyzed_by: str = Field(default="system")
    documents_analyzed: int = Field(default=0)

    class Config:
        use_enum_values = True


# ==================== Delta Table Schemas (for Spark) ====================

# These are the schemas for Delta tables in Databricks
DELTA_SCHEMAS = {
    "companies": """
        company_id STRING,
        name STRING,
        industry STRING,
        stage STRING,
        founded_year INT,
        headquarters STRING,
        website STRING,
        created_at TIMESTAMP,
        updated_at TIMESTAMP,
        total_documents INT,
        last_analyzed TIMESTAMP
    """,

    "documents": """
        document_id STRING,
        company_id STRING,
        filename STRING,
        file_path STRING,
        file_type STRING,
        file_size_bytes BIGINT,
        document_type STRING,
        classification_confidence FLOAT,
        page_count INT,
        has_tables BOOLEAN,
        has_charts BOOLEAN,
        processed BOOLEAN,
        processing_error STRING,
        uploaded_at TIMESTAMP,
        processed_at TIMESTAMP
    """,

    "financial_metrics": """
        metric_id STRING,
        company_id STRING,
        document_id STRING,
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
    """,

    "document_chunks": """
        chunk_id STRING,
        company_id STRING,
        document_id STRING,
        text STRING,
        chunk_index INT,
        document_type STRING,
        page_number INT,
        section_title STRING,
        created_at TIMESTAMP
    """,

    "investment_analysis": """
        analysis_id STRING,
        company_id STRING,
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
    """
}
