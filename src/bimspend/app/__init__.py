"""BIMSpend desktop application shell.

A tkinter-based Windows desktop application providing the Build 01+
user interface over the BIMSpend domain layer.

Architecture: composition, not merger.
- Domain layer (models, db, adapters, correlation, review, dashboard)
  is shared with the CLI runner and any future integrations.
- GUI layer is thin: it calls domain methods and displays results.
- No real employee data, no monitoring, no production deployment.
"""

from .main import main

__all__ = ["main"]
