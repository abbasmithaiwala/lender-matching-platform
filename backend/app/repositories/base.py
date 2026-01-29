from typing import Generic, TypeVar, Type, Optional, List, Any, Dict
from uuid import UUID
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeMeta

# Type variable for the model class
ModelType = TypeVar("ModelType", bound=DeclarativeMeta)


class BaseRepository(Generic[ModelType]):
    """
    Generic base repository providing common CRUD operations.

    This class implements the repository pattern with async database operations,
    providing a foundation for domain-specific repositories to extend.

    Type Parameters:
        ModelType: The SQLAlchemy model class this repository manages
    """

    def __init__(self, model: Type[ModelType], db: AsyncSession):
        """
        Initialize the repository.

        Args:
            model: The SQLAlchemy model class
            db: Async database session
        """
        self.model = model
        self.db = db

    async def create(self, **kwargs: Any) -> ModelType:
        """
        Create a new entity.

        Args:
            **kwargs: Field values for the new entity

        Returns:
            The created entity with generated ID
        """
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def get_by_id(self, id: UUID) -> Optional[ModelType]:
        """
        Retrieve an entity by its ID.

        Args:
            id: The UUID of the entity

        Returns:
            The entity if found, None otherwise
        """
        stmt = select(self.model).where(self.model.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[Any] = None
    ) -> List[ModelType]:
        """
        Retrieve all entities with pagination.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return
            order_by: Optional ordering clause

        Returns:
            List of entities
        """
        stmt = select(self.model).offset(skip).limit(limit)

        if order_by is not None:
            stmt = stmt.order_by(order_by)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update(self, id: UUID, **kwargs: Any) -> Optional[ModelType]:
        """
        Update an entity by ID.

        Args:
            id: The UUID of the entity to update
            **kwargs: Fields to update with new values

        Returns:
            The updated entity if found, None otherwise
        """
        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**kwargs)
            .returning(self.model)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.scalar_one_or_none()

    async def delete(self, id: UUID) -> bool:
        """
        Delete an entity by ID.

        Args:
            id: The UUID of the entity to delete

        Returns:
            True if entity was deleted, False if not found
        """
        stmt = delete(self.model).where(self.model.id == id)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount > 0

    async def exists(self, id: UUID) -> bool:
        """
        Check if an entity exists by ID.

        Args:
            id: The UUID of the entity

        Returns:
            True if entity exists, False otherwise
        """
        stmt = select(self.model.id).where(self.model.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def count(self, **filters: Any) -> int:
        """
        Count entities matching the given filters.

        Args:
            **filters: Field equality filters

        Returns:
            Count of matching entities
        """
        stmt = select(self.model)

        for field, value in filters.items():
            if hasattr(self.model, field):
                stmt = stmt.where(getattr(self.model, field) == value)

        result = await self.db.execute(stmt)
        return len(list(result.scalars().all()))

    async def find_by(self, **filters: Any) -> List[ModelType]:
        """
        Find entities matching the given field filters.

        Args:
            **filters: Field equality filters (e.g., status="active")

        Returns:
            List of matching entities
        """
        stmt = select(self.model)

        for field, value in filters.items():
            if hasattr(self.model, field):
                stmt = stmt.where(getattr(self.model, field) == value)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def find_one_by(self, **filters: Any) -> Optional[ModelType]:
        """
        Find a single entity matching the given filters.

        Args:
            **filters: Field equality filters

        Returns:
            The first matching entity, or None if not found
        """
        stmt = select(self.model)

        for field, value in filters.items():
            if hasattr(self.model, field):
                stmt = stmt.where(getattr(self.model, field) == value)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
