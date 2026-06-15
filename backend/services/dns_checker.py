"""DNS validation for SPF, DKIM, and DMARC records."""
import dns.resolver
from dataclasses import dataclass
from backend.services.provider_presets import PROVIDER_PRESETS


DKIM_SELECTORS = {
    "gmail": ["20230601", "20210112", "20251104", "google"],
    "outlook": ["selector1", "selector2"],
    "yahoo": ["s1024", "s2048"],
    "seznam": ["default", "beta"],
    "mailcz": ["default"],
    "zoho": ["zoho"],
    "sendgrid": ["s1", "s2"],
    "mailgun": ["default", "smtp"],
    "ses": ["default"],
    "icloud": ["sig1"],
}

COMMON_SELECTORS = [
    "default", "dkim", "mail", "mx", "mx2", "selector1", "selector2",
    "s1", "s2", "k1", "google", "zoho", "smtp", "sig1",
]


@dataclass
class DnsCheckResult:
    record_type: str  # spf, dkim, dmarc
    status: str       # ok, missing
    current_value: str | None = None
    suggestion: str | None = None


def check_spf(domain: str) -> DnsCheckResult:
    """Check if SPF record exists."""
    try:
        answers = dns.resolver.resolve(domain, "TXT")
        for rdata in answers:
            txt = str(rdata).strip('"')
            if txt.startswith("v=spf1"):
                return DnsCheckResult("spf", "ok", current_value=txt)
    except Exception:
        pass
    return DnsCheckResult("spf", "missing")


def check_dkim(domain: str, provider_type: str = None) -> DnsCheckResult:
    """Check if DKIM record exists, trying provider-specific and common selectors."""
    selectors = DKIM_SELECTORS.get(provider_type, [])
    if not selectors:
        selectors = COMMON_SELECTORS

    for selector in selectors:
        dkim_domain = f"{selector}._domainkey.{domain}"
        try:
            answers = dns.resolver.resolve(dkim_domain, "TXT")
            for rdata in answers:
                txt = str(rdata).strip('"')
                if "v=DKIM1" in txt or "p=" in txt:
                    return DnsCheckResult("dkim", "ok",
                                          current_value=f"selector={selector}")
        except Exception:
            pass
        try:
            answers = dns.resolver.resolve(dkim_domain, "CNAME")
            if answers:
                target = str(answers[0]).rstrip(".")
                return DnsCheckResult("dkim", "ok",
                                      current_value=f"selector={selector} (CNAME → {target})")
        except Exception:
            pass

    return DnsCheckResult("dkim", "missing",
                          suggestion="No DKIM record found. Check your domain's DKIM selector.")


def check_dmarc(domain: str) -> DnsCheckResult:
    """Check if DMARC record exists."""
    try:
        answers = dns.resolver.resolve(f"_dmarc.{domain}", "TXT")
        for rdata in answers:
            txt = str(rdata).strip('"')
            if txt.startswith("v=DMARC1"):
                return DnsCheckResult("dmarc", "ok", current_value=txt)
    except Exception:
        pass
    return DnsCheckResult("dmarc", "missing")


def check_domain(domain: str, provider_type: str = None) -> list[DnsCheckResult]:
    """Run all DNS checks for a domain."""
    return [
        check_spf(domain),
        check_dkim(domain, provider_type),
        check_dmarc(domain),
    ]