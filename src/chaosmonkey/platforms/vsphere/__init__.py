"""VMware vSphere platform integration."""

from .client import VSpherePlatform
from .discovery import VSphereDiscovery

__all__ = ["VSpherePlatform", "VSphereDiscovery"]
