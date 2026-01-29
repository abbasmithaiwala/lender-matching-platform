"""Pydantic schemas for application-related entities."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import ApplicationStatus, Condition, LegalStructure


# ==================== Business Schemas ====================


class BusinessBase(BaseModel):
    """Base schema for business with common fields."""

    legal_name: str = Field(..., min_length=1, max_length=255)
    dba_name: Optional[str] = Field(None, max_length=255)
    industry: str = Field(..., min_length=1, max_length=100)
    legal_structure: LegalStructure
    established_date: date
    annual_revenue: Optional[Decimal] = Field(None, ge=0)
    address_line1: str = Field(..., min_length=1, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=2, max_length=2, pattern="^[A-Z]{2}$")
    zip_code: str = Field(..., min_length=5, max_length=10)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        """Ensure state is uppercase."""
        return v.upper()


class BusinessCreate(BusinessBase):
    """Schema for creating a business."""

    pass


class BusinessUpdate(BaseModel):
    """Schema for updating a business (all fields optional)."""

    legal_name: Optional[str] = Field(None, min_length=1, max_length=255)
    dba_name: Optional[str] = Field(None, max_length=255)
    industry: Optional[str] = Field(None, min_length=1, max_length=100)
    legal_structure: Optional[LegalStructure] = None
    established_date: Optional[date] = None
    annual_revenue: Optional[Decimal] = Field(None, ge=0)
    address_line1: Optional[str] = Field(None, min_length=1, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    state: Optional[str] = Field(None, min_length=2, max_length=2, pattern="^[A-Z]{2}$")
    zip_code: Optional[str] = Field(None, min_length=5, max_length=10)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: Optional[str]) -> Optional[str]:
        """Ensure state is uppercase if provided."""
        return v.upper() if v else v


class BusinessResponse(BusinessBase):
    """Schema for business response."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== Personal Guarantor Schemas ====================


class GuarantorBase(BaseModel):
    """Base schema for personal guarantor with common fields."""

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    fico_score: Optional[int] = Field(None, ge=300, le=850)
    paynet_score: Optional[int] = Field(None, ge=0, le=100)
    bankruptcy_history: bool = False
    bankruptcy_discharge_date: Optional[date] = None
    credit_utilization_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    revolving_credit_available: Optional[Decimal] = Field(None, ge=0)
    is_homeowner: bool = False
    is_us_citizen: bool = True
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, min_length=2, max_length=2, pattern="^[A-Z]{2}$")
    zip_code: Optional[str] = Field(None, max_length=10)

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: Optional[str]) -> Optional[str]:
        """Ensure state is uppercase if provided."""
        return v.upper() if v else v

    @field_validator("bankruptcy_discharge_date")
    @classmethod
    def validate_bankruptcy_date(cls, v: Optional[date], values) -> Optional[date]:
        """Ensure bankruptcy discharge date is only set when bankruptcy_history is True."""
        # Note: In Pydantic v2, we need to use info.data to access other fields
        return v


class GuarantorCreate(GuarantorBase):
    """Schema for creating a personal guarantor."""

    pass


class GuarantorUpdate(BaseModel):
    """Schema for updating a personal guarantor (all fields optional)."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    fico_score: Optional[int] = Field(None, ge=300, le=850)
    paynet_score: Optional[int] = Field(None, ge=0, le=100)
    bankruptcy_history: Optional[bool] = None
    bankruptcy_discharge_date: Optional[date] = None
    credit_utilization_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    revolving_credit_available: Optional[Decimal] = Field(None, ge=0)
    is_homeowner: Optional[bool] = None
    is_us_citizen: Optional[bool] = None
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, min_length=2, max_length=2, pattern="^[A-Z]{2}$")
    zip_code: Optional[str] = Field(None, max_length=10)

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: Optional[str]) -> Optional[str]:
        """Ensure state is uppercase if provided."""
        return v.upper() if v else v


class GuarantorResponse(GuarantorBase):
    """Schema for guarantor response."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== Equipment Schemas ====================


class EquipmentBase(BaseModel):
    """Base schema for equipment with common fields."""

    equipment_type: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    manufacturer: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    year_manufactured: Optional[int] = Field(None, ge=1900, le=2100)
    condition: Condition
    cost: Decimal = Field(..., gt=0)
    serial_number: Optional[str] = Field(None, max_length=100)

    @field_validator("year_manufactured")
    @classmethod
    def validate_year(cls, v: Optional[int]) -> Optional[int]:
        """Ensure year is not in the future."""
        if v:
            from datetime import datetime

            current_year = datetime.now().year
            if v > current_year:
                raise ValueError(f"Year manufactured cannot be in the future (max: {current_year})")
        return v


class EquipmentCreate(EquipmentBase):
    """Schema for creating equipment."""

    pass


class EquipmentUpdate(BaseModel):
    """Schema for updating equipment (all fields optional)."""

    equipment_type: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    manufacturer: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    year_manufactured: Optional[int] = Field(None, ge=1900, le=2100)
    condition: Optional[Condition] = None
    cost: Optional[Decimal] = Field(None, gt=0)
    serial_number: Optional[str] = Field(None, max_length=100)

    @field_validator("year_manufactured")
    @classmethod
    def validate_year(cls, v: Optional[int]) -> Optional[int]:
        """Ensure year is not in the future."""
        if v:
            from datetime import datetime

            current_year = datetime.now().year
            if v > current_year:
                raise ValueError(f"Year manufactured cannot be in the future (max: {current_year})")
        return v


class EquipmentResponse(EquipmentBase):
    """Schema for equipment response."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    age_years: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# ==================== Loan Application Schemas ====================


class LoanApplicationBase(BaseModel):
    """Base schema for loan application with common fields."""

    requested_amount: Decimal = Field(..., gt=0)
    requested_term_months: int = Field(..., gt=0, le=360)
    down_payment_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    down_payment_amount: Optional[Decimal] = Field(None, ge=0)
    purpose: Optional[str] = None
    comparable_debt_payments: Optional[Decimal] = Field(None, ge=0)


class LoanApplicationCreate(LoanApplicationBase):
    """Schema for creating a loan application with nested entities."""

    business: BusinessCreate
    guarantor: GuarantorCreate
    equipment: EquipmentCreate

    @field_validator("down_payment_amount")
    @classmethod
    def validate_down_payment(cls, v: Optional[Decimal], info) -> Optional[Decimal]:
        """Ensure down payment doesn't exceed requested amount."""
        if v and info.data.get("requested_amount"):
            requested_amount = info.data["requested_amount"]
            if v > requested_amount:
                raise ValueError("Down payment cannot exceed requested amount")
        return v


class LoanApplicationUpdate(BaseModel):
    """Schema for updating a loan application (all fields optional)."""

    status: Optional[ApplicationStatus] = None
    requested_amount: Optional[Decimal] = Field(None, gt=0)
    requested_term_months: Optional[int] = Field(None, gt=0, le=360)
    down_payment_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    down_payment_amount: Optional[Decimal] = Field(None, ge=0)
    purpose: Optional[str] = None
    comparable_debt_payments: Optional[Decimal] = Field(None, ge=0)
    business: Optional[BusinessUpdate] = None
    guarantor: Optional[GuarantorUpdate] = None
    equipment: Optional[EquipmentUpdate] = None


class LoanApplicationResponse(LoanApplicationBase):
    """Schema for loan application response with nested entities."""

    id: UUID
    application_number: str
    status: ApplicationStatus
    business_id: UUID
    guarantor_id: UUID
    equipment_id: UUID
    submitted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    # Nested entities
    business: BusinessResponse
    guarantor: GuarantorResponse
    equipment: EquipmentResponse

    # Computed fields
    net_financed_amount: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True)


class LoanApplicationListResponse(BaseModel):
    """Schema for paginated list of loan applications."""

    items: list[LoanApplicationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
