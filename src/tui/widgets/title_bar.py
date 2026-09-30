"""TitleBar widget - the classic iPod title bar."""

from textual.widgets import Static

from src.tui.widgets.menu_item import SCREEN_WIDTH

STATE_GLYPHS = {"playing": "▶", "paused": "❚❚"}
REPEAT_GLYPHS = {"all": "↻", "one": "↻1"}


class TitleBar(Static):
    """Screen title centred, play state on the left, shuffle/repeat on the right.

    Reads the player status the app polls (``app.player_status``); the app
    refreshes every TitleBar when that status changes.
    """

    DEFAULT_CSS = """
    TitleBar {
        width: 100%;
        height: 2;
        text-style: bold;
        border-bottom: solid ansi_bright_black;
    }
    """

    def __init__(self, title: str, width: int = SCREEN_WIDTH, id: str | None = None):
        super().__init__(id=id)
        self.title = title
        self.display_width = width

    def set_title(self, title: str) -> None:
        self.title = title
        self.refresh()

    def render(self) -> str:
        status = getattr(self.app, "player_status", None) or {}
        left = STATE_GLYPHS.get(status.get("state", ""), "")
        modes = []
        if status.get("shuffle"):
            modes.append("⇄")
        if status.get("repeat") in REPEAT_GLYPHS:
            modes.append(REPEAT_GLYPHS[status["repeat"]])
        right = " ".join(modes)

        # Keep the title centred on the screen whatever the side glyphs are.
        side = 4
        room = self.display_width - 2 * side
        title = self.title if len(self.title) <= room else self.title[: room - 2] + ".."
        return f" {left:<{side - 1}}{title:^{room}}{right:>{side - 1}} "
