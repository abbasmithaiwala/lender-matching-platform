"""Core enums for type safety across the application."""

from enum import Enum


class LegalStructure(str, Enum):
    """Business legal structure types."""

    LLC = "LLC"
    CORPORATION = "Corporation"
    S_CORP = "S-Corp"
    C_CORP = "C-Corp"
    PARTNERSHIP = "Partnership"
    SOLE_PROPRIETORSHIP = "Sole Proprietorship"
    NON_PROFIT = "Non-Profit"
    OTHER = "Other"


class Condition(str, Enum):
    """Equipment condition states."""

    NEW = "New"
    USED = "Used"
    REFURBISHED = "Refurbished"
    CERTIFIED_PRE_OWNED = "Certified Pre-Owned"


class ApplicationStatus(str, Enum):
    """Loan application workflow states."""

    DRAFT = "Draft"
    SUBMITTED = "Submitted"
    UNDER_REVIEW = "Under Review"
    IN_UNDERWRITING = "In Underwriting"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    WITHDRAWN = "Withdrawn"
    EXPIRED = "Expired"


class UnderwritingStatus(str, Enum):
    """Underwriting run status states."""

    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


class RuleType(str, Enum):
    """Policy rule types for lender matching."""

    # Credit-related rules
    MIN_FICO = "min_fico"
    MIN_PAYNET = "min_paynet"
    CREDIT_TIER = "credit_tier"
    MAX_CREDIT_UTILIZATION = "max_credit_utilization"

    # Business-related rules
    TIME_IN_BUSINESS = "time_in_business"
    MIN_REVENUE = "min_revenue"
    LEGAL_STRUCTURE = "legal_structure"

    # Loan-related rules
    MIN_LOAN_AMOUNT = "min_loan_amount"
    MAX_LOAN_AMOUNT = "max_loan_amount"
    MIN_LOAN_TERM = "min_loan_term"
    MAX_LOAN_TERM = "max_loan_term"
    MIN_DOWN_PAYMENT = "min_down_payment"
    MAX_LTV = "max_ltv"

    # Equipment-related rules
    EQUIPMENT_TYPE = "equipment_type"
    EQUIPMENT_AGE = "equipment_age"
    EQUIPMENT_CONDITION = "equipment_condition"

    # Geographic and industry rules
    EXCLUDED_STATES = "excluded_states"
    EXCLUDED_INDUSTRIES = "excluded_industries"
    ALLOWED_STATES = "allowed_states"
    ALLOWED_INDUSTRIES = "allowed_industries"

    # Guarantor-related rules
    BANKRUPTCY_HISTORY = "bankruptcy_history"
    HOMEOWNER_REQUIRED = "homeowner_required"
    US_CITIZEN_REQUIRED = "us_citizen_required"

    # Other rules
    CUSTOM = "custom"
