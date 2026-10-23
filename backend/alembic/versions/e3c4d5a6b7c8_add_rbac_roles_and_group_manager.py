"""add_rbac_roles_and_group_manager

Revision ID: e3c4d5a6b7c8
Revises: 217ab0e09fbb
Create Date: 2026-10-16 16:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e3c4d5a6b7c8'
down_revision: Union[str, Sequence[str], None] = '217ab0e09fbb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add canonical 4 roles to user_role_enum
    # In PostgreSQL, ALTER TYPE ... ADD VALUE cannot run inside transactional block in some versions,
    # so we execute using commit_block if needed, or direct execute with autocommit.
    connection = op.get_bind()
    for role_name in ['ADMIN', 'MANAGER', 'ACCOUNTANT', 'MEMBER']:
        connection.execute(sa.text(f"ALTER TYPE user_role_enum ADD VALUE IF NOT EXISTS '{role_name}'"))

    # 2. Add manager_id to chit_groups
    op.add_column('chit_groups', sa.Column('manager_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_chit_groups_manager_id',
        'chit_groups',
        'users',
        ['manager_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_chit_groups_manager_id', 'chit_groups', ['manager_id'])


def downgrade() -> None:
    op.drop_index('ix_chit_groups_manager_id', table_name='chit_groups')
    op.drop_constraint('fk_chit_groups_manager_id', 'chit_groups', type_='foreignkey')
    op.drop_column('chit_groups', 'manager_id')
