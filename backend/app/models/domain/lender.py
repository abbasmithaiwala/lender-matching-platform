"""Lender and policy domain models for matching engine."""

import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import RuleType
from app.db.base import BaseModel


class Lender(BaseModel):
    """Lender entity with first-class exclusions for fast filtering."""

    __tablename__ = "lenders"

    # Basic Information
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Loan Constraints
    min_loan_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    max_loan_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )

    # First-Class Exclusions for Tier 1 Fast Filtering
    excluded_states: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String(2)), nullable=True
    )  # e.g., ["CA", "NV", "ND", "VT"]
    excluded_industries: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String(100)), nullable=True
    )  # e.g., ["Cannabis", "Gambling"]

    # Relationships
    programs: Mapped[list["PolicyProgram"]] = relationship(
        "PolicyProgram",
        back_populates="lender",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Lender(id={self.id}, name={self.name!r}, active={self.active})>"


class PolicyProgram(BaseModel):
    """Policy program/tier with eligibility conditions and rate metadata."""

    __tablename__ = "policy_programs"

    # Foreign Key
    lender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lenders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Program Identification
    program_name: Mapped[str] = mapped_column(String(255), nullable=False)
    program_code: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # e.g., "A", "B", "Medical A+", "Tier 1"
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Credit Tier Classification
    credit_tier: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # e.g., "Prime", "Near Prime", "Subprime"

    # Tier 2: Program Eligibility Conditions (JSONB)
    # Examples: {"requires_paynet": true}, {"legal_structure": ["Corp"]}, {"industry": ["Medical"]}
    eligibility_conditions: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    # Rate Metadata (JSONB) - Rate tables and adjustments
    # Examples:
    # {
    #   "base_rates": [
    #     {"min_amount": 10000, "max_amount": 50000, "rate": 7.25},
    #     {"min_amount": 50001, "max_amount": 100000, "rate": 6.75}
    #   ],
    #   "adjustments": [
    #     {"condition": "equipment_age > 15", "delta": 0.5},
    #     {"condition": "fico < 680", "delta": 1.0}
    #   ]
    # }
    rate_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)

    # Minimum Fit Score Threshold
    min_fit_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True, default=Decimal("0.00")
    )  # 0-100 scale

    # Active Status
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    lender: Mapped["Lender"] = relationship(
        "Lender",
        back_populates="programs",
    )
    rules: Mapped[list["PolicyRule"]] = relationship(
        "PolicyRule",
        back_populates="program",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<PolicyProgram(id={self.id}, name={self.program_name!r}, "
            f"code={self.program_code!r}, tier={self.credit_tier!r})>"
        )


class PolicyRule(BaseModel):
    """Policy rule with flexible JSONB criteria storage."""

    __tablename__ = "policy_rules"

    # Foreign Key
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policy_programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Rule Identification
    rule_type: Mapped[RuleType] = mapped_column(
        SQLEnum(RuleType, name="rule_type"),
        nullable=False,
        index=True,
    )
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Flexible Criteria Storage (JSONB)
    # Structure varies by rule_type:
    # - min_fico: {"min_score": 680}
    # - time_in_business: {"min_years": 2}
    # - equipment_age: {"max_age_years": 15}
    # - excluded_states: {"states": ["CA", "NV"]}
    # - loan_amount: {"min_amount": 10000, "max_amount": 250000}
    criteria: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Scoring & Evaluation
    weight: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("1.00")
    )  # Weight for scoring (default 1.0)
    is_mandatory: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )  # True = hard requirement, False = guideline

    # Active Status
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    program: Mapped["PolicyProgram"] = relationship(
        "PolicyProgram",
        back_populates="rules",
    )

    def __repr__(self) -> str:
        return (
            f"<PolicyRule(id={self.id}, type={self.rule_type.value}, "
            f"name={self.rule_name!r}, mandatory={self.is_mandatory})>"
        )
