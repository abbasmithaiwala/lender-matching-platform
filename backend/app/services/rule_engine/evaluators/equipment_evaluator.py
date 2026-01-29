"""Equipment rule evaluator for equipment criteria."""

from datetime import datetime
from decimal import Decimal
from typing import List

from app.core.enums import Condition, RuleType
from app.services.rule_engine.base import (
    EvaluationContext,
    EvaluationResult,
    RuleEvaluator,
)


class EquipmentEvaluator(RuleEvaluator):
    """
    Evaluator for equipment-related rules.

    Handles:
    - EQUIPMENT_TYPE: Equipment type matching
    - EQUIPMENT_AGE: Maximum equipment age requirements
    - EQUIPMENT_CONDITION: Equipment condition requirements
    """

    def evaluate(self, context: EvaluationContext) -> EvaluationResult:
        """
        Evaluate equipment-related rules against the application context.

        Args:
            context: EvaluationContext containing all application data

        Returns:
            EvaluationResult with pass/fail, score, reason, and evidence

        Raises:
            ValueError: If rule type is not equipment-related or criteria are invalid
        """
        rule = context.rule

        # Route to appropriate handler based on rule type
        if rule.rule_type == RuleType.EQUIPMENT_TYPE:
            return self._evaluate_equipment_type(context)
        elif rule.rule_type == RuleType.EQUIPMENT_AGE:
            return self._evaluate_equipment_age(context)
        elif rule.rule_type == RuleType.EQUIPMENT_CONDITION:
            return self._evaluate_equipment_condition(context)
        else:
            raise ValueError(
                f"EquipmentEvaluator cannot handle rule type: {rule.rule_type.value}"
            )

    def _evaluate_equipment_type(
        self, context: EvaluationContext
    ) -> EvaluationResult:
        """
        Evaluate equipment type matching.

        Criteria format:
        - {"allowed_types": ["Construction", "Medical", "Transportation"]}
        - {"excluded_types": ["Aircraft", "Watercraft"]}

        Args:
            context: EvaluationContext

        Returns:
            EvaluationResult indicating if equipment type is allowed
        """
        rule = context.rule
        equipment = context.equipment
        criteria = rule.criteria

        allowed_types = self._extract_criteria_value(
            criteria, "allowed_types", required=False, default=None
        )
        excluded_types = self._extract_criteria_value(
            criteria, "excluded_types", required=False, default=None
        )

        if allowed_types is None and excluded_types is None:
            raise ValueError(
                "EQUIPMENT_TYPE rule requires either 'allowed_types' or 'excluded_types'"
            )

        equipment_type = equipment.equipment_type

        # Check exclusions first
        if excluded_types is not None:
            if not isinstance(excluded_types, list):
                excluded_types = [excluded_types]

            # Case-insensitive matching
            normalized_excluded = [et.lower() for et in excluded_types]
            if equipment_type.lower() in normalized_excluded:
                return EvaluationResult(
                    passed=False,
                    score=Decimal("0.00"),
                    reason=f"Equipment type '{equipment_type}' is excluded",
                    evidence={
                        "actual": equipment_type,
                        "excluded_types": excluded_types,
                    },
                    weight=rule.weight,
                    is_mandatory=rule.is_mandatory,
                )

        # Check allowed types
        if allowed_types is not None:
            if not isinstance(allowed_types, list):
                allowed_types = [allowed_types]

            # Case-insensitive matching
            normalized_allowed = [at.lower() for at in allowed_types]
            passed = equipment_type.lower() in normalized_allowed

            if passed:
                score = self._calculate_score(True, rule.weight)
                reason = f"Equipment type '{equipment_type}' is allowed"
            else:
                score = Decimal("0.00")
                reason = f"Equipment type '{equipment_type}' is not in allowed list: {', '.join(allowed_types)}"

            return EvaluationResult(
                passed=passed,
                score=score,
                reason=reason,
                evidence={
                    "actual": equipment_type,
                    "allowed_types": allowed_types,
                },
                weight=rule.weight,
                is_mandatory=rule.is_mandatory,
            )

        # If we reach here, no exclusions matched
        return EvaluationResult(
            passed=True,
            score=self._calculate_score(True, rule.weight),
            reason=f"Equipment type '{equipment_type}' is not excluded",
            evidence={
                "actual": equipment_type,
                "excluded_types": excluded_types,
            },
            weight=rule.weight,
            is_mandatory=rule.is_mandatory,
        )

    def _evaluate_equipment_age(self, context: EvaluationContext) -> EvaluationResult:
        """
        Evaluate maximum equipment age requirement.

        Criteria format: {"max_age_years": 15}

        Args:
            context: EvaluationContext

        Returns:
            EvaluationResult with scoring
        """
        rule = context.rule
        equipment = context.equipment
        criteria = rule.criteria

        max_age_years = self._extract_criteria_value(
            criteria, "max_age_years", required=True
        )

        # Calculate equipment age
        if equipment.year_manufactured is None:
            # If year not specified, check condition
            if equipment.condition == Condition.NEW:
                # New equipment has age 0
                actual_age = 0
            else:
                # Cannot determine age for used equipment without year
                return EvaluationResult(
                    passed=False,
                    score=Decimal("0.00"),
                    reason=f"Equipment year manufactured is required for age verification (maximum: {max_age_years} years)",
                    evidence={
                        "actual": None,
                        "required": max_age_years,
                    },
                    weight=rule.weight,
                    is_mandatory=rule.is_mandatory,
                )
        else:
            current_year = datetime.now().year
            actual_age = current_year - equipment.year_manufactured

        passed = actual_age <= max_age_years

        if passed:
            score = self._calculate_score(True, rule.weight)
            reason = f"Equipment age {actual_age} years is within maximum of {max_age_years} years"
        else:
            # Award partial credit if close (within 2 years)
            age_excess = actual_age - max_age_years
            if age_excess <= 2:
                partial_credit = Decimal(str(max(0, 1 - (age_excess / 2))))
                score = self._calculate_score(False, rule.weight, partial_credit)
            else:
                score = Decimal("0.00")

            reason = f"Equipment age {actual_age} years exceeds maximum of {max_age_years} years (excess: {age_excess} years)"

        return EvaluationResult(
            passed=passed,
            score=score,
            reason=reason,
            evidence={
                "actual": actual_age,
                "required": max_age_years,
                "year_manufactured": equipment.year_manufactured,
                "excess": actual_age - max_age_years if not passed else 0,
            },
            weight=rule.weight,
            is_mandatory=rule.is_mandatory,
        )

    def _evaluate_equipment_condition(
        self, context: EvaluationContext
    ) -> EvaluationResult:
        """
        Evaluate equipment condition requirements.

        Criteria format:
        - {"allowed_conditions": ["New", "Certified Pre-Owned"]}
        - {"excluded_conditions": ["Used"]}

        Args:
            context: EvaluationContext

        Returns:
            EvaluationResult indicating if condition meets requirements
        """
        rule = context.rule
        equipment = context.equipment
        criteria = rule.criteria

        allowed_conditions = self._extract_criteria_value(
            criteria, "allowed_conditions", required=False, default=None
        )
        excluded_conditions = self._extract_criteria_value(
            criteria, "excluded_conditions", required=False, default=None
        )

        if allowed_conditions is None and excluded_conditions is None:
            raise ValueError(
                "EQUIPMENT_CONDITION rule requires either 'allowed_conditions' or 'excluded_conditions'"
            )

        equipment_condition = equipment.condition.value

        # Check exclusions first
        if excluded_conditions is not None:
            if not isinstance(excluded_conditions, list):
                excluded_conditions = [excluded_conditions]

            # Normalize for comparison
            normalized_excluded = []
            for cond in excluded_conditions:
                if isinstance(cond, str):
                    try:
                        enum_val = Condition(cond)
                        normalized_excluded.append(enum_val.value)
                    except ValueError:
                        normalized_excluded.append(cond)

            if equipment_condition in normalized_excluded:
                return EvaluationResult(
                    passed=False,
                    score=Decimal("0.00"),
                    reason=f"Equipment condition '{equipment_condition}' is excluded",
                    evidence={
                        "actual": equipment_condition,
                        "excluded_conditions": excluded_conditions,
                    },
                    weight=rule.weight,
                    is_mandatory=rule.is_mandatory,
                )

        # Check allowed conditions
        if allowed_conditions is not None:
            if not isinstance(allowed_conditions, list):
                allowed_conditions = [allowed_conditions]

            # Normalize for comparison
            normalized_allowed = []
            for cond in allowed_conditions:
                if isinstance(cond, str):
                    try:
                        enum_val = Condition(cond)
                        normalized_allowed.append(enum_val.value)
                    except ValueError:
                        normalized_allowed.append(cond)

            passed = equipment_condition in normalized_allowed

            if passed:
                score = self._calculate_score(True, rule.weight)
                reason = f"Equipment condition '{equipment_condition}' is allowed"
            else:
                score = Decimal("0.00")
                reason = f"Equipment condition '{equipment_condition}' is not in allowed list: {', '.join(normalized_allowed)}"

            return EvaluationResult(
                passed=passed,
                score=score,
                reason=reason,
                evidence={
                    "actual": equipment_condition,
                    "allowed_conditions": normalized_allowed,
                },
                weight=rule.weight,
                is_mandatory=rule.is_mandatory,
            )

        # If we reach here, no exclusions matched
        return EvaluationResult(
            passed=True,
            score=self._calculate_score(True, rule.weight),
            reason=f"Equipment condition '{equipment_condition}' is not excluded",
            evidence={
                "actual": equipment_condition,
                "excluded_conditions": excluded_conditions,
            },
            weight=rule.weight,
            is_mandatory=rule.is_mandatory,
        )
