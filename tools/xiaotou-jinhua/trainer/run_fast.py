#!/usr/bin/env python3
"""快速版入口：多线程智能扫描。"""

import os
import sys
from pathlib import Path

os.environ["XTJH_FAST"] = "1"

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.app import main

if __name__ == "__main__":
    main()
