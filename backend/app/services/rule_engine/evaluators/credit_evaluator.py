"""Credit score rule evaluator for FICO and PayNet rules."""

from decimal import Decimal
from typing import Optional

from app.core.enums import RuleType
from app.services.rule_engine.base import (
    EvaluationContext,
    EvaluationResult,
    RuleEvaluator,
)


class CreditEvaluator(RuleEvaluator):
    """
    Evaluator for credit-related rules.

    Handles:
    - MIN_FICO: Minimum FICO score requirements
    - MIN_PAYNET: Minimum PayNet score requirements
    - CREDIT_TIER: Credit tier combination evaluation
    - MAX_CREDIT_UTILIZATION: Maximum credit utilization percentage
    """

    def evaluate(self, context: EvaluationContext) -> EvaluationResult:
        """
        Evaluate credit-related rules against the application context.

        Args:
            context: EvaluationContext containing all application data

        Returns:
            EvaluationResult with pass/fail, score, reason, and evidence

        Raises:
            ValueError: If rule type is not credit-related or criteria are invalid
        """
        rule = context.rule
        guarantor = context.guarantor

        # Route to appropriate handler based on rule type
        if rule.rule_type == RuleType.MIN_FICO:
            return self._evaluate_min_fico(context)
        elif rule.rule_type == RuleType.MIN_PAYNET:
            return self._evaluate_min_paynet(context)
        elif rule.rule_type == RuleType.CREDIT_TIER:
            return self._evaluate_credit_tier(context)
        elif rule.rule_type == RuleType.MAX_CREDIT_UTILIZATION:
            return self._evaluate_max_credit_utilization(context)
        else:
            raise ValueError(
                f"CreditEvaluator cannot handle rule type: {rule.rule_type.value}"
            )

    def _evaluate_min_fico(self, context: EvaluationContext) -> EvaluationResult:
        """
        Evaluate minimum FICO score requirement.

        Criteria format: {"min_score": 680}

        Args:
            context: EvaluationContext

        Returns:
            EvaluationResult with scoring based on how close actual is to required
        """
        rule = context.rule
        guarantor = context.guarantor
        criteria = rule.criteria

        min_score = self._extract_criteria_value(criteria, "min_score", required=True)

        # Handle missing FICO score
        if guarantor.fico_score is None:
            return EvaluationResult(
                passed=False,
                score=Decimal("0.00"),
                reason=f"FICO score is required (minimum: {min_score})",
                evidence={
                    "actual": None,
                    "required": min_score,
                },
                weight=rule.weight,
                is_mandatory=rule.is_mandatory,
            )

        actual_score = guarantor.fico_score
        passed = actual_score >= min_score

        # Calculate score with partial credit if close
        if passed:
            score = self._calculate_score(True, rule.weight)
            reason = f"FICO score {actual_score} meets minimum requirement of {min_score}"
        else:
            # Award partial credit if within 50 points
            score_gap = min_score - actual_score
            if score_gap <= 50:
                partial_credit = Decimal(str(max(0, 1 - (score_gap / 50))))
                score = self._calculate_score(False, rule.weight, partial_credit)
            else:
                score = Decimal("0.00")

            reason = f"FICO score {actual_score} is below minimum requirement of {min_score} (gap: {score_gap})"

        return EvaluationResult(
            passed=passed,
            score=score,
            reason=reason,
            evidence={
                "actual": actual_score,
                "required": min_score,
                "gap": min_score - actual_score if not passed else 0,
            },
            weight=rule.weight,
            is_mandatory=rule.is_mandatory,
        )

    def _evaluate_min_paynet(self, context: EvaluationContext) -> EvaluationResult:
        """
        Evaluate minimum PayNet score requirement.

        Criteria format: {"min_score": 70}

        Args:
            context: EvaluationContext

        Returns:
            EvaluationResult with scoring
        """
        rule = context.rule
        guarantor = context.guarantor
        criteria = rule.criteria

        min_score = self._extract_criteria_value(criteria, "min_score", required=True)

        # Handle missing PayNet score
        if guarantor.paynet_score is None:
            return EvaluationResult(
                passed=False,
                score=Decimal("0.00"),
                reason=f"PayNet score is required (minimum: {min_score})",
                evidence={
                    "actual": None,
                    "required": min_score,
                },
                weight=rule.weight,
                is_mandatory=rule.is_mandatory,
            )

        actual_score = guarantor.paynet_score
        passed = actual_score >= min_score

        # Calculate score with partial credit if close
        if passed:
            score = self._calculate_score(True, rule.weight)
            reason = f"PayNet score {actual_score} meets minimum requirement of {min_score}"
        else:
            # Award partial credit if within 20 points
            score_gap = min_score - actual_score
            if score_gap <= 20:
                partial_credit = Decimal(str(max(0, 1 - (score_gap / 20))))
                score = self._calculate_score(False, rule.weight, partial_credit)
            else:
                score = Decimal("0.00")

            reason = f"PayNet score {actual_score} is below minimum requirement of {min_score} (gap: {score_gap})"

        return EvaluationResult(
            passed=passed,
            score=score,
            reason=reason,
            evidence={
                "actual": actual_score,
                "required": min_score,
                "gap": min_score - actual_score if not passed else 0,
            },
            weight=rule.weight,
            is_mandatory=rule.is_mandatory,
        )

    def _evaluate_credit_tier(self, context: EvaluationContext) -> EvaluationResult:
        """
        Evaluate credit tier combination requirements.

        Criteria format:
        {
            "min_fico": 680,
            "min_paynet": 70,
            "tier_name": "Prime"
        }

        Both scores must meet their minimums to pass.

        Args:
            context: EvaluationContext

        Returns:
            EvaluationResult combining both credit scores
        """
        rule = context.rule
        guarantor = context.guarantor
        criteria = rule.criteria

        min_fico = self._extract_criteria_value(
            criteria, "min_fico", required=False, default=None
        )
        min_paynet = self._extract_criteria_value(
            criteria, "min_paynet", required=False, default=None
        )
        tier_name = self._extract_criteria_value(
            criteria, "tier_name", required=False, default="Unknown"
        )

        reasons = []
        passed_checks = []
        failed_checks = []

        # Check FICO if specified
        if min_fico is not None:
            if guarantor.fico_score is None:
                failed_checks.append("FICO score missing")
                reasons.append(f"FICO score required (min: {min_fico})")
            elif guarantor.fico_score >= min_fico:
                passed_checks.append(f"FICO {guarantor.fico_score} >= {min_fico}")
            else:
                failed_checks.append(
                    f"FICO {guarantor.fico_score} < {min_fico}"
                )
                reasons.append(
                    f"FICO score {guarantor.fico_score} below {min_fico}"
                )

        # Check PayNet if specified
        if min_paynet is not None:
            if guarantor.paynet_score is None:
                failed_checks.append("PayNet score missing")
                reasons.append(f"PayNet score required (min: {min_paynet})")
            elif guarantor.paynet_score >= min_paynet:
                passed_checks.append(
                    f"PayNet {guarantor.paynet_score} >= {min_paynet}"
                )
            else:
                failed_checks.append(
                    f"PayNet {guarantor.paynet_score} < {min_paynet}"
                )
                reasons.append(
                    f"PayNet score {guarantor.paynet_score} below {min_paynet}"
                )

        # Determine overall pass/fail
        passed = len(failed_checks) == 0

        if passed:
            score = self._calculate_score(True, rule.weight)
            reason = f"{tier_name} credit tier requirements met: {', '.join(passed_checks)}"
        else:
            score = Decimal("0.00")
            reason = f"{tier_name} credit tier not met: {', '.join(failed_checks)}"

        return EvaluationResult(
            passed=passed,
            score=score,
            reason=reason,
            evidence={
                "tier_name": tier_name,
                "required": {
                    "min_fico": min_fico,
                    "min_paynet": min_paynet,
                },
                "actual": {
                    "fico": guarantor.fico_score,
                    "paynet": guarantor.paynet_score,
                },
                "passed_checks": passed_checks,
                "failed_checks": failed_checks,
            },
            weight=rule.weight,
            is_mandatory=rule.is_mandatory,
        )

    def _evaluate_max_credit_utilization(
        self, context: EvaluationContext
    ) -> EvaluationResult:
        """
        Evaluate maximum credit utilization percentage.

        Criteria format: {"max_percentage": 75.0}

        Args:
            context: EvaluationContext

        Returns:
            EvaluationResult with scoring
        """
        rule = context.rule
        guarantor = context.guarantor
        criteria = rule.criteria

        max_percentage = Decimal(
            str(self._extract_criteria_value(criteria, "max_percentage", required=True))
        )

        # Handle missing credit utilization
        if guarantor.credit_utilization_percentage is None:
            # If not specified, assume it passes (many applications won't have this)
            if not rule.is_mandatory:
                return EvaluationResult(
                    passed=True,
                    score=self._calculate_score(True, rule.weight),
                    reason="Credit utilization not provided, assuming acceptable",
                    evidence={
                        "actual": None,
                        "required": float(max_percentage),
                    },
                    weight=rule.weight,
                    is_mandatory=rule.is_mandatory,
                )
            else:
                return EvaluationResult(
                    passed=False,
                    score=Decimal("0.00"),
                    reason=f"Credit utilization is required (maximum: {max_percentage}%)",
                    evidence={
                        "actual": None,
                        "required": float(max_percentage),
                    },
                    weight=rule.weight,
                    is_mandatory=rule.is_mandatory,
                )

        actual_percentage = guarantor.credit_utilization_percentage
        passed = actual_percentage <= max_percentage

        if passed:
            score = self._calculate_score(True, rule.weight)
            reason = f"Credit utilization {actual_percentage}% is within maximum of {max_percentage}%"
        else:
            score = Decimal("0.00")
            reason = f"Credit utilization {actual_percentage}% exceeds maximum of {max_percentage}%"

        return EvaluationResult(
            passed=passed,
            score=score,
            reason=reason,
            evidence={
                "actual": float(actual_percentage),
                "required": float(max_percentage),
                "excess": float(actual_percentage - max_percentage) if not passed else 0,
            },
            weight=rule.weight,
            is_mandatory=rule.is_mandatory,
        )
