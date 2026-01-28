"""Application domain models for loan applications and related entities."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ApplicationStatus, Condition, LegalStructure
from app.db.base import BaseModel


class Business(BaseModel):
    """Business entity with industry and location data."""

    __tablename__ = "businesses"

    # Basic Information
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dba_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Industry & Structure
    industry: Mapped[str] = mapped_column(String(100), nullable=False)
    legal_structure: Mapped[LegalStructure] = mapped_column(
        SQLEnum(LegalStructure, name="legal_structure"),
        nullable=False,
    )

    # Time & Financial Metrics
    established_date: Mapped[date] = mapped_column(Date, nullable=False)
    annual_revenue: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )

    # Location
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)  # 2-letter state code
    zip_code: Mapped[str] = mapped_column(String(10), nullable=False)

    # Contact
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    loan_applications: Mapped[list["LoanApplication"]] = relationship(
        "LoanApplication",
        back_populates="business",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Business(id={self.id}, legal_name={self.legal_name!r}, industry={self.industry!r})>"


class PersonalGuarantor(BaseModel):
    """Personal guarantor with credit scores and history."""

    __tablename__ = "personal_guarantors"

    # Personal Information
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Credit Scores
    fico_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    paynet_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Credit History
    bankruptcy_history: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    bankruptcy_discharge_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Financial Details
    credit_utilization_percentage: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )  # e.g., 45.50 for 45.5%
    revolving_credit_available: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )

    # Status Flags
    is_homeowner: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_us_citizen: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Contact
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Address
    address_line1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    zip_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Relationships
    loan_applications: Mapped[list["LoanApplication"]] = relationship(
        "LoanApplication",
        back_populates="guarantor",
        cascade="all, delete-orphan",
    )

    @property
    def full_name(self) -> str:
        """Return full name of guarantor."""
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<PersonalGuarantor(id={self.id}, name={self.full_name!r}, fico={self.fico_score})>"


class Equipment(BaseModel):
    """Equipment model with type, age, and condition."""

    __tablename__ = "equipment"

    # Equipment Details
    equipment_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Age & Condition
    year_manufactured: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    condition: Mapped[Condition] = mapped_column(
        SQLEnum(Condition, name="equipment_condition"),
        nullable=False,
    )

    # Pricing
    cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    serial_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    loan_applications: Mapped[list["LoanApplication"]] = relationship(
        "LoanApplication",
        back_populates="equipment",
        cascade="all, delete-orphan",
    )

    @property
    def age_years(self) -> Optional[int]:
        """Calculate equipment age in years."""
        if self.year_manufactured:
            current_year = datetime.now().year
            return current_year - self.year_manufactured
        return None

    def __repr__(self) -> str:
        return f"<Equipment(id={self.id}, type={self.equipment_type!r}, condition={self.condition.value})>"


class LoanApplication(BaseModel):
    """Loan application linking business, guarantor, and equipment."""

    __tablename__ = "loan_applications"

    # Application Identification
    application_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    # Status
    status: Mapped[ApplicationStatus] = mapped_column(
        SQLEnum(ApplicationStatus, name="application_status"),
        default=ApplicationStatus.DRAFT,
        nullable=False,
        index=True,
    )

    # Foreign Keys
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )
    guarantor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("personal_guarantors.id", ondelete="CASCADE"),
        nullable=False,
    )
    equipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("equipment.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Loan Details
    requested_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    requested_term_months: Mapped[int] = mapped_column(Integer, nullable=False)
    down_payment_percentage: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )  # e.g., 10.00 for 10%
    down_payment_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )

    # Additional Context
    purpose: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    comparable_debt_payments: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )  # Monthly comparable debt

    # Dates
    submitted_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Relationships
    business: Mapped["Business"] = relationship(
        "Business",
        back_populates="loan_applications",
    )
    guarantor: Mapped["PersonalGuarantor"] = relationship(
        "PersonalGuarantor",
        back_populates="loan_applications",
    )
    equipment: Mapped["Equipment"] = relationship(
        "Equipment",
        back_populates="loan_applications",
    )

    @property
    def net_financed_amount(self) -> Decimal:
        """Calculate net amount to be financed after down payment."""
        if self.down_payment_amount:
            return self.requested_amount - self.down_payment_amount
        return self.requested_amount

    def __repr__(self) -> str:
        return (
            f"<LoanApplication(id={self.id}, number={self.application_number!r}, "
            f"status={self.status.value}, amount={self.requested_amount})>"
        )
