from pathlib import Path

# 127.0.0.1, not localhost: on Windows "localhost" tries IPv6 first and the Flask dev server
# listens on IPv4 only, which adds about 2 s to every new connection made by requests.
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output"
DEFAULT_OUTPUT = OUTPUT_DIR / "laptops"

MIN_REQUEST_DELAY_SECONDS = 0.5
REQUEST_DELAY_SECONDS = 0.6
WAIT_TIMEOUT_SECONDS = 15
END_OF_LIST_QUIET_SECONDS = 1.5
MAX_ATTEMPTS = 5
RETRY_BASE_DELAY_SECONDS = 1.0
RETRY_MAX_DELAY_SECONDS = 30.0
CHECKPOINT_EVERY_PRODUCTS = 10

# NBP table A no. 200/A/NBP/2026 published 2026-10-14
RATES_TO_PLN = {"PLN": 1.0, "EUR": 4.3706, "USD": 3.9042}
RATES_SOURCE = "NBP, tabela A nr 200/A/NBP/2026 z 2026-10-14"
