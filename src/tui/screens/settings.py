"""Settings screen."""

import os
import subprocess

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Static, Input, Button
from textual import work

from src.tui.screens.list_screen import ListScreen

DAEMON_LABEL = "org.iaconelli.rmcd"

TIMEOUT_OPTIONS = [0, 5, 15, 30]
TIMEOUT_LABELS = {0: "Off", 5: "5 Seconds", 15: "15 Seconds", 30: "30 Seconds"}


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


class SettingsScreen(ListScreen):
    """iPod-style Settings: each row shows its current value on the right."""

    screen_title = "Settings"

    def load_items(self) -> list:
        return ["About", "Shuffle", "Repeat", "Now Playing Timeout",
                "Receiver", "Reindex Library", "Restart Daemon"]

    def format_item(self, item) -> tuple:
        status = getattr(self.app, "player_status", None) or {}
        config = self.app.config_manager.config
        if item == "About":
            return (item, True, "")
        if item == "Shuffle":
            return (item, False, "Songs" if status.get("shuffle") else "Off")
        if item == "Repeat":
            return (item, False, status.get("repeat", "off").title())
        if item == "Now Playing Timeout":
            timeout = config.ui.inactivity_timeout
            return (item, False, TIMEOUT_LABELS.get(timeout, f"{timeout}s"))
        if item == "Receiver":
            return (item, False, config.daemon.receiver_host or "None")
        if item == "Reindex Library":
            exists, age, _count = self.app.music_controller.index_status()
            return (item, False, age if exists else "Never")
        return (item, False, "")

    def on_player_status(self) -> None:
        super().on_player_status()
        if self._items:
            self.refresh_labels()

    def on_screen_resume(self) -> None:
        if self._items:
            self.refresh_labels()

    def on_item_selected(self, index: int, item) -> None:
        if item == "About":
            self.app.push_screen(AboutScreen())
        elif item == "Shuffle":
            self.app.music_controller.toggle_shuffle()
            self._refresh_status()
        elif item == "Repeat":
            self.app.music_controller.cycle_repeat()
            self._refresh_status()
        elif item == "Now Playing Timeout":
            self._cycle_timeout()
        elif item == "Receiver":
            self._edit_receiver_hostname()
        elif item == "Reindex Library":
            self._trigger_reindex()
        elif item == "Restart Daemon":
            self._restart_daemon()

    def _refresh_status(self) -> None:
        status = self.app.music_controller.get_status()
        if status:
            self.app.apply_player_status(status)

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
        self.app.call_from_thread(self.refresh_labels)

    def _cycle_timeout(self) -> None:
        config = self.app.config_manager.config
        current = config.ui.inactivity_timeout
        try:
            idx = TIMEOUT_OPTIONS.index(current)
        except ValueError:
            idx = 0
        config.ui.inactivity_timeout = TIMEOUT_OPTIONS[(idx + 1) % len(TIMEOUT_OPTIONS)]
        self.app.config_manager.save()
        self.refresh_labels()

    def _edit_receiver_hostname(self) -> None:
        current_value = self.app.config_manager.config.daemon.receiver_host or ""

        def handle_result(hostname: str | None) -> None:
            if hostname is not None:
                config = self.app.config_manager.config
                old_hostname = config.daemon.receiver_host
                config.daemon.receiver_host = hostname if hostname else None
                self.app.config_manager.save()
                self.refresh_labels()

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



class AboutScreen(ListScreen):
    """Library totals, like the iPod's About screen."""

    screen_title = "About"

    def load_items(self) -> list:
        controller = self.app.music_controller
        _exists, age, _count = controller.index_status()
        return [
            ("Songs", f"{len(controller.get_all_songs()):,}"),
            ("Artists", f"{len(controller.get_all_artists()):,}"),
            ("Albums", f"{len(controller.get_all_albums()):,}"),
            ("Playlists", f"{len(controller.get_playlists()):,}"),
            ("Updated", age),
        ]

    def format_item(self, item) -> tuple:
        label, value = item
        return (label, False, value)

    def on_item_selected(self, index: int, item) -> None:
        pass
