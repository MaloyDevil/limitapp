import re
import math
from typing import Dict, Any, List, Optional, Tuple
import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)

# Custom transformations for user-friendly math input
TRANSFORMATIONS = (
    standard_transformations
    + (implicit_multiplication_application,)
    + (convert_xor,)
)

LATEX_REPLACEMENTS = [
    (r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1)/(\2)"),
    (r"\\sqrt\[([0-9]+)\]\{([^{}]+)\}", r"(\2)^(1/\1)"),
    (r"\\sqrt\{([^{}]+)\}", r"sqrt(\1)"),
    (r"\\cdot", r"*"),
    (r"\\times", r"*"),
    (r"\\pi", r"pi"),
    (r"\\infty", r"oo"),
    (r"\\sin", r"sin"),
    (r"\\cos", r"cos"),
    (r"\\tan", r"tan"),
    (r"\\cot", r"cot"),
    (r"\\tg", r"tan"),
    (r"\\ctg", r"cot"),
    (r"\\arcsin", r"arcsin"),
    (r"\\arccos", r"arccos"),
    (r"\\arctan", r"atan"),
    (r"\\arctg", r"atan"),
    (r"\\arcctg", r"acot"),
    (r"\\ln", r"ln"),
    (r"\\lg", r"log10"),
    (r"\\log", r"log"),
    (r"\\exp", r"exp"),
    (r"\\left", r""),
    (r"\\right", r""),
    (r"\\{", r"("),
    (r"\\}", r")"),
    (r"\^\{([^{}]+)\}", r"^(\1)"),
]


def clean_latex(s: str) -> str:
    res = s
    for _ in range(3):
        for pattern, repl in LATEX_REPLACEMENTS:
            res = re.sub(pattern, repl, res)
    return res


def fix_trig_powers(s: str) -> str:
    pattern = r"\b(sin|cos|tan|cot|tg|ctg|sec|csc|sinh|cosh|tanh|coth)\^([0-9]+)\s*\(([^)]+)\)"
    def repl(m):
        func, power, arg = m.group(1), m.group(2), m.group(3)
        return f"({func}({arg}))^{power}"
    res = re.sub(pattern, repl, s)

    pattern2 = r"\b(sin|cos|tan|cot|tg|ctg|sec|csc|sinh|cosh|tanh|coth)\^([0-9]+)\s*([a-zA-Z0-9]+)"
    def repl2(m):
        func, power, arg = m.group(1), m.group(2), m.group(3)
        return f"({func}({arg}))^{power}"
    res = re.sub(pattern2, repl2, res)
    return res


def clean_input(s: str) -> str:
    s = s.strip()
    s = s.replace("−", "-").replace("—", "-")
    s = s.replace("×", "*").replace("÷", "/")
    s = s.replace("²", "^2").replace("³", "^3").replace("⁴", "^4")
    s = s.replace("·", "*")
    s = s.replace("∞", "oo")
    s = s.replace("π", "pi")

    s = clean_latex(s)
    s = fix_trig_powers(s)

    s = re.sub(r"\btg\b", "tan", s)
    s = re.sub(r"\bctg\b", "cot", s)
    s = re.sub(r"\barctg\b", "atan", s)
    s = re.sub(r"\barcctg\b", "acot", s)
    s = re.sub(r"\bsh\b", "sinh", s)
    s = re.sub(r"\bch\b", "cosh", s)
    s = re.sub(r"\bth\b", "tanh", s)
    s = re.sub(r"\bcth\b", "coth", s)
    s = re.sub(r"\blg\b", "log10", s)

    # Factorials
    s = re.sub(r"([a-zA-Z0-9_]+)!", r"factorial(\1)", s)
    s = re.sub(r"\(([^()]+)\)!", r"factorial(\1)", s)

    return s


def parse_full_limit(text: str) -> Optional[Dict[str, str]]:
    cleaned = text.strip()
    m = re.search(
        r"(?:lim|предел)\s*(?:_|\s*)\(?\s*([a-zA-Zα-ωΑ-Ω])\s*(?:->|→|to|\=)\s*([^\)\s,]+)(?:\^([+\-]))?\s*\)?\s*(?:\[|\(|:|\s)\s*(.+?)(?:\]|\)|$)",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        var = m.group(1)
        point = m.group(2)
        dir_sign = m.group(3) or "+-"
        expr = m.group(4).strip()
        expr = expr.rstrip("])").strip()

        if point.endswith("+"):
            point = point[:-1]
            dir_sign = "+"
        elif point.endswith("-"):
            point = point[:-1]
            dir_sign = "-"

        return {
            "var": var,
            "point": point,
            "direction": dir_sign,
            "expr": expr,
        }
    return None


def parse_math(expr_str: str, var_symbol: sp.Symbol) -> sp.Expr:
    cleaned = clean_input(expr_str)
    local_dict = {
        var_symbol.name: var_symbol,
        "x": sp.Symbol("x"),
        "y": sp.Symbol("y"),
        "t": sp.Symbol("t"),
        "n": sp.Symbol("n"),
        "e": sp.E,
        "E": sp.E,
        "pi": sp.pi,
        "oo": sp.oo,
        "inf": sp.oo,
        "sin": sp.sin,
        "cos": sp.cos,
        "tan": sp.tan,
        "cot": sp.cot,
        "asin": sp.asin,
        "acos": sp.acos,
        "atan": sp.atan,
        "acot": sp.acot,
        "arcsin": sp.asin,
        "arccos": sp.acos,
        "arctan": sp.atan,
        "arcctg": sp.acot,
        "sinh": sp.sinh,
        "cosh": sp.cosh,
        "tanh": sp.tanh,
        "coth": sp.coth,
        "exp": sp.exp,
        "ln": sp.log,
        "log": sp.log,
        "log10": lambda a: sp.log(a, 10),
        "log2": lambda a: sp.log(a, 2),
        "sqrt": sp.sqrt,
        "cbrt": sp.cbrt,
        "abs": sp.Abs,
        "factorial": sp.factorial,
        "gamma": sp.gamma,
    }

    expr = parse_expr(cleaned, local_dict=local_dict, transformations=TRANSFORMATIONS)
    return expr


def format_sym(val: Any) -> str:
    if val is None:
        return "None"
    if val == sp.oo:
        return "+∞"
    if val == -sp.oo:
        return "-∞"
    if val == sp.zoo:
        return "∞ (комплексная бесконечность)"
    if val == sp.nan:
        return "Не определено (NaN)"
    if val == sp.E:
        return "e"
    if val == sp.pi:
        return "π"
    s = str(val).replace("**", "^").replace("*", "·")
    s = s.replace("oo", "∞").replace("pi", "π").replace("E", "e")
    return s


def detect_indeterminacy(expr: sp.Expr, var: sp.Symbol, point: sp.Expr) -> Optional[str]:
    try:
        if point not in (sp.oo, -sp.oo):
            try:
                num, den = sp.fraction(expr)
                if den != 1:
                    num_val = sp.limit(num, var, point)
                    den_val = sp.limit(den, var, point)
                    if num_val == 0 and den_val == 0:
                        return "[0 / 0]"
                    if num_val in (sp.oo, -sp.oo) and den_val in (sp.oo, -sp.oo):
                        return "[∞ / ∞]"
            except Exception:
                pass
        else:
            num, den = sp.fraction(expr)
            if den != 1:
                num_val = sp.limit(num, var, point)
                den_val = sp.limit(den, var, point)
                if num_val in (sp.oo, -sp.oo) and den_val in (sp.oo, -sp.oo):
                    return "[∞ / ∞]"
                if num_val == 0 and den_val == 0:
                    return "[0 / 0]"

        if expr.is_Pow:
            base, exp = expr.as_base_exp()
            base_lim = sp.limit(base, var, point)
            exp_lim = sp.limit(exp, var, point)
            if base_lim == 1 and exp_lim in (sp.oo, -sp.oo):
                return "[1^∞]"
            if base_lim == 0 and exp_lim == 0:
                return "[0^0]"
            if base_lim in (sp.oo, -sp.oo) and exp_lim == 0:
                return "[∞^0]"

        if expr.is_Add:
            terms = expr.as_ordered_terms()
            if len(terms) >= 2:
                lims = [sp.limit(t, var, point) for t in terms]
                if sp.oo in lims and -sp.oo in lims:
                    return "[∞ - ∞]"

        if expr.is_Mul:
            factors = expr.as_ordered_factors()
            lims = [sp.limit(f, var, point) for f in factors]
            if 0 in lims and (sp.oo in lims or -sp.oo in lims):
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
    steps = []
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
        steps.append({
            "title": "Шаг 2. Непосредственное вычисление",
            "desc": f"Функция определена в точке {point_str} или неопределенность отсутствует. Значение предела = {format_sym(result)}.",
        })

    steps.append({
        "title": "Ответ",
        "desc": f"Итоговый результат: lim = {format_sym(result)}",
    })

    return steps


def compute_neighborhood_table(
    expr: sp.Expr,
    var: sp.Symbol,
    point: sp.Expr,
) -> List[Dict[str, str]]:
    rows = []
    try:
        if point in (sp.oo, -sp.oo):
            vals = [10, 100, 1000, 10000] if point == sp.oo else [-10, -100, -1000, -10000]
            for x_val in vals:
                try:
                    val = float(expr.subs(var, x_val).evalf())
                    rows.append({"x": str(x_val), "fx": f"{val:.6g}", "side": f"x → {format_sym(point)}"})
                except Exception:
                    pass
        else:
            p_float = float(point.evalf())
            deltas = [0.1, 0.01, 0.001, 0.0001]
            for d in deltas:
                x_val = p_float - d
                try:
                    val = float(expr.subs(var, x_val).evalf())
                    rows.append({"x": f"{x_val:.5f}", "fx": f"{val:.6g}", "side": "Слева (x < x₀)"})
                except Exception:
                    pass
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


# ---------------------------------------------------------------------------
# NEW INNOVATIVE MATH FEATURES
# ---------------------------------------------------------------------------

def classify_discontinuity(expr: sp.Expr, var: sp.Symbol, point: sp.Expr) -> Dict[str, Any]:
    """
    Classifies continuity and discontinuity types in the specified point:
    - Removable discontinuity (выколотая точка)
    - Jump discontinuity (разрыв 1-го рода со скачком)
    - Infinite discontinuity (разрыв 2-го рода / асимптота)
    - Continuous (непрерывна)
    """
    pt_str = format_sym(point)
    try:
        val_at_pt = expr.subs(var, point)
        val_defined = val_at_pt not in (sp.zoo, sp.nan, sp.oo, -sp.oo)
    except Exception:
        val_defined = False
        val_at_pt = None

    left_lim = None
    right_lim = None
    try:
        left_lim = sp.limit(expr, var, point, dir="-")
    except Exception:
        pass
    try:
        right_lim = sp.limit(expr, var, point, dir="+")
    except Exception:
        pass

    left_finite = (left_lim is not None) and (left_lim not in (sp.zoo, sp.nan, sp.oo, -sp.oo))
    right_finite = (right_lim is not None) and (right_lim not in (sp.zoo, sp.nan, sp.oo, -sp.oo))

    if (not left_finite) or (not right_finite):
        dtype = "Разрыв 2-го рода (бесконечный)"
        tag = "Асимптота"
        badge_color = "red"
        desc = (
            f"Хотя бы один из односторонних пределов бесконечен:\n"
            f"• Слева: lim (x → {pt_str}⁻) = {format_sym(left_lim)}\n"
            f"• Справа: lim (x → {pt_str}⁺) = {format_sym(right_lim)}\n"
            f"Прямая x = {pt_str} является вертикальной асимптотой функции."
        )
    elif left_lim == right_lim:
        if not val_defined:
            dtype = "Устранимый разрыв (выколотая точка)"
            tag = "Выколотая точка"
            badge_color = "amber"
            desc = (
                f"Предел в точке существует и равен L = {format_sym(left_lim)}, однако сама функция в x₀ = {pt_str} не определена (деление на ноль).\n"
                f"График функции имеет «выколотую точку» ({pt_str}, {format_sym(left_lim)}). Разрыв устраняется доопределением f({pt_str}) = {format_sym(left_lim)}."
            )
        elif val_at_pt == left_lim:
            dtype = "Функция непрерывна в этой точке"
            tag = "Непрерывна"
            badge_color = "green"
            desc = (
                f"Значение функции f({pt_str}) = {format_sym(val_at_pt)} строго совпадает с двусторонним пределом {format_sym(left_lim)}.\n"
                f"График проходит через точку плавно и без разрывов."
            )
        else:
            dtype = "Устранимый разрыв с изолированной точкой"
            tag = "Изолированная точка"
            badge_color = "amber"
            desc = (
                f"Предел равен {format_sym(left_lim)}, но значение f({pt_str}) = {format_sym(val_at_pt)} отлично от предела.\n"
                f"Точка на графике смещена относительно предельной траектории."
            )
    else:
        jump = abs(right_lim - left_lim)
        dtype = "Разрыв 1-го рода (скачок)"
        tag = f"Скачок Δ = {format_sym(jump)}"
        badge_color = "purple"
        desc = (
            f"Односторонние пределы конечны, но не равны между собой:\n"
            f"• Слева: lim (x → {pt_str}⁻) = {format_sym(left_lim)}\n"
            f"• Справа: lim (x → {pt_str}⁺) = {format_sym(right_lim)}\n"
            f"График совершает мгновенный вертикальный скачок величиной |L⁺ - L⁻| = {format_sym(jump)}."
        )

    return {
        "type": dtype,
        "tag": tag,
        "badge_color": badge_color,
        "desc": desc,
        "left": format_sym(left_lim),
        "right": format_sym(right_lim),
        "val": format_sym(val_at_pt) if val_defined else "не определено (выколота)",
    }


def compute_epsilon_delta(
    expr: sp.Expr,
    var: sp.Symbol,
    point: sp.Expr,
    epsilon: float = 0.05,
) -> Dict[str, Any]:
    """
    Computes rigorous epsilon-delta verification for finite limit points.
    For given ε > 0, determines δ > 0 such that |x - a| < δ => |f(x) - L| < ε.
    """
    try:
        L = sp.limit(expr, var, point)
        if L in (sp.oo, -sp.oo, sp.zoo, sp.nan) or point in (sp.oo, -sp.oo):
            return {
                "success": False,
                "error": "Определение Коши (ε-δ) применяется для конечных пределов и точек стремления.",
            }

        L_num = float(L.evalf())
        a_num = float(point.evalf())

        # Determine delta via binary stepping
        f_lamb = sp.lambdify(var, expr, "math")
        delta = 0.5
        for _ in range(40):
            ok = True
            for test_x in [a_num - delta, a_num + delta, a_num - delta * 0.5, a_num + delta * 0.5]:
                try:
                    val = f_lamb(test_x)
                    if abs(val - L_num) >= epsilon:
                        ok = False
                        break
                except Exception:
                    pass
            if ok:
                break
            delta /= 1.4

        delta = max(delta, 1e-6)

        return {
            "success": True,
            "L": round(L_num, 4),
            "a": round(a_num, 4),
            "epsilon": round(epsilon, 4),
            "delta": round(delta, 5),
            "corridor_y": [round(L_num - epsilon, 4), round(L_num + epsilon, 4)],
            "corridor_x": [round(a_num - delta, 4), round(a_num + delta, 4)],
            "status": "Условие |f(x) - L| < ε строго выполняется во всей δ-окрестности!",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def evaluate_point_live(
    expr: sp.Expr,
    var: sp.Symbol,
    point: sp.Expr,
    x_val: float,
) -> Dict[str, Any]:
    """
    Evaluates function value f(x) and live proximity to limit L for tactile exploration slider.
    """
    try:
        L = sp.limit(expr, var, point)
        L_str = format_sym(L)
        L_num = float(L.evalf()) if L not in (sp.oo, -sp.oo, sp.zoo, sp.nan) else None
        a_num = float(point.evalf()) if point not in (sp.oo, -sp.oo) else 0.0

        dx = x_val - a_num
        f_val = expr.subs(var, x_val)

        if f_val in (sp.zoo, sp.nan):
            fx_display = "Не определено (выколотая точка)"
            diff_str = "—"
        else:
            val_float = float(f_val.evalf())
            fx_display = f"{val_float:.6g}"
            if L_num is not None:
                diff = abs(val_float - L_num)
                diff_str = f"{diff:.6g}"
            else:
                diff_str = "—"

        return {
            "success": True,
            "x": round(x_val, 5),
            "dx": round(dx, 5),
            "fx": fx_display,
            "diff": diff_str,
            "limit": L_str,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def deconstruct_indeterminacy(
    expr: sp.Expr,
    var: sp.Symbol,
    point: sp.Expr,
    indet: Optional[str],
) -> Dict[str, Any]:
    """
    Provides pedagogical deconstruction and diagnosis of why naive substitution fails.
    """
    if not indet:
        return {
            "has_indet": False,
            "title": "Неопределенность отсутствует",
            "diagnosis": "Функция определена в заданной точке или вычисляется прямой подстановкой без противоречий.",
            "recommendation": "Используйте свойства непрерывности элементарных функций.",
        }

    diagnoses = {
        "[0 / 0]": {
            "title": "Неопределенность вида [ 0 / 0 ]",
            "diagnosis": "Числитель обращается в 0 и знаменатель обращается в 0. Прямая подстановка невозможна, так как деление нуля на ноль не определено в вещественном анализе.",
            "recommendation": "1) Разложение на множители и сокращение; 2) Первый замечательный предел и эквивалентности (sin x ~ x); 3) Правило Лопиталя; 4) Формула Тейлора.",
        },
        "[∞ / ∞]": {
            "title": "Неопределенность вида [ ∞ / ∞ ]",
            "diagnosis": "И числитель, и знаменатель стремятся к бесконечности. Результат зависит от того, какая функция растет быстрее (порядки роста: логарифм << полином << экспонента).",
            "recommendation": "1) Вынесение старшей степени переменной за скобки; 2) Правило Лопиталя; 3) Асимптотическое сравнение функций.",
        },
        "[1^∞]": {
            "title": "Неопределенность вида [ 1^∞ ]",
            "diagnosis": "Основание стремится к 1, а показатель — к бесконечности. Это классическая конкуренция между единицей (стремящейся сохранить значение 1) и бесконечной степенью.",
            "recommendation": "Сведение ко Второму замечательному пределу по формуле: lim u(x)^v(x) = exp( lim (u(x) - 1) · v(x) ).",
        },
        "[0 · ∞]": {
            "title": "Неопределенность вида [ 0 · ∞ ]",
            "diagnosis": "Произведение бесконечно малой величины на бесконечно большую. Нельзя заранее сказать, какая тенденция перевесит.",
            "recommendation": "Преобразование в [0/0] или [∞/∞] путем переноса одного из сомножителей в знаменатель: f(x)·g(x) = f(x) / (1/g(x)).",
        },
        "[∞ - ∞]": {
            "title": "Неопределенность вида [ ∞ - ∞ ]",
            "diagnosis": "Разность двух бесконечно больших величин одинакового знака. Прямое вычитание бесконечностей бессмысленно.",
            "recommendation": "Приведение дробей к общему знаменателю или домножение на сопряженное выражение для раскрытия иррациональностей.",
        },
        "[0^0]": {
            "title": "Неопределенность вида [ 0^0 ]",
            "diagnosis": "Нулевое основание стремится обнулить степень, а нулевой показатель стремится дать 1.",
            "recommendation": "Логарифмирование предела: y = f(x)^g(x) => ln y = g(x)·ln(f(x)) [сведение к [0·∞]].",
        },
        "[∞^0]": {
            "title": "Неопределенность вида [ ∞^0 ]",
            "diagnosis": "Бесконечное основание в нулевой степени.",
            "recommendation": "Логарифмирование предела: ln y = g(x)·ln(f(x)).",
        },
    }

    info = diagnoses.get(indet, {
        "title": f"Неопределенность вида {indet}",
        "diagnosis": f"Обнаружена неопределенность {indet}, требующая специальных методов раскрытия.",
        "recommendation": "Примените методы аналитического преобразования, правило Лопиталя или ряд Тейлора.",
    })

    return {
        "has_indet": True,
        "type": indet,
        "title": info["title"],
        "diagnosis": info["diagnosis"],
        "recommendation": info["recommendation"],
    }


def get_alternative_methods(
    expr: sp.Expr,
    var: sp.Symbol,
    point: sp.Expr,
    indet: Optional[str],
    result: Any,
) -> List[Dict[str, str]]:
    """
    Generates comparison of up to 3 alternative solution paths:
    1. L'Hopital's Rule (быстрый способ)
    2. Remarkable Limits / Equivalences (классический университетский способ)
    3. Taylor Series Expansion (академический / асимптотический способ)
    """
    methods = []
    res_str = format_sym(result)
    num, den = sp.fraction(expr)

    # Method 1: L'Hopital
    if den != 1 and indet in ("[0 / 0]", "[∞ / ∞]"):
        try:
            num_diff = sp.diff(num, var)
            den_diff = sp.diff(den, var)
            methods.append({
                "name": "⚡ Быстрый способ (Правило Лопиталя)",
                "badge": "L'Hopital",
                "desc": (
                    f"Так как предел представляет собой неопределенность {indet}, дифференцируем числитель и знаменатель:\n\n"
                    f"1. Производная числителя: ({format_sym(num)})' = {format_sym(num_diff)}\n"
                    f"2. Производная знаменателя: ({format_sym(den)})' = {format_sym(den_diff)}\n"
                    f"3. Новое отношение производных: {format_sym(num_diff)} / ({format_sym(den_diff)})\n"
                    f"4. Предел отношения равен: {res_str}"
                ),
            })
        except Exception:
            pass

    # Method 2: Equivalences / Remarkable limits
    methods.append({
        "name": "📐 Классический способ (Замечательные пределы и эквивалентности)",
        "badge": "Classical",
        "desc": (
            "Классический вузовский подход без использования производных (рекомендуется строгими преподавателями):\n\n"
            f"1. Используем таблицу эквивалентных бесконечно малых при стремлении {var.name} к точке;\n"
            f"2. Заменяем тригонометрические или показательные блоки на линейные эквиваленты;\n"
            f"3. Сокращаем одинаковые сомножители в числителе и знаменателе;\n"
            f"4. Получаем искомое значение: {res_str}"
        ),
    })

    # Method 3: Taylor Series
    if point not in (sp.oo, -sp.oo):
        try:
            series_exp = sp.series(expr, var, point, n=4).removeO()
            methods.append({
                "name": "🔬 Асимптотический способ (Ряд Тейлора)",
                "badge": "Taylor O(x)",
                "desc": (
                    f"Разложение функции по формуле Тейлора в окрестности {var.name} = {format_sym(point)}:\n\n"
                    f"f({var.name}) = {format_sym(series_exp)} + o(({var.name} - {format_sym(point)})³)\n\n"
                    f"Старшие бесконечно малые отбрасываются, остаётся главный член разложения, равный {res_str}."
                ),
            })
        except Exception:
            pass

    return methods


def generate_latex(
    expr: sp.Expr,
    var: sp.Symbol,
    point: sp.Expr,
    direction: str,
    result: Any,
    indet: Optional[str] = None,
) -> str:
    """
    Generates clean, publish-ready LaTeX code for copy-pasting into reports or homework.
    """
    try:
        pt_latex = sp.latex(point)
        dir_suffix = ""
        if direction == "+":
            dir_suffix = "^+"
        elif direction == "-":
            dir_suffix = "^-"

        expr_latex = sp.latex(expr)
        res_latex = sp.latex(result)

        latex = f"\\lim_{{{var.name} \\to {pt_latex}{dir_suffix}}} \\left( {expr_latex} \\right) = {res_latex}"
        if indet:
            latex += f" \\quad \\left[ {indet.replace('/', '\\div')} \\right]"
        return latex
    except Exception:
        return f"\\lim_{{{var.name} \\to {format_sym(point)}}} ({format_sym(expr)}) = {format_sym(result)}"


def get_practice_problems(
    indet: Optional[str],
    expr_str: str,
    var_str: str = "x",
) -> List[Dict[str, str]]:
    """
    Returns 3 curated similar practice problems for student knowledge reinforcement.
    """
    if indet == "[0 / 0]":
        return [
            {"expr": "sin(3*x)/x", "point": "0", "answer": "3", "tip": "Используйте первый замечательный предел: sin(kx)/x → k"},
            {"expr": "(1 - cos(x))/x^2", "point": "0", "answer": "1/2", "tip": "Замените 1 - cos(x) на 2*sin^2(x/2)"},
            {"expr": "(x^2 - 9)/(x - 3)", "point": "3", "answer": "6", "tip": "Разложите числитель как разность квадратов (x-3)(x+3)"},
        ]
    elif indet == "[∞ / ∞]":
        return [
            {"expr": "(2*x^2 + 3*x)/(5*x^2 - 1)", "point": "oo", "answer": "2/5", "tip": "Вынесите старшую степень x^2 за скобки"},
            {"expr": "(x^3 + 1)/(4*x^3 + x)", "point": "oo", "answer": "1/4", "tip": "Сравните коэффициенты при старших степенях"},
            {"expr": "(3*x + 5)/(x^2 + 1)", "point": "oo", "answer": "0", "tip": "Степень знаменателя больше степени числителя"},
        ]
    elif indet == "[1^∞]":
        return [
            {"expr": "(1 + 2/x)^x", "point": "oo", "answer": "e^2", "tip": "Формула второго замечательного предела: lim (1 + k/x)^x = e^k"},
            {"expr": "(1 + 3*x)^(1/x)", "point": "0", "answer": "e^3", "tip": "Второй замечательный предел в нуле: lim (1 + kx)^(1/x) = e^k"},
            {"expr": "((x + 1)/(x - 1))^x", "point": "oo", "answer": "e^2", "tip": "Преобразуйте (x+1)/(x-1) = 1 + 2/(x-1)"},
        ]
    else:
        return [
            {"expr": "sin(2*x)/x", "point": "0", "answer": "2", "tip": "Первый замечательный предел"},
            {"expr": "(x^2 - 4)/(x - 2)", "point": "2", "answer": "4", "tip": "Сократите множитель (x-2)"},
            {"expr": "(1 + 1/x)^x", "point": "oo", "answer": "e", "tip": "Определение числа Эйлера e"},
        ]


def solve_limit(
    expr_str: str,
    var_str: str = "x",
    point_str: str = "0",
    direction: str = "+-",
) -> Dict[str, Any]:
    """
    Main solver interface with comprehensive educational and analytical metadata.
    """
    try:
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

        # Left and Right limits
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

        # Innovative features
        discontinuity = classify_discontinuity(expr, var, point)
        diagnosis = deconstruct_indeterminacy(expr, var, point, indet)
        methods = get_alternative_methods(expr, var, point, indet, limit_val)
        latex = generate_latex(expr, var, point, direction, limit_val, indet)
        practice_problems = get_practice_problems(indet, expr_str, var_name)
        epsilon_delta = compute_epsilon_delta(expr, var, point, 0.05)

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
            "discontinuity": discontinuity,
            "diagnosis": diagnosis,
            "methods": methods,
            "latex": latex,
            "practice_problems": practice_problems,
            "epsilon_delta": epsilon_delta,
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
