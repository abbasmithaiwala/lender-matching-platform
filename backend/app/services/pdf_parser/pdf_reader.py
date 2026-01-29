"""PDF text extraction utility using pdfplumber and pypdf."""

import logging
from pathlib import Path
from typing import Optional

import pdfplumber
import pypdf

logger = logging.getLogger(__name__)


class PDFReader:
    """Utility for extracting text content from PDF files."""

    @staticmethod
    def extract_text_pdfplumber(pdf_path: Path) -> str:
        """
        Extract text from PDF using pdfplumber (better for structured documents).

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text content from all pages

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            Exception: For other PDF reading errors
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            text_content = []
            with pdfplumber.open(pdf_path) as pdf:
                logger.info(f"Reading PDF with {len(pdf.pages)} pages: {pdf_path.name}")
                for page_num, page in enumerate(pdf.pages, start=1):
                    page_text = page.extract_text()
                    if page_text:
                        text_content.append(f"--- Page {page_num} ---\n{page_text}")
                    else:
                        logger.warning(f"No text extracted from page {page_num}")

            full_text = "\n\n".join(text_content)
            logger.info(
                f"Successfully extracted {len(full_text)} characters from {pdf_path.name}"
            )
            return full_text

        except Exception as e:
            logger.error(f"Error reading PDF with pdfplumber: {e}")
            raise

    @staticmethod
    def extract_text_pypdf(pdf_path: Path) -> str:
        """
        Extract text from PDF using pypdf (fallback method).

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text content from all pages

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            Exception: For other PDF reading errors
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            text_content = []
            with open(pdf_path, "rb") as file:
                pdf_reader = pypdf.PdfReader(file)
                logger.info(f"Reading PDF with {len(pdf_reader.pages)} pages: {pdf_path.name}")

                for page_num, page in enumerate(pdf_reader.pages, start=1):
                    page_text = page.extract_text()
                    if page_text:
                        text_content.append(f"--- Page {page_num} ---\n{page_text}")
                    else:
                        logger.warning(f"No text extracted from page {page_num}")

            full_text = "\n\n".join(text_content)
            logger.info(
                f"Successfully extracted {len(full_text)} characters from {pdf_path.name}"
            )
            return full_text

        except Exception as e:
            logger.error(f"Error reading PDF with pypdf: {e}")
            raise

    @classmethod
    def extract_text(
        cls, pdf_path: Path, method: str = "pdfplumber"
    ) -> str:
        """
        Extract text from PDF using the specified method.

        Args:
            pdf_path: Path to the PDF file
            method: Extraction method ('pdfplumber' or 'pypdf')

        Returns:
            Extracted text content

        Raises:
            ValueError: If invalid method specified
            FileNotFoundError: If PDF file doesn't exist
            Exception: For other PDF reading errors
        """
        pdf_path = Path(pdf_path)

        if method == "pdfplumber":
            return cls.extract_text_pdfplumber(pdf_path)
        elif method == "pypdf":
            return cls.extract_text_pypdf(pdf_path)
        else:
            raise ValueError(f"Invalid extraction method: {method}. Use 'pdfplumber' or 'pypdf'")

    @classmethod
    def extract_text_with_fallback(cls, pdf_path: Path) -> str:
        """
        Extract text from PDF with automatic fallback.
        Tries pdfplumber first, falls back to pypdf if it fails.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text content

        Raises:
            Exception: If both methods fail
        """
        pdf_path = Path(pdf_path)

        try:
            return cls.extract_text_pdfplumber(pdf_path)
        except Exception as e:
            logger.warning(
                f"pdfplumber extraction failed: {e}. Trying pypdf as fallback..."
            )
            try:
                return cls.extract_text_pypdf(pdf_path)
            except Exception as fallback_error:
                logger.error(f"Both extraction methods failed for {pdf_path.name}")
                raise Exception(
                    f"Failed to extract text from PDF using both methods. "
                    f"pdfplumber error: {e}, pypdf error: {fallback_error}"
                )

    @staticmethod
    def get_pdf_metadata(pdf_path: Path) -> dict:
        """
        Extract metadata from PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary containing PDF metadata

        Raises:
            FileNotFoundError: If PDF file doesn't exist
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            with open(pdf_path, "rb") as file:
                pdf_reader = pypdf.PdfReader(file)
                metadata = pdf_reader.metadata or {}

                return {
                    "title": metadata.get("/Title", ""),
                    "author": metadata.get("/Author", ""),
                    "subject": metadata.get("/Subject", ""),
                    "creator": metadata.get("/Creator", ""),
                    "producer": metadata.get("/Producer", ""),
                    "creation_date": metadata.get("/CreationDate", ""),
                    "modification_date": metadata.get("/ModDate", ""),
                    "page_count": len(pdf_reader.pages),
                }
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            return {}
