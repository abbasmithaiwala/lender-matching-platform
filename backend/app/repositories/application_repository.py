"""Repository for loan application data access with specialized queries."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import ApplicationStatus
from app.models.domain.application import LoanApplication, Business, PersonalGuarantor, Equipment
from app.repositories.base import BaseRepository


class ApplicationRepository(BaseRepository[LoanApplication]):
    """
    Repository for LoanApplication with specialized queries.

    Provides optimized queries with eager loading for related entities
    (business, guarantor, equipment) and status-based filtering.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the application repository.

        Args:
            db: Async database session
        """
        super().__init__(LoanApplication, db)

    async def get_by_id_with_relations(self, id: UUID) -> Optional[LoanApplication]:
        """
        Retrieve an application by ID with all related entities eagerly loaded.

        Uses selectinload to optimize query performance and avoid N+1 queries.

        Args:
            id: The UUID of the application

        Returns:
            The application with business, guarantor, and equipment loaded,
            or None if not found
        """
        stmt = (
            select(LoanApplication)
            .where(LoanApplication.id == id)
            .options(
                selectinload(LoanApplication.business),
                selectinload(LoanApplication.guarantor),
                selectinload(LoanApplication.equipment),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_application_number(
        self, application_number: str
    ) -> Optional[LoanApplication]:
        """
        Retrieve an application by its application number.

        Args:
            application_number: Unique application number

        Returns:
            The application if found, None otherwise
        """
        stmt = (
            select(LoanApplication)
            .where(LoanApplication.application_number == application_number)
            .options(
                selectinload(LoanApplication.business),
                selectinload(LoanApplication.guarantor),
                selectinload(LoanApplication.equipment),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_with_relations(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[LoanApplication]:
        """
        Retrieve all applications with related entities eagerly loaded.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of applications with all relations loaded
        """
        stmt = (
            select(LoanApplication)
            .options(
                selectinload(LoanApplication.business),
                selectinload(LoanApplication.guarantor),
                selectinload(LoanApplication.equipment),
            )
            .order_by(LoanApplication.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_status(
        self,
        status: ApplicationStatus,
        skip: int = 0,
        limit: int = 100,
    ) -> List[LoanApplication]:
        """
        Retrieve applications filtered by status with relations loaded.

        Args:
            status: Application status to filter by
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of applications matching the status
        """
        stmt = (
            select(LoanApplication)
            .where(LoanApplication.status == status)
            .options(
                selectinload(LoanApplication.business),
                selectinload(LoanApplication.guarantor),
                selectinload(LoanApplication.equipment),
            )
            .order_by(LoanApplication.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_business_id(
        self,
        business_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> List[LoanApplication]:
        """
        Retrieve all applications for a specific business.

        Args:
            business_id: UUID of the business
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of applications for the business
        """
        stmt = (
            select(LoanApplication)
            .where(LoanApplication.business_id == business_id)
            .options(
                selectinload(LoanApplication.business),
                selectinload(LoanApplication.guarantor),
                selectinload(LoanApplication.equipment),
            )
            .order_by(LoanApplication.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_submitted_applications(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[LoanApplication]:
        """
        Retrieve applications that have been submitted (not in draft status).

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of submitted applications
        """
        stmt = (
            select(LoanApplication)
            .where(LoanApplication.status != ApplicationStatus.DRAFT)
            .options(
                selectinload(LoanApplication.business),
                selectinload(LoanApplication.guarantor),
                selectinload(LoanApplication.equipment),
            )
            .order_by(LoanApplication.submitted_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_pending_underwriting(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[LoanApplication]:
        """
        Retrieve applications pending underwriting evaluation.

        Returns applications with status SUBMITTED or UNDER_REVIEW that
        need to be processed through the matching engine.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of applications pending underwriting
        """
        stmt = (
            select(LoanApplication)
            .where(
                LoanApplication.status.in_([
                    ApplicationStatus.SUBMITTED,
                    ApplicationStatus.UNDER_REVIEW,
                ])
            )
            .options(
                selectinload(LoanApplication.business),
                selectinload(LoanApplication.guarantor),
                selectinload(LoanApplication.equipment),
            )
            .order_by(LoanApplication.submitted_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_status(self, status: ApplicationStatus) -> int:
        """
        Count applications with a specific status.

        Args:
            status: Application status to count

        Returns:
            Number of applications with the given status
        """
        stmt = select(LoanApplication).where(LoanApplication.status == status)
        result = await self.db.execute(stmt)
        return len(list(result.scalars().all()))

    async def update_status(
        self,
        id: UUID,
        status: ApplicationStatus,
    ) -> Optional[LoanApplication]:
        """
        Update the status of an application.

        Args:
            id: UUID of the application
            status: New status to set

        Returns:
            Updated application with relations, or None if not found
        """
        application = await self.get_by_id(id)
        if application:
            application.status = status
            await self.db.flush()
            await self.db.refresh(application)
            # Re-fetch with relations
            return await self.get_by_id_with_relations(id)
        return None
