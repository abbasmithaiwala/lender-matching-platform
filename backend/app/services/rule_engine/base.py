"""Rule engine foundation with evaluation context, results, and base evaluator."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from app.models.domain.application import (
    Business,
    Equipment,
    LoanApplication,
    PersonalGuarantor,
)
from app.models.domain.lender import PolicyProgram, PolicyRule


@dataclass
class EvaluationContext:
    """
    Evaluation context containing all application data for rule evaluation.

    This context is passed to rule evaluators and contains all information
    needed to assess whether an application meets policy requirements.

    Attributes:
        application: The loan application being evaluated
        business: Business information (loaded from application)
        guarantor: Personal guarantor information (loaded from application)
        equipment: Equipment information (loaded from application)
        program: The policy program being evaluated against
        rule: The specific rule being evaluated
    """

    application: LoanApplication
    business: Business
    guarantor: PersonalGuarantor
    equipment: Equipment
    program: PolicyProgram
    rule: PolicyRule


@dataclass
class EvaluationResult:
    """
    Result of evaluating a single rule against an application.

    Contains pass/fail status, scoring information, and detailed evidence
    for transparency and debugging.

    Attributes:
        passed: Whether the rule evaluation passed
        score: Contribution to overall fit score (0-100 scale)
        reason: Human-readable explanation of the result
        evidence: Structured data showing actual vs. required values
        weight: Weight of this rule in scoring (from the rule)
        is_mandatory: Whether this is a hard requirement or guideline
    """

    passed: bool
    score: Decimal = field(default=Decimal("0.00"))
    reason: Optional[str] = None
    evidence: Optional[dict] = field(default_factory=dict)
    weight: Decimal = field(default=Decimal("1.00"))
    is_mandatory: bool = True

    def __post_init__(self):
        """Ensure score is a Decimal."""
        if not isinstance(self.score, Decimal):
            self.score = Decimal(str(self.score))
        if not isinstance(self.weight, Decimal):
            self.weight = Decimal(str(self.weight))


class RuleEvaluator(ABC):
    """
    Abstract base class for rule evaluators using the Strategy pattern.

    Each concrete evaluator implements evaluation logic for a specific
    rule type (e.g., credit score, business age, equipment criteria).

    Subclasses must implement the evaluate() method to process their
    specific rule type and return an EvaluationResult.
    """

    @abstractmethod
    def evaluate(self, context: EvaluationContext) -> EvaluationResult:
        """
        Evaluate a rule against the provided context.

        Args:
            context: EvaluationContext containing all application data

        Returns:
            EvaluationResult with pass/fail, score, reason, and evidence

        Raises:
            ValueError: If the rule criteria are invalid or missing required fields
        """
        pass

    def _calculate_score(
        self,
        passed: bool,
        weight: Decimal,
        partial_credit: Decimal = Decimal("0.00"),
    ) -> Decimal:
        """
        Calculate the score contribution for this rule.

        Args:
            passed: Whether the rule passed
            weight: Weight of the rule
            partial_credit: Partial credit to award (0.0 to 1.0) if not fully passed

        Returns:
            Score contribution (0-100 scale, weighted)
        """
        if passed:
            return Decimal("100.00") * weight

        # Award partial credit if applicable
        if partial_credit > Decimal("0.00"):
            return Decimal("100.00") * weight * partial_credit

        return Decimal("0.00")

    def _extract_criteria_value(
        self,
        criteria: dict,
        key: str,
        default: Optional[any] = None,
        required: bool = True,
    ) -> any:
        """
        Safely extract a value from rule criteria with validation.

        Args:
            criteria: The rule's criteria dictionary
            key: The key to extract
            default: Default value if key not found (only used if not required)
            required: Whether this field is required

        Returns:
            The extracted value

        Raises:
            ValueError: If required field is missing
        """
        if key not in criteria:
            if required:
                raise ValueError(f"Required criteria field '{key}' is missing")
            return default

        return criteria[key]
