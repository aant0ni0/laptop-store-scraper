"""Data quality checks, descriptive statistics and charts used by notebooks/analysis.ipynb."""

import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from scraper.dataset import INT_FIELDS

NUMERIC_COLUMNS = [
    "price_pln",
    "rating",
    "review_count",
    "warranty_months",
    "screen_size_in",
    "weight_kg",
    "release_year",
    "ram_gb",
    "storage_gb",
    "battery_wh",
]
NAME_PATTERN = re.compile(
    r'(?P<screen>\d+(?:\.\d+)?)" .+?'
    r"/(?P<ram>\d+)GB/(?P<storage>\d+)(?P<unit>GB|TB)(?:/(?P<gpu>RTX \d+))?$"
)


def load_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig", parse_dates=["date_added"])
    for column in INT_FIELDS:
        df[column] = df[column].astype("Int64")
    return df


def load_raw(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", dtype=str)


def missing_values(df: pd.DataFrame) -> pd.DataFrame:
    missing = df.isna().sum()
    return pd.DataFrame(
        {
            "dtype": df.dtypes.astype(str),
            "missing": missing,
            "missing_pct": (missing / len(df) * 100).round(1),
        }
    )


def duplicates(raw: pd.DataFrame, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    duplicated = raw[raw.duplicated("id", keep=False)].sort_values(["id", "source_page"])
    counts = pd.DataFrame(
        {
            "rows": [len(raw), len(df)],
            "unique_ids": [raw["id"].nunique(), df["id"].nunique()],
            "duplicate_rows": [int(raw.duplicated("id").sum()), int(df.duplicated("id").sum())],
        },
        index=["before (raw)", "after (clean)"],
    )
    return counts, duplicated[["id", "name", "source_page", "layout"]]


def descriptive_statistics(df: pd.DataFrame, columns: list[str] = NUMERIC_COLUMNS) -> pd.DataFrame:
    numeric = df[columns].astype("float64")
    return pd.DataFrame(
        {
            "count": numeric.count(),
            "mean": numeric.mean(),
            "median": numeric.median(),
            "mode": numeric.mode().iloc[0],
            "std": numeric.std(),
            "min": numeric.min(),
            "q1": numeric.quantile(0.25),
            "q3": numeric.quantile(0.75),
            "max": numeric.max(),
        }
    ).round(2)


def iqr_outliers(df: pd.DataFrame, column: str, factor: float = 1.5) -> pd.DataFrame:
    values = df[column].astype("float64")
    q1, q3 = values.quantile([0.25, 0.75])
    low, high = q1 - factor * (q3 - q1), q3 + factor * (q3 - q1)
    return df[(values < low) | (values > high)]


def outlier_counts(df: pd.DataFrame, columns: list[str] = NUMERIC_COLUMNS) -> pd.Series:
    return pd.Series({column: len(iqr_outliers(df, column)) for column in columns})


def naive_price(text: str) -> float | None:
    """What a careless parser does: keep the digits. "1 299,00 zł" becomes 129900."""
    digits = re.sub(r"\D", "", str(text))
    return float(digits) if digits else None


def name_consistency(df: pd.DataFrame) -> pd.DataFrame:
    """Compare screen, RAM, storage and GPU written in the product name with the spec columns."""
    parts = df["name"].str.extract(NAME_PATTERN)
    storage = parts["storage"].astype("float64") * parts["unit"].map({"GB": 1, "TB": 1024})
    gpu_in_name = parts["gpu"].fillna("")
    gpu_in_specs = df["gpu"].fillna("").str.extract(r"(RTX \d+)")[0].fillna("")
    checks = pd.DataFrame(
        {
            "name_parsed": parts["ram"].notna(),
            "screen": parts["screen"].astype("float64") == df["screen_size_in"],
            "ram": parts["ram"].astype("float64") == df["ram_gb"].astype("float64"),
            "storage": storage == df["storage_gb"].astype("float64"),
            "gpu": gpu_in_name == gpu_in_specs,
        }
    )
    return checks.sum().to_frame("matching").assign(of=len(df))


def with_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.assign(
        dedicated_gpu=df["gpu"].str.startswith("NVIDIA").astype("float64"),
        ssd=(df["storage_type"] == "SSD").astype("float64"),
    )


def correlations(df: pd.DataFrame) -> pd.DataFrame:
    columns = [*NUMERIC_COLUMNS, "dedicated_gpu"]
    return with_derived_columns(df)[columns].astype("float64").corr().round(2)


def save_figure(figure: plt.Figure, directory: Path, name: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.png"
    figure.savefig(path, dpi=150, bbox_inches="tight")
    return path


def price_histogram(df: pd.DataFrame) -> plt.Figure:
    figure, axis = plt.subplots(figsize=(8, 4.5))
    axis.hist(df["price_pln"].dropna(), bins=30, color="#3b6ea8", edgecolor="white")
    axis.axvline(df["price_pln"].mean(), color="#c0392b", linestyle="--", label="średnia")
    axis.axvline(df["price_pln"].median(), color="#2c3e50", linestyle=":", label="mediana")
    axis.set(title="Rozkład cen laptopów", xlabel="Cena [PLN]", ylabel="Liczba produktów")
    axis.legend()
    return figure


def price_boxplot_by_category(df: pd.DataFrame) -> plt.Figure:
    order = df.groupby("category")["price_pln"].median().sort_values().index
    figure, axis = plt.subplots(figsize=(8, 4.5))
    axis.boxplot(
        [df.loc[df["category"] == category, "price_pln"].dropna() for category in order],
        tick_labels=list(order),
    )
    axis.set(title="Cena według kategorii", xlabel="Kategoria", ylabel="Cena [PLN]")
    return figure


def correlation_heatmap(corr: pd.DataFrame) -> plt.Figure:
    figure, axis = plt.subplots(figsize=(8, 6.5))
    image = axis.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    axis.set_xticks(range(len(corr)), corr.columns, rotation=45, ha="right")
    axis.set_yticks(range(len(corr)), corr.index)
    for row in range(len(corr)):
        for column in range(len(corr)):
            value = corr.iloc[row, column]
            color = "white" if abs(value) > 0.6 else "black"
            axis.text(
                column, row, f"{value:.2f}", ha="center", va="center", fontsize=7, color=color
            )
    figure.colorbar(image, ax=axis, label="współczynnik Pearsona")
    axis.set_title("Macierz korelacji cech liczbowych")
    return figure


def scatter(df: pd.DataFrame, x: str, y: str, title: str, xlabel: str, ylabel: str) -> plt.Figure:
    figure, axis = plt.subplots(figsize=(6.5, 4.5))
    axis.scatter(df[x].astype("float64"), df[y].astype("float64"), alpha=0.5, s=14)
    r = df[[x, y]].astype("float64").corr().iloc[0, 1]
    axis.set(title=f"{title} (r = {r:.2f})", xlabel=xlabel, ylabel=ylabel)
    return figure
