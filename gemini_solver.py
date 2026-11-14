"""
LimitApp Gemini AI Solver - Integration with Google Gemini API
Creator: Нарницкий Роман (Syrok)
Provides AI-powered detailed educational solutions and step-by-step calculus explanations.
"""

from typing import Dict, Any, Optional
import httpx


GEMINI_MODELS = [
    ("gemini-1.5-flash", "Gemini 1.5 Flash (Быстрый и бесплатный)"),
    ("gemini-2.0-flash", "Gemini 2.0 Flash (Новейший ИИ)"),
    ("gemini-1.5-pro", "Gemini 1.5 Pro (Глубокий анализ)"),
]

DEFAULT_MODEL = "gemini-1.5-flash"


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


def solve_limit_with_gemini(
    expr: str,
    var: str = "x",
    point: str = "0",
    direction: str = "+-",
    api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    timeout: float = 25.0,
) -> Dict[str, Any]:
    """
    Calls Google Gemini REST API to solve the limit with AI reasoning.
    Returns:
        dict: {"success": bool, "text": str, "model": str, "error": str}
    """
    clean_key = (api_key or "").strip()
    if not clean_key:
        return {
            "success": False,
            "error": "API ключ Gemini не указан. Пожалуйста, введите ваш бесплатный ключ в настройках ИИ.",
        }

    prompt = build_math_prompt(expr, var, point, direction)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={clean_key}"

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

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload)

        if resp.status_code == 200:
            data = resp.json()
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
                        "model": model,
                        "error": None,
                    }
            return {
                "success": False,
                "error": "Модель Gemini вернула пустой ответ. Попробуйте повторить запрос.",
            }

        elif resp.status_code in (400, 403):
            err_data = resp.json().get("error", {})
            err_msg = err_data.get("message", "Неверный API ключ")
            return {
                "success": False,
                "error": f"Ошибка авторизации Google Gemini ({resp.status_code}): {err_msg}. Проверьте правильность API ключа.",
            }
        elif resp.status_code == 429:
            return {
                "success": False,
                "error": "Превышен бесплатный лимит запросов Google Gemini (429 Too Many Requests). Подождите 1 минуту и попробуйте снова.",
            }
        else:
            return {
                "success": False,
                "error": f"Ошибка сервера Google Gemini (HTTP {resp.status_code}): {resp.text[:200]}",
            }

    except httpx.ConnectError:
        return {
            "success": False,
            "error": "Не удалось подключиться к серверам Google Gemini. Проверьте подключение к интернету.",
        }
    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "Время ожидания ответа от Google Gemini истекло (таймаут). Попробуйте снова.",
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Сбой обращения к Gemini API: {str(e)}",
        }
