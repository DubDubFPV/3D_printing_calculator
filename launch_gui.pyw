"""Double-click launcher for the 3D Slicer Screenshot Calculator GUI."""

from __future__ import annotations

import os
import sys
from pathlib import Path


if __name__ == "__main__":
    project_dir = Path(__file__).resolve().parent
    if str(project_dir) not in sys.path:
        sys.path.insert(0, str(project_dir))

    os.environ.setdefault("SLICER_DEBUG", "1")

    from gui_calculator import main

    main()
