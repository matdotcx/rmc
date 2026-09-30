"""Settings screen."""

import os
import subprocess

from textual.app import ComposeResult
from textual.containers import Vertical, Container
from textual.screen import Screen, ModalScreen
from textual.widgets import Static, Input, Button
from textual.reactive import reactive
from textual import work

from src.tui.widgets import MenuItem

DAEMON_LABEL = "org.iaconelli.rmcd"

TIMEOUT_OPTIONS = [0, 5, 15, 30]
TIMEOUT_LABELS = {0: "Off", 5: "5s", 15: "15s", 30: "30s"}


class ReceiverHostInputScreen(ModalScreen[str]):
    """Modal screen for entering receiver hostname."""

    CSS = """
    ReceiverHostInputScreen {
        align: center middle;
    }

    #input-dialog {
        width: 60;
        height: 9;
        background: $surface;
        border: solid $primary;
        padding: 1;
    }

    #input-dialog Input {
        width: 100%;
        margin: 1 0;
    }

    #input-dialog .buttons {
        width: 100%;
        height: 3;
        align: center middle;
    }

    #input-dialog Button {
        margin: 0 1;
    }
    """

    def __init__(self, current_value: str = ""):
        super().__init__()
        self.current_value = current_value

    def compose(self) -> ComposeResult:
        with Container(id="input-dialog"):
            yield Static("Enter Receiver Hostname:")
            yield Input(value=self.current_value, placeholder="e.g., marantz", id="hostname-input")
            with Container(classes="buttons"):
                yield Button("Save", variant="primary", id="save-btn")
                yield Button("Cancel", id="cancel-btn")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            hostname = self.query_one(Input).value.strip()
            self.dismiss(hostname)
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        hostname = event.value.strip()
        self.dismiss(hostname)


class SettingsScreen(Screen):
    """Settings menu."""

    BINDINGS = [
        ("left", "back", "Back"),
        ("escape", "back", "Back"),
        ("right", "select_item", "Select"),
        ("enter", "select_item", "Select"),
        ("up", "move_up", "Up"),
        ("down", "move_down", "Down"),
        ("k", "move_up", "Up"),
        ("j", "move_down", "Down"),
    ]

    selected_index = reactive(0)

    def __init__(self):
        super().__init__()
        self._menu_items = []
        self._item_widgets = []

    def compose(self) -> ComposeResult:
        yield Static("Settings".center(48), id="list-header")
        yield Vertical(id="settings-list")
        yield Static("", id="list-status")

    def on_mount(self) -> None:
        self._rebuild_menu()

    def _rebuild_menu(self) -> None:
        timeout = self.app.config_manager.config.ui.inactivity_timeout
        timeout_label = TIMEOUT_LABELS.get(timeout, f"{timeout}s")

        _, index_age, index_count = self.app.music_controller.index_status()
        if index_count > 0:
            index_label = f"{index_age} | {index_count:,} tracks"
        else:
            index_label = "not indexed"

        receiver_host = self.app.config_manager.config.daemon.receiver_host or "not set"

        self._menu_items = [
            ("Reindex Library", False, index_label),
            ("Inactivity Timeout", False, timeout_label),
            ("Receiver Hostname", False, receiver_host),
            ("Restart Daemon", False, ""),
        ]

        # Update existing widgets in-place if count matches, otherwise build fresh
        if len(self._item_widgets) == len(self._menu_items):
            for i, (label, has_chevron, indicator) in enumerate(self._menu_items):
                self._item_widgets[i].update_content(label, has_chevron, indicator)
                if i == self.selected_index:
                    self._item_widgets[i].add_class("selected")
                else:
                    self._item_widgets[i].remove_class("selected")
        else:
            container = self.query_one("#settings-list", Vertical)
            container.remove_children()
            widgets = []
            for i, (label, has_chevron, indicator) in enumerate(self._menu_items):
                mi = MenuItem(label, has_chevron, indicator)
                if i == self.selected_index:
                    mi.add_class("selected")
                widgets.append(mi)
            container.mount(*widgets)
            self._item_widgets = widgets

    def watch_selected_index(self, old_index: int, new_index: int) -> None:
        if old_index == new_index:
            return
        try:
            if 0 <= old_index < len(self._item_widgets):
                self._item_widgets[old_index].remove_class("selected")
            if 0 <= new_index < len(self._item_widgets):
                self._item_widgets[new_index].add_class("selected")
        except Exception:
            pass

    def action_move_up(self) -> None:
        if self.selected_index > 0:
            self.selected_index -= 1

    def action_move_down(self) -> None:
        if self.selected_index < len(self._menu_items) - 1:
            self.selected_index += 1

    def action_select_item(self) -> None:
        label = self._menu_items[self.selected_index][0]
        if label == "Reindex Library":
            self._trigger_reindex()
        elif label == "Inactivity Timeout":
            self._cycle_timeout()
        elif label == "Receiver Hostname":
            self._edit_receiver_hostname()
        elif label == "Restart Daemon":
            self._restart_daemon()

    @work(exclusive=True, thread=True)
    def _trigger_reindex(self) -> None:
        self.app.call_from_thread(self.app.notify, "Reindexing library...")
        count = self.app.music_controller.reindex()
        if count >= 0:
            self.app.call_from_thread(self.app.notify, f"Indexed {count:,} tracks")
        else:
            self.app.call_from_thread(
                self.app.notify, "Reindex failed — is daemon running?", severity="error"
            )
        self.app.call_from_thread(self._rebuild_menu)

    def _cycle_timeout(self) -> None:
        config = self.app.config_manager.config
        current = config.ui.inactivity_timeout
        try:
            idx = TIMEOUT_OPTIONS.index(current)
        except ValueError:
            idx = 0
        config.ui.inactivity_timeout = TIMEOUT_OPTIONS[(idx + 1) % len(TIMEOUT_OPTIONS)]
        self.app.config_manager.save()
        self._rebuild_menu()

    def _edit_receiver_hostname(self) -> None:
        current_value = self.app.config_manager.config.daemon.receiver_host or ""

        def handle_result(hostname: str | None) -> None:
            if hostname is not None:
                config = self.app.config_manager.config
                old_hostname = config.daemon.receiver_host
                config.daemon.receiver_host = hostname if hostname else None
                self.app.config_manager.save()
                self._rebuild_menu()

                if hostname != old_hostname:
                    if hostname:
                        self.app.notify(f"Receiver hostname set to: {hostname}")
                    else:
                        self.app.notify("Receiver hostname cleared")
                    # Automatically restart daemon with new settings
                    self._restart_daemon()

        self.app.push_screen(ReceiverHostInputScreen(current_value), handle_result)

    @work(exclusive=True, thread=True)
    def _restart_daemon(self) -> None:
        """Restart the rmcd daemon with current configuration."""
        self.app.call_from_thread(self.app.notify, "Restarting daemon...")

        # Restart the LaunchAgent; its start script re-reads the config.
        try:
            result = subprocess.run(
                ["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/{DAEMON_LABEL}"],
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode == 0:
                self.app.call_from_thread(self.app.notify, "Daemon restarted successfully!")
            else:
                error_msg = result.stderr or result.stdout or "Unknown error"
                self.app.call_from_thread(
                    self.app.notify,
                    f"Daemon restart failed: {error_msg[:100]}",
                    severity="error"
                )
        except subprocess.TimeoutExpired:
            self.app.call_from_thread(
                self.app.notify,
                "Daemon restart timed out",
                severity="error"
            )
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify,
                f"Daemon restart error: {str(e)}",
                severity="error"
            )

    def action_back(self) -> None:
        self.app.pop_screen()
