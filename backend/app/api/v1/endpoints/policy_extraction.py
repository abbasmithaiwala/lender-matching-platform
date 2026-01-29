"""API endpoints for policy extraction from PDFs."""

import logging
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.models.schemas.policy_extraction import (
    ApprovalResponse,
    ExtractionListResponse,
    ExtractionResult,
    PolicyExtractionUploadRequest,
    UpdateExtractionRequest,
)
from app.services.lender_service import LenderService
from app.services.pdf_parser import PolicyExtractor

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage for extractions (in production, use Redis or database)
_extraction_cache: dict[UUID, dict] = {}


@router.post("/upload", response_model=ExtractionResult, status_code=status.HTTP_201_CREATED)
async def upload_and_extract_pdf(
    file: Annotated[UploadFile, File(description="PDF file to extract policies from")],
    enhance: bool = False,
    validate_extraction: bool = False,
) -> ExtractionResult:
    """
    Upload a PDF file and extract lender policies.

    Args:
        file: PDF file
        enhance: Whether to enhance extraction with additional pass
        validate_extraction: Whether to validate extracted data

    Returns:
        Extraction result with extracted policy data

    Raises:
        HTTPException: If file is invalid or extraction fails
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF",
        )

    # Validate file size (max 10MB)
    file_content = await file.read()
    if len(file_content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size must be less than 10MB",
        )

    # Save temporarily
    temp_dir = Path("/tmp/lender_pdfs")
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / file.filename

    try:
        # Write file
        with open(temp_path, "wb") as f:
            f.write(file_content)

        # Extract policy
        logger.info(f"Starting extraction for: {file.filename}")
        extractor = PolicyExtractor()
        result = await extractor.extract_from_pdf(
            pdf_path=temp_path,
            enhance=enhance,
            validate=validate_extraction,
        )

        # Log result structure for debugging
        logger.debug(f"Result keys: {result.keys()}")
        if "extracted_data" in result and result["extracted_data"]:
            logger.debug(f"Extracted data type: {type(result['extracted_data'])}")
            if isinstance(result["extracted_data"], dict):
                logger.debug(f"Extracted data keys: {result['extracted_data'].keys()}")

        # Convert to ExtractionResult
        try:
            extraction_result = ExtractionResult(**result)
        except Exception as e:
            logger.error(f"Failed to convert result to ExtractionResult: {e}")
            logger.error(f"Result structure: {result}")
            raise

        # Store in cache
        _extraction_cache[extraction_result.extraction_id] = extraction_result.model_dump()

        logger.info(
            f"Extraction completed: {extraction_result.extraction_id}, "
            f"status: {extraction_result.status}"
        )

        return extraction_result

    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extraction failed: {str(e)}",
        )
    finally:
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()


@router.get("", response_model=ExtractionListResponse)
async def list_extractions() -> ExtractionListResponse:
    """
    List all policy extractions.

    Returns:
        List of extractions with summary information
    """
    from app.models.schemas.policy_extraction import ExtractionListItem

    extractions = []
    for extraction_id, data in _extraction_cache.items():
        item = ExtractionListItem(
            extraction_id=extraction_id,
            pdf_filename=data.get("pdf_filename", ""),
            status=data.get("status", ""),
            lender_name=data.get("extracted_data", {}).get("lender", {}).get("name"),
            programs_count=len(data.get("extracted_data", {}).get("programs", [])),
            created_at=data.get("created_at"),
            approved=False,  # Track separately in production
        )
        extractions.append(item)

    # Sort by creation date (newest first)
    extractions.sort(key=lambda x: x.created_at, reverse=True)

    return ExtractionListResponse(
        extractions=extractions,
        total=len(extractions),
    )


@router.get("/{extraction_id}", response_model=ExtractionResult)
async def get_extraction(extraction_id: UUID) -> ExtractionResult:
    """
    Get extraction result by ID.

    Args:
        extraction_id: Extraction ID

    Returns:
        Extraction result

    Raises:
        HTTPException: If extraction not found
    """
    if extraction_id not in _extraction_cache:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Extraction {extraction_id} not found",
        )

    data = _extraction_cache[extraction_id]
    return ExtractionResult(**data)


@router.put("/{extraction_id}", response_model=ExtractionResult)
async def update_extraction(
    extraction_id: UUID,
    update_request: UpdateExtractionRequest,
) -> ExtractionResult:
    """
    Update extracted policy data.

    Args:
        extraction_id: Extraction ID
        update_request: Update request with modified data

    Returns:
        Updated extraction result

    Raises:
        HTTPException: If extraction not found
    """
    if extraction_id not in _extraction_cache:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Extraction {extraction_id} not found",
        )

    data = _extraction_cache[extraction_id]

    # Update lender info
    if update_request.lender:
        lender_data = data.get("extracted_data", {}).get("lender", {})
        for field, value in update_request.lender.model_dump(exclude_unset=True).items():
            lender_data[field] = value

    # Update programs
    if update_request.programs:
        data["extracted_data"]["programs"] = [
            p.model_dump() for p in update_request.programs
        ]

    # Update cache
    _extraction_cache[extraction_id] = data

    logger.info(f"Updated extraction: {extraction_id}")

    return ExtractionResult(**data)


@router.post("/{extraction_id}/approve", response_model=ApprovalResponse)
async def approve_extraction(
    extraction_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """
    Approve extraction and save to database.

    This creates the lender, programs, and rules in the database.

    Args:
        extraction_id: Extraction ID
        db: Database session

    Returns:
        Approval response with created entity IDs

    Raises:
        HTTPException: If extraction not found or approval fails
    """
    if extraction_id not in _extraction_cache:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Extraction {extraction_id} not found",
        )

    data = _extraction_cache[extraction_id]

    if data.get("status") != "success":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot approve failed extraction",
        )

    extracted_data = data.get("extracted_data")
    if not extracted_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No extracted data to approve",
        )

    try:
        lender_service = LenderService(db)

        # Create lender
        lender_data = extracted_data["lender"]
        lender = await lender_service.create_lender(
            name=lender_data["name"],
            description=lender_data.get("description", ""),
            min_loan_amount=lender_data["min_loan_amount"],
            max_loan_amount=lender_data["max_loan_amount"],
            excluded_states=lender_data.get("excluded_states", []),
            excluded_industries=lender_data.get("excluded_industries", []),
        )

        logger.info(f"Created lender: {lender.id} - {lender.name}")

        # Create programs and rules
        program_ids = []
        for program_data in extracted_data["programs"]:
            program = await lender_service.create_program(
                lender_id=lender.id,
                program_name=program_data["program_name"],
                program_code=program_data["program_code"],
                credit_tier=program_data["credit_tier"],
                min_fit_score=program_data.get("min_fit_score", 60.0),
                description=program_data.get("description", ""),
                eligibility_conditions=program_data.get("eligibility_conditions", {}),
                rate_metadata=program_data.get("rate_metadata", {}),
            )

            program_ids.append(program.id)
            logger.info(f"Created program: {program.id} - {program.program_name}")

            # Create rules for program
            for rule_data in program_data.get("rules", []):
                rule = await lender_service.create_rule(
                    program_id=program.id,
                    rule_type=rule_data["rule_type"],
                    rule_name=rule_data["rule_name"],
                    criteria=rule_data["criteria"],
                    weight=rule_data.get("weight", 1.0),
                    is_mandatory=rule_data.get("is_mandatory", True),
                )
                logger.debug(f"Created rule: {rule.id} - {rule.rule_name}")

        # Mark as approved (in production, track this in database)
        logger.info(
            f"Successfully approved extraction {extraction_id}: "
            f"Lender {lender.id}, {len(program_ids)} programs"
        )

        return ApprovalResponse(
            success=True,
            message=f"Successfully created lender '{lender.name}' with {len(program_ids)} programs",
            lender_id=lender.id,
            program_ids=program_ids,
        )

    except Exception as e:
        logger.error(f"Approval failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve extraction: {str(e)}",
        )


@router.delete("/{extraction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_extraction(extraction_id: UUID) -> None:
    """
    Delete extraction from cache.

    Args:
        extraction_id: Extraction ID

    Raises:
        HTTPException: If extraction not found
    """
    if extraction_id not in _extraction_cache:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Extraction {extraction_id} not found",
        )

    del _extraction_cache[extraction_id]
    logger.info(f"Deleted extraction: {extraction_id}")
