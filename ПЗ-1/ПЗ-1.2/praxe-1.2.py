"""ПЗ1 (ч.2): арифметичні дії в двійковій, вісімковій і шістнадцятковій системах
Додавання, віднімання, множення, ділення - у стовпчик, з перевіркою в десятковій системі.
Віднімання в двійковій системі через додатковий код.
"""

DIGITS = "0123456789ABCDEF"


#допоміжні функції
def parse(s, base):
    s = s.strip().upper()
    if not s:
        raise ValueError("Порожнє число")
    for ch in s:
        d = DIGITS.find(ch)
        if d < 0 or d >= base:
            raise ValueError(f"Цифра '{ch}' недопустима для основи {base}")
    return s.lstrip("0") or "0"


def to_vec(s):
    """Цифри від молодшого розряду до старшого."""
    return [DIGITS.index(c) for c in reversed(s)]


def from_vec(v):
    v = v[:]
    while len(v) > 1 and v[-1] == 0:
        v.pop()
    return "".join(DIGITS[d] for d in reversed(v))


def to_base(n, base):
    if n == 0:
        return "0"
    res = ""
    while n > 0:
        res = DIGITS[n % base] + res
        n //= base
    return res


# алгоритми
def add_str(a, b, base, verbose=False):
    x, y = to_vec(a), to_vec(b)
    n = max(len(x), len(y))
    x += [0] * (n - len(x))
    y += [0] * (n - len(y))
    carry, res = 0, []
    for i in range(n):
        s = x[i] + y[i] + carry
        d, c = s % base, s // base
        if verbose:
            print(f"  розряд {i}: {DIGITS[x[i]]} + {DIGITS[y[i]]} + перенос {carry} = {s}(10) -> пишемо {DIGITS[d]}, перенос {c}")
        res.append(d)
        carry = c
    if carry:
        res.append(carry)
        if verbose:
            print(f"  розряд {n}: залишився перенос {carry}")
    return from_vec(res)


def sub_str(a, b, base, verbose=False):
    """a - b, обов'язково a >= b."""
    x, y = to_vec(a), to_vec(b)
    y += [0] * (len(x) - len(y))
    borrow, res = 0, []
    for i in range(len(x)):
        d = x[i] - y[i] - borrow
        nb = 0
        if d < 0:
            d += base
            nb = 1
        if verbose:
            note = f", позичаємо {base} зі старшого розряду" if nb else ""
            print(f"  розряд {i}: {DIGITS[x[i]]} - {DIGITS[y[i]]} - позика {borrow} -> {DIGITS[d]}{note}")
        res.append(d)
        borrow = nb
    return from_vec(res)


def mul_str(a, b, base, verbose=False):
    x = to_vec(a)
    total = "0"
    for i, m in enumerate(to_vec(b)):
        carry, part = 0, []
        for dgt in x:
            p = dgt * m + carry
            part.append(p % base)
            carry = p // base
        if carry:
            part.append(carry)
        p_str = from_vec(part)
        shifted = p_str + "0" * i if p_str != "0" else "0"
        if verbose:
            print(f"  цифра {DIGITS[m]} (розряд {i}): {a} * {DIGITS[m]} = {p_str}, зсув на {i} -> {shifted}")
        total = add_str(total, shifted, base)
    return total


def div_str(a, b, base, verbose=False):
    d = int(b, base)
    if d == 0:
        raise ZeroDivisionError("Ділення на нуль")
    rem, q = 0, []
    for ch in a:
        rem = rem * base + DIGITS.index(ch)
        qd = rem // d
        if verbose:
            print(f"  знесли {ch}: поточне ділене {to_base(rem, base)}, ділник {b} вміщується {DIGITS[qd]} р.")
        rem -= qd * d
        q.append(DIGITS[qd])
    return "".join(q).lstrip("0") or "0", to_base(rem, base)


# віднімання
def sub_twos_complement(a, b):
    bits = ((max(len(a), len(b)) + 1 + 7) // 8) * 8
    ma, mb = a.zfill(bits - 1), b.zfill(bits - 1)
    inv = "1" + "".join("1" if c == "0" else "0" for c in mb)
    add = bin(int(inv, 2) + 1)[2:].zfill(bits)

    print(f"\nРозрядна сітка n = {bits}")
    print(f"+{a}: прямий код   0.{ma}")
    print(f"-{b}: прямий код   1.{mb}")
    print(f"-{b}: зворотний    {inv[0]}.{inv[1:]}")
    print(f"-{b}: додатковий   {add[0]}.{add[1:]}")

    total = int("0" + ma, 2) + int(add, 2)
    full = bin(total)[2:].zfill(bits + 1)
    carry, res = full[0], full[1:]
    print(f"\n  0.{ma}\n+ {add[0]}.{add[1:]}\n= {carry}{res[0]}.{res[1:]}")
    if carry == "1":
        print("Одиниця переносу виходить за розрядну сітку.")

    if res[0] == "0":
        value = int(res, 2)
        print(f"Результат (знак 0, додатний): {res[0]}.{res[1:]} = {bin(value)[2:]}(2) = {value}(10)")
    else:
        value = -(2 ** bits - int(res, 2))
        print(f"Результат (знак 1, від'ємний, у додатковому коді): {res[0]}.{res[1:]} = {value}(10)")
    expected = int(a, 2) - int(b, 2)
    print(f"Перевірка: {int(a, 2)} - {int(b, 2)} = {expected} -> {'вірно' if expected == value else 'ПОМИЛКА'}")


OPS = {"1": "+", "2": "-", "3": "*", "4": ":"}


def run_operation(op):
    base = int(input("Основа системи (2/8/16): "))
    if base not in (2, 8, 16):
        raise ValueError("Основа має бути 2, 8 або 16")
    a = parse(input("Перше число: "), base)
    b = parse(input("Друге число: "), base)
    ia, ib = int(a, base), int(b, base)
    print(f"\n{a}({base}) {op} {b}({base})")

    if op == "+":
        res = add_str(a, b, base, True)
        expected = ia + ib
    elif op == "-":
        if ia >= ib:
            res = sub_str(a, b, base, True)
            expected = ia - ib
        else:
            print("  (перше число менше за друге, рахуємо b - a і ставимо мінус)")
            res = "-" + sub_str(b, a, base, True)
            expected = ia - ib
    elif op == "*":
        res = mul_str(a, b, base, True)
        expected = ia * ib
    else:
        q, r = div_str(a, b, base, True)
        print(f"\nРезультат: частка {q}({base}), остача {r}({base})")
        qi, ri = int(q, base), int(r, base)
        print(f"Перевірка в десятковій: {ia} : {ib} = {qi}, остача {ri}; {qi}*{ib} + {ri} = {qi * ib + ri} -> "
              f"{'вірно' if qi * ib + ri == ia else 'ПОМИЛКА'}")
        return

    print(f"\nРезультат: {res}({base})")
    got = int(res, base)
    print(f"Перевірка в десятковій: {ia} {op} {ib} = {expected}; {res}({base}) = {got} -> "
          f"{'вірно' if got == expected else 'ПОМИЛКА'}")


def main():
    while True:
        print("\n=== ПЗ1 ч.2: арифметика в системах числення ===")
        print("1 - додавання")
        print("2 - віднімання (стовпчиком)")
        print("3 - множення")
        print("4 - ділення")
        print("5 - віднімання через додатковий код (двійкова)")
        print("0 - вихід")
        choice = input("> ").strip()
        try:
            if choice in OPS:
                run_operation(OPS[choice])
            elif choice == "5":
                a = parse(input("Зменшуване (двійкове): "), 2)
                b = parse(input("Від'ємник (двійкове): "), 2)
                sub_twos_complement(a, b)
            elif choice == "0":
                break
        except Exception as e:
            print("Помилка:", e)


if __name__ == "__main__":
    main()
