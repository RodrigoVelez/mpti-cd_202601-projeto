#!/usr/bin/env python3
"""
IBGE Dados de Municípios

Coleta dados de municípios brasileiros via API REST do IBGE,
grava o JSON bruto e converte para CSV tabular.

API: https://servicodados.ibge.gov.br/api/v1/localidades/municipios?orderBy=nome

Uso:
    python3 ibge_dados_municipios.py
    python3 ibge_dados_municipios.py --estados SP RJ MG
"""

import gzip
import ssl
import sys
import json
import argparse
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

import pandas as pd

# ─── Configuração ─────────────────────────────────────────────────────────────
API_URL  = 'https://servicodados.ibge.gov.br/api/v1/localidades/municipios?orderBy=nome'
BASE_DIR = Path('dados') / 'ibge_dados_municipios'

# ─── API ──────────────────────────────────────────────────────────────────────

def buscar_municipios() -> list:
    print(f'Consultando API IBGE...')
    ctx = ssl._create_unverified_context()
    try:
        with urlopen(API_URL, timeout=60, context=ctx) as resp:
            raw = resp.read()
            if resp.info().get('Content-Encoding') == 'gzip' or raw[:2] == b'\x1f\x8b':
                raw = gzip.decompress(raw)
            dados = json.loads(raw.decode('utf-8'))
    except URLError as e:
        print(f'  [ERR]  Falha na requisição: {e}')
        sys.exit(1)
    print(f'  [OK]   {len(dados):,} municípios recebidos')
    return dados

def _sigla_uf(m: dict) -> str | None:
    try:
        return m['microrregiao']['mesorregiao']['UF']['sigla']
    except (TypeError, KeyError):
        pass
    try:
        return m['regiao-imediata']['regiao-intermediaria']['UF']['sigla']
    except (TypeError, KeyError):
        return None


def filtrar_por_estados(dados: list, estados: list) -> list:
    filtrados = [m for m in dados if _sigla_uf(m) in estados]
    print(f'  [OK]   {len(filtrados):,} municípios após filtro: {", ".join(estados)}')
    return filtrados


# ─── Persistência ─────────────────────────────────────────────────────────────

def salvar_json(dados: list, caminho: Path):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    tamanho = caminho.stat().st_size / 1024
    print(f'  [OK]   {caminho}  ({tamanho:.1f} KB)')


def _renomear_colunas(colunas: list[str]) -> dict[str, str]:
    """Retorna mapeamento col_original → pai_campo, descartando duplicatas."""
    vistas: set[str] = set()
    mapa: dict[str, str] = {}
    for col in colunas:
        partes = col.split('.')
        if len(partes) > 1:
            novo = f'{partes[-2]}_{partes[-1]}'.lower().replace('-', '_')
        else:
            novo = partes[-1].lower().replace('-', '_')
        if novo not in vistas:
            vistas.add(novo)
            mapa[col] = novo
    return mapa


def salvar_csv(dados: list, caminho: Path):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df = pd.json_normalize(dados, sep='.')
    mapa = _renomear_colunas(list(df.columns))
    df = df[list(mapa.keys())].rename(columns=mapa)
    df = df.dropna(axis=1, how='all')
    for col in df.select_dtypes(include='float64').columns:
        df[col] = df[col].astype('Int64')
    df.to_csv(caminho, index=False, encoding='utf-8-sig')
    print(f'  [OK]   {caminho}  ({len(df):,} linhas, {len(df.columns)} colunas)')


# ─── Execução principal ───────────────────────────────────────────────────────

def executar(estados: list | None):
    sufixo = ('_' + '_'.join(sorted(estados))) if estados else ''
    json_path = BASE_DIR / 'json' / f'municipios{sufixo}.json'
    csv_path  = BASE_DIR / 'csv'  / f'municipios{sufixo}.csv'

    print(f'\n{"=" * 60}')
    print(f'IBGE — Dados de Municípios')
    print(f'API      : {API_URL}')
    print(f'Estados  : {", ".join(estados) if estados else "todos"}')
    print(f'Destino  : {BASE_DIR}/')
    print(f'{"=" * 60}\n')

    # ── Etapa 1: Coleta ───────────────────────────────────────────
    print('[ Etapa 1/2 — Coleta via API ]\n')
    dados = buscar_municipios()
    if estados:
        dados = filtrar_por_estados(dados, estados)
    print()

    # ── Etapa 2: Gravação ─────────────────────────────────────────
    print('[ Etapa 2/2 — Gravação ]\n')
    salvar_json(dados, json_path)
    salvar_csv(dados, csv_path)
    print(f'\nConcluído. Arquivos em {BASE_DIR}/\n')


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Coleta dados de municípios do IBGE via API REST',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Exemplos:\n'
               '  python3 ibge_dados_municipios.py\n'
               '  python3 ibge_dados_municipios.py --estados SP RJ MG\n',
    )
    parser.add_argument(
        '--estados',
        nargs='+',
        metavar='UF',
        help='Filtrar por sigla(s) de estado (ex: SP RJ MG). Padrão: todos.',
    )

    args = parser.parse_args()
    estados = [uf.upper() for uf in args.estados] if args.estados else None

    executar(estados)


if __name__ == '__main__':
    main()
