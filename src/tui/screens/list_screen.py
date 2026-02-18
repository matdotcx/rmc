"""Reusable list screen base class using MenuItem + VerticalScroll."""

from abc import abstractmethod
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Static
from textual.reactive import reactive
from textual import work

from src.tui.widgets import MenuItem


class ListScreen(Screen):
    """Abstract base for scrollable menu-item list screens.

    Subclasses override:
        screen_title: str
        load_items() -> list
        format_item(item) -> (label, has_chevron, indicator)
        on_item_selected(index, item)
    """

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

    screen_title: str = "List"
    selected_index = reactive(0)

    def __init__(self):
        super().__init__()
        self._items = []
        self._item_widgets = []

    def compose(self) -> ComposeResult:
        yield Static(self.screen_title.center(48), id="list-header")
        yield VerticalScroll(id="list-container", can_focus=False)
        yield Static("Loading...", id="list-status")

    def on_mount(self) -> None:
        self._start_loading()

    @work(thread=True)
    def _start_loading(self) -> None:
        items = self.load_items()
        self.app.call_from_thread(self._populate, items)

    def _populate(self, items: list) -> None:
        self._items = items
        self._item_widgets = []
        container = self.query_one("#list-container", VerticalScroll)
        container.remove_children()

        if not items:
            self.query_one("#list-status", Static).update("No items found")
            return

        widgets = []
        for i, item in enumerate(items):
            label, has_chevron, indicator = self.format_item(item)
            mi = MenuItem(label, has_chevron, indicator)
            if i == 0:
                mi.add_class("selected")
            widgets.append(mi)

        container.mount(*widgets)
        self._item_widgets = widgets
        self.selected_index = 0
        self.query_one("#list-status", Static).update(f"{len(items)} items")

    def watch_selected_index(self, old_index: int, new_index: int) -> None:
        if old_index == new_index:
            return
        try:
            if 0 <= old_index < len(self._item_widgets):
                self._item_widgets[old_index].remove_class("selected")
            if 0 <= new_index < len(self._item_widgets):
                selected = self._item_widgets[new_index]
                selected.add_class("selected")
                self._ensure_visible(selected)
        except Exception:
            pass

    def _ensure_visible(self, widget: MenuItem) -> None:
        """Scroll the container only if the widget is outside the visible area."""
        container = self.query_one("#list-container", VerticalScroll)
        scroll_y = container.scroll_offset.y
        viewport_height = container.size.height
        # Each MenuItem is 1 row tall; its position is its index in children
        try:
            widget_y = self._item_widgets.index(widget)
        except ValueError:
            return
        if widget_y < scroll_y:
            container.scroll_to(0, widget_y, animate=False)
        elif widget_y >= scroll_y + viewport_height:
            container.scroll_to(0, widget_y - viewport_height + 1, animate=False)

    def action_move_up(self) -> None:
        if self.selected_index > 0:
            self.selected_index -= 1

    def action_move_down(self) -> None:
        if self._items and self.selected_index < len(self._items) - 1:
            self.selected_index += 1

    def action_select_item(self) -> None:
        if self._items:
            self.on_item_selected(self.selected_index, self._items[self.selected_index])

    def action_back(self) -> None:
        self.app.pop_screen()

    @abstractmethod
    def load_items(self) -> list:
        """Load items in background thread. Return list of items."""
        ...

    @abstractmethod
    def format_item(self, item) -> tuple:
        """Return (label, has_chevron, indicator) for an item."""
        ...

    @abstractmethod
    def on_item_selected(self, index: int, item) -> None:
        """Handle item selection."""
        ...
