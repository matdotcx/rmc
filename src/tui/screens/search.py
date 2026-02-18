"""Search screen with Input widget and scrollable results."""

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Static, Input
from textual.reactive import reactive
from textual import work

from src.tui.widgets import MenuItem


class SearchScreen(Screen):
    """Library search with real-time results."""

    BINDINGS = [
        ("left", "back", "Back"),
        ("escape", "back", "Back"),
        ("right", "select_item", "Select"),
        ("enter", "select_or_submit", "Select"),
        ("up", "move_up", "Up"),
        ("down", "move_down", "Down"),
    ]

    selected_index = reactive(-1)  # -1 = input focused

    def __init__(self):
        super().__init__()
        self._items = []
        self._result_widgets = []

    def compose(self) -> ComposeResult:
        yield Static("Search".center(48), id="list-header")
        yield Input(placeholder="Type to search...", id="search-input")
        yield VerticalScroll(id="list-container", can_focus=False)
        yield Static("", id="list-status")

    def on_mount(self) -> None:
        self.query_one("#search-input", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.strip()
        if query:
            self._do_search(query)
        else:
            self._clear_results()

    def _clear_results(self) -> None:
        self._items = []
        self._result_widgets = []
        self.selected_index = -1
        container = self.query_one("#list-container", VerticalScroll)
        container.remove_children()
        self.query_one("#list-status", Static).update("")

    @work(thread=True, exclusive=True)
    def _do_search(self, query: str) -> None:
        results = self.app.music_controller.search_library(query) or []
        self.app.call_from_thread(self._populate, results)

    def _populate(self, items: list) -> None:
        self._items = items
        self._result_widgets = []
        container = self.query_one("#list-container", VerticalScroll)
        container.remove_children()

        if not items:
            self.query_one("#list-status", Static).update("No results")
            return

        widgets = []
        for i, item in enumerate(items):
            name = item.get("name", "Unknown")
            artist = item.get("artist", "")
            label = f"{name} - {artist}" if artist else name
            mi = MenuItem(label, False, "")
            widgets.append(mi)

        container.mount(*widgets)
        self._result_widgets = widgets
        self.selected_index = -1
        self.query_one("#list-status", Static).update(f"{len(items)} results")

    def on_key(self, event) -> None:
        inp = self.query_one("#search-input", Input)
        if inp.has_focus:
            if event.key == "down":
                if self._items:
                    self.selected_index = 0
                    event.prevent_default()
                    event.stop()
            # Let j/k type normally when input is focused
            return

        if event.key in ("j", "k"):
            if event.key == "j":
                self.action_move_down()
            else:
                self.action_move_up()
            event.prevent_default()
            event.stop()

    def watch_selected_index(self, old_index: int, new_index: int) -> None:
        if old_index == new_index:
            return
        inp = self.query_one("#search-input", Input)
        if old_index >= 0 and old_index < len(self._result_widgets):
            try:
                self._result_widgets[old_index].remove_class("selected")
            except Exception:
                pass
        if new_index >= 0 and new_index < len(self._result_widgets):
            try:
                selected = self._result_widgets[new_index]
                selected.add_class("selected")
                self._ensure_visible(new_index)
                inp.blur()
            except Exception:
                pass
        elif new_index == -1:
            inp.focus()

    def _ensure_visible(self, index: int) -> None:
        """Scroll the container only if the item is outside the visible area."""
        container = self.query_one("#list-container", VerticalScroll)
        scroll_y = container.scroll_offset.y
        viewport_height = container.size.height
        if index < scroll_y:
            container.scroll_to(0, index, animate=False)
        elif index >= scroll_y + viewport_height:
            container.scroll_to(0, index - viewport_height + 1, animate=False)

    def action_move_up(self) -> None:
        if self.selected_index > 0:
            self.selected_index -= 1
        elif self.selected_index == 0:
            self.selected_index = -1

    def action_move_down(self) -> None:
        if self.selected_index < len(self._items) - 1:
            self.selected_index += 1

    def action_select_or_submit(self) -> None:
        inp = self.query_one("#search-input", Input)
        if inp.has_focus:
            if self._items:
                self.selected_index = 0
            return
        self.action_select_item()

    def action_select_item(self) -> None:
        if self._items and 0 <= self.selected_index < len(self._items):
            item = self._items[self.selected_index]
            self.app.music_controller.play_track(
                item.get("name", ""), item.get("artist", "")
            )
            from src.tui.screens.now_playing import NowPlayingScreen
            self.app.push_screen(NowPlayingScreen())

    def action_back(self) -> None:
        self.app.pop_screen()
