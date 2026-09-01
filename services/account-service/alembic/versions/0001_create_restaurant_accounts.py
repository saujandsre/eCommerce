"""Create restaurant accounts table."""
from alembic import op
import sqlalchemy as sa
revision="0001"
down_revision=None
branch_labels=None
depends_on=None
def upgrade():
    op.create_table("restaurant_accounts",sa.Column("restaurant_id",sa.Integer(),nullable=False),sa.Column("restaurant_name",sa.String(255),nullable=False),sa.Column("credit_limit_npr",sa.Numeric(14,2),nullable=False),sa.Column("available_credit_npr",sa.Numeric(14,2),nullable=False),sa.Column("reserved_credit_npr",sa.Numeric(14,2),nullable=False),sa.CheckConstraint("credit_limit_npr >= 0",name="ck_accounts_limit_nonnegative"),sa.CheckConstraint("available_credit_npr >= 0",name="ck_accounts_available_nonnegative"),sa.CheckConstraint("reserved_credit_npr >= 0",name="ck_accounts_reserved_nonnegative"),sa.CheckConstraint("available_credit_npr + reserved_credit_npr <= credit_limit_npr",name="ck_accounts_credit_within_limit"),sa.PrimaryKeyConstraint("restaurant_id"))
def downgrade(): op.drop_table("restaurant_accounts")
