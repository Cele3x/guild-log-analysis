"""
Cooldown assignment compliance — landscape PDF table.

One landscape page; one row per fight, one column per assignment. Cells are
green when the assigned cast landed within the on-time margin, red when it
didn't. Styled to match :mod:`guild_log_analysis.plotting.player_deaths`.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle

from ..analysis.cd_assignments import ComplianceReport
from ..config.constants import ClassColors
from .styles import PlotColors, PlotStyleManager

logger = logging.getLogger(__name__)


# Landscape A4-ish, but we size the figure to content.
PAGE_WIDTH = 16.5
PAGE_MARGIN_X = 0.45

TOP_ACCENT_HEIGHT = 0.06
HEADER_HEIGHT = 0.85
HEADER_RULE_PAD = 0.22
COLUMN_HEADER_HEIGHT = 0.95
ROW_HEIGHT = 0.62
PAGE_BOTTOM_PAD = 0.40

# Column geometry.
PULL_COL_WIDTH = 1.55
MIN_DATA_COL_WIDTH = 1.35

# Cell colors.
OK_FILL = "#1F4D2E"          # deep green
OK_TEXT = "#A8E6B0"
OFF_FILL = "#5A1F1F"         # deep red
OFF_TEXT = "#FFB4A2"
NEUTRAL_FILL = "#23272E"     # phase not reached / absent
DIM_TEXT = "#8E96A1"
SOFT_TEXT = "#B6BCC4"
RULE_COLOR = "#2D343F"
ACCENT_COLOR = "#5DADE2"

# Char-width approximations (axis units == inches at fontsize 10).
CHAR_W_8 = 0.062
CHAR_W_9 = 0.072
CHAR_W_10 = 0.082


def _format_mmss(seconds: int) -> str:
    seconds = max(0, int(round(seconds)))
    return f"{seconds // 60}:{seconds % 60:02d}"


def _fight_date(fight_start_ms: int, report_start_ms: int = 0) -> str:
    if not fight_start_ms:
        return ""
    try:
        return datetime.fromtimestamp(
            (report_start_ms + fight_start_ms) / 1000.0
        ).strftime("%H:%M")
    except (ValueError, OSError):
        return ""


class CDAssignmentsPlot:
    """Render a :class:`ComplianceReport` as a landscape PDF table."""

    def __init__(self, compliance: ComplianceReport, title: str, date: str) -> None:
        """
        :param compliance: Output of :func:`check_assignments`.
        :param title: Plot title (used in the page header and PDF metadata).
        :param date: Date string for the page header (e.g. ``"30.04.2026"``).
        """
        self.compliance = compliance
        self.title = title
        self.date = date

    # ------------------------------------------------------------------ layout

    def _column_width(self, n_cols: int, content_width: float) -> float:
        """Distribute remaining width across the data columns."""
        if n_cols <= 0:
            return MIN_DATA_COL_WIDTH
        return max(MIN_DATA_COL_WIDTH, (content_width - PULL_COL_WIDTH) / n_cols)

    def _figure_size(self) -> tuple[float, float, float]:
        """Return ``(figure_width, figure_height, data_col_width)`` for this report."""
        comp = self.compliance
        n_cols = len(comp.assignments)
        n_rows = len(comp.fights)

        # Dynamic width: enough for all columns at MIN_DATA_COL_WIDTH plus margins.
        min_content_width = PULL_COL_WIDTH + MIN_DATA_COL_WIDTH * max(n_cols, 1)
        content_width = max(PAGE_WIDTH - 2 * PAGE_MARGIN_X, min_content_width)
        fig_width = content_width + 2 * PAGE_MARGIN_X
        col_width = self._column_width(n_cols, content_width)

        body_height = max(n_rows, 1) * ROW_HEIGHT
        page_height = (
            TOP_ACCENT_HEIGHT
            + HEADER_HEIGHT
            + HEADER_RULE_PAD
            + COLUMN_HEADER_HEIGHT
            + body_height
            + PAGE_BOTTOM_PAD
        )
        return fig_width, page_height, col_width

    # ------------------------------------------------------------------ build

    def create_figure(self) -> plt.Figure:
        """Build the figure for the compliance table."""
        PlotStyleManager.setup_plot_style()

        fig_width, page_height, col_width = self._figure_size()
        fig = plt.figure(figsize=(fig_width, page_height))
        fig.patch.set_facecolor(PlotColors.BACKGROUND)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, fig_width)
        ax.set_ylim(0, page_height)
        ax.invert_yaxis()
        ax.set_facecolor(PlotColors.BACKGROUND)
        ax.axis("off")

        # Top accent + header
        ax.add_patch(Rectangle(
            (0, 0), fig_width, TOP_ACCENT_HEIGHT,
            facecolor=ACCENT_COLOR, edgecolor="none", zorder=2,
        ))
        self._draw_page_header(ax, fig_width)

        # Hairline rule
        rule_y = TOP_ACCENT_HEIGHT + HEADER_HEIGHT + HEADER_RULE_PAD * 0.55
        ax.plot(
            [PAGE_MARGIN_X, fig_width - PAGE_MARGIN_X],
            [rule_y, rule_y],
            color=RULE_COLOR, linewidth=0.8, zorder=2,
        )

        body_top = TOP_ACCENT_HEIGHT + HEADER_HEIGHT + HEADER_RULE_PAD
        self._draw_column_headers(ax, body_top, fig_width, col_width)

        rows_top = body_top + COLUMN_HEADER_HEIGHT
        self._draw_rows(ax, rows_top, fig_width, col_width)

        return fig

    # ------------------------------------------------------------------ pieces

    def _draw_page_header(self, ax: plt.Axes, fig_width: float) -> None:
        x_left = PAGE_MARGIN_X
        x_right = fig_width - PAGE_MARGIN_X
        comp = self.compliance

        ax.text(
            x_left, TOP_ACCENT_HEIGHT + 0.40,
            self.title,
            fontsize=24, fontweight="bold", color=ACCENT_COLOR,
            ha="left", va="center",
        )

        n_fights = len(comp.fights)
        n_cols = len(comp.assignments)
        subtitle = (
            f"CD Assignment Compliance   ·   "
            f"{n_fights} pull{'s' if n_fights != 1 else ''}   ·   "
            f"{n_cols} assignment{'s' if n_cols != 1 else ''}   ·   "
            f"margin ±{comp.margin_seconds:g}s"
        )
        ax.text(
            x_left, TOP_ACCENT_HEIGHT + 0.72,
            subtitle,
            fontsize=11, color=SOFT_TEXT,
            ha="left", va="center",
        )

        ax.text(
            x_right, TOP_ACCENT_HEIGHT + 0.40,
            self.date,
            fontsize=11, color=DIM_TEXT,
            ha="right", va="center",
        )

    def _draw_column_headers(
        self,
        ax: plt.Axes,
        y_top: float,
        fig_width: float,
        col_width: float,
    ) -> None:
        x_left = PAGE_MARGIN_X
        comp = self.compliance

        # "Pull" column header
        ax.text(
            x_left + 0.10, y_top + COLUMN_HEADER_HEIGHT * 0.5,
            "PULL",
            fontsize=9, fontweight="bold", color=DIM_TEXT,
            ha="left", va="center",
        )

        x = x_left + PULL_COL_WIDTH
        for assignment in comp.assignments:
            cx = x + col_width / 2.0
            class_color = self._class_color(comp.results, assignment.player_name)

            # Phase + time (top line) — class-colored
            ph_time = f"P{assignment.phase}  {_format_mmss(assignment.time_seconds)}"
            ax.text(
                cx, y_top + 0.28,
                ph_time,
                fontsize=10, fontweight="bold", color=class_color,
                ha="center", va="center",
            )

            # Player (middle line) — class-colored, bold
            player = self._truncate(assignment.player_name, col_width, CHAR_W_9)
            ax.text(
                cx, y_top + 0.55,
                player,
                fontsize=9.5, fontweight="bold", color=class_color,
                ha="center", va="center",
            )

            # Optional note text (bottom, dim, italic) — kept muted so it
            # doesn't compete with the class-colored header lines.
            if assignment.text:
                txt = self._truncate(assignment.text, col_width, CHAR_W_8)
                ax.text(
                    cx, y_top + 0.78,
                    txt,
                    fontsize=8, color=DIM_TEXT, style="italic",
                    ha="center", va="center",
                )

            x += col_width

        # Hairline below column header
        rule_y = y_top + COLUMN_HEADER_HEIGHT
        ax.plot(
            [PAGE_MARGIN_X, fig_width - PAGE_MARGIN_X],
            [rule_y, rule_y],
            color=RULE_COLOR, linewidth=0.6, zorder=2,
        )

    def _draw_rows(
        self,
        ax: plt.Axes,
        y_top: float,
        fig_width: float,
        col_width: float,
    ) -> None:
        x_left = PAGE_MARGIN_X
        comp = self.compliance

        # Group fights by report so we can subtly delimit them.
        prev_report: Optional[str] = None
        for row_idx, fight in enumerate(comp.fights):
            row_y = y_top + row_idx * ROW_HEIGHT
            row_center = row_y + ROW_HEIGHT / 2.0

            if prev_report is not None and fight.report_code != prev_report:
                ax.plot(
                    [PAGE_MARGIN_X, fig_width - PAGE_MARGIN_X],
                    [row_y, row_y],
                    color=ACCENT_COLOR, linewidth=0.8, alpha=0.5, zorder=2,
                )
            prev_report = fight.report_code

            # Pull column
            ax.text(
                x_left + 0.10, row_center,
                f"#{fight.pull_index}",
                fontsize=11, fontweight="bold", color=PlotColors.TEXT_PRIMARY,
                ha="left", va="center",
            )

            # Data cells
            x = x_left + PULL_COL_WIDTH
            for a_idx, assignment in enumerate(comp.assignments):
                self._draw_cell(
                    ax,
                    x, row_y, col_width, ROW_HEIGHT,
                    comp.results.get((fight.report_code, fight.fight_id, a_idx)),
                )
                x += col_width

            # Inter-row hairline
            ax.plot(
                [PAGE_MARGIN_X, fig_width - PAGE_MARGIN_X],
                [row_y + ROW_HEIGHT, row_y + ROW_HEIGHT],
                color=RULE_COLOR, linewidth=0.4, zorder=2,
            )

    def _draw_cell(
        self,
        ax: plt.Axes,
        x: float,
        y: float,
        w: float,
        h: float,
        result: Any,
    ) -> None:
        # Inset rect so cells don't visually touch.
        pad = 0.06
        rx, ry = x + pad, y + pad
        rw, rh = w - 2 * pad, h - 2 * pad

        if (
            result is None
            or not result.phase_reached
            or not result.player_in_roster
            or result.player_dead
        ):
            ax.add_patch(Rectangle(
                (rx, ry), rw, rh,
                facecolor=NEUTRAL_FILL, edgecolor="none", zorder=2,
            ))
            if result is None:
                label = "—"
            elif not result.player_in_roster:
                label = "absent"
            elif result.player_dead:
                label = "dead"
            else:
                label = "phase not reached"
            ax.text(
                rx + rw / 2.0, ry + rh / 2.0,
                label,
                fontsize=8.5, color=DIM_TEXT, style="italic",
                ha="center", va="center",
            )
            return

        fill = OK_FILL if result.hit else OFF_FILL
        ax.add_patch(Rectangle(
            (rx, ry), rw, rh,
            facecolor=fill, edgecolor="none", zorder=2,
        ))

        # Spell name (top half) — white for legibility
        spell_name = self._truncate(result.spell_name, rw, CHAR_W_9)
        ax.text(
            rx + rw / 2.0, ry + rh * 0.35,
            spell_name,
            fontsize=9.5, fontweight="bold", color=PlotColors.TEXT_PRIMARY,
            ha="center", va="center",
        )

        # Status (bottom half) — OK or signed delta in seconds
        if result.hit:
            status = "OK"
            color = OK_TEXT
        else:
            if result.actual_offset_seconds is None:
                status = "MISSING"
            else:
                status = f"{result.actual_offset_seconds:+.1f}s"
            color = OFF_TEXT
        ax.text(
            rx + rw / 2.0, ry + rh * 0.72,
            status,
            fontsize=9.5, fontweight="bold", color=color,
            ha="center", va="center",
        )

    # ------------------------------------------------------------------ utils

    @staticmethod
    def _truncate(text: str, width: float, char_width: float) -> str:
        max_chars = max(3, int((width - 0.10) / char_width))
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 1] + "…"

    @staticmethod
    def _class_color(
        results: dict[tuple[str, int, int], Any],
        player_name: str,
    ) -> str:
        for r in results.values():
            if r.player_name == player_name and r.player_class:
                return getattr(ClassColors, r.player_class, PlotColors.TEXT_PRIMARY)
        return PlotColors.TEXT_PRIMARY

    # ------------------------------------------------------------------ saving

    def save_pdf(self, file_path: str) -> str:
        """Render the table to a single-page landscape PDF and return the path."""
        fig = self.create_figure()
        with PdfPages(file_path) as pdf:
            pdf.savefig(
                fig,
                facecolor=PlotColors.BACKGROUND,
                edgecolor="none",
                bbox_inches="tight",
            )
            meta = pdf.infodict()
            meta["Title"] = f"{self.title} — CD Assignment Compliance"
            meta["Subject"] = (
                f"Cooldown assignment compliance, ±{self.compliance.margin_seconds:g}s margin"
            )
            meta["CreationDate"] = datetime.now()
        plt.close(fig)
        logger.info("CD assignment PDF written to %s", file_path)
        return file_path
