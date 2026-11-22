"""Cuenta de Google en usuarios.

Las bases nuevas ya traen la columna, porque 0001 crea el modelo actual.
Esta migración la agrega solo si falta, para una base que se creó antes.
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_google"
down_revision = "0001_esquema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "usuarios" not in inspector.get_table_names():
        return
    columnas = {columna["name"] for columna in inspector.get_columns("usuarios")}
    if "google_sub" in columnas:
        return
    op.add_column("usuarios", sa.Column("google_sub", sa.String(length=255), nullable=True))
    op.create_index("ix_usuarios_google_sub", "usuarios", ["google_sub"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "usuarios" not in inspector.get_table_names():
        return
    columnas = {columna["name"] for columna in inspector.get_columns("usuarios")}
    if "google_sub" not in columnas:
        return
    for indice in inspector.get_indexes("usuarios"):
        if indice.get("column_names") == ["google_sub"] and indice.get("name"):
            op.drop_index(indice["name"], table_name="usuarios")
    for restriccion in inspector.get_unique_constraints("usuarios"):
        if restriccion.get("column_names") == ["google_sub"] and restriccion.get("name"):
            op.drop_constraint(restriccion["name"], "usuarios", type_="unique")
    op.drop_column("usuarios", "google_sub")
