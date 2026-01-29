"""Policy rule management endpoints."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session
from app.models.schemas.lender import (
    PolicyRuleCreate,
    PolicyRuleResponse,
    PolicyRuleUpdate,
    PolicyRuleListResponse,
)
from app.services.lender_service import LenderService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/programs/{program_id}/rules",
    response_model=PolicyRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a policy rule",
    description="Create a new policy rule for a program",
)
async def create_rule(
    program_id: UUID,
    rule_data: PolicyRuleCreate,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> PolicyRuleResponse:
    """
    Create a new policy rule for a program.

    Creates a rule with:
    - Rule type (from RuleType enum)
    - Rule name and description
    - Criteria (JSONB) - structure varies by rule type
    - Weight for scoring
    - is_mandatory flag (true = hard requirement, false = guideline)

    Example criteria by rule type:
    - MIN_FICO: {"min_score": 680}
    - MIN_PAYNET: {"min_score": 50}
    - TIME_IN_BUSINESS: {"min_years": 2}
    - EQUIPMENT_AGE: {"max_age_years": 15}
    - EXCLUDED_STATES: {"states": ["CA", "NV"]}
    """
    try:
        service = LenderService(db)

        # Override program_id from path
        rule = await service.create_rule(
            program_id=program_id,
            rule_type=rule_data.rule_type,
            rule_name=rule_data.rule_name,
            criteria=rule_data.criteria,
            description=rule_data.description,
            weight=rule_data.weight,
            is_mandatory=rule_data.is_mandatory,
            active=rule_data.active,
        )

        return PolicyRuleResponse.model_validate(rule)

    except ValueError as e:
        logger.error(f"Validation error creating rule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating rule: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create rule",
        )


@router.get(
    "/programs/{program_id}/rules",
    response_model=PolicyRuleListResponse,
    summary="List rules for a program",
    description="Retrieve all policy rules for a program",
)
async def list_rules_for_program(
    program_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    active_only: Annotated[
        bool, Query(description="Filter for active rules only")
    ] = True,
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=100, description="Number of items per page")
    ] = 50,
) -> PolicyRuleListResponse:
    """
    List all rules for a program.

    Returns rules ordered by rule type and name.
    """
    service = LenderService(db)

    # Get rules
    rules = await service.get_rules_for_program(
        program_id=program_id, active_only=active_only
    )

    # Apply pagination
    skip = (page - 1) * page_size
    paginated_rules = rules[skip : skip + page_size]

    total = len(rules)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PolicyRuleListResponse(
        items=[PolicyRuleResponse.model_validate(rule) for rule in paginated_rules],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/rules/{rule_id}",
    response_model=PolicyRuleResponse,
    summary="Get rule by ID",
    description="Retrieve a policy rule by its ID",
)
async def get_rule(
    rule_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> PolicyRuleResponse:
    """
    Retrieve a policy rule by ID.

    Returns the complete rule definition including criteria.
    """
    service = LenderService(db)
    rule = await service.get_rule(rule_id)

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule with ID {rule_id} not found",
        )

    return PolicyRuleResponse.model_validate(rule)


@router.put(
    "/rules/{rule_id}",
    response_model=PolicyRuleResponse,
    summary="Update a policy rule",
    description="Update rule information",
)
async def update_rule(
    rule_id: UUID,
    update_data: PolicyRuleUpdate,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> PolicyRuleResponse:
    """
    Update a policy rule's information.

    Supports partial updates of:
    - rule_name
    - description
    - criteria (JSONB)
    - weight
    - is_mandatory
    - active

    Note: rule_type cannot be changed after creation.
    """
    try:
        service = LenderService(db)

        update_dict = update_data.model_dump(exclude_unset=True, exclude_none=True)

        rule = await service.update_rule(rule_id, **update_dict)

        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule with ID {rule_id} not found",
            )

        return PolicyRuleResponse.model_validate(rule)

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating rule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error updating rule: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update rule",
        )


@router.delete(
    "/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a policy rule",
    description="Delete a policy rule from a program",
)
async def delete_rule(
    rule_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """
    Delete a policy rule.

    This permanently removes the rule from the program.
    """
    service = LenderService(db)
    deleted = await service.delete_rule(rule_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule with ID {rule_id} not found",
        )


@router.post(
    "/rules/{rule_id}/activate",
    response_model=PolicyRuleResponse,
    summary="Activate a rule",
    description="Set a rule's active status to true",
)
async def activate_rule(
    rule_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> PolicyRuleResponse:
    """
    Activate a policy rule.

    Sets the rule's active flag to true, including it in evaluations.
    """
    try:
        service = LenderService(db)
        rule = await service.update_rule(rule_id, active=True)

        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule with ID {rule_id} not found",
            )

        return PolicyRuleResponse.model_validate(rule)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating rule: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate rule",
        )


@router.post(
    "/rules/{rule_id}/deactivate",
    response_model=PolicyRuleResponse,
    summary="Deactivate a rule",
    description="Set a rule's active status to false",
)
async def deactivate_rule(
    rule_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> PolicyRuleResponse:
    """
    Deactivate a policy rule.

    Sets the rule's active flag to false, excluding it from evaluations.
    """
    try:
        service = LenderService(db)
        rule = await service.update_rule(rule_id, active=False)

        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule with ID {rule_id} not found",
            )

        return PolicyRuleResponse.model_validate(rule)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating rule: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate rule",
        )
