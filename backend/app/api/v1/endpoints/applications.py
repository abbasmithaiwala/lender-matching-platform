"""Application CRUD endpoints."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session
from app.models.schemas.application import (
    LoanApplicationCreate,
    LoanApplicationResponse,
    LoanApplicationUpdate,
    LoanApplicationListResponse,
)
from app.services.application_service import ApplicationService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/",
    response_model=LoanApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new loan application",
    description="Create a new loan application with business, guarantor, and equipment information",
)
async def create_application(
    application_data: LoanApplicationCreate,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> LoanApplicationResponse:
    """
    Create a new loan application.

    Creates a loan application with all required nested entities:
    - Business information
    - Personal guarantor information
    - Equipment information
    - Loan details

    Returns the created application with a generated application number.
    """
    try:
        service = ApplicationService(db)

        # Convert Pydantic models to dicts
        business_data = application_data.business.model_dump()
        guarantor_data = application_data.guarantor.model_dump()
        equipment_data = application_data.equipment.model_dump()
        loan_data = application_data.model_dump(
            exclude={"business", "guarantor", "equipment"}
        )

        application = await service.create_application(
            business_data=business_data,
            guarantor_data=guarantor_data,
            equipment_data=equipment_data,
            loan_data=loan_data,
        )

        return LoanApplicationResponse.model_validate(application)

    except ValueError as e:
        logger.error(f"Validation error creating application: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating application: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create application",
        )


@router.get(
    "/{application_id}",
    response_model=LoanApplicationResponse,
    summary="Get application by ID",
    description="Retrieve a loan application by its UUID with all related entities",
)
async def get_application(
    application_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> LoanApplicationResponse:
    """
    Retrieve a loan application by ID.

    Returns the application with all nested entities:
    - Business information
    - Personal guarantor information
    - Equipment information
    """
    service = ApplicationService(db)
    application = await service.get_application(application_id)

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID {application_id} not found",
        )

    return LoanApplicationResponse.model_validate(application)


@router.get(
    "/",
    response_model=LoanApplicationListResponse,
    summary="List all applications",
    description="Retrieve all loan applications with pagination",
)
async def list_applications(
    db: Annotated[AsyncSession, Depends(get_session)],
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=100, description="Number of items per page")
    ] = 10,
) -> LoanApplicationListResponse:
    """
    List all loan applications with pagination.

    Returns a paginated list of applications with metadata.
    """
    service = ApplicationService(db)

    # Calculate skip and limit
    skip = (page - 1) * page_size
    limit = page_size

    # Get applications
    applications = await service.get_all_applications(skip=skip, limit=limit)

    # Count total (in production, this should be a separate optimized query)
    # For now, we'll use a simple count from the status count method
    from app.core.enums import ApplicationStatus
    from sqlalchemy import select, func
    from app.models.domain.application import LoanApplication

    total_query = select(func.count(LoanApplication.id))
    total_result = await db.execute(total_query)
    total = total_result.scalar()

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return LoanApplicationListResponse(
        items=[LoanApplicationResponse.model_validate(app) for app in applications],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.put(
    "/{application_id}",
    response_model=LoanApplicationResponse,
    summary="Update an application",
    description="Update a loan application and its related entities",
)
async def update_application(
    application_id: UUID,
    update_data: LoanApplicationUpdate,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> LoanApplicationResponse:
    """
    Update a loan application.

    Supports partial updates of:
    - Application status and loan details
    - Business information
    - Guarantor information
    - Equipment information
    """
    try:
        service = ApplicationService(db)

        # Get existing application
        application = await service.get_application(application_id)
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application with ID {application_id} not found",
            )

        # Update application-level fields
        update_dict = update_data.model_dump(exclude_unset=True, exclude_none=True)

        if "status" in update_dict:
            await service.update_application_status(application_id, update_dict["status"])

        # Update nested entities
        if update_data.business:
            business_updates = update_data.business.model_dump(
                exclude_unset=True, exclude_none=True
            )
            for key, value in business_updates.items():
                setattr(application.business, key, value)

        if update_data.guarantor:
            guarantor_updates = update_data.guarantor.model_dump(
                exclude_unset=True, exclude_none=True
            )
            for key, value in guarantor_updates.items():
                setattr(application.guarantor, key, value)

        if update_data.equipment:
            equipment_updates = update_data.equipment.model_dump(
                exclude_unset=True, exclude_none=True
            )
            for key, value in equipment_updates.items():
                setattr(application.equipment, key, value)

        # Update application fields
        app_fields = {
            "requested_amount",
            "requested_term_months",
            "down_payment_percentage",
            "down_payment_amount",
            "purpose",
            "comparable_debt_payments",
        }
        for key, value in update_dict.items():
            if key in app_fields:
                setattr(application, key, value)

        await db.commit()
        await db.refresh(application)

        return LoanApplicationResponse.model_validate(application)

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating application: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error updating application: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update application",
        )


@router.delete(
    "/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an application",
    description="Delete a loan application and all related entities",
)
async def delete_application(
    application_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """
    Delete a loan application.

    This will cascade delete all related entities:
    - Business
    - Personal guarantor
    - Equipment
    """
    service = ApplicationService(db)
    deleted = await service.delete_application(application_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID {application_id} not found",
        )


@router.post(
    "/{application_id}/submit",
    response_model=LoanApplicationResponse,
    summary="Submit an application",
    description="Submit a draft application for underwriting",
)
async def submit_application(
    application_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> LoanApplicationResponse:
    """
    Submit an application for underwriting.

    This transitions the application from DRAFT to SUBMITTED status
    and sets the submitted_at timestamp.
    """
    try:
        service = ApplicationService(db)
        application = await service.submit_application(application_id)

        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application with ID {application_id} not found",
            )

        return LoanApplicationResponse.model_validate(application)

    except ValueError as e:
        logger.error(f"Validation error submitting application: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error submitting application: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit application",
        )
