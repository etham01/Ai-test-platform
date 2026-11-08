from __future__ import annotations

import ipaddress
import posixpath
import socket
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from app.core.config import settings

DEFAULT_PORTS = {"http": 80, "https": 443}
DANGEROUS_PATH_WORDS = {
    "logout",
    "signout",
    "sign-out",
    "delete",
    "remove",
    "destroy",
    "download",
}
DANGEROUS_EXTENSIONS = {
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".rar",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".css",
    ".js",
    ".json",
    ".xml",
    ".csv",
    ".exe",
    ".msi",
    ".dmg",
    ".mp4",
    ".mp3",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
}
METADATA_HOSTS = {
    "metadata",
    "metadata.google.internal",
    "metadata.goog",
    "instance-data",
}
METADATA_IPS = {
    ipaddress.ip_address("169.254.169.254"),
    ipaddress.ip_address("100.100.100.200"),
    ipaddress.ip_address("fd00:ec2::254"),
}
TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {"fbclid", "gclid", "yclid", "mc_cid", "mc_eid"}


class URLPolicyError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _normalise_path(path: str) -> str:
    if not path:
        return "/"
    # posixpath.normpath resolves . and .. but keeps a leading slash.
    normalised = posixpath.normpath(path)
    if not normalised.startswith("/"):
        normalised = "/" + normalised
    if normalised != "/":
        normalised = normalised.rstrip("/")
    return normalised or "/"


def normalize_url(url: str, base_url: str | None = None) -> str:
    """Normalise a URL for deduplication and policy checks.

    Removes fragments, default ports, dot segments, duplicate/trailing slashes
    (except root), sorts query parameters, and drops common tracking parameters.
    """
    raw = (url or "").strip()
    if base_url:
        raw = urljoin(base_url, raw)
    if not raw:
        raise URLPolicyError("INVALID_URL", "URL 为空")

    parsed = urlsplit(raw)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise URLPolicyError("INVALID_SCHEME", f"不支持的协议: {scheme or '(空)'}")
    if not parsed.hostname:
        raise URLPolicyError("INVALID_HOST", "URL 缺少主机名")
    if parsed.username or parsed.password:
        raise URLPolicyError("URL_CREDENTIALS", "URL 不能包含用户名或密码")

    host = parsed.hostname.lower()
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise URLPolicyError("INVALID_HOST", "主机名无法编码") from exc

    try:
        port = parsed.port
    except ValueError as exc:
        raise URLPolicyError("INVALID_PORT", "端口非法") from exc
    if port == DEFAULT_PORTS[scheme]:
        port = None

    host_for_netloc = f"[{host}]" if ":" in host and not host.startswith("[") else host
    netloc = host_for_netloc if port is None else f"{host_for_netloc}:{port}"

    query_pairs = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered in TRACKING_QUERY_KEYS or lowered.startswith(TRACKING_QUERY_PREFIXES):
            continue
        query_pairs.append((key, value))
    query_pairs.sort(key=lambda item: (item[0], item[1]))
    query = urlencode(query_pairs, doseq=True)

    return urlunsplit((scheme, netloc, _normalise_path(parsed.path), query, ""))


def origin_of(url: str) -> str:
    parsed = urlsplit(normalize_url(url))
    host = parsed.hostname or ""
    display_host = f"[{host}]" if ":" in host else host
    port = parsed.port
    if port is None:
        return f"{parsed.scheme}://{display_host}"
    return f"{parsed.scheme}://{display_host}:{port}"


def same_origin(left: str, right: str) -> bool:
    try:
        return origin_of(left) == origin_of(right)
    except URLPolicyError:
        return False


def is_dangerous_link(url: str) -> bool:
    raw = (url or "").strip()
    lowered = raw.lower()
    if not raw or lowered.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return True
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return True
    if parsed.scheme and parsed.scheme.lower() not in {"http", "https"}:
        return True
    path = parsed.path.lower()
    if any(part in DANGEROUS_PATH_WORDS for part in path.split("/") if part):
        return True
    return any(path.endswith(ext) for ext in DANGEROUS_EXTENSIONS)


def is_forbidden_ip(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return True
    if ip in METADATA_IPS:
        return True
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
        or not ip.is_global
    )


def resolve_host_ips(host: str, port: int) -> list[str]:
    try:
        direct = ipaddress.ip_address(host)
        return [str(direct)]
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise URLPolicyError("DNS_RESOLUTION_FAILED", f"无法解析主机: {host}") from exc
    ips: list[str] = []
    for info in infos:
        address = info[4][0]
        if address not in ips:
            ips.append(address)
    if not ips:
        raise URLPolicyError("DNS_RESOLUTION_FAILED", f"主机没有可用地址: {host}")
    return ips


@dataclass
class URLPolicy:
    base_url: str
    allowed_origins: list[str] = field(default_factory=list)
    dev_allowed_origins: list[str] = field(default_factory=list)
    resolve_dns: bool = True

    @classmethod
    def for_project(
        cls,
        base_url: str,
        *,
        dev_allowed_origins: list[str] | None = None,
        resolve_dns: bool = True,
    ) -> URLPolicy:
        base = normalize_url(base_url)
        allowed = [origin_of(base)]
        if dev_allowed_origins is None:
            dev_allowed_origins = settings.dev_allowed_origin_list
        return cls(
            base_url=base,
            allowed_origins=allowed,
            dev_allowed_origins=[origin_of(item) for item in dev_allowed_origins],
            resolve_dns=resolve_dns,
        )

    def _is_allowed_origin(self, origin: str) -> bool:
        return origin in self.allowed_origins or origin in self.dev_allowed_origins

    def validate(self, url: str, *, allow_dev: bool = True) -> str:
        try:
            normalized = normalize_url(url)
            parsed = urlsplit(normalized)
            origin = origin_of(normalized)
        except URLPolicyError:
            raise
        except ValueError as exc:
            raise URLPolicyError("INVALID_URL", "URL 非法") from exc

        host = (parsed.hostname or "").lower()
        if host in METADATA_HOSTS:
            raise URLPolicyError("TARGET_NOT_ALLOWED", "云元数据地址被禁止")

        allowed_origins = set(self.allowed_origins)
        if allow_dev:
            allowed_origins.update(self.dev_allowed_origins)
        if origin not in allowed_origins:
            raise URLPolicyError(
                "TARGET_NOT_ALLOWED", f"目标不在授权同源范围内: {origin}"
            )

        port = parsed.port or DEFAULT_PORTS[parsed.scheme]
        is_dev_origin = origin in self.dev_allowed_origins and settings.is_development
        if not self.resolve_dns:
            return normalized

        try:
            literal_ip = ipaddress.ip_address(host)
            ips = [str(literal_ip)]
        except ValueError:
            ips = resolve_host_ips(host, port)

        for address in ips:
            if address in {str(item) for item in METADATA_IPS}:
                raise URLPolicyError("TARGET_NOT_ALLOWED", "云元数据地址被禁止")
            if is_forbidden_ip(address):
                # Development demo site exception is intentionally exact-origin only.
                if is_dev_origin and address in {"127.0.0.1", "::1"}:
                    continue
                raise URLPolicyError(
                    "TARGET_NOT_ALLOWED",
                    f"目标解析到私有/保留地址，已拒绝: {address}",
                )
        return normalized

    def resolve_link(self, href: str, current_url: str) -> str | None:
        """Return a normalised followable URL, or None for unsafe/non-HTML links."""
        if is_dangerous_link(href):
            return None
        try:
            normalized = normalize_url(href, current_url)
            self.validate(normalized)
            return normalized
        except URLPolicyError:
            return None
