#!/usr/bin/env python3
"""Launch 小偷进化 memory trainer GUI."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.app import main

if __name__ == "__main__":
    main()
