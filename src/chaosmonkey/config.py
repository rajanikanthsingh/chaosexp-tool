"""Configuration helpers for ChaosMonkey."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency for YAML
    yaml = None  # type: ignore

DEFAULT_CONFIG_FILENAMES = ("chaosmonkey.yaml", "chaosmonkey.yml", "chaosmonkey.json")

# Load environment variables from .env file
load_dotenv()

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Debug: Log loaded environment variables
logger.debug("Loaded NOMAD_ADDR: %s", os.getenv("NOMAD_ADDR"))
logger.debug("Loaded NOMAD_TOKEN: %s", os.getenv("NOMAD_TOKEN"))
logger.debug("Loaded NOMAD_REGION: %s", os.getenv("NOMAD_REGION"))
logger.debug("Loaded NOMAD_NAMESPACE: %s", os.getenv("NOMAD_NAMESPACE"))


@dataclass
class NomadSettings:
    """Nomad connection configuration."""

    address: str = field(default_factory=lambda: os.getenv("NOMAD_ADDR", "http://127.0.0.1:4646"))
    region: Optional[str] = field(default_factory=lambda: os.getenv("NOMAD_REGION"))
    token: Optional[str] = field(default_factory=lambda: os.getenv("NOMAD_TOKEN"))
    namespace: Optional[str] = field(default_factory=lambda: os.getenv("NOMAD_NAMESPACE"))


@dataclass
class OLVMSettings:
    """OLVM/oVirt platform configuration."""
    
    url: Optional[str] = field(default_factory=lambda: os.getenv("OLVM_URL"))
    username: Optional[str] = field(default_factory=lambda: os.getenv("OLVM_USERNAME"))
    password: Optional[str] = field(default_factory=lambda: os.getenv("OLVM_PASSWORD"))
    ca_file: Optional[str] = field(default_factory=lambda: os.getenv("OLVM_CA_FILE"))
    insecure: bool = field(default_factory=lambda: os.getenv("OLVM_INSECURE", "false").lower() == "true")


@dataclass
class VSphereSettings:
    """VMware vSphere platform configuration."""
    
    server: Optional[str] = field(default_factory=lambda: os.getenv("VSPHERE_SERVER"))
    username: Optional[str] = field(default_factory=lambda: os.getenv("VSPHERE_USERNAME"))
    password: Optional[str] = field(default_factory=lambda: os.getenv("VSPHERE_PASSWORD"))
    port: int = field(default_factory=lambda: int(os.getenv("VSPHERE_PORT", "443")))
    insecure: bool = field(default_factory=lambda: os.getenv("VSPHERE_INSECURE", "true").lower() == "true")


@dataclass
class DoraSettings:
    """Dora API configuration."""
    
    host: str = field(default_factory=lambda: os.getenv("DORA_HOST", "hostname"))
    api_port: int = field(default_factory=lambda: int(os.getenv("DORA_API_PORT", "8000")))
    auth_port: int = field(default_factory=lambda: int(os.getenv("DORA_AUTH_PORT", "51051")))
    username: Optional[str] = field(default_factory=lambda: os.getenv("DORA_USERNAME"))
    password: Optional[str] = field(default_factory=lambda: os.getenv("DORA_PASSWORD"))


@dataclass
class PrometheusSettings:
    """Prometheus monitoring configuration."""
    
    url: str = field(default_factory=lambda: os.getenv(
        "PROMETHEUS_URL"
    ))
    timeout: int = field(default_factory=lambda: int(os.getenv("PROMETHEUS_TIMEOUT", "10")))


@dataclass
class PlatformSettings:
    """Virtualization platform configurations."""
    
    olvm: OLVMSettings = field(default_factory=OLVMSettings)
    vsphere: VSphereSettings = field(default_factory=VSphereSettings)
    dora: DoraSettings = field(default_factory=DoraSettings)


@dataclass(slots=True)
class ChaosToolkitSettings:
    """Chaos Toolkit execution configuration."""

    experiments_path: Path = Path("experiments")
    reports_path: Path = Path("reports")
    dry_run: bool = False


@dataclass
class Settings:
    """Aggregate configuration for the CLI."""

    nomad: NomadSettings = field(default_factory=NomadSettings)
    chaos: ChaosToolkitSettings = field(default_factory=ChaosToolkitSettings)
    platforms: PlatformSettings = field(default_factory=PlatformSettings)
    prometheus: PrometheusSettings = field(default_factory=PrometheusSettings)


def load_settings(config_path: Optional[Path]) -> Settings:
    """Load settings from file or return defaults."""
    if config_path is None:
        config_path = _auto_discover_config()

    if config_path and config_path.exists():
        data = _parse_config_file(config_path)
        return _settings_from_dict(data)

    return Settings()


def _auto_discover_config() -> Optional[Path]:
    cwd = Path.cwd()
    for name in DEFAULT_CONFIG_FILENAMES:
        candidate = cwd / name
        if candidate.exists():
            return candidate
    return None


def _parse_config_file(path: Path) -> Dict[str, Any]:
    text = path.read_text()
    if path.suffix.lower() == ".json":
        return json.loads(text)

    if path.suffix.lower() in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError(
                "PyYAML is required to parse YAML configuration files but is not installed."
            )
        return yaml.safe_load(text) or {}

    raise ValueError(f"Unsupported configuration format: {path.suffix}")


def _settings_from_dict(payload: Dict[str, Any]) -> Settings:
    nomad_cfg = payload.get("nomad", {})
    chaos_cfg = payload.get("chaos", {})
    platforms_cfg = payload.get("platforms", {})

    default_nomad = NomadSettings()
    default_chaos = ChaosToolkitSettings()
    default_platforms = PlatformSettings()

    # Parse OLVM settings
    olvm_cfg = platforms_cfg.get("olvm", {})
    olvm = OLVMSettings(
        url=olvm_cfg.get("url", default_platforms.olvm.url),
        username=olvm_cfg.get("username", default_platforms.olvm.username),
        password=olvm_cfg.get("password", default_platforms.olvm.password),
        ca_file=olvm_cfg.get("ca_file", default_platforms.olvm.ca_file),
        insecure=olvm_cfg.get("insecure", default_platforms.olvm.insecure),
    )
    
    # Parse vSphere settings
    vsphere_cfg = platforms_cfg.get("vsphere", {})
    vsphere = VSphereSettings(
        server=vsphere_cfg.get("server", default_platforms.vsphere.server),
        username=vsphere_cfg.get("username", default_platforms.vsphere.username),
        password=vsphere_cfg.get("password", default_platforms.vsphere.password),
        port=vsphere_cfg.get("port", default_platforms.vsphere.port),
        insecure=vsphere_cfg.get("insecure", default_platforms.vsphere.insecure),
    )
    
    # Parse Dora settings
    dora_cfg = platforms_cfg.get("dora", {})
    dora = DoraSettings(
        host=dora_cfg.get("host", default_platforms.dora.host),
        api_port=dora_cfg.get("api_port", default_platforms.dora.api_port),
        auth_port=dora_cfg.get("auth_port", default_platforms.dora.auth_port),
        username=dora_cfg.get("username", default_platforms.dora.username),
        password=dora_cfg.get("password", default_platforms.dora.password),
    )
    
    # Parse Prometheus settings
    prometheus_cfg = payload.get("prometheus", {})
    default_prometheus = PrometheusSettings()
    prometheus = PrometheusSettings(
        url=prometheus_cfg.get("url", default_prometheus.url),
        timeout=prometheus_cfg.get("timeout", default_prometheus.timeout),
    )

    settings = Settings(
        nomad=NomadSettings(
            address=nomad_cfg.get("address", default_nomad.address),
            region=nomad_cfg.get("region", default_nomad.region),
            token=nomad_cfg.get("token", default_nomad.token),
            namespace=nomad_cfg.get("namespace", default_nomad.namespace),
        ),
        chaos=ChaosToolkitSettings(
            experiments_path=Path(chaos_cfg.get("experiments_path", default_chaos.experiments_path)),
            reports_path=Path(chaos_cfg.get("reports_path", default_chaos.reports_path)),
            dry_run=bool(chaos_cfg.get("dry_run", default_chaos.dry_run)),
        ),
        platforms=PlatformSettings(
            olvm=olvm,
            vsphere=vsphere,
            dora=dora,
        ),
        prometheus=prometheus,
    )
    return settings
