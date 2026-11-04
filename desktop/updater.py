"""Sistema de verificacao e download automatico de atualizacoes via GitHub Releases.

Repositorio oficial: https://github.com/LeanLopes01/NarizEletr-nico
Comportamento offline: Se nao houver acesso a internet, avisa o usuario na interface
sem bloquear ou impedir o uso normal do programa.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import urllib.error
import urllib.request
import webbrowser
import zipfile
from pathlib import Path

from .qt_compat import QThread, Signal
from .version import (
    GITHUB_API_LATEST_RELEASE,
    GITHUB_API_RELEASES_LIST,
    GITHUB_RAW_VERSION_JSON,
    GITHUB_RELEASES_URL,
    get_local_version,
    is_newer_version,
)

USER_AGENT = "NarizEletronico-Updater/0.4.3 (Arduino-UNO-SCADA)"


def _http_get_json(url: str, timeout: float = 6.0) -> dict | list:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github.v3+json, application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw)


def check_github_for_updates(local_version: str | None = None, timeout: float = 6.0) -> dict:
    """Consulta o repositorio LeanLopes01/NarizEletr-nico em busca de nova versao.

    Retorna um dicionario com:
      - status: 'update_available' | 'up_to_date' | 'offline' | 'error'
      - local_version: str
      - remote_version: str
      - title: str
      - notes: str
      - download_url: str | None
      - asset_name: str | None
      - html_url: str
      - message: str
    """
    local_ver = local_version or get_local_version()
    remote_ver = local_ver
    title = ""
    notes = ""
    download_url: str | None = None
    asset_name: str | None = None
    html_url = GITHUB_RELEASES_URL
    network_reached = False

    # 1. Tenta consultar a ultima Release oficial no GitHub API
    release_obj: dict | None = None
    try:
        data = _http_get_json(GITHUB_API_LATEST_RELEASE, timeout=timeout)
        network_reached = True
        if isinstance(data, dict) and data.get("tag_name"):
            release_obj = data
    except urllib.error.HTTPError as http_err:
        # 404 significa que o repositorio foi alcancado, mas ainda nao possui release publicada
        network_reached = True
        if http_err.code == 404:
            try:
                rel_list = _http_get_json(GITHUB_API_RELEASES_LIST, timeout=timeout)
                if isinstance(rel_list, list) and rel_list:
                    # Procura primeira release com tag semantica ou a mais recente
                    for r in rel_list:
                        if isinstance(r, dict) and r.get("tag_name"):
                            release_obj = r
                            break
            except Exception:
                pass
    except (urllib.error.URLError, TimeoutError, OSError) as net_err:
        return {
            "status": "offline",
            "local_version": local_ver,
            "remote_version": local_ver,
            "title": "",
            "notes": "",
            "download_url": None,
            "asset_name": None,
            "html_url": html_url,
            "message": (
                "Sem acesso à internet para verificar atualizações no GitHub. "
                "O programa continuará funcionando normalmente em modo offline."
            ),
            "detail": str(net_err),
        }

    # Extrai dados da Release se encontrada
    if release_obj:
        tag_name = str(release_obj.get("tag_name", "")).strip()
        if tag_name and tag_name.lower() != "update":
            remote_ver = tag_name.lstrip("vV")
        title = str(release_obj.get("name") or f"Versão {remote_ver}")
        notes = str(release_obj.get("body") or "").strip()
        html_url = str(release_obj.get("html_url") or GITHUB_RELEASES_URL)

        # Prioriza instalador .exe do Inno Setup; se nao houver, usa .zip
        assets = release_obj.get("assets") or []
        exe_asset = None
        zip_asset = None
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            aname = str(asset.get("name", ""))
            burl = str(asset.get("browser_download_url", ""))
            if not burl:
                continue
            if aname.lower().endswith(".exe") and exe_asset is None:
                exe_asset = (aname, burl)
            elif aname.lower().endswith(".zip") and zip_asset is None:
                zip_asset = (aname, burl)

        chosen = exe_asset or zip_asset
        if chosen:
            asset_name, download_url = chosen

    # 2. Consulta tambem o version.json na branch main (padrao atualizacao.py / novaVersao.py)
    try:
        vjson = _http_get_json(GITHUB_RAW_VERSION_JSON, timeout=timeout)
        network_reached = True
        if isinstance(vjson, dict):
            v_main = str(vjson.get("version") or vjson.get("versionSetup") or "").strip()
            if v_main and is_newer_version(v_main, remote_ver):
                remote_ver = v_main
            if not download_url:
                z_url = str(vjson.get("zipUrl") or "").strip()
                if z_url:
                    download_url = z_url
                    asset_name = z_url.rsplit("/", 1)[-1] or "atualizacao.zip"
    except urllib.error.HTTPError:
        network_reached = True
    except (urllib.error.URLError, TimeoutError, OSError) as net_err:
        if not network_reached:
            return {
                "status": "offline",
                "local_version": local_ver,
                "remote_version": local_ver,
                "title": "",
                "notes": "",
                "download_url": None,
                "asset_name": None,
                "html_url": html_url,
                "message": (
                    "Sem acesso à internet para verificar atualizações no GitHub. "
                    "O programa continuará funcionando normalmente em modo offline."
                ),
                "detail": str(net_err),
            }

    if is_newer_version(remote_ver, local_ver):
        return {
            "status": "update_available",
            "local_version": local_ver,
            "remote_version": remote_ver,
            "title": title or f"Nova Versão v{remote_ver}",
            "notes": notes or f"Uma nova versão (v{remote_ver}) está disponível no repositório oficial.",
            "download_url": download_url,
            "asset_name": asset_name,
            "html_url": html_url,
            "message": f"Nova versão disponível: v{remote_ver} (atual: v{local_ver})",
        }

    return {
        "status": "up_to_date",
        "local_version": local_ver,
        "remote_version": remote_ver,
        "title": title,
        "notes": notes,
        "download_url": download_url,
        "asset_name": asset_name,
        "html_url": html_url,
        "message": f"Sistema atualizado (v{local_ver})",
    }


class UpdateCheckWorker(QThread):
    """Thread em segundo plano para verificar atualizacoes sem travar a interface."""

    finished_check = Signal(dict)

    def __init__(self, local_version: str | None = None, manual: bool = False):
        super().__init__()
        self.local_version = local_version
        self.manual = manual

    def run(self):
        result = check_github_for_updates(self.local_version)
        result["manual"] = self.manual
        self.finished_check.emit(result)


class UpdateDownloadWorker(QThread):
    """Thread para baixar o instalador (.exe Inno Setup) ou pacote (.zip) da Release."""

    progress = Signal(int, str)
    download_finished = Signal(str)
    download_failed = Signal(str)

    def __init__(self, download_url: str, asset_name: str | None = None):
        super().__init__()
        self.download_url = download_url
        self.asset_name = asset_name or download_url.rsplit("/", 1)[-1] or "nariz-eletronico-update.exe"

    def run(self):
        try:
            target_dir = Path(tempfile.gettempdir()) / "NarizEletronico_Updates"
            target_dir.mkdir(parents=True, exist_ok=True)
            dest_path = target_dir / self.asset_name

            req = urllib.request.Request(
                self.download_url,
                headers={"User-Agent": USER_AGENT},
            )
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                total_bytes = int(resp.headers.get("Content-Length", 0) or 0)
                downloaded = 0
                chunk_size = 65536
                with open(dest_path, "wb") as out_file:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        out_file.write(chunk)
                        downloaded += len(chunk)
                        if total_bytes > 0:
                            pct = min(100, int((downloaded * 100) / total_bytes))
                            mb_done = downloaded / (1024 * 1024)
                            mb_tot = total_bytes / (1024 * 1024)
                            self.progress.emit(pct, f"Baixando {self.asset_name}: {mb_done:.1f} / {mb_tot:.1f} MB ({pct}%)")
                        else:
                            mb_done = downloaded / (1024 * 1024)
                            self.progress.emit(50, f"Baixando {self.asset_name}: {mb_done:.1f} MB...")

            self.progress.emit(100, f"Download concluído: {dest_path}")
            self.download_finished.emit(str(dest_path))
        except Exception as exc:
            self.download_failed.emit(f"Falha ao baixar atualização: {exc}")


def apply_downloaded_update(file_path: str) -> tuple[bool, str]:
    """Executa o instalador Inno Setup (.exe) ou extrai pacote (.zip) baixado."""
    path = Path(file_path)
    if not path.exists():
        return False, f"Arquivo de atualização não encontrado: {path}"

    try:
        if path.suffix.lower() == ".exe":
            # Inicia o instalador do Inno Setup em processo independente
            subprocess.Popen([str(path)], close_fds=True)
            return True, f"Instalador iniciado: {path.name}"

        if path.suffix.lower() == ".zip":
            extract_dir = path.parent / path.stem
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(path, "r") as zf:
                zf.extractall(extract_dir)
            # Se houver um instalador .exe dentro do zip, executa-o
            exes = list(extract_dir.rglob("*.exe"))
            if exes:
                subprocess.Popen([str(exes[0])], close_fds=True)
                return True, f"Atualizador iniciado: {exes[0].name}"
            # Caso contrario, abre a pasta extraida para o usuario
            if os.name == "nt":
                os.startfile(str(extract_dir))  # type: ignore[attr-defined]
            return True, f"Pacote extraído em: {extract_dir}"

        webbrowser.open(GITHUB_RELEASES_URL)
        return True, "Página de releases aberta no navegador."
    except Exception as exc:
        return False, f"Não foi possível iniciar o instalador: {exc}"
