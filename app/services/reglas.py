from app.domain.ciclo import ReglasPago
from app.models import Perfil


def reglas_de(perfil: Perfil) -> ReglasPago:
    return ReglasPago(
        frecuencia=perfil.frecuencia,
        dia_de_corte=perfil.dia_de_corte,
        segundo_dia_de_corte=perfil.segundo_dia_de_corte,
        ancla_de_pago=perfil.ancla_de_pago,
        pct_obligatorio=perfil.pct_obligatorio,
        pct_deuda_extra=perfil.pct_deuda_extra,
        pct_variable=perfil.pct_variable,
        pct_gustos=perfil.pct_gustos,
        pct_colchon=perfil.pct_colchon,
    )
