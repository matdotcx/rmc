"""Reusable list screen base class using a windowed pool of MenuItems."""

from abc import abstractmethod
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static
from textual import events, work

from src.tui.widgets import MenuItem, TitleBar

NOW_PLAYING_MARK = "♪"


def _jump_key(label: str) -> str:
    """Normalise a label for jump matching: lowercase, ignore a leading 'The '."""
    key = label.lower()
    return key[4:] if key.startswith("the ") else key


def sort_key(label: str) -> str:
    """Sort like the iPod: case-insensitive, ignoring a leading 'The '."""
    return _jump_key(label)


class ListScreen(Screen):
    """Abstract base for scrollable menu-item list screens.

    Only enough MenuItem widgets to fill the viewport are mounted; moving
    through the list re-labels them, so lists with thousands of entries open
    instantly.

    Subclasses override:
        screen_title: str
        load_items() -> list
        format_item(item) -> (label, has_chevron, indicator)
        on_item_selected(index, item)
    and, for lists of songs:
        item_music_id(item) -> str, to mark the song that is playing
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
        ("pageup", "page_up", "Page up"),
        ("pagedown", "page_down", "Page down"),
        ("ctrl+b", "page_up", "Page up"),
        ("ctrl+f", "page_down", "Page down"),
        ("home", "first", "First"),
        ("end", "last", "Last"),
        ("g", "first", "First"),
        ("G", "last", "Last"),
        ("slash", "start_jump", "Jump"),
    ]

    screen_title: str = "List"

    def __init__(self):
        super().__init__()
        self._items = []
        self._labels = []
        self._jump_keys = []
        self._music_ids = []
        self._pool = []
        self._top = 0
        self._selected = 0
        self._jump = None  # None when not jumping, else the typed prefix

    def compose(self) -> ComposeResult:
        yield TitleBar(self.screen_title, id="list-header")
        yield Vertical(id="list-container")
        yield Static("Loading...", id="list-status")

    def on_mount(self) -> None:
        self._start_loading()

    @work(thread=True)
    def _start_loading(self) -> None:
        items = self.load_items()
        self.app.call_from_thread(self._populate, items)

    def _populate(self, items: list) -> None:
        self._items = items
        self._labels = [self.format_item(item) for item in items]
        self._jump_keys = [_jump_key(label) for label, _, _ in self._labels]
        self._music_ids = [self.item_music_id(item) for item in items]
        self._top = 0
        self._selected = 0
        self._rebuild_pool()
        self._update_status()

    # -- Windowed rendering --

    def _viewport_height(self) -> int:
        height = self.query_one("#list-container", Vertical).size.height
        return max(1, height or 20)

    def _rebuild_pool(self) -> None:
        """Mount one MenuItem per visible row, then fill them."""
        container = self.query_one("#list-container", Vertical)
        container.remove_children()
        rows = min(self._viewport_height(), len(self._items))
        self._pool = [MenuItem("", False, "") for _ in range(rows)]
        if self._pool:
            container.mount(*self._pool)
        self._clamp_window()
        self._render_window()

    def on_resize(self, event: events.Resize) -> None:
        if self._items:
            self.call_after_refresh(self._rebuild_pool)

    def _clamp_window(self) -> None:
        rows = len(self._pool)
        if self._selected < self._top:
            self._top = self._selected
        elif rows and self._selected >= self._top + rows:
            self._top = self._selected - rows + 1
        self._top = max(0, min(self._top, max(0, len(self._items) - rows)))

    def refresh_labels(self) -> None:
        """Re-format every item in place (e.g. after a setting changes)."""
        self._labels = [self.format_item(item) for item in self._items]
        self._render_window()

    def on_player_status(self) -> None:
        """Called by the app when the polled player status changes."""
        self.query_one(TitleBar).refresh()
        if self._pool and any(self._music_ids):
            self._render_window()

    def _scroll_marks(self) -> list:
        """The iPod scroll bar: a thumb in the last column, sized to the window."""
        rows, total = len(self._pool), len(self._items)
        if total <= rows:
            return [" "] * rows
        thumb = max(1, round(rows * rows / total))
        start = round(self._top * (rows - thumb) / (total - rows))
        return ["█" if start <= row < start + thumb else "│" for row in range(rows)]

    def _render_window(self) -> None:
        now_id = ((getattr(self.app, "player_status", None) or {}).get("track") or {}).get("id")
        marks = self._scroll_marks()
        for slot, widget in enumerate(self._pool):
            index = self._top + slot
            label, has_chevron, indicator = self._labels[index]
            if now_id and self._music_ids[index] == now_id:
                indicator = NOW_PLAYING_MARK
            changed = widget.label != label
            widget.update_content(label, has_chevron, indicator)
            widget.set_scroll_mark(marks[slot])
            if index == self._selected:
                if changed:
                    # Restart the marquee for the new label.
                    widget.remove_class("selected")
                widget.add_class("selected")
            else:
                widget.remove_class("selected")

    def _select(self, index: int) -> None:
        if not self._items:
            return
        self._selected = max(0, min(index, len(self._items) - 1))
        self._clamp_window()
        self._render_window()
        self._update_status()

    def _update_status(self) -> None:
        status = self.query_one("#list-status", Static)
        if not self._items:
            status.update("  No items")
        elif self._jump is not None:
            status.update(f"  Jump: {self._jump}_")
        else:
            status.update("")

    # -- Navigation --

    def action_move_up(self) -> None:
        self._select(self._selected - 1)

    def action_move_down(self) -> None:
        self._select(self._selected + 1)

    def action_page_up(self) -> None:
        self._select(self._selected - max(1, len(self._pool) - 1))

    def action_page_down(self) -> None:
        self._select(self._selected + max(1, len(self._pool) - 1))

    def action_first(self) -> None:
        self._select(0)

    def action_last(self) -> None:
        self._select(len(self._items) - 1)

    def action_select_item(self) -> None:
        if self._items:
            self.on_item_selected(self._selected, self._items[self._selected])

    def action_back(self) -> None:
        self.app.pop_screen()

    # -- Jump to prefix --

    def action_start_jump(self) -> None:
        if self._items:
            self._jump = ""
            self._update_status()

    def _end_jump(self) -> None:
        self._jump = None
        self._update_status()

    def on_key(self, event: events.Key) -> None:
        """While jumping, printable keys extend the prefix instead of acting as bindings."""
        if self._jump is None:
            return
        event.prevent_default()
        event.stop()
        if event.key in ("escape", "enter"):
            self._end_jump()
            return
        if event.key == "backspace":
            self._jump = self._jump[:-1]
        elif event.character and event.character.isprintable():
            self._jump += event.character.lower()
        else:
            return
        self._jump_to_prefix()
        self._update_status()

    def _jump_to_prefix(self) -> None:
        prefix = self._jump or ""
        for index, key in enumerate(self._jump_keys):
            if key.startswith(prefix):
                self._select(index)
                return

    def item_music_id(self, item) -> str | None:
        """MusicKit ID of the song an item plays, if the item is a song."""
        return None

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


class SongListScreen(ListScreen):
    """A list of songs, shown by title only like the iPod.

    Choosing a song plays it with the whole list queued around it, and then
    shows Now Playing.
    """

    def format_item(self, item) -> tuple:
        return (item.get("name", "Unknown"), False, "")

    def item_music_id(self, item) -> str | None:
        return item.get("music_id")

    def on_item_selected(self, index: int, item) -> None:
        self.app.music_controller.play_tracks(self._items, index)
        from src.tui.screens.now_playing import NowPlayingScreen
        self.app.push_screen(NowPlayingScreen())
