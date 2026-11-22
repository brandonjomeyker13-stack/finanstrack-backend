"""Esquema inicial.

El dibujo de las tablas vive en app/models. Esta migración lo crea tal cual,
para que Render (alembic upgrade head) y una base nueva de Supabase queden
iguales. Los cambios de después van en migraciones nuevas, no editando esta.
"""

from alembic import op

from app.db.base import Base
import app.models  # noqa: F401

revision = "0001_esquema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
