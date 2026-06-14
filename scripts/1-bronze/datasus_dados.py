#!/usr/bin/env python3
"""
DATASUS Downloader e Conversor

Baixa arquivos DBC do FTP do DATASUS, organiza por sistema/ano/extensão
e converte para CSV.

Uso:
    python3 datasus_dados.py --sistema SIM
    python3 datasus_dados.py --sistema SIH --anos 2022 2023
    python3 datasus_dados.py --sistema SIM --estados SP RJ MG --anos 2020 2021
    python3 datasus_dados.py --sistema SIM --apenas-converter
    python3 datasus_dados.py --listar-sistemas
"""

import ftplib
import sys
import argparse
import tempfile
from pathlib import Path

import pandas as pd
import pyreaddbc.readdbc as _readdbc
from dbfread import DBF


# ─── Configuração ─────────────────────────────────────────────────────────────

FTP_HOST = 'ftp.datasus.gov.br'

ESTADOS = [
    'AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO',
    'MA', 'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR',
    'RJ', 'RN', 'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO',
]

SISTEMAS = {
    'SIM': {
        'descricao': 'Mortalidade — Declarações de Óbito',
        'ftp_path': '/dissemin/publicos/SIM/CID10/DORES/',
        'frequencia': 'anual',
        'arquivo': lambda uf, ano, _mes=None: f'DO{uf}{ano}.dbc',
    },
    'SIH': {
        'descricao': 'Internação Hospitalar — AIH Reduzida',
        'ftp_path': '/dissemin/publicos/SIHSUS/200801_/Dados/',
        'frequencia': 'mensal',
        'arquivo': lambda uf, ano, mes: f'RD{uf}{str(ano)[2:]}{mes:02d}.dbc',
    },
    'SIA': {
        'descricao': 'Procedimentos Ambulatoriais',
        'ftp_path': '/dissemin/publicos/SIASUS/200801_/Dados/',
        'frequencia': 'mensal',
        'arquivo': lambda uf, ano, mes: f'PA{uf}{str(ano)[2:]}{mes:02d}.dbc',
    },
    'SINASC': {
        'descricao': 'Nascidos Vivos — Declarações de Nascimento',
        'ftp_path': '/dissemin/publicos/SINASC/NOV/DNRES/',
        'frequencia': 'anual',
        'arquivo': lambda uf, ano, _mes=None: f'DN{uf}{ano}.dbc',
    },
}

BASE_DIR = Path('dados') / '1-bronze'
ANO_INICIO = 2010
ANO_FIM = 2024


# ─── FTP ──────────────────────────────────────────────────────────────────────

def conectar_ftp() -> ftplib.FTP:
    print(f'Conectando ao FTP {FTP_HOST}...')
    ftp = ftplib.FTP(FTP_HOST, timeout=60)
    ftp.login()
    ftp.set_pasv(True)
    print('Conectado.\n')
    return ftp


def baixar_arquivo(ftp: ftplib.FTP, ftp_path: str, arquivo: str, destino: Path) -> bool:
    if destino.exists():
        print(f'  [SKIP] {arquivo}')
        return True

    destino.parent.mkdir(parents=True, exist_ok=True)

    try:
        ftp.cwd(ftp_path)
        with open(destino, 'wb') as f:
            ftp.retrbinary(f'RETR {arquivo}', f.write)
        tamanho = destino.stat().st_size / 1024
        print(f'  [OK]   {arquivo}  ({tamanho:.1f} KB)')
        return True

    except ftplib.error_perm:
        print(f'  [--]   {arquivo} não encontrado')
        return False

    except Exception as e:
        print(f'  [ERR]  {arquivo}: {e}')
        destino.unlink(missing_ok=True)
        return False


# ─── Conversão DBC → CSV ──────────────────────────────────────────────────────

def dbc_para_csv(dbc: Path, csv: Path) -> bool:
    if csv.exists():
        print(f'  [SKIP] {csv.name}')
        return True

    csv.parent.mkdir(parents=True, exist_ok=True)
    tmp_dbf = None

    try:
        with tempfile.NamedTemporaryFile(suffix='.dbf', delete=False) as tmp:
            tmp_dbf = Path(tmp.name)

        _readdbc.dbc2dbf(str(dbc), str(tmp_dbf))
        df = pd.DataFrame(iter(DBF(str(tmp_dbf), encoding='latin-1')))
        df.to_csv(csv, index=False, encoding='utf-8-sig')
        print(f'  [OK]   {csv.name}  ({len(df):,} linhas, {len(df.columns)} colunas)')
        return True

    except Exception as e:
        print(f'  [ERR]  {dbc.name}: {e}')
        csv.unlink(missing_ok=True)
        return False

    finally:
        if tmp_dbf and tmp_dbf.exists():
            tmp_dbf.unlink()


# ─── Listagem de arquivos esperados ───────────────────────────────────────────

def listar_arquivos(sistema: str, anos: list, estados: list) -> list:
    cfg = SISTEMAS[sistema]
    arquivos = []

    if cfg['frequencia'] == 'anual':
        for ano in anos:
            for uf in estados:
                nome = cfg['arquivo'](uf, ano)
                arquivos.append((nome, ano))
    else:
        for ano in anos:
            for mes in range(1, 13):
                for uf in estados:
                    nome = cfg['arquivo'](uf, ano, mes)
                    arquivos.append((nome, ano))

    return arquivos


# ─── Validação de layout ──────────────────────────────────────────────────────

def _ler_cabecalho(csv: Path) -> tuple[tuple, str | None]:
    try:
        with open(csv, encoding='utf-8-sig') as f:
            primeira_linha = f.readline().rstrip('\n')
        return tuple(primeira_linha.split(',')), None
    except Exception as e:
        return (), str(e)


def _relatar_exercicio(ano: str, cabecalhos: dict[str, tuple], prefixo: str):
    grupos: dict[tuple, list[str]] = {}
    for nome, colunas in cabecalhos.items():
        grupos.setdefault(colunas, []).append(nome)

    total = len(cabecalhos)

    if len(grupos) == 1:
        colunas_ref = next(iter(grupos))
        print(f'  {ano}  [OK]  {total} arquivo(s) — {len(colunas_ref)} colunas')
        return

    # Divergência — referência é o grupo com mais arquivos
    grupo_ref = max(grupos, key=lambda k: len(grupos[k]))
    colunas_ref = set(grupo_ref)
    divergentes = sum(len(v) for k, v in grupos.items() if k != grupo_ref)

    print(f'  {ano}  [DIVERGENTE]  {total} arquivo(s) — {divergentes} com layout diferente')

    for colunas, arquivos in grupos.items():
        if colunas == grupo_ref:
            continue
        colunas_set = set(colunas)
        ausentes = sorted(colunas_ref - colunas_set)
        extras = sorted(colunas_set - colunas_ref)
        for arq in arquivos:
            detalhes = []
            if ausentes:
                detalhes.append(f'ausentes: {", ".join(ausentes)}')
            if extras:
                detalhes.append(f'extras: {", ".join(extras)}')
            print(f'         {prefixo}{arq}  →  {" | ".join(detalhes)}')


def validar_layout(sistema: str):
    csv_dir = BASE_DIR / sistema / 'csv'

    if not csv_dir.exists():
        print(f'\nNenhum CSV encontrado em {csv_dir}/\n')
        sys.exit(1)

    # Organiza CSVs por exercício (subpasta)
    anos = sorted(p.name for p in csv_dir.iterdir() if p.is_dir())
    if not anos:
        print(f'\nNenhuma subpasta de exercício encontrada em {csv_dir}/\n')
        sys.exit(1)

    total_arquivos = sum(len(list((csv_dir / a).glob('*.csv'))) for a in anos)

    print(f'\n{"=" * 60}')
    print(f'Validação de layout — {sistema}')
    print(f'Diretório  : {csv_dir}/')
    print(f'Exercícios : {anos[0]}–{anos[-1]}  ({len(anos)} anos)')
    print(f'Arquivos   : {total_arquivos} CSVs')
    print(f'{"=" * 60}\n')

    erros_leitura: list[str] = []
    resumo_divergentes: list[str] = []

    for ano in anos:
        csvs = sorted((csv_dir / ano).glob('*.csv'))
        if not csvs:
            print(f'  {ano}  [--]  nenhum arquivo')
            continue

        cabecalhos: dict[str, tuple] = {}
        for csv in csvs:
            colunas, erro = _ler_cabecalho(csv)
            if erro:
                erros_leitura.append(f'  {ano}/{csv.name}: {erro}')
            else:
                cabecalhos[csv.name] = colunas

        _relatar_exercicio(ano, cabecalhos, prefixo=f'{ano}/')

        grupos = {}
        for colunas in cabecalhos.values():
            grupos.setdefault(colunas, 0)
            grupos[colunas] += 1
        if len(grupos) > 1:
            resumo_divergentes.append(ano)

    if erros_leitura:
        print('\nErros de leitura:')
        for msg in erros_leitura:
            print(msg)

    print(f'\n{"─" * 60}')
    if not resumo_divergentes:
        print(f'RESUMO: todos os exercícios têm layout consistente.')
    else:
        print(f'RESUMO: exercícios com divergência — {", ".join(resumo_divergentes)}')
    print()


# ─── Execução principal ───────────────────────────────────────────────────────

def executar(sistema: str, anos: list, estados: list, apenas_converter: bool):
    cfg = SISTEMAS[sistema]
    arquivos = listar_arquivos(sistema, anos, estados)

    print(f'\n{"=" * 60}')
    print(f'Sistema  : {sistema} — {cfg["descricao"]}')
    print(f'FTP path : {cfg["ftp_path"]}')
    print(f'Anos     : {anos[0]}–{anos[-1]}  ({len(anos)} exercícios)')
    print(f'Estados  : {len(estados)} UFs  ({", ".join(estados[:5])}{"..." if len(estados) > 5 else ""})')
    print(f'Arquivos : {len(arquivos)} previstos')
    print(f'Destino  : {BASE_DIR / sistema}/')
    print(f'{"=" * 60}\n')

    # ── Etapa 1: Download ──────────────────────────────────────────
    if not apenas_converter:
        print('[ Etapa 1/2 — Download ]\n')
        ftp = conectar_ftp()
        baixados = 0
        for nome, ano in arquivos:
            destino = BASE_DIR / sistema / 'dbc' / str(ano) / nome
            if baixar_arquivo(ftp, cfg['ftp_path'], nome, destino):
                baixados += 1
        ftp.quit()
        print(f'\nDownload concluído: {baixados}/{len(arquivos)} arquivos.\n')
    else:
        print('[ Etapa 1/2 — Download ignorado (--apenas-converter) ]\n')

    # ── Etapa 2: Conversão ────────────────────────────────────────
    print('[ Etapa 2/2 — Conversão DBC → CSV ]\n')
    convertidos = 0
    for nome, ano in arquivos:
        dbc = BASE_DIR / sistema / 'dbc' / str(ano) / nome
        csv = BASE_DIR / sistema / 'csv' / str(ano) / nome.replace('.dbc', '.csv')
        if not dbc.exists():
            continue
        if dbc_para_csv(dbc, csv):
            convertidos += 1

    print(f'\nConversão concluída: {convertidos} arquivo(s) convertido(s).')
    print(f'CSVs em: {BASE_DIR / sistema / "csv"}/\n')


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Baixa e converte dados do DATASUS (FTP)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Exemplos:\n'
               '  python3 datasus_dados.py --sistema SIM\n'
               '  python3 datasus_dados.py --sistema SIH --anos 2022 2023\n'
               '  python3 datasus_dados.py --sistema SIM --estados SP RJ MG\n'
               '  python3 datasus_dados.py --sistema SIM --apenas-converter\n'
               '  python3 datasus_dados.py --listar-sistemas\n',
    )

    parser.add_argument(
        '--sistema',
        choices=SISTEMAS.keys(),
        metavar='SISTEMA',
        help='Sistema DATASUS: ' + ', '.join(SISTEMAS.keys()),
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
        '--estados',
        nargs='+',
        default=ESTADOS,
        metavar='UF',
        help='Siglas dos estados (padrão: todos os 27)',
    )
    parser.add_argument(
        '--apenas-converter',
        action='store_true',
        help='Pula o download e converte apenas os DBCs já baixados',
    )
    parser.add_argument(
        '--listar-sistemas',
        action='store_true',
        help='Lista os sistemas disponíveis e sai',
    )
    parser.add_argument(
        '--validacao',
        action='store_true',
        help='Verifica se todos os CSVs do sistema têm o mesmo layout de colunas',
    )

    args = parser.parse_args()

    if args.listar_sistemas:
        print('\nSistemas disponíveis:\n')
        for sigla, cfg in SISTEMAS.items():
            print(f'  {sigla:<8} {cfg["descricao"]}')
            print(f'           FTP: {cfg["ftp_path"]}')
            print(f'           Frequência: {cfg["frequencia"]}\n')
        sys.exit(0)

    if not args.sistema:
        parser.print_help()
        print('\nErro: --sistema é obrigatório. Use --listar-sistemas para ver as opções.\n')
        sys.exit(1)

    if args.validacao:
        validar_layout(args.sistema)
        sys.exit(0)

    estados = [uf.upper() for uf in args.estados]
    invalidos = [uf for uf in estados if uf not in ESTADOS]
    if invalidos:
        print(f'Erro: estados inválidos: {invalidos}')
        print(f'Estados válidos: {ESTADOS}')
        sys.exit(1)

    executar(args.sistema, sorted(args.anos), estados, args.apenas_converter)


if __name__ == '__main__':
    main()
