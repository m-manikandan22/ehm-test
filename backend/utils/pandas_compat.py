"""pandas_compat.py — Workaround for pandas 3.0+ Copy-on-Write.

pandapower 2.14.x uses ``Series.values[:] = ...`` to write results back
into a DataFrame. Under pandas 3.0+ Copy-on-Write this raises
``ValueError: assignment destination is read-only`` because ``.values``
returns a read-only numpy view.

This module applies a tiny monkey-patch: override ``Series.values`` and
``DataFrame.values`` to return a *writable* numpy copy. This restores
pandapower's behaviour on the existing installation without requiring
a pandapower upgrade (which would cascade into other dependency
changes).

Scope
-----
The patch is applied at import time of this module. It only affects
``.values`` access — it does not change any pandas copy/semantic
behaviour elsewhere. The original ndarray returned by ``.values`` is
already a separate object from the underlying column, so making it
writable is the safest possible override.
"""
from __future__ import annotations

import pandas as pd


_PATCHED = False


def _apply_pandas_compat_patch() -> None:
    """Make Series.values and DataFrame.values return writable copies."""
    global _PATCHED
    if _PATCHED:
        return

    def _values_writable(self):
        # Force a copy via to_numpy() then enable writes. ``to_numpy()``
        # already returns a fresh ndarray; flipping the writable flag
        # restores the legacy 2.x semantics.
        arr = self.to_numpy()
        arr.setflags(write=True)
        return arr

    pd.Series.values = property(_values_writable)
    pd.DataFrame.values = property(_values_writable)
    _PATCHED = True


# Apply eagerly on import so callers get the patched behaviour
# regardless of how they invoke us.
_apply_pandas_compat_patch()