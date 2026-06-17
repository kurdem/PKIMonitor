"""Pytest configuration.

Sets an isolated SQLite database *before* the application is imported, so the
module-level settings/engine singletons bind to the test database.
"""

import os
import tempfile

# Must run at import time, before any `app.*` import happens.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["RUN_CHECKS_ON_STARTUP"] = "false"
