"""Adapter Layer : capture des trames et fichiers depuis le canal physique."""

from bridge_core.adapter.base import BaseAdapter, RawFrame, adapter_registry

__all__ = ["BaseAdapter", "RawFrame", "adapter_registry"]
