from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")
PERCENT = Decimal("100")


def as_decimal(value: Decimal | int | str) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def money(value: Decimal | int | str) -> Decimal:
    return as_decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def line_amounts(
    quantity: Decimal, unit_price: Decimal, tax_rate: Decimal
) -> tuple[Decimal, Decimal, Decimal]:
    net = money(as_decimal(quantity) * as_decimal(unit_price))
    tax = money(net * as_decimal(tax_rate) / PERCENT)
    return net, tax, money(net + tax)
