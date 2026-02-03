"""Settings screen for configuring RMC preferences."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static
from textual.reactive import reactive

from src.tui.widgets import MenuItem


class SettingsScreen(Screen):
    """Settings screen with configurable options."""

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
        """Initialize settings screen."""
        super().__init__()
        self.menu_items = [
            ("Inactivity Timeout", True, ""),
        ]

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static("Settings".center(48), id="settings-header")
        with Vertical(id="settings-list"):
            for i, (label, has_chevron, indicator) in enumerate(self.menu_items):
                item = MenuItem(label, has_chevron, indicator, id=f"settings-item-{i}")
                if i == 0:
                    item.add_class("selected")
                yield item
        yield Static("", id="settings-status")

    def on_mount(self) -> None:
        """Set up screen on mount."""
        self._update_status()

    def _update_status(self) -> None:
        """Update the current setting value display."""
        timeout = self.app.config_manager.config.ui.inactivity_timeout
        if timeout == 0:
            timeout_str = "disabled"
        else:
            timeout_str = f"{timeout}s"
        status = self.query_one("#settings-status", Static)
        status.update(f"  Current timeout: {timeout_str}")

    def watch_selected_index(self, old_index: int, new_index: int) -> None:
        """Update selection styling when index changes."""
        if old_index != new_index:
            try:
                self.query_one(f"#settings-item-{old_index}", MenuItem).remove_class("selected")
                self.query_one(f"#settings-item-{new_index}", MenuItem).add_class("selected")
            except Exception:
                pass

    def action_move_up(self) -> None:
        """Move selection up."""
        if self.selected_index > 0:
            self.selected_index -= 1

    def action_move_down(self) -> None:
        """Move selection down."""
        if self.selected_index < len(self.menu_items) - 1:
            self.selected_index += 1

    def action_select_item(self) -> None:
        """Handle item selection."""
        selected_label = self.menu_items[self.selected_index][0]

        if selected_label == "Inactivity Timeout":
            self.app.push_screen(TimeoutSettingScreen())

    def action_back(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()


class TimeoutSettingScreen(Screen):
    """Screen for selecting inactivity timeout value."""

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
        """Initialize timeout setting screen."""
        super().__init__()
        self.timeout_options = [
            (5, "5 seconds"),
            (15, "15 seconds"),
            (30, "30 seconds"),
            (0, "Disabled"),
        ]

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static("Inactivity Timeout".center(48), id="timeout-header")
        with Vertical(id="timeout-list"):
            current_timeout = self.app.config_manager.config.ui.inactivity_timeout
            for i, (value, label) in enumerate(self.timeout_options):
                indicator = "*" if value == current_timeout else ""
                item = MenuItem(label, has_chevron=False, indicator=indicator, id=f"timeout-item-{i}")
                if i == 0:
                    item.add_class("selected")
                yield item

    def on_mount(self) -> None:
        """Set initial selection to current value."""
        current_timeout = self.app.config_manager.config.ui.inactivity_timeout
        for i, (value, _) in enumerate(self.timeout_options):
            if value == current_timeout:
                self.selected_index = i
                break

    def watch_selected_index(self, old_index: int, new_index: int) -> None:
        """Update selection styling when index changes."""
        if old_index != new_index:
            try:
                self.query_one(f"#timeout-item-{old_index}", MenuItem).remove_class("selected")
                self.query_one(f"#timeout-item-{new_index}", MenuItem).add_class("selected")
            except Exception:
                pass

    def action_move_up(self) -> None:
        """Move selection up."""
        if self.selected_index > 0:
            self.selected_index -= 1

    def action_move_down(self) -> None:
        """Move selection down."""
        if self.selected_index < len(self.timeout_options) - 1:
            self.selected_index += 1

    def action_select_item(self) -> None:
        """Save the selected timeout value."""
        value, label = self.timeout_options[self.selected_index]
        self.app.config_manager.config.ui.inactivity_timeout = value
        self.app.config_manager.save()
        self.app.notify(f"Timeout set to {label}")
        self.app.pop_screen()

    def action_back(self) -> None:
        """Go back to settings."""
        self.app.pop_screen()
