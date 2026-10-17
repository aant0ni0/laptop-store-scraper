import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Checkpoint:
    """Progress saved to disk so an interrupted run can resume with --resume."""

    path: Path
    page_count: int | None = None
    catalog_pages: dict[int, list[dict]] = field(default_factory=dict)
    details: dict[int, dict] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "Checkpoint":
        if not path.exists():
            return cls(path)
        data = json.loads(path.read_text("utf-8"))
        return cls(
            path=path,
            page_count=data.get("page_count"),
            catalog_pages={int(page): rows for page, rows in data["catalog_pages"].items()},
            details={int(product_id): row for product_id, row in data["details"].items()},
        )

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "page_count": self.page_count,
            "catalog_pages": self.catalog_pages,
            "details": self.details,
        }
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False), "utf-8")
        temporary.replace(self.path)
