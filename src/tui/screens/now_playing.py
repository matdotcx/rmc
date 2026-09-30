"""Now Playing screen, laid out like the classic iPod's."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static

from src.tui.widgets import TitleBar, SCREEN_WIDTH

# How long the volume bar replaces the progress bar after a volume change.
VOLUME_BAR_SECONDS = 2.0
BAR_FILLED = "━"
BAR_EMPTY = "─"


def _bar(fraction: float, width: int) -> str:
    filled = round(max(0.0, min(1.0, fraction)) * width)
    return BAR_FILLED * filled + BAR_EMPTY * (width - filled)


def _clock(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def _fit(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 2] + ".."


class NowPlayingScreen(Screen):
    """Screen displaying the current song, its place in the queue and progress."""

    BINDINGS = [
        ("left", "back", "Back"),
        ("escape", "back", "Back"),
        ("space", "playpause", "Play/Pause"),
        ("n", "next_track", "Next"),
        ("p", "previous_track", "Previous"),
        ("s", "toggle_shuffle", "Shuffle"),
        ("r", "cycle_repeat", "Repeat"),
        ("+", "volume_up", "Volume Up"),
        ("=", "volume_up", "Volume Up"),
        ("-", "volume_down", "Volume Down"),
    ]

    def __init__(self):
        super().__init__()
        self._volume_timer = None

    def compose(self) -> ComposeResult:
        yield TitleBar("Now Playing")
        yield Static(id="now-playing-display")

    def on_mount(self) -> None:
        # Show the current song straight away rather than on the next poll.
        status = self.app.music_controller.get_status()
        if status:
            self.app.player_status = status
        self.on_player_status()

    def on_player_status(self) -> None:
        self.query_one(TitleBar).refresh()
        self.query_one("#now-playing-display", Static).update(self._format_display())

    def _format_display(self) -> str:
        status = self.app.player_status or {}
        track = status.get("track")
        width = SCREEN_WIDTH - 4
        lines = [""]

        if not track:
            lines += ["", "Not Playing".center(SCREEN_WIDTH)]
            return "\n".join(lines)

        index, count = status.get("queue_index"), status.get("queue_count")
        lines.append(f"  {index} of {count}" if index and count else "")
        lines.append("")
        lines.append(f"  {_fit(track.get('name', ''), width)}")
        lines.append(f"  {_fit(track.get('artist', ''), width)}")
        lines.append(f"  {_fit(track.get('album', ''), width)}")
        lines += ["", ""]

        if self._volume_timer is not None:
            volume = status.get("volume", 0)
            label = "Volume"
            bar_width = SCREEN_WIDTH - 4 - len(label) - 1 - 4
            lines.append(f"  {label} {_bar(volume / 100, bar_width)} {volume:>3}")
        else:
            position = track.get("position", 0.0)
            duration = track.get("duration", 0.0)
            elapsed = _clock(position)
            remaining = "-" + _clock(duration - position)
            bar_width = SCREEN_WIDTH - 4 - len(elapsed) - len(remaining) - 2
            fraction = position / duration if duration else 0.0
            lines.append(f"  {elapsed} {_bar(fraction, bar_width)} {remaining}")

        return "\n".join(lines)

    def _show_volume(self) -> None:
        """Swap the progress bar for the volume bar for a moment, like the iPod."""
        if self._volume_timer is not None:
            self._volume_timer.stop()
        self._volume_timer = self.set_timer(VOLUME_BAR_SECONDS, self._hide_volume)
        status = self.app.music_controller.get_status()
        if status:
            self.app.player_status = status
        self.on_player_status()

    def _hide_volume(self) -> None:
        self._volume_timer = None
        self.on_player_status()

    def action_playpause(self) -> None:
        self.app.music_controller.playpause()

    def action_next_track(self) -> None:
        self.app.music_controller.next_track()

    def action_previous_track(self) -> None:
        self.app.music_controller.previous_track()

    def action_toggle_shuffle(self) -> None:
        self.app.music_controller.toggle_shuffle()

    def action_cycle_repeat(self) -> None:
        self.app.music_controller.cycle_repeat()

    def action_volume_up(self) -> None:
        self.app.music_controller.volume_up()
        self._show_volume()

    def action_volume_down(self) -> None:
        self.app.music_controller.volume_down()
        self._show_volume()

    def action_back(self) -> None:
        self.app.pop_screen()
