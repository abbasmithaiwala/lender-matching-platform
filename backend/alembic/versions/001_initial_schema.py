"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-01-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ENUM types
    op.execute("CREATE TYPE legal_structure AS ENUM ('LLC', 'Corporation', 'S-Corp', 'C-Corp', 'Partnership', 'Sole Proprietorship', 'Non-Profit', 'Other')")
    op.execute("CREATE TYPE equipment_condition AS ENUM ('New', 'Used', 'Refurbished', 'Certified Pre-Owned')")
    op.execute("CREATE TYPE application_status AS ENUM ('Draft', 'Submitted', 'Under Review', 'In Underwriting', 'Approved', 'Rejected', 'Withdrawn', 'Expired')")
    op.execute("CREATE TYPE underwriting_status AS ENUM ('Pending', 'In Progress', 'Completed', 'Failed', 'Cancelled')")
    op.execute("""
        CREATE TYPE rule_type AS ENUM (
            'min_fico', 'min_paynet', 'credit_tier', 'max_credit_utilization',
            'time_in_business', 'min_revenue', 'legal_structure',
            'min_loan_amount', 'max_loan_amount', 'min_loan_term', 'max_loan_term', 'min_down_payment', 'max_ltv',
            'equipment_type', 'equipment_age', 'equipment_condition',
            'excluded_states', 'excluded_industries', 'allowed_states', 'allowed_industries',
            'bankruptcy_history', 'homeowner_required', 'us_citizen_required',
            'custom'
        )
    """)

    # Create businesses table
    op.create_table(
        'businesses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('legal_name', sa.String(length=255), nullable=False),
        sa.Column('dba_name', sa.String(length=255), nullable=True),
        sa.Column('industry', sa.String(length=100), nullable=False),
        sa.Column('legal_structure', postgresql.ENUM(name='legal_structure', create_type=False), nullable=False),
        sa.Column('established_date', sa.Date(), nullable=False),
        sa.Column('annual_revenue', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('address_line1', sa.String(length=255), nullable=False),
        sa.Column('address_line2', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=2), nullable=False),
        sa.Column('zip_code', sa.String(length=10), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
    )

    # Create personal_guarantors table
    op.create_table(
        'personal_guarantors',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('fico_score', sa.Integer(), nullable=True),
        sa.Column('paynet_score', sa.Integer(), nullable=True),
        sa.Column('bankruptcy_history', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('bankruptcy_discharge_date', sa.Date(), nullable=True),
        sa.Column('credit_utilization_percentage', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('revolving_credit_available', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('is_homeowner', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_us_citizen', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('address_line1', sa.String(length=255), nullable=True),
        sa.Column('address_line2', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=2), nullable=True),
        sa.Column('zip_code', sa.String(length=10), nullable=True),
    )

    # Create equipment table
    op.create_table(
        'equipment',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('equipment_type', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('manufacturer', sa.String(length=100), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('year_manufactured', sa.Integer(), nullable=True),
        sa.Column('condition', postgresql.ENUM(name='equipment_condition', create_type=False), nullable=False),
        sa.Column('cost', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('serial_number', sa.String(length=100), nullable=True),
    )

    # Create loan_applications table
    op.create_table(
        'loan_applications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('application_number', sa.String(length=50), nullable=False, unique=True),
        sa.Column('status', postgresql.ENUM(name='application_status', create_type=False), nullable=False, server_default='Draft'),
        sa.Column('business_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('guarantor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('equipment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('requested_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('requested_term_months', sa.Integer(), nullable=False),
        sa.Column('down_payment_percentage', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('down_payment_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('purpose', sa.Text(), nullable=True),
        sa.Column('comparable_debt_payments', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['guarantor_id'], ['personal_guarantors.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['equipment_id'], ['equipment.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_loan_applications_application_number', 'loan_applications', ['application_number'])
    op.create_index('ix_loan_applications_status', 'loan_applications', ['status'])

    # Create lenders table
    op.create_table(
        'lenders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('min_loan_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('max_loan_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('excluded_states', postgresql.ARRAY(sa.String(length=2)), nullable=True),
        sa.Column('excluded_industries', postgresql.ARRAY(sa.String(length=100)), nullable=True),
    )
    op.create_index('ix_lenders_name', 'lenders', ['name'])
    op.create_index('ix_lenders_active', 'lenders', ['active'])

    # Create policy_programs table
    op.create_table(
        'policy_programs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('lender_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('program_name', sa.String(length=255), nullable=False),
        sa.Column('program_code', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('credit_tier', sa.String(length=50), nullable=True),
        sa.Column('eligibility_conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('rate_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('min_fit_score', sa.Numeric(precision=5, scale=2), nullable=True, server_default='0.00'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.ForeignKeyConstraint(['lender_id'], ['lenders.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_policy_programs_lender_id', 'policy_programs', ['lender_id'])

    # Create policy_rules table
    op.create_table(
        'policy_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('program_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rule_type', postgresql.ENUM(name='rule_type', create_type=False), nullable=False),
        sa.Column('rule_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('criteria', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('weight', sa.Numeric(precision=5, scale=2), nullable=False, server_default='1.00'),
        sa.Column('is_mandatory', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.ForeignKeyConstraint(['program_id'], ['policy_programs.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_policy_rules_program_id', 'policy_rules', ['program_id'])
    op.create_index('ix_policy_rules_rule_type', 'policy_rules', ['rule_type'])

    # Create underwriting_runs table
    op.create_table(
        'underwriting_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', postgresql.ENUM(name='underwriting_status', create_type=False), nullable=False, server_default='Pending'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_lenders_evaluated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_programs_evaluated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('matched_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rejected_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['application_id'], ['loan_applications.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_underwriting_runs_application_id', 'underwriting_runs', ['application_id'])
    op.create_index('ix_underwriting_runs_status', 'underwriting_runs', ['status'])

    # Create match_results table
    op.create_table(
        'match_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('underwriting_run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lender_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('program_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_eligible', sa.Boolean(), nullable=False),
        sa.Column('fit_score', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.00'),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('rejection_tier', sa.Integer(), nullable=True),
        sa.Column('estimated_rate', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('estimated_monthly_payment', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('approval_probability', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('total_rules_evaluated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rules_passed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rules_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('mandatory_rules_passed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['underwriting_run_id'], ['underwriting_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lender_id'], ['lenders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['program_id'], ['policy_programs.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_match_results_underwriting_run_id', 'match_results', ['underwriting_run_id'])
    op.create_index('ix_match_results_lender_id', 'match_results', ['lender_id'])
    op.create_index('ix_match_results_program_id', 'match_results', ['program_id'])
    op.create_index('ix_match_results_is_eligible', 'match_results', ['is_eligible'])
    op.create_index('ix_match_results_fit_score', 'match_results', ['fit_score'])

    # Create rule_evaluations table
    op.create_table(
        'rule_evaluations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('match_result_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rule_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('rule_name', sa.String(length=255), nullable=False),
        sa.Column('rule_type', sa.String(length=100), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('score', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.00'),
        sa.Column('weight', sa.Numeric(precision=5, scale=2), nullable=False, server_default='1.00'),
        sa.Column('is_mandatory', sa.Boolean(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['match_result_id'], ['match_results.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rule_id'], ['policy_rules.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_rule_evaluations_match_result_id', 'rule_evaluations', ['match_result_id'])
    op.create_index('ix_rule_evaluations_rule_id', 'rule_evaluations', ['rule_id'])
    op.create_index('ix_rule_evaluations_rule_type', 'rule_evaluations', ['rule_type'])
    op.create_index('ix_rule_evaluations_passed', 'rule_evaluations', ['passed'])


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_index('ix_rule_evaluations_passed', table_name='rule_evaluations')
    op.drop_index('ix_rule_evaluations_rule_type', table_name='rule_evaluations')
    op.drop_index('ix_rule_evaluations_rule_id', table_name='rule_evaluations')
    op.drop_index('ix_rule_evaluations_match_result_id', table_name='rule_evaluations')
    op.drop_table('rule_evaluations')

    op.drop_index('ix_match_results_fit_score', table_name='match_results')
    op.drop_index('ix_match_results_is_eligible', table_name='match_results')
    op.drop_index('ix_match_results_program_id', table_name='match_results')
    op.drop_index('ix_match_results_lender_id', table_name='match_results')
    op.drop_index('ix_match_results_underwriting_run_id', table_name='match_results')
    op.drop_table('match_results')

    op.drop_index('ix_underwriting_runs_status', table_name='underwriting_runs')
    op.drop_index('ix_underwriting_runs_application_id', table_name='underwriting_runs')
    op.drop_table('underwriting_runs')

    op.drop_index('ix_policy_rules_rule_type', table_name='policy_rules')
    op.drop_index('ix_policy_rules_program_id', table_name='policy_rules')
    op.drop_table('policy_rules')

    op.drop_index('ix_policy_programs_lender_id', table_name='policy_programs')
    op.drop_table('policy_programs')

    op.drop_index('ix_lenders_active', table_name='lenders')
    op.drop_index('ix_lenders_name', table_name='lenders')
    op.drop_table('lenders')

    op.drop_index('ix_loan_applications_status', table_name='loan_applications')
    op.drop_index('ix_loan_applications_application_number', table_name='loan_applications')
    op.drop_table('loan_applications')

    op.drop_table('equipment')
    op.drop_table('personal_guarantors')
    op.drop_table('businesses')

    # Drop ENUM types
    op.execute('DROP TYPE rule_type')
    op.execute('DROP TYPE underwriting_status')
    op.execute('DROP TYPE application_status')
    op.execute('DROP TYPE equipment_condition')
    op.execute('DROP TYPE legal_structure')
