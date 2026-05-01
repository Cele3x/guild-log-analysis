"""
Player Deaths visualization module.

Renders per-player death recaps as portrait pages — one page per player.
Designed for multi-page PDF output where the WCL link on each death is a
clickable hyperlink.
"""

import logging
import re
from datetime import datetime
from typing import Any, Optional

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from ..config.constants import ClassColors
from .styles import PlotColors, PlotStyleManager

logger = logging.getLogger(__name__)


class PlayerDeathsPlot:
    """
    Per-player death recap visualization.

    One portrait page per player. Each death is a flowing block: a heading
    row with fight metadata and a clickable WCL link, a small horizontal
    bar chart of the top damage sources, and an inline list of cooldowns
    that were still off cooldown at the moment of death.
    """

    # --- Page geometry (axis-units == inches) ---
    PAGE_WIDTH = 8.27
    PAGE_MARGIN_X = 0.55

    TOP_ACCENT_HEIGHT = 0.06
    HEADER_HEIGHT = 0.85
    HEADER_RULE_PAD = 0.22

    # Per-death block geometry.
    DEATH_TOP_PAD = 0.22
    META_ROW_HEIGHT = 0.36
    META_TO_BARS_GAP = 0.22
    DAMAGE_ROW_HEIGHT = 0.30
    BARS_TO_CD_GAP = 0.30
    CD_LINE_HEIGHT = 0.26
    DEATH_BOTTOM_PAD = 0.22
    DEATH_SEPARATOR_PAD = 0.04  # extra space for separator hairline

    PAGE_BOTTOM_PAD = 0.45

    # Bar geometry inside a damage row.
    BAR_HEIGHT = 0.18
    BAR_TRACK_COLOR = "#2A313B"

    # Type colors for cooldown names.
    TYPE_COLORS = {
        "defensive": "#5DADE2",
        "heal": "#58D68D",
        "external": "#F4D03F",
        "raid_defensive": "#BB8FCE",
        "consumable": "#E59866",
    }
    TYPE_PRIORITY = {
        "defensive": 0,
        "heal": 1,
        "raid_defensive": 2,
        "external": 3,
        "consumable": 4,
    }

    WOWHEAD_URL = "https://www.wowhead.com/spell={spell_id}"

    DIM_TEXT = "#8E96A1"
    SOFT_TEXT = "#B6BCC4"
    RULE_COLOR = "#2D343F"
    KILL_BLOW_COLOR = "#FF6B6B"
    LINK_COLOR = "#5DADE2"

    # Char-width approximations (axis units) at common font sizes.
    CHAR_W_10 = 0.082
    CHAR_W_11 = 0.090
    CHAR_W_22 = 0.180

    def __init__(
        self,
        title: str,
        date: str,
        player_data: list[dict[str, Any]],
        figsize: tuple[int, int] = (8, 11),  # kept for API compat; ignored
    ) -> None:
        """
        Initialize player deaths plot.

        :param title: Plot title (used in PDF metadata only)
        :param date: Date string for the plot
        :param player_data: List of player death data
        :param figsize: Ignored; portrait pages are sized to content.
        """
        self.title = title
        self.date = date
        self.player_data = player_data
        self.figsize = figsize

    # ------------------------------------------------------------------ helpers

    def _content_width(self) -> float:
        return self.PAGE_WIDTH - 2 * self.PAGE_MARGIN_X

    @classmethod
    def _wowhead_url(cls, spell_id: Optional[int]) -> Optional[str]:
        if spell_id is None or spell_id <= 0:
            return None
        return cls.WOWHEAD_URL.format(spell_id=spell_id)

    @staticmethod
    def _format_mmss(seconds: float) -> str:
        seconds = max(0, int(round(seconds)))
        return f"{seconds // 60}:{seconds % 60:02d}"

    def _wrap_separated(
        self,
        items: list[tuple[str, str, Optional[str]]],
        width: float,
        char_width: float = 0.082,
        sep: str = "  ·  ",
        sep_advance: float = 0.32,
    ) -> list[list[tuple[float, str, str, bool, Optional[str]]]]:
        """
        Wrap ``(label, color, url)`` items onto bullet-separated lines.

        :returns: lines; each line is
            ``[(x_offset, text, color, is_sep, url), ...]``.
            Separators carry no url and are rendered in a muted color.
        """
        if not items:
            return []
        lines: list[list[tuple[float, str, str, bool, Optional[str]]]] = []
        current: list[tuple[float, str, str, bool, Optional[str]]] = []
        cur_x = 0.0
        for idx, (label, color, url) in enumerate(items):
            label_advance = len(label) * char_width
            need_sep = idx > 0
            advance = label_advance + (sep_advance if need_sep else 0.0)
            if current and cur_x + advance > width:
                lines.append(current)
                current = [(0.0, label, color, False, url)]
                cur_x = label_advance
                continue
            if need_sep:
                current.append((cur_x, sep, self.RULE_COLOR, True, None))
                cur_x += sep_advance
            current.append((cur_x, label, color, False, url))
            cur_x += label_advance
        if current:
            lines.append(current)
        return lines

    # ------------------------------------------------------------------ layout

    def _compute_death_layout(self, death: dict[str, Any]) -> dict[str, Any]:
        damage_sources = [
            s for s in (death.get("damage_sources") or [])
            if s.get("hp_percentage", 0) > 0.0
        ][:3]
        n_dmg = max(1, len(damage_sources))

        sorted_avail = sorted(
            death.get("available_defensives") or [],
            key=lambda a: (self.TYPE_PRIORITY.get(a["type"], 9), a["name"]),
        )
        items = [
            (
                a["name"],
                self.TYPE_COLORS.get(a["type"], PlotColors.TEXT_PRIMARY),
                self._wowhead_url(a.get("spell_id")),
            )
            for a in sorted_avail
        ]
        wrapped = self._wrap_separated(items, self._content_width())
        n_cd_lines = max(1, len(wrapped))

        damage_section_h = n_dmg * self.DAMAGE_ROW_HEIGHT
        cd_section_h = n_cd_lines * self.CD_LINE_HEIGHT

        block_h = (
            self.DEATH_TOP_PAD
            + self.META_ROW_HEIGHT
            + self.META_TO_BARS_GAP
            + damage_section_h
            + self.BARS_TO_CD_GAP
            + cd_section_h
            + self.DEATH_BOTTOM_PAD
        )
        return {
            "damage_sources": damage_sources,
            "wrapped_cooldowns": wrapped,
            "has_cooldowns": bool(items),
            "block_height": block_h,
        }

    def _compute_page_layout(self, deaths: list[dict[str, Any]]) -> dict[str, Any]:
        blocks = [self._compute_death_layout(d) for d in deaths]
        deaths_height = sum(b["block_height"] for b in blocks)
        # Separators between blocks (n - 1) consume just a hairline of space.
        deaths_height += max(0, len(blocks) - 1) * self.DEATH_SEPARATOR_PAD
        page_height = (
            self.TOP_ACCENT_HEIGHT
            + self.HEADER_HEIGHT
            + self.HEADER_RULE_PAD
            + deaths_height
            + self.PAGE_BOTTOM_PAD
        )
        return {"blocks": blocks, "page_height": page_height}

    # ------------------------------------------------------------------ public

    def create_plot(self) -> plt.Figure:
        """Render the first player's page (legacy single-figure path)."""
        if not self.player_data:
            return self._create_empty_plot()
        figs = self.create_player_figures()
        if not figs:
            return self._create_empty_plot()
        return figs[0][1]

    def create_player_figures(self) -> list[tuple[dict[str, Any], plt.Figure]]:
        """Build one portrait figure per player, sized to its content."""
        PlotStyleManager.setup_plot_style()
        out: list[tuple[dict[str, Any], plt.Figure]] = []
        for player_info in self.player_data:
            deaths = player_info.get("deaths") or []
            if not deaths:
                continue
            layout = self._compute_page_layout(deaths)
            fig = plt.figure(figsize=(self.PAGE_WIDTH, layout["page_height"]))
            fig.patch.set_facecolor(PlotColors.BACKGROUND)
            ax = fig.add_axes([0, 0, 1, 1])
            ax.set_xlim(0, self.PAGE_WIDTH)
            ax.set_ylim(0, layout["page_height"])
            ax.invert_yaxis()
            ax.set_facecolor(PlotColors.BACKGROUND)
            ax.axis("off")
            self._draw_page(ax, player_info, deaths, layout)
            out.append((player_info, fig))
        return out

    def _create_empty_plot(self) -> plt.Figure:
        PlotStyleManager.setup_plot_style()
        fig, ax = plt.subplots(figsize=(self.PAGE_WIDTH, 4))
        ax.text(
            0.5, 0.5,
            "No player deaths data available",
            ha="center", va="center", transform=ax.transAxes,
            fontsize=14, color=self.DIM_TEXT,
        )
        fig.patch.set_facecolor(PlotColors.BACKGROUND)
        ax.set_facecolor(PlotColors.BACKGROUND)
        ax.axis("off")
        return fig

    # ------------------------------------------------------------------ drawing

    def _draw_page(
        self,
        ax: plt.Axes,
        player_info: dict[str, Any],
        deaths: list[dict[str, Any]],
        layout: dict[str, Any],
    ) -> None:
        player_class = player_info.get("player_class", "Unknown")
        class_color = getattr(ClassColors, player_class, PlotColors.TEXT_PRIMARY)
        damage_palette = self._build_damage_source_palette(deaths, class_color)

        # Top accent strip — full bleed, class colored.
        ax.add_patch(Rectangle(
            (0, 0), self.PAGE_WIDTH, self.TOP_ACCENT_HEIGHT,
            facecolor=class_color, edgecolor="none", zorder=2,
        ))

        # Header.
        header_top = self.TOP_ACCENT_HEIGHT
        self._draw_header(ax, player_info, deaths, header_top, class_color)

        # Hairline rule under header.
        rule_y = header_top + self.HEADER_HEIGHT + self.HEADER_RULE_PAD * 0.55
        ax.plot(
            [self.PAGE_MARGIN_X, self.PAGE_WIDTH - self.PAGE_MARGIN_X],
            [rule_y, rule_y],
            color=self.RULE_COLOR, linewidth=0.8, zorder=2,
        )

        # Death blocks.
        y = (
            self.TOP_ACCENT_HEIGHT
            + self.HEADER_HEIGHT
            + self.HEADER_RULE_PAD
        )
        for idx, (death, block) in enumerate(zip(deaths, layout["blocks"])):
            self._draw_death_block(ax, idx, death, block, y, class_color, damage_palette)
            y += block["block_height"]
            if idx < len(deaths) - 1:
                # Subtle separator hairline between deaths.
                ax.plot(
                    [self.PAGE_MARGIN_X, self.PAGE_WIDTH - self.PAGE_MARGIN_X],
                    [y + self.DEATH_SEPARATOR_PAD / 2,
                     y + self.DEATH_SEPARATOR_PAD / 2],
                    color=self.RULE_COLOR, linewidth=0.6, zorder=2,
                )
                y += self.DEATH_SEPARATOR_PAD

    def _draw_header(
        self,
        ax: plt.Axes,
        player_info: dict[str, Any],
        deaths: list[dict[str, Any]],
        y_top: float,
        class_color: str,
    ) -> None:
        player_name = player_info["player_name"]
        player_class = player_info.get("player_class", "Unknown")
        player_spec = player_info.get("player_spec")

        x_left = self.PAGE_MARGIN_X
        x_right = self.PAGE_WIDTH - self.PAGE_MARGIN_X

        # Player name — large, class colored.
        ax.text(
            x_left, y_top + 0.40,
            player_name,
            fontsize=26, fontweight="bold", color=class_color,
            ha="left", va="center",
        )

        # Subtitle: spec / class, death count.
        spec_class = (
            f"{player_spec} {player_class.title()}"
            if player_spec else player_class.title()
        )
        n_deaths = len(deaths)
        subtitle = (
            f"{spec_class}   ·   {n_deaths} death"
            f"{'s' if n_deaths != 1 else ''}"
        )
        ax.text(
            x_left, y_top + 0.72,
            subtitle,
            fontsize=11, color=self.SOFT_TEXT,
            ha="left", va="center",
        )

        # Date — right aligned, baseline matches name.
        ax.text(
            x_right, y_top + 0.40,
            self.date,
            fontsize=11, color=self.DIM_TEXT,
            ha="right", va="center",
        )

    def _build_damage_source_palette(
        self, deaths: list[dict[str, Any]], class_color: str
    ) -> dict[str, str]:
        """Build a stable, harmonious palette for damage source names."""
        names: list[str] = []
        for death in deaths:
            for source in death.get("damage_sources", []) or []:
                if source.get("hp_percentage", 0) > 0.0:
                    name = source["name"]
                    if name not in names:
                        names.append(name)
        # Use a curated palette that reads well on dark backgrounds.
        base_palette = [
            "#E07A5F", "#81B29A", "#F2CC8F", "#9D8DF1",
            "#5DADE2", "#F4A261", "#A0CED9", "#E5989B",
            "#B5E48C", "#FFB4A2", "#76C7C0", "#D7B3F0",
        ]
        return {name: base_palette[i % len(base_palette)] for i, name in enumerate(names)}

    # ------------------------------------------------------------------ blocks

    def _draw_death_block(
        self,
        ax: plt.Axes,
        idx: int,
        death: dict[str, Any],
        block: dict[str, Any],
        y_top: float,
        class_color: str,
        damage_palette: dict[str, str],
    ) -> None:
        x_left = self.PAGE_MARGIN_X
        x_right = self.PAGE_WIDTH - self.PAGE_MARGIN_X

        # --- Meta row ---
        meta_y = y_top + self.DEATH_TOP_PAD + self.META_ROW_HEIGHT * 0.5

        # Death # in the class color, bold.
        title = f"Death {idx + 1}"
        ax.text(
            x_left, meta_y,
            title,
            fontsize=15, fontweight="bold", color=class_color,
            ha="left", va="center",
        )

        # Inline fight metadata — bullet-separated, muted.
        title_advance = len(title) * 0.13 + 0.20  # rough advance for fontsize 15 bold
        fight_id = death.get("fight_id")
        time_str = self._format_mmss(death.get("fight_time_seconds", 0))
        length_str = self._format_mmss(death.get("fight_length_seconds", 0))
        meta = f"Fight {fight_id}   ·   {time_str} of {length_str}"
        ax.text(
            x_left + title_advance, meta_y,
            meta,
            fontsize=10.5, color=self.SOFT_TEXT,
            ha="left", va="center",
        )

        # WCL hyperlink — right aligned, no icon. Underlined-style by color only.
        wcl_url = death.get("wcl_url")
        if wcl_url:
            ax.text(
                x_right, meta_y,
                "View on Warcraft Logs",
                fontsize=10.5, color=self.LINK_COLOR,
                ha="right", va="center", url=wcl_url, fontweight="bold",
            )

        # --- Damage source bars ---
        bars_top = (
            y_top
            + self.DEATH_TOP_PAD
            + self.META_ROW_HEIGHT
            + self.META_TO_BARS_GAP
        )
        damage_sources = block["damage_sources"]
        if damage_sources:
            self._draw_damage_bars(
                ax, x_left, x_right, bars_top, damage_sources, damage_palette
            )
            bars_bottom = bars_top + len(damage_sources) * self.DAMAGE_ROW_HEIGHT
        else:
            ax.text(
                x_left, bars_top + self.DAMAGE_ROW_HEIGHT / 2,
                "No damage sources captured",
                fontsize=10, color=self.DIM_TEXT, style="italic",
                ha="left", va="center",
            )
            bars_bottom = bars_top + self.DAMAGE_ROW_HEIGHT

        # --- Cooldowns line ---
        cd_top = bars_bottom + self.BARS_TO_CD_GAP
        self._draw_cooldowns(
            ax, x_left, x_right, cd_top,
            block["wrapped_cooldowns"], block["has_cooldowns"],
        )

    def _draw_damage_bars(
        self,
        ax: plt.Axes,
        x_left: float,
        x_right: float,
        y_top: float,
        damage_sources: list[dict[str, Any]],
        damage_palette: dict[str, str],
    ) -> None:
        # Layout: name (left), bar (middle), percentage (right).
        total_w = x_right - x_left
        name_col_w = 2.85
        pct_col_w = 0.65
        gap = 0.18
        bar_x = x_left + name_col_w + gap
        bar_w = total_w - name_col_w - pct_col_w - 2 * gap

        max_pct = max(s.get("hp_percentage", 0) for s in damage_sources)
        # Scale so the largest source fills the bar — keeps small deaths legible.
        scale_ref = max(max_pct, 1e-6)

        for i, source in enumerate(damage_sources):
            row_y = y_top + self.DAMAGE_ROW_HEIGHT * (i + 0.5)
            color = damage_palette.get(source["name"], PlotColors.TEXT_PRIMARY)
            is_kill = source.get("is_killing_blow", False)
            pct = source.get("hp_percentage", 0)

            # Source name — truncate gracefully if too long.
            name = source["name"]
            max_chars = int(name_col_w / self.CHAR_W_10) - 1
            if len(name) > max_chars:
                name = name[: max_chars - 1] + "…"

            name_color = self.KILL_BLOW_COLOR if is_kill else PlotColors.TEXT_PRIMARY
            wh_url = self._wowhead_url(source.get("ability_id"))
            link_kwargs = {"url": wh_url} if wh_url else {}
            ax.text(
                x_left, row_y,
                name,
                fontsize=10.5, color=name_color,
                ha="left", va="center",
                fontweight="bold" if is_kill else "normal",
                **link_kwargs,
            )
            if is_kill:
                # Inline "killing blow" tag, placed just after the name.
                name_advance = len(name) * (self.CHAR_W_10 * 1.05)
                ax.text(
                    x_left + name_advance + 0.10, row_y,
                    "killing blow",
                    fontsize=8, color=self.KILL_BLOW_COLOR,
                    ha="left", va="center", style="italic",
                )

            # Track.
            track_y = row_y - self.BAR_HEIGHT / 2
            ax.add_patch(Rectangle(
                (bar_x, track_y), bar_w, self.BAR_HEIGHT,
                facecolor=self.BAR_TRACK_COLOR, edgecolor="none", zorder=2,
            ))
            # Filled bar.
            fill_w = bar_w * (pct / scale_ref)
            fill_color = self._tint(color, 0.0) if not is_kill else color
            ax.add_patch(Rectangle(
                (bar_x, track_y), fill_w, self.BAR_HEIGHT,
                facecolor=fill_color, edgecolor="none", zorder=3,
            ))

            # Percentage on the right.
            ax.text(
                x_right, row_y,
                f"{pct:.0f}%",
                fontsize=10.5, color=PlotColors.TEXT_PRIMARY,
                ha="right", va="center",
                fontweight="bold" if is_kill else "normal",
            )

    @staticmethod
    def _tint(hex_color: str, amount: float) -> str:
        """Return ``hex_color`` blended toward white by ``amount`` in [0, 1]."""
        try:
            rgb = mcolors.to_rgb(hex_color)
        except ValueError:
            return hex_color
        r, g, b = (c + (1 - c) * amount for c in rgb)
        return mcolors.to_hex((r, g, b))

    def _draw_cooldowns(
        self,
        ax: plt.Axes,
        x_left: float,
        x_right: float,
        y_top: float,
        wrapped: list[list[tuple[float, str, str, bool]]],
        has_cooldowns: bool,
    ) -> None:
        label = "Cooldowns ready"
        ax.text(
            x_left, y_top + self.CD_LINE_HEIGHT * 0.5,
            label.upper(),
            fontsize=8.5, fontweight="bold",
            color=self.DIM_TEXT, ha="left", va="center",
        )
        # Names start at a fixed indent so wrapped lines align cleanly.
        names_x = x_left + 1.55

        if not has_cooldowns:
            ax.text(
                names_x, y_top + self.CD_LINE_HEIGHT * 0.5,
                "nothing off cooldown",
                fontsize=10, color=self.DIM_TEXT, style="italic",
                ha="left", va="center",
            )
            return

        # Re-wrap to the narrower remaining width.
        avail_w = (x_right - names_x)
        # We already wrapped to content_width; re-wrap to avail_w if it's narrower.
        if avail_w < self._content_width():
            # Cheap re-wrap: flatten labels and re-run.
            flat: list[tuple[str, str, Optional[str]]] = []
            for line in wrapped:
                for _x, text, color, is_sep, url in line:
                    if not is_sep:
                        flat.append((text, color, url))
            wrapped = self._wrap_separated(flat, avail_w)

        for line_idx, line in enumerate(wrapped):
            line_y = y_top + self.CD_LINE_HEIGHT * (line_idx + 0.5)
            for x_off, text, color, _is_sep, url in line:
                kwargs = {"url": url} if url else {}
                ax.text(
                    names_x + x_off, line_y,
                    text,
                    fontsize=10, color=color,
                    ha="left", va="center",
                    **kwargs,
                )

    # ------------------------------------------------------------------ saving

    def save(self, filename: Optional[str] = None) -> str:
        """Save the (legacy) first-player figure to a PNG."""
        if filename is None:
            try:
                date_obj = datetime.strptime(self.date, "%d.%m.%Y")
                date_stamp = date_obj.strftime("%Y-%m-%d")
            except (ValueError, AttributeError):
                date_stamp = datetime.now().strftime("%Y-%m-%d")
            clean_title = re.sub(r"[^\w\s-]", "", self.title)
            clean_title = re.sub(r"[-\s]+", "_", clean_title).strip("_").lower()
            filename = f"{date_stamp}_{clean_title}_player_deaths.png"

        from ..config.settings import Settings
        plots_dir = Settings().plots_directory
        file_path = plots_dir / filename
        fig = self.create_plot()
        fig.savefig(
            file_path, dpi=300, bbox_inches="tight",
            facecolor=fig.get_facecolor(), edgecolor="none", pad_inches=0.1,
        )
        plt.close(fig)
        logger.info(f"Player deaths plot saved to {file_path}")
        return str(file_path)

    def show(self) -> None:
        fig = self.create_plot()
        plt.show()
        plt.close(fig)
