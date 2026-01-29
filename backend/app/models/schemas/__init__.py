"""Pydantic schemas for API validation and serialization."""

from app.models.schemas.application import (
    BusinessCreate,
    BusinessResponse,
    BusinessUpdate,
    EquipmentCreate,
    EquipmentResponse,
    EquipmentUpdate,
    GuarantorCreate,
    GuarantorResponse,
    GuarantorUpdate,
    LoanApplicationCreate,
    LoanApplicationResponse,
    LoanApplicationUpdate,
)
from app.models.schemas.lender import (
    LenderCreate,
    LenderResponse,
    LenderUpdate,
    PolicyProgramCreate,
    PolicyProgramResponse,
    PolicyProgramUpdate,
    PolicyRuleCreate,
    PolicyRuleResponse,
    PolicyRuleUpdate,
)
from app.models.schemas.match import (
    MatchResultResponse,
    RuleEvaluationResponse,
    UnderwritingRunCreate,
    UnderwritingRunResponse,
)

__all__ = [
    # Application schemas
    "BusinessCreate",
    "BusinessUpdate",
    "BusinessResponse",
    "GuarantorCreate",
    "GuarantorUpdate",
    "GuarantorResponse",
    "EquipmentCreate",
    "EquipmentUpdate",
    "EquipmentResponse",
    "LoanApplicationCreate",
    "LoanApplicationUpdate",
    "LoanApplicationResponse",
    # Lender schemas
    "LenderCreate",
    "LenderUpdate",
    "LenderResponse",
    "PolicyProgramCreate",
    "PolicyProgramUpdate",
    "PolicyProgramResponse",
    "PolicyRuleCreate",
    "PolicyRuleUpdate",
    "PolicyRuleResponse",
    # Match schemas
    "UnderwritingRunCreate",
    "UnderwritingRunResponse",
    "MatchResultResponse",
    "RuleEvaluationResponse",
]
