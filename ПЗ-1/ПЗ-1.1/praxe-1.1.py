"""ПЗ1 (ч.1): переведення між системами числення + прямий/зворотний/додатковий код"""
from decimal import Decimal

DIGITS = "0123456789ABCDEF"


def int_to_base(n, b, verbose=False):
    """Метод ділення (ціла частина)."""
    if n == 0:
        return "0"
    res, q = "", n
    while q > 0:
        r = q % b
        if verbose:
            print(f"  {q} : {b} = {q // b}, залишок {r} ({DIGITS[r]})")
        res = DIGITS[r] + res
        q //= b
    return res


def frac_to_base(f, b, max_digits=16, verbose=False):
    """Метод множення (дробова частина)."""
    res = ""
    for _ in range(max_digits):
        if f == 0:
            break
        p = f * b
        d = int(p)
        if verbose:
            print(f"  {f} * {b} = {p} -> {DIGITS[d]}")
        res += DIGITS[d]
        f = p - d
    return res


def to_decimal(s, b, verbose=False):
    """Будь-яка система -> десяткова (формула полінома)."""
    s = s.replace(",", ".").upper()
    int_part, _, frac_part = s.partition(".")
    result = Decimal(0)
    terms = []
    for i, ch in enumerate(int_part):
        d = DIGITS.find(ch)
        if d < 0 or d >= b:
            raise ValueError(f"Цифра '{ch}' недопустима для основи {b}")
        p = len(int_part) - 1 - i
        result += d * Decimal(b) ** p
        terms.append(f"{d}*{b}^{p}")
    for k, ch in enumerate(frac_part, 1):
        d = DIGITS.find(ch)
        if d < 0 or d >= b:
            raise ValueError(f"Цифра '{ch}' недопустима для основи {b}")
        result += d * Decimal(b) ** -k
        terms.append(f"{d}*{b}^-{k}")
    if verbose:
        print("  " + " + ".join(terms) + f" = {fmt(result)}")
    return result


def fmt(x):
    return format(x.normalize(), "f")


def convert(num, src, dst):
    dec = to_decimal(num, src, verbose=(src != 10))
    ip = int(dec)
    fp = dec - ip
    print(f"\nДесяткове значення: {fmt(dec)}")

    if dst == 10:
        res = fmt(dec)
    else:
        print("Ціла частина (метод ділення):")
        res = int_to_base(ip, dst, verbose=True)
        if fp > 0:
            print("Дробова частина (метод множення):")
            res += "." + frac_to_base(fp, dst, verbose=True)

    print(f"\nРезультат: {num}({src}) = {res}({dst})")
    back = to_decimal(res, dst)
    status = "збігається" if back == dec else "не збігається (дробова частина обрізана)"
    print(f"Перевірка: {res}({dst}) -> {fmt(back)}(10) - {status}")


def codes(n):
    """Прямий, зворотний, додатковий коди числа -n (сітка кратна 8)."""
    mag = int_to_base(n, 2)
    bits = ((len(mag) + 1 + 7) // 8) * 8
    m = mag.zfill(bits - 1)

    inv = "1" + "".join("1" if c == "0" else "0" for c in m)
    add = bin(int(inv, 2) + 1)[2:].zfill(bits)

    print(f"\n{n}(10) = {mag}(2), розрядна сітка n = {bits}")
    print(f"+{n} (прямий = зворотний = додатковий): 0.{m}")
    print(f"-{n} прямий:     1.{m}")
    print(f"-{n} зворотний:  {inv[0]}.{inv[1:]}")
    print(f"-{n} додатковий: {add[0]}.{add[1:]}")

    total = int(add, 2) + n
    ok = "одиниця переносу виходить за сітку, залишається 0 - вірно" if total == 2 ** bits else "помилка"
    print(f"\nПеревірка: {n} + (-{n}) = {bin(total)[2:]}(2); {ok}")


def main():
    while True:
        print("\n=== ПЗ1: системи числення ===")
        print("1 - переведення між системами (2/8/10/16)")
        print("2 - прямий, зворотний, додатковий коди")
        print("0 - вихід")
        choice = input("> ").strip()
        try:
            if choice == "1":
                num = input("Число: ").strip()
                src = int(input("Основа вихідної системи (2/8/10/16): "))
                dst = int(input("Основа цільової системи (2/8/10/16): "))
                convert(num, src, dst)
            elif choice == "2":
                codes(int(input("Додатне десяткове число n (код буде для -n): ")))
            elif choice == "0":
                break
        except Exception as e:
            print("Помилка:", e)


if __name__ == "__main__":
    main()
