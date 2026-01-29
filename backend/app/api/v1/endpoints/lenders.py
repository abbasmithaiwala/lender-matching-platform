"""Lender management endpoints."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.deps import get_session
from app.models.schemas.lender import (
    LenderCreate,
    LenderResponse,
    LenderDetailResponse,
    LenderUpdate,
    LenderListResponse,
    PolicyProgramCreate,
    PolicyProgramResponse,
    PolicyProgramDetailResponse,
    PolicyProgramUpdate,
    PolicyProgramListResponse,
)
from app.services.lender_service import LenderService
from app.models.domain.lender import Lender, PolicyProgram

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Lender Endpoints ====================


@router.post(
    "/",
    response_model=LenderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new lender",
    description="Create a new lender with exclusion rules",
)
async def create_lender(
    lender_data: LenderCreate,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> LenderResponse:
    """
    Create a new lender.

    Creates a lender with:
    - Basic information (name, description)
    - Loan amount constraints
    - State exclusions (first-class filtering)
    - Industry exclusions (first-class filtering)
    """
    try:
        service = LenderService(db)

        lender = await service.create_lender(
            name=lender_data.name,
            description=lender_data.description,
            min_loan_amount=lender_data.min_loan_amount,
            max_loan_amount=lender_data.max_loan_amount,
            excluded_states=lender_data.excluded_states,
            excluded_industries=lender_data.excluded_industries,
            active=lender_data.active,
        )

        return LenderResponse.model_validate(lender)

    except ValueError as e:
        logger.error(f"Validation error creating lender: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating lender: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create lender",
        )


@router.get(
    "/{lender_id}",
    response_model=LenderDetailResponse,
    summary="Get lender by ID",
    description="Retrieve a lender with all its programs",
)
async def get_lender(
    lender_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> LenderDetailResponse:
    """
    Retrieve a lender by ID.

    Returns the lender with all associated policy programs.
    """
    service = LenderService(db)
    lender = await service.get_lender(lender_id)

    if not lender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lender with ID {lender_id} not found",
        )

    return LenderDetailResponse.model_validate(lender)


@router.get(
    "/",
    response_model=LenderListResponse,
    summary="List all lenders",
    description="Retrieve all lenders with pagination",
)
async def list_lenders(
    db: Annotated[AsyncSession, Depends(get_session)],
    active_only: Annotated[
        bool, Query(description="Filter for active lenders only")
    ] = True,
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=100, description="Number of items per page")
    ] = 10,
) -> LenderListResponse:
    """
    List all lenders with pagination.

    Returns a paginated list of lenders.
    """
    service = LenderService(db)

    # Calculate skip and limit
    skip = (page - 1) * page_size
    limit = page_size

    # Get lenders
    lenders = await service.get_all_lenders(
        active_only=active_only, skip=skip, limit=limit
    )

    # Count total
    query = select(func.count(Lender.id))
    if active_only:
        query = query.where(Lender.active == True)
    total_result = await db.execute(query)
    total = total_result.scalar()

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return LenderListResponse(
        items=[LenderResponse.model_validate(lender) for lender in lenders],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.put(
    "/{lender_id}",
    response_model=LenderDetailResponse,
    summary="Update a lender",
    description="Update lender information",
)
async def update_lender(
    lender_id: UUID,
    update_data: LenderUpdate,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> LenderDetailResponse:
    """
    Update a lender's information.

    Supports partial updates of all lender fields.
    """
    try:
        service = LenderService(db)

        update_dict = update_data.model_dump(exclude_unset=True, exclude_none=True)

        lender = await service.update_lender(lender_id, **update_dict)

        if not lender:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lender with ID {lender_id} not found",
            )

        return LenderDetailResponse.model_validate(lender)

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating lender: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error updating lender: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update lender",
        )


@router.delete(
    "/{lender_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a lender",
    description="Delete a lender and all associated programs and rules",
)
async def delete_lender(
    lender_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """
    Delete a lender.

    This will cascade delete all associated:
    - Policy programs
    - Policy rules
    """
    service = LenderService(db)
    deleted = await service.delete_lender(lender_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lender with ID {lender_id} not found",
        )


@router.post(
    "/{lender_id}/activate",
    response_model=LenderResponse,
    summary="Activate a lender",
    description="Set a lender's active status to true",
)
async def activate_lender(
    lender_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> LenderResponse:
    """
    Activate a lender.

    Sets the lender's active flag to true, making it available for matching.
    """
    service = LenderService(db)
    lender = await service.activate_lender(lender_id)

    if not lender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lender with ID {lender_id} not found",
        )

    return LenderResponse.model_validate(lender)


@router.post(
    "/{lender_id}/deactivate",
    response_model=LenderResponse,
    summary="Deactivate a lender",
    description="Set a lender's active status to false",
)
async def deactivate_lender(
    lender_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> LenderResponse:
    """
    Deactivate a lender.

    Sets the lender's active flag to false, excluding it from matching.
    """
    service = LenderService(db)
    lender = await service.deactivate_lender(lender_id)

    if not lender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lender with ID {lender_id} not found",
        )

    return LenderResponse.model_validate(lender)


# ==================== Program Endpoints ====================


@router.post(
    "/{lender_id}/programs",
    response_model=PolicyProgramResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a policy program",
    description="Create a new policy program for a lender",
)
async def create_program(
    lender_id: UUID,
    program_data: PolicyProgramCreate,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> PolicyProgramResponse:
    """
    Create a new policy program for a lender.

    Creates a program with:
    - Program tier information (name, code, credit tier)
    - Eligibility conditions (JSONB)
    - Rate metadata (JSONB)
    - Minimum fit score threshold
    """
    try:
        service = LenderService(db)

        # Override lender_id from path
        program = await service.create_program(
            lender_id=lender_id,
            program_name=program_data.program_name,
            program_code=program_data.program_code,
            description=program_data.description,
            credit_tier=program_data.credit_tier,
            eligibility_conditions=program_data.eligibility_conditions,
            rate_metadata=program_data.rate_metadata,
            min_fit_score=program_data.min_fit_score,
            active=program_data.active,
        )

        return PolicyProgramResponse.model_validate(program)

    except ValueError as e:
        logger.error(f"Validation error creating program: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating program: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create program",
        )


@router.get(
    "/{lender_id}/programs",
    response_model=PolicyProgramListResponse,
    summary="List programs for a lender",
    description="Retrieve all policy programs for a lender",
)
async def list_programs_for_lender(
    lender_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    active_only: Annotated[
        bool, Query(description="Filter for active programs only")
    ] = True,
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=100, description="Number of items per page")
    ] = 50,
) -> PolicyProgramListResponse:
    """
    List all programs for a lender.

    Returns programs with basic information (without rules).
    """
    service = LenderService(db)

    # Get programs
    programs = await service.get_programs_for_lender(
        lender_id=lender_id, active_only=active_only
    )

    # Apply pagination
    skip = (page - 1) * page_size
    paginated_programs = programs[skip : skip + page_size]

    total = len(programs)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PolicyProgramListResponse(
        items=[
            PolicyProgramResponse.model_validate(program)
            for program in paginated_programs
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/programs/{program_id}",
    response_model=PolicyProgramDetailResponse,
    summary="Get program by ID",
    description="Retrieve a policy program with all its rules",
)
async def get_program(
    program_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> PolicyProgramDetailResponse:
    """
    Retrieve a policy program by ID.

    Returns the program with all associated policy rules.
    """
    service = LenderService(db)
    program = await service.get_program(program_id)

    if not program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Program with ID {program_id} not found",
        )

    return PolicyProgramDetailResponse.model_validate(program)


@router.put(
    "/programs/{program_id}",
    response_model=PolicyProgramResponse,
    summary="Update a policy program",
    description="Update program information",
)
async def update_program(
    program_id: UUID,
    update_data: PolicyProgramUpdate,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> PolicyProgramResponse:
    """
    Update a policy program's information.

    Supports partial updates of all program fields.
    """
    try:
        service = LenderService(db)

        update_dict = update_data.model_dump(exclude_unset=True, exclude_none=True)

        program = await service.update_program(program_id, **update_dict)

        if not program:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Program with ID {program_id} not found",
            )

        return PolicyProgramResponse.model_validate(program)

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating program: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error updating program: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update program",
        )


@router.delete(
    "/programs/{program_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a policy program",
    description="Delete a program and all associated rules",
)
async def delete_program(
    program_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """
    Delete a policy program.

    This will cascade delete all associated policy rules.
    """
    service = LenderService(db)
    deleted = await service.delete_program(program_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Program with ID {program_id} not found",
        )
