"""Match result domain models for underwriting evaluation results."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import UnderwritingStatus
from app.db.base import BaseModel


class UnderwritingRun(BaseModel):
    """Underwriting run to track evaluation executions."""

    __tablename__ = "underwriting_runs"

    # Foreign Key - Link to Loan Application
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("loan_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Execution Status
    status: Mapped[UnderwritingStatus] = mapped_column(
        SQLEnum(UnderwritingStatus, name="underwriting_status"),
        default=UnderwritingStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Execution Summary
    total_lenders_evaluated: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    total_programs_evaluated: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    matched_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Error Handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata - Store execution context or parameters
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)

    # Relationships
    match_results: Mapped[list["MatchResult"]] = relationship(
        "MatchResult",
        back_populates="underwriting_run",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<UnderwritingRun(id={self.id}, application_id={self.application_id}, "
            f"status={self.status.value}, matched={self.matched_count})>"
        )


class MatchResult(BaseModel):
    """Match result with eligibility and fit score for a lender/program."""

    __tablename__ = "match_results"

    # Foreign Keys
    underwriting_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("underwriting_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lenders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policy_programs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Eligibility & Scoring
    is_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    fit_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0.00"), index=True
    )  # 0-100 scale

    # Rejection Reason (if not eligible)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rejection_tier: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # 1, 2, or 3 indicating which tier rejected

    # Rate Estimation
    estimated_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )  # Interest rate percentage, e.g., 7.25
    estimated_monthly_payment: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )

    # Approval Probability (Heuristic)
    approval_probability: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )  # 0-100 scale

    # Rule Evaluation Summary
    total_rules_evaluated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rules_passed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rules_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mandatory_rules_passed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Metadata - Additional context or details
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)

    # Relationships
    underwriting_run: Mapped["UnderwritingRun"] = relationship(
        "UnderwritingRun",
        back_populates="match_results",
    )
    lender: Mapped["Lender"] = relationship("Lender")
    program: Mapped[Optional["PolicyProgram"]] = relationship("PolicyProgram")
    rule_evaluations: Mapped[list["RuleEvaluation"]] = relationship(
        "RuleEvaluation",
        back_populates="match_result",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<MatchResult(id={self.id}, lender_id={self.lender_id}, "
            f"eligible={self.is_eligible}, fit_score={self.fit_score})>"
        )


class RuleEvaluation(BaseModel):
    """Individual rule evaluation result for transparency."""

    __tablename__ = "rule_evaluations"

    # Foreign Keys
    match_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("match_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policy_rules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Rule Identification (denormalized for historical tracking)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Evaluation Result
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0.00")
    )  # Contribution to overall fit score

    # Weight & Importance
    weight: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("1.00")
    )
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Detailed Reason & Evidence
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, default=dict
    )  # Actual vs required values

    # Relationships
    match_result: Mapped["MatchResult"] = relationship(
        "MatchResult",
        back_populates="rule_evaluations",
    )
    rule: Mapped[Optional["PolicyRule"]] = relationship("PolicyRule")

    def __repr__(self) -> str:
        return (
            f"<RuleEvaluation(id={self.id}, rule_name={self.rule_name!r}, "
            f"type={self.rule_type}, passed={self.passed}, score={self.score})>"
        )
