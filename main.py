import sys
import asyncio
import subprocess
import os

import flet as ft

class TimerApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "⏱️ PC timer"  # временный заголовок
        self.page.window.width = 440
        self.page.window.height = 600  # хватит без статус-бара
        self.page.window.resizable = False
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE_700)

        if os.path.exists("icon.png"):
            self.page.window.icon = "icon.png"

        self.remaining_seconds = 0
        self.cancelled = False
        self.mode = "shutdown"
        self.task = None
        self.current_language = "ru"
        self.sound_enabled = True

        # --- Словари переводов ---
        self.translations = {
            "ru": {
                "title": "⏱️ Таймер выключения / сна",
                "choose_time": "Выберите время:",
                "hours_label": "Часы:",
                "minutes_label": "Минуты:",
                "action_label": "Действие:",
                "shutdown_btn": "Выключение",
                "sleep_btn": "Спящий режим",
                "start_btn": "Запустить",
                "cancel_btn": "Отменить",
                "warning_title": "⚠️ Внимание",
                "warning_cancel": "Отменить",
                "error_zero_time": "Выберите время больше 0",
                "time_format": "{hours} часов {minutes:02d} минут",
                "remaining_format": "Осталось {h} ч {m:02d} мин",
                "warning_text": "До {action} осталось: {seconds} сек.",
                "action_shutdown": "выключения",
                "action_sleep": "перехода в сон",
            },
            "ua": {
                "title": "⏱️ Таймер вимкнення / сну",
                "choose_time": "Виберіть час:",
                "hours_label": "Години:",
                "minutes_label": "Хвилини:",
                "action_label": "Дія:",
                "shutdown_btn": "Вимкнення",
                "sleep_btn": "Сплячий режим",
                "start_btn": "Запустити",
                "cancel_btn": "Скасувати",
                "warning_title": "⚠️ Увага",
                "warning_cancel": "Скасувати",
                "error_zero_time": "Виберіть час більше 0",
                "time_format": "{hours} годин {minutes:02d} хвилин",
                "remaining_format": "Залишилось {h} год {m:02d} хв",
                "warning_text": "До {action} залишилось: {seconds} сек.",
                "action_shutdown": "вимкнення",
                "action_sleep": "переходу в сон",
            }
        }

        # --- Верхняя строка: динамик + языки ---
        self.sound_btn = ft.IconButton(
            icon=ft.Icons.VOLUME_UP,
            icon_size=20,
            on_click=self.toggle_sound,
            style=ft.ButtonStyle(color=ft.Colors.WHITE),
        )
        self.lang_ru_btn = ft.Button(
            content=ft.Text("RU", size=14, weight=ft.FontWeight.BOLD),
            on_click=lambda e: self.switch_language("ru"),
            style=ft.ButtonStyle(
                padding=ft.Padding(4, 4, 4, 4),
                shape=ft.RoundedRectangleBorder(radius=6),
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_600,
            ),
        )
        self.lang_ua_btn = ft.Button(
            content=ft.Text("UA", size=14, weight=ft.FontWeight.BOLD),
            on_click=lambda e: self.switch_language("ua"),
            style=ft.ButtonStyle(
                padding=ft.Padding(4, 4, 4, 4),
                shape=ft.RoundedRectangleBorder(radius=6),
                color=ft.Colors.GREY_400,
                bgcolor=ft.Colors.TRANSPARENT,
            ),
        )
        top_row = ft.Row(
            [self.sound_btn, ft.Container(expand=True), self.lang_ru_btn, self.lang_ua_btn],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        # Заголовок
        self.title_text = ft.Text(
            self.tr("title"), size=22, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER
        )

        # Выбор времени
        self.choose_time_label = ft.Text(self.tr("choose_time"), size=16)
        self.hours_label = ft.Text(self.tr("hours_label"), size=14)
        self.minutes_label = ft.Text(self.tr("minutes_label"), size=14)
        self.hours_slider = ft.Slider(
            min=0, max=24, value=0, divisions=24,
            label="{value}",
            active_color=ft.Colors.BLUE_400,
            on_change=self.update_time_display,
        )
        self.minutes_slider = ft.Slider(
            min=0, max=59, value=10, divisions=59,
            label="{value}",
            active_color=ft.Colors.BLUE_400,
            on_change=self.update_time_display,
        )
        self.time_display = ft.Text(
            self._format_time(0, 10), size=20, weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER, color=ft.Colors.BLUE_200,
        )

        # Действие
        self.action_label = ft.Text(self.tr("action_label"), size=16)
        self.btn_shutdown_text = ft.Text(self.tr("shutdown_btn"), size=14)
        self.btn_sleep_text = ft.Text(self.tr("sleep_btn"), size=14)
        self.btn_shutdown = ft.Button(
            content=ft.Row([
                ft.Icon(ft.Icons.POWER_SETTINGS_NEW, size=18),
                self.btn_shutdown_text,
            ], alignment=ft.MainAxisAlignment.CENTER),
            on_click=self.set_mode_shutdown,
            style=ft.ButtonStyle(
                padding=ft.Padding(left=16, top=8, right=16, bottom=8),
                shape=ft.RoundedRectangleBorder(radius=8),
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_600,
            ),
        )
        self.btn_sleep = ft.Button(
            content=ft.Row([
                ft.Icon(ft.Icons.BEDTIME, size=18),
                self.btn_sleep_text,
            ], alignment=ft.MainAxisAlignment.CENTER),
            on_click=self.set_mode_sleep,
            style=ft.ButtonStyle(
                padding=ft.Padding(left=16, top=8, right=16, bottom=8),
                shape=ft.RoundedRectangleBorder(radius=8),
                color=ft.Colors.GREY_400,
                bgcolor=ft.Colors.TRANSPARENT,
            ),
        )
        self.mode_toggle = ft.Container(
            content=ft.Row(
                [self.btn_shutdown, self.btn_sleep],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=0,
            ),
            padding=ft.Padding(4, 4, 4, 4),
            border_radius=10,
            bgcolor=ft.Colors.GREY_900,
        )

        # Кнопки запуска/отмены
        self.start_btn_text = ft.Text(self.tr("start_btn"), size=16)
        self.cancel_btn_text = ft.Text(self.tr("cancel_btn"), size=16)
        self.start_btn = ft.Button(
            content=ft.Row(
                [ft.Icon(ft.Icons.PLAY_ARROW, size=20), self.start_btn_text],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            on_click=self.start_timer,
            style=ft.ButtonStyle(
                padding=ft.Padding(left=24, top=12, right=24, bottom=12),
                shape=ft.RoundedRectangleBorder(radius=10),
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_600,
            ),
        )
        self.cancel_btn = ft.Button(
            content=ft.Row(
                [ft.Icon(ft.Icons.CANCEL, size=20), self.cancel_btn_text],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            visible=False,
            on_click=self.cancel_timer,
            style=ft.ButtonStyle(
                padding=ft.Padding(left=24, top=12, right=24, bottom=12),
                shape=ft.RoundedRectangleBorder(radius=10),
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.RED_600,
            ),
        )

        # Диалог предупреждения
        self.warning_title = ft.Text(self.tr("warning_title"), size=20, weight=ft.FontWeight.BOLD)
        self.warning_content = ft.Text("", size=18)
        self.warning_dlg = ft.AlertDialog(
            modal=True,
            title=self.warning_title,
            content=self.warning_content,
            actions=[
                ft.TextButton(
                    self.tr("warning_cancel"),
                    on_click=self.cancel_from_dialog,
                    style=ft.ButtonStyle(color=ft.Colors.RED_400),
                )
            ],
        )

        # Сборка интерфейса (отступ сверху = 10)
        self.page.add(
            ft.Container(
                padding=ft.Padding(left=30, top=10, right=30, bottom=30),
                content=ft.Column(
                    [
                        top_row,
                        self.title_text,
                        ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                        self.choose_time_label,
                        self.time_display,
                        self.hours_label,
                        self.hours_slider,
                        self.minutes_label,
                        self.minutes_slider,
                        self.action_label,
                        self.mode_toggle,
                        ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                        ft.Row([self.start_btn, self.cancel_btn], alignment=ft.MainAxisAlignment.CENTER),
                        # статусная строка полностью удалена
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
        )

    # --- Вспомогательные функции ---
    def tr(self, key):
        return self.translations[self.current_language][key]

    def _format_time(self, hours, minutes):
        return self.tr("time_format").format(hours=hours, minutes=minutes)

    def _format_remaining(self, h, m):
        return self.tr("remaining_format").format(h=h, m=m)

    def apply_language(self):
        self.title_text.value = self.tr("title")
        self.choose_time_label.value = self.tr("choose_time")
        self.hours_label.value = self.tr("hours_label")
        self.minutes_label.value = self.tr("minutes_label")
        self.action_label.value = self.tr("action_label")
        self.btn_shutdown_text.value = self.tr("shutdown_btn")
        self.btn_sleep_text.value = self.tr("sleep_btn")
        self.start_btn_text.value = self.tr("start_btn")
        self.cancel_btn_text.value = self.tr("cancel_btn")
        self.warning_title.value = self.tr("warning_title")
        self.warning_dlg.actions[0].text = self.tr("warning_cancel")
        if self.task is None or self.task.done():
            self.update_time_display()
        self.page.update()

    def switch_language(self, lang):
        self.current_language = lang
        if lang == "ru":
            self.lang_ru_btn.style.color = ft.Colors.WHITE
            self.lang_ru_btn.style.bgcolor = ft.Colors.BLUE_600
            self.lang_ua_btn.style.color = ft.Colors.GREY_400
            self.lang_ua_btn.style.bgcolor = ft.Colors.TRANSPARENT
        else:
            self.lang_ua_btn.style.color = ft.Colors.WHITE
            self.lang_ua_btn.style.bgcolor = ft.Colors.BLUE_600
            self.lang_ru_btn.style.color = ft.Colors.GREY_400
            self.lang_ru_btn.style.bgcolor = ft.Colors.TRANSPARENT
        self.apply_language()

    def toggle_sound(self, e):
        self.sound_enabled = not self.sound_enabled
        self.sound_btn.icon = ft.Icons.VOLUME_UP if self.sound_enabled else ft.Icons.VOLUME_OFF
        self.page.update()

    def set_mode_shutdown(self, e):
        self.mode = "shutdown"
        self._update_toggle_style()

    def set_mode_sleep(self, e):
        self.mode = "sleep"
        self._update_toggle_style()

    def _update_toggle_style(self):
        if self.mode == "shutdown":
            self.btn_shutdown.style.color = ft.Colors.WHITE
            self.btn_shutdown.style.bgcolor = ft.Colors.BLUE_600
            self.btn_sleep.style.color = ft.Colors.GREY_400
            self.btn_sleep.style.bgcolor = ft.Colors.TRANSPARENT
        else:
            self.btn_sleep.style.color = ft.Colors.WHITE
            self.btn_sleep.style.bgcolor = ft.Colors.BLUE_600
            self.btn_shutdown.style.color = ft.Colors.GREY_400
            self.btn_shutdown.style.bgcolor = ft.Colors.TRANSPARENT
        self.page.update()

    def update_time_display(self, e=None):
        if self.task is None or self.task.done():
            hours = int(self.hours_slider.value)
            minutes = int(self.minutes_slider.value)
            self.time_display.value = self._format_time(hours, minutes)
            self.page.update()

    def start_timer(self, e):
        hours = int(self.hours_slider.value)
        minutes = int(self.minutes_slider.value)
        total_seconds = hours * 3600 + minutes * 60
        if total_seconds <= 0:
            # Показываем SnackBar вместо status_text
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(self.tr("error_zero_time")),
                bgcolor=ft.Colors.RED_400,
                duration=3000,
            )
            self.page.snack_bar.open = True
            self.page.update()
            return

        self.remaining_seconds = total_seconds
        self.cancelled = False

        self.btn_shutdown.disabled = True
        self.btn_sleep.disabled = True
        self.hours_slider.disabled = True
        self.minutes_slider.disabled = True
        self.start_btn.visible = False
        self.cancel_btn.visible = True

        h, m = divmod(self.remaining_seconds, 3600)
        m //= 60
        self.time_display.value = self._format_remaining(h, m)
        self.page.update()

        self.task = self.page.run_task(self._countdown)

    async def _countdown(self):
        warning_shown = False
        while self.remaining_seconds > 0 and not self.cancelled:
            await asyncio.sleep(1)
            self.remaining_seconds -= 1

            if self.remaining_seconds % 60 == 0:
                h, m = divmod(self.remaining_seconds, 3600)
                m //= 60
                self.time_display.value = self._format_remaining(h, m)
                self.page.update()

            if self.remaining_seconds <= 60 and not warning_shown:
                warning_shown = True
                await self._show_warning()

            if self.warning_dlg.open:
                action_word = self.tr("action_shutdown") if self.mode == "shutdown" else self.tr("action_sleep")
                self.warning_content.value = self.tr("warning_text").format(
                    action=action_word, seconds=self.remaining_seconds
                )
                self.page.update()

        if not self.cancelled:
            self._execute_action()
        else:
            self._reset_ui()  # без сообщения

    async def _show_warning(self):
        if self.sound_enabled:
            self._play_alert_sound()

        self.page.window.minimized = False
        await self.page.window.to_front()
        self.page.window.always_on_top = True

        action_word = self.tr("action_shutdown") if self.mode == "shutdown" else self.tr("action_sleep")
        self.warning_content.value = self.tr("warning_text").format(
            action=action_word, seconds=60
        )
        self.warning_dlg.open = True
        self.page.update()

    def _play_alert_sound(self):
        try:
            if sys.platform == "win32":
                import winsound
                winsound.Beep(1000, 500)
            else:
                print('\a')
        except Exception:
            pass

    def cancel_from_dialog(self, e):
        self.warning_dlg.open = False
        self.page.update()
        self.cancel_timer(e)

    def cancel_timer(self, e=None):
        self.cancelled = True
        self.warning_dlg.open = False
        self.page.window.always_on_top = False
        self._reset_ui()  # без сообщения

    def _reset_ui(self):
        self.start_btn.visible = True
        self.cancel_btn.visible = False

        self.btn_shutdown.disabled = False
        self.btn_sleep.disabled = False
        self.hours_slider.disabled = False
        self.minutes_slider.disabled = False

        hours, minutes = int(self.hours_slider.value), int(self.minutes_slider.value)
        self.time_display.value = self._format_time(hours, minutes)
        self.page.update()

    def _execute_action(self):
        self.warning_dlg.open = False
        self.page.window.always_on_top = False
        self.page.update()

        if self.mode == "shutdown":
            self._shutdown()
        elif self.mode == "sleep":
            self._sleep()

    def _shutdown(self):
        try:
            if sys.platform == "win32":
                subprocess.run(["shutdown", "/s", "/t", "0"], check=True)
            elif sys.platform.startswith("linux"):
                subprocess.run(["shutdown", "now"], check=True)
            elif sys.platform == "darwin":
                subprocess.run(["sudo", "shutdown", "-h", "now"], check=True)
        except Exception:
            # При ошибке тоже можно показать SnackBar
            self._reset_ui()
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(self.tr("error_action")),
                bgcolor=ft.Colors.RED_400,
                duration=3000,
            )
            self.page.snack_bar.open = True
            self.page.update()

    def _sleep(self):
        try:
            if sys.platform == "win32":
                subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=True)
            elif sys.platform.startswith("linux"):
                subprocess.run(["systemctl", "suspend"], check=True)
            elif sys.platform == "darwin":
                subprocess.run(["pmset", "sleepnow"], check=True)
        except Exception:
            self._reset_ui()
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(self.tr("error_action")),
                bgcolor=ft.Colors.RED_400,
                duration=3000,
            )
            self.page.snack_bar.open = True
            self.page.update()

def main(page: ft.Page):
    TimerApp(page)

if __name__ == "__main__":
    ft.run(main)