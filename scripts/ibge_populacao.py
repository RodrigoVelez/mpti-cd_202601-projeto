#!/usr/bin/env python3
"""
IBGE POPSVS Downloader e Conversor

Baixa arquivos ZIP de projeções populacionais do IBGE via FTP do DATASUS,
extrai os DBFs e converte para CSV.

FTP base: ftp://ftp.datasus.gov.br/dissemin/publicos/IBGE/POPSVS/

Uso:
    python3 ibge.py
    python3 ibge.py --anos 2020 2021 2022
    python3 ibge.py --apenas-converter
    python3 ibge.py --validacao
"""

import ftplib
import sys
import argparse
import zipfile
import tempfile
from pathlib import Path

import pandas as pd
from dbfread import DBF

# ─── Configuração ─────────────────────────────────────────────────────────────
FTP_HOST    = 'ftp.datasus.gov.br'
FTP_PATH    = '/dissemin/publicos/IBGE/POPSVS/'
BASE_DIR    = Path('dados') / 'ibge_populacao'
ANO_INICIO  = 2010
ANO_FIM     = 2024

def nome_zip(ano: int) -> str:
    return f'POPSBR{str(ano)[2:]}.zip'

def nome_dbf(ano: int) -> str:
    return f'POP{str(ano)[2:]}.dbf'

def nome_csv(ano: int) -> str:
    return f'POP{str(ano)[2:]}.csv'

# ─── FTP ──────────────────────────────────────────────────────────────────────
def conectar_ftp() -> ftplib.FTP:
    print(f'Conectando ao FTP {FTP_HOST}...')
    ftp = ftplib.FTP(FTP_HOST, timeout=60)
    ftp.login()
    ftp.set_pasv(True)
    print('Conectado.\n')
    return ftp

def baixar_zip(ftp: ftplib.FTP, arquivo: str, destino: Path) -> bool:
    if destino.exists():
        print(f'  [SKIP] {arquivo}')
        return True

    destino.parent.mkdir(parents=True, exist_ok=True)

    try:
        ftp.cwd(FTP_PATH)
        with open(destino, 'wb') as f:
            ftp.retrbinary(f'RETR {arquivo}', f.write)
        tamanho = destino.stat().st_size / 1024
        print(f'  [OK]   {arquivo}  ({tamanho:.1f} KB)')
        return True

    except ftplib.error_perm:
        print(f'  [--]   {arquivo} não encontrado no FTP')
        return False

    except Exception as e:
        print(f'  [ERR]  {arquivo}: {e}')
        destino.unlink(missing_ok=True)
        return False

# ─── Extração ZIP → DBF ───────────────────────────────────────────────────────
def extrair_dbf(zip_path: Path, dbf_dest: Path) -> bool:
    if dbf_dest.exists():
        print(f'  [SKIP] {dbf_dest.name} já extraído')
        return True

    dbf_dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            dbfs = [n for n in z.namelist() if n.lower().endswith('.dbf')]
            if not dbfs:
                print(f'  [ERR]  {zip_path.name}: nenhum DBF encontrado no ZIP')
                return False
            with z.open(dbfs[0]) as src, open(dbf_dest, 'wb') as dst:
                dst.write(src.read())
        tamanho = dbf_dest.stat().st_size / (1024 * 1024)
        print(f'  [OK]   {dbf_dest.name}  ({tamanho:.1f} MB)')
        return True

    except Exception as e:
        print(f'  [ERR]  {zip_path.name}: {e}')
        dbf_dest.unlink(missing_ok=True)
        return False


# ─── Conversão DBF → CSV ──────────────────────────────────────────────────────
def dbf_para_csv(dbf_path: Path, csv_path: Path) -> bool:
    if csv_path.exists():
        print(f'  [SKIP] {csv_path.name}')
        return True

    csv_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        df = pd.DataFrame(iter(DBF(str(dbf_path), encoding='latin-1')))
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f'  [OK]   {csv_path.name}  ({len(df):,} linhas, {len(df.columns)} colunas)')
        return True

    except Exception as e:
        print(f'  [ERR]  {dbf_path.name}: {e}')
        csv_path.unlink(missing_ok=True)
        return False


# ─── Validação de layout ──────────────────────────────────────────────────────
def _ler_cabecalho(csv: Path) -> tuple[tuple, str | None]:
    try:
        with open(csv, encoding='utf-8-sig') as f:
            primeira_linha = f.readline().rstrip('\n')
        return tuple(primeira_linha.split(',')), None
    except Exception as e:
        return (), str(e)

def validar_layout():
    csv_dir = BASE_DIR / 'csv'

    csvs = sorted(csv_dir.rglob('*.csv'))
    if not csvs:
        print(f'\nNenhum CSV encontrado em {csv_dir}/\n')
        sys.exit(1)

    print(f'\n{"=" * 60}')
    print(f'Validação de layout — IBGE POPSVS')
    print(f'Diretório  : {csv_dir}/')
    print(f'Exercícios : {len(csvs)} arquivo(s)')
    print(f'{"=" * 60}\n')

    cabecalhos: dict[int, tuple] = {}
    erros: list[str] = []

    for csv in csvs:
        ano = int(csv.parent.name)
        colunas, erro = _ler_cabecalho(csv)
        if erro:
            erros.append(f'  {ano}/{csv.name}: {erro}')
        else:
            cabecalhos[ano] = colunas

    # Referência = layout majoritário entre todos os anos
    grupos: dict[tuple, list[int]] = {}
    for ano, colunas in cabecalhos.items():
        grupos.setdefault(colunas, []).append(ano)

    grupo_ref = max(grupos, key=lambda k: len(grupos[k]))
    colunas_ref = set(grupo_ref)

    divergentes: list[int] = []

    for ano in sorted(cabecalhos):
        colunas = cabecalhos[ano]
        if colunas == grupo_ref:
            print(f'  {ano}  [OK]  {len(colunas)} colunas')
        else:
            colunas_set = set(colunas)
            ausentes = sorted(colunas_ref - colunas_set)
            extras   = sorted(colunas_set - colunas_ref)
            detalhes = []
            if ausentes:
                detalhes.append(f'ausentes: {", ".join(ausentes)}')
            if extras:
                detalhes.append(f'extras: {", ".join(extras)}')
            print(f'  {ano}  [DIVERGENTE]  {len(colunas)} colunas  →  {" | ".join(detalhes)}')
            divergentes.append(ano)

    if erros:
        print('\nErros de leitura:')
        for msg in erros:
            print(msg)

    print(f'\n{"─" * 60}')
    if not divergentes:
        print(f'RESUMO: todos os exercícios têm layout consistente.')
    else:
        print(f'RESUMO: exercícios com divergência — {", ".join(str(a) for a in divergentes)}')
    print()


# ─── Execução principal ───────────────────────────────────────────────────────
def executar(anos: list, apenas_converter: bool):
    print(f'\n{"=" * 60}')
    print(f'IBGE POPSVS — Projeções Populacionais')
    print(f'FTP path   : {FTP_PATH}')
    print(f'Anos       : {anos[0]}–{anos[-1]}  ({len(anos)} exercícios)')
    print(f'Destino    : {BASE_DIR}/')
    print(f'{"=" * 60}\n')

    # ── Etapa 1: Download ──────────────────────────────────────────
    if not apenas_converter:
        print('[ Etapa 1/3 — Download ZIP ]\n')
        ftp = conectar_ftp()
        for ano in anos:
            arquivo = nome_zip(ano)
            destino = BASE_DIR / 'zip' / str(ano) / arquivo
            baixar_zip(ftp, arquivo, destino)
        ftp.quit()
        print()
    else:
        print('[ Etapa 1/3 — Download ignorado (--apenas-converter) ]\n')

    # ── Etapa 2: Extração ZIP → DBF ───────────────────────────────
    print('[ Etapa 2/3 — Extração ZIP → DBF ]\n')
    for ano in anos:
        zip_path = BASE_DIR / 'zip' / str(ano) / nome_zip(ano)
        dbf_dest = BASE_DIR / 'dbf' / str(ano) / nome_dbf(ano)
        if not zip_path.exists():
            continue
        extrair_dbf(zip_path, dbf_dest)
    print()

    # ── Etapa 3: Conversão DBF → CSV ──────────────────────────────
    print('[ Etapa 3/3 — Conversão DBF → CSV ]\n')
    convertidos = 0
    for ano in anos:
        dbf_path = BASE_DIR / 'dbf' / str(ano) / nome_dbf(ano)
        csv_path = BASE_DIR / 'csv' / str(ano) / nome_csv(ano)
        if not dbf_path.exists():
            continue
        if dbf_para_csv(dbf_path, csv_path):
            convertidos += 1

    print(f'\nConcluído: {convertidos} arquivo(s) convertido(s).')
    print(f'CSVs em: {BASE_DIR / "csv"}/\n')


# ─── CLI ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description='Baixa e converte projeções populacionais IBGE/DATASUS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Exemplos:\n'
               '  python3 ibge.py\n'
               '  python3 ibge.py --anos 2020 2021 2022\n'
               '  python3 ibge.py --apenas-converter\n'
               '  python3 ibge.py --validacao\n',
    )
    parser.add_argument(
        '--anos',
        nargs='+',
        type=int,
        default=list(range(ANO_INICIO, ANO_FIM + 1)),
        metavar='ANO',
        help=f'Anos a processar (padrão: {ANO_INICIO}–{ANO_FIM})',
    )
    parser.add_argument(
        '--apenas-converter',
        action='store_true',
        help='Pula o download e converte apenas os arquivos já baixados',
    )
    parser.add_argument(
        '--validacao',
        action='store_true',
        help='Verifica se todos os CSVs têm o mesmo layout de colunas por exercício',
    )

    args = parser.parse_args()

    if args.validacao:
        validar_layout()
        sys.exit(0)

    executar(sorted(args.anos), args.apenas_converter)

if __name__ == '__main__':
    main()
