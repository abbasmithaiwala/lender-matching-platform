"""Rule engine orchestrator for coordinating policy evaluations."""

from decimal import Decimal
from typing import Dict, List, Type

from app.core.enums import RuleType
from app.models.domain.application import LoanApplication
from app.models.domain.lender import PolicyProgram, PolicyRule
from app.services.rule_engine.base import (
    EvaluationContext,
    EvaluationResult,
    RuleEvaluator,
)
from app.services.rule_engine.evaluators import (
    BusinessEvaluator,
    CreditEvaluator,
    EquipmentEvaluator,
    GeographicEvaluator,
    LoanEvaluator,
)


class ProgramEvaluationResult:
    """
    Result of evaluating all rules for a program.

    Attributes:
        program: The policy program evaluated
        is_eligible: Overall eligibility (all mandatory rules passed)
        fit_score: Overall fit score (0-100 scale, weighted)
        total_rules_evaluated: Number of rules evaluated
        rules_passed: Number of rules that passed
        rules_failed: Number of rules that failed
        mandatory_rules_passed: Whether all mandatory rules passed
        rule_results: List of individual rule evaluation results
    """

    def __init__(
        self,
        program: PolicyProgram,
        is_eligible: bool,
        fit_score: Decimal,
        total_rules_evaluated: int,
        rules_passed: int,
        rules_failed: int,
        mandatory_rules_passed: bool,
        rule_results: List[tuple[PolicyRule, EvaluationResult]],
    ):
        self.program = program
        self.is_eligible = is_eligible
        self.fit_score = fit_score
        self.total_rules_evaluated = total_rules_evaluated
        self.rules_passed = rules_passed
        self.rules_failed = rules_failed
        self.mandatory_rules_passed = mandatory_rules_passed
        self.rule_results = rule_results


class RuleEngine:
    """
    Rule engine orchestrator for coordinating policy evaluations.

    This class:
    - Maintains a registry of rule evaluators
    - Coordinates evaluation of all rules in a program
    - Implements weighted score aggregation
    - Handles mandatory vs. optional rules
    """

    def __init__(self):
        """Initialize the rule engine with evaluator registry."""
        self._evaluators: Dict[RuleType, RuleEvaluator] = {}
        self._register_default_evaluators()

    def _register_default_evaluators(self):
        """Register default evaluators for all rule types."""
        # Credit evaluators
        credit_evaluator = CreditEvaluator()
        self._evaluators[RuleType.MIN_FICO] = credit_evaluator
        self._evaluators[RuleType.MIN_PAYNET] = credit_evaluator
        self._evaluators[RuleType.CREDIT_TIER] = credit_evaluator
        self._evaluators[RuleType.MAX_CREDIT_UTILIZATION] = credit_evaluator

        # Business evaluators
        business_evaluator = BusinessEvaluator()
        self._evaluators[RuleType.TIME_IN_BUSINESS] = business_evaluator
        self._evaluators[RuleType.MIN_REVENUE] = business_evaluator
        self._evaluators[RuleType.LEGAL_STRUCTURE] = business_evaluator

        # Loan evaluators
        loan_evaluator = LoanEvaluator()
        self._evaluators[RuleType.MIN_LOAN_AMOUNT] = loan_evaluator
        self._evaluators[RuleType.MAX_LOAN_AMOUNT] = loan_evaluator
        self._evaluators[RuleType.MIN_LOAN_TERM] = loan_evaluator
        self._evaluators[RuleType.MAX_LOAN_TERM] = loan_evaluator
        self._evaluators[RuleType.MIN_DOWN_PAYMENT] = loan_evaluator
        self._evaluators[RuleType.MAX_LTV] = loan_evaluator

        # Equipment evaluators
        equipment_evaluator = EquipmentEvaluator()
        self._evaluators[RuleType.EQUIPMENT_TYPE] = equipment_evaluator
        self._evaluators[RuleType.EQUIPMENT_AGE] = equipment_evaluator
        self._evaluators[RuleType.EQUIPMENT_CONDITION] = equipment_evaluator

        # Geographic evaluators
        geographic_evaluator = GeographicEvaluator()
        self._evaluators[RuleType.EXCLUDED_STATES] = geographic_evaluator
        self._evaluators[RuleType.EXCLUDED_INDUSTRIES] = geographic_evaluator
        self._evaluators[RuleType.ALLOWED_STATES] = geographic_evaluator
        self._evaluators[RuleType.ALLOWED_INDUSTRIES] = geographic_evaluator

    def register_evaluator(
        self, rule_type: RuleType, evaluator: RuleEvaluator
    ) -> None:
        """
        Register a custom evaluator for a specific rule type.

        Args:
            rule_type: The rule type to handle
            evaluator: The evaluator instance
        """
        self._evaluators[rule_type] = evaluator

    def evaluate_program(
        self,
        application: LoanApplication,
        program: PolicyProgram,
    ) -> ProgramEvaluationResult:
        """
        Evaluate all rules in a program against an application.

        Args:
            application: The loan application to evaluate
            program: The policy program to evaluate against

        Returns:
            ProgramEvaluationResult with overall eligibility and fit score

        Raises:
            ValueError: If application or program is missing required data
        """
        # Validate application has all required relationships loaded
        if not application.business:
            raise ValueError("Application must have business relationship loaded")
        if not application.guarantor:
            raise ValueError("Application must have guarantor relationship loaded")
        if not application.equipment:
            raise ValueError("Application must have equipment relationship loaded")

        # Evaluate each rule
        rule_results: List[tuple[PolicyRule, EvaluationResult]] = []
        total_score = Decimal("0.00")
        total_weight = Decimal("0.00")
        rules_passed = 0
        rules_failed = 0
        all_mandatory_passed = True

        # Get active rules for the program
        active_rules = [rule for rule in program.rules if rule.active]

        for rule in active_rules:
            # Get appropriate evaluator
            evaluator = self._evaluators.get(rule.rule_type)

            if evaluator is None:
                # Skip rules without registered evaluators
                # In production, you might want to log this
                continue

            # Create evaluation context
            context = EvaluationContext(
                application=application,
                business=application.business,
                guarantor=application.guarantor,
                equipment=application.equipment,
                program=program,
                rule=rule,
            )

            # Evaluate the rule
            try:
                result = evaluator.evaluate(context)
                rule_results.append((rule, result))

                # Update statistics
                if result.passed:
                    rules_passed += 1
                else:
                    rules_failed += 1
                    if result.is_mandatory:
                        all_mandatory_passed = False

                # Accumulate weighted score
                total_score += result.score
                total_weight += result.weight

            except Exception as e:
                # If evaluation fails, treat as failed rule
                # In production, you might want better error handling
                failed_result = EvaluationResult(
                    passed=False,
                    score=Decimal("0.00"),
                    reason=f"Evaluation error: {str(e)}",
                    evidence={"error": str(e)},
                    weight=rule.weight,
                    is_mandatory=rule.is_mandatory,
                )
                rule_results.append((rule, failed_result))
                rules_failed += 1
                if rule.is_mandatory:
                    all_mandatory_passed = False
                total_weight += rule.weight

        # Calculate overall fit score (normalized to 0-100)
        if total_weight > Decimal("0.00"):
            fit_score = (total_score / total_weight).quantize(Decimal("0.01"))
        else:
            fit_score = Decimal("0.00")

        # Determine overall eligibility
        # Must pass all mandatory rules AND meet minimum fit score
        is_eligible = all_mandatory_passed
        if program.min_fit_score and fit_score < program.min_fit_score:
            is_eligible = False

        return ProgramEvaluationResult(
            program=program,
            is_eligible=is_eligible,
            fit_score=fit_score,
            total_rules_evaluated=len(active_rules),
            rules_passed=rules_passed,
            rules_failed=rules_failed,
            mandatory_rules_passed=all_mandatory_passed,
            rule_results=rule_results,
        )

    def evaluate_rule(
        self,
        application: LoanApplication,
        program: PolicyProgram,
        rule: PolicyRule,
    ) -> EvaluationResult:
        """
        Evaluate a single rule against an application.

        Args:
            application: The loan application to evaluate
            program: The policy program containing the rule
            rule: The specific rule to evaluate

        Returns:
            EvaluationResult for the rule

        Raises:
            ValueError: If no evaluator is registered for the rule type
        """
        evaluator = self._evaluators.get(rule.rule_type)

        if evaluator is None:
            raise ValueError(f"No evaluator registered for rule type: {rule.rule_type.value}")

        # Validate application has required relationships
        if not application.business:
            raise ValueError("Application must have business relationship loaded")
        if not application.guarantor:
            raise ValueError("Application must have guarantor relationship loaded")
        if not application.equipment:
            raise ValueError("Application must have equipment relationship loaded")

        # Create evaluation context
        context = EvaluationContext(
            application=application,
            business=application.business,
            guarantor=application.guarantor,
            equipment=application.equipment,
            program=program,
            rule=rule,
        )

        # Evaluate and return
        return evaluator.evaluate(context)
