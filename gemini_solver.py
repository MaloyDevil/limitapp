"""
LimitApp Gemini AI Solver - Integration with Google Gemini API
Creator: Нарницкий Роман (Syrok)
Provides AI-powered detailed educational solutions and step-by-step calculus explanations.
"""

from typing import Dict, Any, Optional
import httpx


GEMINI_MODELS = [
    ("gemini-3.1-flash-lite", "Gemini 3.1 Flash-Lite (Быстрый, стабильный и бесплатный)"),
    ("gemini-3.5-flash-lite", "Gemini 3.5 Flash-Lite (Новейший и производительный)"),
    ("gemini-3.8-flash", "Gemini 3.8 Flash (Флагманский анализ)"),
]

DEFAULT_MODEL = "gemini-3.1-flash-lite"
FALLBACK_MODELS = ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite"]


def build_math_prompt(expr: str, var: str, point: str, direction: str) -> str:
    """Builds an educational prompt for mathematical analysis of limits."""
    dir_str = "двусторонний"
    dir_math = f"{var} → {point}"
    if direction == "+":
        dir_str = "справа (правосторонний)"
        dir_math = f"{var} → {point}⁺"
    elif direction == "-":
        dir_str = "слева (левосторонний)"
        dir_math = f"{var} → {point}⁻"

    return f"""Ты — преподаватель высшей математики и эксперт по математическому анализу.
Твоя задача — подробно, строго и понятно для студента решить математический предел:

Задание:
lim ({dir_math}) [ {expr} ]
Направление стремления: {dir_str}

Требования к ответу:
1. Запиши исходный предел в красивом математическом виде.
2. Проведи анализ подстановки точки {point}: определи, возникает ли неопределенность (например, [0/0], [∞/∞], [1^∞], [0·∞], [∞ - ∞], [0^0], [∞^0]) или функция непрерывна.
3. Опиши подробный пошаговый ход решения с указанием применяемых математических теорем и методов:
   - Если используется Правило Лопиталя: покажи дифференцирование числителя и знаменателя.
   - Если используются замечательные пределы или эквивалентные бесконечно малые: выпиши применяемые эквивалентности.
   - Если используется разложение в ряд Тейлора: покажи степени и малые o(...).
   - Если неопределенность [1^∞]: покажи сведение ко второму замечательному пределу через экспоненту.
4. Проанализируй поведение односторонних пределов, если это требуется для доказательства существования предела.
5. Запиши четкий окончательный ответ.
6. Дай краткий совет или геометрический смысл (к чему приближается график функции).

Форматируй ответ в понятном GitHub Markdown с формулами, списками и выделением ключевых шагов. Отвечай на русском языке."""


def _execute_gemini_request(url: str, prompt: str, timeout: float) -> tuple[int, dict, str]:
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2048,
        },
    }
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, json=payload)
        try:
            data = resp.json()
        except Exception:
            data = {}
        return resp.status_code, data, resp.text


def solve_limit_with_gemini(
    expr: str,
    var: str = "x",
    point: str = "0",
    direction: str = "+-",
    api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    timeout: float = 35.0,
) -> Dict[str, Any]:
    """
    Calls Google Gemini REST API to solve the limit with AI reasoning.
    Includes automatic fallback to stable models if a deprecated or overloaded model is requested.
    """
    clean_key = (api_key or "").strip()
    if not clean_key:
        return {
            "success": False,
            "error": "API ключ Gemini не указан. Пожалуйста, введите ваш бесплатный ключ в настройках ИИ.",
        }

    prompt = build_math_prompt(expr, var, point, direction)

    # Models queue: chosen model first, then fallback models if different
    models_to_try = [model]
    for fb in FALLBACK_MODELS:
        if fb not in models_to_try:
            models_to_try.append(fb)

    last_error = ""

    for cur_model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{cur_model}:generateContent?key={clean_key}"
        try:
            status_code, data, raw_text = _execute_gemini_request(url, prompt, timeout)

            if status_code == 200:
                candidates = data.get("candidates", [])
                if candidates:
                    first_cand = candidates[0]
                    content = first_cand.get("content", {})
                    parts = content.get("parts", [])
                    if parts:
                        ai_text = parts[0].get("text", "")
                        return {
                            "success": True,
                            "text": ai_text,
                            "model": cur_model,
                            "error": None,
                        }
                return {
                    "success": False,
                    "error": "Модель Gemini вернула пустой ответ. Попробуйте повторить запрос.",
                }

            elif status_code in (400, 403):
                err_data = data.get("error", {})
                err_msg = err_data.get("message", "Неверный API ключ или доступ запрещен")
                return {
                    "success": False,
                    "error": f"Ошибка авторизации Google Gemini ({status_code}): {err_msg}. Проверьте правильность API ключа.",
                }

            elif status_code == 404:
                err_data = data.get("error", {})
                err_msg = err_data.get("message", "Модель недоступна")
                last_error = f"Модель {cur_model} недоступна: {err_msg}"
                # If there are fallback models, loop will automatically try the next stable model
                continue

            elif status_code in (429, 503):
                err_data = data.get("error", {})
                err_msg = err_data.get("message", "Высокая нагрузка на сервер Google Gemini")
                last_error = f"Сервер Gemini перегружен ({status_code}): {err_msg}"
                # Try fallback model
                continue

            else:
                err_data = data.get("error", {})
                err_msg = err_data.get("message", raw_text[:180])
                last_error = f"Ошибка сервера Google Gemini ({status_code}): {err_msg}"
                continue

        except httpx.ConnectError:
            return {
                "success": False,
                "error": "Не удалось подключиться к серверам Google Gemini. Проверьте подключение к интернету.",
            }
        except httpx.TimeoutException:
            last_error = f"Время ожидания ответа от модели {cur_model} истекло."
            continue
        except Exception as e:
            return {
                "success": False,
                "error": f"Сбой обращения к Gemini API: {str(e)}",
            }

    return {
        "success": False,
        "error": last_error or "Не удалось получить ответ от Google Gemini. Попробуйте снова позже.",
    }
