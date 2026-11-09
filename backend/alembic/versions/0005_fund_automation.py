"""fund automation

Revision ID: 0005
Revises: 0004
"""
import sqlalchemy as sa
from alembic import op


revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('entries', sa.Column('fund_id', sa.Uuid(), nullable=True))
    op.create_index(op.f('ix_entries_fund_id'), 'entries', ['fund_id'], unique=False)
    op.create_foreign_key('entries_fund_id_fkey', 'entries', 'funds', ['fund_id'], ['id'], ondelete='SET NULL')
    op.add_column('recurring', sa.Column('fund_id', sa.Uuid(), nullable=True))
    op.create_index(op.f('ix_recurring_fund_id'), 'recurring', ['fund_id'], unique=False)
    op.create_foreign_key('recurring_fund_id_fkey', 'recurring', 'funds', ['fund_id'], ['id'], ondelete='SET NULL')
    op.add_column('funds', sa.Column('monthly_amount', sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column('funds', sa.Column('monthly_day', sa.Integer(), server_default='1', nullable=False))
    op.add_column('funds', sa.Column('income_pct', sa.Numeric(precision=5, scale=2), nullable=True))
    op.add_column('funds', sa.Column('auto_start', sa.Date(), nullable=True))
    # Existing funds: automation (when switched on later) counts from the day the fund was created.
    op.execute("update funds set auto_start = created_at::date where auto_start is null")
    # Autogenerate does not emit CHECK constraints on existing tables: added by hand.
    op.create_check_constraint('entry_fund_personal', 'entries', "fund_id is null or scope = 'personal'")
    op.create_check_constraint('recurring_fund_personal', 'recurring', "fund_id is null or scope = 'personal'")
    op.create_check_constraint('fund_monthly_nonneg', 'funds', 'monthly_amount is null or monthly_amount >= 0')
    op.create_check_constraint('fund_monthly_day', 'funds', 'monthly_day between 1 and 28')
    op.create_check_constraint('fund_income_pct', 'funds', 'income_pct is null or (income_pct between 0 and 100)')


def downgrade() -> None:
    for name, table in (
        ('fund_income_pct', 'funds'), ('fund_monthly_day', 'funds'), ('fund_monthly_nonneg', 'funds'),
        ('recurring_fund_personal', 'recurring'), ('entry_fund_personal', 'entries'),
    ):
        op.drop_constraint(name, table, type_='check')
    op.drop_column('funds', 'auto_start')
    op.drop_column('funds', 'income_pct')
    op.drop_column('funds', 'monthly_day')
    op.drop_column('funds', 'monthly_amount')
    op.drop_constraint('recurring_fund_id_fkey', 'recurring', type_='foreignkey')
    op.drop_index(op.f('ix_recurring_fund_id'), table_name='recurring')
    op.drop_column('recurring', 'fund_id')
    op.drop_constraint('entries_fund_id_fkey', 'entries', type_='foreignkey')
    op.drop_index(op.f('ix_entries_fund_id'), table_name='entries')
    op.drop_column('entries', 'fund_id')
