"""Utilitarios de credenciais e publicacao de notas de atualizacao para o Nariz Eletronico.

Baseado em: C:\ProjetoTablepRPG\Outros\AtualizacaoAutomatica\notas_utils.py
Repositorio alvo: https://github.com/LeanLopes01/NarizEletr-nico
"""
from __future__ import annotations

import base64
import datetime
import json
import os
import re
from pathlib import Path
import requests

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
CAMINHO_NOTAS_MD = HERE / "NotasAtualizacao.md"
CAMINHO_CREDENCIAIS_EXTERNAS = Path(r"C:\ProjetoTablepRPG\Outros\AtualizacaoAutomatica\atualizacao.py")
NOTAS_INDEX_PATH = "notas/index.json"


def obter_github_token() -> str:
    """Obtem o token do GitHub a partir de C:\ProjetoTablepRPG\Outros\AtualizacaoAutomatica ou variavel de ambiente."""
    env_tok = os.environ.get("GITHUB_TOKEN", "").strip()
    if env_tok:
        return env_tok
    if CAMINHO_CREDENCIAIS_EXTERNAS.exists():
        texto = CAMINHO_CREDENCIAIS_EXTERNAS.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'GITHUB_TOKEN\s*=\s*["\']([^"\']+)["\']', texto)
        if m:
            return m.group(1).strip()
    raise RuntimeError(
        "Token do GitHub nao encontrado em GITHUB_TOKEN nem em "
        f"{CAMINHO_CREDENCIAIS_EXTERNAS}."
    )


def ler_versao_projeto() -> str:
    """Le a versao atual do arquivo version.json na raiz do projeto."""
    vfile = PROJECT_ROOT / "version.json"
    if vfile.exists():
        data = json.loads(vfile.read_text(encoding="utf-8"))
        return str(data.get("version", "0.4.3")).strip()
    return "0.4.3"


def ler_notas_md(caminho: str | Path = CAMINHO_NOTAS_MD) -> str:
    path = Path(caminho)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def obter_titulo_versao(versao: str) -> str:
    return input(
        f"Digite o titulo curto das notas da versao {versao} (ex.: 'Calibracao MQ2/MQ3/MQ5 e Dashboard v{versao}'): "
    ).strip()


def limpar_notas_md(caminho: str | Path = CAMINHO_NOTAS_MD):
    Path(caminho).write_text("", encoding="utf-8")


def _get_conteudo_arquivo(headers: dict, repo_owner: str, repo_name: str, caminho_repo: str, branch: str):
    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{caminho_repo}"
    r = requests.get(api_url, headers=headers, params={"ref": branch}, timeout=15)
    if r.status_code == 200:
        dados = r.json()
        conteudo = base64.b64decode(dados["content"]).decode("utf-8")
        return conteudo, dados.get("sha")
    return None, None


def _put_conteudo_arquivo(
    headers: dict,
    repo_owner: str,
    repo_name: str,
    caminho_repo: str,
    branch: str,
    conteudo_str: str,
    mensagem: str,
    sha: str | None = None,
):
    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{caminho_repo}"
    conteudo_b64 = base64.b64encode(conteudo_str.encode("utf-8")).decode("utf-8")
    commit_data = {
        "message": mensagem,
        "content": conteudo_b64,
        "branch": branch,
    }
    if sha:
        commit_data["sha"] = sha
    return requests.put(api_url, headers=headers, json=commit_data, timeout=20)


def obter_version_setup_atual(headers: dict, repo_owner: str, repo_name: str, branch: str, fallback: str) -> str:
    conteudo, _ = _get_conteudo_arquivo(headers, repo_owner, repo_name, "version.json", branch)
    if conteudo:
        try:
            dados = json.loads(conteudo)
            return str(dados.get("versionSetup", fallback))
        except json.JSONDecodeError:
            pass
    return fallback


def publicar_notas_versao(
    headers: dict,
    repo_owner: str,
    repo_name: str,
    branch: str,
    versao: str,
    titulo: str,
    conteudo_md: str,
):
    hoje = datetime.date.today()
    data_str = f"{hoje.year}-{hoje.month:02d}-{hoje.day:02d}"
    print(f"\nPublicando notas de atualizacao da versao {versao}...")

    caminho_md_repo = f"notas/{versao}.md"
    _, sha_md = _get_conteudo_arquivo(headers, repo_owner, repo_name, caminho_md_repo, branch)
    r_md = _put_conteudo_arquivo(
        headers,
        repo_owner,
        repo_name,
        caminho_md_repo,
        branch,
        conteudo_md,
        f"Notas de atualizacao da versao {versao}",
        sha_md,
    )
    if r_md.status_code in (200, 201):
        print(f"   OK: {caminho_md_repo} enviado!")
    else:
        print(f"   ERRO ao enviar {caminho_md_repo}:", r_md.json())
        return

    conteudo_index, sha_index = _get_conteudo_arquivo(headers, repo_owner, repo_name, NOTAS_INDEX_PATH, branch)
    indice = json.loads(conteudo_index) if conteudo_index else {"versoes": []}
    indice.setdefault("versoes", [])
    indice["versoes"] = [v for v in indice["versoes"] if v.get("versao") != versao]
    indice["versoes"].insert(0, {"versao": versao, "data": data_str, "titulo": titulo})

    novo_conteudo_index = json.dumps(indice, ensure_ascii=False, indent=2)
    r_index = _put_conteudo_arquivo(
        headers,
        repo_owner,
        repo_name,
        NOTAS_INDEX_PATH,
        branch,
        novo_conteudo_index,
        f"Adiciona notas da versao {versao} ao index",
        sha_index,
    )
    if r_index.status_code in (200, 201):
        print("   OK: notas/index.json atualizado!")
    else:
        print("   ERRO ao atualizar notas/index.json:", r_index.json())
