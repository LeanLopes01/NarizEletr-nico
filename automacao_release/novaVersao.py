"""Script de deploy de nova versao e instalador Inno Setup para o GitHub Releases.

Baseado em: C:\ProjetoTablepRPG\Outros\AtualizacaoAutomatica\novaVersao.py
Repositorio: https://github.com/LeanLopes01/NarizEletr-nico
Nota: Execute apenas quando quiser compilar o instalador Inno Setup e publicar uma Release.
"""
from __future__ import annotations

import base64
import json
import os
import re
import subprocess
from pathlib import Path
import requests

from notas_utils import (
    PROJECT_ROOT,
    ler_notas_md,
    ler_versao_projeto,
    limpar_notas_md,
    obter_github_token,
    obter_titulo_versao,
    publicar_notas_versao,
)

ARQUIVO_VERSION_JSON = PROJECT_ROOT / "version.json"
ARQUIVO_SCRIPT_INNO = PROJECT_ROOT / "instalador_inno_setup.iss"
PASTA_DIST_EXE = PROJECT_ROOT / "dist" / "NarizEletronico"
PASTA_OUTPUT = PROJECT_ROOT / "Output"

CANDIDATOS_INNO = [
    Path(r"C:\Program Files\Inno Setup 7\ISCC.exe"),
    Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
    Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
]

REPO_OWNER = "LeanLopes01"
REPO_NAME = "NarizEletr-nico"
BRANCH_NAME = "main"
UPDATE_RELEASE_TAG = "Update"
UPDATE_ZIP_NAME = "atualizacao.zip"


def localizar_iscc() -> Path | None:
    for p in CANDIDATOS_INNO:
        if p.exists():
            return p
    return None


def main():
    print("Iniciando automacao de Deploy do Instalador Nariz Eletronico...\n")

    versao_atual = ler_versao_projeto()
    print(f"Versao lida em version.json: {versao_atual}")

    if not (PASTA_DIST_EXE / "NarizEletronico.exe").exists():
        print(
            f"AVISO: O executavel ainda nao foi compilado em {PASTA_DIST_EXE / 'NarizEletronico.exe'}.\n"
            "Quando estiver pronto para gerar o .exe, rode primeiro: gerar_exe_pyinstaller.bat"
        )
        return

    conteudo_notas = ler_notas_md()
    titulo_versao = obter_titulo_versao(versao_atual) if conteudo_notas else None

    setup_name = f"nariz-eletronico-{versao_atual}-setup.exe"
    caminho_setup_final = PASTA_OUTPUT / setup_name
    PASTA_OUTPUT.mkdir(parents=True, exist_ok=True)

    for old_file in PASTA_OUTPUT.glob("nariz-eletronico-*-setup.exe"):
        try:
            old_file.unlink()
        except Exception:
            pass

    # Atualiza a versao no script .iss
    conteudo_iss = ARQUIVO_SCRIPT_INNO.read_text(encoding="utf-8")
    novo_iss = re.sub(
        r'#define MyAppVersion\s+".*"',
        f'#define MyAppVersion "{versao_atual}"',
        conteudo_iss,
    )
    ARQUIVO_SCRIPT_INNO.write_text(novo_iss, encoding="utf-8")

    iscc = localizar_iscc()
    if iscc is None:
        print("ERRO: Compilador ISCC.exe do Inno Setup nao encontrado.")
        return

    print(f"Compilando instalador via Inno Setup ({iscc})...")
    res = subprocess.run([str(iscc), str(ARQUIVO_SCRIPT_INNO)], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"ERRO no Inno Setup:\n{res.stderr}")
        return
    print(f"OK: Instalador {setup_name} compilado!")

    token = obter_github_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    release_tag = f"v{versao_atual}"
    api_release_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/tags/{release_tag}"
    r_release = requests.get(api_release_url, headers=headers, timeout=20)

    if r_release.status_code == 200:
        release_data = r_release.json()
    else:
        api_create_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases"
        corpo_release = conteudo_notas or f"Release oficial v{versao_atual} do Nariz Eletronico (Arduino UNO R3)."
        nova_release = {
            "tag_name": release_tag,
            "name": titulo_versao or f"E-Nose Control & Analytics v{versao_atual}",
            "body": corpo_release,
            "draft": False,
            "prerelease": False,
        }
        r_create = requests.post(api_create_url, headers=headers, json=nova_release, timeout=20)
        if r_create.status_code != 201:
            print("ERRO ao criar release:", r_create.json())
            return
        release_data = r_create.json()

    for asset in release_data.get("assets", []):
        if asset["name"].endswith(".exe"):
            requests.delete(asset["url"], headers=headers, timeout=20)

    upload_base_url = release_data["upload_url"].split("{")[0]
    headers_upload = headers.copy()
    headers_upload["Content-Type"] = "application/octet-stream"
    print(f"Enviando {setup_name} para a Release {release_tag}...")
    with open(caminho_setup_final, "rb") as f:
        r_up = requests.post(f"{upload_base_url}?name={setup_name}", headers=headers_upload, data=f, timeout=180)
    if r_up.status_code != 201:
        print("ERRO no upload do instalador:", r_up.json())
        return
    print("OK: Instalador enviado para o GitHub Releases!")

    # Atualiza version.json local e remoto
    url_zip = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/download/{UPDATE_RELEASE_TAG}/{UPDATE_ZIP_NAME}"
    dados_json = {
        "version": versao_atual,
        "versionSetup": versao_atual,
        "repoOwner": REPO_OWNER,
        "repoName": REPO_NAME,
        "releaseTag": release_tag,
        "zipUrl": url_zip,
        "installerName": setup_name,
    }
    json_str = json.dumps(dados_json, indent=2)
    ARQUIVO_VERSION_JSON.write_text(json_str + "\n", encoding="utf-8")

    api_contents_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/version.json"
    sha_atual = None
    r_get = requests.get(api_contents_url, headers=headers, timeout=15)
    if r_get.status_code == 200:
        sha_atual = r_get.json().get("sha")

    commit_data = {
        "message": f"Update version.json to {versao_atual} via deploy automatico (Instalador)",
        "content": base64.b64encode(json_str.encode("utf-8")).decode("utf-8"),
        "branch": BRANCH_NAME,
    }
    if sha_atual:
        commit_data["sha"] = sha_atual

    r_put = requests.put(api_contents_url, headers=headers, json=commit_data, timeout=20)
    if r_put.status_code in (200, 201):
        print("OK: version.json atualizado na branch main!")

    if conteudo_notas and titulo_versao:
        publicar_notas_versao(headers, REPO_OWNER, REPO_NAME, BRANCH_NAME, versao_atual, titulo_versao, conteudo_notas)
        limpar_notas_md()

    print("\nSUCESSO TOTAL! Instalador compilado, release publicada e repositorio atualizado.")


if __name__ == "__main__":
    main()
