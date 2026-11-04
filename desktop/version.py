"""Informacoes de versao e repositorio oficial do Nariz Eletronico para Auto-Update."""
from __future__ import annotations

import json
from pathlib import Path

APP_NAME = "E-Nose Control & Analytics"
APP_VERSION = "0.4.3"
GITHUB_OWNER = "LeanLopes01"
GITHUB_REPO = "NarizEletr-nico"
GITHUB_BRANCH = "main"

GITHUB_REPO_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}"
GITHUB_RELEASES_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
GITHUB_API_LATEST_RELEASE = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
GITHUB_API_RELEASES_LIST = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
GITHUB_RAW_VERSION_JSON = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/version.json"


def get_local_version() -> str:
    """Retorna a versao atual lendo o version.json local (ou APP_VERSION como fallback)."""
    candidates = [
        Path(__file__).resolve().parent.parent / "version.json",
        Path.cwd() / "version.json",
    ]
    for path in candidates:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                ver = str(data.get("version", "")).strip()
                if ver:
                    return ver
            except Exception:
                pass
    return APP_VERSION


def parse_version_tuple(version_str: str) -> tuple[int, ...]:
    """Converte strings como 'v0.4.3' ou '0.4.3.1' em tupla numerica comparavel (0, 4, 3)."""
    clean = version_str.strip().lstrip("vV")
    parts: list[int] = []
    for token in clean.replace("-", ".").split("."):
        digits = "".join(ch for ch in token if ch.isdigit())
        if digits:
            parts.append(int(digits))
    return tuple(parts) if parts else (0,)


def is_newer_version(remote_version: str, local_version: str | None = None) -> bool:
    """Retorna True se remote_version for estritamente mais recente que local_version."""
    local_ver = local_version or get_local_version()
    r_tup = parse_version_tuple(remote_version)
    l_tup = parse_version_tuple(local_ver)
    max_len = max(len(r_tup), len(l_tup))
    r_pad = r_tup + (0,) * (max_len - len(r_tup))
    l_pad = l_tup + (0,) * (max_len - len(l_tup))
    return r_pad > l_pad
