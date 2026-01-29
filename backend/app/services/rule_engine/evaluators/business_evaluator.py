"""Business rule evaluator for business criteria."""

from datetime import date
from decimal import Decimal
from typing import List

from app.core.enums import LegalStructure, RuleType
from app.services.rule_engine.base import (
    EvaluationContext,
    EvaluationResult,
    RuleEvaluator,
)


class BusinessEvaluator(RuleEvaluator):
    """
    Evaluator for business-related rules.

    Handles:
    - TIME_IN_BUSINESS: Minimum time in business requirements
    - MIN_REVENUE: Minimum annual revenue requirements
    - LEGAL_STRUCTURE: Business structure requirements
    """

    def evaluate(self, context: EvaluationContext) -> EvaluationResult:
        """
        Evaluate business-related rules against the application context.

        Args:
            context: EvaluationContext containing all application data

        Returns:
            EvaluationResult with pass/fail, score, reason, and evidence

        Raises:
            ValueError: If rule type is not business-related or criteria are invalid
        """
        rule = context.rule

        # Route to appropriate handler based on rule type
        if rule.rule_type == RuleType.TIME_IN_BUSINESS:
            return self._evaluate_time_in_business(context)
        elif rule.rule_type == RuleType.MIN_REVENUE:
            return self._evaluate_min_revenue(context)
        elif rule.rule_type == RuleType.LEGAL_STRUCTURE:
            return self._evaluate_legal_structure(context)
        else:
            raise ValueError(
                f"BusinessEvaluator cannot handle rule type: {rule.rule_type.value}"
            )

    def _evaluate_time_in_business(
        self, context: EvaluationContext
    ) -> EvaluationResult:
        """
        Evaluate minimum time in business requirement.

        Criteria format: {"min_years": 2} or {"min_months": 24}

        Args:
            context: EvaluationContext

        Returns:
            EvaluationResult with scoring based on business age
        """
        rule = context.rule
        business = context.business
        criteria = rule.criteria

        # Extract minimum requirement (either years or months)
        min_years = self._extract_criteria_value(
            criteria, "min_years", required=False, default=None
        )
        min_months = self._extract_criteria_value(
            criteria, "min_months", required=False, default=None
        )

        if min_years is None and min_months is None:
            raise ValueError(
                "TIME_IN_BUSINESS rule requires either 'min_years' or 'min_months'"
            )

        # Convert to months for uniform comparison
        if min_years is not None:
            required_months = min_years * 12
        else:
            required_months = min_months

        # Calculate actual time in business
        today = date.today()
        established_date = business.established_date

        # Calculate months between dates
        actual_months = (
            (today.year - established_date.year) * 12
            + today.month
            - established_date.month
        )
        actual_years = actual_months / 12

        passed = actual_months >= required_months

        # Calculate score with partial credit
        if passed:
            score = self._calculate_score(True, rule.weight)
            reason = f"Business has been operating for {actual_years:.1f} years (requirement: {required_months/12:.1f} years)"
        else:
            # Award partial credit if within 6 months
            months_gap = required_months - actual_months
            if months_gap <= 6:
                partial_credit = Decimal(str(max(0, 1 - (months_gap / 6))))
                score = self._calculate_score(False, rule.weight, partial_credit)
            else:
                score = Decimal("0.00")

            reason = f"Business has only been operating for {actual_years:.1f} years (requirement: {required_months/12:.1f} years, gap: {months_gap} months)"

        return EvaluationResult(
            passed=passed,
            score=score,
            reason=reason,
            evidence={
                "actual_months": actual_months,
                "actual_years": round(actual_years, 2),
                "required_months": required_months,
                "required_years": round(required_months / 12, 2),
                "established_date": str(established_date),
                "gap_months": required_months - actual_months if not passed else 0,
            },
            weight=rule.weight,
            is_mandatory=rule.is_mandatory,
        )

    def _evaluate_min_revenue(self, context: EvaluationContext) -> EvaluationResult:
        """
        Evaluate minimum annual revenue requirement.

        Criteria format: {"min_amount": 250000}

        Args:
            context: EvaluationContext

        Returns:
            EvaluationResult with scoring
        """
        rule = context.rule
        business = context.business
        criteria = rule.criteria

        min_amount = Decimal(
            str(self._extract_criteria_value(criteria, "min_amount", required=True))
        )

        # Handle missing revenue
        if business.annual_revenue is None:
            return EvaluationResult(
                passed=False,
                score=Decimal("0.00"),
                reason=f"Annual revenue is required (minimum: ${min_amount:,.2f})",
                evidence={
                    "actual": None,
                    "required": float(min_amount),
                },
                weight=rule.weight,
                is_mandatory=rule.is_mandatory,
            )

        actual_revenue = business.annual_revenue
        passed = actual_revenue >= min_amount

        if passed:
            score = self._calculate_score(True, rule.weight)
            reason = f"Annual revenue ${actual_revenue:,.2f} meets minimum requirement of ${min_amount:,.2f}"
        else:
            # Award partial credit if within 20% of requirement
            revenue_gap = min_amount - actual_revenue
            percentage_gap = (revenue_gap / min_amount) * 100

            if percentage_gap <= 20:
                partial_credit = Decimal(str(max(0, 1 - (percentage_gap / 20))))
                score = self._calculate_score(False, rule.weight, partial_credit)
            else:
                score = Decimal("0.00")

            reason = f"Annual revenue ${actual_revenue:,.2f} is below minimum requirement of ${min_amount:,.2f} (gap: ${revenue_gap:,.2f})"

        return EvaluationResult(
            passed=passed,
            score=score,
            reason=reason,
            evidence={
                "actual": float(actual_revenue),
                "required": float(min_amount),
                "gap": float(min_amount - actual_revenue) if not passed else 0,
            },
            weight=rule.weight,
            is_mandatory=rule.is_mandatory,
        )

    def _evaluate_legal_structure(
        self, context: EvaluationContext
    ) -> EvaluationResult:
        """
        Evaluate business legal structure requirements.

        Criteria format: {"allowed_structures": ["LLC", "Corporation", "S-Corp"]}

        Args:
            context: EvaluationContext

        Returns:
            EvaluationResult indicating if structure is allowed
        """
        rule = context.rule
        business = context.business
        criteria = rule.criteria

        allowed_structures = self._extract_criteria_value(
            criteria, "allowed_structures", required=True
        )

        # Ensure it's a list
        if not isinstance(allowed_structures, list):
            allowed_structures = [allowed_structures]

        # Normalize for comparison (convert to enum values)
        normalized_allowed = []
        for structure in allowed_structures:
            if isinstance(structure, str):
                # Try to match enum value
                try:
                    enum_val = LegalStructure(structure)
                    normalized_allowed.append(enum_val.value)
                except ValueError:
                    # Keep original if not a valid enum
                    normalized_allowed.append(structure)
            else:
                normalized_allowed.append(structure)

        actual_structure = business.legal_structure.value
        passed = actual_structure in normalized_allowed

        if passed:
            score = self._calculate_score(True, rule.weight)
            reason = f"Business structure '{actual_structure}' is allowed"
        else:
            score = Decimal("0.00")
            reason = f"Business structure '{actual_structure}' is not allowed. Allowed: {', '.join(normalized_allowed)}"

        return EvaluationResult(
            passed=passed,
            score=score,
            reason=reason,
            evidence={
                "actual": actual_structure,
                "allowed": normalized_allowed,
            },
            weight=rule.weight,
            is_mandatory=rule.is_mandatory,
        )
