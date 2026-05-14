import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def _bar(df: pd.DataFrame, ax) -> None:
    ax.bar(df.iloc[:, 0].astype(str), df.iloc[:, 1])
    ax.tick_params(axis="x", rotation=45)


def _line(df: pd.DataFrame, ax) -> None:
    ax.plot(df.iloc[:, 0].astype(str), df.iloc[:, 1], marker="o")
    ax.tick_params(axis="x", rotation=45)


def _pie(df: pd.DataFrame, ax) -> None:
    ax.pie(df.iloc[:, 1], labels=df.iloc[:, 0].astype(str), autopct="%1.1f%%")
    ax.set_aspect("equal")


def _scatter(df: pd.DataFrame, ax) -> None:
    ax.scatter(df.iloc[:, 0], df.iloc[:, 1])


def _hist(df: pd.DataFrame, ax) -> None:
    numeric = df.select_dtypes(include="number")
    series = numeric.iloc[:, 0] if not numeric.empty else df.iloc[:, 0]
    ax.hist(series.dropna(), bins=20)


_DISPATCH = {
    "bar": _bar,
    "line": _line,
    "pie": _pie,
    "scatter": _scatter,
    "hist": _hist,
}


def make_figure(
    df: pd.DataFrame,
    viz_type: str,
    title: str,
    x_label: str,
    y_label: str,
) -> plt.Figure:
    """Build and return a matplotlib Figure. No I/O."""
    if viz_type not in _DISPATCH:
        raise ValueError(f"Unsupported viz_type: {viz_type}")
    if df is None or df.empty:
        raise ValueError("Cannot render an empty DataFrame")

    fig, ax = plt.subplots(figsize=(8, 5))
    _DISPATCH[viz_type](df, ax)

    ax.set_title(title)
    if viz_type != "pie":
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)

    plt.tight_layout()
    return fig


def save_figure(fig: plt.Figure, out_path: str) -> str:
    """Save a Figure to disk at 150 DPI, close it, return the path."""
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def render(
    df: pd.DataFrame,
    viz_type: str,
    title: str,
    x_label: str,
    y_label: str,
    out_path: str,
) -> str:
    """Backwards-compat wrapper: make_figure + save_figure."""
    return save_figure(make_figure(df, viz_type, title, x_label, y_label), out_path)
