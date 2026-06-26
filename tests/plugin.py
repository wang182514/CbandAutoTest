"""
Plugin discovery and registration framework.

Each test module imports `register_test` and decorates its runner function.
On startup, `discover()` scans the `tests` package to populate the registry.
Adding a new test requires zero changes to the UI or runner — just drop a .py
file with `@register_test(...)` into `tests/`.
"""

import importlib
import pkgutil
from typing import Callable, Any

# ── global registry ──────────────────────────────────────────────────

PLUGIN_REGISTRY: dict[str, dict[str, Any]] = {}


# ── decorator ────────────────────────────────────────────────────────

def register_test(
    id: str,
    name: str,
    category: str = "general",
    order: int = 0,
    requires: list[str] | None = None,
    include_in_run_all: bool = True,
) -> Callable:
    """
    Decorator — registers a test function into the global plugin registry.

    Parameters
    ----------
    id : str
        Unique test identifier (e.g. "rx_nf").
    name : str
        Human-readable name shown in the UI (e.g. "RX 噪声系数 + 增益").
    category : str
        Grouping key for the UI button layout ("rx" / "tx" / "general").
    order : int
        Sort order (lower = earlier); used for button layout and run-all sequence.
    requires : list[str] | None
        Optional IDs of prerequisite tests; not yet enforced by the runner.
    include_in_run_all : bool
        If False, this test is excluded when the user clicks "Run All".
        Individual test button still works normally.
    """

    def decorator(fn: Callable):
        PLUGIN_REGISTRY[id] = {
            "id": id,
            "name": name,
            "category": category,
            "order": order,
            "requires": requires or [],
            "include_in_run_all": include_in_run_all,
            "runner": fn,
        }
        return fn

    return decorator


# ── discovery ────────────────────────────────────────────────────────

def discover() -> dict[str, dict[str, Any]]:
    """
    Import every module under the ``tests`` package.  Side-effect: all
    ``@register_test`` decorators fire, populating ``PLUGIN_REGISTRY``.

    Returns
    -------
    dict
        The fully-populated PLUGIN_REGISTRY (same object, also available
        as a module-level variable).
    """
    import tests as _pkg

    for _, mod_name, _ in pkgutil.iter_modules(_pkg.__path__):
        # skip plugin itself and base
        if mod_name in ("plugin", "base"):
            continue
        importlib.import_module(f"tests.{mod_name}")

    return PLUGIN_REGISTRY
