"""Settings screen."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static
from textual.reactive import reactive
from textual import work

from src.tui.widgets import MenuItem

TIMEOUT_OPTIONS = [0, 5, 15, 30]
TIMEOUT_LABELS = {0: "Off", 5: "5s", 15: "15s", 30: "30s"}


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

        self._menu_items = [
            ("Reindex Library", False, index_label),
            ("Inactivity Timeout", False, timeout_label),
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

    def action_back(self) -> None:
        self.app.pop_screen()
