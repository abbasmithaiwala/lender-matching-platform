"""Loan rule evaluator for loan amount and term rules."""

from decimal import Decimal

from app.core.enums import RuleType
from app.services.rule_engine.base import (
    EvaluationContext,
    EvaluationResult,
    RuleEvaluator,
)


class LoanEvaluator(RuleEvaluator):
    """
    Evaluator for loan-related rules.

    Handles:
    - MIN_LOAN_AMOUNT: Minimum loan amount requirements
    - MAX_LOAN_AMOUNT: Maximum loan amount requirements
    - MIN_LOAN_TERM: Minimum loan term in months
    - MAX_LOAN_TERM: Maximum loan term in months
    - MIN_DOWN_PAYMENT: Minimum down payment percentage
    - MAX_LTV: Maximum loan-to-value ratio
    """

    def evaluate(self, context: EvaluationContext) -> EvaluationResult:
        """
        Evaluate loan-related rules against the application context.

        Args:
            context: EvaluationContext containing all application data

        Returns:
            EvaluationResult with pass/fail, score, reason, and evidence

        Raises:
            ValueError: If rule type is not loan-related or criteria are invalid
        """
        rule = context.rule

        # Route to appropriate handler based on rule type
        if rule.rule_type == RuleType.MIN_LOAN_AMOUNT:
            return self._evaluate_min_loan_amount(context)
        elif rule.rule_type == RuleType.MAX_LOAN_AMOUNT:
            return self._evaluate_max_loan_amount(context)
        elif rule.rule_type == RuleType.MIN_LOAN_TERM:
            return self._evaluate_min_loan_term(context)
        elif rule.rule_type == RuleType.MAX_LOAN_TERM:
            return self._evaluate_max_loan_term(context)
        elif rule.rule_type == RuleType.MIN_DOWN_PAYMENT:
            return self._evaluate_min_down_payment(context)
        elif rule.rule_type == RuleType.MAX_LTV:
            return self._evaluate_max_ltv(context)
        else:
            raise ValueError(
                f"LoanEvaluator cannot handle rule type: {rule.rule_type.value}"
            )

    def _evaluate_min_loan_amount(
        self, context: EvaluationContext
    ) -> EvaluationResult:
        """
        Evaluate minimum loan amount requirement.

        Criteria format: {"min_amount": 10000}

        Args:
            context: EvaluationContext

        Returns:
            EvaluationResult with scoring
        """
        rule = context.rule
        application = context.application
        criteria = rule.criteria

        min_amount = Decimal(
            str(self._extract_criteria_value(criteria, "min_amount", required=True))
        )
        requested_amount = application.requested_amount

        passed = requested_amount >= min_amount

        if passed:
            score = self._calculate_score(True, rule.weight)
            reason = f"Loan amount ${requested_amount:,.2f} meets minimum of ${min_amount:,.2f}"
        else:
            score = Decimal("0.00")
            gap = min_amount - requested_amount
            reason = f"Loan amount ${requested_amount:,.2f} is below minimum of ${min_amount:,.2f} (gap: ${gap:,.2f})"

        return EvaluationResult(
            passed=passed,
            score=score,
            reason=reason,
            evidence={
                "actual": float(requested_amount),
                "required": float(min_amount),
                "gap": float(min_amount - requested_amount) if not passed else 0,
            },
            weight=rule.weight,
            is_mandatory=rule.is_mandatory,
        )

    def _evaluate_max_loan_amount(
        self, context: EvaluationContext
    ) -> EvaluationResult:
        """
        Evaluate maximum loan amount requirement.

        Criteria format: {"max_amount": 250000}

        Args:
            context: EvaluationContext

        Returns:
            EvaluationResult with scoring
        """
        rule = context.rule
        application = context.application
        criteria = rule.criteria

        max_amount = Decimal(
            str(self._extract_criteria_value(criteria, "max_amount", required=True))
        )
        requested_amount = application.requested_amount

        passed = requested_amount <= max_amount

        if passed:
            score = self._calculate_score(True, rule.weight)
            reason = f"Loan amount ${requested_amount:,.2f} is within maximum of ${max_amount:,.2f}"
        else:
            score = Decimal("0.00")
            excess = requested_amount - max_amount
            reason = f"Loan amount ${requested_amount:,.2f} exceeds maximum of ${max_amount:,.2f} (excess: ${excess:,.2f})"

        return EvaluationResult(
            passed=passed,
            score=score,
            reason=reason,
            evidence={
                "actual": float(requested_amount),
                "required": float(max_amount),
                "excess": float(requested_amount - max_amount) if not passed else 0,
            },
            weight=rule.weight,
            is_mandatory=rule.is_mandatory,
        )

    def _evaluate_min_loan_term(self, context: EvaluationContext) -> EvaluationResult:
        """
        Evaluate minimum loan term requirement.

        Criteria format: {"min_months": 12}

        Args:
            context: EvaluationContext

        Returns:
            EvaluationResult with scoring
        """
        rule = context.rule
        application = context.application
        criteria = rule.criteria

        min_months = self._extract_criteria_value(
            criteria, "min_months", required=True
        )
        requested_term = application.requested_term_months

        passed = requested_term >= min_months

        if passed:
            score = self._calculate_score(True, rule.weight)
            reason = f"Loan term {requested_term} months meets minimum of {min_months} months"
        else:
            score = Decimal("0.00")
            gap = min_months - requested_term
            reason = f"Loan term {requested_term} months is below minimum of {min_months} months (gap: {gap} months)"

        return EvaluationResult(
            passed=passed,
            score=score,
            reason=reason,
            evidence={
                "actual": requested_term,
                "required": min_months,
                "gap": min_months - requested_term if not passed else 0,
            },
            weight=rule.weight,
            is_mandatory=rule.is_mandatory,
        )

    def _evaluate_max_loan_term(self, context: EvaluationContext) -> EvaluationResult:
        """
        Evaluate maximum loan term requirement.

        Criteria format: {"max_months": 60}

        Args:
            context: EvaluationContext

        Returns:
            EvaluationResult with scoring
        """
        rule = context.rule
        application = context.application
        criteria = rule.criteria

        max_months = self._extract_criteria_value(
            criteria, "max_months", required=True
        )
        requested_term = application.requested_term_months

        passed = requested_term <= max_months

        if passed:
            score = self._calculate_score(True, rule.weight)
            reason = f"Loan term {requested_term} months is within maximum of {max_months} months"
        else:
            score = Decimal("0.00")
            excess = requested_term - max_months
            reason = f"Loan term {requested_term} months exceeds maximum of {max_months} months (excess: {excess} months)"

        return EvaluationResult(
            passed=passed,
            score=score,
            reason=reason,
            evidence={
                "actual": requested_term,
                "required": max_months,
                "excess": requested_term - max_months if not passed else 0,
            },
            weight=rule.weight,
            is_mandatory=rule.is_mandatory,
        )

    def _evaluate_min_down_payment(
        self, context: EvaluationContext
    ) -> EvaluationResult:
        """
        Evaluate minimum down payment percentage requirement.

        Criteria format: {"min_percentage": 10.0}

        Args:
            context: EvaluationContext

        Returns:
            EvaluationResult with scoring
        """
        rule = context.rule
        application = context.application
        criteria = rule.criteria

        min_percentage = Decimal(
            str(
                self._extract_criteria_value(
                    criteria, "min_percentage", required=True
                )
            )
        )

        # Handle missing down payment
        if application.down_payment_percentage is None:
            # Assume 0% if not specified
            actual_percentage = Decimal("0.00")
        else:
            actual_percentage = application.down_payment_percentage

        passed = actual_percentage >= min_percentage

        if passed:
            score = self._calculate_score(True, rule.weight)
            reason = f"Down payment {actual_percentage}% meets minimum of {min_percentage}%"
        else:
            score = Decimal("0.00")
            gap = min_percentage - actual_percentage
            reason = f"Down payment {actual_percentage}% is below minimum of {min_percentage}% (gap: {gap}%)"

        return EvaluationResult(
            passed=passed,
            score=score,
            reason=reason,
            evidence={
                "actual": float(actual_percentage),
                "required": float(min_percentage),
                "gap": float(min_percentage - actual_percentage) if not passed else 0,
            },
            weight=rule.weight,
            is_mandatory=rule.is_mandatory,
        )

    def _evaluate_max_ltv(self, context: EvaluationContext) -> EvaluationResult:
        """
        Evaluate maximum loan-to-value ratio.

        Criteria format: {"max_percentage": 90.0}

        LTV = (Loan Amount / Equipment Cost) * 100

        Args:
            context: EvaluationContext

        Returns:
            EvaluationResult with scoring
        """
        rule = context.rule
        application = context.application
        equipment = context.equipment
        criteria = rule.criteria

        max_ltv = Decimal(
            str(
                self._extract_criteria_value(
                    criteria, "max_percentage", required=True
                )
            )
        )

        # Calculate LTV
        equipment_cost = equipment.cost
        loan_amount = application.requested_amount

        if equipment_cost == 0:
            return EvaluationResult(
                passed=False,
                score=Decimal("0.00"),
                reason="Equipment cost cannot be zero for LTV calculation",
                evidence={
                    "actual": None,
                    "required": float(max_ltv),
                },
                weight=rule.weight,
                is_mandatory=rule.is_mandatory,
            )

        actual_ltv = (loan_amount / equipment_cost) * Decimal("100")
        passed = actual_ltv <= max_ltv

        if passed:
            score = self._calculate_score(True, rule.weight)
            reason = f"LTV {actual_ltv:.2f}% is within maximum of {max_ltv}%"
        else:
            score = Decimal("0.00")
            excess = actual_ltv - max_ltv
            reason = f"LTV {actual_ltv:.2f}% exceeds maximum of {max_ltv}% (excess: {excess:.2f}%)"

        return EvaluationResult(
            passed=passed,
            score=score,
            reason=reason,
            evidence={
                "actual": float(actual_ltv),
                "required": float(max_ltv),
                "loan_amount": float(loan_amount),
                "equipment_cost": float(equipment_cost),
                "excess": float(actual_ltv - max_ltv) if not passed else 0,
            },
            weight=rule.weight,
            is_mandatory=rule.is_mandatory,
        )
