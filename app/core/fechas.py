from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.core.config import settings


def hoy() -> date:
    """El día del usuario, no el del servidor.

    Render corre en UTC. En Colombia, entre las 7 pm y la medianoche el
    día UTC ya cambió y el periodo de pago todavía no.
    """
    return datetime.now(ZoneInfo(settings.ZONA_HORARIA)).date()
