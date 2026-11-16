"""Conservative source eligibility gate; not a substitute for external verification."""
from dataclasses import dataclass
from urllib.parse import urlparse
import ipaddress

@dataclass(frozen=True)
class ValidationResult:
    eligible: bool
    reasons: tuple[str, ...]

def validate_public_https_url(url: str) -> ValidationResult:
    p = urlparse(url)
    reasons = []
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        reasons.append("absolute HTTPS URL without credentials required")
    host = p.hostname or ""
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        reasons.append("local hosts forbidden")
    try:
        if not ipaddress.ip_address(host).is_global:
            reasons.append("non-public IP forbidden")
    except ValueError:
        pass
    return ValidationResult(not reasons, tuple(reasons))

# DNS resolution, redirect chains, robots/policies and live provider quality
# must be checked by the isolated connector runner before approval.
