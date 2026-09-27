"""Confine monetario: nessun float accettato dal ledger."""

from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation, localcontext
from functools import wraps

QUANTUM = Decimal("0.000001")
ZERO = Decimal("0.000000")


def money_context(function):
    """Contesto fisso anche se un chiamante modifica il contesto Decimal globale."""

    @wraps(function)
    def wrapped(*args, **kwargs):
        with localcontext() as ctx:
            ctx.prec = 50
            ctx.rounding = ROUND_HALF_EVEN
            return function(*args, **kwargs)

    return wrapped


def money(value: Decimal | str | int) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, Decimal | str | int):
        raise ValueError("Importo UM: usare Decimal, intero o stringa, mai float")
    try:
        with localcontext() as ctx:
            ctx.prec = 50
            result = Decimal(value)
            if not result.is_finite() or abs(result) >= Decimal("1e24"):
                raise ValueError("Importo UM non finito o fuori scala (< 1e24)")
            return result.quantize(QUANTUM, rounding=ROUND_HALF_EVEN)
    except InvalidOperation as exc:
        raise ValueError("Importo UM non valido") from exc


def positive_money(value: Decimal | str | int) -> Decimal:
    result = money(value)
    if result <= ZERO:
        raise ValueError("L'importo quantizzato deve essere positivo")
    return result


def weekly_rate(annual_rate: float) -> float:
    import math

    if not math.isfinite(annual_rate) or annual_rate <= -1:
        raise ValueError("Tasso annuo effettivo deve essere finito e > -1")
    return math.expm1(math.log1p(annual_rate) / 52)
