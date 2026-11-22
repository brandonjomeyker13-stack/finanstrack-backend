"""Pesos enteros. En Colombia no hay centavos, y las bolsas tienen que sumar el pago."""


def repartir(total: int, porcentajes: dict[str, int]) -> dict[str, int]:
    """Reparte `total` según porcentajes que deberían sumar 100.

    Método del resto mayor: la parte entera va a cada bolsa y los pesos
    que sobran van a las fracciones más grandes. La suma es exactamente
    `total`. Un peso no se pierde ni se inventa.
    """
    if not porcentajes:
        return {}
    if total <= 0:
        return {clave: 0 for clave in porcentajes}

    suma = sum(porcentajes.values())
    if suma <= 0:
        return {clave: 0 for clave in porcentajes}

    resultado: dict[str, int] = {}
    fracciones: dict[str, int] = {}
    asignado = 0
    for clave, porcentaje in porcentajes.items():
        piso = (total * porcentaje) // suma
        resultado[clave] = piso
        fracciones[clave] = (total * porcentaje) % suma
        asignado += piso

    sobrante = total - asignado
    orden = sorted(fracciones, key=lambda clave: fracciones[clave], reverse=True)
    for i in range(sobrante):
        resultado[orden[i % len(orden)]] += 1
    return resultado


def recortar(
    bolsas: dict[str, int],
    a_restar: int,
    orden: tuple[str, ...],
) -> tuple[int, list[tuple[str, int]]]:
    """Saca `a_restar` siguiendo `orden`, sin dejar una bolsa en negativo.

    Devuelve lo que no se alcanzó a cubrir y cada recorte, para poder
    decirlo en vez de esconder un negativo.
    """
    pendiente = max(0, a_restar)
    hechos: list[tuple[str, int]] = []
    if pendiente == 0:
        return 0, hechos

    for bolsa in orden:
        if pendiente <= 0:
            break
        saldo = bolsas.get(bolsa, 0)
        if saldo <= 0:
            continue
        recorte = saldo if saldo < pendiente else pendiente
        bolsas[bolsa] = saldo - recorte
        pendiente -= recorte
        hechos.append((bolsa, recorte))
    return pendiente, hechos


def pesos(valor: int) -> str:
    """$1.250.000 — el punto de mil, el signo adelante."""
    numero = abs(int(valor))
    texto = f"{numero:,}".replace(",", ".")
    return f"-${texto}" if valor < 0 else f"${texto}"


def por_dia(disponible: int, dias: int) -> int:
    if disponible <= 0 or dias <= 0:
        return 0
    return (disponible + dias // 2) // dias
