"""Launch the Algominds Momentum Pacer tearsheet.

The production service HC-AGM-Public starts
``C:\\HC\\apps\\agm\\start_agm.py``. That deployed copy calls ``runpy`` with
an absolute path. This repository copy resolves ``Momentum Pacer/mp_ts.py``
beside this file, which is the same directory layout.
"""

from __future__ import annotations

import runpy
from pathlib import Path


def momentum_pacer_script() -> Path:
    return Path(__file__).resolve().parent / "Momentum Pacer" / "mp_ts.py"


if __name__ == "__main__":
    runpy.run_path(str(momentum_pacer_script()), run_name="__main__")
