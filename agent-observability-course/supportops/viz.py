"""Helpers de visualización compartidos por los notebooks (requiere ``pip install -e agent-observability-course[viz]``).

Diagramas dibujados en código (sin imágenes externas): cajas, flechas, cascadas de trazas (waterfall).
Convención de colores: trazas = azul, métricas = naranja, logs = verde, perfiles = morado, errores = rojo.
"""
from __future__ import annotations

from typing import Any, Iterable, Sequence

import matplotlib

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

PALETTE = {
    "traces": "#2a6fdb", "metrics": "#e8833a", "logs": "#2f9e63", "profiles": "#8e5bd0", "error": "#d64545",
    "ok": "#2f9e63", "warn": "#e0a100", "neutral": "#6b7280", "light": "#eef2f7", "dark": "#1f2937",
}


def apply_style() -> None:
    plt.rcParams.update({
        "figure.dpi": 110, "savefig.dpi": 110, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.alpha": 0.25, "axes.titlesize": 12, "axes.titleweight": "bold",
        "axes.labelsize": 10, "font.size": 10, "legend.frameon": False,
    })


def canvas(width: float = 10, height: float = 4, xlim: tuple[float, float] = (0, 100), ylim: tuple[float, float] = (0, 40)):
    """Eje vacío (sin ejes ni rejilla) para dibujar diagramas en coordenadas libres."""
    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.axis("off"); ax.grid(False)
    return fig, ax


def box(ax, x: float, y: float, w: float, h: float, text: str, color: str = PALETTE["traces"], fc: str | None = None,
        fontsize: int = 9, text_color: str | None = None, bold: bool = False) -> tuple[float, float, float, float]:
    """Caja redondeada con texto centrado; (x, y) = esquina inferior izquierda. Devuelve (x, y, w, h)."""
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.2", linewidth=1.6, edgecolor=color,
                       facecolor=fc or (color + "22"))
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize, color=text_color or PALETTE["dark"],
            fontweight="bold" if bold else "normal", wrap=True)
    return x, y, w, h


def arrow(ax, p1: tuple[float, float], p2: tuple[float, float], text: str = "", color: str = PALETTE["neutral"],
          style: str = "-|>", rad: float = 0.0, fontsize: int = 8, dashed: bool = False, lw: float = 1.6) -> None:
    a = FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=14, linewidth=lw, color=color,
                        connectionstyle=f"arc3,rad={rad}", linestyle="--" if dashed else "-")
    ax.add_patch(a)
    if text:
        ax.text((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2 + 1.2, text, ha="center", va="bottom", fontsize=fontsize, color=color)


def right(b: tuple[float, float, float, float]) -> tuple[float, float]: return (b[0] + b[2] + 0.3, b[1] + b[3] / 2)
def left(b: tuple[float, float, float, float]) -> tuple[float, float]: return (b[0] - 0.3, b[1] + b[3] / 2)
def top(b: tuple[float, float, float, float]) -> tuple[float, float]: return (b[0] + b[2] / 2, b[1] + b[3] + 0.3)
def bottom(b: tuple[float, float, float, float]) -> tuple[float, float]: return (b[0] + b[2] / 2, b[1] - 0.3)


def waterfall(spans: Sequence[dict[str, Any]], ax=None, title: str = "", t_unit: str = "s", show_attrs: Sequence[str] = ()):
    """Cascada de una traza a partir de spans en el formato de ``supportops.schema.SPAN_SCHEMA``.

    Barra azul = span OK, roja = ERROR; la sangría refleja la profundidad (parent_span_id).
    """
    by_id = {s["span_id"]: s for s in spans}
    children: dict[Any, list[dict[str, Any]]] = {}
    for s in spans:
        children.setdefault(s.get("parent_span_id") if s.get("parent_span_id") in by_id else None, []).append(s)
    ordered: list[tuple[int, dict[str, Any]]] = []

    def walk(pid: Any, d: int) -> None:
        for s in sorted(children.get(pid, []), key=lambda x: (x["start_unix_nano"], -(x["end_unix_nano"] or 0))):
            ordered.append((d, s))
            walk(s["span_id"], d + 1)

    walk(None, 0)
    t0 = min(s["start_unix_nano"] for s in spans)
    own = ax is None
    if own:
        fig, ax = plt.subplots(figsize=(10, 0.45 * len(spans) + 1.2))
        fig.subplots_adjust(left=0.32)
    for i, (d, s) in enumerate(ordered):
        st = (s["start_unix_nano"] - t0) / 1e9
        du = ((s["end_unix_nano"] or s["start_unix_nano"]) - s["start_unix_nano"]) / 1e9
        color = PALETTE["error"] if s["status"] == "ERROR" else PALETTE["traces"]
        ax.barh(i, du, left=st, color=color, alpha=0.85, height=0.6)
        ax.annotate(s["name"], xy=(0, i), xycoords=("axes fraction", "data"), xytext=(-245 + 12 * d, 0),
                    textcoords="offset points", ha="left", va="center", fontsize=8)
        ax.text(st + du, i, f" {du:.2f}{t_unit}", va="center", fontsize=7, color=PALETTE["neutral"])
    ax.set_yticks([]); ax.invert_yaxis(); ax.set_xlabel(f"tiempo desde el inicio ({t_unit})")
    ax.grid(axis="y", visible=False)
    if title:
        ax.set_title(title)
    return ax


def percentile(xs: Iterable[float], q: float) -> float:
    xs = sorted(xs)
    if not xs:
        return float("nan")
    k = (len(xs) - 1) * q
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)
