"""Scoring and ranking logic for lender matching."""

from decimal import Decimal
from typing import Dict, Any, List, Optional

from app.models.domain.lender import PolicyProgram
from app.services.rule_engine.base import EvaluationResult


class ScoringEngine:
    """
    Scoring engine for calculating fit scores and estimating rates.

    Provides weighted scoring algorithms, rate estimation based on credit tiers,
    and approval probability heuristics for lender matching.
    """

    @staticmethod
    def calculate_fit_score(
        evaluation_results: List[EvaluationResult],
        program: PolicyProgram,
    ) -> Decimal:
        """
        Calculate weighted fit score from rule evaluation results.

        The fit score is calculated as a weighted average of all rule scores,
        normalized to a 0-100 scale. Mandatory rules that fail result in a score of 0.

        Args:
            evaluation_results: List of evaluation results from rule engine
            program: The policy program being evaluated

        Returns:
            Fit score between 0 and 100
        """
        # Check if any mandatory rules failed
        for result in evaluation_results:
            if result.is_mandatory and not result.passed:
                return Decimal("0.00")

        # If no rules, return 0
        if not evaluation_results:
            return Decimal("0.00")

        # Calculate weighted score
        total_weighted_score = Decimal("0.00")
        total_weight = Decimal("0.00")

        for result in evaluation_results:
            # Score is already 0-1 from evaluators, multiply by weight
            weighted_score = Decimal(str(result.score)) * result.weight
            total_weighted_score += weighted_score
            total_weight += result.weight

        # Avoid division by zero
        if total_weight == 0:
            return Decimal("0.00")

        # Calculate average and scale to 0-100
        average_score = total_weighted_score / total_weight
        fit_score = average_score * Decimal("100")

        # Ensure score is within bounds
        return max(Decimal("0.00"), min(Decimal("100.00"), fit_score))

    @staticmethod
    def estimate_rate(
        program: PolicyProgram,
        loan_amount: Decimal,
        equipment_age_years: Optional[int] = None,
        fico_score: Optional[int] = None,
    ) -> Optional[Decimal]:
        """
        Estimate interest rate based on program rate metadata.

        Uses rate_metadata JSONB to find base rates and apply adjustments
        based on equipment age, credit score, etc.

        Example rate_metadata structure:
        {
            "base_rates": [
                {"min_amount": 10000, "max_amount": 50000, "rate": 7.25},
                {"min_amount": 50001, "max_amount": 100000, "rate": 6.75}
            ],
            "adjustments": [
                {"condition": "equipment_age > 15", "delta": 0.5},
                {"condition": "fico < 680", "delta": 1.0}
            ]
        }

        Args:
            program: Policy program with rate_metadata
            loan_amount: Requested loan amount
            equipment_age_years: Age of equipment in years (optional)
            fico_score: FICO credit score (optional)

        Returns:
            Estimated rate as decimal (e.g., 7.25 for 7.25%), or None if cannot estimate
        """
        rate_metadata = program.rate_metadata
        if not rate_metadata or not isinstance(rate_metadata, dict):
            return None

        # Find base rate from rate table
        base_rate = ScoringEngine._find_base_rate(rate_metadata, loan_amount)
        if base_rate is None:
            return None

        # Apply adjustments
        adjustments = rate_metadata.get("adjustments", [])
        total_adjustment = Decimal("0.00")

        for adjustment in adjustments:
            if not isinstance(adjustment, dict):
                continue

            condition = adjustment.get("condition", "")
            delta = adjustment.get("delta", 0)

            # Evaluate simple conditions
            if ScoringEngine._evaluate_adjustment_condition(
                condition, equipment_age_years, fico_score
            ):
                total_adjustment += Decimal(str(delta))

        final_rate = Decimal(str(base_rate)) + total_adjustment

        # Ensure rate is positive
        return max(Decimal("0.00"), final_rate)

    @staticmethod
    def _find_base_rate(
        rate_metadata: Dict[str, Any], loan_amount: Decimal
    ) -> Optional[float]:
        """
        Find base rate from rate table based on loan amount.

        Args:
            rate_metadata: Rate metadata JSONB
            loan_amount: Loan amount to find rate for

        Returns:
            Base rate if found, None otherwise
        """
        base_rates = rate_metadata.get("base_rates", [])
        if not isinstance(base_rates, list):
            return None

        for rate_entry in base_rates:
            if not isinstance(rate_entry, dict):
                continue

            min_amount = rate_entry.get("min_amount")
            max_amount = rate_entry.get("max_amount")
            rate = rate_entry.get("rate")

            if min_amount is None or max_amount is None or rate is None:
                continue

            # Check if loan amount falls within this range
            min_dec = Decimal(str(min_amount))
            max_dec = Decimal(str(max_amount))

            if min_dec <= loan_amount <= max_dec:
                return float(rate)

        return None

    @staticmethod
    def _evaluate_adjustment_condition(
        condition: str,
        equipment_age_years: Optional[int],
        fico_score: Optional[int],
    ) -> bool:
        """
        Evaluate a simple adjustment condition.

        Supports conditions like:
        - "equipment_age > 15"
        - "fico < 680"
        - "equipment_age >= 10"

        Args:
            condition: Condition string
            equipment_age_years: Equipment age in years
            fico_score: FICO credit score

        Returns:
            True if condition is met, False otherwise
        """
        if not condition:
            return False

        condition = condition.strip().lower()

        # Equipment age conditions
        if "equipment_age" in condition:
            if equipment_age_years is None:
                return False

            if ">" in condition:
                try:
                    if ">=" in condition:
                        threshold = int(condition.split(">=")[1].strip())
                        return equipment_age_years >= threshold
                    else:
                        threshold = int(condition.split(">")[1].strip())
                        return equipment_age_years > threshold
                except (ValueError, IndexError):
                    return False

            if "<" in condition:
                try:
                    if "<=" in condition:
                        threshold = int(condition.split("<=")[1].strip())
                        return equipment_age_years <= threshold
                    else:
                        threshold = int(condition.split("<")[1].strip())
                        return equipment_age_years < threshold
                except (ValueError, IndexError):
                    return False

        # FICO score conditions
        if "fico" in condition:
            if fico_score is None:
                return False

            if ">" in condition:
                try:
                    if ">=" in condition:
                        threshold = int(condition.split(">=")[1].strip())
                        return fico_score >= threshold
                    else:
                        threshold = int(condition.split(">")[1].strip())
                        return fico_score > threshold
                except (ValueError, IndexError):
                    return False

            if "<" in condition:
                try:
                    if "<=" in condition:
                        threshold = int(condition.split("<=")[1].strip())
                        return fico_score <= threshold
                    else:
                        threshold = int(condition.split("<")[1].strip())
                        return fico_score < threshold
                except (ValueError, IndexError):
                    return False

        return False

    @staticmethod
    def calculate_approval_probability(
        fit_score: Decimal,
        mandatory_rules_passed: bool,
    ) -> Decimal:
        """
        Calculate approval probability heuristic based on fit score.

        This is a simplified heuristic. Real-world systems would use
        historical data and machine learning models.

        Logic:
        - If any mandatory rules failed: 0% probability
        - 90-100 fit score: 90-100% probability
        - 80-89 fit score: 70-89% probability
        - 70-79 fit score: 50-69% probability
        - 60-69 fit score: 30-49% probability
        - Below 60: 10-29% probability

        Args:
            fit_score: Calculated fit score (0-100)
            mandatory_rules_passed: Whether all mandatory rules passed

        Returns:
            Approval probability as percentage (0-100)
        """
        if not mandatory_rules_passed:
            return Decimal("0.00")

        if fit_score >= 90:
            # High fit: 90-100% probability
            # Linear interpolation: 90 + (score - 90) * 1
            probability = Decimal("90.00") + (fit_score - Decimal("90.00"))
            return min(Decimal("100.00"), probability)

        if fit_score >= 80:
            # Good fit: 70-89% probability
            # Linear interpolation
            range_size = Decimal("19.00")  # 89 - 70
            score_in_range = fit_score - Decimal("80.00")
            probability = Decimal("70.00") + (score_in_range / Decimal("10.00")) * range_size
            return probability

        if fit_score >= 70:
            # Moderate fit: 50-69% probability
            range_size = Decimal("19.00")  # 69 - 50
            score_in_range = fit_score - Decimal("70.00")
            probability = Decimal("50.00") + (score_in_range / Decimal("10.00")) * range_size
            return probability

        if fit_score >= 60:
            # Low fit: 30-49% probability
            range_size = Decimal("19.00")  # 49 - 30
            score_in_range = fit_score - Decimal("60.00")
            probability = Decimal("30.00") + (score_in_range / Decimal("10.00")) * range_size
            return probability

        # Very low fit: 10-29% probability
        range_size = Decimal("19.00")  # 29 - 10
        score_in_range = fit_score
        if score_in_range > Decimal("60.00"):
            score_in_range = Decimal("60.00")
        probability = Decimal("10.00") + (score_in_range / Decimal("60.00")) * range_size
        return max(Decimal("10.00"), probability)

    @staticmethod
    def rank_programs_by_score(
        program_scores: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Rank programs by fit score in descending order.

        Args:
            program_scores: List of dicts with at least {"program": ..., "fit_score": ...}

        Returns:
            Sorted list of program scores (highest first)
        """
        return sorted(
            program_scores,
            key=lambda x: x.get("fit_score", Decimal("0.00")),
            reverse=True,
        )

    @staticmethod
    def calculate_credit_tier_score(
        fico_score: Optional[int],
        paynet_score: Optional[int],
    ) -> str:
        """
        Determine credit tier based on FICO and PayNet scores.

        This is a simplified credit tier classification.
        Real-world systems would use more sophisticated algorithms.

        Tiers:
        - Prime: FICO >= 720 or PayNet >= 80
        - Near Prime: FICO 680-719 or PayNet 60-79
        - Subprime: FICO 640-679 or PayNet 40-59
        - Deep Subprime: FICO < 640 or PayNet < 40

        Args:
            fico_score: FICO credit score (300-850)
            paynet_score: PayNet score (1-100)

        Returns:
            Credit tier string (Prime, Near Prime, Subprime, Deep Subprime)
        """
        # If both scores available, use the better tier
        tiers = []

        if fico_score is not None:
            if fico_score >= 720:
                tiers.append("Prime")
            elif fico_score >= 680:
                tiers.append("Near Prime")
            elif fico_score >= 640:
                tiers.append("Subprime")
            else:
                tiers.append("Deep Subprime")

        if paynet_score is not None:
            if paynet_score >= 80:
                tiers.append("Prime")
            elif paynet_score >= 60:
                tiers.append("Near Prime")
            elif paynet_score >= 40:
                tiers.append("Subprime")
            else:
                tiers.append("Deep Subprime")

        if not tiers:
            return "Unknown"

        # Return the best tier
        tier_priority = {"Prime": 0, "Near Prime": 1, "Subprime": 2, "Deep Subprime": 3}
        best_tier = min(tiers, key=lambda t: tier_priority.get(t, 99))
        return best_tier
