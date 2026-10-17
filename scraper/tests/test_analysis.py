import pandas as pd

from scraper.analysis import descriptive_statistics, iqr_outliers, naive_price, name_consistency


def test_naive_price_shows_the_decimal_comma_bug():
    assert naive_price("1 299,00 zł") == 129900
    assert naive_price("—") is None


def test_iqr_outliers_flags_values_far_from_the_middle():
    df = pd.DataFrame({"price_pln": [1000, 1100, 1200, 1300, 1400, 129900]})
    assert iqr_outliers(df, "price_pln")["price_pln"].tolist() == [129900]


def test_descriptive_statistics_include_mode_and_quartiles():
    df = pd.DataFrame({"ram_gb": pd.array([8, 16, 16, 32, None], dtype="Int64")})
    stats = descriptive_statistics(df, ["ram_gb"]).loc["ram_gb"]
    assert stats["count"] == 4
    assert stats["mode"] == 16
    assert stats["median"] == 16
    assert stats["q1"] == 14
    assert stats["max"] == 32


def test_name_consistency_compares_name_with_spec_columns():
    df = pd.DataFrame(
        {
            "name": [
                'Lenovo Legion 5 16" i7-13650HX/32GB/1TB/RTX 4060',
                'HP 15s 15.6" i3-1215U/8GB/512GB',
            ],
            "screen_size_in": [16.0, 15.6],
            "ram_gb": pd.array([32, 16], dtype="Int64"),
            "storage_gb": pd.array([1024, 512], dtype="Int64"),
            "gpu": ["NVIDIA GeForce RTX 4060", "Intel UHD Graphics"],
        }
    )
    result = name_consistency(df)["matching"]
    assert result["name_parsed"] == 2
    assert result["screen"] == 2
    assert result["ram"] == 1
    assert result["storage"] == 2
    assert result["gpu"] == 2
