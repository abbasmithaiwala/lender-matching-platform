"""Repository for lender data access optimized for matching engine queries."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.domain.lender import Lender, PolicyProgram, PolicyRule
from app.repositories.base import BaseRepository


class LenderRepository(BaseRepository[Lender]):
    """
    Repository for Lender with specialized queries.

    Provides optimized queries with deep eager loading for programs and rules,
    specifically designed for efficient matching engine operations.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the lender repository.

        Args:
            db: Async database session
        """
        super().__init__(Lender, db)

    async def get_active_lenders(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Lender]:
        """
        Retrieve all active lenders.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of active lenders (without deep relations loaded)
        """
        stmt = (
            select(Lender)
            .where(Lender.active == True)
            .order_by(Lender.name)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id_with_policies(self, id: UUID) -> Optional[Lender]:
        """
        Retrieve a lender by ID with all programs and rules eagerly loaded.

        Uses deep eager loading to fetch the complete policy hierarchy
        in a single optimized query, preventing N+1 query issues.

        Args:
            id: The UUID of the lender

        Returns:
            The lender with programs and rules loaded, or None if not found
        """
        stmt = (
            select(Lender)
            .where(Lender.id == id)
            .options(
                selectinload(Lender.programs).selectinload(PolicyProgram.rules)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Lender]:
        """
        Retrieve a lender by name.

        Args:
            name: Lender name (case-sensitive)

        Returns:
            The lender if found, None otherwise
        """
        stmt = select(Lender).where(Lender.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_lenders_with_policies(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Lender]:
        """
        Retrieve active lenders with complete policy hierarchies.

        This method is optimized for the matching engine, loading all
        active lenders with their programs and rules in a single efficient
        query. This prevents N+1 query issues when evaluating multiple lenders.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of active lenders with programs and rules fully loaded
        """
        stmt = (
            select(Lender)
            .where(Lender.active == True)
            .options(
                selectinload(Lender.programs).selectinload(PolicyProgram.rules)
            )
            .order_by(Lender.name)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_all_lenders_with_policies(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Lender]:
        """
        Retrieve all lenders (active and inactive) with complete policies.

        Useful for admin interfaces that need to display or manage
        all lender configurations regardless of active status.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of all lenders with programs and rules fully loaded
        """
        stmt = (
            select(Lender)
            .options(
                selectinload(Lender.programs).selectinload(PolicyProgram.rules)
            )
            .order_by(Lender.name)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_active_programs_for_lender(
        self, lender_id: UUID
    ) -> List[PolicyProgram]:
        """
        Retrieve all active programs for a specific lender.

        Args:
            lender_id: UUID of the lender

        Returns:
            List of active programs with rules loaded
        """
        stmt = (
            select(PolicyProgram)
            .where(
                PolicyProgram.lender_id == lender_id,
                PolicyProgram.active == True,
            )
            .options(selectinload(PolicyProgram.rules))
            .order_by(PolicyProgram.program_code)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_active_lenders(self) -> int:
        """
        Count the number of active lenders.

        Returns:
            Number of active lenders
        """
        stmt = select(Lender).where(Lender.active == True)
        result = await self.db.execute(stmt)
        return len(list(result.scalars().all()))

    async def count_programs_for_lender(self, lender_id: UUID) -> int:
        """
        Count the number of programs for a specific lender.

        Args:
            lender_id: UUID of the lender

        Returns:
            Number of programs (both active and inactive)
        """
        stmt = select(PolicyProgram).where(PolicyProgram.lender_id == lender_id)
        result = await self.db.execute(stmt)
        return len(list(result.scalars().all()))

    async def deactivate_lender(self, id: UUID) -> Optional[Lender]:
        """
        Deactivate a lender (soft delete).

        Args:
            id: UUID of the lender

        Returns:
            Updated lender, or None if not found
        """
        lender = await self.get_by_id(id)
        if lender:
            lender.active = False
            await self.db.flush()
            await self.db.refresh(lender)
            return lender
        return None

    async def activate_lender(self, id: UUID) -> Optional[Lender]:
        """
        Activate a lender.

        Args:
            id: UUID of the lender

        Returns:
            Updated lender, or None if not found
        """
        lender = await self.get_by_id(id)
        if lender:
            lender.active = True
            await self.db.flush()
            await self.db.refresh(lender)
            return lender
        return None
