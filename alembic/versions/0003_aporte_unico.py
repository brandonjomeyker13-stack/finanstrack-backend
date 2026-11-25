"""Un solo aporte automático del colchón por periodo.

Dos pantallas cargaban el periodo al mismo tiempo y cada una depositaba
el colchón. Aquí se juntan las filas repetidas del mismo periodo, sin
cambiar la suma, y no se permite crear otra. Al abrir la app, el periodo
actual vuelve a quedar en el porcentaje de ahora.
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_aporte_unico"
down_revision = "0002_google"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "movimientos_fondo" not in inspector.get_table_names():
        return
    filas = bind.execute(
        sa.text(
            """
            SELECT id, usuario_id, ciclo_inicio, monto
            FROM movimientos_fondo
            WHERE tipo = 'aporte_ciclo'
            ORDER BY usuario_id, ciclo_inicio, created_at, id
            """
        )
    ).fetchall()
    grupos: dict[tuple[str, str], list] = {}
    for fila in filas:
        grupos.setdefault((fila.usuario_id, str(fila.ciclo_inicio)), []).append(fila)
    for grupo in grupos.values():
        if len(grupo) < 2:
            continue
        total = sum(int(item.monto) for item in grupo)
        bind.execute(
            sa.text("UPDATE movimientos_fondo SET monto = :monto WHERE id = :id"),
            {"monto": total, "id": grupo[0].id},
        )
        for extra in grupo[1:]:
            bind.execute(
                sa.text("DELETE FROM movimientos_fondo WHERE id = :id"),
                {"id": extra.id},
            )
    indices = {indice["name"] for indice in inspector.get_indexes("movimientos_fondo")}
    if "uq_aporte_ciclo" in indices:
        return
    op.create_index(
        "uq_aporte_ciclo",
        "movimientos_fondo",
        ["usuario_id", "ciclo_inicio"],
        unique=True,
        sqlite_where=sa.text("tipo = 'aporte_ciclo'"),
        postgresql_where=sa.text("tipo = 'aporte_ciclo'"),
    )


def downgrade() -> None:
    op.drop_index("uq_aporte_ciclo", table_name="movimientos_fondo")
