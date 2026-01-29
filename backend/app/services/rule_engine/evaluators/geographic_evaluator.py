"""Geographic and industry rule evaluator.

Note: Lender-level exclusions (excluded_states, excluded_industries) are
checked in Tier 1 of the matching engine. This evaluator handles rule-level
geographic and industry criteria for specific programs.
"""

from decimal import Decimal
from typing import List

from app.core.enums import RuleType
from app.services.rule_engine.base import (
    EvaluationContext,
    EvaluationResult,
    RuleEvaluator,
)


class GeographicEvaluator(RuleEvaluator):
    """
    Evaluator for geographic and industry-related rules.

    Handles:
    - EXCLUDED_STATES: State exclusions (rule-level)
    - EXCLUDED_INDUSTRIES: Industry exclusions (rule-level)
    - ALLOWED_STATES: State requirements (rule-level)
    - ALLOWED_INDUSTRIES: Industry requirements (rule-level)

    Note: Lender-level exclusions are handled separately in Matcher Tier 1.
    """

    def evaluate(self, context: EvaluationContext) -> EvaluationResult:
        """
        Evaluate geographic/industry rules against the application context.

        Args:
            context: EvaluationContext containing all application data

        Returns:
            EvaluationResult with pass/fail, score, reason, and evidence

        Raises:
            ValueError: If rule type is not geographic/industry-related or criteria are invalid
        """
        rule = context.rule

        # Route to appropriate handler based on rule type
        if rule.rule_type == RuleType.EXCLUDED_STATES:
            return self._evaluate_excluded_states(context)
        elif rule.rule_type == RuleType.EXCLUDED_INDUSTRIES:
            return self._evaluate_excluded_industries(context)
        elif rule.rule_type == RuleType.ALLOWED_STATES:
            return self._evaluate_allowed_states(context)
        elif rule.rule_type == RuleType.ALLOWED_INDUSTRIES:
            return self._evaluate_allowed_industries(context)
        else:
            raise ValueError(
                f"GeographicEvaluator cannot handle rule type: {rule.rule_type.value}"
            )

    def _evaluate_excluded_states(
        self, context: EvaluationContext
    ) -> EvaluationResult:
        """
        Evaluate state exclusions (rule-level).

        Criteria format: {"states": ["CA", "NV", "ND"]}

        Args:
            context: EvaluationContext

        Returns:
            EvaluationResult indicating if state is excluded
        """
        rule = context.rule
        business = context.business
        criteria = rule.criteria

        excluded_states = self._extract_criteria_value(
            criteria, "states", required=True
        )

        # Ensure it's a list
        if not isinstance(excluded_states, list):
            excluded_states = [excluded_states]

        # Normalize state codes to uppercase
        normalized_excluded = [state.upper() for state in excluded_states]
        business_state = business.state.upper()

        # Pass if NOT in excluded list
        passed = business_state not in normalized_excluded

        if passed:
            score = self._calculate_score(True, rule.weight)
            reason = f"Business state '{business_state}' is not excluded"
        else:
            score = Decimal("0.00")
            reason = f"Business state '{business_state}' is excluded by this program"

        return EvaluationResult(
            passed=passed,
            score=score,
            reason=reason,
            evidence={
                "actual": business_state,
                "excluded_states": normalized_excluded,
            },
            weight=rule.weight,
            is_mandatory=rule.is_mandatory,
        )

    def _evaluate_excluded_industries(
        self, context: EvaluationContext
    ) -> EvaluationResult:
        """
        Evaluate industry exclusions (rule-level).

        Criteria format: {"industries": ["Cannabis", "Gambling", "Adult Entertainment"]}

        Args:
            context: EvaluationContext

        Returns:
            EvaluationResult indicating if industry is excluded
        """
        rule = context.rule
        business = context.business
        criteria = rule.criteria

        excluded_industries = self._extract_criteria_value(
            criteria, "industries", required=True
        )

        # Ensure it's a list
        if not isinstance(excluded_industries, list):
            excluded_industries = [excluded_industries]

        # Normalize for case-insensitive comparison
        normalized_excluded = [industry.lower() for industry in excluded_industries]
        business_industry = business.industry.lower()

        # Pass if NOT in excluded list
        passed = business_industry not in normalized_excluded

        if passed:
            score = self._calculate_score(True, rule.weight)
            reason = f"Business industry '{business.industry}' is not excluded"
        else:
            score = Decimal("0.00")
            reason = f"Business industry '{business.industry}' is excluded by this program"

        return EvaluationResult(
            passed=passed,
            score=score,
            reason=reason,
            evidence={
                "actual": business.industry,
                "excluded_industries": excluded_industries,
            },
            weight=rule.weight,
            is_mandatory=rule.is_mandatory,
        )

    def _evaluate_allowed_states(
        self, context: EvaluationContext
    ) -> EvaluationResult:
        """
        Evaluate state requirements (rule-level).

        Criteria format: {"states": ["TX", "FL", "GA"]}

        Args:
            context: EvaluationContext

        Returns:
            EvaluationResult indicating if state is allowed
        """
        rule = context.rule
        business = context.business
        criteria = rule.criteria

        allowed_states = self._extract_criteria_value(
            criteria, "states", required=True
        )

        # Ensure it's a list
        if not isinstance(allowed_states, list):
            allowed_states = [allowed_states]

        # Normalize state codes to uppercase
        normalized_allowed = [state.upper() for state in allowed_states]
        business_state = business.state.upper()

        # Pass if in allowed list
        passed = business_state in normalized_allowed

        if passed:
            score = self._calculate_score(True, rule.weight)
            reason = f"Business state '{business_state}' is in allowed list"
        else:
            score = Decimal("0.00")
            reason = f"Business state '{business_state}' is not in allowed list: {', '.join(normalized_allowed)}"

        return EvaluationResult(
            passed=passed,
            score=score,
            reason=reason,
            evidence={
                "actual": business_state,
                "allowed_states": normalized_allowed,
            },
            weight=rule.weight,
            is_mandatory=rule.is_mandatory,
        )

    def _evaluate_allowed_industries(
        self, context: EvaluationContext
    ) -> EvaluationResult:
        """
        Evaluate industry requirements (rule-level).

        Criteria format: {"industries": ["Medical", "Healthcare", "Dental"]}

        Args:
            context: EvaluationContext

        Returns:
            EvaluationResult indicating if industry is allowed
        """
        rule = context.rule
        business = context.business
        criteria = rule.criteria

        allowed_industries = self._extract_criteria_value(
            criteria, "industries", required=True
        )

        # Ensure it's a list
        if not isinstance(allowed_industries, list):
            allowed_industries = [allowed_industries]

        # Normalize for case-insensitive comparison
        normalized_allowed = [industry.lower() for industry in allowed_industries]
        business_industry = business.industry.lower()

        # Pass if in allowed list
        passed = business_industry in normalized_allowed

        if passed:
            score = self._calculate_score(True, rule.weight)
            reason = f"Business industry '{business.industry}' is in allowed list"
        else:
            score = Decimal("0.00")
            reason = f"Business industry '{business.industry}' is not in allowed list: {', '.join(allowed_industries)}"

        return EvaluationResult(
            passed=passed,
            score=score,
            reason=reason,
            evidence={
                "actual": business.industry,
                "allowed_industries": allowed_industries,
            },
            weight=rule.weight,
            is_mandatory=rule.is_mandatory,
        )
