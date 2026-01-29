"""Underwriting service for orchestrating the matching process."""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ApplicationStatus, UnderwritingStatus
from app.models.domain.application import LoanApplication
from app.models.domain.match import UnderwritingRun, MatchResult, RuleEvaluation
from app.repositories.application_repository import ApplicationRepository
from app.repositories.lender_repository import LenderRepository
from app.repositories.match_repository import MatchRepository
from app.services.rule_engine.matcher import Matcher

logger = logging.getLogger(__name__)


class UnderwritingService:
    """
    Underwriting service to orchestrate the matching process.

    This service:
    - Coordinates the matcher with lender and application repositories
    - Creates and tracks underwriting runs
    - Persists match results and rule evaluations
    - Handles errors gracefully with logging
    - Updates application status after underwriting
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the underwriting service.

        Args:
            db: Async database session
        """
        self.db = db
        self.application_repo = ApplicationRepository(db)
        self.lender_repo = LenderRepository(db)
        self.match_repo = MatchRepository(db)
        self.matcher = Matcher()

    async def run_underwriting(
        self,
        application_id: UUID,
        meta: Optional[dict] = None,
    ) -> UnderwritingRun:
        """
        Run underwriting for an application against all active lenders.

        This is the main orchestration method that:
        1. Creates an underwriting run
        2. Fetches application with all relations
        3. Fetches all active lenders with policies
        4. Runs the matching algorithm
        5. Persists all results to the database
        6. Updates application status

        Args:
            application_id: UUID of the loan application
            meta: Optional metadata about the run

        Returns:
            Completed UnderwritingRun with all results

        Raises:
            ValueError: If application not found or missing required data
        """
        # Create underwriting run
        run = await self.match_repo.create_underwriting_run(
            application_id=application_id,
            meta=meta or {},
        )

        try:
            # Update status to IN_PROGRESS and set start time
            await self.match_repo.update_run_status(
                run_id=run.id,
                status=UnderwritingStatus.IN_PROGRESS,
                started_at=datetime.now(),
            )
            await self.db.commit()

            # Fetch application with all relations
            application = await self.application_repo.get_by_id_with_relations(
                application_id
            )

            if not application:
                raise ValueError(f"Application with ID {application_id} not found")

            # Validate application has required data
            if not application.business:
                raise ValueError("Application must have business relationship loaded")
            if not application.guarantor:
                raise ValueError("Application must have guarantor relationship loaded")
            if not application.equipment:
                raise ValueError("Application must have equipment relationship loaded")

            # Fetch all active lenders with policies
            lenders = await self.lender_repo.get_active_lenders_with_policies()

            if not lenders:
                logger.warning("No active lenders found for underwriting")
                # Complete the run with empty results
                await self.match_repo.update_run_status(
                    run_id=run.id,
                    status=UnderwritingStatus.COMPLETED,
                    completed_at=datetime.now(),
                )
                await self.match_repo.update_run_summary(
                    run_id=run.id,
                    total_lenders_evaluated=0,
                    total_programs_evaluated=0,
                    matched_count=0,
                    rejected_count=0,
                )
                await self.db.commit()
                return await self.match_repo.get_run_by_id_with_results(run.id)

            # Run the matching algorithm
            logger.info(
                f"Running underwriting for application {application_id} "
                f"against {len(lenders)} lenders"
            )
            match_results = self.matcher.match_application_to_lenders(
                application=application,
                lenders=lenders,
            )

            # Persist results
            await self._persist_match_results(run, match_results)

            # Calculate summary statistics
            total_programs_evaluated = sum(
                len(lender.programs) for lender in lenders
            )
            matched_count = sum(1 for r in match_results if r.is_eligible)
            rejected_count = len(match_results) - matched_count

            # Update run summary
            await self.match_repo.update_run_summary(
                run_id=run.id,
                total_lenders_evaluated=len(lenders),
                total_programs_evaluated=total_programs_evaluated,
                matched_count=matched_count,
                rejected_count=rejected_count,
            )

            # Update run status to completed
            await self.match_repo.update_run_status(
                run_id=run.id,
                status=UnderwritingStatus.COMPLETED,
                completed_at=datetime.now(),
            )

            # Update application status to IN_UNDERWRITING if it was SUBMITTED
            if application.status == ApplicationStatus.SUBMITTED:
                application.status = ApplicationStatus.IN_UNDERWRITING
                await self.db.flush()

            # Commit all changes
            await self.db.commit()

            logger.info(
                f"Underwriting completed for application {application_id}: "
                f"{matched_count} matched, {rejected_count} rejected"
            )

            # Return the run with all results loaded
            return await self.match_repo.get_run_by_id_with_results(run.id)

        except Exception as e:
            # Handle errors gracefully
            logger.error(
                f"Underwriting failed for application {application_id}: {str(e)}",
                exc_info=True,
            )

            # Update run status to FAILED
            await self.match_repo.update_run_status(
                run_id=run.id,
                status=UnderwritingStatus.FAILED,
                completed_at=datetime.now(),
                error_message=str(e),
            )
            await self.db.commit()

            # Re-raise the exception
            raise

    async def _persist_match_results(
        self,
        run: UnderwritingRun,
        match_results: List,
    ) -> None:
        """
        Persist match results and rule evaluations to the database.

        Args:
            run: The underwriting run
            match_results: List of MatchResult objects from matcher
        """
        # Create MatchResult entities
        db_match_results = []
        all_rule_evaluations = []

        for match_result in match_results:
            # Count rule statistics
            rules_passed = sum(
                1 for _, eval_result in match_result.rule_evaluations if eval_result.passed
            )
            rules_failed = len(match_result.rule_evaluations) - rules_passed
            mandatory_passed = all(
                eval_result.passed
                for _, eval_result in match_result.rule_evaluations
                if eval_result.is_mandatory
            )

            # Create MatchResult database entity
            db_match = MatchResult(
                underwriting_run_id=run.id,
                lender_id=match_result.lender.id,
                program_id=match_result.program.id if match_result.program else None,
                is_eligible=match_result.is_eligible,
                fit_score=match_result.fit_score,
                rejection_reason=match_result.rejection_reason,
                rejection_tier=match_result.rejection_tier,
                estimated_rate=match_result.estimated_rate,
                approval_probability=match_result.approval_probability,
                total_rules_evaluated=len(match_result.rule_evaluations),
                rules_passed=rules_passed,
                rules_failed=rules_failed,
                mandatory_rules_passed=mandatory_passed,
                meta={},
            )
            db_match_results.append(db_match)

        # Batch insert match results
        inserted_matches = await self.match_repo.batch_create_match_results(
            db_match_results
        )

        # Create RuleEvaluation entities for each match result
        for i, match_result in enumerate(match_results):
            db_match = inserted_matches[i]

            for rule, eval_result in match_result.rule_evaluations:
                rule_eval = RuleEvaluation(
                    match_result_id=db_match.id,
                    rule_id=rule.id,
                    rule_name=rule.rule_name,
                    rule_type=rule.rule_type.value,
                    passed=eval_result.passed,
                    score=eval_result.score,
                    weight=eval_result.weight,
                    is_mandatory=eval_result.is_mandatory,
                    reason=eval_result.reason,
                    evidence=eval_result.evidence,
                )
                all_rule_evaluations.append(rule_eval)

        # Batch insert rule evaluations
        if all_rule_evaluations:
            await self.match_repo.batch_create_rule_evaluations(all_rule_evaluations)

    async def get_underwriting_run(
        self, run_id: UUID
    ) -> Optional[UnderwritingRun]:
        """
        Retrieve an underwriting run with all results.

        Args:
            run_id: UUID of the underwriting run

        Returns:
            UnderwritingRun with results loaded, or None if not found
        """
        return await self.match_repo.get_run_by_id_with_results(run_id)

    async def get_latest_underwriting_for_application(
        self, application_id: UUID
    ) -> Optional[UnderwritingRun]:
        """
        Get the most recent underwriting run for an application.

        Args:
            application_id: UUID of the loan application

        Returns:
            Most recent UnderwritingRun with results, or None if not found
        """
        return await self.match_repo.get_latest_run_by_application(application_id)

    async def get_matched_lenders(
        self, run_id: UUID
    ) -> List[MatchResult]:
        """
        Get only matched (eligible) lenders for a run, sorted by fit score.

        Args:
            run_id: UUID of the underwriting run

        Returns:
            List of eligible MatchResult instances sorted by fit_score descending
        """
        return await self.match_repo.get_matched_lenders_by_run(run_id)

    async def get_rejected_lenders(
        self, run_id: UUID
    ) -> List[MatchResult]:
        """
        Get only rejected (ineligible) lenders for a run.

        Args:
            run_id: UUID of the underwriting run

        Returns:
            List of ineligible MatchResult instances
        """
        return await self.match_repo.get_rejected_lenders_by_run(run_id)

    async def get_all_match_results(
        self, run_id: UUID, eligible_only: bool = False
    ) -> List[MatchResult]:
        """
        Get all match results for a run.

        Args:
            run_id: UUID of the underwriting run
            eligible_only: If True, only return eligible matches

        Returns:
            List of MatchResult instances
        """
        return await self.match_repo.get_match_results_by_run(
            run_id, eligible_only=eligible_only
        )

    async def get_rule_evaluations_for_match(
        self, match_result_id: UUID
    ) -> List[RuleEvaluation]:
        """
        Get all rule evaluations for a specific match result.

        Args:
            match_result_id: UUID of the match result

        Returns:
            List of RuleEvaluation instances
        """
        return await self.match_repo.get_rule_evaluations_by_match_result(
            match_result_id
        )

    async def get_underwriting_runs_for_application(
        self,
        application_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> List[UnderwritingRun]:
        """
        Get all underwriting runs for an application.

        Args:
            application_id: UUID of the loan application
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of UnderwritingRun instances
        """
        return await self.match_repo.get_all_runs_by_application(
            application_id, skip=skip, limit=limit
        )

    async def count_underwriting_runs(self, application_id: UUID) -> int:
        """
        Count underwriting runs for an application.

        Args:
            application_id: UUID of the loan application

        Returns:
            Number of underwriting runs
        """
        return await self.match_repo.count_runs_by_application(application_id)

    async def rerun_underwriting(
        self,
        application_id: UUID,
        reason: Optional[str] = None,
    ) -> UnderwritingRun:
        """
        Re-run underwriting for an application.

        Useful when policies have been updated or application data has changed.

        Args:
            application_id: UUID of the loan application
            reason: Optional reason for re-running

        Returns:
            New UnderwritingRun with updated results
        """
        meta = {"rerun": True, "reason": reason} if reason else {"rerun": True}
        return await self.run_underwriting(application_id, meta=meta)
