"""Application entry point.

Launches the BIMSpend desktop application with the synthetic-data
domain layer. Real ActivityWatch/Miru/Revit adapters can be swapped
in through the adapter interfaces in src/bimspend/adapters/base.py.

Usage:
    python -m bimspend.app.main
"""

from .shell import BIMSpendApp


def main():
    app = BIMSpendApp()
    app.run()


if __name__ == "__main__":
    main()
