"""Pydantic schemas for lender and policy-related entities."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import RuleType


# ==================== Lender Schemas ====================


class LenderBase(BaseModel):
    """Base schema for lender with common fields."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    active: bool = True
    min_loan_amount: Optional[Decimal] = Field(None, ge=0)
    max_loan_amount: Optional[Decimal] = Field(None, ge=0)
    excluded_states: Optional[list[str]] = Field(None, description="List of excluded state codes (e.g., ['CA', 'NV'])")
    excluded_industries: Optional[list[str]] = Field(
        None, description="List of excluded industry names (e.g., ['Cannabis', 'Gambling'])"
    )


class LenderCreate(LenderBase):
    """Schema for creating a lender."""

    pass


class LenderUpdate(BaseModel):
    """Schema for updating a lender (all fields optional)."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    active: Optional[bool] = None
    min_loan_amount: Optional[Decimal] = Field(None, ge=0)
    max_loan_amount: Optional[Decimal] = Field(None, ge=0)
    excluded_states: Optional[list[str]] = None
    excluded_industries: Optional[list[str]] = None


class LenderResponse(LenderBase):
    """Schema for lender response."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LenderDetailResponse(LenderResponse):
    """Schema for lender response with programs."""

    programs: list["PolicyProgramResponse"] = []

    model_config = ConfigDict(from_attributes=True)


# ==================== Policy Program Schemas ====================


class PolicyProgramBase(BaseModel):
    """Base schema for policy program with common fields."""

    program_name: str = Field(..., min_length=1, max_length=255)
    program_code: Optional[str] = Field(None, max_length=50, description="Program tier code (e.g., 'A', 'B', 'Medical A+')")
    description: Optional[str] = None
    credit_tier: Optional[str] = Field(
        None, max_length=50, description="Credit tier classification (e.g., 'Prime', 'Near Prime')"
    )
    eligibility_conditions: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        description="Program eligibility conditions (e.g., {'requires_paynet': true, 'legal_structure': ['Corp']})",
    )
    rate_metadata: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        description="Rate tables and adjustments (e.g., base_rates, adjustments)",
    )
    min_fit_score: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0, le=100)
    active: bool = True


class PolicyProgramCreate(PolicyProgramBase):
    """Schema for creating a policy program."""

    lender_id: UUID


class PolicyProgramUpdate(BaseModel):
    """Schema for updating a policy program (all fields optional)."""

    program_name: Optional[str] = Field(None, min_length=1, max_length=255)
    program_code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    credit_tier: Optional[str] = Field(None, max_length=50)
    eligibility_conditions: Optional[dict[str, Any]] = None
    rate_metadata: Optional[dict[str, Any]] = None
    min_fit_score: Optional[Decimal] = Field(None, ge=0, le=100)
    active: Optional[bool] = None


class PolicyProgramResponse(PolicyProgramBase):
    """Schema for policy program response."""

    id: UUID
    lender_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PolicyProgramDetailResponse(PolicyProgramResponse):
    """Schema for policy program response with rules."""

    rules: list["PolicyRuleResponse"] = []

    model_config = ConfigDict(from_attributes=True)


# ==================== Policy Rule Schemas ====================


class PolicyRuleBase(BaseModel):
    """Base schema for policy rule with common fields."""

    rule_type: RuleType
    rule_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    criteria: dict[str, Any] = Field(
        ...,
        description="Rule criteria (structure varies by rule_type, e.g., {'min_score': 680} for min_fico)",
    )
    weight: Decimal = Field(default=Decimal("1.00"), ge=0, description="Weight for scoring (default 1.0)")
    is_mandatory: bool = Field(
        default=True,
        description="True = hard requirement, False = guideline",
    )
    active: bool = True


class PolicyRuleCreate(PolicyRuleBase):
    """Schema for creating a policy rule."""

    program_id: UUID


class PolicyRuleUpdate(BaseModel):
    """Schema for updating a policy rule (all fields optional)."""

    rule_type: Optional[RuleType] = None
    rule_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    criteria: Optional[dict[str, Any]] = None
    weight: Optional[Decimal] = Field(None, ge=0)
    is_mandatory: Optional[bool] = None
    active: Optional[bool] = None


class PolicyRuleResponse(PolicyRuleBase):
    """Schema for policy rule response."""

    id: UUID
    program_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== Bulk Operations ====================


class LenderBulkCreate(BaseModel):
    """Schema for bulk creating lender with programs and rules."""

    lender: LenderCreate
    programs: list["PolicyProgramWithRules"] = []


class PolicyProgramWithRules(BaseModel):
    """Schema for policy program with associated rules."""

    program: PolicyProgramBase
    rules: list[PolicyRuleBase] = []


# ==================== List Responses ====================


class LenderListResponse(BaseModel):
    """Schema for paginated list of lenders."""

    items: list[LenderResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class PolicyProgramListResponse(BaseModel):
    """Schema for paginated list of policy programs."""

    items: list[PolicyProgramResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class PolicyRuleListResponse(BaseModel):
    """Schema for paginated list of policy rules."""

    items: list[PolicyRuleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
