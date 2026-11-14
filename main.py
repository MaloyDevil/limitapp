"""
LimitApp - Мобильный калькулятор математических пределов
Создатель: Нарницкий Роман (никнейм Syrok)
Стек: Python, SymPy, Flet (Material 3 / Flutter Engine), Google Gemini API
Версия: 1.4.0
"""

import sys
import os
import json
import random
import webbrowser
from datetime import datetime
import flet as ft

import engine
import presets
import gemini_solver

_base_dir = os.path.dirname(os.path.abspath(__file__))
ICON_PNG = os.path.join(_base_dir, "icon.png") if os.path.exists(os.path.join(_base_dir, "icon.png")) else os.path.join(_base_dir, "assets", "icon.png")
ICON_ICO = os.path.join(_base_dir, "icon.ico") if os.path.exists(os.path.join(_base_dir, "icon.ico")) else os.path.join(_base_dir, "assets", "icon.ico")
ICON_PATH = ICON_PNG if os.path.exists(ICON_PNG) else (ICON_ICO if os.path.exists(ICON_ICO) else "")

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".limitapp_config.json")


class LimitApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.history = []
        self.history_filter = "all"  # "all" or "fav"
        self.handbook_search_query = ""
        self.active_keypad_tab = "basic"  # "basic" or "func"

        # Load configuration (Gemini API key & selected model)
        self.gemini_api_key, self.gemini_model = self.load_config()

        # Configure window & page
        self.page.title = "LimitApp | Калькулятор Пределов"
        if hasattr(self.page, "window"):
            self.page.window.width = 430
            self.page.window.height = 880
            self.page.window.min_width = 360
            self.page.window.min_height = 640
            self.page.window.resizable = True
            try:
                if os.path.exists(ICON_ICO):
                    self.page.window.icon = ICON_ICO
                elif os.path.exists(ICON_PNG):
                    self.page.window.icon = ICON_PNG
            except Exception:
                pass

        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 0

        # Live Math preview label
        self.live_preview_text = ft.Text(
            "lim (x → 0) [ sin(x)/x ]",
            size=15,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.PRIMARY,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

        # UI Controls for Calculator
        self.expr_input = ft.TextField(
            label="Функция f(x)",
            hint_text="Например: sin(x)/x, (1-cos(x))/x^2 или lim(x->0)",
            value="sin(x)/x",
            prefix_icon=ft.Icons.FUNCTIONS,
            border=ft.OutlineInputBorder(border_radius=12),
            autofocus=True,
            expand=True,
            on_change=self.on_input_changed,
            on_submit=self.on_calculate_click,
        )

        self.var_input = ft.TextField(
            label="Перем.",
            value="x",
            width=80,
            text_align=ft.TextAlign.CENTER,
            border=ft.OutlineInputBorder(border_radius=12),
            on_change=self.on_input_changed,
        )

        self.point_input = ft.TextField(
            label="Стремится к (x₀)",
            value="0",
            hint_text="0, oo, -oo, 1, pi...",
            border=ft.OutlineInputBorder(border_radius=12),
            expand=True,
            on_change=self.on_input_changed,
            on_submit=self.on_calculate_click,
        )

        self.dir_dropdown = ft.Dropdown(
            label="Направление",
            value="+-",
            border=ft.OutlineInputBorder(border_radius=12),
            options=[
                ft.dropdown.Option("+-", "Двусторонний (x → x₀)"),
                ft.dropdown.Option("+", "Справа (x → x₀⁺)"),
                ft.dropdown.Option("-", "Слева (x → x₀⁻)"),
            ],
            expand=True,
            on_select=self.on_input_changed,
        )

        # Result display container
        self.result_container = ft.Column(spacing=12, visible=False)

        # Tab views
        self.calc_view = self.build_calculator_view()
        self.handbook_view = self.build_handbook_view()
        self.history_view = self.build_history_view()
        self.about_view = self.build_about_view()

        # View container for swapping tabs
        self.content_container = ft.Container(
            content=self.calc_view,
            expand=True,
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
        )

        # Mobile Bottom Navigation Bar
        self.nav_bar = ft.NavigationBar(
            selected_index=0,
            on_change=self.on_nav_change,
            destinations=[
                ft.NavigationBarDestination(
                    icon=ft.Icons.CALCULATE_OUTLINED,
                    selected_icon=ft.Icons.CALCULATE,
                    label="Калькулятор",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.MENU_BOOK_OUTLINED,
                    selected_icon=ft.Icons.MENU_BOOK,
                    label="Справочник",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.HISTORY_OUTLINED,
                    selected_icon=ft.Icons.HISTORY,
                    label="История",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.PERSON_OUTLINED,
                    selected_icon=ft.Icons.PERSON,
                    label="Автор",
                ),
            ],
        )

        # App Bar
        self.theme_btn = ft.IconButton(
            icon=ft.Icons.LIGHT_MODE,
            tooltip="Сменить тему оформления",
            on_click=self.toggle_theme,
        )

        leading_control = (
            ft.Container(
                content=ft.Image(
                    src=ICON_PNG,
                    width=28,
                    height=28,
                    fit=ft.BoxFit.CONTAIN,
                ),
                bgcolor=ft.Colors.INDIGO_900,
                border_radius=8,
                padding=3,
                width=34,
                height=34,
                alignment=ft.Alignment.CENTER,
            )
            if os.path.exists(ICON_PNG)
            else ft.Icon(ft.Icons.ALL_INCLUSIVE, color=ft.Colors.AMBER_400)
        )

        self.app_bar = ft.AppBar(
            leading=ft.Container(
                content=leading_control,
                padding=ft.Padding.only(left=12, top=6, bottom=6),
            ),
            title=ft.Row(
                spacing=8,
                controls=[
                    ft.Text("LimitApp", weight=ft.FontWeight.BOLD, size=19),
                    ft.Container(
                        content=ft.Text("AI PRO", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        bgcolor=ft.Colors.INDIGO_600,
                        padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                        border_radius=8,
                    ),
                ],
                tight=True,
            ),
            actions=[
                ft.IconButton(
                    icon=ft.Icons.CASINO_OUTLINED,
                    tooltip="Случайный пример",
                    on_click=self.load_random_example,
                ),
                ft.IconButton(
                    icon=ft.Icons.AUTO_AWESOME,
                    tooltip="Настройки Gemini AI",
                    on_click=self.open_gemini_settings,
                ),
                self.theme_btn,
            ],
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            elevation=2,
        )

        self.page.appbar = self.app_bar
        self.page.navigation_bar = self.nav_bar
        self.page.add(self.content_container)

    # -------------------------------------------------------------
    # Configuration / Gemini API key storage
    # -------------------------------------------------------------
    def load_config(self) -> tuple[str, str]:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        model = gemini_solver.DEFAULT_MODEL
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    api_key = cfg.get("gemini_api_key", api_key)
                    model = cfg.get("gemini_model", model)
            except Exception:
                pass
        return api_key, model

    def save_config(self, api_key: str, model: str):
        self.gemini_api_key = api_key.strip()
        self.gemini_model = model.strip()
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"gemini_api_key": self.gemini_api_key, "gemini_model": self.gemini_model}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def open_gemini_settings(self, e=None):
        api_field = ft.TextField(
            label="Google Gemini API Key",
            value=self.gemini_api_key,
            password=True,
            can_reveal_password=True,
            border=ft.OutlineInputBorder(border_radius=12),
            prefix_icon=ft.Icons.KEY,
            hint_text="AIzaSy...",
            helper_text="Бесплатный ключ из Google AI Studio",
        )

        model_dropdown = ft.Dropdown(
            label="Модель нейросети",
            value=self.gemini_model or gemini_solver.DEFAULT_MODEL,
            border=ft.OutlineInputBorder(border_radius=12),
            options=[ft.dropdown.Option(m_id, m_label) for m_id, m_label in gemini_solver.GEMINI_MODELS],
        )

        status_text = ft.Text("", size=12, italic=True)

        def on_open_ai_studio(ev):
            try:
                webbrowser.open("https://aistudio.google.com/app/apikey")
            except Exception:
                pass

        def on_test_key(ev):
            test_key = (api_field.value or "").strip()
            if not test_key:
                status_text.value = "⚠️ Введите ключ для проверки"
                status_text.color = ft.Colors.AMBER_400
                self.page.update()
                return

            status_text.value = "⏳ Проверка подключения к Gemini API..."
            status_text.color = ft.Colors.PRIMARY
            self.page.update()

            def test_worker():
                res = gemini_solver.solve_limit_with_gemini(
                    expr="x",
                    var="x",
                    point="0",
                    direction="+-",
                    api_key=test_key,
                    model=model_dropdown.value or gemini_solver.DEFAULT_MODEL,
                    timeout=12.0,
                )
                if res["success"]:
                    status_text.value = "✅ Ключ активен! Соединение успешно установлено."
                    status_text.color = ft.Colors.GREEN_400
                else:
                    err = res.get("error", "Ошибка соединения")
                    status_text.value = f"❌ {err}"
                    status_text.color = ft.Colors.RED_400
                self.page.update()

            self.page.run_thread(test_worker)

        def on_save(ev):
            new_key = (api_field.value or "").strip()
            new_model = model_dropdown.value or gemini_solver.DEFAULT_MODEL
            self.save_config(new_key, new_model)
            self.page.pop_dialog()
            self.show_toast("Настройки Gemini AI сохранены! ✨")

        def on_close(ev):
            self.page.pop_dialog()

        dialog = ft.AlertDialog(
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.AUTO_AWESOME, color=ft.Colors.AMBER_400, size=24),
                    ft.Text("Настройки Gemini AI", weight=ft.FontWeight.BOLD, size=17),
                ],
                spacing=8,
                tight=True,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "Для автоматического решения пределов с подробным преподавательским объяснением "
                            "используется официальный бесплатный API Google Gemini.",
                            size=12,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        api_field,
                        ft.FilledTonalButton(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.OPEN_IN_NEW, size=16),
                                    ft.Text("Получить бесплатный ключ (AI Studio)", size=12),
                                ],
                                spacing=6,
                                tight=True,
                            ),
                            url="https://aistudio.google.com/app/apikey",
                            on_click=on_open_ai_studio,
                        ),
                        model_dropdown,
                        ft.Row(
                            controls=[
                                ft.OutlinedButton(
                                    content=ft.Row(
                                        controls=[ft.Icon(ft.Icons.NETWORK_CHECK, size=15), ft.Text("Проверить ключ", size=12)],
                                        spacing=4,
                                        tight=True,
                                    ),
                                    on_click=on_test_key,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.START,
                        ),
                        status_text,
                    ],
                    spacing=12,
                    tight=True,
                ),
                width=380,
            ),
            actions=[
                ft.TextButton("Закрыть", on_click=on_close),
                ft.FilledButton("Сохранить", on_click=on_save),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.show_dialog(dialog)

    # -------------------------------------------------------------
    # Navigation & General Handlers
    # -------------------------------------------------------------
    def toggle_theme(self, e):
        if self.page.theme_mode == ft.ThemeMode.DARK:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.theme_btn.icon = ft.Icons.DARK_MODE
        else:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.theme_btn.icon = ft.Icons.LIGHT_MODE
        self.page.update()

    def show_toast(self, message: str):
        try:
            self.page.show_dialog(ft.SnackBar(ft.Text(message)))
        except Exception:
            pass

    def on_nav_change(self, e):
        idx = self.nav_bar.selected_index
        if idx == 0:
            self.content_container.content = self.calc_view
        elif idx == 1:
            self.content_container.content = self.build_handbook_view()
        elif idx == 2:
            self.content_container.content = self.build_history_view()
        elif idx == 3:
            self.content_container.content = self.build_about_view()
        self.page.update()

    def on_input_changed(self, e=None):
        self.update_live_preview()

    def update_live_preview(self):
        expr = (self.expr_input.value or "f(x)").strip()
        var = (self.var_input.value or "x").strip()
        pt = (self.point_input.value or "0").strip()
        d = self.dir_dropdown.value or "+-"

        d_str = ""
        if d == "+":
            d_str = "⁺"
        elif d == "-":
            d_str = "⁻"

        pt_display = pt.replace("oo", "∞").replace("pi", "π")
        self.live_preview_text.value = f"lim ({var} → {pt_display}{d_str})  [ {expr} ]"
        try:
            self.page.update()
        except Exception:
            pass

    def insert_symbol(self, sym: str):
        if sym == "CLEAR":
            self.expr_input.value = ""
        elif sym == "BACK":
            val = self.expr_input.value or ""
            known_tokens = [
                "arcsin(", "arccos(", "arcctg(", "arctg(", "sinh(", "cosh(", "tanh(",
                "sin(", "cos(", "tan(", "cot(", "ctg(",
                "sqrt(", "cbrt(", "abs(", "exp(", "log(", "ln(", "lg(",
                "oo", "pi",
            ]
            deleted = False
            for token in known_tokens:
                if val.endswith(token):
                    self.expr_input.value = val[:-len(token)]
                    deleted = True
                    break
            if not deleted and val:
                self.expr_input.value = val[:-1]
        elif sym == "x^2":
            self.expr_input.value = (self.expr_input.value or "") + "^2"
        elif sym == "x^3":
            self.expr_input.value = (self.expr_input.value or "") + "^3"
        elif sym == "1/x":
            self.expr_input.value = (self.expr_input.value or "") + "1/("
        elif sym == "e^x":
            self.expr_input.value = (self.expr_input.value or "") + "exp("
        else:
            self.expr_input.value = (self.expr_input.value or "") + sym
        self._focus_control(self.expr_input)
        self.update_live_preview()

    def apply_template(self, expr_template: str, var="x", point="0", direction="+-"):
        self.expr_input.value = expr_template
        self.var_input.value = var
        self.point_input.value = point
        self.dir_dropdown.value = direction
        self._focus_control(self.expr_input)
        self.update_live_preview()
        self.show_toast(f"Шаблон вставлен: {expr_template}")

    def select_variable(self, v: str):
        self.var_input.value = v
        # Sequence limits typically tend to infinity
        if v == "n" and self.point_input.value == "0":
            self.point_input.value = "oo"
        self._focus_control(self.var_input)
        self.update_live_preview()

    def insert_point(self, val: str):
        self.point_input.value = val
        self._focus_control(self.point_input)
        self.update_live_preview()

    def select_direction(self, d: str):
        self.dir_dropdown.value = d
        self.update_live_preview()

    def _focus_control(self, ctrl):
        try:
            res = ctrl.focus()
            if hasattr(res, "close"):
                res.close()
        except Exception:
            pass

    def load_random_example(self, e=None):
        all_items = []
        for cat in presets.CATEGORIES:
            all_items.extend(cat["items"])
        if all_items:
            p = random.choice(all_items)
            self.load_preset(p)
            self.show_toast(f"🎲 Пример: {p['title']}")

    def clear_inputs(self, e=None):
        self.expr_input.value = ""
        self.var_input.value = "x"
        self.point_input.value = "0"
        self.dir_dropdown.value = "+-"
        self.result_container.visible = False
        self.update_live_preview()
        self.show_toast("Поля очищены")

    def make_key(self, code: str, label: str, ktype: str) -> ft.Control:
        if len(label) >= 6:
            font_size = 9.5
        elif len(label) >= 4:
            font_size = 11.0
        elif len(label) >= 2:
            font_size = 12.5
        else:
            font_size = 15.0

        if ktype == "clear":
            content = ft.Text(label, weight=ft.FontWeight.BOLD, size=13, color=ft.Colors.ON_ERROR_CONTAINER, no_wrap=True)
            bgcolor = ft.Colors.ERROR_CONTAINER
            border = ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)
        elif ktype == "back":
            content = ft.Icon(ft.Icons.BACKSPACE_OUTLINED, size=17, color=ft.Colors.ON_SECONDARY_CONTAINER)
            bgcolor = ft.Colors.SECONDARY_CONTAINER
            border = ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)
        elif ktype == "var":
            content = ft.Text(label, weight=ft.FontWeight.BOLD, italic=True, size=font_size, color=ft.Colors.ON_PRIMARY_CONTAINER, no_wrap=True)
            bgcolor = ft.Colors.PRIMARY_CONTAINER
            border = ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)
        elif ktype == "func":
            content = ft.Text(label, weight=ft.FontWeight.W_600, size=font_size, color=ft.Colors.PRIMARY, no_wrap=True)
            bgcolor = ft.Colors.SURFACE_CONTAINER_HIGH
            border = ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)
        elif ktype == "num":
            content = ft.Text(label, weight=ft.FontWeight.BOLD, size=15, color=ft.Colors.ON_SURFACE, no_wrap=True)
            bgcolor = ft.Colors.SURFACE_CONTAINER_HIGHEST
            border = ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)
        else:  # "op"
            content = ft.Text(label, weight=ft.FontWeight.BOLD, size=font_size, color=ft.Colors.ON_SURFACE, no_wrap=True)
            bgcolor = ft.Colors.SURFACE_CONTAINER_HIGHEST
            border = ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)

        return ft.Container(
            content=content,
            alignment=ft.Alignment.CENTER,
            height=38,
            expand=1,
            bgcolor=bgcolor,
            border_radius=8,
            border=border,
            padding=ft.Padding.symmetric(horizontal=1),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            ink=True,
            on_click=lambda e, s=code: self.insert_symbol(s),
        )

    # -------------------------------------------------------------
    # Calculator View Builder
    # -------------------------------------------------------------
    def build_calculator_view(self) -> ft.Control:
        # 1. Formula Template Quick Chips
        template_chips_data = [
            ("a / b", "(x) / (x)", "Дробь"),
            ("√x", "sqrt(x)", "Корень"),
            ("xⁿ", "x^(2)", "Степень"),
            ("|x|", "abs(x)", "Модуль"),
            ("sin(x)/x", "sin(x)/x", "1-й замечательный"),
            ("(1+1/x)ˣ", "(1 + 1/x)^x", "2-й замечательный (∞)"),
            ("(1+x)^(1/x)", "(1 + x)^(1/x)", "2-й замечательный (0)"),
            ("(eˣ-1)/x", "(exp(x) - 1)/x", "Экспонента"),
            ("ln(1+x)/x", "ln(1 + x)/x", "Логарифм"),
            ("(1-cos(x))/x²", "(1 - cos(x))/x^2", "Тригонометрия"),
            ("tg(x)", "tan(x)", "Тангенс"),
            ("n!", "n!", "Факториал"),
        ]

        template_chips = []
        for label, tmpl, tip in template_chips_data:
            chip = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.AUTO_AWESOME, size=12, color=ft.Colors.AMBER_400),
                        ft.Text(label, size=11, weight=ft.FontWeight.BOLD, no_wrap=True),
                    ],
                    spacing=4,
                    tight=True,
                ),
                padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                border_radius=8,
                border=ft.Border.all(0.8, ft.Colors.OUTLINE_VARIANT),
                tooltip=tip,
                ink=True,
                on_click=lambda e, t=tmpl: self.apply_template(t),
            )
            template_chips.append(chip)

        template_scroll_row = ft.Row(
            controls=template_chips,
            spacing=6,
            scroll=ft.ScrollMode.ADAPTIVE,
        )

        # 2. Keypad Rows
        # Tab 1: 🔢 123 / Алгебра
        basic_r1 = [("x", "x", "var"), ("n", "n", "var"), ("(", "(", "op"), (")", ")", "op"), ("CLEAR", "C", "clear")]
        basic_r2 = [("7", "7", "num"), ("8", "8", "num"), ("9", "9", "num"), ("/", "÷", "op"), ("BACK", "⌫", "back")]
        basic_r3 = [("4", "4", "num"), ("5", "5", "num"), ("6", "6", "num"), ("*", "×", "op"), ("^", "^", "op")]
        basic_r4 = [("1", "1", "num"), ("2", "2", "num"), ("3", "3", "num"), ("-", "−", "op"), ("sqrt(", "√", "func")]
        basic_r5 = [("0", "0", "num"), (".", ".", "num"), (",", ",", "num"), ("+", "+", "op"), ("abs(", "|x|", "func")]

        # Tab 2: 📐 f(x) Функции
        func_r1 = [("sin(", "sin", "func"), ("cos(", "cos", "func"), ("tan(", "tg", "func"), ("cot(", "ctg", "func"), ("pi", "π", "var")]
        func_r2 = [("arcsin(", "arcsin", "func"), ("arccos(", "arccos", "func"), ("atan(", "arctg", "func"), ("acot(", "arcctg", "func"), ("e", "e", "var")]
        func_r3 = [("ln(", "ln", "func"), ("lg(", "lg", "func"), ("log(", "log", "func"), ("exp(", "exp", "func"), ("oo", "∞", "var")]
        func_r4 = [("sinh(", "sh", "func"), ("cosh(", "ch", "func"), ("tanh(", "th", "func"), ("!", "n!", "op"), ("BACK", "⌫", "back")]
        func_r5 = [("x^2", "x²", "func"), ("x^3", "x³", "func"), ("1/x", "1/x", "func"), ("e^x", "eˣ", "func"), ("CLEAR", "C", "clear")]

        self.basic_keys_col = ft.Column(
            controls=[
                ft.Row(controls=[self.make_key(c, l, t) for c, l, t in basic_r1], spacing=5),
                ft.Row(controls=[self.make_key(c, l, t) for c, l, t in basic_r2], spacing=5),
                ft.Row(controls=[self.make_key(c, l, t) for c, l, t in basic_r3], spacing=5),
                ft.Row(controls=[self.make_key(c, l, t) for c, l, t in basic_r4], spacing=5),
                ft.Row(controls=[self.make_key(c, l, t) for c, l, t in basic_r5], spacing=5),
            ],
            spacing=5,
            visible=True,
        )

        self.func_keys_col = ft.Column(
            controls=[
                ft.Row(controls=[self.make_key(c, l, t) for c, l, t in func_r1], spacing=5),
                ft.Row(controls=[self.make_key(c, l, t) for c, l, t in func_r2], spacing=5),
                ft.Row(controls=[self.make_key(c, l, t) for c, l, t in func_r3], spacing=5),
                ft.Row(controls=[self.make_key(c, l, t) for c, l, t in func_r4], spacing=5),
                ft.Row(controls=[self.make_key(c, l, t) for c, l, t in func_r5], spacing=5),
            ],
            spacing=5,
            visible=False,
        )

        def switch_tab(tab_name: str):
            self.active_keypad_tab = tab_name
            self.basic_keys_col.visible = (tab_name == "basic")
            self.func_keys_col.visible = (tab_name == "func")
            tab_basic_btn.bgcolor = ft.Colors.PRIMARY_CONTAINER if tab_name == "basic" else ft.Colors.SURFACE_CONTAINER_HIGH
            tab_func_btn.bgcolor = ft.Colors.PRIMARY_CONTAINER if tab_name == "func" else ft.Colors.SURFACE_CONTAINER_HIGH
            self.page.update()

        tab_basic_btn = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.PIN, size=15),
                    ft.Text("123 / Алгебра", size=12, weight=ft.FontWeight.BOLD),
                ],
                spacing=4,
                tight=True,
            ),
            padding=ft.Padding.symmetric(horizontal=12, vertical=6),
            bgcolor=ft.Colors.PRIMARY_CONTAINER,
            border_radius=8,
            ink=True,
            on_click=lambda e: switch_tab("basic"),
        )

        tab_func_btn = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.FUNCTIONS, size=15),
                    ft.Text("f(x) Функции", size=12, weight=ft.FontWeight.BOLD),
                ],
                spacing=4,
                tight=True,
            ),
            padding=ft.Padding.symmetric(horizontal=12, vertical=6),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            border_radius=8,
            ink=True,
            on_click=lambda e: switch_tab("func"),
        )

        keypad_container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Row(controls=[tab_basic_btn, tab_func_btn], spacing=6, tight=True),
                            ft.TextButton(
                                content=ft.Row(
                                    controls=[ft.Icon(ft.Icons.CLEAR_ALL, size=15), ft.Text("Очистить", size=11)],
                                    spacing=4,
                                    tight=True,
                                ),
                                style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=6, vertical=2)),
                                on_click=self.clear_inputs,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    self.basic_keys_col,
                    self.func_keys_col,
                ],
                spacing=8,
            ),
            padding=10,
            border_radius=14,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        )

        # 3. Variable selector chips
        var_chips = []
        for v in ["x", "n", "t", "y"]:
            chip = ft.Container(
                content=ft.Text(v, size=12, weight=ft.FontWeight.BOLD, italic=True),
                padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                border_radius=8,
                border=ft.Border.all(0.8, ft.Colors.OUTLINE_VARIANT),
                ink=True,
                on_click=lambda e, var_val=v: self.select_variable(var_val),
            )
            var_chips.append(chip)

        # 4. Point chips
        quick_points = [
            ("0", "0"),
            ("oo", "+∞"),
            ("-oo", "-∞"),
            ("1", "1"),
            ("-1", "-1"),
            ("pi", "π"),
            ("pi/2", "π/2"),
            ("e", "e"),
        ]
        point_chips = []
        for val, label in quick_points:
            chip = ft.Container(
                content=ft.Text(label, size=12, weight=ft.FontWeight.W_600, color=ft.Colors.ON_PRIMARY_CONTAINER),
                padding=ft.Padding.symmetric(horizontal=9, vertical=4),
                bgcolor=ft.Colors.PRIMARY_CONTAINER,
                border_radius=8,
                border=ft.Border.all(0.8, ft.Colors.OUTLINE_VARIANT),
                ink=True,
                on_click=lambda e, v=val: self.insert_point(v),
            )
            point_chips.append(chip)

        # Direction Chips
        dir_chips = []
        for d_code, d_label in [("+-", "x → x₀"), ("+", "x → x₀⁺"), ("-", "x → x₀⁻")]:
            chip = ft.Container(
                content=ft.Text(d_label, size=11, weight=ft.FontWeight.W_600),
                padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                border_radius=8,
                border=ft.Border.all(0.8, ft.Colors.OUTLINE_VARIANT),
                ink=True,
                on_click=lambda e, code=d_code: self.select_direction(code),
            )
            dir_chips.append(chip)

        # 5. Primary Calculate Buttons
        calc_btn = ft.FilledButton(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.FLASH_ON, color=ft.Colors.AMBER_300, size=18),
                    ft.Text("Рассчитать", weight=ft.FontWeight.BOLD, size=14),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                tight=True,
            ),
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.INDIGO_600,
                color=ft.Colors.WHITE,
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.Padding.symmetric(vertical=12, horizontal=8),
            ),
            expand=3,
            on_click=self.on_calculate_click,
        )

        gemini_btn = ft.FilledTonalButton(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.AUTO_AWESOME, color=ft.Colors.AMBER_400, size=18),
                    ft.Text("Gemini AI", weight=ft.FontWeight.BOLD, size=14),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                tight=True,
            ),
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.Padding.symmetric(vertical=12, horizontal=8),
            ),
            expand=3,
            tooltip="Решить с подробным объяснением от Google Gemini AI",
            on_click=self.on_gemini_solve_click,
        )

        gemini_cfg_btn = ft.IconButton(
            icon=ft.Icons.SETTINGS,
            tooltip="Настройки Gemini API",
            on_click=self.open_gemini_settings,
        )

        return ft.ListView(
            expand=True,
            spacing=12,
            controls=[
                ft.Container(
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            # Header with action chips
                            ft.Row(
                                controls=[
                                    ft.Row(
                                        controls=[
                                            ft.Icon(ft.Icons.AUTO_AWESOME, size=16, color=ft.Colors.AMBER_400),
                                            ft.Text("Быстрые шаблоны задач:", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE_VARIANT),
                                        ],
                                        spacing=4,
                                        tight=True,
                                    ),
                                    ft.TextButton(
                                        content=ft.Row(
                                            [ft.Icon(ft.Icons.CASINO_OUTLINED, size=15), ft.Text("Пример", size=11)],
                                            spacing=4,
                                            tight=True,
                                        ),
                                        style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=6, vertical=2)),
                                        on_click=self.load_random_example,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),

                            # Horizontal scrolling template chips
                            template_scroll_row,

                            # Live Formula Preview Card
                            ft.Container(
                                content=ft.Row(
                                    controls=[
                                        ft.Icon(ft.Icons.AUTO_GRAPH, size=18, color=ft.Colors.PRIMARY),
                                        self.live_preview_text,
                                    ],
                                    spacing=8,
                                    tight=True,
                                ),
                                padding=ft.Padding.symmetric(horizontal=12, vertical=10),
                                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                                border_radius=10,
                                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                            ),

                            # Input Fields
                            ft.Row(controls=[self.expr_input, self.var_input], spacing=8),

                            # Variable selector chips
                            ft.Row(
                                controls=[
                                    ft.Text("Переменная:", size=11, weight=ft.FontWeight.W_600, color=ft.Colors.ON_SURFACE_VARIANT),
                                    *var_chips,
                                ],
                                spacing=6,
                                tight=True,
                            ),

                            # Tabbed Ergonomic Keyboard
                            keypad_container,

                            ft.Divider(height=1, thickness=0.5),

                            # Limit Parameters (x0, direction)
                            ft.Text("Точка стремления и направление", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Row(controls=[self.point_input, self.dir_dropdown], spacing=8),

                            # Point chips
                            ft.Row(
                                controls=[
                                    ft.Text("x₀:", size=12, weight=ft.FontWeight.W_600, color=ft.Colors.ON_SURFACE_VARIANT),
                                    *point_chips,
                                ],
                                spacing=6,
                                wrap=True,
                            ),

                            # Quick direction chips
                            ft.Row(
                                controls=[
                                    ft.Text("Знак:", size=11, weight=ft.FontWeight.W_600, color=ft.Colors.ON_SURFACE_VARIANT),
                                    *dir_chips,
                                ],
                                spacing=6,
                                tight=True,
                            ),

                            ft.Container(height=4),

                            # Action buttons row
                            ft.Row(
                                controls=[
                                    calc_btn,
                                    gemini_btn,
                                    gemini_cfg_btn,
                                ],
                                spacing=8,
                            ),
                        ],
                    ),
                    padding=16,
                    border_radius=16,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                    border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                ),
                self.result_container,
            ],
        )

    # -------------------------------------------------------------
    # SymPy Analytical Limit Calculation
    # -------------------------------------------------------------
    def on_calculate_click(self, e):
        raw_expr = self.expr_input.value.strip() if self.expr_input.value else ""
        if not raw_expr:
            self.show_toast("Пожалуйста, введите функцию f(x)")
            return

        # Check if user pasted a complete limit notation
        parsed_full = engine.parse_full_limit(raw_expr)
        if parsed_full:
            self.expr_input.value = parsed_full["expr"]
            self.var_input.value = parsed_full["var"]
            self.point_input.value = parsed_full["point"]
            self.dir_dropdown.value = parsed_full["direction"]
            self.update_live_preview()

        expr_text = self.expr_input.value.strip()
        var_text = self.var_input.value.strip() if self.var_input.value else "x"
        point_text = self.point_input.value.strip() if self.point_input.value else "0"
        dir_val = self.dir_dropdown.value or "+-"

        res = engine.solve_limit(expr_text, var_text, point_text, dir_val)

        if not res["success"]:
            self.result_container.visible = True
            self.result_container.controls = [
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED_400),
                                        ft.Text("Не удалось вычислить предел", weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400),
                                    ],
                                    tight=True,
                                ),
                                ft.Text(res.get("error", "Проверьте синтаксис ввода.")),
                            ],
                            spacing=8,
                        ),
                        padding=16,
                    ),
                    color=ft.Colors.ERROR_CONTAINER,
                )
            ]
            self.page.update()
            return

        # Render successful results
        self.render_result(res)

        # Add to history
        self.history.insert(0, {
            "id": datetime.now().timestamp(),
            "time": datetime.now().strftime("%H:%M:%S"),
            "expr": expr_text,
            "var": var_text,
            "point": point_text,
            "dir": dir_val,
            "result": res["result_display"],
            "favorite": False,
        })
        if len(self.history) > 50:
            self.history.pop()

        self.page.update()

    def render_result(self, res: dict):
        self.result_container.visible = True
        self.result_container.controls.clear()

        var = res["var"]
        pt = res["point_display"]
        dir_char = ""
        if res["direction"] == "+":
            dir_char = "⁺"
        elif res["direction"] == "-":
            dir_char = "⁻"

        lim_notation = f"lim ({var} → {pt}{dir_char})  [{res['expr_display']}]"
        ans_text = res["result_display"]
        numeric_text = res.get("numeric_display")

        header_items = [
            ft.Row(
                controls=[
                    ft.Text(lim_notation, size=13, color=ft.Colors.ON_SURFACE_VARIANT, italic=True),
                    ft.Container(
                        content=ft.Text("Аналитическое решение", size=10, weight=ft.FontWeight.W_600, color=ft.Colors.GREEN_400),
                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                        padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                        border_radius=6,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Text("= ", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
                        ft.Text(ans_text, size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
                        ft.Text(f" ({numeric_text})" if numeric_text else "", size=15, color=ft.Colors.ON_SURFACE_VARIANT),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    tight=True,
                ),
                padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                border_radius=10,
                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            ),
        ]

        if res.get("indeterminacy"):
            header_items.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, size=16, color=ft.Colors.AMBER_400),
                            ft.Text(f"Неопределенность {res['indeterminacy']}", weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_400, size=13),
                        ],
                        spacing=6,
                        tight=True,
                    ),
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                    border_radius=8,
                )
            )

        if res.get("left_limit") and res.get("right_limit"):
            header_items.append(
                ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Text(f"Слева: {res['left_limit']}", size=12),
                            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                            border_radius=6,
                        ),
                        ft.Container(
                            content=ft.Text(f"Справа: {res['right_limit']}", size=12),
                            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                            border_radius=6,
                        ),
                    ],
                    spacing=8,
                    tight=True,
                )
            )

        def copy_result(e):
            full_text = f"{lim_notation} = {ans_text}\n"
            if res.get("indeterminacy"):
                full_text += f"Тип: {res['indeterminacy']}\n"
            for step in res.get("steps", []):
                full_text += f"\n{step['title']}:\n{step['desc']}\n"
            try:
                ft.Clipboard.set(full_text)
                self.show_toast("Решение скопировано в буфер!")
            except Exception:
                self.show_toast("Текст готов!")

        def toggle_favorite(e):
            if self.history:
                self.history[0]["favorite"] = not self.history[0].get("favorite", False)
                fav_btn.icon = ft.Icons.STAR if self.history[0]["favorite"] else ft.Icons.STAR_BORDER
                fav_btn.icon_color = ft.Colors.AMBER_400 if self.history[0]["favorite"] else None
                self.page.update()
                self.show_toast("Добавлено в избранное ⭐" if self.history[0]["favorite"] else "Удалено из избранного")

        fav_btn = ft.IconButton(
            icon=ft.Icons.STAR_BORDER,
            tooltip="Добавить в избранное",
            on_click=toggle_favorite,
        )

        copy_btn = ft.OutlinedButton(
            content=ft.Row(
                controls=[ft.Icon(ft.Icons.COPY, size=16), ft.Text("Скопировать", size=13)],
                spacing=6,
                tight=True,
            ),
            on_click=copy_result,
        )

        ai_deep_btn = ft.FilledTonalButton(
            content=ft.Row(
                controls=[ft.Icon(ft.Icons.AUTO_AWESOME, size=16, color=ft.Colors.AMBER_400), ft.Text("Объяснить с ИИ", size=13)],
                spacing=6,
                tight=True,
            ),
            on_click=self.on_gemini_solve_click,
        )

        header_items.append(
            ft.Row(
                controls=[fav_btn, copy_btn, ai_deep_btn],
                alignment=ft.MainAxisAlignment.END,
                spacing=6,
                tight=True,
            )
        )

        main_card = ft.Card(
            content=ft.Container(
                content=ft.Column(controls=header_items, spacing=10),
                padding=16,
            ),
            elevation=3,
        )
        self.result_container.controls.append(main_card)

        # Step-by-Step Breakdown Cards
        if res.get("steps"):
            step_controls = []
            for s in res["steps"]:
                step_controls.append(
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text(s["title"], weight=ft.FontWeight.BOLD, size=13, color=ft.Colors.PRIMARY),
                                ft.Text(s["desc"], size=12),
                            ],
                            spacing=4,
                        ),
                        padding=12,
                        border_radius=10,
                        bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                    )
                )

            steps_card = ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.RULE, color=ft.Colors.INDIGO_ACCENT),
                                    ft.Text("Подробный ход решения", weight=ft.FontWeight.BOLD, size=15),
                                ],
                                spacing=8,
                                tight=True,
                            ),
                            ft.Divider(height=1, thickness=0.5),
                            ft.Column(controls=step_controls, spacing=8),
                        ],
                        spacing=10,
                    ),
                    padding=16,
                )
            )
            self.result_container.controls.append(steps_card)

        # Neighborhood Convergence Table
        table_rows = res.get("table", [])
        if table_rows:
            table_controls = [
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(r["side"], size=11, color=ft.Colors.ON_SURFACE_VARIANT)),
                        ft.DataCell(ft.Text(r["x"], size=12, weight=ft.FontWeight.W_600)),
                        ft.DataCell(ft.Text(r["fx"], size=12, color=ft.Colors.PRIMARY)),
                    ]
                )
                for r in table_rows
            ]

            data_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Окрестность", size=12, weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text(f"{var}", size=12, weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text(f"f({var})", size=12, weight=ft.FontWeight.BOLD)),
                ],
                rows=table_controls,
                heading_row_height=36,
                data_row_min_height=32,
                data_row_max_height=36,
            )

            table_card = ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.TABLE_CHART_OUTLINED, color=ft.Colors.CYAN_400),
                                    ft.Text("Численное приближение к точке", weight=ft.FontWeight.BOLD, size=15),
                                ],
                                spacing=8,
                                tight=True,
                            ),
                            ft.Text("Демонстрация сходимости функции:", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Container(content=data_table, alignment=ft.Alignment.CENTER),
                        ],
                        spacing=8,
                    ),
                    padding=16,
                )
            )
            self.result_container.controls.append(table_card)

    # -------------------------------------------------------------
    # Google Gemini AI Solver Integration
    # -------------------------------------------------------------
    def on_gemini_solve_click(self, e=None):
        raw_expr = self.expr_input.value.strip() if self.expr_input.value else ""
        if not raw_expr:
            self.show_toast("Пожалуйста, введите функцию f(x)")
            return

        # Check API key
        if not (self.gemini_api_key or "").strip():
            self.show_toast("Введите бесплатный ключ Gemini API для решения через ИИ")
            self.open_gemini_settings()
            return

        # Check full limit expression syntax
        parsed_full = engine.parse_full_limit(raw_expr)
        if parsed_full:
            self.expr_input.value = parsed_full["expr"]
            self.var_input.value = parsed_full["var"]
            self.point_input.value = parsed_full["point"]
            self.dir_dropdown.value = parsed_full["direction"]
            self.update_live_preview()

        expr_text = self.expr_input.value.strip()
        var_text = self.var_input.value.strip() if self.var_input.value else "x"
        point_text = self.point_input.value.strip() if self.point_input.value else "0"
        dir_val = self.dir_dropdown.value or "+-"

        # Show loading indicator in result container
        self.result_container.visible = True
        self.result_container.controls = [
            ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.ProgressRing(width=22, height=22, stroke_width=2.5),
                                    ft.Text("Gemini AI составляет пошаговое математическое решение...", size=13, weight=ft.FontWeight.BOLD),
                                ],
                                spacing=12,
                                tight=True,
                            ),
                            ft.Text(
                                f"Модель: {self.gemini_model} • Вычисление аналитических преобразований и теорий...",
                                size=11,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                        ],
                        spacing=8,
                    ),
                    padding=16,
                ),
                elevation=2,
            )
        ]
        self.page.update()

        # Run async Gemini query via thread
        def gemini_worker():
            res = gemini_solver.solve_limit_with_gemini(
                expr=expr_text,
                var=var_text,
                point=point_text,
                direction=dir_val,
                api_key=self.gemini_api_key,
                model=self.gemini_model,
                timeout=30.0,
            )
            self.render_gemini_result(res, expr_text, var_text, point_text, dir_val)

        self.page.run_thread(gemini_worker)

    def render_gemini_result(self, res: dict, expr: str, var: str, point: str, direction: str):
        self.result_container.visible = True
        self.result_container.controls.clear()

        dir_char = ""
        if direction == "+":
            dir_char = "⁺"
        elif direction == "-":
            dir_char = "⁻"
        pt_display = point.replace("oo", "∞").replace("pi", "π")
        lim_title = f"lim ({var} → {pt_display}{dir_char}) [ {expr} ]"

        if not res["success"]:
            # Error card
            error_card = ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED_400),
                                    ft.Text("Ошибка решения Gemini AI", weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400, size=15),
                                ],
                                spacing=8,
                                tight=True,
                            ),
                            ft.Text(res.get("error", "Произошла ошибка при обращении к Gemini API."), size=12),
                            ft.Row(
                                controls=[
                                    ft.FilledButton(
                                        content=ft.Row(
                                            controls=[ft.Icon(ft.Icons.SETTINGS, size=16), ft.Text("Настроить API ключ", size=12)],
                                            spacing=6,
                                            tight=True,
                                        ),
                                        on_click=self.open_gemini_settings,
                                    ),
                                    ft.OutlinedButton(
                                        content=ft.Row(
                                            controls=[ft.Icon(ft.Icons.FLASH_ON, size=16), ft.Text("Решить через SymPy", size=12)],
                                            spacing=6,
                                            tight=True,
                                        ),
                                        on_click=self.on_calculate_click,
                                    ),
                                ],
                                spacing=8,
                            ),
                        ],
                        spacing=10,
                    ),
                    padding=16,
                ),
                color=ft.Colors.ERROR_CONTAINER,
            )
            self.result_container.controls.append(error_card)
            self.page.update()
            return

        # Success card with AI explanations
        ai_text = res.get("text", "")

        def copy_ai_text(e):
            try:
                ft.Clipboard.set(ai_text)
                self.show_toast("Объяснение Gemini AI скопировано в буфер!")
            except Exception:
                self.show_toast("Текст скопирован!")

        ai_header = ft.Row(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.AUTO_AWESOME, color=ft.Colors.AMBER_400, size=20),
                        ft.Text("Решение Google Gemini AI", weight=ft.FontWeight.BOLD, size=15),
                    ],
                    spacing=8,
                    tight=True,
                ),
                ft.Container(
                    content=ft.Text(res.get("model", "Gemini"), size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    bgcolor=ft.Colors.PURPLE_700,
                    padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                    border_radius=8,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        ai_toolbar = ft.Row(
            controls=[
                ft.OutlinedButton(
                    content=ft.Row(
                        controls=[ft.Icon(ft.Icons.COPY, size=15), ft.Text("Скопировать", size=12)],
                        spacing=4,
                        tight=True,
                    ),
                    on_click=copy_ai_text,
                ),
                ft.TextButton(
                    content=ft.Row(
                        controls=[ft.Icon(ft.Icons.REFRESH, size=15), ft.Text("Повторить", size=12)],
                        spacing=4,
                        tight=True,
                    ),
                    on_click=self.on_gemini_solve_click,
                ),
                ft.TextButton(
                    content=ft.Row(
                        controls=[ft.Icon(ft.Icons.FLASH_ON, size=15), ft.Text("Сверить с SymPy", size=12)],
                        spacing=4,
                        tight=True,
                    ),
                    on_click=self.on_calculate_click,
                ),
            ],
            spacing=6,
            tight=True,
        )

        md_view = ft.Markdown(
            value=ai_text,
            selectable=True,
            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
        )

        ai_card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ai_header,
                        ft.Text(lim_title, size=12, italic=True, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Divider(height=1, thickness=0.5),
                        md_view,
                        ft.Divider(height=1, thickness=0.5),
                        ai_toolbar,
                    ],
                    spacing=10,
                ),
                padding=16,
            ),
            elevation=3,
        )

        self.result_container.controls.append(ai_card)

        # Add to history
        self.history.insert(0, {
            "id": datetime.now().timestamp(),
            "time": datetime.now().strftime("%H:%M:%S"),
            "expr": expr,
            "var": var,
            "point": point,
            "dir": direction,
            "result": "Gemini AI Решение",
            "favorite": False,
        })
        if len(self.history) > 50:
            self.history.pop()

        self.page.update()

    # -------------------------------------------------------------
    # Handbook View
    # -------------------------------------------------------------
    def load_preset(self, p: dict):
        self.expr_input.value = p["expr"]
        self.var_input.value = p["var"]
        self.point_input.value = p["point"]
        self.dir_dropdown.value = p["dir"]
        self.update_live_preview()
        self.nav_bar.selected_index = 0
        self.content_container.content = self.calc_view
        self.page.update()
        self.on_calculate_click(None)

    def on_handbook_search_change(self, e):
        self.handbook_search_query = (e.control.value or "").strip().lower()
        self.content_container.content = self.build_handbook_view()
        self.page.update()

    def build_handbook_view(self) -> ft.Control:
        search_field = ft.TextField(
            hint_text="Поиск по справочнику (формула, функция, предел)...",
            value=self.handbook_search_query,
            prefix_icon=ft.Icons.SEARCH,
            border=ft.OutlineInputBorder(border_radius=12),
            dense=True,
            content_padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            on_change=self.on_handbook_search_change,
        )

        items = [search_field]
        q = self.handbook_search_query

        if q:
            matched_presets = []
            for cat in presets.CATEGORIES:
                for p in cat["items"]:
                    if q in p["title"].lower() or q in p["formula"].lower() or q in p["desc"].lower() or q in p["expr"].lower():
                        matched_presets.append((cat["category"], p))

            if matched_presets:
                items.append(ft.Text(f"Найдено примеров: {len(matched_presets)}", size=12, color=ft.Colors.PRIMARY, weight=ft.FontWeight.BOLD))
                for cat_name, p in matched_presets:
                    items.append(
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Row(
                                        controls=[
                                            ft.Text(p["title"], weight=ft.FontWeight.BOLD, size=13),
                                            ft.Container(
                                                content=ft.Text(f"= {p['result']}", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                                bgcolor=ft.Colors.INDIGO,
                                                padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                                                border_radius=6,
                                            ),
                                        ],
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    ),
                                    ft.Text(p["formula"], size=13, color=ft.Colors.PRIMARY, weight=ft.FontWeight.W_600),
                                    ft.Text(f"Раздел: {cat_name} • {p['desc']}", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                                    ft.Row(
                                        controls=[
                                            ft.TextButton(
                                                content=ft.Row(
                                                    controls=[ft.Icon(ft.Icons.PLAY_ARROW, size=16), ft.Text("Решить в калькуляторе", size=12)],
                                                    spacing=4,
                                                    tight=True,
                                                ),
                                                on_click=lambda e, pr=p: self.load_preset(pr),
                                            )
                                        ],
                                        alignment=ft.MainAxisAlignment.END,
                                        tight=True,
                                    ),
                                ],
                                spacing=6,
                            ),
                            padding=12,
                            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                            border_radius=12,
                            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                        )
                    )
            else:
                items.append(
                    ft.Container(
                        content=ft.Text(f"По запросу '{q}' ничего не найдено.", size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                        padding=12,
                        alignment=ft.Alignment.CENTER,
                    )
                )

            return ft.ListView(
                expand=True,
                spacing=10,
                controls=items,
            )

        # Presets by category (normal view)
        for cat in presets.CATEGORIES:
            cat_cards = []
            for p in cat["items"]:
                cat_cards.append(
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Text(p["title"], weight=ft.FontWeight.BOLD, size=13),
                                        ft.Container(
                                            content=ft.Text(f"= {p['result']}", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                            bgcolor=ft.Colors.INDIGO,
                                            padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                                            border_radius=6,
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                ft.Text(p["formula"], size=13, color=ft.Colors.PRIMARY, weight=ft.FontWeight.W_600),
                                ft.Text(p["desc"], size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                                ft.Row(
                                    controls=[
                                        ft.TextButton(
                                            content=ft.Row(
                                                controls=[ft.Icon(ft.Icons.PLAY_ARROW, size=16), ft.Text("Решить в калькуляторе", size=12)],
                                                spacing=4,
                                                tight=True,
                                            ),
                                            on_click=lambda e, pr=p: self.load_preset(pr),
                                        )
                                    ],
                                    alignment=ft.MainAxisAlignment.END,
                                    tight=True,
                                ),
                            ],
                            spacing=6,
                        ),
                        padding=12,
                        bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                        border_radius=12,
                        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                    )
                )

            items.append(
                ft.ExpansionTile(
                    title=ft.Text(cat["category"], weight=ft.FontWeight.BOLD, size=15),
                    leading=ft.Icon(ft.Icons.FUNCTIONS, color=ft.Colors.INDIGO_ACCENT),
                    controls=cat_cards,
                )
            )

        # Equivalents Table Card
        equiv_rows = [
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(e["source"], weight=ft.FontWeight.BOLD, size=12)),
                    ft.DataCell(ft.Text("~", color=ft.Colors.PRIMARY, size=14)),
                    ft.DataCell(ft.Text(e["equiv"], color=ft.Colors.PRIMARY, weight=ft.FontWeight.BOLD, size=12)),
                    ft.DataCell(ft.Text(e["cond"], size=11, color=ft.Colors.ON_SURFACE_VARIANT)),
                ]
            )
            for e in presets.EQUIVALENCES
        ]

        equiv_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Функция")),
                ft.DataColumn(ft.Text("")),
                ft.DataColumn(ft.Text("Эквивалент")),
                ft.DataColumn(ft.Text("Условие")),
            ],
            rows=equiv_rows,
            heading_row_height=36,
            data_row_min_height=30,
            data_row_max_height=34,
        )

        items.append(
            ft.ExpansionTile(
                title=ft.Text("Таблица эквивалентных бесконечно малых", weight=ft.FontWeight.BOLD, size=14),
                leading=ft.Icon(ft.Icons.AUTO_AWESOME, color=ft.Colors.AMBER_400),
                controls=[
                    ft.Container(
                        content=equiv_table,
                        padding=8,
                        alignment=ft.Alignment.CENTER,
                    )
                ],
            )
        )

        # Indeterminacies Guide
        indet_cards = []
        for ind in presets.INDETERMINACY_TABLE:
            indet_cards.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(ind["type"], weight=ft.FontWeight.BOLD, size=13, color=ft.Colors.AMBER_300),
                            ft.Text(ind["methods"], size=11),
                        ],
                        spacing=4,
                    ),
                    padding=10,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                    border_radius=8,
                )
            )

        items.append(
            ft.ExpansionTile(
                title=ft.Text("Таблица 7 типов неопределенностей", weight=ft.FontWeight.BOLD, size=14),
                leading=ft.Icon(ft.Icons.HELP_OUTLINE, color=ft.Colors.CYAN_400),
                controls=indet_cards,
            )
        )

        return ft.ListView(
            expand=True,
            spacing=10,
            controls=items,
        )

    # -------------------------------------------------------------
    # History View
    # -------------------------------------------------------------
    def build_history_view(self) -> ft.Control:
        if not self.history:
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Container(
                            content=ft.Image(
                                src=ICON_PNG,
                                width=48,
                                height=48,
                                fit=ft.BoxFit.CONTAIN,
                            ),
                            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                            border_radius=12,
                            padding=8,
                        )
                        if os.path.exists(ICON_PNG)
                        else ft.Icon(ft.Icons.HISTORY, size=64, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Text("История пуста", size=18, weight=ft.FontWeight.BOLD),
                        ft.Text("Здесь будут отображаться вычисленные вами пределы.", size=13, color=ft.Colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=12,
                ),
                alignment=ft.Alignment.CENTER,
                expand=True,
            )

        history_items = []

        def clear_history(e):
            self.history.clear()
            self.content_container.content = self.build_history_view()
            self.page.update()
            self.show_toast("История очищена")

        def set_history_filter(val: str):
            self.history_filter = val
            self.content_container.content = self.build_history_view()
            self.page.update()

        clear_btn = ft.OutlinedButton(
            content=ft.Row(
                controls=[ft.Icon(ft.Icons.DELETE_SWEEP, size=16), ft.Text("Очистить", size=12)],
                spacing=4,
                tight=True,
            ),
            on_click=clear_history,
        )

        fav_count = len([h for h in self.history if h.get("favorite")])
        filter_row = ft.Row(
            controls=[
                ft.Container(
                    content=ft.Text(f"Все ({len(self.history)})", size=12, weight=ft.FontWeight.W_600),
                    padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                    bgcolor=ft.Colors.PRIMARY_CONTAINER if self.history_filter == "all" else ft.Colors.SURFACE_CONTAINER_HIGH,
                    border_radius=8,
                    ink=True,
                    on_click=lambda e: set_history_filter("all"),
                ),
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.STAR, size=14, color=ft.Colors.AMBER_400),
                            ft.Text(f"Избранное ({fav_count})", size=12, weight=ft.FontWeight.W_600),
                        ],
                        spacing=4,
                        tight=True,
                    ),
                    padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                    bgcolor=ft.Colors.PRIMARY_CONTAINER if self.history_filter == "fav" else ft.Colors.SURFACE_CONTAINER_HIGH,
                    border_radius=8,
                    ink=True,
                    on_click=lambda e: set_history_filter("fav"),
                ),
                ft.Container(expand=True),
                clear_btn,
            ],
            alignment=ft.MainAxisAlignment.START,
        )
        history_items.append(filter_row)

        displayed_list = self.history if self.history_filter == "all" else [h for h in self.history if h.get("favorite")]

        if not displayed_list and self.history_filter == "fav":
            history_items.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.STAR_BORDER, size=48, color=ft.Colors.AMBER_400),
                            ft.Text("Нет избранных записей", size=15, weight=ft.FontWeight.BOLD),
                            ft.Text("Нажмите ⭐ в карточке решения, чтобы сохранить предел сюда.", size=12, color=ft.Colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    padding=30,
                    alignment=ft.Alignment.CENTER,
                )
            )

        for item in displayed_list:
            d_label = "x → " + item["point"]
            if item["dir"] == "+":
                d_label += "⁺"
            elif item["dir"] == "-":
                d_label += "⁻"

            def restore_item(e, it=item):
                self.expr_input.value = it["expr"]
                self.var_input.value = it["var"]
                self.point_input.value = it["point"]
                self.dir_dropdown.value = it["dir"]
                self.update_live_preview()
                self.nav_bar.selected_index = 0
                self.content_container.content = self.calc_view
                self.page.update()
                self.on_calculate_click(None)

            def toggle_item_fav(e, it=item):
                it["favorite"] = not it.get("favorite", False)
                self.content_container.content = self.build_history_view()
                self.page.update()

            fav_icon = ft.IconButton(
                icon=ft.Icons.STAR if item.get("favorite") else ft.Icons.STAR_BORDER,
                icon_color=ft.Colors.AMBER_400 if item.get("favorite") else ft.Colors.ON_SURFACE_VARIANT,
                icon_size=18,
                tooltip="В избранное",
                on_click=lambda e, it=item: toggle_item_fav(e, it),
            )

            history_items.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Text(f"lim ({d_label}) [{item['expr']}]", weight=ft.FontWeight.BOLD, size=13),
                                    ft.Text(f"Время: {item.get('time', '--:--')}", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            ft.Row(
                                controls=[
                                    ft.Container(
                                        content=ft.Text(f"= {item['result']}", weight=ft.FontWeight.BOLD, size=14, color=ft.Colors.PRIMARY),
                                        padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                                        border_radius=6,
                                    ),
                                    fav_icon,
                                ],
                                spacing=4,
                                tight=True,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                    bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                    border_radius=12,
                    border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                    ink=True,
                    on_click=restore_item,
                )
            )

        return ft.ListView(
            expand=True,
            spacing=10,
            controls=history_items,
        )

    # -------------------------------------------------------------
    # About View
    # -------------------------------------------------------------
    def build_about_view(self) -> ft.Control:
        app_icon_control = (
            ft.Container(
                content=ft.Image(
                    src=ICON_PNG,
                    width=54,
                    height=54,
                    fit=ft.BoxFit.CONTAIN,
                ),
                width=64,
                height=64,
                bgcolor=ft.Colors.INDIGO_900,
                border_radius=14,
                padding=5,
                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                shadow=ft.BoxShadow(blur_radius=16, color=ft.Colors.with_opacity(0.35, ft.Colors.BLACK)),
                alignment=ft.Alignment.CENTER,
            )
            if os.path.exists(ICON_PNG)
            else ft.CircleAvatar(
                content=ft.Icon(ft.Icons.ALL_INCLUSIVE, size=32, color=ft.Colors.AMBER_400),
                radius=32,
            )
        )

        return ft.ListView(
            expand=True,
            spacing=14,
            controls=[
                # 1. Main App Header Card with Icon
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        app_icon_control,
                                        ft.Column(
                                            controls=[
                                                ft.Row(
                                                    controls=[
                                                        ft.Text("LimitApp", size=20, weight=ft.FontWeight.BOLD),
                                                        ft.Container(
                                                            content=ft.Text("AI PRO", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                                            bgcolor=ft.Colors.INDIGO_600,
                                                            padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                                            border_radius=6,
                                                        ),
                                                    ],
                                                    spacing=6,
                                                    tight=True,
                                                ),
                                                ft.Text("Математический калькулятор пределов", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                                                ft.Row(
                                                    controls=[
                                                        ft.Icon(ft.Icons.AUTO_AWESOME, size=14, color=ft.Colors.AMBER_400),
                                                        ft.Text("Версия 1.4.0 • Google Gemini AI & SymPy", size=11, color=ft.Colors.GREEN_400),
                                                    ],
                                                    spacing=4,
                                                    tight=True,
                                                ),
                                            ],
                                            spacing=2,
                                        ),
                                    ],
                                    spacing=14,
                                ),
                                ft.Divider(height=1, thickness=0.5),
                                ft.Text(
                                    "LimitApp — аналитический мобильный калькулятор математических пределов с пошаговым решением, "
                                    "интеграцией бесплатного искусственного интеллекта Google Gemini, "
                                    "раскрытием всех 7 типов неопределенностей и интерактивным вводом математических формул.",
                                    size=12,
                                ),
                            ],
                            spacing=12,
                        ),
                        padding=18,
                    ),
                    elevation=3,
                ),
                # 2. Author Card
                ft.Card(
                    content=ft.Container(
                        content=ft.Row(
                            controls=[
                                (
                                    ft.Container(
                                        content=ft.Image(
                                            src=ICON_PNG,
                                            width=38,
                                            height=38,
                                            fit=ft.BoxFit.CONTAIN,
                                        ),
                                        width=48,
                                        height=48,
                                        bgcolor=ft.Colors.INDIGO_900,
                                        border_radius=12,
                                        padding=5,
                                        border=ft.Border.all(0.8, ft.Colors.OUTLINE_VARIANT),
                                        alignment=ft.Alignment.CENTER,
                                    )
                                    if os.path.exists(ICON_PNG)
                                    else ft.CircleAvatar(
                                        content=ft.Icon(ft.Icons.PERSON, size=28, color=ft.Colors.WHITE),
                                        radius=24,
                                    )
                                ),
                                ft.Column(
                                    controls=[
                                        ft.Text("Нарницкий Роман", size=16, weight=ft.FontWeight.BOLD),
                                        ft.Row(
                                            controls=[
                                                ft.Container(
                                                    content=ft.Text("Syrok", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                                    bgcolor=ft.Colors.PURPLE,
                                                    padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                                                    border_radius=8,
                                                ),
                                                ft.Text("Автор и создатель проекта", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                                            ],
                                            spacing=6,
                                            tight=True,
                                        ),
                                    ],
                                    spacing=2,
                                ),
                            ],
                            spacing=12,
                        ),
                        padding=14,
                    ),
                    elevation=2,
                ),
                # 3. Features Card
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Icon(ft.Icons.AUTO_AWESOME, color=ft.Colors.AMBER_400),
                                        ft.Text("Ключевые возможности v1.4.0", weight=ft.FontWeight.BOLD, size=15),
                                    ],
                                    spacing=8,
                                    tight=True,
                                ),
                                ft.Divider(height=1, thickness=0.5),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.AUTO_AWESOME, color=ft.Colors.AMBER_400, size=22),
                                    title=ft.Text("✨ Бесплатный Google Gemini AI", size=13, weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("Пошаговое объяснение любого предела, теорем и графического смысла через Gemini 1.5 Flash, 2.0 Flash и 1.5 Pro.", size=11),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.TOUCH_APP, color=ft.Colors.PRIMARY, size=22),
                                    title=ft.Text("🎨 Быстрый и удобный ввод формул", size=13, weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("Готовые интерактивные шаблоны дробей, степеней, корней и замечательных пределов в 1 клик.", size=11),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.KEYBOARD, color=ft.Colors.PRIMARY, size=22),
                                    title=ft.Text("🔢 Двухуровневая математическая клавиатура", size=13, weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("Вкладки '123 / Алгебра' и 'f(x) Функции' с крупными удобными кнопками без загромождения экрана.", size=11),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=ft.Colors.GREEN_400, size=20),
                                    title=ft.Text("Решение любого существующего предела", size=13),
                                    subtitle=ft.Text("Поддержка LaTeX, тригонометрических степеней sin²(x), факториалов n!, корней, последовательностей.", size=11),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=ft.Colors.GREEN_400, size=20),
                                    title=ft.Text("Двусторонние и односторонние пределы", size=13),
                                    subtitle=ft.Text("Расчет при x → x₀, x → x₀⁺ и x → x₀⁻ с пошаговым обоснованием.", size=11),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=ft.Colors.GREEN_400, size=20),
                                    title=ft.Text("Раскрытие 7 типов неопределенностей", size=13),
                                    subtitle=ft.Text("0/0, ∞/∞, 0·∞, ∞-∞, 1^∞, 0^0, ∞^0 (Правило Лопиталя, Тейлор, эквивалентности).", size=11),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=ft.Colors.GREEN_400, size=20),
                                    title=ft.Text("Интерактивный справочник с живым поиском", size=13),
                                    subtitle=ft.Text("Мгновенная фильтрация замечательных пределов и перенос в калькулятор в 1 клик.", size=11),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=ft.Colors.GREEN_400, size=20),
                                    title=ft.Text("⭐ Избранное и история вычислений", size=13),
                                    subtitle=ft.Text("Сохранение ключевых задач в закладки для подготовки к экзаменам.", size=11),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=ft.Colors.GREEN_400, size=20),
                                    title=ft.Text("🎨 Идеальная Android Adaptive Icon", size=13),
                                    subtitle=ft.Text("Чётко и ровно вырезанная иконка без артефактов под любой лаунчер (Pixel, Samsung, Xiaomi).", size=11),
                                ),
                            ],
                            spacing=4,
                        ),
                        padding=16,
                    ),
                    elevation=2,
                ),
                # 4. Tech Stack Card
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Icon(ft.Icons.DEVELOPER_MODE, color=ft.Colors.INDIGO_ACCENT),
                                        ft.Text("Стек технологий", weight=ft.FontWeight.BOLD, size=15),
                                    ],
                                    spacing=8,
                                    tight=True,
                                ),
                                ft.Divider(height=1, thickness=0.5),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.AUTO_AWESOME, size=22, color=ft.Colors.AMBER_400),
                                    title=ft.Text("Google Gemini REST API", weight=ft.FontWeight.W_600, size=13),
                                    subtitle=ft.Text("Интеллектуальный анализ задач, генерация математических доказательств и объяснений.", size=11),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.TERMINAL, size=22),
                                    title=ft.Text("Python 3 & SymPy", weight=ft.FontWeight.W_600, size=13),
                                    subtitle=ft.Text("Символьное дифференцирование, ряды Тейлора и точные аналитические расчеты.", size=11),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.PHONE_ANDROID, size=22),
                                    title=ft.Text("Flet & Flutter Engine", weight=ft.FontWeight.W_600, size=13),
                                    subtitle=ft.Text("Кроссплатформенный Material Design 3 интерфейс.", size=11),
                                ),
                            ],
                            spacing=6,
                        ),
                        padding=16,
                    ),
                    elevation=2,
                ),
            ],
        )


def main(page: ft.Page):
    LimitApp(page)


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
