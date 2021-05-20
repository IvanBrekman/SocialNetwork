"""Добавление поля is_read в модель Message

Revision ID: 8d80e417ede3
Revises: 01f25223ad1d
Create Date: 2021-04-26 19:48:31.756366

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8d80e417ede3'
down_revision = '01f25223ad1d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('messages', sa.Column('is_read', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('messages', 'is_read')
    # ### end Alembic commands ###
