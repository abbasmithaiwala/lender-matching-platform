"""Policy extraction service using LLM to parse PDF content."""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from app.services.pdf_parser.llm_extractor import LLMExtractor
from app.services.pdf_parser.pdf_reader import PDFReader
from app.services.pdf_parser.prompts import (
    POLICY_EXTRACTION_PROMPT,
    POLICY_VALIDATION_PROMPT,
    POLICY_ENHANCEMENT_PROMPT,
)

logger = logging.getLogger(__name__)


class PolicyExtractor:
    """Service for extracting structured lender policy data from PDFs using LLM."""

    def __init__(self, llm_extractor: Optional[LLMExtractor] = None):
        """
        Initialize the policy extractor.

        Args:
            llm_extractor: Optional LLMExtractor instance (creates new one if not provided)
        """
        self.llm_extractor = llm_extractor or LLMExtractor()
        self.pdf_reader = PDFReader()

    async def extract_from_pdf(
        self,
        pdf_path: Path,
        enhance: bool = True,
        validate: bool = True,
    ) -> dict[str, Any]:
        """
        Extract policy data from a PDF file.

        Args:
            pdf_path: Path to the PDF file
            enhance: Whether to enhance the extraction with additional pass
            validate: Whether to validate the extracted data

        Returns:
            Dictionary containing extracted policy data and metadata

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            Exception: For extraction errors
        """
        pdf_path = Path(pdf_path)
        logger.info(f"Starting policy extraction from: {pdf_path.name}")

        try:
            # Step 1: Extract text from PDF
            logger.info("Step 1: Extracting text from PDF...")
            pdf_text = self.pdf_reader.extract_text_with_fallback(pdf_path)
            pdf_metadata = self.pdf_reader.get_pdf_metadata(pdf_path)

            if not pdf_text or len(pdf_text.strip()) < 100:
                raise ValueError(f"Insufficient text extracted from PDF: {len(pdf_text)} characters")

            logger.info(f"Extracted {len(pdf_text)} characters from {pdf_metadata.get('page_count', 0)} pages")

            # Step 2: Extract policy structure using LLM
            logger.info("Step 2: Extracting policy structure using LLM...")
            extracted_data = await self.llm_extractor.extract_with_prompt(
                content=pdf_text,
                prompt=POLICY_EXTRACTION_PROMPT,
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=8000,
            )

            # Check for parsing errors
            if "parsing_error" in extracted_data:
                logger.warning(f"JSON parsing issue: {extracted_data['parsing_error']}")
                # Try to extract from raw_content if available
                if "raw_content" in extracted_data:
                    try:
                        extracted_data = json.loads(extracted_data["raw_content"])
                    except json.JSONDecodeError:
                        raise ValueError("Failed to parse LLM response as JSON")

            # Validate basic structure
            if "lender" not in extracted_data or "programs" not in extracted_data:
                raise ValueError("Extracted data missing required fields: 'lender' or 'programs'")

            logger.info(
                f"Successfully extracted: {len(extracted_data.get('programs', []))} programs"
            )

            # Step 3: Enhance extraction (optional)
            if enhance:
                logger.info("Step 3: Enhancing extraction...")
                try:
                    extracted_data = await self._enhance_extraction(extracted_data, pdf_text)
                except Exception as e:
                    logger.warning(f"Enhancement failed, using original extraction: {e}")

            # Step 4: Validate extraction (optional)
            validation_result = None
            if validate:
                logger.info("Step 4: Validating extraction...")
                try:
                    validation_result = await self._validate_extraction(extracted_data)
                except Exception as e:
                    logger.warning(f"Validation failed: {e}")
                    validation_result = {
                        "valid": False,
                        "errors": [{"field": "validation", "message": str(e), "severity": "error"}],
                        "suggestions": [],
                    }

            # Prepare response
            result = {
                "status": "success",
                "pdf_filename": pdf_path.name,
                "pdf_metadata": pdf_metadata,
                "extracted_data": extracted_data,
                "validation": validation_result,
                "extraction_metadata": {
                    "pdf_characters": len(pdf_text),
                    "programs_count": len(extracted_data.get("programs", [])),
                    "total_rules": sum(
                        len(p.get("rules", [])) for p in extracted_data.get("programs", [])
                    ),
                    "enhanced": enhance,
                    "validated": validate,
                },
            }

            logger.info("Policy extraction completed successfully")
            return result

        except Exception as e:
            logger.error(f"Policy extraction failed: {e}", exc_info=True)
            return {
                "status": "error",
                "pdf_filename": pdf_path.name,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    async def extract_from_text(
        self,
        pdf_text: str,
        filename: str = "unknown.pdf",
    ) -> dict[str, Any]:
        """
        Extract policy data from already-extracted PDF text.

        Args:
            pdf_text: The extracted text content
            filename: Original PDF filename for reference

        Returns:
            Dictionary containing extracted policy data
        """
        logger.info(f"Starting policy extraction from text ({len(pdf_text)} characters)")

        try:
            extracted_data = await self.llm_extractor.extract_with_prompt(
                content=pdf_text,
                prompt=POLICY_EXTRACTION_PROMPT,
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=8000,
            )

            # Check for parsing errors
            if "parsing_error" in extracted_data:
                logger.warning(f"JSON parsing issue: {extracted_data['parsing_error']}")
                if "raw_content" in extracted_data:
                    try:
                        extracted_data = json.loads(extracted_data["raw_content"])
                    except json.JSONDecodeError:
                        raise ValueError("Failed to parse LLM response as JSON")

            return {
                "status": "success",
                "pdf_filename": filename,
                "extracted_data": extracted_data,
            }

        except Exception as e:
            logger.error(f"Text extraction failed: {e}", exc_info=True)
            return {
                "status": "error",
                "pdf_filename": filename,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    async def _enhance_extraction(
        self,
        extracted_data: dict[str, Any],
        pdf_text: str,
    ) -> dict[str, Any]:
        """
        Enhance extracted data with additional LLM pass.

        Args:
            extracted_data: Initially extracted data
            pdf_text: Original PDF text for reference

        Returns:
            Enhanced extraction
        """
        try:
            enhanced = await self.llm_extractor.extract_with_prompt(
                content=pdf_text,
                prompt=POLICY_ENHANCEMENT_PROMPT.format(
                    extracted_data=json.dumps(extracted_data, indent=2),
                    pdf_content=pdf_text[:5000],  # Limit context size
                ),
                response_format={"type": "json_object"},
                temperature=0.1,  # Lower temperature for consistency
                max_tokens=8000,
            )

            # Check if enhanced data has required structure
            if "lender" in enhanced and "programs" in enhanced:
                logger.info("Enhancement successful")
                return enhanced
            else:
                logger.warning("Enhanced data missing required structure, using original")
                return extracted_data

        except Exception as e:
            logger.warning(f"Enhancement failed: {e}")
            return extracted_data

    async def _validate_extraction(self, extracted_data: dict[str, Any]) -> dict[str, Any]:
        """
        Validate extracted policy data.

        Args:
            extracted_data: The extracted data to validate

        Returns:
            Validation result with errors and suggestions
        """
        try:
            validation = await self.llm_extractor.extract_with_prompt(
                content="",
                prompt=POLICY_VALIDATION_PROMPT.format(
                    extracted_data=json.dumps(extracted_data, indent=2)
                ),
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=2000,
            )

            logger.info(
                f"Validation complete: {validation.get('valid', False)}, "
                f"{len(validation.get('errors', []))} errors"
            )

            return validation

        except Exception as e:
            logger.warning(f"Validation failed: {e}")
            return {
                "valid": False,
                "errors": [{"field": "validation", "message": str(e), "severity": "error"}],
                "suggestions": [],
            }

    def validate_structure_locally(self, extracted_data: dict[str, Any]) -> dict[str, Any]:
        """
        Perform local (non-LLM) validation of extracted data structure.

        Args:
            extracted_data: The extracted data to validate

        Returns:
            Validation result
        """
        errors = []
        warnings = []

        # Check lender section
        lender = extracted_data.get("lender", {})
        if not lender.get("name"):
            errors.append({"field": "lender.name", "message": "Lender name is required", "severity": "error"})

        if not isinstance(lender.get("min_loan_amount"), (int, float)):
            warnings.append({"field": "lender.min_loan_amount", "message": "Should be a number", "severity": "warning"})

        if not isinstance(lender.get("max_loan_amount"), (int, float)):
            warnings.append({"field": "lender.max_loan_amount", "message": "Should be a number", "severity": "warning"})

        # Check programs
        programs = extracted_data.get("programs", [])
        if not programs:
            errors.append({"field": "programs", "message": "At least one program is required", "severity": "error"})

        for i, program in enumerate(programs):
            if not program.get("program_name"):
                errors.append({
                    "field": f"programs[{i}].program_name",
                    "message": "Program name is required",
                    "severity": "error",
                })

            if not program.get("program_code"):
                warnings.append({
                    "field": f"programs[{i}].program_code",
                    "message": "Program code is recommended",
                    "severity": "warning",
                })

            # Check rules
            rules = program.get("rules", [])
            if not rules:
                warnings.append({
                    "field": f"programs[{i}].rules",
                    "message": "Program has no rules defined",
                    "severity": "warning",
                })

            for j, rule in enumerate(rules):
                if not rule.get("rule_type"):
                    errors.append({
                        "field": f"programs[{i}].rules[{j}].rule_type",
                        "message": "Rule type is required",
                        "severity": "error",
                    })

                if not rule.get("criteria"):
                    errors.append({
                        "field": f"programs[{i}].rules[{j}].criteria",
                        "message": "Rule criteria is required",
                        "severity": "error",
                    })

        return {
            "valid": len(errors) == 0,
            "errors": errors + warnings,
            "suggestions": [
                "Review all programs have appropriate credit tiers",
                "Verify rate_metadata contains accurate rate information",
                "Check that is_mandatory flags are correctly set",
            ] if len(errors) == 0 else [],
        }
