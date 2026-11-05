"""Frozen Windows preview entry point. Synthetic fixtures only."""
from pathlib import Path
import os
from bimspend.app.shell import BIMSpendApp


def main() -> None:
    local_data = os.environ.get("LOCALAPPDATA")
    if not local_data:
        raise RuntimeError("LOCALAPPDATA is required for the Windows preview.")
    data_dir = Path(local_data) / "BIMSpend" / "preview"
    data_dir.mkdir(parents=True, exist_ok=True)
    app = BIMSpendApp(db_path=str(data_dir / "bimspend.db"))
    app.run()


if __name__ == "__main__":
    main()
