"""Repository for underwriting match results and rule evaluations."""

from typing import List, Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import UnderwritingStatus
from app.models.domain.match import UnderwritingRun, MatchResult, RuleEvaluation
from app.repositories.base import BaseRepository


class MatchRepository(BaseRepository[UnderwritingRun]):
    """
    Repository for underwriting match results.

    Provides specialized methods for creating underwriting runs,
    batch inserting match results and evaluations, and querying
    results by application.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the match repository.

        Args:
            db: Async database session
        """
        super().__init__(UnderwritingRun, db)

    async def create_underwriting_run(
        self,
        application_id: UUID,
        meta: Optional[dict] = None,
    ) -> UnderwritingRun:
        """
        Create a new underwriting run for an application.

        Args:
            application_id: UUID of the loan application
            meta: Optional metadata about the run (e.g., parameters, context)

        Returns:
            Created UnderwritingRun instance
        """
        run = UnderwritingRun(
            application_id=application_id,
            status=UnderwritingStatus.PENDING,
            started_at=None,
            completed_at=None,
            total_lenders_evaluated=0,
            total_programs_evaluated=0,
            matched_count=0,
            rejected_count=0,
            meta=meta or {},
        )
        self.db.add(run)
        await self.db.flush()
        await self.db.refresh(run)
        return run

    async def update_run_status(
        self,
        run_id: UUID,
        status: UnderwritingStatus,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
    ) -> Optional[UnderwritingRun]:
        """
        Update the status and timing of an underwriting run.

        Args:
            run_id: UUID of the underwriting run
            status: New status to set
            started_at: Optional start time
            completed_at: Optional completion time
            error_message: Optional error message if failed

        Returns:
            Updated UnderwritingRun, or None if not found
        """
        run = await self.get_by_id(run_id)
        if not run:
            return None

        run.status = status
        if started_at:
            run.started_at = started_at
        if completed_at:
            run.completed_at = completed_at
        if error_message:
            run.error_message = error_message

        await self.db.flush()
        await self.db.refresh(run)
        return run

    async def update_run_summary(
        self,
        run_id: UUID,
        total_lenders_evaluated: int,
        total_programs_evaluated: int,
        matched_count: int,
        rejected_count: int,
    ) -> Optional[UnderwritingRun]:
        """
        Update the summary statistics of an underwriting run.

        Args:
            run_id: UUID of the underwriting run
            total_lenders_evaluated: Total number of lenders evaluated
            total_programs_evaluated: Total number of programs evaluated
            matched_count: Number of matched lenders
            rejected_count: Number of rejected lenders

        Returns:
            Updated UnderwritingRun, or None if not found
        """
        run = await self.get_by_id(run_id)
        if not run:
            return None

        run.total_lenders_evaluated = total_lenders_evaluated
        run.total_programs_evaluated = total_programs_evaluated
        run.matched_count = matched_count
        run.rejected_count = rejected_count

        await self.db.flush()
        await self.db.refresh(run)
        return run

    async def create_match_result(self, **kwargs) -> MatchResult:
        """
        Create a single match result.

        Args:
            **kwargs: MatchResult field values

        Returns:
            Created MatchResult instance
        """
        match_result = MatchResult(**kwargs)
        self.db.add(match_result)
        await self.db.flush()
        await self.db.refresh(match_result)
        return match_result

    async def batch_create_match_results(
        self, match_results: List[MatchResult]
    ) -> List[MatchResult]:
        """
        Batch insert multiple match results for performance.

        Args:
            match_results: List of MatchResult instances to insert

        Returns:
            List of created MatchResult instances with IDs
        """
        self.db.add_all(match_results)
        await self.db.flush()

        # Refresh all instances to get generated IDs
        for result in match_results:
            await self.db.refresh(result)

        return match_results

    async def create_rule_evaluation(self, **kwargs) -> RuleEvaluation:
        """
        Create a single rule evaluation.

        Args:
            **kwargs: RuleEvaluation field values

        Returns:
            Created RuleEvaluation instance
        """
        rule_eval = RuleEvaluation(**kwargs)
        self.db.add(rule_eval)
        await self.db.flush()
        await self.db.refresh(rule_eval)
        return rule_eval

    async def batch_create_rule_evaluations(
        self, rule_evaluations: List[RuleEvaluation]
    ) -> List[RuleEvaluation]:
        """
        Batch insert multiple rule evaluations for performance.

        Args:
            rule_evaluations: List of RuleEvaluation instances to insert

        Returns:
            List of created RuleEvaluation instances with IDs
        """
        self.db.add_all(rule_evaluations)
        await self.db.flush()

        # Refresh all instances to get generated IDs
        for evaluation in rule_evaluations:
            await self.db.refresh(evaluation)

        return rule_evaluations

    async def get_run_by_id_with_results(
        self, run_id: UUID
    ) -> Optional[UnderwritingRun]:
        """
        Retrieve an underwriting run with all match results eagerly loaded.

        Args:
            run_id: UUID of the underwriting run

        Returns:
            UnderwritingRun with match_results loaded, or None if not found
        """
        stmt = (
            select(UnderwritingRun)
            .where(UnderwritingRun.id == run_id)
            .options(
                selectinload(UnderwritingRun.match_results).selectinload(
                    MatchResult.lender
                ),
                selectinload(UnderwritingRun.match_results).selectinload(
                    MatchResult.program
                ),
                selectinload(UnderwritingRun.match_results).selectinload(
                    MatchResult.rule_evaluations
                ),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_run_by_application(
        self, application_id: UUID
    ) -> Optional[UnderwritingRun]:
        """
        Get the most recent underwriting run for an application.

        Args:
            application_id: UUID of the loan application

        Returns:
            Most recent UnderwritingRun with results, or None if not found
        """
        stmt = (
            select(UnderwritingRun)
            .where(UnderwritingRun.application_id == application_id)
            .options(
                selectinload(UnderwritingRun.match_results).selectinload(
                    MatchResult.lender
                ),
                selectinload(UnderwritingRun.match_results).selectinload(
                    MatchResult.program
                ),
                selectinload(UnderwritingRun.match_results).selectinload(
                    MatchResult.rule_evaluations
                ),
            )
            .order_by(UnderwritingRun.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_runs_by_application(
        self,
        application_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> List[UnderwritingRun]:
        """
        Get all underwriting runs for an application.

        Args:
            application_id: UUID of the loan application
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of UnderwritingRun instances ordered by creation date
        """
        stmt = (
            select(UnderwritingRun)
            .where(UnderwritingRun.application_id == application_id)
            .order_by(UnderwritingRun.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_match_results_by_run(
        self, run_id: UUID, eligible_only: bool = False
    ) -> List[MatchResult]:
        """
        Get all match results for a specific underwriting run.

        Args:
            run_id: UUID of the underwriting run
            eligible_only: If True, only return eligible matches

        Returns:
            List of MatchResult instances with lender and program loaded
        """
        stmt = (
            select(MatchResult)
            .where(MatchResult.underwriting_run_id == run_id)
            .options(
                selectinload(MatchResult.lender),
                selectinload(MatchResult.program),
                selectinload(MatchResult.rule_evaluations),
            )
            .order_by(MatchResult.fit_score.desc())
        )

        if eligible_only:
            stmt = stmt.where(MatchResult.is_eligible == True)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_matched_lenders_by_run(
        self, run_id: UUID
    ) -> List[MatchResult]:
        """
        Get only matched (eligible) lenders for a run, sorted by fit score.

        Args:
            run_id: UUID of the underwriting run

        Returns:
            List of eligible MatchResult instances sorted by fit_score descending
        """
        return await self.get_match_results_by_run(run_id, eligible_only=True)

    async def get_rejected_lenders_by_run(
        self, run_id: UUID
    ) -> List[MatchResult]:
        """
        Get only rejected (ineligible) lenders for a run.

        Args:
            run_id: UUID of the underwriting run

        Returns:
            List of ineligible MatchResult instances
        """
        stmt = (
            select(MatchResult)
            .where(MatchResult.underwriting_run_id == run_id)
            .where(MatchResult.is_eligible == False)
            .options(
                selectinload(MatchResult.lender),
                selectinload(MatchResult.program),
                selectinload(MatchResult.rule_evaluations),
            )
            .order_by(MatchResult.rejection_tier, MatchResult.created_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_rule_evaluations_by_match_result(
        self, match_result_id: UUID
    ) -> List[RuleEvaluation]:
        """
        Get all rule evaluations for a specific match result.

        Args:
            match_result_id: UUID of the match result

        Returns:
            List of RuleEvaluation instances for the match
        """
        stmt = (
            select(RuleEvaluation)
            .where(RuleEvaluation.match_result_id == match_result_id)
            .order_by(
                RuleEvaluation.is_mandatory.desc(),  # Mandatory rules first
                RuleEvaluation.passed.desc(),  # Passed rules before failed
                RuleEvaluation.weight.desc(),  # Higher weight first
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_runs_by_status(
        self,
        status: UnderwritingStatus,
        skip: int = 0,
        limit: int = 100,
    ) -> List[UnderwritingRun]:
        """
        Get underwriting runs by status.

        Args:
            status: UnderwritingStatus to filter by
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of UnderwritingRun instances matching the status
        """
        stmt = (
            select(UnderwritingRun)
            .where(UnderwritingRun.status == status)
            .order_by(UnderwritingRun.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_runs_by_application(self, application_id: UUID) -> int:
        """
        Count the number of underwriting runs for an application.

        Args:
            application_id: UUID of the loan application

        Returns:
            Number of underwriting runs for the application
        """
        stmt = select(UnderwritingRun).where(
            UnderwritingRun.application_id == application_id
        )
        result = await self.db.execute(stmt)
        return len(list(result.scalars().all()))
