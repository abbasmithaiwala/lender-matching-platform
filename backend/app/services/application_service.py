"""Application service for business logic and CRUD operations."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ApplicationStatus
from app.models.domain.application import (
    LoanApplication,
    Business,
    PersonalGuarantor,
    Equipment,
)
from app.repositories.application_repository import ApplicationRepository


class ApplicationService:
    """
    Application service for managing loan applications.

    Provides business logic for creating, retrieving, updating loan applications
    with proper validation and application number generation.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the application service.

        Args:
            db: Async database session
        """
        self.db = db
        self.repo = ApplicationRepository(db)

    @staticmethod
    def generate_application_number() -> str:
        """
        Generate a unique application number.

        Format: APP-YYYYMMDD-XXXXXXXX
        Example: APP-20260129-A3F5B2C1

        Returns:
            A unique application number string
        """
        date_str = datetime.now().strftime("%Y%m%d")
        unique_id = uuid.uuid4().hex[:8].upper()
        return f"APP-{date_str}-{unique_id}"

    async def create_application(
        self,
        business_data: Dict[str, Any],
        guarantor_data: Dict[str, Any],
        equipment_data: Dict[str, Any],
        loan_data: Dict[str, Any],
    ) -> LoanApplication:
        """
        Create a new loan application with all related entities.

        Args:
            business_data: Business information dictionary
            guarantor_data: Personal guarantor information dictionary
            equipment_data: Equipment information dictionary
            loan_data: Loan details dictionary

        Returns:
            Created loan application with all relations

        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Validate required fields
        self._validate_business_data(business_data)
        self._validate_guarantor_data(guarantor_data)
        self._validate_equipment_data(equipment_data)
        self._validate_loan_data(loan_data)

        # Create business entity
        business = Business(**business_data)
        self.db.add(business)

        # Create guarantor entity
        guarantor = PersonalGuarantor(**guarantor_data)
        self.db.add(guarantor)

        # Create equipment entity
        equipment = Equipment(**equipment_data)
        self.db.add(equipment)

        # Flush to get IDs for foreign keys
        await self.db.flush()

        # Create application with generated number
        application_number = self.generate_application_number()

        # Calculate down payment amount if percentage is provided
        requested_amount = Decimal(str(loan_data.get("requested_amount", 0)))
        down_payment_percentage = loan_data.get("down_payment_percentage")
        down_payment_amount = loan_data.get("down_payment_amount")

        if down_payment_percentage and not down_payment_amount:
            down_payment_amount = (
                requested_amount * Decimal(str(down_payment_percentage)) / Decimal("100")
            )

        application = LoanApplication(
            application_number=application_number,
            business_id=business.id,
            guarantor_id=guarantor.id,
            equipment_id=equipment.id,
            requested_amount=requested_amount,
            requested_term_months=loan_data.get("requested_term_months"),
            down_payment_percentage=Decimal(str(down_payment_percentage))
            if down_payment_percentage
            else None,
            down_payment_amount=Decimal(str(down_payment_amount))
            if down_payment_amount
            else None,
            purpose=loan_data.get("purpose"),
            comparable_debt_payments=Decimal(str(loan_data["comparable_debt_payments"]))
            if loan_data.get("comparable_debt_payments")
            else None,
            status=ApplicationStatus.DRAFT,
        )

        self.db.add(application)
        await self.db.commit()
        await self.db.refresh(application)

        # Load relations
        return await self.repo.get_by_id_with_relations(application.id)

    async def get_application(self, application_id: UUID) -> Optional[LoanApplication]:
        """
        Retrieve an application by ID with all relations.

        Args:
            application_id: UUID of the application

        Returns:
            Application with all relations loaded, or None if not found
        """
        return await self.repo.get_by_id_with_relations(application_id)

    async def get_application_by_number(
        self, application_number: str
    ) -> Optional[LoanApplication]:
        """
        Retrieve an application by application number.

        Args:
            application_number: Application number (e.g., APP-20260129-A3F5B2C1)

        Returns:
            Application with all relations, or None if not found
        """
        return await self.repo.get_by_application_number(application_number)

    async def get_all_applications(
        self, skip: int = 0, limit: int = 100
    ) -> List[LoanApplication]:
        """
        Retrieve all applications with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of applications with relations loaded
        """
        return await self.repo.get_all_with_relations(skip=skip, limit=limit)

    async def get_applications_by_status(
        self, status: ApplicationStatus
    ) -> List[LoanApplication]:
        """
        Retrieve all applications with a specific status.

        Args:
            status: Application status to filter by

        Returns:
            List of applications with the given status
        """
        return await self.repo.get_by_status(status)

    async def get_pending_underwriting_applications(self) -> List[LoanApplication]:
        """
        Retrieve applications that are pending underwriting.

        Returns:
            List of submitted applications waiting for underwriting
        """
        return await self.repo.get_pending_underwriting()

    async def update_application_status(
        self, application_id: UUID, status: ApplicationStatus
    ) -> Optional[LoanApplication]:
        """
        Update the status of an application.

        Args:
            application_id: UUID of the application
            status: New status to set

        Returns:
            Updated application, or None if not found
        """
        application = await self.repo.get_by_id(application_id)
        if not application:
            return None

        # Set submitted_at timestamp when transitioning to SUBMITTED
        if status == ApplicationStatus.SUBMITTED and not application.submitted_at:
            application.submitted_at = datetime.now()

        application.status = status
        await self.db.commit()
        await self.db.refresh(application)

        return await self.repo.get_by_id_with_relations(application.id)

    async def submit_application(
        self, application_id: UUID
    ) -> Optional[LoanApplication]:
        """
        Submit an application (transition from DRAFT to SUBMITTED).

        Args:
            application_id: UUID of the application

        Returns:
            Updated application, or None if not found

        Raises:
            ValueError: If application is not in DRAFT status
        """
        application = await self.repo.get_by_id(application_id)
        if not application:
            return None

        if application.status != ApplicationStatus.DRAFT:
            raise ValueError(
                f"Cannot submit application with status {application.status.value}"
            )

        return await self.update_application_status(
            application_id, ApplicationStatus.SUBMITTED
        )

    async def delete_application(self, application_id: UUID) -> bool:
        """
        Delete an application and all related entities.

        Args:
            application_id: UUID of the application

        Returns:
            True if deleted, False if not found
        """
        return await self.repo.delete(application_id)

    async def count_applications_by_status(
        self, status: ApplicationStatus
    ) -> int:
        """
        Count applications by status.

        Args:
            status: Application status to count

        Returns:
            Number of applications with the given status
        """
        return await self.repo.count_by_status(status)

    # Validation methods
    @staticmethod
    def _validate_business_data(data: Dict[str, Any]) -> None:
        """Validate business data has required fields."""
        required_fields = [
            "legal_name",
            "industry",
            "legal_structure",
            "established_date",
            "address_line1",
            "city",
            "state",
            "zip_code",
        ]
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            raise ValueError(
                f"Missing required business fields: {', '.join(missing_fields)}"
            )

        # Validate state is 2 characters
        if len(data.get("state", "")) != 2:
            raise ValueError("State must be a 2-letter code")

    @staticmethod
    def _validate_guarantor_data(data: Dict[str, Any]) -> None:
        """Validate guarantor data has required fields."""
        required_fields = ["first_name", "last_name"]
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            raise ValueError(
                f"Missing required guarantor fields: {', '.join(missing_fields)}"
            )

        # Validate credit scores if provided
        fico = data.get("fico_score")
        if fico and (fico < 300 or fico > 850):
            raise ValueError("FICO score must be between 300 and 850")

        paynet = data.get("paynet_score")
        if paynet and (paynet < 1 or paynet > 100):
            raise ValueError("PayNet score must be between 1 and 100")

    @staticmethod
    def _validate_equipment_data(data: Dict[str, Any]) -> None:
        """Validate equipment data has required fields."""
        required_fields = ["equipment_type", "condition", "cost"]
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            raise ValueError(
                f"Missing required equipment fields: {', '.join(missing_fields)}"
            )

        # Validate cost is positive
        cost = data.get("cost")
        if cost and Decimal(str(cost)) <= 0:
            raise ValueError("Equipment cost must be greater than 0")

    @staticmethod
    def _validate_loan_data(data: Dict[str, Any]) -> None:
        """Validate loan data has required fields."""
        required_fields = ["requested_amount", "requested_term_months"]
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            raise ValueError(
                f"Missing required loan fields: {', '.join(missing_fields)}"
            )

        # Validate amounts are positive
        requested_amount = data.get("requested_amount")
        if requested_amount and Decimal(str(requested_amount)) <= 0:
            raise ValueError("Requested amount must be greater than 0")

        # Validate term is positive
        term = data.get("requested_term_months")
        if term and term <= 0:
            raise ValueError("Requested term must be greater than 0")

        # Validate down payment percentage if provided
        down_payment_pct = data.get("down_payment_percentage")
        if down_payment_pct:
            pct_decimal = Decimal(str(down_payment_pct))
            if pct_decimal < 0 or pct_decimal > 100:
                raise ValueError("Down payment percentage must be between 0 and 100")
