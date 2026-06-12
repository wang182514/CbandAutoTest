"""
Configuration manager — loads/saves settings from JSON file.
Provides dotted access to nested dicts via __getattr__ on dict nodes.
"""

import json
import os
from copy import deepcopy
from typing import Any


class _ConfigNode(dict):
    """A dict that allows attribute-style access recursively."""

    def __getitem__(self, key):
        val = super().__getitem__(key)
        if isinstance(val, dict) and not isinstance(val, _ConfigNode):
            val = _ConfigNode(val)
            super().__setitem__(key, val)
        return val

    def __getattr__(self, key: str) -> Any:
        if key in self:
            return self[key]
        raise AttributeError(f"No such key: {key}")

    def __setattr__(self, key: str, value: Any):
        self[key] = value

    def __delattr__(self, key: str):
        if key in self:
            del self[key]
        else:
            raise AttributeError(f"No such key: {key}")


class ConfigManager:
    """Loads, holds, and saves configuration as a nested _ConfigNode."""

    def __init__(self, defaults_path: str = None):
        self._defaults_path = defaults_path
        self._file_path: str | None = None
        self._data: _ConfigNode = _ConfigNode()
        if defaults_path and os.path.exists(defaults_path):
            self._load_from(defaults_path)

    # ---- load / save -------------------------------------------------------

    def load(self, path: str):
        """Deep-merge a user settings file on top of current data."""
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        self._deep_merge(self._data, raw)
        self._file_path = path

    def save(self, path: str = None):
        """Save current config to `path` (or the last loaded path)."""
        target = path or self._file_path
        if target is None:
            raise ValueError("No save path specified.")
        os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
        with open(target, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, ensure_ascii=False, indent=4)
        self._file_path = target

    def reload(self):
        """Reload from the last loaded file."""
        if self._file_path:
            self._load_from(self._file_path)

    # ---- access ------------------------------------------------------------

    def __getattr__(self, key: str) -> Any:
        """Delegate attribute access to the internal _ConfigNode."""
        # __getattr__ is only called when normal lookup fails, so 'data'
        # (a property) and other real attrs are found first.
        if key.startswith("_"):
            raise AttributeError(key)
        if key in self._data:
            val = self._data[key]
            if isinstance(val, dict) and not isinstance(val, _ConfigNode):
                val = _ConfigNode(val)
                self._data[key] = val
            return val
        raise AttributeError(f"No such config key: {key}")

    def __setattr__(self, key: str, value: Any):
        """Route attribute-like writes into _data for top-level keys."""
        if key.startswith("_") or hasattr(type(self), key):
            super().__setattr__(key, value)
        elif key in self._data:
            self._data[key] = value
        else:
            super().__setattr__(key, value)

    @property
    def data(self) -> _ConfigNode:
        return self._data

    def get(self, dotted_key: str, default=None):
        """Convenience: cfg.get('instruments.rx_power_supply.ip')."""
        node = self._data
        for part in dotted_key.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return default
        return node

    def set(self, dotted_key: str, value):
        """Convenience: cfg.set('serial_number', 'SN001')."""
        parts = dotted_key.split(".")
        node = self._data
        for part in parts[:-1]:
            if part not in node or not isinstance(node[part], dict):
                node[part] = _ConfigNode()
            node = node[part]
        node[parts[-1]] = value

    # ---- internals ---------------------------------------------------------

    def _load_from(self, path: str):
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        self._data = _ConfigNode(raw)

    @staticmethod
    def _deep_merge(base: dict, overlay: dict):
        """Recursively merge overlay into base in-place."""
        for key, val in overlay.items():
            if key in base and isinstance(base[key], dict) and isinstance(val, dict):
                ConfigManager._deep_merge(base[key], val)
            else:
                base[key] = val

    def __repr__(self):
        return f"<ConfigManager file={self._file_path!r}>"
