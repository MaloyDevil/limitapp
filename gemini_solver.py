"""
LimitApp Gemini AI Solver - Integration with Google Gemini API
Creator: Нарницкий Роман (Syrok)
Provides AI-powered detailed educational solutions, step-by-step calculus explanations,
multimodal image recognition (OCR of limits from photos), and interactive solution verification.
"""

from typing import Dict, Any, Optional
import base64
import json
import re
import httpx


GEMINI_MODELS = [
    ("gemini-3.5-flash-lite", "Gemini 3.5 Flash-Lite (Новейший, сбалансированный и бесплатный)"),
    ("gemini-3.1-flash-lite", "Gemini 3.1 Flash-Lite (Высокая скорость ответа)"),
    ("gemini-3.8-flash", "Gemini 3.8 Flash (Флагманский глубокий анализ)"),
]

DEFAULT_MODEL = "gemini-3.5-flash-lite"
FALLBACK_MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash"]


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
2. Проведи анализ подстановки точки {point}: определи, возникает ли неопределенность (например, [0/0], [∞/∞], [1^∞], [0·∞], [∞-∞] и т.д.).
3. Подробно объясни теоремы и методы раскрытия:
   - Если применяется Правило Лопиталя: покажи производные числителя и знаменателя отдельно.
   - Если применяются эквивалентности или первый/второй замечательные пределы: выпиши конкретные формулы эквивалентности.
   - Если применяется разложение Тейлора: покажи формулы разложения до малых порядка o().
4. Опиши геометрический и физический смысл поведения функции вблизи точки {point} (поведение графика, асимптота, выколотая точка или скачок).
5. Напиши четкий финальный ответ в рамке или жирным шрифтом: Ответ: ...

Используй чистый структурированный Markdown с формулами в $...$ и заголовками шагов. Пиши понятно, дружелюбно и академически строго на русском языке."""


def solve_limit_with_gemini(
    expr: str,
    var: str = "x",
    point: str = "0",
    direction: str = "+-",
    api_key: str = "",
    model: str = DEFAULT_MODEL,
    timeout: float = 35.0,
) -> Dict[str, Any]:
    """
    Solves math limit via Google Gemini API with automatic fallback to alternative models.
    """
    if not api_key or not api_key.strip():
        return {
            "success": False,
            "error": "API ключ Google Gemini не указан. Введите бесплатный ключ в настройках (кнопка шестеренки или меню Автор).",
        }

    prompt = build_math_prompt(expr, var, point, direction)

    models_to_try = [model]
    for fb in FALLBACK_MODELS:
        if fb not in models_to_try:
            models_to_try.append(fb)

    last_error = ""

    for target_model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={api_key.strip()}"
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
                "maxOutputTokens": 2800,
            }
        }

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, json=payload)

            if response.status_code == 200:
                data = response.json()
                try:
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts and "text" in parts[0]:
                            return {
                                "success": True,
                                "text": parts[0]["text"],
                                "model": target_model,
                            }
                except Exception as parse_err:
                    last_error = f"Ошибка парсинга ответа: {parse_err}"
                    continue

            elif response.status_code == 404:
                last_error = f"Модель {target_model} недоступна (404). Пробуем резервную..."
                continue
            elif response.status_code in (429, 503):
                last_error = f"Сервер Gemini перегружен ({response.status_code}) на {target_model}. Пробуем резервную модель..."
                continue
            elif response.status_code == 400:
                err_data = response.json().get("error", {})
                msg = err_data.get("message", "Неверный запрос или ключ API.")
                return {
                    "success": False,
                    "error": f"Ошибка Gemini API (400): {msg}",
                }
            else:
                last_error = f"Ошибка Gemini API (код {response.status_code}): {response.text[:200]}"
                continue

        except httpx.TimeoutException:
            last_error = f"Таймаут соединения с {target_model}. Пробуем более быструю модель..."
            continue
        except Exception as e:
            last_error = f"Ошибка подключения к {target_model}: {str(e)}"
            continue

    return {
        "success": False,
        "error": f"Не удалось получить ответ от Gemini API. Причина: {last_error}",
    }


def recognize_limit_from_image(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    api_key: str = "",
    model: str = DEFAULT_MODEL,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """
    Multimodal OCR: extracts mathematical limit expression, variable, point, and direction
    from an image or photo of handwriting/textbook.
    """
    if not api_key or not api_key.strip():
        return {
            "success": False,
            "error": "API ключ Google Gemini не указан. Задайте ключ в настройках приложения.",
        }

    b64_data = base64.b64encode(image_bytes).decode("utf-8")

    prompt = """Ты — высокоточный OCR-инструмент и эксперт по математическому анализу.
Проанализируй изображение и извлеки из него математический предел (lim).
Определи:
1. Математическую функцию f(x) (в формате, пригодном для калькулятора, например: sin(x)/x, (1-cos(x))/x^2, (1+1/x)^x)
2. Переменную предела (обычно x, n, t, y)
3. Предельную точку (например: 0, oo, -oo, 1, pi, pi/2, e)
4. Направление стремления (+- если двусторонний, + если справа, - если слева)

Верни СТРОГО валидный JSON следующей структуры, без лишнего текста:
```json
{
  "expr": "...",
  "var": "x",
  "point": "0",
  "direction": "+-"
}
```"""

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": b64_data,
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 600,
        }
    }

    models_to_try = [model]
    for fb in FALLBACK_MODELS:
        if fb not in models_to_try:
            models_to_try.append(fb)

    last_error = ""
    for target_model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={api_key.strip()}"
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=payload)

            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts and "text" in parts[0]:
                        raw_text = parts[0]["text"]
                        # Extract JSON
                        m = re.search(r"\{[^{}]*\"expr\"[^{}]*\}", raw_text, re.DOTALL)
                        if m:
                            parsed_json = json.loads(m.group(0))
                            return {
                                "success": True,
                                "expr": str(parsed_json.get("expr", "")).strip(),
                                "var": str(parsed_json.get("var", "x")).strip() or "x",
                                "point": str(parsed_json.get("point", "0")).strip() or "0",
                                "direction": str(parsed_json.get("direction", "+-")).strip() or "+-",
                                "model": target_model,
                            }
                        else:
                            last_error = "Модель не смогла разобрать формулу в JSON."
            elif resp.status_code in (404, 429, 503):
                last_error = f"Модель {target_model} занята ({resp.status_code})."
                continue
            else:
                last_error = f"Ошибка Gemini API: {resp.status_code}"
                continue
        except Exception as e:
            last_error = str(e)
            continue

    return {
        "success": False,
        "error": f"Не удалось распознать предел на изображении: {last_error}",
    }


def check_user_solution(
    expr: str,
    var: str,
    point: str,
    direction: str,
    user_solution_step: str,
    api_key: str = "",
    model: str = DEFAULT_MODEL,
    timeout: float = 25.0,
) -> Dict[str, Any]:
    """
    AI Tutor feature: evaluates student's manual solution attempt,
    flags lost minuses, illegal algebraic substitutions, and gives actionable hints.
    """
    if not api_key or not api_key.strip():
        return {
            "success": False,
            "error": "Для работы AI-репетитора требуется указать бесплатный ключ Gemini API.",
        }

    prompt = f"""Ты — чуткий преподаватель математического анализа и репетитор.
Студент решает следующий предел:
lim ({var} → {point}) [ {expr} ]

Студент прислал свой ход решения или ответ:
\"\"\"{user_solution_step}\"\"\"

Твоя задача как репетитора:
1. Оценить правильность хода мысли студента (Верно / Содержит ошибку / Частично верно).
2. Если есть ошибка, точно и доброжелательно укажи на неё (например: потерянный минус, неправильно взятая производная, незаконное применение эквивалентности не в окрестности нуля, деление на ноль).
3. Дай студенту подсказку, как исправить эту строчку и продвинуться к верному ответу.
4. Отвечай кратко, понятно и ободряюще на русском языке в Markdown."""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key.strip()}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1200},
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload)
        if resp.status_code == 200:
            candidates = resp.json().get("candidates", [])
            if candidates:
                return {
                    "success": True,
                    "review": candidates[0]["content"]["parts"][0]["text"],
                    "model": model,
                }
        return {"success": False, "error": f"Ошибка ответа Gemini: {resp.status_code}"}
    except Exception as e:
        return {"success": False, "error": f"Ошибка проверки решения: {str(e)}"}
