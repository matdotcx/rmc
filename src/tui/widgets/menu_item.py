"""MenuItem widget - one iPod list row: label, right-aligned value, chevron, scroll bar."""

from textual.widgets import Static
from textual.reactive import reactive

SCREEN_WIDTH = 48


class MenuItem(Static):
    """A single menu row, laid out like a classic iPod list:

        [pad] label ...marquee...  [value] [>] [scroll bar]

    The value is right-aligned (a setting's current value, or the
    now-playing marker on a song row). The last column draws the list's
    scroll bar, which the owning list sets via ``scroll_mark``.
    """

    DEFAULT_CSS = """
    MenuItem {
        width: 100%;
        height: 1;
    }

    MenuItem.selected {
        background: ansi_blue;
        color: ansi_bright_white;
        text-style: bold;
    }
    """

    # For scrolling long text
    scroll_offset = reactive(0)

    def __init__(
        self,
        label: str,
        has_chevron: bool = True,
        indicator: str = "",
        width: int = SCREEN_WIDTH,
        id: str | None = None,
    ):
        """Initialize menu item.

        Args:
            label: The menu item text
            has_chevron: Whether to show > chevron on the right
            indicator: Right-aligned value (e.g. "Off", or "♪" for now playing)
            width: Total display width for the item
            id: Optional widget ID
        """
        super().__init__(id=id)
        self.label = label
        self.has_chevron = has_chevron
        self.indicator = indicator
        self.scroll_mark = " "
        self.display_width = width
        self._scroll_timer = None

    def update_content(self, label: str, has_chevron: bool, indicator: str) -> None:
        """Update the menu item content in-place."""
        self.label = label
        self.has_chevron = has_chevron
        self.indicator = indicator
        self.refresh()

    def set_scroll_mark(self, mark: str) -> None:
        if mark != self.scroll_mark:
            self.scroll_mark = mark
            self.refresh()

    def _available(self) -> int:
        """Columns left for the label."""
        # [2 pad] label [2 gap] value [1 space] chevron [1 space] scroll bar
        value = len(self.indicator) + 1 if self.indicator else 0
        return self.display_width - 2 - 2 - value - 1 - 1 - 1

    def on_mount(self) -> None:
        """Start scroll timer if text is too long."""
        self._check_scroll_needed()

    def _check_scroll_needed(self) -> bool:
        """Check if text needs scrolling."""
        return len(self.label) > self._available()

    def watch_scroll_offset(self, value: int) -> None:
        """Re-render when scroll offset changes."""
        self.refresh()

    def _start_scrolling(self) -> None:
        """Start the scroll animation."""
        if self._scroll_timer is None and self._check_scroll_needed():
            self._scroll_timer = self.set_interval(0.3, self._scroll_tick)

    def _stop_scrolling(self) -> None:
        """Stop the scroll animation."""
        if self._scroll_timer:
            self._scroll_timer.stop()
            self._scroll_timer = None
        self.scroll_offset = 0

    def _scroll_tick(self) -> None:
        """Advance scroll position."""
        max_offset = len(self.label) - self._available() + 3  # +3 for wrap padding
        self.scroll_offset = (self.scroll_offset + 1) % (max_offset + 10)  # Pause at start

    def on_focus(self) -> None:
        """Start scrolling when focused."""
        self._start_scrolling()

    def on_blur(self) -> None:
        """Stop scrolling when unfocused."""
        self._stop_scrolling()

    def add_class(self, name: str) -> None:
        """Handle class addition - start scrolling when selected."""
        super().add_class(name)
        if name == "selected":
            self._start_scrolling()

    def remove_class(self, name: str) -> None:
        """Handle class removal - stop scrolling when deselected."""
        super().remove_class(name)
        if name == "selected":
            self._stop_scrolling()

    def render(self) -> str:
        """Render the menu item with proper alignment."""
        chevron = ">" if self.has_chevron else " "
        value = f"{self.indicator} " if self.indicator else ""
        available = self._available()

        if len(self.label) <= available:
            text_part = self.label
        elif "selected" in self.classes:
            # Marquee: offset the text
            offset = max(0, self.scroll_offset - 5)  # Pause at start
            scrolled = self.label[offset:] if offset < len(self.label) else self.label
            text_part = scrolled[:available]
        else:
            # Truncate with ellipsis
            text_part = self.label[: available - 2] + ".."

        padding = available - len(text_part) + 2
        return f"  {text_part}{' ' * padding}{value}{chevron} {self.scroll_mark}"
