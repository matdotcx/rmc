"""MenuItem widget - single-line menu item with scrolling text and right-justified chevron."""

from textual.widgets import Static
from textual.reactive import reactive


class MenuItem(Static):
    """A single menu item - one line, chevron right-justified, scrolling text."""

    DEFAULT_CSS = """
    MenuItem {
        width: 100%;
        height: 1;
    }

    MenuItem.selected {
        text-style: bold reverse;
    }
    """

    # For scrolling long text
    scroll_offset = reactive(0)

    def __init__(
        self,
        label: str,
        has_chevron: bool = True,
        indicator: str = "",
        width: int = 48,
        id: str | None = None,
    ):
        """Initialize menu item.

        Args:
            label: The menu item text
            has_chevron: Whether to show > chevron on the right
            indicator: Optional indicator (e.g., "*" for now playing)
            width: Total display width for the item
            id: Optional widget ID
        """
        super().__init__(id=id)
        self.label = label
        self.has_chevron = has_chevron
        self.indicator = indicator
        self.display_width = width
        self._scroll_timer = None

    def update_content(self, label: str, has_chevron: bool, indicator: str) -> None:
        """Update the menu item content in-place."""
        self.label = label
        self.has_chevron = has_chevron
        self.indicator = indicator
        self.refresh()

    def on_mount(self) -> None:
        """Start scroll timer if text is too long."""
        self._check_scroll_needed()

    def _check_scroll_needed(self) -> bool:
        """Check if text needs scrolling."""
        ind = f" {self.indicator}" if self.indicator else ""
        full_text = f"{self.label}{ind}"
        # Available space: width - left_pad(2) - gap(2) - chevron(1) - right_pad(2)
        available = self.display_width - 7
        return len(full_text) > available

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
        ind = f" {self.indicator}" if self.indicator else ""
        full_text = f"{self.label}{ind}"
        available = self.display_width - 7
        max_offset = len(full_text) - available + 3  # +3 for wrap padding
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
        ind = f" {self.indicator}" if self.indicator else ""
        full_text = f"{self.label}{ind}"

        # Layout: [2 pad] [text...] [2 space gap] [chevron] [2 pad]
        left_pad = 2
        right_pad = 2
        gap = 2
        available = self.display_width - left_pad - gap - 1 - right_pad

        if len(full_text) <= available:
            # Fits - just use the text
            text_part = full_text
        else:
            # Too long - scroll if selected, else truncate
            if "selected" in self.classes:
                # Scrolling: offset the text
                offset = max(0, self.scroll_offset - 5)  # Pause at start
                scrolled = full_text[offset:] if offset < len(full_text) else full_text
                text_part = scrolled[:available]
            else:
                # Truncate with ellipsis
                text_part = full_text[: available - 2] + ".."

        # Build line with symmetric padding
        padding_needed = available - len(text_part)
        return f"{' ' * left_pad}{text_part}{' ' * (padding_needed + gap)}{chevron}{' ' * right_pad}"
