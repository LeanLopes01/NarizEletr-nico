"""Script de deploy rapido por pacote .zip para o Auto-Updater do Nariz Eletronico.

Baseado em: C:\ProjetoTablepRPG\Outros\AtualizacaoAutomatica\atualizacao.py
Repositorio: https://github.com/LeanLopes01/NarizEletr-nico
"""
from __future__ import annotations

import base64
import json
import shutil
from pathlib import Path
import requests

from notas_utils import (
    PROJECT_ROOT,
    ler_notas_md,
    ler_versao_projeto,
    limpar_notas_md,
    obter_github_token,
    obter_titulo_versao,
    obter_version_setup_atual,
    publicar_notas_versao,
)

PASTA_BUILD = PROJECT_ROOT / "dist" / "NarizEletronico"
CAMINHO_ZIP_BASE = PROJECT_ROOT / "Output" / "atualizacao"
ARQUIVO_VERSION_JSON = PROJECT_ROOT / "version.json"

REPO_OWNER = "LeanLopes01"
REPO_NAME = "NarizEletr-nico"
RELEASE_TAG = "Update"
ZIP_NAME = "atualizacao.zip"
BRANCH_NAME = "main"


def main():
    print("Iniciando automacao de Deploy Rapido (.zip) do Nariz Eletronico...\n")
    versao_atual = ler_versao_projeto()
    print(f"Versao atual: {versao_atual}")

    if not PASTA_BUILD.exists():
        print(
            f"AVISO: A pasta de build {PASTA_BUILD} ainda nao existe.\n"
            "Quando quiser gerar o .exe, execute gerar_exe_pyinstaller.bat primeiro."
        )
        return

    conteudo_notas = ler_notas_md()
    titulo_versao = obter_titulo_versao(versao_atual) if conteudo_notas else None

    CAMINHO_ZIP_BASE.parent.mkdir(parents=True, exist_ok=True)
    arquivo_zip = shutil.make_archive(str(CAMINHO_ZIP_BASE), "zip", str(PASTA_BUILD))
    print(f"OK: Pacote compactado em {arquivo_zip}")

    token = obter_github_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    url_zip = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/download/{RELEASE_TAG}/{ZIP_NAME}"
    version_setup = obter_version_setup_atual(headers, REPO_OWNER, REPO_NAME, BRANCH_NAME, fallback=versao_atual)
    dados_json = {
        "version": versao_atual,
        "versionSetup": version_setup,
        "repoOwner": REPO_OWNER,
        "repoName": REPO_NAME,
        "releaseTag": f"v{versao_atual}",
        "zipUrl": url_zip,
        "installerName": f"nariz-eletronico-{version_setup}-setup.exe",
    }
    json_str = json.dumps(dados_json, indent=2)
    ARQUIVO_VERSION_JSON.write_text(json_str + "\n", encoding="utf-8")

    # Garante que a release 'Update' exista
    api_rel_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/tags/{RELEASE_TAG}"
    r_rel = requests.get(api_rel_url, headers=headers, timeout=20)
    if r_rel.status_code == 200:
        release_data = r_rel.json()
    else:
        r_create = requests.post(
            f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases",
            headers=headers,
            json={
                "tag_name": RELEASE_TAG,
                "name": f"Auto-Update Package (v{versao_atual})",
                "body": "Pacote de atualizacao automatica do Nariz Eletronico.",
                "draft": False,
                "prerelease": False,
            },
            timeout=20,
        )
        if r_create.status_code != 201:
            print("ERRO ao criar release Update:", r_create.json())
            return
        release_data = r_create.json()

    for asset in release_data.get("assets", []):
        if asset["name"] == ZIP_NAME:
            requests.delete(asset["url"], headers=headers, timeout=20)

    upload_base = release_data["upload_url"].split("{")[0]
    headers_zip = headers.copy()
    headers_zip["Content-Type"] = "application/zip"
    with open(arquivo_zip, "rb") as f:
        r_zip = requests.post(f"{upload_base}?name={ZIP_NAME}", headers=headers_zip, data=f, timeout=180)
    if r_zip.status_code == 201:
        print("OK: atualizacao.zip enviado para a Release!")
    else:
        print("ERRO no upload do zip:", r_zip.json())
        return

    # Atualiza version.json na branch main
    api_contents_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/version.json"
    sha_atual = None
    r_get = requests.get(api_contents_url, headers=headers, timeout=15)
    if r_get.status_code == 200:
        sha_atual = r_get.json().get("sha")

    commit_data = {
        "message": f"Update version.json to {versao_atual} via deploy automatico",
        "content": base64.b64encode(json_str.encode("utf-8")).decode("utf-8"),
        "branch": BRANCH_NAME,
    }
    if sha_atual:
        commit_data["sha"] = sha_atual
    requests.put(api_contents_url, headers=headers, json=commit_data, timeout=20)

    if conteudo_notas and titulo_versao:
        publicar_notas_versao(headers, REPO_OWNER, REPO_NAME, BRANCH_NAME, versao_atual, titulo_versao, conteudo_notas)
        limpar_notas_md()

    print("\nSUCESSO TOTAL! Build enviada e repositorio atualizado.")


if __name__ == "__main__":
    main()
