"""Las cinco bolsas. Cuatro se gastan; el colchón solo se toca en un golpe."""

OBLIGATORIO = "obligatorio"
DEUDA_EXTRA = "deuda_extra"
VARIABLE = "variable"
GUSTOS = "gustos"
COLCHON = "colchon"

BOLSAS = (OBLIGATORIO, DEUDA_EXTRA, VARIABLE, GUSTOS, COLCHON)
GASTABLES = (OBLIGATORIO, DEUDA_EXTRA, VARIABLE, GUSTOS)

# Cuando las cuotas no caben en Cuentas, se achica en este orden.
# Día a día se toca de último: mercado y transporte.
ORDEN_RECORTE = (GUSTOS, DEUDA_EXTRA, COLCHON, VARIABLE)

NOMBRES = {
    OBLIGATORIO: "Cuentas",
    DEUDA_EXTRA: "Deudas",
    VARIABLE: "Día a día",
    GUSTOS: "Gustos",
    COLCHON: "Colchón",
}

DETALLES = {
    OBLIGATORIO: "Arriendo, servicios y la cuota de este periodo",
    DEUDA_EXTRA: "Abonos de más, para salir antes",
    VARIABLE: "Mercado, transporte, lo que cambia",
    GUSTOS: "Lo que te das, sin culpa hasta aquí",
    COLCHON: "No se gasta. Se guarda para un golpe",
}
