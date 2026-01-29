"""Pydantic schemas for match result and underwriting-related entities."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import UnderwritingStatus


# ==================== Underwriting Run Schemas ====================


class UnderwritingRunCreate(BaseModel):
    """Schema for creating an underwriting run."""

    application_id: UUID


class UnderwritingRunBase(BaseModel):
    """Base schema for underwriting run."""

    application_id: UUID
    status: UnderwritingStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_lenders_evaluated: int = 0
    total_programs_evaluated: int = 0
    matched_count: int = 0
    rejected_count: int = 0
    error_message: Optional[str] = None
    meta: Optional[dict[str, Any]] = Field(default_factory=dict)


class UnderwritingRunResponse(UnderwritingRunBase):
    """Schema for underwriting run response."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UnderwritingRunDetailResponse(UnderwritingRunResponse):
    """Schema for underwriting run with match results."""

    match_results: list["MatchResultResponse"] = []

    model_config = ConfigDict(from_attributes=True)


# ==================== Rule Evaluation Schemas ====================


class RuleEvaluationBase(BaseModel):
    """Base schema for rule evaluation."""

    rule_id: Optional[UUID] = None
    rule_name: str
    rule_type: str
    passed: bool
    score: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    weight: Decimal = Field(default=Decimal("1.00"), ge=0)
    is_mandatory: bool
    reason: Optional[str] = None
    evidence: Optional[dict[str, Any]] = Field(default_factory=dict)


class RuleEvaluationResponse(RuleEvaluationBase):
    """Schema for rule evaluation response."""

    id: UUID
    match_result_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== Match Result Schemas ====================


class MatchResultBase(BaseModel):
    """Base schema for match result."""

    lender_id: UUID
    program_id: Optional[UUID] = None
    is_eligible: bool
    fit_score: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    rejection_reason: Optional[str] = None
    rejection_tier: Optional[int] = Field(None, ge=1, le=3, description="Tier that rejected (1, 2, or 3)")
    estimated_rate: Optional[Decimal] = Field(None, ge=0, description="Interest rate percentage")
    estimated_monthly_payment: Optional[Decimal] = Field(None, ge=0)
    approval_probability: Optional[Decimal] = Field(None, ge=0, le=100)
    total_rules_evaluated: int = 0
    rules_passed: int = 0
    rules_failed: int = 0
    mandatory_rules_passed: bool = False
    meta: Optional[dict[str, Any]] = Field(default_factory=dict)


class MatchResultResponse(MatchResultBase):
    """Schema for match result response."""

    id: UUID
    underwriting_run_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MatchResultDetailResponse(MatchResultResponse):
    """Schema for match result with rule evaluations and lender/program details."""

    rule_evaluations: list[RuleEvaluationResponse] = []
    lender_name: Optional[str] = None
    program_name: Optional[str] = None
    program_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ==================== Summary Schemas ====================


class MatchResultSummary(BaseModel):
    """Summary schema for match results."""

    total_matches: int
    matched_lenders: int
    rejected_lenders: int
    avg_fit_score: Optional[Decimal] = None
    best_match: Optional[MatchResultResponse] = None
    tier_1_rejections: int = 0
    tier_2_rejections: int = 0
    tier_3_rejections: int = 0


class UnderwritingResultsResponse(BaseModel):
    """Complete underwriting results response."""

    run: UnderwritingRunResponse
    summary: MatchResultSummary
    matched_results: list[MatchResultDetailResponse] = []
    rejected_results: list[MatchResultDetailResponse] = []

    @property
    def has_matches(self) -> bool:
        """Check if there are any matched results."""
        return len(self.matched_results) > 0


# ==================== List Responses ====================


class MatchResultListResponse(BaseModel):
    """Schema for paginated list of match results."""

    items: list[MatchResultResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
