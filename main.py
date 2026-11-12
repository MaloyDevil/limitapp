"""
LimitApp - Мобильный калькулятор математических пределов
Создатель: Нарницкий Роман (никнейм Syrok)
Стек: Python, SymPy, Flet (Material 3 / Flutter Engine)
"""

import sys
import os
import json
from datetime import datetime
import flet as ft

import engine
import presets


class LimitApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.history = []

        # Configure window & page
        self.page.title = "LimitApp | Калькулятор Пределов"
        if hasattr(self.page, "window"):
            self.page.window.width = 420
            self.page.window.height = 860
            self.page.window.min_width = 360
            self.page.window.min_height = 640
            self.page.window.resizable = True

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

        self.app_bar = ft.AppBar(
            leading=ft.Container(
                content=ft.Icon(ft.Icons.ALL_INCLUSIVE, color=ft.Colors.AMBER_400),
                padding=ft.Padding.only(left=12),
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
            actions=[self.theme_btn],
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
            self.content_container.content = self.handbook_view
        elif idx == 2:
            self.content_container.content = self.build_history_view()
        elif idx == 3:
            self.content_container.content = self.about_view
        self.page.update()

    def insert_symbol(self, sym: str):
        if sym == "CLEAR":
            self.expr_input.value = ""
        elif sym == "BACK":
            if self.expr_input.value:
                self.expr_input.value = self.expr_input.value[:-1]
        else:
            self.expr_input.value = (self.expr_input.value or "") + sym
        self.expr_input.focus()
        self.page.update()

    def insert_point(self, val: str):
        self.point_input.value = val
        self.point_input.focus()
        self.page.update()

    def build_calculator_view(self) -> ft.Control:
        # Math keyboard chips
        symbols = [
            ("x", "x"), ("+", "+"), ("-", "-"), ("*", "×"),
            ("/", "÷"), ("^", "^"), ("sqrt(", "√"), ("(", "("), (")", ")"),
            ("sin(", "sin"), ("cos(", "cos"), ("tan(", "tg"),
            ("ln(", "ln"), ("e", "e"), ("pi", "π"), ("oo", "∞"),
            ("abs(", "|x|"), ("BACK", "⌫"), ("CLEAR", "C"),
        ]

        keyboard_buttons = []
        for code, label in symbols:
            btn = ft.Container(
                content=ft.Text(label, weight=ft.FontWeight.W_600, size=13),
                padding=ft.Padding.symmetric(horizontal=10, vertical=7),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                border_radius=8,
                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                ink=True,
                on_click=lambda e, s=code: self.insert_symbol(s),
            )
            keyboard_buttons.append(btn)

        keyboard_row = ft.Row(
            controls=keyboard_buttons,
            scroll=ft.ScrollMode.ADAPTIVE,
            spacing=6,
        )

        # Quick point chips
        quick_points = [("0", "0"), ("oo", "+∞"), ("-oo", "-∞"), ("1", "1"), ("pi", "π"), ("e", "e")]
        point_chips = []
        for val, label in quick_points:
            chip = ft.Container(
                content=ft.Text(f"x₀ = {label}", size=12, weight=ft.FontWeight.W_500),
                padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                bgcolor=ft.Colors.PRIMARY_CONTAINER,
                border_radius=6,
                ink=True,
                on_click=lambda e, v=val: self.insert_point(v),
            )
            point_chips.append(chip)

        calc_btn = ft.FilledButton(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.FLASH_ON, color=ft.Colors.AMBER_300),
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
                        spacing=6,
                        controls=[
                            ft.Text("Введите функцию и параметры", size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Row(controls=[self.expr_input, self.var_input], spacing=8),
                            ft.Text("Клавиатура символов:", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                            keyboard_row,
                            ft.Divider(height=1, thickness=0.5),
                            ft.Row(controls=[self.point_input, self.dir_dropdown], spacing=8),
                            ft.Row(controls=point_chips, spacing=6, wrap=True),
                            ft.Container(height=4),
                            calc_btn,
                        ],
                    ),
                    padding=14,
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
            "time": datetime.now().strftime("%H:%M:%S"),
            "expr": expr_text,
            "var": var_text,
            "point": point_text,
            "dir": dir_val,
            "result": res["result_display"],
        })
        if len(self.history) > 50:
            self.history.pop()

        self.page.update()

    def render_result(self, res: dict):
        self.result_container.visible = True
        self.result_container.controls.clear()

        # 1. Main Answer Card
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
            ft.Text(lim_notation, size=13, color=ft.Colors.ON_SURFACE_VARIANT, italic=True),
            ft.Row(
                controls=[
                    ft.Text("= ", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
                    ft.Text(ans_text, size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
                    ft.Text(f" ({numeric_text})" if numeric_text else "", size=16, color=ft.Colors.ON_SURFACE_VARIANT),
                ],
                alignment=ft.MainAxisAlignment.START,
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

        # One-sided limit badges
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

        # Copy button
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

        copy_btn = ft.OutlinedButton(
            content=ft.Row(
                controls=[ft.Icon(ft.Icons.COPY, size=16), ft.Text("Скопировать решение", size=13)],
                spacing=6,
            ),
            on_click=copy_result,
        )

        header_items.append(ft.Row(controls=[copy_btn], alignment=ft.MainAxisAlignment.END))

        main_card = ft.Card(
            content=ft.Container(
                content=ft.Column(controls=header_items, spacing=10),
                padding=16,
            ),
            elevation=3,
        )
        self.result_container.controls.append(main_card)

        # 2. Step-by-Step Breakdown Cards
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

        # 3. Neighborhood Convergence Table
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

    def build_handbook_view(self) -> ft.Control:
        items = []

        # Presets by category
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
                        ft.Icon(ft.Icons.HISTORY, size=64, color=ft.Colors.ON_SURFACE_VARIANT),
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

        clear_btn = ft.OutlinedButton(
            content=ft.Row(
                controls=[ft.Icon(ft.Icons.DELETE_SWEEP, size=16), ft.Text("Очистить историю", size=13)],
                spacing=6,
            ),
            on_click=clear_history,
        )

        history_items.append(
            ft.Row(
                controls=[
                    ft.Text(f"Всего записей: {len(self.history)}", size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                    clear_btn,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
        )

        for item in self.history:
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

            history_items.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Text(f"lim ({d_label}) [{item['expr']}]", weight=ft.FontWeight.BOLD, size=13),
                                    ft.Text(f"Время: {item['time']}", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            ft.Container(
                                content=ft.Text(f"= {item['result']}", weight=ft.FontWeight.BOLD, size=14, color=ft.Colors.PRIMARY),
                                padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                                border_radius=6,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=12,
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
        return ft.ListView(
            expand=True,
            spacing=14,
            controls=[
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.CircleAvatar(
                                            content=ft.Icon(ft.Icons.PERSON, size=32, color=ft.Colors.WHITE),
                                            bgcolor=ft.Colors.INDIGO,
                                            radius=28,
                                        ),
                                        ft.Column(
                                            controls=[
                                                ft.Text("Нарницкий Роман", size=19, weight=ft.FontWeight.BOLD),
                                                ft.Row(
                                                    controls=[
                                                        ft.Container(
                                                            content=ft.Text("Syrok", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                                            bgcolor=ft.Colors.PURPLE,
                                                            padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                                                            border_radius=8,
                                                        ),
                                                        ft.Text("Автор и создатель", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                                                    ],
                                                    spacing=6,
                                                ),
                                            ],
                                            spacing=4,
                                        ),
                                    ],
                                    spacing=14,
                                ),
                                ft.Divider(height=1, thickness=0.5),
                                ft.Text(
                                    "LimitApp — высокоточный мобильный калькулятор математических пределов с пошаговым решением, "
                                    "анализом неопределенностей и встроенным математическим справочником.",
                                    size=13,
                                ),
                            ],
                            spacing=12,
                        ),
                        padding=18,
                    ),
                    elevation=3,
                ),
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
                                    subtitle=ft.Text("Аналитическое дифференцирование, разложения в ряды Тейлора и точные пределы.", size=11),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.PHONE_ANDROID, size=22),
                                    title=ft.Text("Flet & Flutter Engine", weight=ft.FontWeight.W_600, size=13),
                                    subtitle=ft.Text("Кроссплатформенный Material Design 3 мобильный интерфейс.", size=11),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.INTEGRATION_INSTRUCTIONS, size=22),
                                    title=ft.Text("GitHub Actions & APK", weight=ft.FontWeight.W_600, size=13),
                                    subtitle=ft.Text("Готовый workflow для автоматической компиляции Android APK.", size=11),
                                ),
                            ],
                            spacing=8,
                        ),
                        padding=16,
                    )
                ),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Icon(ft.Icons.SECURITY_UPDATE_GOOD, color=ft.Colors.GREEN_400),
                                        ft.Text("Сборка в Android APK", weight=ft.FontWeight.BOLD, size=15),
                                    ],
                                    spacing=8,
                                ),
                                ft.Divider(height=1, thickness=0.5),
                                ft.Text(
                                    "В проект добавлен готовый файл .github/workflows/build-apk.yml. "
                                    "После загрузки проекта в ваш репозиторий GitHub, Actions автоматически "
                                    "соберет готовый APK файл для установки на любой Android телефон!",
                                    size=12,
                                ),
                            ],
                            spacing=10,
                        ),
                        padding=16,
                    )
                ),
            ],
        )


def main(page: ft.Page):
    LimitApp(page)


if __name__ == "__main__":
    ft.run(main)
