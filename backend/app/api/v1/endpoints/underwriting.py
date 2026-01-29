"""Underwriting endpoints for running and retrieving match results."""

import logging
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.deps import get_session
from app.models.schemas.match import (
    UnderwritingRunCreate,
    UnderwritingRunResponse,
    UnderwritingRunDetailResponse,
    UnderwritingResultsResponse,
    MatchResultDetailResponse,
    MatchResultSummary,
    RuleEvaluationResponse,
)
from app.services.underwriting_service import UnderwritingService
from app.models.domain.lender import Lender, PolicyProgram

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/run",
    response_model=UnderwritingResultsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run underwriting for an application",
    description="Execute the matching algorithm to find suitable lenders for an application",
)
async def run_underwriting(
    request: UnderwritingRunCreate,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> UnderwritingResultsResponse:
    """
    Run underwriting for a loan application.

    This endpoint:
    1. Creates an underwriting run
    2. Evaluates the application against all active lenders
    3. Applies the three-tier matching algorithm
    4. Returns matched and rejected lenders with detailed criteria breakdown

    The matching process includes:
    - Tier 1: Lender-level fast filtering (states, industries, loan amount)
    - Tier 2: Program eligibility evaluation
    - Tier 3: Detailed rule evaluation and scoring
    """
    try:
        service = UnderwritingService(db)

        # Run the underwriting process
        run = await service.run_underwriting(
            application_id=request.application_id,
            meta={"source": "api"},
        )

        # Get match results with details
        matched_results = await service.get_matched_lenders(run.id)
        rejected_results = await service.get_rejected_lenders(run.id)

        # Enrich match results with lender and program names
        matched_details = []
        for match in matched_results:
            # Get lender name
            lender_stmt = select(Lender).where(Lender.id == match.lender_id)
            lender_result = await db.execute(lender_stmt)
            lender = lender_result.scalar_one_or_none()

            # Get program name if available
            program_name = None
            program_code = None
            if match.program_id:
                program_stmt = select(PolicyProgram).where(
                    PolicyProgram.id == match.program_id
                )
                program_result = await db.execute(program_stmt)
                program = program_result.scalar_one_or_none()
                if program:
                    program_name = program.program_name
                    program_code = program.program_code

            # Get rule evaluations
            rule_evals = await service.get_rule_evaluations_for_match(match.id)

            matched_details.append(
                MatchResultDetailResponse(
                    **match.__dict__,
                    rule_evaluations=[
                        RuleEvaluationResponse.model_validate(eval)
                        for eval in rule_evals
                    ],
                    lender_name=lender.name if lender else None,
                    program_name=program_name,
                    program_code=program_code,
                )
            )

        rejected_details = []
        for match in rejected_results:
            # Get lender name
            lender_stmt = select(Lender).where(Lender.id == match.lender_id)
            lender_result = await db.execute(lender_stmt)
            lender = lender_result.scalar_one_or_none()

            # Get program name if available
            program_name = None
            program_code = None
            if match.program_id:
                program_stmt = select(PolicyProgram).where(
                    PolicyProgram.id == match.program_id
                )
                program_result = await db.execute(program_stmt)
                program = program_result.scalar_one_or_none()
                if program:
                    program_name = program.program_name
                    program_code = program.program_code

            # Get rule evaluations
            rule_evals = await service.get_rule_evaluations_for_match(match.id)

            rejected_details.append(
                MatchResultDetailResponse(
                    **match.__dict__,
                    rule_evaluations=[
                        RuleEvaluationResponse.model_validate(eval)
                        for eval in rule_evals
                    ],
                    lender_name=lender.name if lender else None,
                    program_name=program_name,
                    program_code=program_code,
                )
            )

        # Calculate summary statistics
        avg_fit_score = None
        if matched_results:
            avg_fit_score = sum(m.fit_score for m in matched_results) / len(
                matched_results
            )

        best_match = matched_details[0] if matched_details else None

        # Count rejections by tier
        tier_1_rejections = sum(1 for r in rejected_results if r.rejection_tier == 1)
        tier_2_rejections = sum(1 for r in rejected_results if r.rejection_tier == 2)
        tier_3_rejections = sum(1 for r in rejected_results if r.rejection_tier == 3)

        summary = MatchResultSummary(
            total_matches=len(matched_results) + len(rejected_results),
            matched_lenders=len(matched_results),
            rejected_lenders=len(rejected_results),
            avg_fit_score=Decimal(str(avg_fit_score)) if avg_fit_score else None,
            best_match=best_match,
            tier_1_rejections=tier_1_rejections,
            tier_2_rejections=tier_2_rejections,
            tier_3_rejections=tier_3_rejections,
        )

        return UnderwritingResultsResponse(
            run=UnderwritingRunResponse.model_validate(run),
            summary=summary,
            matched_results=matched_details,
            rejected_results=rejected_details,
        )

    except ValueError as e:
        logger.error(f"Validation error running underwriting: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error running underwriting: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to run underwriting",
        )


@router.get(
    "/runs/{run_id}",
    response_model=UnderwritingRunDetailResponse,
    summary="Get underwriting run by ID",
    description="Retrieve an underwriting run with basic match results",
)
async def get_underwriting_run(
    run_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> UnderwritingRunDetailResponse:
    """
    Retrieve an underwriting run by ID.

    Returns the run details with basic match results (without detailed rule evaluations).
    Use the /runs/{run_id}/results endpoint for detailed results.
    """
    service = UnderwritingService(db)
    run = await service.get_underwriting_run(run_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Underwriting run with ID {run_id} not found",
        )

    return UnderwritingRunDetailResponse.model_validate(run)


@router.get(
    "/runs/{run_id}/results",
    response_model=UnderwritingResultsResponse,
    summary="Get detailed underwriting results",
    description="Retrieve complete underwriting results with rule evaluations",
)
async def get_underwriting_results(
    run_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> UnderwritingResultsResponse:
    """
    Get detailed underwriting results for a run.

    Returns:
    - Run metadata
    - Summary statistics
    - Matched lenders with fit scores and detailed rule evaluations
    - Rejected lenders with rejection reasons and failed criteria
    """
    try:
        service = UnderwritingService(db)

        # Get the run
        run = await service.get_underwriting_run(run_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Underwriting run with ID {run_id} not found",
            )

        # Get match results
        matched_results = await service.get_matched_lenders(run_id)
        rejected_results = await service.get_rejected_lenders(run_id)

        # Enrich match results with lender and program names and rule evaluations
        matched_details = []
        for match in matched_results:
            # Get lender name
            lender_stmt = select(Lender).where(Lender.id == match.lender_id)
            lender_result = await db.execute(lender_stmt)
            lender = lender_result.scalar_one_or_none()

            # Get program name if available
            program_name = None
            program_code = None
            if match.program_id:
                program_stmt = select(PolicyProgram).where(
                    PolicyProgram.id == match.program_id
                )
                program_result = await db.execute(program_stmt)
                program = program_result.scalar_one_or_none()
                if program:
                    program_name = program.program_name
                    program_code = program.program_code

            # Get rule evaluations
            rule_evals = await service.get_rule_evaluations_for_match(match.id)

            matched_details.append(
                MatchResultDetailResponse(
                    **match.__dict__,
                    rule_evaluations=[
                        RuleEvaluationResponse.model_validate(eval)
                        for eval in rule_evals
                    ],
                    lender_name=lender.name if lender else None,
                    program_name=program_name,
                    program_code=program_code,
                )
            )

        rejected_details = []
        for match in rejected_results:
            # Get lender name
            lender_stmt = select(Lender).where(Lender.id == match.lender_id)
            lender_result = await db.execute(lender_stmt)
            lender = lender_result.scalar_one_or_none()

            # Get program name if available
            program_name = None
            program_code = None
            if match.program_id:
                program_stmt = select(PolicyProgram).where(
                    PolicyProgram.id == match.program_id
                )
                program_result = await db.execute(program_stmt)
                program = program_result.scalar_one_or_none()
                if program:
                    program_name = program.program_name
                    program_code = program.program_code

            # Get rule evaluations
            rule_evals = await service.get_rule_evaluations_for_match(match.id)

            rejected_details.append(
                MatchResultDetailResponse(
                    **match.__dict__,
                    rule_evaluations=[
                        RuleEvaluationResponse.model_validate(eval)
                        for eval in rule_evals
                    ],
                    lender_name=lender.name if lender else None,
                    program_name=program_name,
                    program_code=program_code,
                )
            )

        # Calculate summary statistics
        avg_fit_score = None
        if matched_results:
            avg_fit_score = sum(m.fit_score for m in matched_results) / len(
                matched_results
            )

        best_match = matched_details[0] if matched_details else None

        # Count rejections by tier
        tier_1_rejections = sum(1 for r in rejected_results if r.rejection_tier == 1)
        tier_2_rejections = sum(1 for r in rejected_results if r.rejection_tier == 2)
        tier_3_rejections = sum(1 for r in rejected_results if r.rejection_tier == 3)

        summary = MatchResultSummary(
            total_matches=len(matched_results) + len(rejected_results),
            matched_lenders=len(matched_results),
            rejected_lenders=len(rejected_results),
            avg_fit_score=Decimal(str(avg_fit_score)) if avg_fit_score else None,
            best_match=best_match,
            tier_1_rejections=tier_1_rejections,
            tier_2_rejections=tier_2_rejections,
            tier_3_rejections=tier_3_rejections,
        )

        return UnderwritingResultsResponse(
            run=UnderwritingRunResponse.model_validate(run),
            summary=summary,
            matched_results=matched_details,
            rejected_results=rejected_details,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving underwriting results: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve underwriting results",
        )


@router.get(
    "/applications/{application_id}/latest",
    response_model=UnderwritingResultsResponse,
    summary="Get latest underwriting results for an application",
    description="Retrieve the most recent underwriting results for a loan application",
)
async def get_latest_underwriting_for_application(
    application_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> UnderwritingResultsResponse:
    """
    Get the latest underwriting results for an application.

    This is a convenience endpoint that returns the most recent underwriting run
    and its results for a given application.
    """
    try:
        service = UnderwritingService(db)

        # Get the latest run
        run = await service.get_latest_underwriting_for_application(application_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No underwriting runs found for application {application_id}",
            )

        # Use the get_underwriting_results logic to build the response
        return await get_underwriting_results(run.id, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving latest underwriting: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve latest underwriting results",
        )


@router.post(
    "/applications/{application_id}/rerun",
    response_model=UnderwritingResultsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Re-run underwriting for an application",
    description="Re-run the matching algorithm for an application with updated data or policies",
)
async def rerun_underwriting(
    application_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> UnderwritingResultsResponse:
    """
    Re-run underwriting for an application.

    Useful when:
    - Application data has been updated
    - Lender policies have changed
    - You want to get fresh matching results

    Creates a new underwriting run and returns complete results.
    """
    try:
        service = UnderwritingService(db)

        # Re-run the underwriting
        run = await service.rerun_underwriting(
            application_id=application_id,
            reason="Manual rerun via API",
        )

        # Return the results using the same logic as run_underwriting
        matched_results = await service.get_matched_lenders(run.id)
        rejected_results = await service.get_rejected_lenders(run.id)

        # Enrich results
        matched_details = []
        for match in matched_results:
            lender_stmt = select(Lender).where(Lender.id == match.lender_id)
            lender_result = await db.execute(lender_stmt)
            lender = lender_result.scalar_one_or_none()

            program_name = None
            program_code = None
            if match.program_id:
                program_stmt = select(PolicyProgram).where(
                    PolicyProgram.id == match.program_id
                )
                program_result = await db.execute(program_stmt)
                program = program_result.scalar_one_or_none()
                if program:
                    program_name = program.program_name
                    program_code = program.program_code

            rule_evals = await service.get_rule_evaluations_for_match(match.id)

            matched_details.append(
                MatchResultDetailResponse(
                    **match.__dict__,
                    rule_evaluations=[
                        RuleEvaluationResponse.model_validate(eval)
                        for eval in rule_evals
                    ],
                    lender_name=lender.name if lender else None,
                    program_name=program_name,
                    program_code=program_code,
                )
            )

        rejected_details = []
        for match in rejected_results:
            lender_stmt = select(Lender).where(Lender.id == match.lender_id)
            lender_result = await db.execute(lender_stmt)
            lender = lender_result.scalar_one_or_none()

            program_name = None
            program_code = None
            if match.program_id:
                program_stmt = select(PolicyProgram).where(
                    PolicyProgram.id == match.program_id
                )
                program_result = await db.execute(program_stmt)
                program = program_result.scalar_one_or_none()
                if program:
                    program_name = program.program_name
                    program_code = program.program_code

            rule_evals = await service.get_rule_evaluations_for_match(match.id)

            rejected_details.append(
                MatchResultDetailResponse(
                    **match.__dict__,
                    rule_evaluations=[
                        RuleEvaluationResponse.model_validate(eval)
                        for eval in rule_evals
                    ],
                    lender_name=lender.name if lender else None,
                    program_name=program_name,
                    program_code=program_code,
                )
            )

        # Calculate summary
        avg_fit_score = None
        if matched_results:
            avg_fit_score = sum(m.fit_score for m in matched_results) / len(
                matched_results
            )

        best_match = matched_details[0] if matched_details else None

        tier_1_rejections = sum(1 for r in rejected_results if r.rejection_tier == 1)
        tier_2_rejections = sum(1 for r in rejected_results if r.rejection_tier == 2)
        tier_3_rejections = sum(1 for r in rejected_results if r.rejection_tier == 3)

        summary = MatchResultSummary(
            total_matches=len(matched_results) + len(rejected_results),
            matched_lenders=len(matched_results),
            rejected_lenders=len(rejected_results),
            avg_fit_score=Decimal(str(avg_fit_score)) if avg_fit_score else None,
            best_match=best_match,
            tier_1_rejections=tier_1_rejections,
            tier_2_rejections=tier_2_rejections,
            tier_3_rejections=tier_3_rejections,
        )

        return UnderwritingResultsResponse(
            run=UnderwritingRunResponse.model_validate(run),
            summary=summary,
            matched_results=matched_details,
            rejected_results=rejected_details,
        )

    except ValueError as e:
        logger.error(f"Validation error re-running underwriting: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error re-running underwriting: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to re-run underwriting",
        )
