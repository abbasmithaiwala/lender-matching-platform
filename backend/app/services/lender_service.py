"""Lender service for policy management and CRUD operations."""

from decimal import Decimal
from typing import Dict, Any, Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RuleType
from app.models.domain.lender import Lender, PolicyProgram, PolicyRule
from app.repositories.lender_repository import LenderRepository


class LenderService:
    """
    Lender service for managing lenders, programs, and policy rules.

    Provides business logic for creating, retrieving, updating lenders
    and their policy configurations with proper JSONB validation.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the lender service.

        Args:
            db: Async database session
        """
        self.db = db
        self.repo = LenderRepository(db)

    # ===== Lender CRUD Operations =====

    async def create_lender(
        self,
        name: str,
        description: Optional[str] = None,
        min_loan_amount: Optional[Decimal] = None,
        max_loan_amount: Optional[Decimal] = None,
        excluded_states: Optional[List[str]] = None,
        excluded_industries: Optional[List[str]] = None,
        active: bool = True,
    ) -> Lender:
        """
        Create a new lender with first-class exclusions.

        Args:
            name: Lender name (must be unique)
            description: Optional description
            min_loan_amount: Minimum loan amount this lender accepts
            max_loan_amount: Maximum loan amount this lender accepts
            excluded_states: List of state codes to exclude (e.g., ["CA", "NV"])
            excluded_industries: List of industries to exclude (e.g., ["Cannabis"])
            active: Whether the lender is active

        Returns:
            Created lender

        Raises:
            ValueError: If validation fails or name already exists
        """
        # Check if lender name already exists
        existing = await self.repo.get_by_name(name)
        if existing:
            raise ValueError(f"Lender with name '{name}' already exists")

        # Validate loan amount constraints
        if min_loan_amount and max_loan_amount:
            if min_loan_amount > max_loan_amount:
                raise ValueError("min_loan_amount cannot exceed max_loan_amount")

        # Validate state codes if provided
        if excluded_states:
            self._validate_state_codes(excluded_states)

        lender = Lender(
            name=name,
            description=description,
            min_loan_amount=min_loan_amount,
            max_loan_amount=max_loan_amount,
            excluded_states=excluded_states,
            excluded_industries=excluded_industries,
            active=active,
        )

        self.db.add(lender)
        await self.db.commit()
        await self.db.refresh(lender)

        return lender

    async def get_lender(self, lender_id: UUID) -> Optional[Lender]:
        """
        Retrieve a lender by ID with all policies.

        Args:
            lender_id: UUID of the lender

        Returns:
            Lender with programs and rules loaded, or None if not found
        """
        return await self.repo.get_by_id_with_policies(lender_id)

    async def get_lender_by_name(self, name: str) -> Optional[Lender]:
        """
        Retrieve a lender by name.

        Args:
            name: Lender name

        Returns:
            Lender if found, None otherwise
        """
        return await self.repo.get_by_name(name)

    async def get_all_lenders(
        self, active_only: bool = True, skip: int = 0, limit: int = 100
    ) -> List[Lender]:
        """
        Retrieve all lenders with their policies.

        Args:
            active_only: If True, return only active lenders
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of lenders with policies loaded
        """
        if active_only:
            return await self.repo.get_active_lenders_with_policies(
                skip=skip, limit=limit
            )
        return await self.repo.get_all_lenders_with_policies(skip=skip, limit=limit)

    async def update_lender(
        self,
        lender_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        min_loan_amount: Optional[Decimal] = None,
        max_loan_amount: Optional[Decimal] = None,
        excluded_states: Optional[List[str]] = None,
        excluded_industries: Optional[List[str]] = None,
        active: Optional[bool] = None,
    ) -> Optional[Lender]:
        """
        Update a lender's information.

        Args:
            lender_id: UUID of the lender
            name: New name (optional)
            description: New description (optional)
            min_loan_amount: New minimum loan amount (optional)
            max_loan_amount: New maximum loan amount (optional)
            excluded_states: New excluded states list (optional)
            excluded_industries: New excluded industries list (optional)
            active: New active status (optional)

        Returns:
            Updated lender, or None if not found

        Raises:
            ValueError: If validation fails
        """
        lender = await self.repo.get_by_id(lender_id)
        if not lender:
            return None

        # Check name uniqueness if changing
        if name and name != lender.name:
            existing = await self.repo.get_by_name(name)
            if existing:
                raise ValueError(f"Lender with name '{name}' already exists")
            lender.name = name

        if description is not None:
            lender.description = description

        if min_loan_amount is not None:
            lender.min_loan_amount = min_loan_amount

        if max_loan_amount is not None:
            lender.max_loan_amount = max_loan_amount

        # Validate loan amount constraints
        if lender.min_loan_amount and lender.max_loan_amount:
            if lender.min_loan_amount > lender.max_loan_amount:
                raise ValueError("min_loan_amount cannot exceed max_loan_amount")

        if excluded_states is not None:
            self._validate_state_codes(excluded_states)
            lender.excluded_states = excluded_states

        if excluded_industries is not None:
            lender.excluded_industries = excluded_industries

        if active is not None:
            lender.active = active

        await self.db.commit()
        await self.db.refresh(lender)

        return await self.repo.get_by_id_with_policies(lender_id)

    async def delete_lender(self, lender_id: UUID) -> bool:
        """
        Delete a lender and all associated programs/rules (cascade).

        Args:
            lender_id: UUID of the lender

        Returns:
            True if deleted, False if not found
        """
        return await self.repo.delete(lender_id)

    async def activate_lender(self, lender_id: UUID) -> Optional[Lender]:
        """
        Activate a lender.

        Args:
            lender_id: UUID of the lender

        Returns:
            Updated lender, or None if not found
        """
        return await self.repo.activate_lender(lender_id)

    async def deactivate_lender(self, lender_id: UUID) -> Optional[Lender]:
        """
        Deactivate a lender (soft delete).

        Args:
            lender_id: UUID of the lender

        Returns:
            Updated lender, or None if not found
        """
        return await self.repo.deactivate_lender(lender_id)

    # ===== Program CRUD Operations =====

    async def create_program(
        self,
        lender_id: UUID,
        program_name: str,
        program_code: Optional[str] = None,
        description: Optional[str] = None,
        credit_tier: Optional[str] = None,
        eligibility_conditions: Optional[Dict[str, Any]] = None,
        rate_metadata: Optional[Dict[str, Any]] = None,
        min_fit_score: Optional[Decimal] = None,
        active: bool = True,
    ) -> PolicyProgram:
        """
        Create a new policy program for a lender.

        Args:
            lender_id: UUID of the lender
            program_name: Program name
            program_code: Program code (e.g., "A", "B", "Medical A+")
            description: Optional description
            credit_tier: Credit tier classification
            eligibility_conditions: JSONB for program applicability logic
            rate_metadata: JSONB for rate tables and adjustments
            min_fit_score: Minimum fit score threshold (0-100)
            active: Whether the program is active

        Returns:
            Created program

        Raises:
            ValueError: If lender not found or validation fails
        """
        # Verify lender exists
        lender = await self.repo.get_by_id(lender_id)
        if not lender:
            raise ValueError(f"Lender with ID {lender_id} not found")

        # Validate eligibility_conditions JSONB
        if eligibility_conditions:
            self._validate_eligibility_conditions(eligibility_conditions)

        # Validate rate_metadata JSONB
        if rate_metadata:
            self._validate_rate_metadata(rate_metadata)

        # Validate min_fit_score range
        if min_fit_score and (min_fit_score < 0 or min_fit_score > 100):
            raise ValueError("min_fit_score must be between 0 and 100")

        program = PolicyProgram(
            lender_id=lender_id,
            program_name=program_name,
            program_code=program_code,
            description=description,
            credit_tier=credit_tier,
            eligibility_conditions=eligibility_conditions or {},
            rate_metadata=rate_metadata or {},
            min_fit_score=min_fit_score or Decimal("0.00"),
            active=active,
        )

        self.db.add(program)
        await self.db.commit()
        await self.db.refresh(program)

        return program

    async def get_program(self, program_id: UUID) -> Optional[PolicyProgram]:
        """
        Retrieve a program by ID.

        Args:
            program_id: UUID of the program

        Returns:
            Program if found, None otherwise
        """
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        stmt = (
            select(PolicyProgram)
            .where(PolicyProgram.id == program_id)
            .options(selectinload(PolicyProgram.rules))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_programs_for_lender(
        self, lender_id: UUID, active_only: bool = True
    ) -> List[PolicyProgram]:
        """
        Retrieve all programs for a lender.

        Args:
            lender_id: UUID of the lender
            active_only: If True, return only active programs

        Returns:
            List of programs with rules loaded
        """
        if active_only:
            return await self.repo.get_active_programs_for_lender(lender_id)

        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        stmt = (
            select(PolicyProgram)
            .where(PolicyProgram.lender_id == lender_id)
            .options(selectinload(PolicyProgram.rules))
            .order_by(PolicyProgram.program_code)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_program(
        self,
        program_id: UUID,
        program_name: Optional[str] = None,
        program_code: Optional[str] = None,
        description: Optional[str] = None,
        credit_tier: Optional[str] = None,
        eligibility_conditions: Optional[Dict[str, Any]] = None,
        rate_metadata: Optional[Dict[str, Any]] = None,
        min_fit_score: Optional[Decimal] = None,
        active: Optional[bool] = None,
    ) -> Optional[PolicyProgram]:
        """
        Update a program's information.

        Args:
            program_id: UUID of the program
            (other parameters as optional updates)

        Returns:
            Updated program, or None if not found

        Raises:
            ValueError: If validation fails
        """
        program = await self.get_program(program_id)
        if not program:
            return None

        if program_name is not None:
            program.program_name = program_name

        if program_code is not None:
            program.program_code = program_code

        if description is not None:
            program.description = description

        if credit_tier is not None:
            program.credit_tier = credit_tier

        if eligibility_conditions is not None:
            self._validate_eligibility_conditions(eligibility_conditions)
            program.eligibility_conditions = eligibility_conditions

        if rate_metadata is not None:
            self._validate_rate_metadata(rate_metadata)
            program.rate_metadata = rate_metadata

        if min_fit_score is not None:
            if min_fit_score < 0 or min_fit_score > 100:
                raise ValueError("min_fit_score must be between 0 and 100")
            program.min_fit_score = min_fit_score

        if active is not None:
            program.active = active

        await self.db.commit()
        await self.db.refresh(program)

        return program

    async def delete_program(self, program_id: UUID) -> bool:
        """
        Delete a program and all associated rules (cascade).

        Args:
            program_id: UUID of the program

        Returns:
            True if deleted, False if not found
        """
        program = await self.get_program(program_id)
        if not program:
            return False

        await self.db.delete(program)
        await self.db.commit()
        return True

    # ===== Rule CRUD Operations =====

    async def create_rule(
        self,
        program_id: UUID,
        rule_type: RuleType,
        rule_name: str,
        criteria: Dict[str, Any],
        description: Optional[str] = None,
        weight: Decimal = Decimal("1.00"),
        is_mandatory: bool = True,
        active: bool = True,
    ) -> PolicyRule:
        """
        Create a new policy rule for a program.

        Args:
            program_id: UUID of the program
            rule_type: Type of rule (from RuleType enum)
            rule_name: Human-readable rule name
            criteria: JSONB criteria specific to rule type
            description: Optional description
            weight: Weight for scoring (default 1.0)
            is_mandatory: True for hard requirements, False for guidelines
            active: Whether the rule is active

        Returns:
            Created rule

        Raises:
            ValueError: If program not found or validation fails
        """
        # Verify program exists
        program = await self.get_program(program_id)
        if not program:
            raise ValueError(f"Program with ID {program_id} not found")

        # Validate criteria JSONB based on rule type
        self._validate_rule_criteria(rule_type, criteria)

        # Validate weight
        if weight < 0:
            raise ValueError("Weight must be non-negative")

        rule = PolicyRule(
            program_id=program_id,
            rule_type=rule_type,
            rule_name=rule_name,
            description=description,
            criteria=criteria,
            weight=weight,
            is_mandatory=is_mandatory,
            active=active,
        )

        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)

        return rule

    async def get_rule(self, rule_id: UUID) -> Optional[PolicyRule]:
        """
        Retrieve a rule by ID.

        Args:
            rule_id: UUID of the rule

        Returns:
            Rule if found, None otherwise
        """
        from sqlalchemy import select

        stmt = select(PolicyRule).where(PolicyRule.id == rule_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_rules_for_program(
        self, program_id: UUID, active_only: bool = True
    ) -> List[PolicyRule]:
        """
        Retrieve all rules for a program.

        Args:
            program_id: UUID of the program
            active_only: If True, return only active rules

        Returns:
            List of rules
        """
        from sqlalchemy import select

        stmt = select(PolicyRule).where(PolicyRule.program_id == program_id)

        if active_only:
            stmt = stmt.where(PolicyRule.active == True)

        stmt = stmt.order_by(PolicyRule.rule_type, PolicyRule.rule_name)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_rule(
        self,
        rule_id: UUID,
        rule_name: Optional[str] = None,
        criteria: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        weight: Optional[Decimal] = None,
        is_mandatory: Optional[bool] = None,
        active: Optional[bool] = None,
    ) -> Optional[PolicyRule]:
        """
        Update a rule's information.

        Args:
            rule_id: UUID of the rule
            (other parameters as optional updates)

        Returns:
            Updated rule, or None if not found

        Raises:
            ValueError: If validation fails
        """
        rule = await self.get_rule(rule_id)
        if not rule:
            return None

        if rule_name is not None:
            rule.rule_name = rule_name

        if criteria is not None:
            self._validate_rule_criteria(rule.rule_type, criteria)
            rule.criteria = criteria

        if description is not None:
            rule.description = description

        if weight is not None:
            if weight < 0:
                raise ValueError("Weight must be non-negative")
            rule.weight = weight

        if is_mandatory is not None:
            rule.is_mandatory = is_mandatory

        if active is not None:
            rule.active = active

        await self.db.commit()
        await self.db.refresh(rule)

        return rule

    async def delete_rule(self, rule_id: UUID) -> bool:
        """
        Delete a rule.

        Args:
            rule_id: UUID of the rule

        Returns:
            True if deleted, False if not found
        """
        rule = await self.get_rule(rule_id)
        if not rule:
            return False

        await self.db.delete(rule)
        await self.db.commit()
        return True

    # ===== Validation Methods =====

    @staticmethod
    def _validate_state_codes(states: List[str]) -> None:
        """Validate that all state codes are 2 characters."""
        for state in states:
            if len(state) != 2:
                raise ValueError(f"Invalid state code: {state}. Must be 2 characters.")

    @staticmethod
    def _validate_eligibility_conditions(conditions: Dict[str, Any]) -> None:
        """
        Validate eligibility_conditions JSONB structure.

        Examples of valid structures:
        - {"requires_paynet": true}
        - {"legal_structure": ["Corp", "S-Corp"]}
        - {"industry": ["Medical", "Healthcare"]}
        """
        # Basic validation - ensure it's a dict
        if not isinstance(conditions, dict):
            raise ValueError("eligibility_conditions must be a dictionary")

        # Validate known fields
        if "requires_paynet" in conditions:
            if not isinstance(conditions["requires_paynet"], bool):
                raise ValueError("requires_paynet must be a boolean")

        if "legal_structure" in conditions:
            if not isinstance(conditions["legal_structure"], list):
                raise ValueError("legal_structure must be a list")

        if "industry" in conditions:
            if not isinstance(conditions["industry"], list):
                raise ValueError("industry must be a list")

    @staticmethod
    def _validate_rate_metadata(metadata: Dict[str, Any]) -> None:
        """
        Validate rate_metadata JSONB structure.

        Example valid structure:
        {
            "base_rates": [
                {"min_amount": 10000, "max_amount": 50000, "rate": 7.25}
            ],
            "adjustments": [
                {"condition": "equipment_age > 15", "delta": 0.5}
            ]
        }
        """
        if not isinstance(metadata, dict):
            raise ValueError("rate_metadata must be a dictionary")

        # Validate base_rates if present
        if "base_rates" in metadata:
            if not isinstance(metadata["base_rates"], list):
                raise ValueError("base_rates must be a list")

            for rate in metadata["base_rates"]:
                if not isinstance(rate, dict):
                    raise ValueError("Each rate entry must be a dictionary")
                # Could add more specific validation here

        # Validate adjustments if present
        if "adjustments" in metadata:
            if not isinstance(metadata["adjustments"], list):
                raise ValueError("adjustments must be a list")

    @staticmethod
    def _validate_rule_criteria(rule_type: RuleType, criteria: Dict[str, Any]) -> None:
        """
        Validate rule criteria JSONB based on rule type.

        Each rule type has specific expected criteria fields.
        """
        if not isinstance(criteria, dict):
            raise ValueError("criteria must be a dictionary")

        # Validate based on rule type
        if rule_type == RuleType.MIN_FICO:
            if "min_score" not in criteria:
                raise ValueError("MIN_FICO requires 'min_score' in criteria")
            if not isinstance(criteria["min_score"], (int, float)):
                raise ValueError("min_score must be a number")

        elif rule_type == RuleType.MIN_PAYNET:
            if "min_score" not in criteria:
                raise ValueError("MIN_PAYNET requires 'min_score' in criteria")

        elif rule_type == RuleType.TIME_IN_BUSINESS:
            if "min_years" not in criteria:
                raise ValueError("TIME_IN_BUSINESS requires 'min_years' in criteria")

        elif rule_type in [RuleType.MIN_LOAN_AMOUNT, RuleType.MAX_LOAN_AMOUNT]:
            if "amount" not in criteria:
                raise ValueError(f"{rule_type.value} requires 'amount' in criteria")

        elif rule_type == RuleType.EQUIPMENT_AGE:
            if "max_age_years" not in criteria:
                raise ValueError("EQUIPMENT_AGE requires 'max_age_years' in criteria")

        elif rule_type in [RuleType.EXCLUDED_STATES, RuleType.ALLOWED_STATES]:
            if "states" not in criteria:
                raise ValueError(f"{rule_type.value} requires 'states' in criteria")
            if not isinstance(criteria["states"], list):
                raise ValueError("states must be a list")

        # Add more validations as needed for other rule types
