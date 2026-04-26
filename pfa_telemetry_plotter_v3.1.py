"""
PFA TELEMETRY PLOTTER — Post Flight Analysis Tool
===================================================
Developed By Chiranjib | Co-Developed by Biswajit

Requirements:
  pip install matplotlib pandas openpyxl nuitka ordered-set

Build:
  python -m nuitka pfa_telemetry_plotter.py
  (see nuitka_build.txt for build config)

"""

import tkinter as tk
from tkinter import ttk, filedialog, colorchooser
import pandas as pd
import numpy as np
import os

import matplotlib
# Handle mpl-data path when compiled with Nuitka
if getattr(matplotlib, "__compiled__", False) or hasattr(os, "__compiled__"):
    _base = os.path.dirname(os.path.abspath(__file__))
    _mpl_data = os.path.join(_base, "matplotlib", "mpl-data")
    if os.path.isdir(_mpl_data):
        matplotlib.matplotlib_fname = lambda: os.path.join(_mpl_data, "matplotlibrc")
        matplotlib.rcParams["datapath"] = _mpl_data
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.animation as animation
import matplotlib.pyplot as plt

# ============================================================
#  CONSTANTS
# ============================================================
COLORS_DEFAULT = ["#3b82f6", "#ef4444", "#22c55e", "#f59e0b", "#8b5cf6",
                  "#ec4899", "#06b6d4", "#f97316", "#14b8a6", "#a855f7"]
CHUNK_SIZE = None  # No limit — load full file

THEMES = {
    "dark": {
        "bg": "#1a1a2e", "panel": "#16213e", "accent": "#0f3460",
        "text": "#e0e0e0", "text2": "#aaaaaa", "muted": "#666666",
        "button": "#0f3460", "entry": "#1a1a2e",
        "topbar": "#0d1b2a", "title_fg": "#7ec8e3", "credit_fg": "#e6c85e",
        "file_ok": "#7ec8e3",
        "plot_face": "#0f0f0f", "ax_face": "#111111", "grid": "#222222",
        "spine": "#333333", "tick": "#888888", "label": "#aaaaaa", "plot_title": "#cccccc",
        "leg_bg": "#1a1a1a", "leg_edge": "#333333", "leg_text": "#cccccc",
        "cursor_bg": "#222222", "cursor_text": "#eeeeee",
        "select_bg": "#0f3460", "select_fg": "#e0e0e0",
        "combo_list_bg": "#1a1a2e", "combo_list_fg": "#e0e0e0",
    },
    "light": {
        "bg": "#f0f0f0", "panel": "#e6e6e6", "accent": "#4a90d9",
        "text": "#222222", "text2": "#444444", "muted": "#999999",
        "button": "#4a90d9", "entry": "#ffffff",
        "topbar": "#ffffff", "title_fg": "#2c5aa0", "credit_fg": "#b8860b",
        "file_ok": "#2c5aa0",
        "plot_face": "#ffffff", "ax_face": "#ffffff", "grid": "#d0d0d0",
        "spine": "#444444", "tick": "#333333", "label": "#333333", "plot_title": "#111111",
        "leg_bg": "#ffffff", "leg_edge": "#aaaaaa", "leg_text": "#333333",
        "cursor_bg": "#ffffff", "cursor_text": "#111111",
        "select_bg": "#4a90d9", "select_fg": "#ffffff",
        "combo_list_bg": "#ffffff", "combo_list_fg": "#222222",
    }
}

# Start with dark as default (set at runtime)
T = THEMES["dark"]

# ============================================================
#  APP ICON
# ============================================================
def create_app_icon(root, size=64):
    """Create a graph-style icon as PhotoImage — no external files."""
    img = tk.PhotoImage(width=size, height=size)
    s = size

    # Background — dark blue rounded feel
    for y in range(s):
        for x in range(s):
            img.put("#0f3460", (x, y))

    # Border
    for i in range(s):
        img.put("#7ec8e3", (i, 0))
        img.put("#7ec8e3", (i, s - 1))
        img.put("#7ec8e3", (0, i))
        img.put("#7ec8e3", (s - 1, i))
        if i < s - 1:
            img.put("#7ec8e3", (i, 1))
            img.put("#7ec8e3", (1, i))

    # Grid lines
    for g in range(12, s - 8, 10):
        for x in range(8, s - 8, 3):
            img.put("#1a3a6a", (x, g))
        for y in range(8, s - 8, 3):
            img.put("#1a3a6a", (g, y))

    # Axes
    ax_left = 10
    ax_bottom = s - 12
    for x in range(ax_left, s - 6):
        img.put("#5588aa", (x, ax_bottom))
    for y in range(6, ax_bottom + 1):
        img.put("#5588aa", (ax_left, y))

    # Plot line — a nice upward trend with a dip
    points = [
        (12, 42), (16, 38), (20, 35), (24, 30), (28, 33),
        (32, 28), (36, 22), (40, 18), (44, 20), (48, 15),
        (52, 12), (56, 10)
    ]
    # Scale to icon size
    scale = s / 64.0
    scaled = [(int(x * scale), int(y * scale)) for x, y in points]

    # Draw thick line
    for i in range(len(scaled) - 1):
        x0, y0 = scaled[i]
        x1, y1 = scaled[i + 1]
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for t in range(steps + 1):
            px = x0 + (x1 - x0) * t // steps
            py = y0 + (y1 - y0) * t // steps
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    nx, ny = px + dx, py + dy
                    if 2 <= nx < s - 2 and 2 <= ny < s - 2:
                        img.put("#3b82f6", (nx, ny))

    # Data dots
    for x, y in scaled[::2]:
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx * dx + dy * dy <= 5:
                    nx, ny = x + dx, y + dy
                    if 2 <= nx < s - 2 and 2 <= ny < s - 2:
                        img.put("#7ec8e3", (nx, ny))

    return img

# ============================================================
#  STYLED MESSAGE DIALOGS
# ============================================================
class StyledDialog(tk.Toplevel):
    """Custom themed message dialog replacing default messagebox."""

    # Icon shapes drawn on canvas
    ICONS = {
        "info": {"bg": "#3b82f6", "symbol": "i"},
        "warning": {"bg": "#f59e0b", "symbol": "!"},
        "error": {"bg": "#ef4444", "symbol": "✕"},
        "success": {"bg": "#22c55e", "symbol": "✓"},
    }

    def __init__(self, parent, title, message, icon_type="info"):
        super().__init__(parent)
        self.title(title)
        bg = T["bg"]
        self.configure(bg=bg)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        try:
            self.iconphoto(False, parent._app_icon)
        except Exception:
            pass
        self.update_idletasks()
        w, h = 380, 160
        px = parent.winfo_x() + (parent.winfo_width() - w) // 2
        py = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{px}+{py}")

        icon_info = self.ICONS.get(icon_type, self.ICONS["info"])
        main = tk.Frame(self, bg=bg, padx=20, pady=15)
        main.pack(fill="both", expand=True)
        icon_canvas = tk.Canvas(main, width=44, height=44, bg=bg, highlightthickness=0)
        icon_canvas.pack(side="left", padx=(0, 15))
        icon_canvas.create_oval(2, 2, 42, 42, fill=icon_info["bg"], outline=icon_info["bg"], width=0)
        icon_canvas.create_text(22, 22, text=icon_info["symbol"], fill="white", font=("Consolas", 18, "bold"))

        text_frame = tk.Frame(main, bg=bg)
        text_frame.pack(side="left", fill="both", expand=True)
        tk.Label(text_frame, text=title, bg=bg, fg=T["text"],
                 font=("Consolas", 11, "bold"), anchor="w").pack(anchor="w")
        tk.Label(text_frame, text=message, bg=bg, fg=T["text2"],
                 font=("Consolas", 9), anchor="w", wraplength=260,
                 justify="left").pack(anchor="w", pady=(5, 0))

        btn_frame = tk.Frame(self, bg=bg)
        btn_frame.pack(fill="x", padx=20, pady=(0, 12))
        ok_btn = tk.Button(btn_frame, text="OK", command=self.destroy,
                            bg=icon_info["bg"], fg="white",
                            font=("Consolas", 9, "bold"), relief="flat",
                            padx=20, pady=4, cursor="hand2",
                            activebackground=icon_info["bg"],
                            activeforeground="white")
        ok_btn.pack(side="right")

        # Bind Enter/Escape
        self.bind("<Return>", lambda e: self.destroy())
        self.bind("<Escape>", lambda e: self.destroy())
        ok_btn.focus_set()

        self.wait_window()

def styled_info(parent, title, message):
    StyledDialog(parent, title, message, "info")

def styled_warning(parent, title, message):
    StyledDialog(parent, title, message, "warning")

def styled_error(parent, title, message):
    StyledDialog(parent, title, message, "error")

def styled_success(parent, title, message):
    StyledDialog(parent, title, message, "success")

# ============================================================
#  ZOOM HANDLER
# ============================================================
class ZoomHandler:
    """Scroll-wheel zoom + left-drag pan + Page Up/Down zoom, clamped to data bounds."""

    ZOOM_FACTOR = 0.12
    ZOOM_OUT_PAD = 0.5
    DRAG_THRESHOLD = 5

    def __init__(self, ax, canvas):
        self.ax = ax
        self.canvas = canvas
        self.orig_xlim = None
        self.orig_ylim = None
        self._captured = False

        # Pan state
        self._panning = False
        self._pan_start = None
        self._press_pixel = None   # screen coords at press
        self.was_dragged = False    # flag for DataCursor to check
        self.enabled = True         # can be toggled by checkbox

        self._cid_scroll = canvas.mpl_connect("scroll_event", self._on_scroll)
        self._cid_dblclick = canvas.mpl_connect("button_press_event", self._on_press)
        self._cid_release = canvas.mpl_connect("button_release_event", self._on_release)
        self._cid_motion = canvas.mpl_connect("motion_notify_event", self._on_motion)
        self._cid_keypress = canvas.mpl_connect("key_press_event", self._on_key_zoom)

    def _capture_orig(self):
        if not self._captured:
            self.orig_xlim = tuple(self.ax.get_xlim())
            self.orig_ylim = tuple(self.ax.get_ylim())
            self._captured = True

    def _get_bounds(self):
        """Max allowed view = original range + padding on each side."""
        ox = self.orig_xlim
        oy = self.orig_ylim
        x_pad = (ox[1] - ox[0]) * self.ZOOM_OUT_PAD
        y_pad = (oy[1] - oy[0]) * self.ZOOM_OUT_PAD
        return (
            ox[0] - x_pad, ox[1] + x_pad,
            oy[0] - y_pad, oy[1] + y_pad,
        )

    def _clamp_view(self, x_lo, x_hi, y_lo, y_hi):
        """Clamp the view so it never slides beyond allowed bounds."""
        bx_lo, bx_hi, by_lo, by_hi = self._get_bounds()
        x_range = x_hi - x_lo
        y_range = y_hi - y_lo

        # Clamp range to not exceed max bounds
        max_x = bx_hi - bx_lo
        max_y = by_hi - by_lo
        if x_range > max_x:
            cx = (x_lo + x_hi) / 2
            x_lo, x_hi = cx - max_x / 2, cx + max_x / 2
            x_range = max_x
        if y_range > max_y:
            cy = (y_lo + y_hi) / 2
            y_lo, y_hi = cy - max_y / 2, cy + max_y / 2
            y_range = max_y

        # Slide back into bounds if shifted out
        if x_lo < bx_lo:
            x_lo, x_hi = bx_lo, bx_lo + x_range
        if x_hi > bx_hi:
            x_lo, x_hi = bx_hi - x_range, bx_hi
        if y_lo < by_lo:
            y_lo, y_hi = by_lo, by_lo + y_range
        if y_hi > by_hi:
            y_lo, y_hi = by_hi - y_range, by_hi

        return x_lo, x_hi, y_lo, y_hi

    def _on_scroll(self, event):
        if not self.enabled or event.inaxes != self.ax:
            return
        self._capture_orig()

        if event.button == "up":
            scale = 1 - self.ZOOM_FACTOR   # zoom in
        elif event.button == "down":
            scale = 1 + self.ZOOM_FACTOR   # zoom out
        else:
            return

        # Current limits
        x_lo, x_hi = self.ax.get_xlim()
        y_lo, y_hi = self.ax.get_ylim()

        # Zoom center = mouse position in data coords
        cx, cy = event.xdata, event.ydata

        # Scale around cursor — the point under cursor stays fixed
        new_x_lo = cx - (cx - x_lo) * scale
        new_x_hi = cx + (x_hi - cx) * scale
        new_y_lo = cy - (cy - y_lo) * scale
        new_y_hi = cy + (y_hi - cy) * scale

        # Clamp so view never leaves data bounds
        new_x_lo, new_x_hi, new_y_lo, new_y_hi = self._clamp_view(
            new_x_lo, new_x_hi, new_y_lo, new_y_hi
        )

        self.ax.set_xlim(new_x_lo, new_x_hi)
        self.ax.set_ylim(new_y_lo, new_y_hi)
        self.canvas.draw_idle()

    def _on_press(self, event):
        if not self.enabled or event.inaxes != self.ax:
            return
        self._capture_orig()

        # Double-click middle mouse → reset
        if event.dblclick and event.button == 2:
            self.ax.set_xlim(self.orig_xlim)
            self.ax.set_ylim(self.orig_ylim)
            self.canvas.draw_idle()
            return

        # Left-click → potential pan (activates after drag threshold)
        if event.button == 1:
            self._press_pixel = (event.x, event.y)
            self._pan_start = (event.xdata, event.ydata)
            self._panning = False
            self.was_dragged = False

    def _on_release(self, event):
        self._panning = False
        self._pan_start = None
        self._press_pixel = None

    def _on_motion(self, event):
        if self._pan_start is None or event.inaxes != self.ax:
            return

        # Check drag threshold before activating pan
        if not self._panning and self._press_pixel:
            dx_px = abs(event.x - self._press_pixel[0])
            dy_px = abs(event.y - self._press_pixel[1])
            if dx_px > self.DRAG_THRESHOLD or dy_px > self.DRAG_THRESHOLD:
                self._panning = True
                self.was_dragged = True
            else:
                return

        dx = self._pan_start[0] - event.xdata
        dy = self._pan_start[1] - event.ydata

        x_lo, x_hi = self.ax.get_xlim()
        y_lo, y_hi = self.ax.get_ylim()

        new_x_lo, new_x_hi, new_y_lo, new_y_hi = self._clamp_view(
            x_lo + dx, x_hi + dx, y_lo + dy, y_hi + dy
        )

        self.ax.set_xlim(new_x_lo, new_x_hi)
        self.ax.set_ylim(new_y_lo, new_y_hi)
        self.canvas.draw_idle()

    def _on_key_zoom(self, event):
        """Page Up = zoom in, Page Down = zoom out (centered on plot midpoint)."""
        if not self.enabled or event.inaxes != self.ax:
            return
        if event.key not in ("pageup", "pagedown"):
            return
        self._capture_orig()

        scale = (1 - self.ZOOM_FACTOR) if event.key == "pageup" else (1 + self.ZOOM_FACTOR)

        x_lo, x_hi = self.ax.get_xlim()
        y_lo, y_hi = self.ax.get_ylim()
        cx = (x_lo + x_hi) / 2
        cy = (y_lo + y_hi) / 2

        new_x_lo = cx - (cx - x_lo) * scale
        new_x_hi = cx + (x_hi - cx) * scale
        new_y_lo = cy - (cy - y_lo) * scale
        new_y_hi = cy + (y_hi - cy) * scale

        new_x_lo, new_x_hi, new_y_lo, new_y_hi = self._clamp_view(
            new_x_lo, new_x_hi, new_y_lo, new_y_hi
        )
        self.ax.set_xlim(new_x_lo, new_x_hi)
        self.ax.set_ylim(new_y_lo, new_y_hi)
        self.canvas.draw_idle()
# ============================================================
#  JUNK SELECTOR
# ============================================================
class JunkSelector:
    """Drag-select scatter points to remove. DEL to confirm removal."""

    def __init__(self, ax, canvas, plot_df, x_col, y_cols, on_remove_callback):
        self.ax = ax
        self.canvas = canvas
        self.plot_df = plot_df
        self.x_col = x_col
        self.y_cols = y_cols
        self.on_remove = on_remove_callback
        self.selecting = False
        self.rect = None
        self.start_xy = None
        self.selected_indices = set()
        self.highlight_artists = []

        self._cid_press = canvas.mpl_connect("button_press_event", self._on_press)
        self._cid_motion = canvas.mpl_connect("motion_notify_event", self._on_motion)
        self._cid_release = canvas.mpl_connect("button_release_event", self._on_release)
        self._cid_key = canvas.mpl_connect("key_press_event", self._on_key)

    def _on_press(self, event):
        if event.inaxes != self.ax or event.button != 1:
            return
        self.selecting = True
        self.start_xy = (event.xdata, event.ydata)
        # Draw selection rectangle
        if self.rect:
            self.rect.remove()
        self.rect = self.ax.axvspan(event.xdata, event.xdata, alpha=0.15, color="#ff4444", zorder=5)
        self.canvas.draw_idle()

    def _on_motion(self, event):
        if not self.selecting or event.inaxes != self.ax or self.start_xy is None:
            return
        # Update rectangle
        if self.rect:
            self.rect.remove()
        x0 = min(self.start_xy[0], event.xdata)
        x1 = max(self.start_xy[0], event.xdata)
        y0 = min(self.start_xy[1], event.ydata)
        y1 = max(self.start_xy[1], event.ydata)

        from matplotlib.patches import Rectangle
        if self.rect and self.rect in self.ax.patches:
            self.rect.remove()
        self.rect = self.ax.add_patch(Rectangle(
            (x0, y0), x1 - x0, y1 - y0,
            linewidth=1.5, edgecolor="#ff4444", facecolor="#ff4444",
            alpha=0.15, zorder=5, linestyle="--"
        ))
        self.canvas.draw_idle()

    def _on_release(self, event):
        if not self.selecting or self.start_xy is None:
            return
        self.selecting = False

        if event.inaxes != self.ax:
            self._clear_rect()
            return

        # Determine selection box
        x0 = min(self.start_xy[0], event.xdata)
        x1 = max(self.start_xy[0], event.xdata)
        y0 = min(self.start_xy[1], event.ydata)
        y1 = max(self.start_xy[1], event.ydata)

        # Ignore tiny drags (less than a click)
        if abs(x1 - x0) < 1e-10 and abs(y1 - y0) < 1e-10:
            self._clear_rect()
            return

        # Find points inside the rectangle
        self._clear_highlights()
        self.selected_indices.clear()

        x_data = self.plot_df[self.x_col].values.astype(float)
        for yc in self.y_cols:
            y_data = self.plot_df[yc].values.astype(float)
            for i in range(len(x_data)):
                if x0 <= x_data[i] <= x1 and y0 <= y_data[i] <= y1:
                    self.selected_indices.add(i)

        # Highlight selected points in red
        if self.selected_indices:
            idx_list = sorted(self.selected_indices)
            for yc in self.y_cols:
                xs = x_data[idx_list]
                ys = self.plot_df[yc].values.astype(float)[idx_list]
                h, = self.ax.plot(xs, ys, "x", color="#ff0000", markersize=8,
                                  markeredgewidth=2, zorder=15)
                self.highlight_artists.append(h)

        self.canvas.draw_idle()

    def _on_key(self, event):
        if event.key == "delete" and self.selected_indices:
            # Get the original df indices that map to these plot_df positions
            original_indices = self.plot_df.index[sorted(self.selected_indices)].tolist()
            self.on_remove(original_indices)
            self.selected_indices.clear()
            self._clear_highlights()
            self._clear_rect()

    def _clear_rect(self):
        if self.rect:
            try:
                self.rect.remove()
            except ValueError:
                pass
            self.rect = None
        self.canvas.draw_idle()

    def _clear_highlights(self):
        for h in self.highlight_artists:
            try:
                h.remove()
            except ValueError:
                pass
        self.highlight_artists.clear()

    def disconnect(self):
        self.canvas.mpl_disconnect(self._cid_press)
        self.canvas.mpl_disconnect(self._cid_motion)
        self.canvas.mpl_disconnect(self._cid_release)
        self.canvas.mpl_disconnect(self._cid_key)
        self._clear_rect()
        self._clear_highlights()

# ============================================================
#  DATA CURSOR
# ============================================================
class DataCursor:
    """Click to place data cursors on lines. Drag to move. DEL to remove."""

    def __init__(self, ax, lines, colors, canvas, zoom_handlers=None):
        self.ax = ax
        self.lines = lines
        self.colors = colors
        self.canvas = canvas
        self.zoom_handlers = zoom_handlers or []
        self.cursors = []
        self.selected = None
        self.dragging = False
        self._press_event = None
        self._cid_press = canvas.mpl_connect("button_press_event", self._on_press)
        self._cid_release = canvas.mpl_connect("button_release_event", self._on_release)
        self._cid_motion = canvas.mpl_connect("motion_notify_event", self._on_motion)
        self._cid_key = canvas.mpl_connect("key_press_event", self._on_key)

    def _get_line_data(self, line_idx):
        line = self.lines[line_idx]
        return np.array(line.get_xdata(), dtype=float), np.array(line.get_ydata(), dtype=float)

    def _find_nearest_on_line(self, line_idx, mx):
        xd, yd = self._get_line_data(line_idx)
        if len(xd) == 0:
            return None
        return int(np.abs(xd - mx).argmin())

    def _find_closest_line(self, event):
        """Find which line the click is closest to (in display pixels). Uses multi-point sampling."""
        best_line = None
        best_dist = 50  # wider threshold for tight plots
        for li, line in enumerate(self.lines):
            xd, yd = self._get_line_data(li)
            if len(xd) == 0:
                continue
            # Check nearest X point
            idx = int(np.abs(xd - event.xdata).argmin())
            # Also check a few neighbors for better Y match
            for offset in range(-3, 4):
                check_idx = max(0, min(len(xd) - 1, idx + offset))
                x, y = xd[check_idx], yd[check_idx]
                disp = self.ax.transData.transform((x, y))
                dist = np.hypot(disp[0] - event.x, disp[1] - event.y)
                if dist < best_dist:
                    best_dist = dist
                    best_line = li
        return best_line

    def _on_press(self, event):
        if event.inaxes != self.ax or event.button != 1:
            return
        self._press_event = event

        # Check if clicking near an existing cursor → select & drag it
        for i, cur in enumerate(self.cursors):
            xd, yd = self._get_line_data(cur["line_idx"])
            xi, yi = xd[cur["data_idx"]], yd[cur["data_idx"]]
            disp = self.ax.transData.transform((xi, yi))
            if np.hypot(disp[0] - event.x, disp[1] - event.y) < 25:
                self.selected = i
                self.dragging = True
                self._highlight_selected()
                return

    def _on_release(self, event):
        if self.dragging:
            self.dragging = False
            return

        if event.inaxes != self.ax or event.button != 1:
            return

        # Check if zoom handler was panning — if so, skip cursor placement
        for zh in self.zoom_handlers:
            if zh.was_dragged:
                return

        # No drag happened → place a new cursor on closest line
        if self._press_event is None:
            return

        line_idx = self._find_closest_line(event)
        if line_idx is None:
            return
        data_idx = self._find_nearest_on_line(line_idx, event.xdata)
        if data_idx is None:
            return

        xd, yd = self._get_line_data(line_idx)
        x, y = xd[data_idx], yd[data_idx]
        line_color = self.colors[line_idx] if line_idx < len(self.colors) else "#ffdd57"

        marker, = self.ax.plot(x, y, "s", color=line_color, markersize=8,
                               markeredgecolor="white", markeredgewidth=1.5, zorder=10)

        label = self.lines[line_idx].get_label()
        ann = self.ax.annotate(
            f"{label}\nX: {x:.4g}\nY: {y:.4g}",
            xy=(x, y), xytext=self._smart_offset(x, y), textcoords="offset points",
            fontsize=8, fontfamily="monospace",
            bbox=dict(boxstyle="round,pad=0.4", facecolor=T["cursor_bg"], edgecolor=line_color, alpha=0.92),
            color=T["cursor_text"], arrowprops=dict(arrowstyle="-|>", color=line_color, lw=1),
            zorder=11
        )
        self.cursors.append({"marker": marker, "annotation": ann,
                             "line_idx": line_idx, "data_idx": data_idx})
        self.selected = len(self.cursors) - 1
        self._highlight_selected()
        self.canvas.draw_idle()
        self._press_event = None

    def _smart_offset(self, x, y):
        """Flip tooltip direction based on anchor position within axes."""
        try:
            x_lo, x_hi = self.ax.get_xlim()
            y_lo, y_hi = self.ax.get_ylim()
            fx = (x - x_lo) / (x_hi - x_lo) if x_hi != x_lo else 0.5
            fy = (y - y_lo) / (y_hi - y_lo) if y_hi != y_lo else 0.5
        except Exception:
            return (15, 15)
        dx = 15 if fx <= 0.75 else -90
        dy = 15 if fy <= 0.80 else -45
        if fy < 0.10 and dy > 0:
            dy = 20
        return (dx, dy)

    def _on_motion(self, event):
        if not self.dragging or self.selected is None or event.inaxes != self.ax:
            return
        cur = self.cursors[self.selected]
        data_idx = self._find_nearest_on_line(cur["line_idx"], event.xdata)
        if data_idx is None:
            return
        xd, yd = self._get_line_data(cur["line_idx"])
        x, y = xd[data_idx], yd[data_idx]
        cur["data_idx"] = data_idx
        cur["marker"].set_data([x], [y])
        cur["annotation"].xy = (x, y)
        cur["annotation"].set_position(self._smart_offset(x, y))
        label = self.lines[cur["line_idx"]].get_label()
        cur["annotation"].set_text(f"{label}\nX: {x:.4g}\nY: {y:.4g}")
        self.canvas.draw_idle()

    def _on_key(self, event):
        if event.key == "delete" and self.selected is not None:
            cur = self.cursors.pop(self.selected)
            cur["marker"].remove()
            cur["annotation"].remove()
            self.selected = None
            self.canvas.draw_idle()

    def _highlight_selected(self):
        for i, cur in enumerate(self.cursors):
            li = cur["line_idx"]
            line_color = self.colors[li] if li < len(self.colors) else "#fff"
            if i == self.selected:
                cur["marker"].set_markeredgecolor("#ffffff")
                cur["marker"].set_markersize(10)
                cur["annotation"].get_bbox_patch().set_edgecolor("#ffffff")
            else:
                cur["marker"].set_markeredgecolor(line_color)
                cur["marker"].set_markersize(8)
                cur["annotation"].get_bbox_patch().set_edgecolor(line_color)
        self.canvas.draw_idle()

    def clear_all(self):
        for cur in self.cursors:
            cur["marker"].remove()
            cur["annotation"].remove()
        self.cursors.clear()
        self.selected = None

# ============================================================
#  MAIN APPLICATION
# ============================================================
class TelemetryPlotter(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PFA Telemetry Plotter")
        self.geometry("1400x850")
        self.configure(bg=T["bg"])
        self.minsize(1100, 650)

        self.df = None
        self.df_original = None       # untouched copy of loaded data
        self.columns = []
        self.data_cursors = []
        self.zoom_handlers = []
        self.junk_selector = None
        self.removed_indices = set()  # indices removed from df_original
        self.removed_history = []     # list of sets for undo
        self.anim = None
        self.anim_running = False

        # Style
        style = ttk.Style(self)
        style.theme_use("clam")
        self._apply_styles()
        self.option_add("*TCombobox*Listbox.font", ("Consolas", 9))

        # App icon
        try:
            self._app_icon = create_app_icon(self, 64)
            self.iconphoto(True, self._app_icon)
        except Exception:
            self._app_icon = None

        self._build_ui()

    def _build_ui(self):
        self.theme_name = "dark"
        self._theme_widgets = []  # (widget, {config_key: theme_key, ...})

        # Top bar
        self._topbar = tk.Frame(self, bg=T["topbar"], height=50)
        self._topbar.pack(fill="x", side="top")
        self._topbar.pack_propagate(False)
        self._title_lbl = tk.Label(self._topbar, text="◈  PFA TELEMETRY PLOTTER", font=("Consolas", 14, "bold"),
                 bg=T["topbar"], fg=T["title_fg"])
        self._title_lbl.pack(side="left", padx=15, pady=10)
        self._sub_lbl = tk.Label(self._topbar, text="Post Flight Analysis Tool", font=("Consolas", 9),
                 bg=T["topbar"], fg=T["muted"])
        self._sub_lbl.pack(side="left", pady=10)

        self._credit_label = tk.Label(self._topbar, text="", font=("Consolas", 9, "italic"),
                                       bg=T["topbar"], fg=T["credit_fg"])
        self._credit_label.pack(side="left", padx=(12, 0), pady=10)
        self._credit_text = "Developed By Chiranjib | Co-Developed by Biswajit"
        self._credit_idx = 0
        self.after(600, self._typewriter_tick)

        btn_frame = tk.Frame(self._topbar, bg=T["topbar"])
        btn_frame.pack(side="right", padx=15)
        self._btn_frame = btn_frame
        self._theme_btn = tk.Button(btn_frame, text="☀ Light", command=self._toggle_theme,
                                     bg="#333", fg="#eee", font=("Consolas", 8, "bold"),
                                     relief="flat", padx=6, pady=2, cursor="hand2")
        self._theme_btn.pack(side="left", padx=3)
        ttk.Button(btn_frame, text="📂 Load", command=self.load_file).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="📊 Plot", command=self.plot_data, style="Go.TButton").pack(side="left", padx=3)
        ttk.Button(btn_frame, text="▶ Animate", command=self.toggle_animation).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="💾 PNG", command=self.export_png).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="🗑 Clear", command=self.clear_plot, style="Accent.TButton").pack(side="left", padx=3)

        # Main split
        main = tk.PanedWindow(self, orient="horizontal", bg=T["bg"], sashwidth=3, sashrelief="flat")
        main.pack(fill="both", expand=True)

        left_container = tk.Frame(main, bg=T["panel"], width=310)
        left_container.pack_propagate(False)

        canvas_scroll = tk.Canvas(left_container, bg=T["panel"], highlightthickness=0, width=295)
        scrollbar = ttk.Scrollbar(left_container, orient="vertical", command=canvas_scroll.yview)
        self.left_panel = tk.Frame(canvas_scroll, bg=T["panel"])

        self.left_panel.bind("<Configure>", lambda e: canvas_scroll.configure(scrollregion=canvas_scroll.bbox("all")))
        canvas_scroll.create_window((0, 0), window=self.left_panel, anchor="nw")
        canvas_scroll.configure(yscrollcommand=scrollbar.set)

        canvas_scroll.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mouse wheel scrolling
        def _on_mousewheel(event):
            canvas_scroll.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas_scroll.bind_all("<MouseWheel>", _on_mousewheel)

        main.add(left_container, minsize=310)

        left = self.left_panel

        # File info
        self.file_label = tk.Label(left, text="No file loaded", bg=T["panel"], fg=T["muted"],
                                    font=("Consolas", 9), wraplength=280)
        self.file_label.pack(pady=(10, 5), padx=10, anchor="w")

        mode_frame = ttk.LabelFrame(left, text="PLOT MODE", padding=8)
        mode_frame.pack(fill="x", padx=10, pady=5)

        self.mode_var = tk.StringVar(value="single")
        modes = [("Single Plot", "single"), ("Multiplot", "multi"), ("Subplots", "subplot"), ("3D Plot", "3d")]
        for txt, val in modes:
            tk.Radiobutton(mode_frame, text=txt, variable=self.mode_var, value=val,
                           bg=T["panel"], fg=T["text"], selectcolor=T["accent"],
                           activebackground=T["panel"], activeforeground=T["text"],
                           font=("Consolas", 9), command=self._on_mode_change).pack(anchor="w")

        type_frame = ttk.LabelFrame(left, text="PLOT TYPE", padding=8)
        type_frame.pack(fill="x", padx=10, pady=5)
        self.plot_type_var = tk.StringVar(value="line")
        for txt, val in [("Line Plot", "line"), ("Scatter Plot", "scatter")]:
            tk.Radiobutton(type_frame, text=txt, variable=self.plot_type_var, value=val,
                           bg=T["panel"], fg=T["text"], selectcolor=T["accent"],
                           activebackground=T["panel"], activeforeground=T["text"],
                           font=("Consolas", 9)).pack(side="left", padx=8)

        # Signal Selection — placed right after Plot Type
        self.signal_frame = ttk.LabelFrame(left, text="SIGNAL SELECTION", padding=8)
        # Don't pack here — _on_mode_change controls visibility

        tk.Label(self.signal_frame, text="X Axis:", bg=T["panel"], fg=T["text"],
                 font=("Consolas", 9)).grid(row=0, column=0, sticky="w", pady=2)
        self.x_combo = ttk.Combobox(self.signal_frame, state="readonly", width=22)
        self.x_combo.grid(row=0, column=1, columnspan=2, sticky="w", pady=2, padx=4)

        self.y_combos = []
        self.y_colors = []
        self.y_color_btns = []
        self.y_remove_btns = []
        self.y_rows = []
        for i in range(3):
            row = tk.Frame(self.signal_frame, bg=T["panel"])
            lbl = tk.Label(row, text=f"Y{i+1 if i > 0 else ''}:", bg=T["panel"], fg=T["text"],
                           font=("Consolas", 9), width=6, anchor="w")
            lbl.pack(side="left")
            cb = ttk.Combobox(row, state="readonly", width=17)
            cb.pack(side="left", padx=4)
            color = COLORS_DEFAULT[i]
            self.y_colors.append(tk.StringVar(value=color))
            btn_c = tk.Button(row, text="  ", bg=color, width=2, relief="solid", bd=1,
                              command=lambda idx=i: self._pick_color(idx))
            btn_c.pack(side="left", padx=2)
            btn_rm = tk.Button(row, text="✕", fg="#ef4444", bg=T["panel"], font=("Consolas", 8, "bold"),
                               relief="flat", width=2, cursor="hand2",
                               command=lambda idx=i: self._remove_y_signal(idx))
            btn_rm.pack(side="left", padx=1)
            self.y_combos.append(cb)
            self.y_color_btns.append(btn_c)
            self.y_remove_btns.append(btn_rm)
            self.y_rows.append(row)
            if i == 0:
                row.grid(row=1, column=0, columnspan=3, sticky="w", pady=2)

        self._title_frame = ttk.LabelFrame(left, text="PLOT TITLE", padding=8)
        self._title_frame.pack(fill="x", padx=10, pady=5)
        self.title_var = tk.StringVar(value="Telemetry Plot")
        ttk.Entry(self._title_frame, textvariable=self.title_var, width=35).pack(fill="x")

        self.subplot_frame = ttk.LabelFrame(left, text="SUBPLOT CONFIG", padding=8)

        self.sp_count_var = tk.IntVar(value=2)
        sc_row = tk.Frame(self.subplot_frame, bg=T["panel"])
        sc_row.pack(fill="x", pady=(0, 8))
        tk.Label(sc_row, text="Count:", bg=T["panel"], fg=T["text"], font=("Consolas", 9)).pack(side="left")
        sp_spin = tk.Spinbox(sc_row, from_=2, to=10, width=4, textvariable=self.sp_count_var,
                              command=self._rebuild_subplot_cfg,
                              bg=T["entry"], fg=T["text"], font=("Consolas", 10, "bold"),
                              buttonbackground=T["button"], selectbackground=T["accent"],
                              relief="flat", justify="center")
        sp_spin.pack(side="left", padx=8)
        tk.Label(sc_row, text="(2-10)", bg=T["panel"], fg=T["muted"], font=("Consolas", 8)).pack(side="left")

        # Default offset (apply to all subplots)
        def_row = tk.Frame(self.subplot_frame, bg=T["panel"])
        def_row.pack(fill="x", pady=(0, 6))
        self.sp_default_offset = tk.BooleanVar(value=False)
        tk.Checkbutton(def_row, text="Apply default offset to all",
                       variable=self.sp_default_offset,
                       bg=T["panel"], fg=T["text"], selectcolor=T["accent"],
                       activebackground=T["panel"], font=("Consolas", 8),
                       command=self._on_default_offset_toggle).pack(anchor="w")
        self.sp_default_frame = tk.Frame(self.subplot_frame, bg=T["panel"])
        # Don't pack yet — only visible when checkbox is on

        self.sp_default_vars = {}
        for r, (lbl, key) in enumerate([("X Min:", "xmin"), ("X Max:", "xmax"),
                                          ("Y Min:", "ymin"), ("Y Max:", "ymax")]):
            tk.Label(self.sp_default_frame, text=lbl, bg=T["panel"], fg=T["text"],
                     font=("Consolas", 8)).grid(row=r // 2, column=(r % 2) * 2, sticky="w", padx=(0, 4))
            sv = tk.StringVar(value="")
            self.sp_default_vars[key] = sv
            ttk.Entry(self.sp_default_frame, textvariable=sv, width=7).grid(
                row=r // 2, column=(r % 2) * 2 + 1, padx=(0, 8), pady=1, sticky="w")
        tk.Label(self.sp_default_frame, text="(leave blank for auto)", bg=T["panel"],
                 fg=T["muted"], font=("Consolas", 7)).grid(row=2, column=0, columnspan=4, sticky="w")

        self.sp_configs = []  # list of dicts with widgets
        self.sp_cfg_frame = tk.Frame(self.subplot_frame, bg=T["panel"])
        self.sp_cfg_frame.pack(fill="x")
        self._rebuild_subplot_cfg()

        # 3D Plot config
        self.frame_3d = ttk.LabelFrame(left, text="3D PLOT CONFIG", padding=8)

        tk.Label(self.frame_3d, text="X Axis:", bg=T["panel"], fg=T["text"], font=("Consolas", 9)).grid(row=0, column=0, sticky="w")
        self.x3d_combo = ttk.Combobox(self.frame_3d, state="readonly", width=15)
        self.x3d_combo.grid(row=0, column=1, padx=4, pady=2)
        tk.Button(self.frame_3d, text="✕", fg="#ef4444", bg=T["panel"], font=("Consolas", 8, "bold"),
                  relief="flat", width=2, cursor="hand2",
                  command=lambda: self.x3d_combo.set("")).grid(row=0, column=2)

        tk.Label(self.frame_3d, text="Y Axis:", bg=T["panel"], fg=T["text"], font=("Consolas", 9)).grid(row=1, column=0, sticky="w")
        self.y3d_combo = ttk.Combobox(self.frame_3d, state="readonly", width=15)
        self.y3d_combo.grid(row=1, column=1, padx=4, pady=2)
        tk.Button(self.frame_3d, text="✕", fg="#ef4444", bg=T["panel"], font=("Consolas", 8, "bold"),
                  relief="flat", width=2, cursor="hand2",
                  command=lambda: self.y3d_combo.set("")).grid(row=1, column=2)

        tk.Label(self.frame_3d, text="Z Axis:", bg=T["panel"], fg=T["text"], font=("Consolas", 9)).grid(row=2, column=0, sticky="w")
        self.z3d_combo = ttk.Combobox(self.frame_3d, state="readonly", width=15)
        self.z3d_combo.grid(row=2, column=1, padx=4, pady=2)
        tk.Button(self.frame_3d, text="✕", fg="#ef4444", bg=T["panel"], font=("Consolas", 8, "bold"),
                  relief="flat", width=2, cursor="hand2",
                  command=lambda: self.z3d_combo.set("")).grid(row=2, column=2)

        tk.Label(self.frame_3d, text="Type:", bg=T["panel"], fg=T["text"], font=("Consolas", 9)).grid(row=3, column=0, sticky="w", pady=(8, 0))
        self.plot3d_type = tk.StringVar(value="trajectory")
        types_3d = [
            ("Trajectory Line", "trajectory"),
            ("Scatter + Time Color", "scatter_time"),
            ("Ribbon + Color", "ribbon"),
            ("Attitude Path", "attitude"),
        ]
        for i, (txt, val) in enumerate(types_3d):
            tk.Radiobutton(self.frame_3d, text=txt, variable=self.plot3d_type, value=val,
                           bg=T["panel"], fg=T["text"], selectcolor=T["accent"],
                           activebackground=T["panel"], font=("Consolas", 8)).grid(
                           row=4 + i, column=0, columnspan=2, sticky="w")

        tk.Label(self.frame_3d, text="Color By:", bg=T["panel"], fg=T["text"], font=("Consolas", 9)).grid(row=8, column=0, sticky="w", pady=(6, 0))
        self.color3d_combo = ttk.Combobox(self.frame_3d, state="readonly", width=18)
        self.color3d_combo.grid(row=8, column=1, padx=4, pady=(6, 2))
        tk.Label(self.frame_3d, text="(for scatter colormap)", bg=T["panel"], fg=T["muted"], font=("Consolas", 7)).grid(row=9, column=0, columnspan=2, sticky="w")

        tk.Label(self.frame_3d, text="X Label:", bg=T["panel"], fg=T["text"], font=("Consolas", 8)).grid(row=10, column=0, sticky="w", pady=(6, 0))
        self.x3d_label = tk.StringVar(value="X")
        ttk.Entry(self.frame_3d, textvariable=self.x3d_label, width=14).grid(row=10, column=1, padx=4, pady=(6, 1))

        tk.Label(self.frame_3d, text="Y Label:", bg=T["panel"], fg=T["text"], font=("Consolas", 8)).grid(row=11, column=0, sticky="w")
        self.y3d_label = tk.StringVar(value="Y")
        ttk.Entry(self.frame_3d, textvariable=self.y3d_label, width=14).grid(row=11, column=1, padx=4, pady=1)

        tk.Label(self.frame_3d, text="Z Label:", bg=T["panel"], fg=T["text"], font=("Consolas", 8)).grid(row=12, column=0, sticky="w")
        self.z3d_label = tk.StringVar(value="Z")
        ttk.Entry(self.frame_3d, textvariable=self.z3d_label, width=14).grid(row=12, column=1, padx=4, pady=1)

        self.line3d_color = tk.StringVar(value=COLORS_DEFAULT[0])
        tk.Label(self.frame_3d, text="Line Color:", bg=T["panel"], fg=T["text"], font=("Consolas", 8)).grid(row=13, column=0, sticky="w", pady=(4, 0))
        self.color3d_btn = tk.Button(self.frame_3d, text="  ", bg=self.line3d_color.get(), width=3,
                                      relief="solid", bd=1,
                                      command=lambda: self._pick_3d_color())
        self.color3d_btn.grid(row=13, column=1, sticky="w", padx=4, pady=(4, 0))

        self.label_frame = ttk.LabelFrame(left, text="AXIS LABELS", padding=8)
        # Don't pack here — _on_mode_change controls visibility

        tk.Label(self.label_frame, text="X Label:", bg=T["panel"], fg=T["text"], font=("Consolas", 9)).grid(row=0, column=0, sticky="w")
        self.xlabel_var = tk.StringVar(value="X")
        ttk.Entry(self.label_frame, textvariable=self.xlabel_var, width=20).grid(row=0, column=1, padx=4, pady=2)

        tk.Label(self.label_frame, text="Y Label:", bg=T["panel"], fg=T["text"], font=("Consolas", 9)).grid(row=1, column=0, sticky="w")
        self.ylabel_var = tk.StringVar(value="Y")
        ttk.Entry(self.label_frame, textvariable=self.ylabel_var, width=20).grid(row=1, column=1, padx=4, pady=2)

        tk.Label(self.label_frame, text="Font Size:", bg=T["panel"], fg=T["text"], font=("Consolas", 9)).grid(row=2, column=0, sticky="w")
        self.fontsize_var = tk.IntVar(value=11)
        ttk.Entry(self.label_frame, textvariable=self.fontsize_var, width=6).grid(row=2, column=1, sticky="w", padx=4, pady=2)

        self.range_frame = ttk.LabelFrame(left, text="AXIS RANGE (OFFSET)", padding=8)
        # Don't pack here — _on_mode_change controls visibility

        for i, (lbl, var_name) in enumerate([("X Min:", "xmin"), ("X Max:", "xmax"), ("Y Min:", "ymin"), ("Y Max:", "ymax")]):
            tk.Label(self.range_frame, text=lbl, bg=T["panel"], fg=T["text"], font=("Consolas", 9)).grid(row=i, column=0, sticky="w")
            sv = tk.StringVar(value="")
            setattr(self, f"{var_name}_var", sv)
            ttk.Entry(self.range_frame, textvariable=sv, width=12).grid(row=i, column=1, padx=4, pady=2, sticky="w")

        tk.Label(self.range_frame, text="(leave blank for auto)", bg=T["panel"], fg=T["muted"],
                 font=("Consolas", 8)).grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 0))

        self._leg_frame = ttk.LabelFrame(left, text="LEGEND (draggable)", padding=8)
        self._leg_frame.pack(fill="x", padx=10, pady=5)

        self.legend_on = tk.BooleanVar(value=True)  # always on
        tk.Label(self._leg_frame, text="Rename signals below after plotting:",
                 bg=T["panel"], fg=T["muted"], font=("Consolas", 8)).pack(anchor="w")

        self.legend_entries = []
        self.legend_entry_frame = tk.Frame(self._leg_frame, bg=T["panel"])
        self.legend_entry_frame.pack(fill="x", pady=(4, 0))

        # Animation speed
        anim_frame = ttk.LabelFrame(left, text="ANIMATION", padding=8)
        anim_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(anim_frame, text="Speed:", bg=T["panel"], fg=T["text"], font=("Consolas", 9)).pack(side="left")
        self.anim_speed_var = tk.IntVar(value=3)
        anim_scale = tk.Scale(anim_frame, from_=1, to=10, orient="horizontal",
                               variable=self.anim_speed_var, showvalue=True, length=140,
                               bg=T["panel"], fg=T["text"], troughcolor=T["entry"],
                               highlightthickness=0, font=("Consolas", 8))
        anim_scale.pack(side="left", padx=4)
        tk.Label(anim_frame, text="1=Slow 10=Fast", bg=T["panel"], fg=T["muted"],
                 font=("Consolas", 7)).pack(anchor="w")

        zoom_frame = ttk.LabelFrame(left, text="ZOOM & PAN", padding=8)
        zoom_frame.pack(fill="x", padx=10, pady=5)

        self.zoom_enabled = tk.BooleanVar(value=True)
        tk.Checkbutton(zoom_frame, text="Enable Zoom & Pan", variable=self.zoom_enabled,
                       bg=T["panel"], fg=T["text"], selectcolor=T["accent"],
                       activebackground=T["panel"], font=("Consolas", 9),
                       command=self._on_zoom_toggle).pack(anchor="w")
        tk.Label(zoom_frame, text="Scroll=Zoom  Drag=Pan  MidDbl=Reset",
                 bg=T["panel"], fg="#666", font=("Consolas", 7)).pack(anchor="w", pady=(2, 0))

        junk_frame = ttk.LabelFrame(left, text="JUNK REMOVER (Scatter)", padding=8)
        junk_frame.pack(fill="x", padx=10, pady=5)

        self.junk_mode = tk.BooleanVar(value=False)
        tk.Checkbutton(junk_frame, text="Enable Junk Selection", variable=self.junk_mode,
                       bg=T["panel"], fg=T["text"], selectcolor=T["accent"],
                       activebackground=T["panel"], font=("Consolas", 9),
                       command=self._on_junk_toggle).pack(anchor="w")

        junk_btn_row = tk.Frame(junk_frame, bg=T["panel"])
        junk_btn_row.pack(fill="x", pady=(4, 0))
        ttk.Button(junk_btn_row, text="Undo Last", command=self._junk_undo).pack(side="left", padx=2)
        ttk.Button(junk_btn_row, text="Reset All", command=self._junk_reset, style="Accent.TButton").pack(side="left", padx=2)

        self.junk_count_label = tk.Label(junk_frame, text="Removed: 0 points", bg=T["panel"],
                                          fg=T["muted"], font=("Consolas", 8))
        self.junk_count_label.pack(anchor="w", pady=(4, 0))

        tk.Label(junk_frame, text="Drag=Select  DEL=Remove  Scatter only",
                 bg=T["panel"], fg="#666", font=("Consolas", 7)).pack(anchor="w", pady=(2, 0))

        right = tk.Frame(main, bg=T["bg"])
        main.add(right, minsize=600)

        self.fig = Figure(facecolor=T["plot_face"], edgecolor=T["spine"])
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # Status bar
        self._status_bar = tk.Frame(right, bg=T["topbar"], height=24)
        self._status_bar.pack(fill="x", side="bottom")
        self._status_bar.pack_propagate(False)
        self.status_label = tk.Label(self._status_bar, text="Ready", bg=T["topbar"], fg=T["muted"],
                                      font=("Consolas", 8))
        self.status_label.pack(side="left", padx=10)

        self._on_mode_change()

    def _typewriter_tick(self):
        if self._credit_idx <= len(self._credit_text):
            self._credit_label.config(text=self._credit_text[:self._credit_idx] + "▌")
            self._credit_idx += 1
            self.after(65, self._typewriter_tick)
        else:
            self._credit_label.config(text=self._credit_text)

    def _toggle_theme(self):
        global T
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        T = THEMES[self.theme_name]
        is_light = self.theme_name == "light"
        self._theme_btn.config(
            text="🌙 Dark" if is_light else "☀ Light",
            bg="#ddd" if is_light else "#333",
            fg="#333" if is_light else "#eee"
        )
        # Top bar + status
        for w in [self._topbar, self._btn_frame]:
            w.config(bg=T["topbar"])
        self._title_lbl.config(bg=T["topbar"], fg=T["title_fg"])
        self._sub_lbl.config(bg=T["topbar"], fg=T["muted"])
        self._credit_label.config(bg=T["topbar"], fg=T["credit_fg"])
        self._status_bar.config(bg=T["topbar"])
        self.status_label.config(bg=T["topbar"], fg=T["muted"])
        self.configure(bg=T["bg"])
        # Sidebar widgets — walk all children recursively
        self._apply_theme_recursive(self)
        # Styles
        self._apply_styles()
        # Figure
        self.fig.set_facecolor(T["plot_face"])
        self._replot_if_ready()
        self.canvas.draw()
        self.status_label.config(text=f"Switched to {self.theme_name} theme")

    def _apply_styles(self):
        style = ttk.Style(self)
        style.configure("TFrame", background=T["panel"])
        style.configure("TLabel", background=T["panel"], foreground=T["text"], font=("Consolas", 10))
        style.configure("TLabelframe", background=T["panel"], foreground=T["text"], font=("Consolas", 10, "bold"))
        style.configure("TLabelframe.Label", background=T["panel"], foreground=T["title_fg"])
        style.configure("TButton", background=T["button"], foreground=T["text"], font=("Consolas", 9, "bold"), padding=4)
        style.map("TButton", background=[("active", T["accent"])])
        style.configure("TCombobox", fieldbackground=T["entry"], background=T["button"],
                         foreground=T["text"], font=("Consolas", 9),
                         selectbackground=T["accent"], selectforeground=T["text"])
        style.map("TCombobox",
                  fieldbackground=[("readonly", T["entry"]), ("disabled", T["bg"])],
                  foreground=[("readonly", T["text"])],
                  selectbackground=[("readonly", T["accent"])],
                  selectforeground=[("readonly", T["text"])])
        style.configure("TEntry", fieldbackground=T["entry"], foreground=T["text"], font=("Consolas", 9))
        style.configure("Accent.TButton", background="#e74c3c", foreground="white")
        style.configure("Go.TButton", background="#27ae60", foreground="white")
        self.option_add("*TCombobox*Listbox.background", T["combo_list_bg"])
        self.option_add("*TCombobox*Listbox.foreground", T["combo_list_fg"])
        self.option_add("*TCombobox*Listbox.selectBackground", T["accent"])
        self.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")

    def _apply_theme_recursive(self, widget):
        """Walk all widgets and update bg/fg for tk widgets (not ttk)."""
        try:
            wclass = widget.winfo_class()
            if wclass in ("Frame", "Canvas") and widget not in (self._topbar, self._btn_frame, self._status_bar):
                widget.config(bg=T["panel"])
            elif wclass == "Label" and widget not in (self._title_lbl, self._sub_lbl, self._credit_label, self.status_label):
                try:
                    widget.config(bg=T["panel"], fg=T["text"])
                except Exception:
                    pass
            elif wclass == "Radiobutton":
                widget.config(bg=T["panel"], fg=T["text"], selectcolor=T["accent"],
                              activebackground=T["panel"], activeforeground=T["text"])
            elif wclass == "Checkbutton":
                widget.config(bg=T["panel"], fg=T["text"], selectcolor=T["accent"],
                              activebackground=T["panel"])
            elif wclass == "Spinbox":
                widget.config(bg=T["entry"], fg=T["text"], buttonbackground=T["button"])
            elif wclass == "Button" and widget != self._theme_btn:
                # Only update generic tk.Buttons (color pickers etc), not theme button
                try:
                    cur_bg = widget.cget("bg")
                    # Skip color picker buttons (they have signal colors)
                    if cur_bg not in [c for c in COLORS_DEFAULT]:
                        widget.config(bg=T["button"], fg=T["text"])
                except Exception:
                    pass
        except Exception:
            pass
        for child in widget.winfo_children():
            self._apply_theme_recursive(child)

    def _rebuild_subplot_cfg(self):
        for w in self.sp_cfg_frame.winfo_children():
            w.destroy()
        self.sp_configs.clear()
        count = self.sp_count_var.get()
        for i in range(count):
            f = ttk.LabelFrame(self.sp_cfg_frame, text=f"  Subplot {i+1}", padding=6)
            f.pack(fill="x", pady=3)
            cfg = {}

            tk.Label(f, text="X:", bg=T["panel"], fg=T["text"], font=("Consolas", 9)).grid(row=0, column=0, sticky="w")
            cfg["x"] = ttk.Combobox(f, state="readonly", width=18)
            cfg["x"].grid(row=0, column=1, padx=4, pady=1)

            tk.Label(f, text="Y:", bg=T["panel"], fg=T["text"], font=("Consolas", 9)).grid(row=1, column=0, sticky="w")
            cfg["y"] = ttk.Combobox(f, state="readonly", width=18)
            cfg["y"].grid(row=1, column=1, padx=4, pady=1)

            cfg["color_var"] = tk.StringVar(value=COLORS_DEFAULT[i % len(COLORS_DEFAULT)])
            cfg["color_btn"] = tk.Button(f, text="  ", bg=cfg["color_var"].get(), width=2,
                                          relief="solid", bd=1,
                                          command=lambda idx=i: self._pick_sp_color(idx))
            cfg["color_btn"].grid(row=1, column=2, padx=2)

            tk.Label(f, text="X Label:", bg=T["panel"], fg=T["text"], font=("Consolas", 8)).grid(row=2, column=0, sticky="w")
            cfg["xlabel"] = tk.StringVar(value="X")
            ttk.Entry(f, textvariable=cfg["xlabel"], width=14).grid(row=2, column=1, padx=4, pady=1, sticky="w")

            tk.Label(f, text="Y Label:", bg=T["panel"], fg=T["text"], font=("Consolas", 8)).grid(row=3, column=0, sticky="w")
            cfg["ylabel"] = tk.StringVar(value="Y")
            ttk.Entry(f, textvariable=cfg["ylabel"], width=14).grid(row=3, column=1, padx=4, pady=1, sticky="w")

            # ranges
            for j, rng in enumerate(["xmin", "xmax", "ymin", "ymax"]):
                r = j // 2
                c = j % 2
                cfg[rng] = tk.StringVar(value="")
                tk.Label(f, text=rng.upper()+":", bg=T["panel"], fg=T["muted"], font=("Consolas", 7)).grid(row=4+r, column=c*2 if c == 0 else 1, sticky="w" if c == 0 else "e")
                ttk.Entry(f, textvariable=cfg[rng], width=7).grid(row=4+r, column=1 if c == 0 else 2, padx=2, pady=1, sticky="w")

            # Legend label
            tk.Label(f, text="Legend:", bg=T["panel"], fg=T["text"], font=("Consolas", 8)).grid(row=6, column=0, sticky="w")
            cfg["legend"] = tk.StringVar(value="")
            ttk.Entry(f, textvariable=cfg["legend"], width=14).grid(row=6, column=1, padx=4, pady=1, sticky="w")

            self.sp_configs.append(cfg)

        # Populate comboboxes if data is already loaded
        if self.columns:
            time_col = None
            for col in self.columns:
                if col.lower().strip().startswith("time") or col.lower().strip() == "t":
                    time_col = col
                    break
            default_x = time_col if time_col else self.columns[0]
            for cfg in self.sp_configs:
                cfg["x"]["values"] = self.columns
                cfg["y"]["values"] = self.columns
                cfg["x"].set(default_x)

    def _pick_sp_color(self, idx):
        c = colorchooser.askcolor(color=self.sp_configs[idx]["color_var"].get())[1]
        if c:
            self.sp_configs[idx]["color_var"].set(c)
            self.sp_configs[idx]["color_btn"].configure(bg=c)

    def _replot_if_ready(self):
        """Re-plot if data is loaded (used by checkbox callbacks)."""
        if self.df is not None and len(self.df) > 0:
            self.plot_data()

    def _on_default_offset_toggle(self):
        """Show/hide default offset input frame for subplots."""
        if self.sp_default_offset.get():
            self.sp_default_frame.pack(fill="x", pady=(0, 6), before=self.sp_cfg_frame)
        else:
            self.sp_default_frame.pack_forget()

    def _on_zoom_toggle(self):
        """Enable/disable zoom & pan. When disabled, reset to original/offset view."""
        enabled = self.zoom_enabled.get()
        for zh in self.zoom_handlers:
            zh.enabled = enabled
            if not enabled and zh.orig_xlim and zh.orig_ylim:
                # Reset to original view (or user-specified offset)
                zh.ax.set_xlim(zh.orig_xlim)
                zh.ax.set_ylim(zh.orig_ylim)
        if not enabled:
            self.canvas.draw_idle()
            self.status_label.config(text="Zoom & Pan disabled — view locked")
        else:
            self.status_label.config(text="Zoom & Pan enabled")

    def _on_junk_toggle(self):
        """Toggle junk selection mode. Only works in scatter mode."""
        if self.junk_mode.get():
            if self.plot_type_var.get() != "scatter":
                self.junk_mode.set(False)
                styled_warning(self, "Junk Remover", "Junk Remover only works in Scatter plot mode.\nSwitch to Scatter and try again!")
                return
            # Disable zoom/pan when junk mode is on (they share left-click drag)
            self.zoom_enabled.set(False)
            self._on_zoom_toggle()
            self.status_label.config(text="Junk Remover ON — drag to select, DEL to remove")
            # Re-plot to attach JunkSelector
            self._replot_if_ready()
        else:
            # Disconnect junk selector
            if self.junk_selector:
                self.junk_selector.disconnect()
                self.junk_selector = None
            self.status_label.config(text="Junk Remover OFF")
            self._replot_if_ready()

    def _junk_remove_points(self, original_indices):
        """Callback from JunkSelector — remove selected points from working df."""
        if not original_indices or self.df_original is None:
            return
        # Save current state for undo
        self.removed_history.append(set(original_indices))
        self.removed_indices.update(original_indices)
        # Rebuild working df
        self.df = self.df_original.drop(index=self.removed_indices, errors="ignore")
        # Update count
        total_removed = len(self.removed_indices)
        self.junk_count_label.config(text=f"Removed: {total_removed} points")
        self.status_label.config(text=f"Removed {len(original_indices)} points ({total_removed} total)")
        # Re-plot with cleaned data
        self._replot_if_ready()

    def _junk_undo(self):
        """Undo last junk removal."""
        if not self.removed_history or self.df_original is None:
            return
        last = self.removed_history.pop()
        self.removed_indices -= last
        self.df = self.df_original.drop(index=self.removed_indices, errors="ignore")
        total_removed = len(self.removed_indices)
        self.junk_count_label.config(text=f"Removed: {total_removed} points")
        self.status_label.config(text=f"Undo — restored {len(last)} points")
        self._replot_if_ready()

    def _junk_reset(self):
        """Reset all junk removals — restore original data."""
        if self.df_original is None:
            return
        self.removed_indices.clear()
        self.removed_history.clear()
        self.df = self.df_original.copy()
        self.junk_count_label.config(text="Removed: 0 points")
        self.status_label.config(text="Junk reset — all data restored")
        self._replot_if_ready()

    def _on_mode_change(self):
        mode = self.mode_var.get()
        for i, row in enumerate(self.y_rows):
            row.grid_forget()
        for w in self.legend_entry_frame.winfo_children():
            w.destroy()
        self.legend_entries.clear()
        # Hide all mode-specific frames
        self.signal_frame.pack_forget()
        self.subplot_frame.pack_forget()
        self.frame_3d.pack_forget()
        self.label_frame.pack_forget()
        self.range_frame.pack_forget()
        # Pack in correct order using before= to insert above legend
        if mode == "single":
            self.y_rows[0].grid(row=1, column=0, columnspan=3, sticky="w", pady=2)
            self.y_remove_btns[0].pack_forget()
            self.signal_frame.pack(fill="x", padx=10, pady=5, before=self._leg_frame)
            self.label_frame.pack(fill="x", padx=10, pady=5, before=self._leg_frame)
            self.range_frame.pack(fill="x", padx=10, pady=5, before=self._leg_frame)
        elif mode == "multi":
            for i in range(3):
                self.y_rows[i].grid(row=1 + i, column=0, columnspan=3, sticky="w", pady=2)
                self.y_remove_btns[i].pack(side="left", padx=1)
            self.signal_frame.pack(fill="x", padx=10, pady=5, before=self._leg_frame)
            self.label_frame.pack(fill="x", padx=10, pady=5, before=self._leg_frame)
            self.range_frame.pack(fill="x", padx=10, pady=5, before=self._leg_frame)
        elif mode == "subplot":
            self.subplot_frame.pack(fill="x", padx=10, pady=5, before=self._leg_frame)
        elif mode == "3d":
            self.frame_3d.pack(fill="x", padx=10, pady=5, before=self._leg_frame)

    def _pick_color(self, idx):
        c = colorchooser.askcolor(color=self.y_colors[idx].get())[1]
        if c:
            self.y_colors[idx].set(c)
            self.y_color_btns[idx].configure(bg=c)

    def _remove_y_signal(self, idx):
        """Clear a Y signal combobox selection."""
        if idx < len(self.y_combos):
            self.y_combos[idx].set("")

    def _pick_3d_color(self):
        c = colorchooser.askcolor(color=self.line3d_color.get())[1]
        if c:
            self.line3d_color.set(c)
            self.color3d_btn.configure(bg=c)

    def _parse_text_file(self, path):
        """Fast pandas parser with manual fallback for tricky formats."""
        import re
        from collections import Counter

        # Read first non-blank line for header
        with open(path, "r", errors="replace") as f:
            for raw_header in f:
                raw_header = raw_header.rstrip("\n\r\x00$")
                if raw_header.strip():
                    break
            else:
                raise ValueError("File is empty")

        # Strip comment prefix
        header_cleaned = re.sub(r'^[#/%]+\s*', '', raw_header).rstrip()

        # CSV detection
        if "," in header_cleaned and header_cleaned.count(",") >= 2:
            return pd.read_csv(path, sep=",", engine="python", skipinitialspace=True)

        # Parse headers — try tab-split first, fall back to any-whitespace
        headers_tab = [x.strip() for x in header_cleaned.split("\t") if x.strip()]
        headers_ws = header_cleaned.split()

        # ─── FAST PATH: pandas read_csv with sep=\s+ ───
        try:
            df_fast = pd.read_csv(path, sep=r'\s+', skiprows=1, header=None,
                                   engine="python", on_bad_lines="skip")
            ncols = df_fast.shape[1]

            # Pick header list that matches data column count
            if len(headers_ws) == ncols:
                headers = headers_ws
            elif len(headers_tab) == ncols:
                headers = headers_tab
            else:
                headers = headers_ws
                if len(headers) < ncols:
                    headers += [f"Col_{i}" for i in range(len(headers), ncols)]
                elif len(headers) > ncols:
                    headers = headers[:ncols]

            df_fast.columns = headers
            print(f"[PFA Parser] Fast: {len(df_fast)} rows × {ncols} cols")
            return df_fast

        except Exception as e:
            print(f"[PFA Parser] Fast path failed ({e}), using manual parser...")

        # ─── MANUAL FALLBACK ───
        DATA_DELIM = re.compile(r"[\t ]{2,}|\t")

        with open(path, "r", errors="replace") as f:
            raw_lines = f.readlines()

        if not raw_lines:
            raise ValueError("File is empty")

        # Clean all lines — strip newlines, carriage returns, trailing special chars
        raw_lines = [line.rstrip("\n\r\x00$") for line in raw_lines]

        # Skip leading blank lines
        start = 0
        while start < len(raw_lines) and raw_lines[start].strip() == "":
            start += 1
        if start >= len(raw_lines):
            raise ValueError("File contains no data")

        header_raw = raw_lines[start]

        # Strip comment prefixes (#, //, %) and trailing whitespace
        header_raw = re.sub(r'^[#/%]+\s*', '', header_raw).rstrip()

        if "," in header_raw and header_raw.count(",") >= 2:
            return pd.read_csv(path, sep=",", nrows=CHUNK_SIZE, engine="python",
                               skiprows=start, skipinitialspace=True)

        header_strategies = [
            lambda h: [x.strip() for x in h.split("\t") if x.strip()],
            lambda h: [x.strip() for x in DATA_DELIM.split(h.strip()) if x.strip()],
            lambda h: [x.strip() for x in re.split(r"[\t ]{3,}|\t", h.strip()) if x.strip()],
            lambda h: [x.strip() for x in re.split(r"[\t ]{4,}|\t", h.strip()) if x.strip()],
            lambda h: [x.strip() for x in re.split(r"[\t ]{5,}|\t", h.strip()) if x.strip()],
            lambda h: h.split(),
        ]
        header_results = [s(header_raw) for s in header_strategies]

        raw_data_lines = []
        for i in range(start + 1, len(raw_lines)):
            line = raw_lines[i].strip()
            if line == "":
                continue
            raw_data_lines.append(line)

        if not raw_data_lines:
            raise ValueError("No data rows found")

        data_strategies = [
            ("any-ws", lambda line: line.split()),
            ("2+ws", lambda line: [x.strip() for x in DATA_DELIM.split(line.strip()) if x.strip()]),
            ("tab", lambda line: [x.strip() for x in line.split("\t") if x.strip()]),
            ("3+ws", lambda line: [x.strip() for x in re.split(r"[\t ]{3,}|\t", line.strip()) if x.strip()]),
            ("4+ws", lambda line: [x.strip() for x in re.split(r"[\t ]{4,}|\t", line.strip()) if x.strip()]),
        ]

        # Sample from beginning, middle AND end
        sample_size = min(50, len(raw_data_lines))
        sample_indices = set()
        sample_indices.update(range(min(sample_size, len(raw_data_lines))))
        mid = len(raw_data_lines) // 2
        sample_indices.update(range(max(0, mid - 10), min(len(raw_data_lines), mid + 10)))
        sample_indices.update(range(max(0, len(raw_data_lines) - 20), len(raw_data_lines)))
        sample_lines = [raw_data_lines[i] for i in sorted(sample_indices)]

        # Find the most consistent data column count across all strategies
        data_col_count = Counter()
        for name, fn in data_strategies:
            for line in sample_lines:
                data_col_count[len(fn(line))] += 1
        expected_cols = data_col_count.most_common(1)[0][0]

        # Now pick the header strategy that gives this exact count
        headers = None
        for r in header_results:
            if len(r) == expected_cols:
                headers = r
                break

        # If no header strategy matches data, use the most common header count and adjust
        if headers is None:
            header_counts = Counter(len(r) for r in header_results)
            best_header_count = header_counts.most_common(1)[0][0]
            headers = next(r for r in header_results if len(r) == best_header_count)
            if len(headers) < expected_cols:
                headers += [f"Col_{i}" for i in range(len(headers), expected_cols)]
            elif len(headers) > expected_cols:
                headers = headers[:expected_cols]

        if not headers or len(headers) < 2:
            raise ValueError("Could not parse headers")

        expected_cols = len(headers)
        print(f"[PFA Parser] Headers ({expected_cols}): {headers[:5]}... +{expected_cols-5} more")

        best_strategy = None
        best_match_count = 0
        for name, strategy in data_strategies:
            matches = sum(1 for line in sample_lines if len(strategy(line)) == expected_cols)
            if matches > best_match_count:
                best_match_count = matches
                best_strategy = (name, strategy)

        if best_strategy is None or best_match_count == 0:
            raise ValueError(f"Could not find a delimiter that gives {expected_cols} columns in data")

        strat_name, strat_fn = best_strategy
        fallback_fn = lambda line: line.split()  # .split() always works for numeric data

        # Hybrid parse: primary strategy + .split() fallback for failed rows
        data_rows = []
        fallback_used = 0
        for line in raw_data_lines:
            tokens = strat_fn(line)
            if len(tokens) == expected_cols:
                data_rows.append(tokens)
            else:
                # Fallback: simple whitespace split (handles 1-space gaps from negative/wide values)
                tokens = fallback_fn(line)
                if len(tokens) == expected_cols:
                    data_rows.append(tokens)
                    fallback_used += 1
                else:
                    print(f"[PFA Parser] Skipped row ({len(tokens)} cols): {line[:80]}...")

        if not data_rows:
            raise ValueError("No data rows matched the expected column count")

        df = pd.DataFrame(data_rows, columns=headers)
        df = df.replace("", np.nan)

        if fallback_used > 0:
            print(f"[PFA Parser] {fallback_used} rows recovered via fallback split")
        print(f"[PFA Parser] Loaded {len(data_rows)} rows × {expected_cols} columns")
        return df

    def load_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("All Supported", "*.txt *.csv *.tsv *.xlsx *.xls"),
                       ("Text", "*.txt *.csv *.tsv"), ("Excel", "*.xlsx *.xls")])
        if not path:
            return

        self.status_label.config(text=f"Loading {os.path.basename(path)}...")
        self.update()

        try:
            ext = os.path.splitext(path)[1].lower()
            if ext in (".xlsx", ".xls"):
                self.df = pd.read_excel(path, nrows=CHUNK_SIZE)
            else:
                self.df = self._parse_text_file(path)

            # Robust numeric conversion — handles negatives, floats, scientific notation
            # First strip any hidden whitespace/non-printable chars from all cells
            for col in self.df.columns:
                if self.df[col].dtype == object:
                    self.df[col] = self.df[col].astype(str).str.strip()
                    self.df[col] = self.df[col].replace({"": np.nan, "nan": np.nan, "None": np.nan})
                self.df[col] = pd.to_numeric(self.df[col], errors="coerce")

            # Verify conversion — print dtypes for debugging
            print(f"[PFA] Column dtypes after conversion:")
            for col in self.df.columns:
                print(f"  {col}: {self.df[col].dtype}  (min={self.df[col].min()}, max={self.df[col].max()})")

            # Strip whitespace from column names
            self.df.columns = [c.strip() for c in self.df.columns]

            # Drop fully empty columns/rows
            self.df = self.df.dropna(axis=1, how="all")
            self.df = self.df.dropna(axis=0, how="all").reset_index(drop=True)

            # Store original for junk remover
            self.df_original = self.df.copy()
            self.removed_indices.clear()
            self.removed_history.clear()
            self.junk_count_label.config(text="Removed: 0 points")
            if self.junk_selector:
                self.junk_selector.disconnect()
                self.junk_selector = None

            self.columns = list(self.df.columns)

            # Auto-pick Time column (case-insensitive) or first column as X
            time_col = None
            for col in self.columns:
                if col.lower().strip().startswith("time") or col.lower().strip() == "t":
                    time_col = col
                    break
            default_x = time_col if time_col else (self.columns[0] if self.columns else "")

            # Update all combos
            self.x_combo["values"] = self.columns
            self.x_combo.set(default_x)
            for cb in self.y_combos:
                cb["values"] = self.columns
            for cfg in self.sp_configs:
                cfg["x"]["values"] = self.columns
                cfg["y"]["values"] = self.columns
                cfg["x"].set(default_x)

            # 3D combos
            for cb in [self.x3d_combo, self.y3d_combo, self.z3d_combo, self.color3d_combo]:
                cb["values"] = self.columns
            self.color3d_combo["values"] = ["(Time Index)"] + self.columns

            rows = len(self.df)
            cols = len(self.columns)
            self.file_label.config(text=f"✓ {os.path.basename(path)}\n  {rows:,} rows · {cols} columns",
                                    fg=T["file_ok"])
            self.status_label.config(text=f"Loaded: {rows:,} rows, {cols} columns")

        except Exception as e:
            styled_error(self, "Load Error", f"Failed to load file:\n{e}")
            self.status_label.config(text="Error loading file")

    def _parse_range(self, var_or_str):
        v = var_or_str.get().strip() if hasattr(var_or_str, 'get') else str(var_or_str).strip()
        if v == "":
            return None
        try:
            return float(v)
        except ValueError:
            return None

    def plot_data(self):
        if self.df is None:
            styled_info(self, "No Data", "Load a file first!")
            return

        self._stop_animation()
        self.data_cursors.clear()
        self.zoom_handlers.clear()
        if self.junk_selector:
            self.junk_selector.disconnect()
            self.junk_selector = None
        self.fig.clear()

        mode = self.mode_var.get()
        fs = self.fontsize_var.get()

        try:
            if mode in ("single", "multi"):
                self._plot_single_multi(mode, fs)
            elif mode == "subplot":
                self._plot_subplots(fs)
            elif mode == "3d":
                self._plot_3d(fs)
        except Exception as e:
            styled_error(self, "Plot Error", str(e))
            return

        self.fig.tight_layout()
        self.canvas.draw()
        self.status_label.config(text="Plot rendered ✓")

    def _plot_single_multi(self, mode, fs):
        ax = self.fig.add_subplot(111, facecolor=T["ax_face"])
        ax.set_title(self.title_var.get(), color=T["plot_title"], fontsize=fs + 2, fontfamily="monospace", pad=12)
        ax.tick_params(colors=T["tick"], labelsize=fs - 1)
        ax.grid(True, color=T["grid"], linewidth=0.5)
        for spine in ax.spines.values():
            spine.set_color(T["spine"])

        x_col = self.x_combo.get()
        if not x_col:
            raise ValueError("Select an X axis signal")

        y_cols = []
        y_colors_list = []
        if mode == "single":
            yc = self.y_combos[0].get()
            if not yc:
                raise ValueError("Select a Y axis signal")
            y_cols.append(yc)
            y_colors_list.append(self.y_colors[0].get())
        else:
            for i in range(3):
                yc = self.y_combos[i].get()
                if yc:
                    y_cols.append(yc)
                    y_colors_list.append(self.y_colors[i].get())
            if not y_cols:
                raise ValueError("Select at least one Y axis signal")

        # Clean data — drop rows where X or any selected Y is NaN, force float
        plot_cols = [x_col] + y_cols
        plot_df = self.df[plot_cols].copy()
        for c in plot_cols:
            plot_df[c] = pd.to_numeric(plot_df[c], errors="coerce").astype(float)
        plot_df = plot_df.dropna()

        # Sort by X so the line plot draws in order
        plot_df = plot_df.sort_values(by=x_col)

        if plot_df.empty:
            raise ValueError("No valid numeric data found for selected signals")

        x_data = plot_df[x_col]

        lines = []
        is_scatter = self.plot_type_var.get() == "scatter"
        for i, (yc, clr) in enumerate(zip(y_cols, y_colors_list)):
            if is_scatter:
                line, = ax.plot(x_data, plot_df[yc], "o", color=clr, markersize=2.5, label=yc, linestyle="none")
            else:
                line, = ax.plot(x_data, plot_df[yc], color=clr, linewidth=1.2, label=yc)
            lines.append(line)

        ax.set_xlabel(self.xlabel_var.get(), fontsize=fs, color=T["label"], fontfamily="monospace")
        ax.set_ylabel(self.ylabel_var.get(), fontsize=fs, color=T["label"], fontfamily="monospace")

        # axis range
        xmin, xmax = self._parse_range(self.xmin_var), self._parse_range(self.xmax_var)
        ymin, ymax = self._parse_range(self.ymin_var), self._parse_range(self.ymax_var)
        if xmin is not None or xmax is not None:
            cur_lo, cur_hi = ax.get_xlim()
            ax.set_xlim(xmin if xmin is not None else cur_lo, xmax if xmax is not None else cur_hi)
        if ymin is not None or ymax is not None:
            cur_lo, cur_hi = ax.get_ylim()
            ax.set_ylim(ymin if ymin is not None else cur_lo, ymax if ymax is not None else cur_hi)

        if self.legend_on.get() and lines:
            # Update legend entry fields
            self._build_legend_entries(y_cols)
            leg = ax.legend(fontsize=fs - 1, facecolor=T["leg_bg"], edgecolor=T["leg_edge"],
                            labelcolor=T["leg_text"], framealpha=0.9)
            if leg:
                leg.set_draggable(True)

        # zoom handler (created first so cursor can reference it)
        zh = ZoomHandler(ax, self.canvas)
        zh.enabled = self.zoom_enabled.get()
        self.zoom_handlers.append(zh)

        # Junk remover mode OR data cursors
        if self.junk_mode.get() and is_scatter:
            self.junk_selector = JunkSelector(
                ax, self.canvas, plot_df, x_col, y_cols,
                on_remove_callback=self._junk_remove_points
            )
        else:
            dc = DataCursor(ax, lines, y_colors_list, self.canvas, zoom_handlers=self.zoom_handlers)
            self.data_cursors.append(dc)

        self._current_ax = ax
        self._current_lines = lines
        self._x_col = x_col
        self._y_cols = y_cols

    def _get_subplot_layout(self, count):
        """
        Returns (nrows, ncols) and a list of (row, col, colspan) for each subplot.
        Layouts match reference images:
          2: 2×1 stacked vertical
          3: 3×1 stacked vertical
          4: 2×2 grid
          5: 3×2, last row centered (1 spanning middle)
          6: 3×2 grid
          7: 4×2, last row centered
          8: 4×2 grid
          9: 3×3 grid
          10: 5×2 grid
        """
        from matplotlib.gridspec import GridSpec

        layouts = {
            2:  (2, 1),    # 2 rows, 1 col
            3:  (3, 1),    # 3 rows, 1 col
            4:  (2, 2),    # 2 rows, 2 cols
            5:  (3, 2),    # 3 rows, 2 cols (5th centered)
            6:  (3, 2),    # 3 rows, 2 cols
            7:  (4, 2),    # 4 rows, 2 cols (7th centered)
            8:  (4, 2),    # 4 rows, 2 cols
            9:  (3, 3),    # 3 rows, 3 cols
            10: (5, 2),    # 5 rows, 2 cols
        }

        nrows, ncols = layouts.get(count, (count // 2 + count % 2, 2))
        total_slots = nrows * ncols

        gs = GridSpec(nrows, ncols, figure=self.fig, hspace=0.4, wspace=0.3)

        axes = []
        slot = 0
        for i in range(count):
            r = slot // ncols
            c = slot % ncols

            # Special: last subplot when count is odd and ncols=2 → center it
            if i == count - 1 and count % 2 == 1 and ncols == 2 and count not in (3,):
                # Span across both columns for centered look
                # Use a subplot that sits in the middle
                ax = self.fig.add_subplot(gs[r, :], facecolor=T["ax_face"])
            elif i == count - 1 and count % 2 == 1 and ncols == 3:
                # For 3 cols, if odd, center last in middle column
                # This won't happen for 9 (3×3 = 9 even slots), just a safety
                ax = self.fig.add_subplot(gs[r, 1], facecolor=T["ax_face"])
            else:
                ax = self.fig.add_subplot(gs[r, c], facecolor=T["ax_face"])

            axes.append(ax)
            slot += 1

        return axes

    def _plot_subplots(self, fs):
        count = self.sp_count_var.get()
        count = max(2, min(10, count))  # clamp 2-10

        axes = self._get_subplot_layout(count)

        self.fig.suptitle(self.title_var.get(), color=T["plot_title"], fontsize=fs + 2, fontfamily="monospace", y=0.99)

        for i, ax in enumerate(axes):
            cfg = self.sp_configs[i]
            x_col = cfg["x"].get()
            y_col = cfg["y"].get()
            if not x_col or not y_col:
                ax.text(0.5, 0.5, f"Subplot {i+1}\nNot configured", ha="center", va="center",
                        color=T["muted"], fontsize=10, transform=ax.transAxes)
                continue

            clr = cfg["color_var"].get()
            leg_label = cfg["legend"].get() or y_col

            # Clean data for this subplot
            sp_df = self.df[[x_col, y_col]].copy()
            sp_df[x_col] = pd.to_numeric(sp_df[x_col], errors="coerce").astype(float)
            sp_df[y_col] = pd.to_numeric(sp_df[y_col], errors="coerce").astype(float)
            sp_df = sp_df.dropna().sort_values(by=x_col).reset_index(drop=True)

            if sp_df.empty:
                ax.text(0.5, 0.5, f"Subplot {i+1}\nNo valid data", ha="center", va="center",
                        color=T["muted"], fontsize=10, transform=ax.transAxes)
                continue

            if self.plot_type_var.get() == "scatter":
                line, = ax.plot(sp_df[x_col], sp_df[y_col], "o", color=clr, markersize=2.5, label=leg_label, linestyle="none")
            else:
                line, = ax.plot(sp_df[x_col], sp_df[y_col], color=clr, linewidth=1.2, label=leg_label)
            ax.set_xlabel(cfg["xlabel"].get(), fontsize=fs - 1, color=T["label"], fontfamily="monospace")
            ax.set_ylabel(cfg["ylabel"].get(), fontsize=fs - 1, color=T["label"], fontfamily="monospace")
            ax.tick_params(colors=T["tick"], labelsize=fs - 2)
            ax.grid(True, color=T["grid"], linewidth=0.5)
            for spine in ax.spines.values():
                spine.set_color(T["spine"])

            # ranges — individual subplot offset
            xmin = self._parse_range(cfg["xmin"].get())
            xmax = self._parse_range(cfg["xmax"].get())
            ymin = self._parse_range(cfg["ymin"].get())
            ymax = self._parse_range(cfg["ymax"].get())
            # If default offset is enabled, use default values where individual is blank
            if self.sp_default_offset.get():
                d_xmin = self._parse_range(self.sp_default_vars["xmin"].get())
                d_xmax = self._parse_range(self.sp_default_vars["xmax"].get())
                d_ymin = self._parse_range(self.sp_default_vars["ymin"].get())
                d_ymax = self._parse_range(self.sp_default_vars["ymax"].get())
                if xmin is None: xmin = d_xmin
                if xmax is None: xmax = d_xmax
                if ymin is None: ymin = d_ymin
                if ymax is None: ymax = d_ymax
            if xmin is not None or xmax is not None:
                cur_lo, cur_hi = ax.get_xlim()
                ax.set_xlim(xmin if xmin is not None else cur_lo, xmax if xmax is not None else cur_hi)
            if ymin is not None or ymax is not None:
                cur_lo, cur_hi = ax.get_ylim()
                ax.set_ylim(ymin if ymin is not None else cur_lo, ymax if ymax is not None else cur_hi)

            if self.legend_on.get():
                leg = ax.legend(fontsize=fs - 2, facecolor=T["leg_bg"], edgecolor=T["leg_edge"],
                                labelcolor=T["leg_text"], framealpha=0.9, loc="lower right")
                if leg:
                    leg.set_draggable(True)

            # zoom handler per subplot
            zh = ZoomHandler(ax, self.canvas)
            zh.enabled = self.zoom_enabled.get()
            self.zoom_handlers.append(zh)

            dc = DataCursor(ax, [line], [clr], self.canvas, zoom_handlers=self.zoom_handlers)
            self.data_cursors.append(dc)

    def _plot_3d(self, fs):
        from mpl_toolkits.mplot3d import Axes3D
        x_col = self.x3d_combo.get()
        y_col = self.y3d_combo.get()
        z_col = self.z3d_combo.get()
        if not x_col or not y_col or not z_col:
            raise ValueError("Select X, Y, and Z axis signals for 3D plot")

        cols = list(set([x_col, y_col, z_col]))
        color_col = self.color3d_combo.get()
        if color_col and color_col != "(Time Index)" and color_col not in cols:
            cols.append(color_col)

        df3 = self.df[cols].copy()
        for c in cols:
            df3[c] = pd.to_numeric(df3[c], errors="coerce").astype(float)
        df3 = df3.dropna().reset_index(drop=True)
        if df3.empty:
            raise ValueError("No valid numeric data for 3D plot")

        # Downsample for 3D performance — matplotlib 3D can't handle 50K+ points
        MAX_3D_POINTS = 5000
        original_len = len(df3)
        if len(df3) > MAX_3D_POINTS:
            step = len(df3) // MAX_3D_POINTS
            df3 = df3.iloc[::step].reset_index(drop=True)
            print(f"[PFA] 3D downsampled: {original_len} → {len(df3)} points (every {step}th)")

        xd = df3[x_col].values
        yd = df3[y_col].values
        zd = df3[z_col].values

        plot_type = self.plot3d_type.get()
        line_clr = self.line3d_color.get()

        ax = self.fig.add_subplot(111, projection="3d")
        ax.set_facecolor(T["ax_face"])
        # Pane colors
        try:
            pane_color = T["ax_face"]
            ax.xaxis.set_pane_color((*self._hex_to_rgb(pane_color), 0.9))
            ax.yaxis.set_pane_color((*self._hex_to_rgb(pane_color), 0.9))
            ax.zaxis.set_pane_color((*self._hex_to_rgb(pane_color), 0.9))
        except Exception:
            pass

        ax.set_title(self.title_var.get(), color=T["plot_title"], fontsize=fs + 2, fontfamily="monospace", pad=10)
        ax.set_xlabel(self.x3d_label.get(), fontsize=fs, color=T["label"], fontfamily="monospace", labelpad=8)
        ax.set_ylabel(self.y3d_label.get(), fontsize=fs, color=T["label"], fontfamily="monospace", labelpad=8)
        ax.set_zlabel(self.z3d_label.get(), fontsize=fs, color=T["label"], fontfamily="monospace", labelpad=8)
        ax.tick_params(colors=T["tick"], labelsize=fs - 2)
        ax.grid(True, color=T["grid"], linewidth=0.3, alpha=0.5)

        if plot_type == "trajectory":
            ax.plot3D(xd, yd, zd, color=line_clr, linewidth=1.5)
            # Mark start and end
            ax.scatter(*[[v] for v in [xd[0], yd[0], zd[0]]], color="#22c55e", s=60, marker="o", zorder=10, label="Start")
            ax.scatter(*[[v] for v in [xd[-1], yd[-1], zd[-1]]], color="#ef4444", s=60, marker="^", zorder=10, label="End")
            leg = ax.legend(fontsize=fs - 2, facecolor=T["leg_bg"], edgecolor=T["leg_edge"],
                            labelcolor=T["leg_text"], framealpha=0.9)

        elif plot_type == "scatter_time":
            if color_col and color_col != "(Time Index)" and color_col in df3.columns:
                c_data = df3[color_col].values
                clabel = color_col
            else:
                c_data = np.arange(len(xd))
                clabel = "Time Index"
            sc = ax.scatter3D(xd, yd, zd, c=c_data, cmap="viridis", s=8, alpha=0.8)
            cbar = self.fig.colorbar(sc, ax=ax, shrink=0.6, pad=0.1)
            cbar.set_label(clabel, color=T["label"], fontsize=fs - 1)
            cbar.ax.tick_params(colors=T["tick"], labelsize=fs - 2)

        elif plot_type == "ribbon":
            from mpl_toolkits.mplot3d.art3d import Poly3DCollection
            # Determine color data for ribbon
            if color_col and color_col != "(Time Index)" and color_col in df3.columns:
                c_data = df3[color_col].values
                clabel = color_col
            else:
                c_data = np.arange(len(xd), dtype=float)
                clabel = "Time Index"

            # Normalize color data to 0-1 for colormap
            c_min, c_max = c_data.min(), c_data.max()
            if c_max == c_min:
                c_norm = np.zeros_like(c_data)
            else:
                c_norm = (c_data - c_min) / (c_max - c_min)

            # Build ribbon width perpendicular to the trajectory
            # Calculate direction vectors between consecutive points
            ribbon_width_frac = 0.03  # 3% of total data range
            x_range = max(xd.max() - xd.min(), 1e-6)
            y_range = max(yd.max() - yd.min(), 1e-6)
            z_range = max(zd.max() - zd.min(), 1e-6)
            w = max(x_range, y_range, z_range) * ribbon_width_frac

            # Use colormap
            cmap = plt.cm.coolwarm

            # Build quads — each segment is a small rectangle
            verts_list = []
            colors_list = []
            for i in range(len(xd) - 1):
                # Direction vector
                dx = xd[i+1] - xd[i]
                dy = yd[i+1] - yd[i]
                dz = zd[i+1] - zd[i]
                length = np.sqrt(dx**2 + dy**2 + dz**2)
                if length < 1e-12:
                    continue

                # Perpendicular vector (cross with up=[0,0,1])
                px, py, pz = -dy, dx, 0
                pl = np.sqrt(px**2 + py**2 + pz**2)
                if pl < 1e-12:
                    px, py, pz = w, 0, 0
                else:
                    px, py, pz = px/pl * w, py/pl * w, pz/pl * w

                # Four corners of the ribbon quad
                v0 = [xd[i] - px, yd[i] - py, zd[i] - pz]
                v1 = [xd[i] + px, yd[i] + py, zd[i] + pz]
                v2 = [xd[i+1] + px, yd[i+1] + py, zd[i+1] + pz]
                v3 = [xd[i+1] - px, yd[i+1] - py, zd[i+1] - pz]
                verts_list.append([v0, v1, v2, v3])

                # Average color for this segment
                avg_norm = (c_norm[i] + c_norm[i+1]) / 2
                colors_list.append(cmap(avg_norm))

            if verts_list:
                poly = Poly3DCollection(verts_list, alpha=0.85, linewidths=0.1, edgecolors=T["spine"])
                poly.set_facecolor(colors_list)
                ax.add_collection3d(poly)

            # Colorbar with proper thresholds
            sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=c_min, vmax=c_max))
            sm.set_array([])
            cbar = self.fig.colorbar(sm, ax=ax, shrink=0.6, pad=0.1)
            cbar.set_label(clabel, color=T["label"], fontsize=fs - 1)
            cbar.ax.tick_params(colors=T["tick"], labelsize=fs - 2)

            # Start/end markers
            ax.scatter(*[[v] for v in [xd[0], yd[0], zd[0]]], color="#22c55e", s=60, marker="o", zorder=10, label="Start")
            ax.scatter(*[[v] for v in [xd[-1], yd[-1], zd[-1]]], color="#ef4444", s=60, marker="^", zorder=10, label="End")
            leg = ax.legend(fontsize=fs - 2, facecolor=T["leg_bg"], edgecolor=T["leg_edge"],
                            labelcolor=T["leg_text"], framealpha=0.9)

        elif plot_type == "attitude":
            # Color segments by progression
            segments = len(xd) - 1
            cmap = plt.cm.plasma
            for i in range(segments):
                frac = i / max(segments, 1)
                ax.plot3D(xd[i:i+2], yd[i:i+2], zd[i:i+2],
                          color=cmap(frac), linewidth=1.5)
            # Add colorbar showing progression
            sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, 1))
            sm.set_array([])
            cbar = self.fig.colorbar(sm, ax=ax, shrink=0.6, pad=0.1)
            cbar.set_label("Flight Progression", color=T["label"], fontsize=fs - 1)
            cbar.ax.tick_params(colors=T["tick"], labelsize=fs - 2)
            ax.scatter(*[[v] for v in [xd[0], yd[0], zd[0]]], color="#22c55e", s=60, marker="o", zorder=10, label="Start")
            ax.scatter(*[[v] for v in [xd[-1], yd[-1], zd[-1]]], color="#ef4444", s=60, marker="^", zorder=10, label="End")
            leg = ax.legend(fontsize=fs - 2, facecolor=T["leg_bg"], edgecolor=T["leg_edge"],
                            labelcolor=T["leg_text"], framealpha=0.9)

        self.status_label.config(text=f"3D {plot_type} plot rendered ✓ | Drag to rotate")

    @staticmethod
    def _hex_to_rgb(hex_color):
        h = hex_color.lstrip("#")
        return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))

    def _build_legend_entries(self, y_cols):
        for w in self.legend_entry_frame.winfo_children():
            w.destroy()
        self.legend_entries.clear()
        for i, yc in enumerate(y_cols):
            f = tk.Frame(self.legend_entry_frame, bg=T["panel"])
            f.pack(fill="x", pady=1)
            tk.Label(f, text=f"L{i+1}:", bg=T["panel"], fg=T["muted"], font=("Consolas", 8)).pack(side="left")
            sv = tk.StringVar(value=yc)
            e = ttk.Entry(f, textvariable=sv, width=20)
            e.pack(side="left", padx=4)
            self.legend_entries.append(sv)

    def toggle_animation(self):
        if self.anim_running:
            self._stop_animation()
        else:
            self._start_animation()

    def _start_animation(self):
        if self.df is None:
            return

        self.data_cursors.clear()
        self.zoom_handlers.clear()
        self.fig.clear()
        mode = self.mode_var.get()
        fs = self.fontsize_var.get()

        if mode in ("subplot", "3d"):
            styled_info(self, "Animation", "Animation works with Single and Multiplot modes.\nSwitch mode and try again!")
            return

        ax = self.fig.add_subplot(111, facecolor=T["ax_face"])
        ax.set_title(self.title_var.get(), color=T["plot_title"], fontsize=fs + 2, fontfamily="monospace", pad=12)
        ax.tick_params(colors=T["tick"], labelsize=fs - 1)
        ax.grid(True, color=T["grid"], linewidth=0.5)
        for spine in ax.spines.values():
            spine.set_color(T["spine"])

        x_col = self.x_combo.get()
        if not x_col:
            return

        y_cols = []
        y_colors_list = []
        if mode == "single":
            yc = self.y_combos[0].get()
            if yc:
                y_cols.append(yc)
                y_colors_list.append(self.y_colors[0].get())
        else:
            for i in range(3):
                yc = self.y_combos[i].get()
                if yc:
                    y_cols.append(yc)
                    y_colors_list.append(self.y_colors[i].get())

        if not y_cols:
            return

        # Clean data
        anim_df = self.df[[x_col] + y_cols].copy()
        for c in [x_col] + y_cols:
            anim_df[c] = pd.to_numeric(anim_df[c], errors="coerce").astype(float)
        anim_df = anim_df.dropna().sort_values(by=x_col).reset_index(drop=True)

        if anim_df.empty:
            return

        x_data = anim_df[x_col].values

        ax.set_xlabel(self.xlabel_var.get(), fontsize=fs, color=T["label"], fontfamily="monospace")
        ax.set_ylabel(self.ylabel_var.get(), fontsize=fs, color=T["label"], fontfamily="monospace")

        # Set axis limits
        ax.set_xlim(x_data.min(), x_data.max())
        all_y = np.concatenate([anim_df[yc].values for yc in y_cols])
        pad = (all_y.max() - all_y.min()) * 0.05
        ax.set_ylim(all_y.min() - pad, all_y.max() + pad)

        # Override with user ranges
        xmin, xmax = self._parse_range(self.xmin_var), self._parse_range(self.xmax_var)
        ymin, ymax = self._parse_range(self.ymin_var), self._parse_range(self.ymax_var)
        if xmin is not None or xmax is not None:
            cur_lo, cur_hi = ax.get_xlim()
            ax.set_xlim(xmin if xmin is not None else cur_lo, xmax if xmax is not None else cur_hi)
        if ymin is not None or ymax is not None:
            cur_lo, cur_hi = ax.get_ylim()
            ax.set_ylim(ymin if ymin is not None else cur_lo, ymax if ymax is not None else cur_hi)

        lines = []
        is_scatter = self.plot_type_var.get() == "scatter"
        for yc, clr in zip(y_cols, y_colors_list):
            if is_scatter:
                line, = ax.plot([], [], "o", color=clr, markersize=2.5, label=yc, linestyle="none")
            else:
                line, = ax.plot([], [], color=clr, linewidth=1.2, label=yc)
            lines.append(line)

        if self.legend_on.get():
            leg = ax.legend(fontsize=fs - 1, facecolor=T["leg_bg"], edgecolor=T["leg_edge"],
                            labelcolor=T["leg_text"], framealpha=0.9)
            if leg:
                leg.set_draggable(True)

        total = len(x_data)
        speed = self.anim_speed_var.get()  # 1-10
        step = max(1, total // max(50, 600 - speed * 55))  # speed 1→~600 frames, 10→~50 frames
        interval = max(5, 30 - speed * 2)  # speed 1→28ms, 10→10ms

        def init():
            for line in lines:
                line.set_data([], [])
            return lines

        def animate(frame):
            n = min(frame * step, total)
            for line, yc in zip(lines, y_cols):
                line.set_data(x_data[:n], anim_df[yc].values[:n])
            if n >= total:
                self._stop_animation()
            return lines

        self.anim = animation.FuncAnimation(
            self.fig, animate, init_func=init,
            frames=total // step + 2, interval=interval, blit=True, repeat=False
        )
        self.anim_running = True
        self.canvas.draw()
        self.status_label.config(text="Animation running ▶")

    def _stop_animation(self):
        if self.anim:
            self.anim.event_source.stop()
            self.anim = None
        self.anim_running = False
        self.status_label.config(text="Animation stopped ■")

    def clear_plot(self):
        """Wipe the canvas, kill animation, remove all cursors."""
        self._stop_animation()
        # Remove all data cursors
        for dc in self.data_cursors:
            dc.clear_all()
        self.data_cursors.clear()
        self.zoom_handlers.clear()
        if self.junk_selector:
            self.junk_selector.disconnect()
            self.junk_selector = None
        # Clear figure
        self.fig.clear()
        self.canvas.draw()
        self.status_label.config(text="Plot cleared")

    def export_png(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png")],
            initialfile=f"{self.title_var.get()}.png"
        )
        if path:
            self.fig.savefig(path, dpi=200, facecolor=self.fig.get_facecolor(),
                             edgecolor="none", bbox_inches="tight")
            self.status_label.config(text=f"Exported: {os.path.basename(path)} ✓")

# ============================================================
#  RUN
# ============================================================
if __name__ == "__main__":
    app = TelemetryPlotter()
    app.mainloop()
