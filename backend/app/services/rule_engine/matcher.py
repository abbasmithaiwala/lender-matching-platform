"""Three-tier matching algorithm for lender-application matching."""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional, Dict, Any

from app.models.domain.application import LoanApplication
from app.models.domain.lender import Lender, PolicyProgram
from app.services.rule_engine.base import EvaluationResult
from app.services.rule_engine.engine import RuleEngine, ProgramEvaluationResult
from app.services.rule_engine.scoring import ScoringEngine


@dataclass
class MatchResult:
    """
    Result of matching an application to a lender program.

    Attributes:
        lender: The lender
        program: The matched program (or None if rejected at Tier 1)
        is_eligible: Overall eligibility
        fit_score: Calculated fit score (0-100)
        rejection_reason: Reason if rejected (None if eligible)
        rejection_tier: Which tier rejected (1, 2, 3, or None)
        estimated_rate: Estimated interest rate
        approval_probability: Estimated approval probability
        rule_evaluations: List of rule evaluation results (Tier 3 only)
    """

    lender: Lender
    program: Optional[PolicyProgram]
    is_eligible: bool
    fit_score: Decimal
    rejection_reason: Optional[str]
    rejection_tier: Optional[int]
    estimated_rate: Optional[Decimal]
    approval_probability: Decimal
    rule_evaluations: List[tuple[Any, EvaluationResult]]


class Matcher:
    """
    Three-tier matching algorithm for lender-application matching.

    Tier 1: Fast lender-level filtering
        - Check excluded_states
        - Check excluded_industries
        - Check loan amount range
        - Early exit for ineligible lenders (performance optimization)

    Tier 2: Program eligibility & selection
        - Check program.eligibility_conditions JSONB
        - Select best matching program per lender

    Tier 3: Detailed rule evaluation & scoring
        - Run rule engine on program rules
        - Calculate weighted fit score
        - Rank results by score
    """

    def __init__(self):
        """Initialize the matcher with rule engine and scoring engine."""
        self.rule_engine = RuleEngine()
        self.scoring_engine = ScoringEngine()

    def match_application_to_lenders(
        self,
        application: LoanApplication,
        lenders: List[Lender],
    ) -> List[MatchResult]:
        """
        Match an application against multiple lenders using three-tier algorithm.

        Args:
            application: Loan application with all relations loaded
            lenders: List of lenders with programs and rules loaded

        Returns:
            List of match results, sorted by fit score (eligible first, then ineligible)

        Raises:
            ValueError: If application is missing required data
        """
        # Validate application has required relationships
        if not application.business:
            raise ValueError("Application must have business relationship loaded")
        if not application.guarantor:
            raise ValueError("Application must have guarantor relationship loaded")
        if not application.equipment:
            raise ValueError("Application must have equipment relationship loaded")

        results: List[MatchResult] = []

        for lender in lenders:
            # Tier 1: Lender-level fast filtering
            tier1_result = self._tier1_lender_filtering(application, lender)

            if not tier1_result["passed"]:
                # Lender rejected at Tier 1
                results.append(
                    MatchResult(
                        lender=lender,
                        program=None,
                        is_eligible=False,
                        fit_score=Decimal("0.00"),
                        rejection_reason=tier1_result["reason"],
                        rejection_tier=1,
                        estimated_rate=None,
                        approval_probability=Decimal("0.00"),
                        rule_evaluations=[],
                    )
                )
                continue  # Early exit optimization

            # Tier 2: Program eligibility & selection
            eligible_programs = self._tier2_program_selection(application, lender)

            if not eligible_programs:
                # No eligible programs found
                results.append(
                    MatchResult(
                        lender=lender,
                        program=None,
                        is_eligible=False,
                        fit_score=Decimal("0.00"),
                        rejection_reason="No eligible programs match application criteria",
                        rejection_tier=2,
                        estimated_rate=None,
                        approval_probability=Decimal("0.00"),
                        rule_evaluations=[],
                    )
                )
                continue

            # Tier 3: Detailed rule evaluation for each eligible program
            best_match = None
            best_score = Decimal("-1.00")

            for program in eligible_programs:
                tier3_result = self._tier3_rule_evaluation(application, program)

                # Keep the program with the highest fit score
                if tier3_result.fit_score > best_score:
                    best_score = tier3_result.fit_score
                    best_match = tier3_result

            # Create match result for the best program
            if best_match:
                # Estimate rate
                estimated_rate = self.scoring_engine.estimate_rate(
                    program=best_match.program,
                    loan_amount=application.requested_amount,
                    equipment_age_years=application.equipment.age_years,
                    fico_score=application.guarantor.fico_score,
                )

                # Calculate approval probability
                approval_probability = self.scoring_engine.calculate_approval_probability(
                    fit_score=best_match.fit_score,
                    mandatory_rules_passed=best_match.mandatory_rules_passed,
                )

                # Determine rejection reason if not eligible
                rejection_reason = None
                rejection_tier = None
                if not best_match.is_eligible:
                    rejection_tier = 3
                    failed_mandatory = [
                        (rule, result)
                        for rule, result in best_match.rule_results
                        if result.is_mandatory and not result.passed
                    ]
                    if failed_mandatory:
                        reasons = [result.reason for _, result in failed_mandatory]
                        rejection_reason = "; ".join(reasons)
                    elif best_match.fit_score < best_match.program.min_fit_score:
                        rejection_reason = (
                            f"Fit score {best_match.fit_score} below minimum "
                            f"{best_match.program.min_fit_score}"
                        )
                    else:
                        rejection_reason = "Failed to meet program requirements"

                results.append(
                    MatchResult(
                        lender=lender,
                        program=best_match.program,
                        is_eligible=best_match.is_eligible,
                        fit_score=best_match.fit_score,
                        rejection_reason=rejection_reason,
                        rejection_tier=rejection_tier,
                        estimated_rate=estimated_rate,
                        approval_probability=approval_probability,
                        rule_evaluations=best_match.rule_results,
                    )
                )

        # Sort results: eligible first (by score desc), then ineligible (by score desc)
        results.sort(
            key=lambda x: (not x.is_eligible, -x.fit_score)
        )

        return results

    def _tier1_lender_filtering(
        self,
        application: LoanApplication,
        lender: Lender,
    ) -> Dict[str, Any]:
        """
        Tier 1: Fast lender-level filtering.

        Checks:
        1. Lender is active
        2. State not in excluded_states
        3. Industry not in excluded_industries
        4. Loan amount within lender's range

        Args:
            application: Loan application
            lender: Lender to check

        Returns:
            Dict with {"passed": bool, "reason": Optional[str]}
        """
        # Check if lender is active
        if not lender.active:
            return {
                "passed": False,
                "reason": f"Lender {lender.name} is not active",
            }

        business = application.business

        # Check excluded states
        if lender.excluded_states and business.state in lender.excluded_states:
            return {
                "passed": False,
                "reason": f"Business state {business.state} is excluded by lender",
            }

        # Check excluded industries
        if lender.excluded_industries:
            # Case-insensitive check
            excluded_lower = [ind.lower() for ind in lender.excluded_industries]
            if business.industry.lower() in excluded_lower:
                return {
                    "passed": False,
                    "reason": f"Business industry {business.industry} is excluded by lender",
                }

        # Check loan amount range
        requested_amount = application.requested_amount

        if lender.min_loan_amount and requested_amount < lender.min_loan_amount:
            return {
                "passed": False,
                "reason": (
                    f"Requested amount ${requested_amount} below lender minimum "
                    f"${lender.min_loan_amount}"
                ),
            }

        if lender.max_loan_amount and requested_amount > lender.max_loan_amount:
            return {
                "passed": False,
                "reason": (
                    f"Requested amount ${requested_amount} exceeds lender maximum "
                    f"${lender.max_loan_amount}"
                ),
            }

        return {"passed": True, "reason": None}

    def _tier2_program_selection(
        self,
        application: LoanApplication,
        lender: Lender,
    ) -> List[PolicyProgram]:
        """
        Tier 2: Program eligibility & selection.

        Checks program.eligibility_conditions JSONB to determine which programs
        are applicable for this application.

        Example eligibility_conditions:
        - {"requires_paynet": true} - Only if PayNet score exists
        - {"legal_structure": ["Corp", "S-Corp"]} - Only for specific structures
        - {"industry": ["Medical", "Healthcare"]} - Only for specific industries

        Args:
            application: Loan application
            lender: Lender with programs

        Returns:
            List of eligible programs
        """
        eligible_programs: List[PolicyProgram] = []

        # Get active programs
        active_programs = [p for p in lender.programs if p.active]

        for program in active_programs:
            if self._check_program_eligibility(application, program):
                eligible_programs.append(program)

        return eligible_programs

    def _check_program_eligibility(
        self,
        application: LoanApplication,
        program: PolicyProgram,
    ) -> bool:
        """
        Check if an application meets program eligibility conditions.

        Args:
            application: Loan application
            program: Policy program to check

        Returns:
            True if eligible, False otherwise
        """
        conditions = program.eligibility_conditions

        if not conditions or not isinstance(conditions, dict):
            # No conditions means all applications are eligible
            return True

        business = application.business
        guarantor = application.guarantor

        # Check requires_paynet
        if conditions.get("requires_paynet"):
            if not guarantor.paynet_score:
                return False

        # Check legal_structure
        if "legal_structure" in conditions:
            required_structures = conditions["legal_structure"]
            if isinstance(required_structures, list):
                if business.legal_structure.value not in required_structures:
                    return False

        # Check industry
        if "industry" in conditions:
            required_industries = conditions["industry"]
            if isinstance(required_industries, list):
                # Case-insensitive match
                required_lower = [ind.lower() for ind in required_industries]
                if business.industry.lower() not in required_lower:
                    return False

        # Check min_revenue if specified
        if "min_revenue" in conditions:
            min_revenue = conditions["min_revenue"]
            if business.annual_revenue is None or business.annual_revenue < Decimal(str(min_revenue)):
                return False

        # Check homeowner_required
        if conditions.get("homeowner_required"):
            if not guarantor.is_homeowner:
                return False

        # Check us_citizen_required
        if conditions.get("us_citizen_required"):
            if not guarantor.is_us_citizen:
                return False

        # All conditions passed
        return True

    def _tier3_rule_evaluation(
        self,
        application: LoanApplication,
        program: PolicyProgram,
    ) -> ProgramEvaluationResult:
        """
        Tier 3: Detailed rule evaluation & scoring.

        Uses the rule engine to evaluate all rules in the program and
        calculate a weighted fit score.

        Args:
            application: Loan application
            program: Policy program to evaluate

        Returns:
            ProgramEvaluationResult with fit score and rule evaluations
        """
        return self.rule_engine.evaluate_program(application, program)

    def match_application_to_lender(
        self,
        application: LoanApplication,
        lender: Lender,
    ) -> Optional[MatchResult]:
        """
        Match an application to a single lender.

        Convenience method for matching against one lender.

        Args:
            application: Loan application
            lender: Lender to match against

        Returns:
            MatchResult, or None if lender has no programs
        """
        results = self.match_application_to_lenders(application, [lender])
        return results[0] if results else None

    def get_eligible_matches(
        self,
        application: LoanApplication,
        lenders: List[Lender],
    ) -> List[MatchResult]:
        """
        Get only eligible matches for an application.

        Args:
            application: Loan application
            lenders: List of lenders

        Returns:
            List of eligible match results, sorted by fit score (descending)
        """
        all_results = self.match_application_to_lenders(application, lenders)
        eligible = [r for r in all_results if r.is_eligible]
        return sorted(eligible, key=lambda x: x.fit_score, reverse=True)

    def get_best_match(
        self,
        application: LoanApplication,
        lenders: List[Lender],
    ) -> Optional[MatchResult]:
        """
        Get the single best match for an application.

        Args:
            application: Loan application
            lenders: List of lenders

        Returns:
            Best matching result (highest fit score), or None if no eligible matches
        """
        eligible = self.get_eligible_matches(application, lenders)
        return eligible[0] if eligible else None
