"""
LimitApp Math Engine - SymPy based Limit Calculation & Step Analysis
Creator: Нарницкий Роман (Syrok)
Enhanced with full LaTeX parsing, extended calculus functions, smart bracket & power normalizer.
"""

import math
import re
from typing import Dict, Any, List, Optional
import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)

TRANSFORMS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)

LOCAL_MATH_DICT = {
    # Constants
    "oo": sp.oo,
    "inf": sp.oo,
    "infinity": sp.oo,
    "pi": sp.pi,
    "PI": sp.pi,
    "e": sp.E,
    "E": sp.E,
    "gamma": sp.EulerGamma,
    "golden_ratio": sp.GoldenRatio,
    # Roots & Power
    "sqrt": sp.sqrt,
    "cbrt": sp.cbrt,
    "root": sp.root,
    # Trigonometric
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
    "tg": sp.tan,
    "cot": sp.cot,
    "ctg": sp.cot,
    "sec": sp.sec,
    "csc": sp.csc,
    "sinc": sp.sinc,
    # Inverse Trigonometric
    "asin": sp.asin,
    "arcsin": sp.asin,
    "acos": sp.acos,
    "arccos": sp.acos,
    "atan": sp.atan,
    "arctg": sp.atan,
    "arctan": sp.atan,
    "acot": sp.acot,
    "arcctg": sp.acot,
    "arccot": sp.acot,
    # Hyperbolic
    "sinh": sp.sinh,
    "sh": sp.sinh,
    "cosh": sp.cosh,
    "ch": sp.cosh,
    "tanh": sp.tanh,
    "th": sp.tanh,
    "coth": sp.coth,
    "cth": sp.coth,
    "asinh": sp.asinh,
    "acosh": sp.acosh,
    "atanh": sp.atanh,
    "acoth": sp.acoth,
    # Exponential & Logarithmic
    "ln": sp.log,
    "log": sp.log,
    "log10": lambda x: sp.log(x, 10),
    "log2": lambda x: sp.log(x, 2),
    "lg": lambda x: sp.log(x, 10),
    "exp": sp.exp,
    # Special & Discrete
    "abs": sp.Abs,
    "Abs": sp.Abs,
    "sign": sp.sign,
    "sgn": sp.sign,
    "factorial": sp.factorial,
    "gamma_fn": sp.gamma,
    "binomial": sp.binomial,
    "floor": sp.floor,
    "ceil": sp.ceiling,
}


def clean_latex(s: str) -> str:
    """Converts LaTeX limit & function syntax into readable math expressions."""
    if not s or "\\" not in s:
        return s
    # Clean formatting
    s = s.replace(r"\left", "").replace(r"\right", "")
    s = s.replace(r"\cdot", "*").replace(r"\times", "*")
    s = s.replace(r"\infty", "oo").replace(r"\pi", "pi")

    # Replace nested \frac{a}{b} -> ((a)/(b))
    while r"\frac" in s:
        s_new = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"((\1)/(\2))", s)
        if s_new == s:
            break
        s = s_new

    # \sqrt[n]{x} -> root(x, n)
    s = re.sub(r"\\sqrt\[([^\]]+)\]\{([^{}]+)\}", r"root(\2, \1)", s)
    # \sqrt{x} -> sqrt(x)
    s = re.sub(r"\\sqrt\{([^{}]+)\}", r"sqrt(\1)", s)

    # Standard LaTeX function names without backslash
    s = re.sub(
        r"\\(sin|cos|tan|cot|sec|csc|asin|acos|atan|acot|sinh|cosh|tanh|coth|ln|log|exp|arcsin|arccos|arctan|arccot)",
        r"\1",
        s,
    )
    return s


def fix_trig_powers(s: str) -> str:
    """
    Transforms notation like sin^2(x) -> (sin(x))^2 and cos^3 x -> (cos(x))^3.
    """
    funcs = (
        r"sin|cos|tan|tg|cot|ctg|sec|csc|asin|arcsin|acos|arccos|atan|arctg|"
        r"acot|arcctg|sinh|sh|cosh|ch|tanh|th|coth|cth|ln|lg|log|exp"
    )
    pattern = rf"\b({funcs})\^(\d+)\s*(\([^\)]+\)|[a-zA-Z0-9]+)"

    def repl(m):
        fn = m.group(1)
        p = m.group(2)
        arg = m.group(3)
        if not arg.startswith("("):
            arg = f"({arg})"
        return f"({fn}{arg})^{p}"

    return re.sub(pattern, repl, s)


def clean_input(expr_str: str) -> str:
    """Preprocesses user input string into standard SymPy syntax."""
    if not expr_str:
        return ""
    s = expr_str.strip()

    # 1. LaTeX cleanup
    s = clean_latex(s)

    # 2. Dashes and Unicode symbols
    s = s.replace("—", "-").replace("–", "-").replace("−", "-")
    s = s.replace("×", "*").replace("·", "*").replace("÷", "/")
    s = s.replace("√", "sqrt")
    s = s.replace("π", "pi")
    s = s.replace("∞", "oo")

    # 3. Square brackets and curly braces -> parentheses
    s = s.replace("[", "(").replace("]", ")")
    s = s.replace("{", "(").replace("}", ")")

    # 4. Absolute values: |expr| -> abs(expr)
    s = re.sub(r"\|([^|]+)\|", r"abs(\1)", s)

    # 5. Decimal comma -> dot: e.g. 0,5 -> 0.5
    s = re.sub(r"(?<=\d),(?=\d)", ".", s)

    # 6. Russian mathematical notation
    s = re.sub(r"\btg\(", "tan(", s)
    s = re.sub(r"\bctg\(", "cot(", s)
    s = re.sub(r"\barctg\(", "atan(", s)
    s = re.sub(r"\barcctg\(", "acot(", s)
    s = re.sub(r"\barccot\(", "acot(", s)
    s = re.sub(r"\bsh\(", "sinh(", s)
    s = re.sub(r"\bch\(", "cosh(", s)
    s = re.sub(r"\bth\(", "tanh(", s)
    s = re.sub(r"\bcth\(", "coth(", s)
    s = re.sub(r"\blg\(", "log10(", s)

    # 7. Trigonometric powers: sin^2(x) -> (sin(x))^2
    s = fix_trig_powers(s)

    # 8. Euler power: e^x or e^(...)
    s = re.sub(r"\be\^(\([^\)]+\)|[a-zA-Z0-9]+)", r"exp(\1)", s)

    # 9. Factorial notation: n! or (n+1)!
    s = re.sub(r"(\([^\)]+\)|[a-zA-Z0-9]+)!", r"factorial(\1)", s)

    return s


def parse_full_limit(text: str) -> Optional[Dict[str, str]]:
    """
    Detects if the user pasted a complete limit notation like:
    - lim (x -> 0) sin(x)/x
    - lim x->0+ 1/x
    - \\lim_{x \\to 0} \\frac{\\sin x}{x}
    - lim_{n -> oo} (1+1/n)^n
    Returns dict with expr, var, point, direction, or None.
    """
    if not text:
        return None
    s = text.strip()
    m = re.search(
        r"\\?lim(?:_\{|\s*\(\s*|\s+)?([a-zA-Z])\s*(?:\\to|->|→)\s*([^)}\]\s]+(?:\s*[\+\-])?)(?:\}|\)|\s*\])?\s*[:\=]?\s*(.+)",
        s,
        re.IGNORECASE,
    )
    if not m:
        return None

    var = m.group(1).strip()
    raw_pt = m.group(2).strip()
    expr = m.group(3).strip()

    if expr.startswith("}") or expr.startswith(")"):
        expr = expr[1:].strip()
    if (expr.startswith("(") and expr.endswith(")")) or (expr.startswith("[") and expr.endswith("]")):
        expr = expr[1:-1].strip()

    direction = "+-"
    if raw_pt.endswith("+") or raw_pt.endswith("^+"):
        direction = "+"
        point = raw_pt.rstrip("^+")
    elif raw_pt.endswith("-") or raw_pt.endswith("^-"):
        direction = "-"
        point = raw_pt.rstrip("^-")
    else:
        point = raw_pt

    return {
        "expr": expr,
        "var": var,
        "point": point,
        "direction": direction,
    }


def parse_math(expr_str: str, var_symbol: sp.Symbol) -> sp.Expr:
    """Safely parses mathematical expression."""
    cleaned = clean_input(expr_str)
    local_dict = dict(LOCAL_MATH_DICT)
    local_dict[var_symbol.name] = var_symbol
    return parse_expr(cleaned, local_dict=local_dict, transformations=TRANSFORMS)


def format_sym(val: Any) -> str:
    """Formats a SymPy value nicely into unicode mathematical text."""
    if val == sp.oo or str(val) == "oo":
        return "+∞"
    if val == -sp.oo or str(val) == "-oo":
        return "-∞"
    if val == sp.zoo or str(val) == "zoo":
        return "∞ (комплексная бесконечность)"
    if val == sp.nan:
        return "Не существует (не определен)"
    if val == sp.E:
        return "e"
    if val == sp.pi:
        return "π"

    s = str(val)
    s = s.replace("**", "^").replace("*", "·")
    s = s.replace("pi", "π").replace("oo", "∞")
    s = s.replace("zoo", "∞")
    return s


def detect_indeterminacy(expr: sp.Expr, var: sp.Symbol, point: sp.Expr) -> Optional[str]:
    """Detects standard calculus indeterminate forms."""
    try:
        # Check fraction: 0/0 or oo/oo
        num, den = sp.fraction(expr)
        if den != 1:
            try:
                num_lim = sp.limit(num, var, point)
                den_lim = sp.limit(den, var, point)
                if num_lim == 0 and den_lim == 0:
                    return "[0 / 0]"
                if abs(num_lim) == sp.oo and abs(den_lim) == sp.oo:
                    return "[∞ / ∞]"
            except Exception:
                pass

        # Check power: 1^oo, 0^0, oo^0
        if expr.is_Pow:
            base, exp = expr.as_base_exp()
            try:
                base_lim = sp.limit(base, var, point)
                exp_lim = sp.limit(exp, var, point)
                if base_lim == 1 and abs(exp_lim) == sp.oo:
                    return "[1^∞]"
                if base_lim == 0 and exp_lim == 0:
                    return "[0^0]"
                if abs(base_lim) == sp.oo and exp_lim == 0:
                    return "[∞^0]"
            except Exception:
                pass

        # Check difference: oo - oo
        if expr.is_Add:
            args = expr.args
            has_pos_oo = False
            has_neg_oo = False
            for arg in args:
                try:
                    arg_lim = sp.limit(arg, var, point)
                    if arg_lim == sp.oo:
                        has_pos_oo = True
                    elif arg_lim == -sp.oo:
                        has_neg_oo = True
                except Exception:
                    pass
            if has_pos_oo and has_neg_oo:
                return "[∞ - ∞]"

        # Check product: 0 * oo
        if expr.is_Mul:
            args = expr.args
            has_zero = False
            has_oo = False
            for arg in args:
                try:
                    arg_lim = sp.limit(arg, var, point)
                    if arg_lim == 0:
                        has_zero = True
                    elif abs(arg_lim) == sp.oo:
                        has_oo = True
                except Exception:
                    pass
            if has_zero and has_oo:
                return "[0 · ∞]"

    except Exception:
        pass
    return None


def generate_steps(
    expr: sp.Expr,
    var: sp.Symbol,
    point: sp.Expr,
    direction: str,
    result: Any,
    indet: Optional[str],
) -> List[Dict[str, str]]:
    """Generates educational step-by-step explanations."""
    steps = []

    # Step 1: Direct substitution
    point_str = format_sym(point)
    steps.append({
        "title": "Шаг 1. Анализ поведения при подстановке",
        "desc": f"Исследуем значение функции при стремлении переменной {var.name} к точке {point_str}.",
    })

    if indet:
        steps.append({
            "title": f"Шаг 2. Обнаружение неопределенности {indet}",
            "desc": f"Прямая подстановка приводит к неопределенности вида {indet}. Требуется аналитическое раскрытие предела.",
        })

        # Step 3: Resolution method analysis
        num, den = sp.fraction(expr)
        if den != 1 and indet in ("[0 / 0]", "[∞ / ∞]"):
            try:
                num_diff = sp.diff(num, var)
                den_diff = sp.diff(den, var)
                steps.append({
                    "title": "Шаг 3. Раскрытие по Правилу Лопиталя",
                    "desc": (
                        f"Поскольку неопределенность {indet}, дифференцируем числитель и знаменатель:\n"
                        f"• Производная числителя ({num})' = {format_sym(num_diff)}\n"
                        f"• Производная знаменателя ({den})' = {format_sym(den_diff)}\n"
                        f"• Предел отношения производных равен: {format_sym(result)}"
                    ),
                })
            except Exception:
                pass

        elif indet == "[1^∞]":
            steps.append({
                "title": "Шаг 3. Сведение ко второму замечательному пределу",
                "desc": (
                    "Для раскрытия неопределенности [1^∞] применяется формула:\n"
                    "lim [u(x)]^v(x) = exp( lim [u(x) - 1] · v(x) )\n"
                    f"Результат вычисления экспоненты дает: {format_sym(result)}"
                ),
            })

        # Taylor expansion if near finite point
        if point not in (sp.oo, -sp.oo):
            try:
                series_exp = sp.series(expr, var, point, n=3).removeO()
                steps.append({
                    "title": "Асимптотическое разложение (ряд Тейлора)",
                    "desc": f"Разложение функции в окрестности {var.name} = {point_str}:\nf({var.name}) ≈ {format_sym(series_exp)} + o(({var.name}-{point_str})²)",
                })
            except Exception:
                pass
    else:
        # Continuous at point
        steps.append({
            "title": "Шаг 2. Непрерывность в точке",
            "desc": f"Функция определена и непрерывна в окрестности точки {point_str}. Значение предела совпадает со значением функции: {format_sym(result)}.",
        })

    # One-sided comparison
    if direction == "+-":
        try:
            lim_left = sp.limit(expr, var, point, dir="-")
            lim_right = sp.limit(expr, var, point, dir="+")
            left_str = format_sym(lim_left)
            right_str = format_sym(lim_right)
            if lim_left == lim_right:
                steps.append({
                    "title": "Шаг 4. Проверка односторонних пределов",
                    "desc": f"Левосторонний предел lim ({var.name}→{point_str}⁻) = {left_str}\nПравосторонний предел lim ({var.name}→{point_str}⁺) = {right_str}\nОба предела совпадают, следовательно двусторонний предел существует.",
                })
            else:
                steps.append({
                    "title": "Шаг 4. Односторонние пределы не совпадают",
                    "desc": f"Левосторонний: {left_str}\nПравосторонний: {right_str}\nТак как пределы слева и справа различаются, обычный двусторонний предел не существует (точка разрыва).",
                })
        except Exception:
            pass

    return steps


def compute_neighborhood_table(
    expr: sp.Expr, var: sp.Symbol, point: sp.Expr, count: int = 4
) -> List[Dict[str, str]]:
    """Calculates numerical values in a tiny epsilon neighborhood of the point."""
    rows = []
    try:
        if point == sp.oo:
            x_vals = [10, 100, 1000, 10000]
            for x_val in x_vals:
                try:
                    val = float(expr.subs(var, x_val).evalf())
                    rows.append({"x": str(x_val), "fx": f"{val:.6g}", "side": "x → +∞"})
                except Exception:
                    pass
        elif point == -sp.oo:
            x_vals = [-10, -100, -1000, -10000]
            for x_val in x_vals:
                try:
                    val = float(expr.subs(var, x_val).evalf())
                    rows.append({"x": str(x_val), "fx": f"{val:.6g}", "side": "x → -∞"})
                except Exception:
                    pass
        else:
            p_float = float(point.evalf())
            deltas = [0.1, 0.01, 0.001, 0.0001]
            # Left side
            for d in deltas:
                x_val = p_float - d
                try:
                    val = float(expr.subs(var, x_val).evalf())
                    rows.append({"x": f"{x_val:.5f}", "fx": f"{val:.6g}", "side": "Слева (x < x₀)"})
                except Exception:
                    pass
            # Right side
            for d in reversed(deltas):
                x_val = p_float + d
                try:
                    val = float(expr.subs(var, x_val).evalf())
                    rows.append({"x": f"{x_val:.5f}", "fx": f"{val:.6g}", "side": "Справа (x > x₀)"})
                except Exception:
                    pass
    except Exception:
        pass
    return rows


def solve_limit(
    expr_str: str,
    var_str: str = "x",
    point_str: str = "0",
    direction: str = "+-",
) -> Dict[str, Any]:
    """
    Main solver interface.
    direction: '+-' (both), '+' (right), '-' (left)
    """
    try:
        # If full limit was passed in expr_str, auto-extract components
        full_parsed = parse_full_limit(expr_str)
        if full_parsed:
            expr_str = full_parsed["expr"]
            var_str = full_parsed["var"] or var_str
            point_str = full_parsed["point"] or point_str
            direction = full_parsed["direction"] or direction

        var_name = clean_input(var_str).strip() or "x"
        var = sp.Symbol(var_name)

        expr = parse_math(expr_str, var)
        point = parse_math(point_str, var)

        # Compute limit
        dir_arg = direction if direction in ("+", "-") else "+-"
        limit_val = sp.limit(expr, var, point, dir=dir_arg)

        # Numeric approximation
        numeric_str = None
        try:
            if limit_val not in (sp.oo, -sp.oo, sp.zoo, sp.nan):
                num_val = float(limit_val.evalf())
                if not (math.isnan(num_val) or math.isinf(num_val)):
                    numeric_str = f"≈ {num_val:.6g}"
        except Exception:
            pass

        # Left and Right limits for completeness
        left_lim_str = None
        right_lim_str = None
        try:
            left_lim = sp.limit(expr, var, point, dir="-")
            left_lim_str = format_sym(left_lim)
        except Exception:
            pass

        try:
            right_lim = sp.limit(expr, var, point, dir="+")
            right_lim_str = format_sym(right_lim)
        except Exception:
            pass

        indet = detect_indeterminacy(expr, var, point)
        steps = generate_steps(expr, var, point, direction, limit_val, indet)
        table = compute_neighborhood_table(expr, var, point)

        dir_label = "Двусторонний (x → x₀)"
        if direction == "+":
            dir_label = "Правосторонний (x → x₀⁺)"
        elif direction == "-":
            dir_label = "Левосторонний (x → x₀⁻)"

        return {
            "success": True,
            "expr_display": str(expr).replace("**", "^"),
            "var": var_name,
            "point_display": format_sym(point),
            "dir_label": dir_label,
            "direction": direction,
            "result_display": format_sym(limit_val),
            "numeric_display": numeric_str,
            "indeterminacy": indet,
            "left_limit": left_lim_str,
            "right_limit": right_lim_str,
            "steps": steps,
            "table": table,
            "error": None,
        }

    except Exception as e:
        err_msg = str(e)
        if "mismatched parentheses" in err_msg.lower() or "unexpected EOF" in err_msg.lower():
            user_error = "Проверьте парность скобок (возможно, не закрыта открывающая скобка)."
        elif "invalid syntax" in err_msg.lower():
            user_error = "Синтаксическая ошибка. Проверьте правильность расстановки знаков операций (*, +, -, /)."
        else:
            user_error = f"Ошибка вычисления: {err_msg}"

        return {
            "success": False,
            "error": user_error,
        }
