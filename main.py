"""
LimitApp - Мобильный калькулятор и умный интерактивный репетитор по математическому анализу
Создатель: Нарницкий Роман (никнейм Syrok)
Стек: Python, SymPy, Flet (Material 3 / Flutter Engine), Google Gemini API
Версия: 1.6.0 (AI Tutor, Visual Epsilon-Delta Explorer & Photo OCR Release)
"""

import sys
import os
import io
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
        self.handbook_category_filter = "Все"
        self.active_keypad_tab = "basic"  # "basic" or "func"

        # Dictionaries to track quick-selector chips for active state highlights
        self.var_chip_widgets = {}
        self.point_chip_widgets = {}
        self.dir_chip_widgets = {}

        # Cached last calculation result
        self.last_res = None

        # Load configuration (Gemini API key & selected model)
        self.gemini_api_key, self.gemini_model = self.load_config()

        # Configure window & page
        self.page.title = "LimitApp | Умный репетитор и калькулятор пределов"
        if hasattr(self.page, "window"):
            self.page.window.width = 440
            self.page.window.height = 900
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

        dark_color_scheme = ft.ColorScheme(
            primary=ft.Colors.INDIGO_400,
            on_primary=ft.Colors.BLACK,
            primary_container=ft.Colors.INDIGO_900,
            on_primary_container=ft.Colors.INDIGO_100,
            secondary=ft.Colors.CYAN_400,
            on_secondary=ft.Colors.BLACK,
            surface="#111827",
            on_surface="#F3F4F6",
            surface_container="#1E293B",
            surface_container_low="#161F2E",
            surface_container_lowest="#0B0F17",
            surface_container_high="#283548",
            surface_container_highest="#334155",
            on_surface_variant="#94A3B8",
            outline="#475569",
            outline_variant="#334155",
        )

        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 0
        self.page.bgcolor = "#0B0F17"

        self.page.theme = ft.Theme(
            color_scheme=dark_color_scheme,
            visual_density=ft.VisualDensity.COMPACT,
            use_material3=True,
            scaffold_bgcolor="#0B0F17",
            card_bgcolor="#161F2E",
            canvas_color="#0B0F17",
            card_theme=ft.CardTheme(color="#161F2E"),
            expansion_tile_theme=ft.ExpansionTileTheme(
                bgcolor="#1E293B",
                collapsed_bgcolor="#1E293B",
                text_color=ft.Colors.ON_SURFACE,
                icon_color=ft.Colors.INDIGO_ACCENT,
            ),
            data_table_theme=ft.DataTableTheme(
                heading_row_color="#283548",
                data_row_color="#161F2E",
            ),
        )
        self.page.dark_theme = ft.Theme(
            color_scheme=dark_color_scheme,
            visual_density=ft.VisualDensity.COMPACT,
            use_material3=True,
            scaffold_bgcolor="#0B0F17",
            card_bgcolor="#161F2E",
            canvas_color="#0B0F17",
            card_theme=ft.CardTheme(color="#161F2E"),
            expansion_tile_theme=ft.ExpansionTileTheme(
                bgcolor="#1E293B",
                collapsed_bgcolor="#1E293B",
                text_color=ft.Colors.ON_SURFACE,
                icon_color=ft.Colors.INDIGO_ACCENT,
            ),
            data_table_theme=ft.DataTableTheme(
                heading_row_color="#283548",
                data_row_color="#161F2E",
            ),
        )

        # Register services in page.services (fixes Unknown control: FilePicker)
        self.clipboard = ft.Clipboard()
        self.file_picker = ft.FilePicker(on_result=self.on_photo_file_picked)
        self.page.services.append(self.clipboard)
        self.page.services.append(self.file_picker)

        # Live Math preview label
        self.live_preview_text = ft.Text(
            "lim (x → 0) [ sin(x)/x ]",
            size=14,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.PRIMARY,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

        # UI Controls for Calculator
        self.expr_input = ft.TextField(
            label="Функция f(x)",
            hint_text="sin(x)/x, (1-cos(x))/x^2...",
            value="sin(x)/x",
            prefix_icon=ft.Icons.FUNCTIONS,
            border=ft.OutlineInputBorder(border_radius=12),
            autofocus=False,
            expand=True,
            on_change=self.on_input_changed,
            on_submit=self.on_calculate_click,
        )

        self.var_input = ft.TextField(
            label="Перем.",
            value="x",
            width=76,
            text_align=ft.TextAlign.CENTER,
            border=ft.OutlineInputBorder(border_radius=12),
            on_change=self.on_input_changed,
        )

        self.point_input = ft.TextField(
            label="Точка (x₀)",
            value="0",
            hint_text="0, oo, 1, pi...",
            border=ft.OutlineInputBorder(border_radius=12),
            expand=3,
            on_change=self.on_input_changed,
            on_submit=self.on_calculate_click,
        )

        self.dir_dropdown = ft.Dropdown(
            label="Направление",
            value="+-",
            border=ft.OutlineInputBorder(border_radius=12),
            options=[
                ft.dropdown.Option("+-", "x → x₀ (двусторонний)"),
                ft.dropdown.Option("+", "x → x₀⁺ (справа)"),
                ft.dropdown.Option("-", "x → x₀⁻ (слева)"),
            ],
            expand=4,
            on_select=self.on_input_changed,
        )

        # Result display container
        self.result_container = ft.Column(spacing=12, visible=False)

        # Explorer / Visual Lab Controls
        self.explorer_slider = ft.Slider(
            min=-0.5,
            max=0.5,
            value=0.05,
            divisions=100,
            label="{value}",
            on_change=self.on_explorer_slider_change,
        )
        self.explorer_x_text = ft.Text("x = 0.05", size=13, weight=ft.FontWeight.BOLD)
        self.explorer_dx_text = ft.Text("Δx = +0.05", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self.explorer_fx_text = ft.Text("f(x) = 0.99958", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY)
        self.explorer_diff_text = ft.Text("|f(x) - L| = 0.00042", size=12, color=ft.Colors.GREEN_400)
        self.explorer_convergence_bar = ft.ProgressBar(value=0.95, color=ft.Colors.GREEN_400, bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST)

        # Epsilon-Delta Explorer Controls
        self.eps_slider = ft.Slider(
            min=0.01,
            max=0.3,
            value=0.05,
            divisions=29,
            label="{value}",
            on_change=self.on_eps_slider_change,
        )
        self.eps_val_text = ft.Text("ε = 0.05", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_400)
        self.delta_val_text = ft.Text("Рассчитанный δ = 0.5000", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_400)
        self.corridor_y_text = ft.Text("Коридор по оси Y: [0.95, 1.05]", size=12)
        self.corridor_x_text = ft.Text("Интервал по оси X: [-0.50, +0.50]", size=12)

        # Tab views
        self.calc_view = self.build_calculator_view()
        self.explorer_view = self.build_explorer_view()
        self.tutor_view = self.build_tutor_view()
        self.handbook_view = self.build_handbook_view()
        self.history_view = self.build_history_view()

        # Update active chip highlights
        self.update_chip_highlights()

        # View container for swapping tabs
        self.content_container = ft.Container(
            content=self.calc_view,
            expand=True,
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            bgcolor="#0B0F17",
        )

        # Mobile Bottom Navigation Bar (5 distinct tabs)
        self.nav_bar = ft.NavigationBar(
            selected_index=0,
            bgcolor="#111827",
            on_change=self.on_nav_change,
            destinations=[
                ft.NavigationBarDestination(
                    icon=ft.Icons.CALCULATE_OUTLINED,
                    selected_icon=ft.Icons.CALCULATE,
                    label="Калькулятор",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.INSIGHTS_OUTLINED,
                    selected_icon=ft.Icons.INSIGHTS,
                    label="Лаборатория",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.SCHOOL_OUTLINED,
                    selected_icon=ft.Icons.SCHOOL,
                    label="Репетитор",
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
                padding=ft.Padding.only(left=10, top=6, bottom=6),
            ),
            title_spacing=0,
            title=ft.Row(
                spacing=8,
                controls=[
                    ft.Text("LimitApp", weight=ft.FontWeight.BOLD, size=18),
                    ft.Container(
                        content=ft.Text("AI TUTOR PRO", size=9, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        bgcolor=ft.Colors.INDIGO_600,
                        padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                        border_radius=8,
                    ),
                ],
                tight=True,
            ),
            actions=[
                ft.IconButton(
                    icon=ft.Icons.CAMERA_ALT_OUTLINED,
                    tooltip="Ввод предела по фото (OCR)",
                    on_click=self.open_photo_input_dialog,
                ),
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
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    api_key = data.get("gemini_api_key", api_key)
                    model = data.get("gemini_model", model)
        except Exception:
            pass
        return api_key, model

    def save_config(self, api_key: str, model: str):
        self.gemini_api_key = api_key
        self.gemini_model = model
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"gemini_api_key": api_key, "gemini_model": model}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def copy_to_clipboard(self, text: str, toast_msg: str = "Скопировано в буфер! 📋"):
        try:
            self.page.run_task(self.clipboard.set, text)
            self.show_toast(toast_msg)
        except Exception:
            self.show_toast(toast_msg)

    def open_gemini_settings(self, e=None):
        api_field = ft.TextField(
            label="Google Gemini API Key",
            value=self.gemini_api_key,
            password=True,
            can_reveal_password=True,
            border=ft.OutlineInputBorder(border_radius=12),
            prefix_icon=ft.Icons.KEY,
            hint_text="AIzaSy...",
            helper="Бесплатный ключ из Google AI Studio",
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
                    timeout=14.0,
                )
                if res["success"]:
                    status_text.value = f"✅ Ключ активен! Модель: {res.get('model', 'Gemini')}"
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
                    ft.Icon(ft.Icons.AUTO_AWESOME, color=ft.Colors.AMBER_400, size=22),
                    ft.Text("Настройки Gemini AI", weight=ft.FontWeight.BOLD, size=16),
                ],
                spacing=8,
                tight=True,
            ),
            scrollable=True,
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "Для автоматического решения пределов с подробным объяснением теорем "
                            "и распознавания формул по фото используется официальный бесплатный API Google Gemini.",
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
                width=340,
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
            self.page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(message, size=13, weight=ft.FontWeight.W_500),
                    behavior=ft.SnackBarBehavior.FLOATING,
                    show_close_icon=True,
                    duration=2500,
                    shape=ft.RoundedRectangleBorder(radius=10),
                )
            )
        except Exception:
            pass

    def on_nav_change(self, e):
        idx = self.nav_bar.selected_index
        if idx == 0:
            self.content_container.content = self.calc_view
        elif idx == 1:
            self.content_container.content = self.build_explorer_view()
        elif idx == 2:
            self.content_container.content = self.build_tutor_view()
        elif idx == 3:
            self.content_container.content = self.build_handbook_view()
        elif idx == 4:
            self.content_container.content = self.build_history_view()
        self.page.update()

    def on_input_changed(self, e=None):
        self.update_live_preview()
        self.update_chip_highlights()

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

    def update_chip_highlights(self):
        cur_var = (self.var_input.value or "").strip()
        cur_pt = (self.point_input.value or "").strip()
        cur_dir = (self.dir_dropdown.value or "+-").strip()

        for v, container in self.var_chip_widgets.items():
            is_active = (cur_var == v)
            container.bgcolor = ft.Colors.PRIMARY_CONTAINER if is_active else ft.Colors.SURFACE_CONTAINER_HIGH
            container.border = ft.Border.all(1.2 if is_active else 0.8, ft.Colors.PRIMARY if is_active else ft.Colors.OUTLINE_VARIANT)
            if hasattr(container.content, "color"):
                container.content.color = ft.Colors.ON_PRIMARY_CONTAINER if is_active else ft.Colors.ON_SURFACE

        for p_val, container in self.point_chip_widgets.items():
            is_active = (cur_pt == p_val)
            container.bgcolor = ft.Colors.PRIMARY_CONTAINER if is_active else ft.Colors.SURFACE_CONTAINER_HIGH
            container.border = ft.Border.all(1.2 if is_active else 0.8, ft.Colors.PRIMARY if is_active else ft.Colors.OUTLINE_VARIANT)
            if hasattr(container.content, "color"):
                container.content.color = ft.Colors.ON_PRIMARY_CONTAINER if is_active else ft.Colors.ON_SURFACE

        for d_val, container in self.dir_chip_widgets.items():
            is_active = (cur_dir == d_val)
            container.bgcolor = ft.Colors.PRIMARY_CONTAINER if is_active else ft.Colors.SURFACE_CONTAINER_HIGH
            container.border = ft.Border.all(1.2 if is_active else 0.8, ft.Colors.PRIMARY if is_active else ft.Colors.OUTLINE_VARIANT)
            if hasattr(container.content, "color"):
                container.content.color = ft.Colors.ON_PRIMARY_CONTAINER if is_active else ft.Colors.ON_SURFACE

        try:
            self.page.update()
        except Exception:
            pass

    # -------------------------------------------------------------
    # Keyboard & Symbol Insertions
    # -------------------------------------------------------------
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
        self.update_live_preview()

    def apply_template(self, expr_template: str, var="x", point="0", direction="+-"):
        self.expr_input.value = expr_template
        self.var_input.value = var
        self.point_input.value = point
        self.dir_dropdown.value = direction
        self.update_live_preview()
        self.update_chip_highlights()
        self.show_toast(f"Шаблон вставлен: {expr_template}")

    def select_variable(self, v: str):
        self.var_input.value = v
        if v == "n" and self.point_input.value == "0":
            self.point_input.value = "oo"
        self.update_live_preview()
        self.update_chip_highlights()

    def insert_point(self, val: str):
        self.point_input.value = val
        self.update_live_preview()
        self.update_chip_highlights()

    def select_direction(self, d: str):
        self.dir_dropdown.value = d
        self.update_live_preview()
        self.update_chip_highlights()

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
        self.update_chip_highlights()

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
            height=42,
            expand=1,
            bgcolor=bgcolor,
            border_radius=10,
            border=border,
            padding=ft.Padding.symmetric(horizontal=1),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            ink=True,
            on_click=lambda e, s=code: self.insert_symbol(s),
        )

    # -------------------------------------------------------------
    # Photo / Multimodal OCR Input via Gemini Vision
    # -------------------------------------------------------------
    def open_photo_input_dialog(self, e=None):
        def pick_from_files(ev):
            self.page.pop_dialog()
            self.file_picker.pick_files(
                dialog_title="Выберите фото примера",
                allowed_extensions=["jpg", "jpeg", "png", "webp"],
                allow_multiple=False,
            )

        def pick_sample(ev, sample_expr, sample_var, sample_pt, sample_dir):
            self.page.pop_dialog()
            self.expr_input.value = sample_expr
            self.var_input.value = sample_var
            self.point_input.value = sample_pt
            self.dir_dropdown.value = sample_dir
            self.update_live_preview()
            self.update_chip_highlights()
            self.show_toast(f"Образец загружен: {sample_expr}")
            self.on_calculate_click(None)

        dialog = ft.AlertDialog(
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.CAMERA_ALT, color=ft.Colors.AMBER_400, size=22),
                    ft.Text("Ввод предела по фото (OCR)", weight=ft.FontWeight.BOLD, size=16),
                ],
                spacing=8,
                tight=True,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "Сфотографируйте рукописный или печатный пример из тетради или учебника. "
                            "Нейросеть Google Gemini Vision автоматически распознает формулу предела и загрузит её в калькулятор.",
                            size=12,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.FilledButton(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.PHOTO_LIBRARY, size=17),
                                    ft.Text("Выбрать фото из галереи / файлов", size=13, weight=ft.FontWeight.BOLD),
                                ],
                                spacing=8,
                                tight=True,
                            ),
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.INDIGO_600,
                                padding=ft.Padding.symmetric(vertical=12, horizontal=8),
                            ),
                            action=ft.PickFiles(
                                self.file_picker,
                                dialog_title="Выберите фото примера",
                                allowed_extensions=["jpg", "jpeg", "png", "webp"],
                            ),
                            on_click=lambda ev: self.page.pop_dialog(),
                        ),
                        ft.Divider(height=1, thickness=0.5),
                        ft.Text("Или выберите тестовый рукописный образец:", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.OutlinedButton(
                            content=ft.Text("Образец 1: lim (x → 0) [ sin(3x)/x ]", size=11),
                            on_click=lambda ev: pick_sample(ev, "sin(3*x)/x", "x", "0", "+-"),
                        ),
                        ft.OutlinedButton(
                            content=ft.Text("Образец 2: lim (x → ∞) [ (1 + 1/x)^x ]", size=11),
                            on_click=lambda ev: pick_sample(ev, "(1 + 1/x)^x", "x", "oo", "+-"),
                        ),
                        ft.OutlinedButton(
                            content=ft.Text("Образец 3: lim (x → 0) [ (1 - cos(x))/x^2 ]", size=11),
                            on_click=lambda ev: pick_sample(ev, "(1 - cos(x))/x^2", "x", "0", "+-"),
                        ),
                    ],
                    spacing=10,
                    tight=True,
                ),
                width=340,
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda ev: self.page.pop_dialog()),
            ],
        )
        self.page.show_dialog(dialog)

    def on_photo_file_picked(self, e: ft.FilePickerResultEvent):
        if not e.files or len(e.files) == 0:
            return

        file_obj = e.files[0]
        file_path = file_obj.path

        if not (self.gemini_api_key or "").strip():
            self.show_toast("Для распознавания фото задайте бесплатный ключ Gemini API")
            self.open_gemini_settings()
            return

        self.show_toast("⏳ Gemini Vision анализирует изображение предела...")

        def ocr_worker():
            try:
                img_bytes = None
                mime = "image/jpeg"

                if file_path and os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        img_bytes = f.read()
                    ext = os.path.splitext(file_path)[1].lower().replace(".", "")
                    mime = "image/png" if ext == "png" else "image/jpeg"
                elif getattr(file_obj, "bytes", None):
                    img_bytes = file_obj.bytes
                    fname = getattr(file_obj, "name", "")
                    mime = "image/png" if fname.lower().endswith(".png") else "image/jpeg"

                if not img_bytes:
                    self.show_toast("Не удалось прочитать изображение")
                    return

                res = gemini_solver.recognize_limit_from_image(
                    image_bytes=img_bytes,
                    mime_type=mime,
                    api_key=self.gemini_api_key,
                    model=self.gemini_model,
                    timeout=30.0,
                )

                if res["success"]:
                    self.expr_input.value = res["expr"]
                    self.var_input.value = res["var"]
                    self.point_input.value = res["point"]
                    self.dir_dropdown.value = res["direction"]
                    self.update_live_preview()
                    self.update_chip_highlights()
                    self.show_toast(f"✨ Распознано: {res['expr']} (x → {res['point']})")
                    self.on_calculate_click(None)
                else:
                    self.show_toast(f"❌ {res.get('error', 'Ошибка распознавания')}")
            except Exception as ex:
                self.show_toast(f"Ошибка чтения файла: {str(ex)}")

        self.page.run_thread(ocr_worker)

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
                        ft.Icon(ft.Icons.AUTO_AWESOME, size=11, color=ft.Colors.AMBER_400),
                        ft.Text(label, size=11, weight=ft.FontWeight.BOLD, no_wrap=True),
                    ],
                    spacing=4,
                    tight=True,
                ),
                padding=ft.Padding.symmetric(horizontal=8, vertical=5),
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
        basic_r1 = [("x", "x", "var"), ("n", "n", "var"), ("(", "(", "op"), (")", ")", "op"), ("CLEAR", "C", "clear")]
        basic_r2 = [("7", "7", "num"), ("8", "8", "num"), ("9", "9", "num"), ("/", "÷", "op"), ("BACK", "⌫", "back")]
        basic_r3 = [("4", "4", "num"), ("5", "5", "num"), ("6", "6", "num"), ("*", "×", "op"), ("^", "^", "op")]
        basic_r4 = [("1", "1", "num"), ("2", "2", "num"), ("3", "3", "num"), ("-", "−", "op"), ("sqrt(", "√", "func")]
        basic_r5 = [("0", "0", "num"), (".", ".", "num"), ("oo", "∞", "var"), ("+", "+", "op"), ("abs(", "|x|", "func")]

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

        # Tab indicator controls
        self.tab_basic_text = ft.Text("123 / Алгебра", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        self.tab_basic_icon = ft.Icon(ft.Icons.PIN, size=15, color=ft.Colors.WHITE)
        self.tab_basic_btn = ft.Container(
            content=ft.Row(
                controls=[self.tab_basic_icon, self.tab_basic_text],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=5,
                tight=True,
            ),
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding.symmetric(vertical=7),
            bgcolor=ft.Colors.PRIMARY,
            border_radius=8,
            expand=True,
            ink=True,
            on_click=lambda e: self.switch_keypad_tab("basic"),
        )

        self.tab_func_text = ft.Text("f(x) Функции", size=12, weight=ft.FontWeight.W_600, color=ft.Colors.ON_SURFACE_VARIANT)
        self.tab_func_icon = ft.Icon(ft.Icons.FUNCTIONS, size=15, color=ft.Colors.ON_SURFACE_VARIANT)
        self.tab_func_btn = ft.Container(
            content=ft.Row(
                controls=[self.tab_func_icon, self.tab_func_text],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=5,
                tight=True,
            ),
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding.symmetric(vertical=7),
            bgcolor=ft.Colors.TRANSPARENT,
            border_radius=8,
            expand=True,
            ink=True,
            on_click=lambda e: self.switch_keypad_tab("func"),
        )

        segmented_tab_switch = ft.Container(
            content=ft.Row(
                controls=[self.tab_basic_btn, self.tab_func_btn],
                spacing=4,
            ),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            padding=3,
            border_radius=10,
            border=ft.Border.all(0.8, ft.Colors.OUTLINE_VARIANT),
        )

        keypad_container = ft.Container(
            content=ft.Column(
                controls=[
                    segmented_tab_switch,
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
        self.var_chip_widgets.clear()
        var_chips = []
        for v in ["x", "n", "t", "y"]:
            chip_text = ft.Text(v, size=12, weight=ft.FontWeight.BOLD, italic=True)
            chip = ft.Container(
                content=chip_text,
                padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                border_radius=8,
                border=ft.Border.all(0.8, ft.Colors.OUTLINE_VARIANT),
                ink=True,
                on_click=lambda e, var_val=v: self.select_variable(var_val),
            )
            self.var_chip_widgets[v] = chip
            var_chips.append(chip)

        # 4. Point chips
        self.point_chip_widgets.clear()
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
            chip_text = ft.Text(label, size=12, weight=ft.FontWeight.W_600)
            chip = ft.Container(
                content=chip_text,
                padding=ft.Padding.symmetric(horizontal=9, vertical=4),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                border_radius=8,
                border=ft.Border.all(0.8, ft.Colors.OUTLINE_VARIANT),
                ink=True,
                on_click=lambda e, v=val: self.insert_point(v),
            )
            self.point_chip_widgets[val] = chip
            point_chips.append(chip)

        # 5. Direction Chips
        self.dir_chip_widgets.clear()
        dir_chips = []
        for d_code, d_label in [("+-", "x → x₀"), ("+", "x → x₀⁺"), ("-", "x → x₀⁻")]:
            chip_text = ft.Text(d_label, size=11, weight=ft.FontWeight.W_600)
            chip = ft.Container(
                content=chip_text,
                padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                border_radius=8,
                border=ft.Border.all(0.8, ft.Colors.OUTLINE_VARIANT),
                ink=True,
                on_click=lambda e, code=d_code: self.select_direction(code),
            )
            self.dir_chip_widgets[d_code] = chip
            dir_chips.append(chip)

        # 6. Primary Action Buttons
        calc_btn = ft.FilledButton(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.FLASH_ON, color=ft.Colors.AMBER_300, size=18),
                    ft.Text("Рассчитать предел", weight=ft.FontWeight.BOLD, size=14),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                tight=True,
            ),
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.INDIGO_600,
                color=ft.Colors.WHITE,
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.Padding.symmetric(vertical=13),
            ),
            expand=True,
            on_click=self.on_calculate_click,
        )

        gemini_btn = ft.FilledTonalButton(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.AUTO_AWESOME, color=ft.Colors.AMBER_400, size=17),
                    ft.Text("Объяснение Gemini AI", weight=ft.FontWeight.BOLD, size=13),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                tight=True,
            ),
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.Padding.symmetric(vertical=12),
            ),
            expand=True,
            tooltip="Решить с подробным объяснением теорем от Google Gemini AI",
            on_click=self.on_gemini_solve_click,
        )

        gemini_cfg_btn = ft.Container(
            content=ft.IconButton(
                icon=ft.Icons.SETTINGS,
                icon_size=19,
                tooltip="Настройки Gemini API",
                on_click=self.open_gemini_settings,
            ),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            border_radius=12,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            width=46,
            height=46,
            alignment=ft.Alignment.CENTER,
        )

        def copy_preview_formula(e):
            val = (self.expr_input.value or "").strip()
            if val:
                self.copy_to_clipboard(val, "Формула скопирована! 📋")

        # Live Formula Blackboard Card with instant Copy icon
        preview_card = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.AUTO_GRAPH, size=18, color=ft.Colors.PRIMARY),
                    ft.Container(
                        content=self.live_preview_text,
                        expand=True,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CAMERA_ALT,
                        icon_size=16,
                        tooltip="Ввод по фото",
                        on_click=self.open_photo_input_dialog,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.COPY,
                        icon_size=16,
                        tooltip="Скопировать формулу",
                        on_click=copy_preview_formula,
                    ),
                ],
                spacing=4,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=ft.Padding.only(left=12, right=4, top=3, bottom=3),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            border_radius=12,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
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
                                            ft.Icon(ft.Icons.AUTO_AWESOME, size=15, color=ft.Colors.AMBER_400),
                                            ft.Text("Шаблоны задач:", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE_VARIANT),
                                        ],
                                        spacing=4,
                                        tight=True,
                                    ),
                                    ft.Row(
                                        controls=[
                                            ft.TextButton(
                                                content=ft.Row(
                                                    [ft.Icon(ft.Icons.CAMERA_ALT, size=13), ft.Text("Фото", size=11)],
                                                    spacing=3,
                                                    tight=True,
                                                ),
                                                style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=6, vertical=2)),
                                                on_click=self.open_photo_input_dialog,
                                            ),
                                            ft.TextButton(
                                                content=ft.Row(
                                                    [ft.Icon(ft.Icons.CASINO_OUTLINED, size=13), ft.Text("Пример", size=11)],
                                                    spacing=3,
                                                    tight=True,
                                                ),
                                                style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=6, vertical=2)),
                                                on_click=self.load_random_example,
                                            ),
                                            ft.TextButton(
                                                content=ft.Row(
                                                    [ft.Icon(ft.Icons.CLEAR_ALL, size=13), ft.Text("Очистить", size=11)],
                                                    spacing=3,
                                                    tight=True,
                                                ),
                                                style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=6, vertical=2)),
                                                on_click=self.clear_inputs,
                                            ),
                                        ],
                                        spacing=2,
                                        tight=True,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),

                            # Horizontal scrolling template chips
                            template_scroll_row,

                            # Live Formula Preview Card
                            preview_card,

                            # Input Fields
                            ft.Row(controls=[self.expr_input, self.var_input], spacing=8),

                            # Variable selector chips
                            ft.Row(
                                controls=[
                                    ft.Text("Переменная:", size=11, weight=ft.FontWeight.W_600, color=ft.Colors.ON_SURFACE_VARIANT),
                                    *var_chips,
                                ],
                                spacing=6,
                                wrap=True,
                            ),

                            ft.Divider(height=1, thickness=0.5),

                            # Limit Parameters (x0, direction)
                            ft.Text("Точка стремления и знак", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE_VARIANT),
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
                                wrap=True,
                            ),

                            ft.Container(height=2),

                            # Action buttons
                            ft.Column(
                                controls=[
                                    ft.Row(controls=[calc_btn]),
                                    ft.Row(
                                        controls=[
                                            gemini_btn,
                                            gemini_cfg_btn,
                                        ],
                                        spacing=8,
                                    ),
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

                # Touch Mathematical Keypad
                keypad_container,

                # Results container
                self.result_container,
            ],
        )

    def switch_keypad_tab(self, tab_name: str):
        self.active_keypad_tab = tab_name
        self.basic_keys_col.visible = (tab_name == "basic")
        self.func_keys_col.visible = (tab_name == "func")

        is_basic = (tab_name == "basic")
        self.tab_basic_btn.bgcolor = ft.Colors.PRIMARY if is_basic else ft.Colors.TRANSPARENT
        self.tab_basic_text.color = ft.Colors.WHITE if is_basic else ft.Colors.ON_SURFACE_VARIANT
        self.tab_basic_icon.color = ft.Colors.WHITE if is_basic else ft.Colors.ON_SURFACE_VARIANT

        self.tab_func_btn.bgcolor = ft.Colors.PRIMARY if not is_basic else ft.Colors.TRANSPARENT
        self.tab_func_text.color = ft.Colors.WHITE if not is_basic else ft.Colors.ON_SURFACE_VARIANT
        self.tab_func_icon.color = ft.Colors.WHITE if not is_basic else ft.Colors.ON_SURFACE_VARIANT

        self.page.update()

    # -------------------------------------------------------------
    # SymPy Analytical Limit Calculation
    # -------------------------------------------------------------
    def on_calculate_click(self, e):
        raw_expr = self.expr_input.value.strip() if self.expr_input.value else ""
        if not raw_expr:
            self.show_toast("Пожалуйста, введите функцию f(x)")
            return

        parsed_full = engine.parse_full_limit(raw_expr)
        if parsed_full:
            self.expr_input.value = parsed_full["expr"]
            self.var_input.value = parsed_full["var"]
            self.point_input.value = parsed_full["point"]
            self.dir_dropdown.value = parsed_full["direction"]
            self.update_live_preview()
            self.update_chip_highlights()

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
                                        ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED_400, size=20),
                                        ft.Text("Не удалось вычислить предел аналитически", weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400, size=14),
                                    ],
                                    tight=True,
                                ),
                                ft.Text(res.get("error", "Проверьте синтаксис ввода."), size=12),
                                ft.Divider(height=1, thickness=0.5),
                                ft.Row(
                                    controls=[
                                        ft.FilledButton(
                                            content=ft.Row(
                                                controls=[
                                                    ft.Icon(ft.Icons.AUTO_AWESOME, color=ft.Colors.AMBER_400, size=16),
                                                    ft.Text("Решить через Gemini AI", size=12, weight=ft.FontWeight.BOLD),
                                                ],
                                                spacing=6,
                                                tight=True,
                                            ),
                                            style=ft.ButtonStyle(bgcolor=ft.Colors.INDIGO_700),
                                            on_click=self.on_gemini_solve_click,
                                        ),
                                        ft.OutlinedButton(
                                            content=ft.Row(
                                                controls=[
                                                    ft.Icon(ft.Icons.CLEAR_ALL, size=16),
                                                    ft.Text("Очистить", size=12),
                                                ],
                                                spacing=4,
                                                tight=True,
                                            ),
                                            on_click=self.clear_inputs,
                                        ),
                                    ],
                                    spacing=8,
                                    wrap=True,
                                ),
                            ],
                            spacing=10,
                        ),
                        padding=16,
                    ),
                    bgcolor=ft.Colors.ERROR_CONTAINER,
                )
            ]
            self.page.update()
            return

        self.last_res = res
        self.render_result(res)

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
                    ft.Container(
                        content=ft.Text(lim_notation, size=13, color=ft.Colors.ON_SURFACE_VARIANT, italic=True),
                        expand=True,
                    ),
                    ft.Container(
                        content=ft.Text("Аналитическое решение", size=10, weight=ft.FontWeight.W_600, color=ft.Colors.GREEN_400),
                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                        padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                        border_radius=6,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                wrap=True,
            ),
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Text("= ", size=26, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
                        ft.Text(ans_text, size=26, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
                        ft.Text(f" ({numeric_text})" if numeric_text else "", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    wrap=True,
                ),
                padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                border_radius=12,
                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            ),
        ]

        # Discontinuity badge in header
        if res.get("discontinuity"):
            disc = res["discontinuity"]
            header_items.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.AUTO_GRAPH, size=15, color=ft.Colors.CYAN_400),
                            ft.Text(f"Тип точки: {disc['tag']}", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_300),
                        ],
                        spacing=6,
                        tight=True,
                    ),
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                    border_radius=8,
                )
            )

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
                    wrap=True,
                )
            )

        def copy_result(e):
            full_text = f"{lim_notation} = {ans_text}\n"
            if res.get("indeterminacy"):
                full_text += f"Тип: {res['indeterminacy']}\n"
            for step in res.get("steps", []):
                full_text += f"\n{step['title']}:\n{step['desc']}\n"
            self.copy_to_clipboard(full_text, "Решение скопировано в буфер!")

        def copy_latex(e):
            latex_code = res.get("latex", "")
            if latex_code:
                self.copy_to_clipboard(latex_code, "LaTeX код скопирован! 📋")

        def open_in_lab(e):
            self.nav_bar.selected_index = 1
            self.content_container.content = self.build_explorer_view()
            self.page.update()

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
                controls=[ft.Icon(ft.Icons.COPY, size=14), ft.Text("Текст", size=11)],
                spacing=4,
                tight=True,
            ),
            on_click=copy_result,
        )

        latex_btn = ft.OutlinedButton(
            content=ft.Row(
                controls=[ft.Icon(ft.Icons.CODE, size=14), ft.Text("LaTeX", size=11)],
                spacing=4,
                tight=True,
            ),
            tooltip="Скопировать чистый LaTeX код формулы",
            on_click=copy_latex,
        )

        lab_btn = ft.FilledTonalButton(
            content=ft.Row(
                controls=[ft.Icon(ft.Icons.INSIGHTS, size=14, color=ft.Colors.CYAN_400), ft.Text("Лаборатория", size=11)],
                spacing=4,
                tight=True,
            ),
            tooltip="Исследовать предел в интерактивном режиме с ползунком и ε-δ",
            on_click=open_in_lab,
        )

        header_items.append(
            ft.Row(
                controls=[
                    fav_btn,
                    ft.Row(
                        controls=[latex_btn, copy_btn, lab_btn],
                        spacing=6,
                        wrap=True,
                        tight=True,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                wrap=True,
            )
        )

        main_card = ft.Card(
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            content=ft.Container(
                content=ft.Column(controls=header_items, spacing=10),
                padding=16,
            ),
            elevation=3,
        )
        self.result_container.controls.append(main_card)

        # 2. Pedagogical Diagnosis of Indeterminacy Card
        if res.get("diagnosis") and res["diagnosis"].get("has_indet"):
            diag = res["diagnosis"]
            diag_card = ft.Card(
                bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                content=ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.HEALTH_AND_SAFETY, color=ft.Colors.AMBER_400, size=18),
                                    ft.Text("Диагноз неопределенности (Матанализ)", weight=ft.FontWeight.BOLD, size=14),
                                ],
                                spacing=8,
                                tight=True,
                            ),
                            ft.Text(diag["diagnosis"], size=12),
                            ft.Divider(height=1, thickness=0.5),
                            ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.LIGHTBULB_OUTLINE, size=16, color=ft.Colors.GREEN_400),
                                    ft.Text(f"Рекомендованный метод: {diag['recommendation']}", size=11, color=ft.Colors.GREEN_300, weight=ft.FontWeight.W_500),
                                ],
                                spacing=6,
                                tight=True,
                            ),
                        ],
                        spacing=8,
                    ),
                    padding=14,
                ),
                elevation=2,
            )
            self.result_container.controls.append(diag_card)

        # 3. Alternative Paths & Methods Comparison
        if res.get("methods"):
            method_tiles = []
            for m in res["methods"]:
                method_tiles.append(
                    ft.ExpansionTile(
                        title=ft.Text(m["name"], weight=ft.FontWeight.BOLD, size=13),
                        leading=ft.Icon(ft.Icons.PLAY_ARROW_ROUNDED, color=ft.Colors.INDIGO_ACCENT),
                        controls=[
                            ft.Container(
                                content=ft.Text(m["desc"], size=12),
                                padding=ft.Padding.only(left=16, right=16, bottom=12),
                            )
                        ],
                    )
                )

            methods_card = ft.Card(
                bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                content=ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.ALT_ROUTE, color=ft.Colors.INDIGO_ACCENT, size=18),
                                    ft.Text("Сравнение методов решения (Alternative Paths)", weight=ft.FontWeight.BOLD, size=14),
                                ],
                                spacing=8,
                                tight=True,
                            ),
                            ft.Text("Один предел можно решить несколькими способами. Выберите подходящий:", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Column(controls=method_tiles, spacing=2),
                        ],
                        spacing=8,
                    ),
                    padding=12,
                ),
                elevation=2,
            )
            self.result_container.controls.append(methods_card)

        # 4. Step-by-Step Breakdown Cards
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
                bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
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

        # 5. Neighborhood Convergence Table
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
                bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                heading_row_color=ft.Colors.SURFACE_CONTAINER_HIGH,
                data_row_color={
                    "hovered": ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    "": ft.Colors.SURFACE_CONTAINER_LOW,
                },
                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                border_radius=10,
                columns=[
                    ft.DataColumn(ft.Text("Окрестность", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE)),
                    ft.DataColumn(ft.Text(f"{var}", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE)),
                    ft.DataColumn(ft.Text(f"f({var})", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE)),
                ],
                rows=table_controls,
                heading_row_height=36,
                data_row_min_height=32,
                data_row_max_height=36,
            )

            table_card = ft.Card(
                bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
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
                            ft.Container(
                                content=ft.Row(controls=[data_table], scroll=ft.ScrollMode.ADAPTIVE, alignment=ft.MainAxisAlignment.CENTER),
                                alignment=ft.Alignment.CENTER,
                            ),
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

        if not (self.gemini_api_key or "").strip():
            self.show_toast("Введите бесплатный ключ Gemini API для решения через ИИ")
            self.open_gemini_settings()
            return

        parsed_full = engine.parse_full_limit(raw_expr)
        if parsed_full:
            self.expr_input.value = parsed_full["expr"]
            self.var_input.value = parsed_full["var"]
            self.point_input.value = parsed_full["point"]
            self.dir_dropdown.value = parsed_full["direction"]
            self.update_live_preview()
            self.update_chip_highlights()

        expr_text = self.expr_input.value.strip()
        var_text = self.var_input.value.strip() if self.var_input.value else "x"
        point_text = self.point_input.value.strip() if self.point_input.value else "0"
        dir_val = self.dir_dropdown.value or "+-"

        self.result_container.visible = True
        self.result_container.controls = [
            ft.Card(
                bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
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

        def gemini_worker():
            res = gemini_solver.solve_limit_with_gemini(
                expr=expr_text,
                var=var_text,
                point=point_text,
                direction=dir_val,
                api_key=self.gemini_api_key,
                model=self.gemini_model,
                timeout=35.0,
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
                                            controls=[ft.Icon(ft.Icons.SETTINGS, size=15), ft.Text("Настроить API ключ", size=12)],
                                            spacing=6,
                                            tight=True,
                                        ),
                                        on_click=self.open_gemini_settings,
                                    ),
                                    ft.OutlinedButton(
                                        content=ft.Row(
                                            controls=[ft.Icon(ft.Icons.FLASH_ON, size=15), ft.Text("Решить через SymPy", size=12)],
                                            spacing=6,
                                            tight=True,
                                        ),
                                        on_click=self.on_calculate_click,
                                    ),
                                ],
                                spacing=8,
                                wrap=True,
                            ),
                        ],
                        spacing=10,
                    ),
                    padding=16,
                ),
                bgcolor=ft.Colors.ERROR_CONTAINER,
            )
            self.result_container.controls.append(error_card)
            self.page.update()
            return

        ai_text = res.get("text", "")

        def copy_ai_text(e):
            self.copy_to_clipboard(ai_text, "Объяснение Gemini AI скопировано в буфер!")

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
            wrap=True,
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
            wrap=True,
        )

        md_view = ft.Markdown(
            value=ai_text,
            selectable=True,
            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
        )

        ai_card = ft.Card(
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
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
                    spacing=12,
                ),
                padding=16,
            ),
            elevation=3,
        )

        self.result_container.controls.append(ai_card)

        self.history.insert(0, {
            "id": datetime.now().timestamp(),
            "time": datetime.now().strftime("%H:%M:%S"),
            "expr": expr,
            "var": var,
            "point": point,
            "dir": direction,
            "result": "✨ Gemini AI",
            "favorite": False,
        })
        if len(self.history) > 50:
            self.history.pop()

        self.page.update()

    # -------------------------------------------------------------
    # Visual Explorer & Epsilon-Delta Laboratory
    # -------------------------------------------------------------
    def on_explorer_slider_change(self, e):
        expr_str = self.expr_input.value.strip() or "sin(x)/x"
        var_str = self.var_input.value.strip() or "x"
        point_str = self.point_input.value.strip() or "0"

        try:
            val_delta = float(self.explorer_slider.value)
            pt_val = 0.0
            if point_str not in ("oo", "-oo"):
                try:
                    pt_val = float(point_str)
                except Exception:
                    pt_val = 0.0

            x_curr = pt_val + val_delta
            var = engine.sp.Symbol(var_str)
            expr = engine.parse_math(expr_str, var)
            point = engine.parse_math(point_str, var)

            data = engine.evaluate_point_live(expr, var, point, x_curr)
            if data["success"]:
                sign = "+" if data["dx"] >= 0 else ""
                self.explorer_x_text.value = f"x = {data['x']:.5f}"
                self.explorer_dx_text.value = f"Δx = {sign}{data['dx']:.5f}"
                self.explorer_fx_text.value = f"f(x) = {data['fx']}"
                self.explorer_diff_text.value = f"|f(x) - L| = {data['diff']}"

                # Progress gauge
                try:
                    d_float = float(data['diff'])
                    val_progress = max(0.0, min(1.0, 1.0 / (1.0 + d_float * 5.0)))
                    self.explorer_convergence_bar.value = val_progress
                except Exception:
                    self.explorer_convergence_bar.value = 0.5
            self.page.update()
        except Exception:
            pass

    def on_eps_slider_change(self, e):
        expr_str = self.expr_input.value.strip() or "sin(x)/x"
        var_str = self.var_input.value.strip() or "x"
        point_str = self.point_input.value.strip() or "0"

        try:
            eps_val = float(self.eps_slider.value)
            var = engine.sp.Symbol(var_str)
            expr = engine.parse_math(expr_str, var)
            point = engine.parse_math(point_str, var)

            res = engine.compute_epsilon_delta(expr, var, point, eps_val)
            if res["success"]:
                self.eps_val_text.value = f"ε = {res['epsilon']:.4f}"
                self.delta_val_text.value = f"Рассчитанный δ = {res['delta']:.5f}"
                self.corridor_y_text.value = f"Коридор по оси Y: [{res['corridor_y'][0]}, {res['corridor_y'][1]}]"
                self.corridor_x_text.value = f"Интервал по оси X: [{res['corridor_x'][0]}, {res['corridor_x'][1]}]"
            self.page.update()
        except Exception:
            pass

    def build_explorer_view(self) -> ft.Control:
        expr_str = self.expr_input.value.strip() or "sin(x)/x"
        var_str = self.var_input.value.strip() or "x"
        point_str = self.point_input.value.strip() or "0"

        # Evaluate discontinuity analysis
        disc_info = None
        try:
            var = engine.sp.Symbol(var_str)
            expr = engine.parse_math(expr_str, var)
            point = engine.parse_math(point_str, var)
            disc_info = engine.classify_discontinuity(expr, var, point)
        except Exception:
            pass

        # Card 1: Tactile Slider Explorer
        tactile_card = ft.Card(
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.TOUCH_APP, color=ft.Colors.CYAN_400, size=20),
                                ft.Text("Тактильный ползунок приближения (x → x₀)", weight=ft.FontWeight.BOLD, size=15),
                            ],
                            spacing=8,
                            tight=True,
                        ),
                        ft.Text("Двигайте ползунок пальцем, чтобы физически приближаться к предельной точке слева и справа:", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                        self.explorer_slider,
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Row(
                                        controls=[self.explorer_x_text, self.explorer_dx_text],
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    ),
                                    ft.Row(
                                        controls=[self.explorer_fx_text, self.explorer_diff_text],
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    ),
                                    ft.Container(height=4),
                                    ft.Row(
                                        controls=[
                                            ft.Text("Сходимость к пределу:", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                                            ft.Container(content=self.explorer_convergence_bar, expand=True),
                                        ],
                                        spacing=8,
                                    ),
                                ],
                                spacing=4,
                            ),
                            padding=12,
                            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                            border_radius=10,
                            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                        ),
                    ],
                    spacing=10,
                ),
                padding=16,
            ),
            elevation=2,
        )

        # Card 2: Epsilon-Delta Rigorous Visualizer
        eps_card = ft.Card(
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.SHIELD_OUTLINED, color=ft.Colors.AMBER_400, size=20),
                                ft.Text("Визуализация определения Коши (ε - δ)", weight=ft.FontWeight.BOLD, size=15),
                            ],
                            spacing=8,
                            tight=True,
                        ),
                        ft.Text("Сужайте коридор ε вокруг предела L — приложение автоматически рассчитывает допустимую ширину δ окрестности x₀:", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                        self.eps_slider,
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Row(
                                        controls=[self.eps_val_text, self.delta_val_text],
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    ),
                                    self.corridor_y_text,
                                    self.corridor_x_text,
                                    ft.Container(height=2),
                                    ft.Row(
                                        controls=[
                                            ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_400, size=15),
                                            ft.Text("Вся δ-окрестность строго лежит внутри коридора ε!", size=11, color=ft.Colors.GREEN_400, weight=ft.FontWeight.BOLD),
                                        ],
                                        spacing=6,
                                        tight=True,
                                    ),
                                ],
                                spacing=4,
                            ),
                            padding=12,
                            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                            border_radius=10,
                            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                        ),
                    ],
                    spacing=10,
                ),
                padding=16,
            ),
            elevation=2,
        )

        # Card 3: Discontinuity Analysis Card
        disc_controls = [
            ft.Row(
                controls=[
                    ft.Icon(ft.Icons.TIMELINE, color=ft.Colors.PURPLE_400, size=20),
                    ft.Text("Анализ разрыва и выколотой точки", weight=ft.FontWeight.BOLD, size=15),
                ],
                spacing=8,
                tight=True,
            ),
        ]

        if disc_info:
            disc_controls.extend([
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.INFO_OUTLINE, size=16, color=ft.Colors.WHITE),
                            ft.Text(disc_info["type"], weight=ft.FontWeight.BOLD, size=13, color=ft.Colors.WHITE),
                        ],
                        spacing=6,
                        tight=True,
                    ),
                    padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                    bgcolor=ft.Colors.INDIGO_700,
                    border_radius=8,
                ),
                ft.Text(disc_info["desc"], size=12),
                ft.Divider(height=1, thickness=0.5),
                ft.Text(f"Значение в самой точке f({point_str}): {disc_info['val']}", size=12, weight=ft.FontWeight.W_600),
            ])

        # Quick Discontinuity presets
        def load_disc_sample(e, ex, v, pt):
            self.expr_input.value = ex
            self.var_input.value = v
            self.point_input.value = pt
            self.dir_dropdown.value = "+-"
            self.update_live_preview()
            self.update_chip_highlights()
            self.content_container.content = self.build_explorer_view()
            self.page.update()

        disc_controls.extend([
            ft.Text("Тестовые примеры разрывов для исследования:", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE_VARIANT),
            ft.Row(
                controls=[
                    ft.OutlinedButton(
                        content=ft.Text("Выколотая точка: sin(x)/x", size=11),
                        on_click=lambda ev: load_disc_sample(ev, "sin(x)/x", "x", "0"),
                    ),
                    ft.OutlinedButton(
                        content=ft.Text("Скачок: |x|/x", size=11),
                        on_click=lambda ev: load_disc_sample(ev, "abs(x)/x", "x", "0"),
                    ),
                    ft.OutlinedButton(
                        content=ft.Text("Асимптота: 1/x", size=11),
                        on_click=lambda ev: load_disc_sample(ev, "1/x", "x", "0"),
                    ),
                ],
                wrap=True,
                spacing=6,
            ),
        ])

        disc_card = ft.Card(
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            content=ft.Container(
                content=ft.Column(controls=disc_controls, spacing=10),
                padding=16,
            ),
            elevation=2,
        )

        return ft.ListView(
            expand=True,
            spacing=12,
            controls=[
                tactile_card,
                eps_card,
                disc_card,
            ],
        )

    # -------------------------------------------------------------
    # AI Tutor & Practice Trainer View
    # -------------------------------------------------------------
    def build_tutor_view(self) -> ft.Control:
        expr_str = self.expr_input.value.strip() or "sin(x)/x"
        var_str = self.var_input.value.strip() or "x"
        point_str = self.point_input.value.strip() or "0"

        # 1. AI Solution Step Checker ("Find the mistake")
        user_step_input = ft.TextField(
            label="Ваш ход решения или предположение",
            hint_text="Например: 'Я заменил sin(x) на x и получил 1' или 'Взял производные...'",
            multiline=True,
            min_lines=2,
            max_lines=4,
            border=ft.OutlineInputBorder(border_radius=12),
        )

        feedback_container = ft.Column(spacing=6)

        def on_verify_step(e):
            step_text = user_step_input.value.strip()
            if not step_text:
                self.show_toast("Введите ход решения для проверки")
                return

            if not (self.gemini_api_key or "").strip():
                self.show_toast("Введите бесплатный ключ Gemini API для работы репетитора")
                self.open_gemini_settings()
                return

            feedback_container.controls = [
                ft.Row(
                    controls=[
                        ft.ProgressRing(width=16, height=16, stroke_width=2),
                        ft.Text("AI-Репетитор анализирует ваш ход решения...", size=12, italic=True),
                    ],
                    spacing=8,
                )
            ]
            self.page.update()

            def tutor_worker():
                res = gemini_solver.check_user_solution(
                    expr=expr_str,
                    var=var_str,
                    point=point_str,
                    direction="+-",
                    user_solution_step=step_text,
                    api_key=self.gemini_api_key,
                    model=self.gemini_model,
                )
                if res["success"]:
                    feedback_container.controls = [
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Row(
                                        controls=[
                                            ft.Icon(ft.Icons.SCHOOL, color=ft.Colors.AMBER_400, size=18),
                                            ft.Text("Отзыв AI-Репетитора", weight=ft.FontWeight.BOLD, size=13),
                                        ],
                                        spacing=6,
                                        tight=True,
                                    ),
                                    ft.Markdown(res["review"]),
                                ],
                                spacing=6,
                            ),
                            padding=12,
                            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                            border_radius=10,
                            border=ft.Border.all(1, ft.Colors.PRIMARY),
                        )
                    ]
                else:
                    feedback_container.controls = [
                        ft.Text(f"❌ {res.get('error')}", color=ft.Colors.RED_400, size=12)
                    ]
                self.page.update()

            self.page.run_thread(tutor_worker)

        tutor_step_card = ft.Card(
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.PSYCHOLOGY, color=ft.Colors.AMBER_400, size=20),
                                ft.Text("Тренажер: Найди ошибку в моем решении", weight=ft.FontWeight.BOLD, size=15),
                            ],
                            spacing=8,
                            tight=True,
                        ),
                        ft.Text(f"Текущая задача: lim ({var_str} → {point_str}) [ {expr_str} ]", size=12, color=ft.Colors.PRIMARY, weight=ft.FontWeight.BOLD),
                        ft.Text("Опишите свой шаг или ответ своими словами, а AI-репетитор проверит математическую строгость и укажет на потерянные знаки:", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                        user_step_input,
                        ft.FilledButton(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.AUTO_AWESOME, size=16),
                                    ft.Text("Проверить решение с репетитором", size=13, weight=ft.FontWeight.BOLD),
                                ],
                                spacing=8,
                                tight=True,
                            ),
                            style=ft.ButtonStyle(bgcolor=ft.Colors.INDIGO_600),
                            on_click=on_verify_step,
                        ),
                        feedback_container,
                    ],
                    spacing=10,
                ),
                padding=16,
            ),
            elevation=2,
        )

        # 2. Practice Mode: Similar Problems Generator
        practice_tasks = []
        try:
            var = engine.sp.Symbol(var_str)
            expr = engine.parse_math(expr_str, var)
            point = engine.parse_math(point_str, var)
            indet = engine.detect_indeterminacy(expr, var, point)
            practice_tasks = engine.get_practice_problems(indet, expr_str, var_str)
        except Exception:
            practice_tasks = engine.get_practice_problems(None, expr_str, var_str)

        practice_controls = [
            ft.Row(
                controls=[
                    ft.Icon(ft.Icons.FITNESS_CENTER, color=ft.Colors.GREEN_400, size=20),
                    ft.Text("Закрепление: 3 похожие задачи для тренировки", weight=ft.FontWeight.BOLD, size=15),
                ],
                spacing=8,
                tight=True,
            ),
            ft.Text("Решите примеры самостоятельно и введите ответ для моментальной самопроверки:", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
        ]

        for i, task in enumerate(practice_tasks, 1):
            ans_input = ft.TextField(
                hint_text="Ваш ответ",
                width=110,
                dense=True,
                border=ft.OutlineInputBorder(border_radius=8),
            )
            result_label = ft.Text("", size=12, weight=ft.FontWeight.BOLD)

            def check_ans(ev, t=task, inp=ans_input, lbl=result_label):
                u_val = (inp.value or "").strip().lower().replace(" ", "")
                c_val = t["answer"].strip().lower().replace(" ", "")
                if u_val == c_val:
                    lbl.value = "Верно! 🎉"
                    lbl.color = ft.Colors.GREEN_400
                else:
                    lbl.value = f"Неверно (ответ {t['answer']})"
                    lbl.color = ft.Colors.RED_400
                self.page.update()

            def load_task_into_calc(ev, t=task):
                self.expr_input.value = t["expr"]
                self.var_input.value = "x"
                self.point_input.value = t["point"]
                self.dir_dropdown.value = "+-"
                self.update_live_preview()
                self.update_chip_highlights()
                self.nav_bar.selected_index = 0
                self.content_container.content = self.calc_view
                self.page.update()
                self.on_calculate_click(None)

            practice_controls.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text(f"Задача #{i}: lim (x → {task['point']}) [ {task['expr']} ]", weight=ft.FontWeight.BOLD, size=13),
                                    ft.IconButton(
                                        icon=ft.Icons.PLAY_ARROW,
                                        icon_size=18,
                                        tooltip="Решить в калькуляторе",
                                        on_click=lambda ev, t=task: load_task_into_calc(ev, t),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Text(f"Подсказка: {task['tip']}", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Row(
                                controls=[
                                    ans_input,
                                    ft.OutlinedButton("Проверить", on_click=lambda ev, t=task, inp=ans_input, lbl=result_label: check_ans(ev, t, inp, lbl)),
                                    result_label,
                                ],
                                spacing=8,
                            ),
                        ],
                        spacing=6,
                    ),
                    padding=12,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                    border_radius=10,
                    border=ft.Border.all(0.8, ft.Colors.OUTLINE_VARIANT),
                )
            )

        practice_card = ft.Card(
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            content=ft.Container(
                content=ft.Column(controls=practice_controls, spacing=10),
                padding=16,
            ),
            elevation=2,
        )

        return ft.ListView(
            expand=True,
            spacing=12,
            controls=[
                tutor_step_card,
                practice_card,
            ],
        )

    # -------------------------------------------------------------
    # Handbook View
    # -------------------------------------------------------------
    def load_preset(self, p: dict):
        self.expr_input.value = p["expr"]
        self.var_input.value = p["var"]
        self.point_input.value = p["point"]
        self.dir_dropdown.value = p["dir"]
        self.update_live_preview()
        self.update_chip_highlights()
        self.nav_bar.selected_index = 0
        self.content_container.content = self.calc_view
        self.page.update()
        self.on_calculate_click(None)

    def on_handbook_search_change(self, e):
        self.handbook_search_query = (e.control.value or "").strip().lower()
        self.content_container.content = self.build_handbook_view()
        self.page.update()

    def set_handbook_category(self, cat_name: str):
        self.handbook_category_filter = cat_name
        self.content_container.content = self.build_handbook_view()
        self.page.update()

    def build_handbook_view(self) -> ft.Control:
        search_field = ft.TextField(
            hint_text="Поиск формул, пределов, функций...",
            value=self.handbook_search_query,
            prefix_icon=ft.Icons.SEARCH,
            border=ft.OutlineInputBorder(border_radius=12),
            dense=True,
            content_padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            border_color=ft.Colors.OUTLINE_VARIANT,
            on_change=self.on_handbook_search_change,
        )

        # Category Filter Chips
        cat_chips = []
        all_cats = [
            "Все",
            "Замечательные пределы",
            "Экспоненты и логарифмы",
            "Тригонометрия",
            "Рациональные и иррациональные",
            "Односторонние пределы и разрывы",
        ]
        for cat_name in all_cats:
            is_active = (self.handbook_category_filter == cat_name)
            short_label = cat_name.replace(" и логарифмы", "").replace(" и иррациональные", "").replace(" и разрывы", "")
            cat_chips.append(
                ft.Container(
                    content=ft.Text(
                        short_label,
                        size=11,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.WHITE if is_active else ft.Colors.ON_SURFACE,
                    ),
                    padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                    bgcolor=ft.Colors.PRIMARY if is_active else ft.Colors.SURFACE_CONTAINER_HIGH,
                    border_radius=8,
                    border=ft.Border.all(1, ft.Colors.PRIMARY if is_active else ft.Colors.OUTLINE_VARIANT),
                    ink=True,
                    on_click=lambda e, c=cat_name: self.set_handbook_category(c),
                )
            )

        cat_chips_row = ft.Row(controls=cat_chips, scroll=ft.ScrollMode.ADAPTIVE, spacing=6)

        items = [search_field, cat_chips_row]
        q = self.handbook_search_query.strip().lower()

        # Presets by category
        for cat in presets.CATEGORIES:
            cat_name = cat["category"]
            if self.handbook_category_filter != "Все" and self.handbook_category_filter != cat_name:
                continue

            cat_cards = []
            for p in cat["items"]:
                if q and (
                    q not in p["title"].lower()
                    and q not in p["formula"].lower()
                    and q not in p["desc"].lower()
                    and q not in p["expr"].lower()
                ):
                    continue

                cat_cards.append(
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Container(
                                            content=ft.Text(
                                                p["title"],
                                                weight=ft.FontWeight.BOLD,
                                                size=13,
                                                color=ft.Colors.ON_SURFACE,
                                            ),
                                            expand=True,
                                        ),
                                        ft.Container(
                                            content=ft.Text(f"= {p['result']}", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                            bgcolor=ft.Colors.INDIGO,
                                            padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                                            border_radius=6,
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    wrap=True,
                                ),
                                ft.Text(p["formula"], size=13, color=ft.Colors.PRIMARY, weight=ft.FontWeight.W_600),
                                ft.Text(p["desc"], size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                                ft.Row(
                                    controls=[
                                        ft.FilledTonalButton(
                                            content=ft.Row(
                                                controls=[ft.Icon(ft.Icons.PLAY_ARROW, size=16), ft.Text("Решить в калькуляторе", size=12)],
                                                spacing=4,
                                                tight=True,
                                            ),
                                            style=ft.ButtonStyle(
                                                shape=ft.RoundedRectangleBorder(radius=8),
                                                padding=ft.Padding.symmetric(horizontal=10, vertical=6),
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
                        margin=ft.Margin.only(bottom=8, left=6, right=6),
                        bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                        border_radius=12,
                        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                    )
                )

            if cat_cards:
                items.append(
                    ft.Container(
                        content=ft.ExpansionTile(
                            title=ft.Text(cat["category"], weight=ft.FontWeight.BOLD, size=14, color=ft.Colors.ON_SURFACE),
                            leading=ft.Icon(ft.Icons.FUNCTIONS, color=ft.Colors.INDIGO_ACCENT, size=20),
                            text_color=ft.Colors.ON_SURFACE,
                            icon_color=ft.Colors.INDIGO_ACCENT,
                            collapsed_text_color=ft.Colors.ON_SURFACE,
                            collapsed_icon_color=ft.Colors.INDIGO_ACCENT,
                            bgcolor=ft.Colors.TRANSPARENT,
                            collapsed_bgcolor=ft.Colors.TRANSPARENT,
                            shape=ft.Border.all(0, ft.Colors.TRANSPARENT),
                            collapsed_shape=ft.Border.all(0, ft.Colors.TRANSPARENT),
                            controls=cat_cards,
                            expanded=(self.handbook_category_filter != "Все" or bool(q)),
                        ),
                        bgcolor=ft.Colors.SURFACE_CONTAINER,
                        border_radius=14,
                        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                        padding=ft.Padding.only(left=4, right=4, bottom=4),
                        margin=ft.Margin.only(bottom=8),
                    )
                )

        # Equivalents Table Card
        equiv_rows = [
            ft.DataRow(
                color={
                    "hovered": ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    "": ft.Colors.SURFACE_CONTAINER_LOW,
                },
                cells=[
                    ft.DataCell(ft.Text(e["source"], weight=ft.FontWeight.BOLD, size=12, color=ft.Colors.ON_SURFACE)),
                    ft.DataCell(ft.Text("~", color=ft.Colors.PRIMARY, size=14, weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(e["equiv"], color=ft.Colors.PRIMARY, weight=ft.FontWeight.BOLD, size=12)),
                    ft.DataCell(ft.Text(e["cond"], size=11, color=ft.Colors.ON_SURFACE_VARIANT)),
                ],
            )
            for e in presets.EQUIVALENCES
        ]

        equiv_table = ft.DataTable(
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            heading_row_color=ft.Colors.SURFACE_CONTAINER_HIGH,
            data_row_color={
                "hovered": ft.Colors.SURFACE_CONTAINER_HIGHEST,
                "": ft.Colors.SURFACE_CONTAINER_LOW,
            },
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=10,
            columns=[
                ft.DataColumn(ft.Text("Функция", weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE, size=12)),
                ft.DataColumn(ft.Text("", color=ft.Colors.ON_SURFACE)),
                ft.DataColumn(ft.Text("Эквивалент", weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY, size=12)),
                ft.DataColumn(ft.Text("Условие", weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE_VARIANT, size=12)),
            ],
            rows=equiv_rows,
            heading_row_height=36,
            data_row_min_height=32,
            data_row_max_height=36,
        )

        items.append(
            ft.Container(
                content=ft.ExpansionTile(
                    title=ft.Text("Таблица эквивалентных бесконечно малых", weight=ft.FontWeight.BOLD, size=14, color=ft.Colors.ON_SURFACE),
                    leading=ft.Icon(ft.Icons.AUTO_AWESOME, color=ft.Colors.AMBER_400, size=20),
                    text_color=ft.Colors.ON_SURFACE,
                    icon_color=ft.Colors.AMBER_400,
                    collapsed_text_color=ft.Colors.ON_SURFACE,
                    collapsed_icon_color=ft.Colors.AMBER_400,
                    bgcolor=ft.Colors.TRANSPARENT,
                    collapsed_bgcolor=ft.Colors.TRANSPARENT,
                    shape=ft.Border.all(0, ft.Colors.TRANSPARENT),
                    collapsed_shape=ft.Border.all(0, ft.Colors.TRANSPARENT),
                    controls=[
                        ft.Container(
                            content=ft.Row(controls=[equiv_table], scroll=ft.ScrollMode.ADAPTIVE, alignment=ft.MainAxisAlignment.CENTER),
                            padding=8,
                            alignment=ft.Alignment.CENTER,
                        )
                    ],
                ),
                bgcolor=ft.Colors.SURFACE_CONTAINER,
                border_radius=14,
                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                padding=ft.Padding.only(left=4, right=4, bottom=4),
                margin=ft.Margin.only(bottom=8),
            )
        )

        # Indeterminacies Guide
        indet_cards = []
        for ind in presets.INDETERMINACY_TABLE:
            indet_cards.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Container(
                                        content=ft.Text(ind["type"], weight=ft.FontWeight.BOLD, size=13, color=ft.Colors.AMBER_300),
                                        padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                                        border_radius=6,
                                        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                                    ),
                                    ft.Text("Тип неопределенности", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                                ],
                                spacing=8,
                                alignment=ft.MainAxisAlignment.START,
                            ),
                            ft.Text(ind["methods"], size=12, color=ft.Colors.ON_SURFACE),
                        ],
                        spacing=6,
                    ),
                    padding=10,
                    margin=ft.Margin.only(bottom=8, left=6, right=6),
                    bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                    border_radius=10,
                    border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                )
            )

        items.append(
            ft.Container(
                content=ft.ExpansionTile(
                    title=ft.Text("Таблица 7 типов неопределенностей", weight=ft.FontWeight.BOLD, size=14, color=ft.Colors.ON_SURFACE),
                    leading=ft.Icon(ft.Icons.HELP_OUTLINE, color=ft.Colors.CYAN_400, size=20),
                    text_color=ft.Colors.ON_SURFACE,
                    icon_color=ft.Colors.CYAN_400,
                    collapsed_text_color=ft.Colors.ON_SURFACE,
                    collapsed_icon_color=ft.Colors.CYAN_400,
                    bgcolor=ft.Colors.TRANSPARENT,
                    collapsed_bgcolor=ft.Colors.TRANSPARENT,
                    shape=ft.Border.all(0, ft.Colors.TRANSPARENT),
                    collapsed_shape=ft.Border.all(0, ft.Colors.TRANSPARENT),
                    controls=indet_cards,
                ),
                bgcolor=ft.Colors.SURFACE_CONTAINER,
                border_radius=14,
                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                padding=ft.Padding.only(left=4, right=4, bottom=4),
                margin=ft.Margin.only(bottom=8),
            )
        )

        return ft.Container(
            content=ft.ListView(
                expand=True,
                spacing=10,
                controls=items,
            ),
            bgcolor="#0B0F17",
            expand=True,
        )

    # -------------------------------------------------------------
    # History & About View
    # -------------------------------------------------------------
    def build_history_view(self) -> ft.Control:
        history_items = []

        def clear_history(e):
            def confirm_clear(ev):
                self.history.clear()
                self.page.pop_dialog()
                self.content_container.content = self.build_history_view()
                self.page.update()
                self.show_toast("История очищена 🗑️")

            def cancel_clear(ev):
                self.page.pop_dialog()

            dialog = ft.AlertDialog(
                title=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.DELETE_SWEEP, color=ft.Colors.ERROR, size=20),
                        ft.Text("Очистить историю?", weight=ft.FontWeight.BOLD, size=16),
                    ],
                    spacing=8,
                    tight=True,
                ),
                content=ft.Text("Все сохраненные вычисления будут удалены из истории.", size=13),
                actions=[
                    ft.TextButton("Отмена", on_click=cancel_clear),
                    ft.FilledButton(
                        "Очистить",
                        style=ft.ButtonStyle(bgcolor=ft.Colors.ERROR),
                        on_click=confirm_clear,
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            self.page.show_dialog(dialog)

        def set_history_filter(val: str):
            self.history_filter = val
            self.content_container.content = self.build_history_view()
            self.page.update()

        clear_btn = ft.OutlinedButton(
            content=ft.Row(
                controls=[ft.Icon(ft.Icons.DELETE_SWEEP, size=15), ft.Text("Очистить", size=12)],
                spacing=4,
                tight=True,
            ),
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
            on_click=clear_history,
        )

        fav_count = len([h for h in self.history if h.get("favorite")])
        filter_row = ft.Row(
            controls=[
                ft.Container(
                    content=ft.Text(
                        f"Все ({len(self.history)})",
                        size=12,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.WHITE if self.history_filter == "all" else ft.Colors.ON_SURFACE,
                    ),
                    padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                    bgcolor=ft.Colors.PRIMARY if self.history_filter == "all" else ft.Colors.SURFACE_CONTAINER_HIGH,
                    border_radius=8,
                    border=ft.Border.all(1, ft.Colors.PRIMARY if self.history_filter == "all" else ft.Colors.OUTLINE_VARIANT),
                    ink=True,
                    on_click=lambda e: set_history_filter("all"),
                ),
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.STAR, size=14, color=ft.Colors.AMBER_400),
                            ft.Text(
                                f"Избранное ({fav_count})",
                                size=12,
                                weight=ft.FontWeight.W_600,
                                color=ft.Colors.WHITE if self.history_filter == "fav" else ft.Colors.ON_SURFACE,
                            ),
                        ],
                        spacing=4,
                        tight=True,
                    ),
                    padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                    bgcolor=ft.Colors.PRIMARY if self.history_filter == "fav" else ft.Colors.SURFACE_CONTAINER_HIGH,
                    border_radius=8,
                    border=ft.Border.all(1, ft.Colors.PRIMARY if self.history_filter == "fav" else ft.Colors.OUTLINE_VARIANT),
                    ink=True,
                    on_click=lambda e: set_history_filter("fav"),
                ),
                ft.Container(expand=True),
                clear_btn,
            ],
            alignment=ft.MainAxisAlignment.START,
            wrap=True,
        )
        history_items.append(filter_row)

        displayed_list = self.history if self.history_filter == "all" else [h for h in self.history if h.get("favorite")]

        if not displayed_list:
            history_items.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Container(
                                content=ft.Icon(ft.Icons.HISTORY_ROUNDED, size=48, color=ft.Colors.INDIGO_ACCENT),
                                padding=12,
                                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                                shape=ft.BoxShape.CIRCLE,
                            ),
                            ft.Text("История пуста", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE),
                            ft.Text(
                                "Здесь будут сохраняться вычисленные вами пределы с подробными результатами и метками времени.",
                                size=12,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.OutlinedButton(
                                content=ft.Row(
                                    controls=[ft.Icon(ft.Icons.PLAY_ARROW, size=15), ft.Text("Решить первый пример", size=12)],
                                    spacing=4,
                                    tight=True,
                                ),
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                                on_click=self.load_random_example,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    padding=24,
                    margin=ft.Margin.symmetric(vertical=10),
                    bgcolor=ft.Colors.SURFACE_CONTAINER,
                    border_radius=16,
                    border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
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
                self.update_chip_highlights()
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

            res_display = item["result"]
            if not res_display.startswith("✨"):
                res_display = f"= {res_display}"

            history_items.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Text(f"lim ({d_label}) [{item['expr']}]", weight=ft.FontWeight.BOLD, size=13, color=ft.Colors.ON_SURFACE, overflow=ft.TextOverflow.ELLIPSIS, max_lines=2),
                                    ft.Text(f"Время: {item.get('time', '--:--')}", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            ft.Row(
                                controls=[
                                    ft.Container(
                                        content=ft.Text(res_display, weight=ft.FontWeight.BOLD, size=13, color=ft.Colors.PRIMARY),
                                        padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                                        border_radius=6,
                                        border=ft.Border.all(0.8, ft.Colors.OUTLINE_VARIANT),
                                    ),
                                    fav_icon,
                                ],
                                spacing=4,
                                tight=True,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=ft.Padding.symmetric(horizontal=12, vertical=10),
                    bgcolor=ft.Colors.SURFACE_CONTAINER,
                    border_radius=12,
                    border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                    ink=True,
                    on_click=restore_item,
                )
            )

        # About Card at the bottom of History tab
        about_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.VERIFIED_USER_OUTLINED, color=ft.Colors.INDIGO_ACCENT, size=20),
                            ft.Text("Об авторе и проекте", weight=ft.FontWeight.BOLD, size=14, color=ft.Colors.ON_SURFACE),
                        ],
                        spacing=8,
                    ),
                    ft.Text(
                        "LimitApp v1.6.0 AI Tutor Pro — Нарницкий Роман (никнейм Syrok).\n"
                        "Умный интерактивный репетитор по высшей математике: пошаговый расчет пределов, "
                        "визуальное исследование ε-δ, сравнение методов и интеграция с Google Gemini AI.",
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Row(
                        controls=[
                            ft.FilledTonalButton(
                                content=ft.Row([ft.Icon(ft.Icons.SEND, size=14), ft.Text("Telegram: @syrok_dev", size=11)], spacing=4, tight=True),
                                url="https://t.me/syrok_dev",
                            ),
                            ft.FilledTonalButton(
                                content=ft.Row([ft.Icon(ft.Icons.CODE, size=14), ft.Text("GitHub Репозиторий", size=11)], spacing=4, tight=True),
                                url="https://github.com/MaloyDevil/limitapp",
                            ),
                        ],
                        spacing=8,
                        wrap=True,
                    ),
                ],
                spacing=10,
            ),
            padding=16,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            border_radius=14,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        )
        history_items.append(about_card)

        return ft.Container(
            content=ft.ListView(
                expand=True,
                spacing=10,
                controls=history_items,
            ),
            bgcolor="#0B0F17",
            expand=True,
        )


def main(page: ft.Page):
    LimitApp(page)


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
