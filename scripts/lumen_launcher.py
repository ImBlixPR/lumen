"""PyInstaller entry point (the package's __main__ uses relative imports)."""

from lumen.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
