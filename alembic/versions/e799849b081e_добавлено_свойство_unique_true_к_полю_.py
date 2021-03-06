"""Добавлено свойство unique=True к полю email у модели User

Revision ID: e799849b081e
Revises: 8d80e417ede3
Create Date: 2021-05-04 20:48:54.641313

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e799849b081e'
down_revision = '8d80e417ede3'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint(None, 'users', ['email'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'users', type_='unique')
    # ### end Alembic commands ###
