"""Generate the laptop catalog used by the shop (shop/data/products.json).

Every product is built step by step: the category decides which components fit,
components decide the price and weight, and a fixed seed makes the output reproducible.
"""

import json
import math
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

SEED = 42
PRODUCT_COUNT = 438
# Fixed reference date instead of date.today(), so the file does not change from day to day.
CATALOG_DATE = date(2026, 10, 1)
CATALOG_AGE_DAYS = 730
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "products.json"

CPUS_BY_TIER = {
    "budget": ["Intel Core i3-1215U", "Intel Core i3-1315U", "AMD Ryzen 3 7320U"],
    "mid": [
        "Intel Core i5-1335U",
        "Intel Core i5-13420H",
        "AMD Ryzen 5 7530U",
        "AMD Ryzen 5 7640HS",
    ],
    "high": [
        "Intel Core i7-1355U",
        "Intel Core i7-13700H",
        "AMD Ryzen 7 7735HS",
        "AMD Ryzen 7 7840HS",
    ],
    "performance": [
        "Intel Core i7-13650HX",
        "Intel Core i9-13980HX",
        "AMD Ryzen 7 7840HS",
        "AMD Ryzen 9 7945HX",
    ],
}
CPU_TIER_PRICE = {"budget": 0, "mid": 700, "high": 1500, "performance": 2500}
DEDICATED_GPU_PRICE = {
    "NVIDIA GeForce RTX 4050": 1500,
    "NVIDIA GeForce RTX 4060": 2200,
    "NVIDIA GeForce RTX 4070": 3500,
    "NVIDIA GeForce RTX 4080": 6000,
}
AVAILABILITY_WEIGHTS = {
    "Dostępny": 60,
    "Ostatnie sztuki": 15,
    "Na zamówienie": 15,
    "Niedostępny": 10,
}


@dataclass(frozen=True, slots=True)
class CategoryProfile:
    label: str
    share: int
    base_price: int
    cpu_tiers: tuple[str, ...]
    dedicated_gpus: tuple[str, ...]
    ram_options_gb: tuple[int, ...]
    storage_options_gb: tuple[int, ...]
    screen_sizes_in: tuple[float, ...]
    resolutions: tuple[str, ...]
    battery_range_wh: tuple[int, int]
    colors: tuple[str, ...]
    systems: tuple[str, ...]
    warranty_options_months: tuple[int, ...]
    extra_weight_kg: float
    hdd_share: float = 0.0


CATEGORIES = {
    "gaming": CategoryProfile(
        label="Gamingowy",
        share=25,
        base_price=2500,
        cpu_tiers=("performance",),
        dedicated_gpus=tuple(DEDICATED_GPU_PRICE),
        ram_options_gb=(16, 32, 64),
        storage_options_gb=(512, 1024, 2048),
        screen_sizes_in=(15.6, 16.0, 17.3),
        resolutions=("1920x1080", "2560x1440", "2560x1600"),
        battery_range_wh=(55, 99),
        colors=("Czarny", "Grafitowy", "Szary"),
        systems=("Windows 11 Home",),
        warranty_options_months=(24,),
        extra_weight_kg=0.5,
    ),
    "business": CategoryProfile(
        label="Biznesowy",
        share=20,
        base_price=2200,
        cpu_tiers=("mid", "high"),
        dedicated_gpus=(),
        ram_options_gb=(8, 16, 32),
        storage_options_gb=(256, 512, 1024),
        screen_sizes_in=(13.3, 14.0, 15.6),
        resolutions=("1920x1080", "1920x1200", "2560x1600"),
        battery_range_wh=(45, 72),
        colors=("Czarny", "Srebrny", "Grafitowy"),
        systems=("Windows 11 Pro",),
        warranty_options_months=(24, 36, 36),
        extra_weight_kg=0.0,
    ),
    "ultrabook": CategoryProfile(
        label="Ultrabook",
        share=20,
        base_price=2600,
        cpu_tiers=("mid", "high"),
        dedicated_gpus=(),
        ram_options_gb=(16, 32),
        storage_options_gb=(512, 1024),
        screen_sizes_in=(13.3, 14.0),
        resolutions=("1920x1200", "2560x1600", "2880x1800"),
        battery_range_wh=(50, 75),
        colors=("Srebrny", "Szary", "Niebieski", "Biały"),
        systems=("Windows 11 Home",),
        warranty_options_months=(24,),
        extra_weight_kg=-0.2,
    ),
    "budget": CategoryProfile(
        label="Budżetowy",
        share=20,
        base_price=900,
        cpu_tiers=("budget", "mid"),
        dedicated_gpus=(),
        ram_options_gb=(8, 16),
        storage_options_gb=(256, 512, 1024),
        screen_sizes_in=(14.0, 15.6, 17.3),
        resolutions=("1366x768", "1920x1080"),
        battery_range_wh=(35, 50),
        colors=("Czarny", "Srebrny", "Szary"),
        systems=("Windows 11 Home", "Brak systemu"),
        warranty_options_months=(12, 24, 24),
        extra_weight_kg=0.1,
        hdd_share=0.25,
    ),
    "convertible": CategoryProfile(
        label="2w1",
        share=15,
        base_price=2300,
        cpu_tiers=("mid", "high"),
        dedicated_gpus=(),
        ram_options_gb=(8, 16, 32),
        storage_options_gb=(512, 1024),
        screen_sizes_in=(13.3, 14.0, 16.0),
        resolutions=("1920x1200", "2560x1600", "2880x1800"),
        battery_range_wh=(45, 70),
        colors=("Srebrny", "Niebieski", "Szary"),
        systems=("Windows 11 Home",),
        warranty_options_months=(24,),
        extra_weight_kg=0.1,
    ),
}

SERIES_BY_CATEGORY = {
    "gaming": {
        "Lenovo": ["Legion 5", "Legion Pro 7", "LOQ 15"],
        "Dell": ["Alienware m16", "G16"],
        "HP": ["Omen 16", "Victus 15"],
        "ASUS": ["ROG Strix G16", "TUF Gaming A15"],
        "Acer": ["Nitro V 15", "Predator Helios 16"],
        "MSI": ["Katana 15", "Raider GE78"],
    },
    "business": {
        "Lenovo": ["ThinkPad T14", "ThinkPad X1 Carbon"],
        "Dell": ["Latitude 5440", "Latitude 7440"],
        "HP": ["EliteBook 840", "ProBook 450"],
        "ASUS": ["ExpertBook B5"],
        "Acer": ["TravelMate P4"],
        "MSI": ["Modern 14"],
    },
    "ultrabook": {
        "Lenovo": ["Yoga Slim 7"],
        "Dell": ["XPS 13"],
        "HP": ["Envy 14"],
        "ASUS": ["Zenbook 14"],
        "Acer": ["Swift Go 14"],
        "MSI": ["Prestige 14"],
    },
    "budget": {
        "Lenovo": ["IdeaPad 3", "IdeaPad Slim 3"],
        "Dell": ["Inspiron 15"],
        "HP": ["15s", "250 G10"],
        "ASUS": ["Vivobook 15"],
        "Acer": ["Aspire 3"],
        "MSI": ["Modern 15"],
    },
    "convertible": {
        "Lenovo": ["Yoga 7 2-in-1"],
        "Dell": ["Inspiron 14 2-in-1"],
        "HP": ["Envy x360", "Spectre x360"],
        "ASUS": ["Zenbook Flip", "Vivobook Flip"],
        "Acer": ["Aspire Spin 14"],
        "MSI": ["Summit E13 Flip"],
    },
}


def generate_products(seed: int = SEED, count: int = PRODUCT_COUNT) -> list[dict]:
    rng = random.Random(seed)
    products = []
    used_names = set()
    for product_id in range(1, count + 1):
        product = generate_product(product_id, rng)
        # Unique names keep real products distinguishable from the duplicates added later.
        while product["name"] in used_names:
            product = generate_product(product_id, rng)
        used_names.add(product["name"])
        products.append(product)
    return products


def generate_product(product_id: int, rng: random.Random) -> dict:
    category = rng.choices(list(CATEGORIES), weights=[p.share for p in CATEGORIES.values()])[0]
    profile = CATEGORIES[category]

    brand = rng.choice(list(SERIES_BY_CATEGORY[category]))
    series = rng.choice(SERIES_BY_CATEGORY[category][brand])

    cpu_tier = rng.choice(profile.cpu_tiers)
    cpu = rng.choice(CPUS_BY_TIER[cpu_tier])
    gpu = rng.choice(profile.dedicated_gpus) if profile.dedicated_gpus else integrated_gpu_for(cpu)
    ram_gb = rng.choice(profile.ram_options_gb)
    storage_type = "HDD" if rng.random() < profile.hdd_share else "SSD"
    storage_gb = 1024 if storage_type == "HDD" else rng.choice(profile.storage_options_gb)
    screen_size_in = rng.choice(profile.screen_sizes_in)

    review_count = min(int(rng.expovariate(1 / 80)) + 1, 1500)
    date_added = CATALOG_DATE - timedelta(days=rng.randint(0, CATALOG_AGE_DAYS))

    return {
        "id": product_id,
        "name": product_name(brand, series, screen_size_in, cpu, ram_gb, storage_gb, gpu),
        "price": product_price(profile, cpu_tier, gpu, ram_gb, storage_gb, storage_type, rng),
        "currency": "PLN",
        "category": profile.label,
        "brand": brand,
        "availability": rng.choices(
            list(AVAILABILITY_WEIGHTS), weights=list(AVAILABILITY_WEIGHTS.values())
        )[0],
        "rating": product_rating(review_count, rng),
        "review_count": review_count,
        "date_added": date_added.isoformat(),
        "warranty_months": rng.choice(profile.warranty_options_months),
        "url": f"/product.html?id={product_id}",
        "cpu": cpu,
        "ram_gb": ram_gb,
        "storage_gb": storage_gb,
        "storage_type": storage_type,
        "gpu": gpu,
        "screen_size_in": screen_size_in,
        "resolution": rng.choice(profile.resolutions),
        "weight_kg": product_weight(profile, screen_size_in, rng),
        "battery_wh": rng.randint(*profile.battery_range_wh),
        "os": rng.choice(profile.systems),
        "color": rng.choice(profile.colors),
        "release_year": rng.randint(date_added.year - 2, date_added.year),
    }


def integrated_gpu_for(cpu: str) -> str:
    if cpu.startswith("AMD"):
        return "AMD Radeon Graphics"
    return "Intel UHD Graphics" if "i3-" in cpu else "Intel Iris Xe Graphics"


def product_name(
    brand: str,
    series: str,
    screen_size_in: float,
    cpu: str,
    ram_gb: int,
    storage_gb: int,
    gpu: str,
) -> str:
    short_cpu = cpu.removeprefix("Intel Core ").removeprefix("AMD ")
    storage_label = f"{storage_gb // 1024}TB" if storage_gb >= 1024 else f"{storage_gb}GB"
    name = f'{brand} {series} {screen_size_in:g}" {short_cpu}/{ram_gb}GB/{storage_label}'
    if gpu in DEDICATED_GPU_PRICE:
        name += f"/{gpu.removeprefix('NVIDIA GeForce ')}"
    return name


def product_price(
    profile: CategoryProfile,
    cpu_tier: str,
    gpu: str,
    ram_gb: int,
    storage_gb: int,
    storage_type: str,
    rng: random.Random,
) -> float:
    price_per_storage_gb = 0.8 if storage_type == "SSD" else 0.2
    price = (
        profile.base_price
        + CPU_TIER_PRICE[cpu_tier]
        + DEDICATED_GPU_PRICE.get(gpu, 0)
        + ram_gb * 45
        + storage_gb * price_per_storage_gb
    )
    price *= rng.uniform(0.9, 1.12)  # market noise: similar laptops never cost exactly the same
    return float(round(price / 100) * 100 - 1)  # shop-style price, e.g. 4499


def product_weight(profile: CategoryProfile, screen_size_in: float, rng: random.Random) -> float:
    weight = 0.33 * screen_size_in - 3.4 + profile.extra_weight_kg + rng.uniform(-0.1, 0.15)
    return round(max(weight, 0.9), 2)


def product_rating(review_count: int, rng: random.Random) -> float:
    # Few reviews -> extreme ratings are likely; many reviews -> rating settles near the mean.
    spread = 0.9 / math.sqrt(1 + review_count / 15)
    rating = rng.gauss(4.3, spread)
    return round(min(max(rating, 1.0), 5.0), 1)


def main() -> None:
    products = generate_products()
    OUTPUT_PATH.write_text(json.dumps(products, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"Saved {len(products)} products to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
