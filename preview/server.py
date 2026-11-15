#!/usr/bin/env python3
"""
Preview server for Market Structure Notes web viewer.
This is the entrypoint used by the Starchild preview system.
"""

import sys
from pathlib import Path

# Add parent to path so we can import msn.cli
sys.path.insert(0, str(Path(__file__).parent.parent))

from msn.cli import create_app
import uvicorn

# Served behind the Starchild preview proxy, so the public Host name isn't
# known here; skip the Host allowlist (cross-site write checks still apply).
app = create_app(allowed_hosts=None)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)