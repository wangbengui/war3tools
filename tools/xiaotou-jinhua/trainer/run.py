#!/usr/bin/env python3
"""Entry point for dev / PyInstaller."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.app import main

if __name__ == "__main__":
    main()
