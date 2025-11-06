"""ChaosMonkey CLI package."""

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:
    __version__ = version("chaosmonkey-cli")
except PackageNotFoundError:  # pragma: no cover - during local dev without install
    __version__ = "0.0.0"
