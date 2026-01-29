"""Pydantic schemas for policy extraction API."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# Request schemas
class PolicyExtractionUploadRequest(BaseModel):
    """Request schema for uploading and extracting PDF."""

    enhance: bool = Field(default=True, description="Whether to enhance extraction")
    validate_extraction: bool = Field(default=True, description="Whether to validate extraction")


# Nested schemas for extracted data
class ExtractedLender(BaseModel):
    """Schema for extracted lender information."""

    name: str
    description: str = ""
    min_loan_amount: float
    max_loan_amount: float
    excluded_states: list[str] = Field(default_factory=list)
    excluded_industries: list[str] = Field(default_factory=list)


class RateTable(BaseModel):
    """Schema for rate table entry."""

    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    min_term: Optional[int] = None
    max_term: Optional[int] = None
    rate: float


class RateAdjustment(BaseModel):
    """Schema for rate adjustment."""

    condition: str
    delta: float
    description: str = ""


class RateMetadata(BaseModel):
    """Schema for rate metadata."""

    base_rates: list[RateTable] = Field(default_factory=list)
    adjustments: list[RateAdjustment] = Field(default_factory=list)


class ExtractedRule(BaseModel):
    """Schema for extracted rule."""

    rule_type: str
    rule_name: str
    criteria: dict[str, Any]
    weight: float = 1.0
    is_mandatory: bool = True


class ExtractedProgram(BaseModel):
    """Schema for extracted program."""

    program_name: str
    program_code: str
    credit_tier: str
    min_fit_score: float = 60.0
    description: str = ""
    eligibility_conditions: dict[str, Any] = Field(default_factory=dict)
    rate_metadata: RateMetadata = Field(default_factory=RateMetadata)
    rules: list[ExtractedRule] = Field(default_factory=list)


class ExtractedPolicyData(BaseModel):
    """Schema for complete extracted policy data."""

    lender: ExtractedLender
    programs: list[ExtractedProgram]


# Validation schemas
class ValidationError(BaseModel):
    """Schema for validation error."""

    field: str
    message: str
    severity: str = Field(pattern="^(error|warning)$")


class ValidationResult(BaseModel):
    """Schema for validation result."""

    valid: bool
    errors: list[ValidationError] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


# Extraction result schemas
class ExtractionMetadata(BaseModel):
    """Schema for extraction metadata."""

    pdf_characters: int
    programs_count: int
    total_rules: int
    enhanced: bool
    validated: bool


class PDFMetadata(BaseModel):
    """Schema for PDF metadata."""

    title: str = ""
    author: str = ""
    subject: str = ""
    creator: str = ""
    producer: str = ""
    creation_date: str = ""
    modification_date: str = ""
    page_count: int


class ExtractionResult(BaseModel):
    """Schema for extraction result."""

    extraction_id: UUID = Field(default_factory=uuid4)
    status: str
    pdf_filename: str
    pdf_metadata: Optional[PDFMetadata] = None
    extracted_data: Optional[ExtractedPolicyData] = None
    validation: Optional[ValidationResult] = None
    extraction_metadata: Optional[ExtractionMetadata] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Update schemas
class UpdateExtractedLenderRequest(BaseModel):
    """Request schema for updating extracted lender."""

    name: Optional[str] = None
    description: Optional[str] = None
    min_loan_amount: Optional[float] = None
    max_loan_amount: Optional[float] = None
    excluded_states: Optional[list[str]] = None
    excluded_industries: Optional[list[str]] = None


class UpdateExtractedRuleRequest(BaseModel):
    """Request schema for updating extracted rule."""

    rule_type: Optional[str] = None
    rule_name: Optional[str] = None
    criteria: Optional[dict[str, Any]] = None
    weight: Optional[float] = None
    is_mandatory: Optional[bool] = None


class UpdateExtractedProgramRequest(BaseModel):
    """Request schema for updating extracted program."""

    program_name: Optional[str] = None
    program_code: Optional[str] = None
    credit_tier: Optional[str] = None
    min_fit_score: Optional[float] = None
    description: Optional[str] = None
    eligibility_conditions: Optional[dict[str, Any]] = None
    rate_metadata: Optional[RateMetadata] = None
    rules: Optional[list[ExtractedRule]] = None


class UpdateExtractionRequest(BaseModel):
    """Request schema for updating extraction."""

    lender: Optional[UpdateExtractedLenderRequest] = None
    programs: Optional[list[ExtractedProgram]] = None


# Response schemas
class ExtractionListItem(BaseModel):
    """Schema for extraction list item."""

    extraction_id: UUID
    pdf_filename: str
    status: str
    lender_name: Optional[str] = None
    programs_count: int = 0
    created_at: datetime
    approved: bool = False


class ExtractionListResponse(BaseModel):
    """Response schema for listing extractions."""

    extractions: list[ExtractionListItem]
    total: int


class ApprovalResponse(BaseModel):
    """Response schema for approval."""

    success: bool
    message: str
    lender_id: Optional[UUID] = None
    program_ids: list[UUID] = Field(default_factory=list)
