"""
LimitApp - Мобильный калькулятор математических пределов
Создатель: Нарницкий Роман (никнейм Syrok)
Стек: Python, SymPy, Flet (Material 3 / Flutter Engine)
"""

import sys
import os
import json
import random
from datetime import datetime
import flet as ft

import engine
import presets

_base_dir = os.path.dirname(os.path.abspath(__file__))
ICON_PNG = os.path.join(_base_dir, "icon.png") if os.path.exists(os.path.join(_base_dir, "icon.png")) else os.path.join(_base_dir, "icon.jpg")
ICON_ICO = os.path.join(_base_dir, "icon.ico") if os.path.exists(os.path.join(_base_dir, "icon.ico")) else ICON_PNG
ICON_PATH = ICON_PNG


class LimitApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.history = []
        self.history_filter = "all"  # "all" or "fav"
        self.handbook_search_query = ""

        # Configure window & page
        self.page.title = "LimitApp | Калькулятор Пределов"
        if hasattr(self.page, "window"):
            self.page.window.width = 420
            self.page.window.height = 860
            self.page.window.min_width = 360
            self.page.window.min_height = 640
            self.page.window.resizable = True
            try:
                self.page.window.icon = ICON_ICO if os.path.exists(ICON_ICO) else ICON_PNG
            except Exception:
                pass

        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 0

        # UI Controls for Calculator
        self.expr_input = ft.TextField(
            label="Функция f(x)",
            hint_text="Например: sin(x)/x или (1+1/x)^x",
            value="sin(x)/x",
            prefix_icon=ft.Icons.FUNCTIONS,
            border_radius=12,
            autofocus=True,
            expand=True,
            on_submit=self.on_calculate_click,
        )

        self.var_input = ft.TextField(
            label="Переменная",
            value="x",
            width=90,
            text_align=ft.TextAlign.CENTER,
            border_radius=12,
        )

        self.point_input = ft.TextField(
            label="Стремится к (x₀)",
            value="0",
            hint_text="0, oo, 1...",
            border_radius=12,
            expand=True,
            on_submit=self.on_calculate_click,
        )

        self.dir_dropdown = ft.Dropdown(
            label="Направление",
            value="+-",
            border_radius=12,
            options=[
                ft.dropdown.Option("+-", "Двусторонний (x → x₀)"),
                ft.dropdown.Option("+", "Справа (x → x₀⁺)"),
                ft.dropdown.Option("-", "Слева (x → x₀⁻)"),
            ],
            expand=True,
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
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
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
            ft.Image(
                src=ICON_PNG,
                width=34,
                height=34,
                fit=ft.BoxFit.CONTAIN,
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
                        content=ft.Text("PRO", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        bgcolor=ft.Colors.INDIGO,
                        padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                        border_radius=8,
                    ),
                ],
            ),
            actions=[
                ft.IconButton(
                    icon=ft.Icons.CASINO_OUTLINED,
                    tooltip="Случайный пример",
                    on_click=self.load_random_example,
                ),
                self.theme_btn,
            ],
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            elevation=2,
        )

        self.page.appbar = self.app_bar
        self.page.navigation_bar = self.nav_bar
        self.page.add(self.content_container)

    def toggle_theme(self, e):
        if self.page.theme_mode == ft.ThemeMode.DARK:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.theme_btn.icon = ft.Icons.DARK_MODE
        else:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.theme_btn.icon = ft.Icons.LIGHT_MODE
        self.page.update()

    def show_toast(self, message: str):
        self.page.show_dialog(ft.SnackBar(ft.Text(message)))

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

    def insert_symbol(self, sym: str):
        if sym == "CLEAR":
            self.expr_input.value = ""
        elif sym == "BACK":
            val = self.expr_input.value or ""
            known_tokens = [
                "arcsin(", "arccos(", "arctg(", "sinh(", "cosh(",
                "sin(", "cos(", "tan(", "cot(", "ctg(",
                "sqrt(", "abs(", "exp(", "log(", "ln(",
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
        else:
            self.expr_input.value = (self.expr_input.value or "") + sym
        self._focus_control(self.expr_input)
        self.page.update()

    def insert_point(self, val: str):
        self.point_input.value = val
        self._focus_control(self.point_input)
        self.page.update()

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
        self.page.update()
        self.show_toast("Поля очищены")

    def make_key(self, code: str, label: str, ktype: str) -> ft.Control:
        if ktype == "clear":
            content = ft.Text(label, weight=ft.FontWeight.BOLD, size=15, color=ft.Colors.ON_ERROR_CONTAINER)
            bgcolor = ft.Colors.ERROR_CONTAINER
            border = ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)
        elif ktype == "back":
            content = ft.Icon(ft.Icons.BACKSPACE_OUTLINED, size=18, color=ft.Colors.ON_SECONDARY_CONTAINER)
            bgcolor = ft.Colors.SECONDARY_CONTAINER
            border = ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)
        elif ktype == "var":
            content = ft.Text(label, weight=ft.FontWeight.BOLD, italic=True, size=15, color=ft.Colors.ON_PRIMARY_CONTAINER)
            bgcolor = ft.Colors.PRIMARY_CONTAINER
            border = ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)
        elif ktype == "func":
            content = ft.Text(label, weight=ft.FontWeight.W_600, size=13, color=ft.Colors.PRIMARY)
            bgcolor = ft.Colors.SURFACE_CONTAINER_HIGH
            border = ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)
        else:  # "op"
            content = ft.Text(label, weight=ft.FontWeight.BOLD, size=16, color=ft.Colors.ON_SURFACE)
            bgcolor = ft.Colors.SURFACE_CONTAINER_HIGHEST
            border = ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)

        return ft.Container(
            content=content,
            alignment=ft.Alignment.CENTER,
            height=40,
            expand=1,
            bgcolor=bgcolor,
            border_radius=9,
            border=border,
            ink=True,
            on_click=lambda e, s=code: self.insert_symbol(s),
        )

    def build_calculator_view(self) -> ft.Control:
        row1_keys = [
            ("sin(", "sin", "func"),
            ("cos(", "cos", "func"),
            ("tan(", "tg", "func"),
            ("cot(", "ctg", "func"),
            ("CLEAR", "C", "clear"),
        ]
        row2_keys = [
            ("ln(", "ln", "func"),
            ("sqrt(", "√", "func"),
            ("^", "^", "op"),
            ("abs(", "|x|", "func"),
            ("BACK", "⌫", "back"),
        ]
        row3_keys = [
            ("x", "x", "var"),
            ("e", "e", "var"),
            ("pi", "π", "var"),
            ("(", "(", "op"),
            (")", ")", "op"),
        ]
        row4_keys = [
            ("oo", "∞", "var"),
            ("+", "+", "op"),
            ("-", "−", "op"),
            ("*", "×", "op"),
            ("/", "÷", "op"),
        ]

        extra_keys = [
            ("arcsin(", "arcsin", "func"),
            ("arccos(", "arccos", "func"),
            ("atan(", "arctg", "func"),
            ("exp(", "exp", "func"),
            ("log(", "log", "func"),
        ]

        self.extra_keyboard_row = ft.Row(
            controls=[self.make_key(c, l, t) for c, l, t in extra_keys],
            spacing=5,
            visible=False,
        )

        def toggle_extra(e):
            self.extra_keyboard_row.visible = not self.extra_keyboard_row.visible
            self.extra_toggle_btn.icon = (
                ft.Icons.EXPAND_LESS if self.extra_keyboard_row.visible else ft.Icons.EXPAND_MORE
            )
            self.extra_toggle_btn.content = (
                "Скрыть f(x)" if self.extra_keyboard_row.visible else "Доп. f(x)"
            )
            self.page.update()

        self.extra_toggle_btn = ft.TextButton(
            content="Доп. f(x)",
            icon=ft.Icons.EXPAND_MORE,
            style=ft.ButtonStyle(
                padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                text_style=ft.TextStyle(size=11, weight=ft.FontWeight.W_600),
            ),
            on_click=toggle_extra,
        )

        keypad_container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.KEYBOARD_ALT_OUTLINED, size=16, color=ft.Colors.PRIMARY),
                                    ft.Text("Клавиатура символов", size=12, weight=ft.FontWeight.BOLD),
                                ],
                                spacing=6,
                            ),
                            self.extra_toggle_btn,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    self.extra_keyboard_row,
                    ft.Row(controls=[self.make_key(c, l, t) for c, l, t in row1_keys], spacing=5),
                    ft.Row(controls=[self.make_key(c, l, t) for c, l, t in row2_keys], spacing=5),
                    ft.Row(controls=[self.make_key(c, l, t) for c, l, t in row3_keys], spacing=5),
                    ft.Row(controls=[self.make_key(c, l, t) for c, l, t in row4_keys], spacing=5),
                ],
                spacing=5,
            ),
            padding=10,
            border_radius=14,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        )

        quick_points = [("0", "0"), ("oo", "+∞"), ("-oo", "-∞"), ("1", "1"), ("pi", "π"), ("e", "e")]
        point_chips = []
        for val, label in quick_points:
            chip = ft.Container(
                content=ft.Text(f"x₀ = {label}", size=12, weight=ft.FontWeight.W_600, color=ft.Colors.ON_PRIMARY_CONTAINER),
                padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                bgcolor=ft.Colors.PRIMARY_CONTAINER,
                border_radius=8,
                border=ft.Border.all(0.8, ft.Colors.OUTLINE_VARIANT),
                ink=True,
                on_click=lambda e, v=val: self.insert_point(v),
            )
            point_chips.append(chip)

        calc_btn = ft.FilledButton(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.FLASH_ON, color=ft.Colors.AMBER_300, size=20),
                    ft.Text("Рассчитать предел", weight=ft.FontWeight.BOLD, size=15),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.INDIGO_600,
                color=ft.Colors.WHITE,
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=14,
            ),
            on_click=self.on_calculate_click,
        )

        return ft.ListView(
            expand=True,
            spacing=14,
            controls=[
                ft.Container(
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text("Функция и переменная", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE_VARIANT),
                                    ft.Row(
                                        controls=[
                                            ft.TextButton(
                                                content="🎲 Пример",
                                                style=ft.ButtonStyle(
                                                    padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                                                    text_style=ft.TextStyle(size=11, weight=ft.FontWeight.W_600),
                                                ),
                                                on_click=self.load_random_example,
                                            ),
                                            ft.TextButton(
                                                content="Очистить",
                                                style=ft.ButtonStyle(
                                                    padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                                                    text_style=ft.TextStyle(size=11, weight=ft.FontWeight.W_600),
                                                ),
                                                on_click=self.clear_inputs,
                                            ),
                                        ],
                                        spacing=2,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Row(controls=[self.expr_input, self.var_input], spacing=8),
                            keypad_container,
                            ft.Divider(height=1, thickness=0.5),
                            ft.Text("Параметры предела", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Row(controls=[self.point_input, self.dir_dropdown], spacing=8),
                            ft.Row(
                                controls=[
                                    ft.Text("x₀:", size=12, weight=ft.FontWeight.W_600, color=ft.Colors.ON_SURFACE_VARIANT),
                                    *point_chips,
                                ],
                                spacing=6,
                                wrap=True,
                            ),
                            ft.Container(height=4),
                            calc_btn,
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

    def on_calculate_click(self, e):
        expr_text = self.expr_input.value.strip() if self.expr_input.value else ""
        if not expr_text:
            self.show_toast("Пожалуйста, введите функцию f(x)")
            return

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
                                        ft.Text("Не удалось вычислить", weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400),
                                    ]
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
                        ft.Text("= ", size=30, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
                        ft.Text(ans_text, size=30, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
                        ft.Text(f" ({numeric_text})" if numeric_text else "", size=16, color=ft.Colors.ON_SURFACE_VARIANT),
                    ],
                    alignment=ft.MainAxisAlignment.START,
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
                controls=[ft.Icon(ft.Icons.COPY, size=16), ft.Text("Скопировать решение", size=13)],
                spacing=6,
            ),
            on_click=copy_result,
        )

        header_items.append(
            ft.Row(
                controls=[fav_btn, copy_btn],
                alignment=ft.MainAxisAlignment.END,
                spacing=6,
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

    def load_preset(self, p: dict):
        self.expr_input.value = p["expr"]
        self.var_input.value = p["var"]
        self.point_input.value = p["point"]
        self.dir_dropdown.value = p["dir"]
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
            border_radius=12,
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
                                                ),
                                                on_click=lambda e, pr=p: self.load_preset(pr),
                                            )
                                        ],
                                        alignment=ft.MainAxisAlignment.END,
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
                                            ),
                                            on_click=lambda e, pr=p: self.load_preset(pr),
                                        )
                                    ],
                                    alignment=ft.MainAxisAlignment.END,
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

    def build_history_view(self) -> ft.Control:
        if not self.history:
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Image(
                            src=ICON_PNG,
                            width=64,
                            height=64,
                            fit=ft.BoxFit.CONTAIN,
                            opacity=0.75,
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

    def build_about_view(self) -> ft.Control:
        app_icon_control = (
            ft.Container(
                content=ft.Image(
                    src=ICON_PNG,
                    width=68,
                    height=68,
                    fit=ft.BoxFit.CONTAIN,
                ),
                width=68,
                height=68,
                shadow=ft.BoxShadow(blur_radius=16, color=ft.Colors.with_opacity(0.35, ft.Colors.BLACK)),
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
                                                            content=ft.Text("PRO", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                                            bgcolor=ft.Colors.INDIGO,
                                                            padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                                            border_radius=6,
                                                        ),
                                                    ],
                                                    spacing=6,
                                                ),
                                                ft.Text("Математический калькулятор пределов", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                                                ft.Row(
                                                    controls=[
                                                        ft.Icon(ft.Icons.CHECK_CIRCLE, size=14, color=ft.Colors.GREEN_400),
                                                        ft.Text("Версия 1.2 • Полный offline режим", size=11, color=ft.Colors.GREEN_400),
                                                    ],
                                                    spacing=4,
                                                ),
                                            ],
                                            spacing=2,
                                        ),
                                    ],
                                    spacing=14,
                                ),
                                ft.Divider(height=1, thickness=0.5),
                                ft.Text(
                                    "LimitApp — высокоточный аналитический калькулятор математических пределов с пошаговым решением, "
                                    "анализом неопределенностей, интерактивным справочником и функцией избранных вычислений.",
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
                                            width=48,
                                            height=48,
                                            fit=ft.BoxFit.CONTAIN,
                                        ),
                                        width=48,
                                        height=48,
                                        shadow=ft.BoxShadow(blur_radius=8, color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK)),
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
                                        ft.Text("Ключевые возможности", weight=ft.FontWeight.BOLD, size=15),
                                    ],
                                    spacing=8,
                                ),
                                ft.Divider(height=1, thickness=0.5),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=ft.Colors.GREEN_400, size=20),
                                    title=ft.Text("Двусторонние и односторонние пределы", size=13),
                                    subtitle=ft.Text("Расчет при x → x₀, x → x₀⁺ и x → x₀⁻ с пошаговым обоснованием.", size=11),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=ft.Colors.GREEN_400, size=20),
                                    title=ft.Text("Раскрытие 7 типов неопределенностей", size=13),
                                    subtitle=ft.Text("Автоопределение 0/0, ∞/∞, 0·∞, ∞-∞, 1^∞, 0^0, ∞^0 (Лопиталь, Тейлор, эквивалентности).", size=11),
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
                                    title=ft.Text("🎲 Генератор случайных примеров", size=13),
                                    subtitle=ft.Text("Быстрая проверка возможностей и изучение типовых задач с пределами.", size=11),
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
                                ),
                                ft.Divider(height=1, thickness=0.5),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.TERMINAL, size=22),
                                    title=ft.Text("Python 3 & SymPy", weight=ft.FontWeight.W_600, size=13),
                                    subtitle=ft.Text("Символьное дифференцирование, разложения в ряды Тейлора и аналитические пределы.", size=11),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.PHONE_ANDROID, size=22),
                                    title=ft.Text("Flet & Flutter Engine", weight=ft.FontWeight.W_600, size=13),
                                    subtitle=ft.Text("Кроссплатформенный Material Design 3 мобильный интерфейс.", size=11),
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
