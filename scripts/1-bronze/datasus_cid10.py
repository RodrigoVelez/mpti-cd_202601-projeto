#!/usr/bin/env python3
"""
DATASUS CID-10 Downloader e Conversor

Suporta duas fontes de download, selecionáveis via --fonte:

  v2008 (padrão)
      URL  : http://www2.datasus.gov.br/cid10/V2008/downloads/CID10CSV.zip
      Pasta: dados/1-bronze/cid-10-datasus-v2008/
      Conteúdo: 6 CSVs (capítulos, grupos, categorias, subcategorias, CID-O)
      Formato bruto: ZIP com CSVs em latin-1, separador ponto-e-vírgula

  ftp
      Host : ftp.datasus.gov.br
      Path : /dissemin/publicos/SIM/CID10/TABELAS/
      Pasta: dados/1-bronze/cid-10-ftp_datasus/
      Conteúdo: CID10.DBF (categorias+subcategorias) e CIDCAP10.DBF (capítulos)
      Formato bruto: DBF compactado

Uso:
    python3 datasus_cid10.py                          # ambas as fontes (padrão)
    python3 datasus_cid10.py --fonte v2008            # só fonte HTTP v2008
    python3 datasus_cid10.py --fonte ftp              # só fonte FTP
    python3 datasus_cid10.py --apenas-converter       # sem download, só converte
    python3 datasus_cid10.py --fonte ftp --validacao  # layout dos CSVs da fonte ftp
"""

import ftplib
import io
import ssl
import sys
import argparse
import zipfile
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

import pandas as pd
from dbfread import DBF


# ─── Configuração ─────────────────────────────────────────────────────────────

# Fonte: v2008 (HTTP)
V2008_URL  = 'http://www2.datasus.gov.br/cid10/V2008/downloads/CID10CSV.zip'
V2008_ZIP  = 'CID10CSV.zip'
V2008_BASE = Path('dados') / '1-bronze' / 'cid-10-datasus-v2008'

# Fonte: ftp (DATASUS FTP)
FTP_HOST  = 'ftp.datasus.gov.br'
FTP_PATH  = '/dissemin/publicos/SIM/CID10/TABELAS/'
FTP_TABELAS = ['CID10.DBF', 'CIDCAP10.DBF']
FTP_BASE  = Path('dados') / '1-bronze' / 'cid-10-ftp_datasus'

FONTES_DISPONIVEIS = ['v2008', 'ftp']


# ═══════════════════════════════════════════════════════════════════════════════
# FONTE: v2008
# ═══════════════════════════════════════════════════════════════════════════════

def _baixar_zip_v2008(destino: Path) -> bool:
    if destino.exists():
        print(f'  [SKIP] {destino.name}')
        return True

    destino.parent.mkdir(parents=True, exist_ok=True)
    ctx = ssl._create_unverified_context()

    try:
        print(f'  Baixando {V2008_URL} ...')
        with urlopen(V2008_URL, timeout=60, context=ctx) as resp:
            dados = resp.read()
        destino.write_bytes(dados)
        tamanho = destino.stat().st_size / 1024
        print(f'  [OK]   {destino.name}  ({tamanho:.1f} KB)')
        return True

    except URLError as e:
        print(f'  [ERR]  {destino.name}: {e}')
        destino.unlink(missing_ok=True)
        return False

    except Exception as e:
        print(f'  [ERR]  {destino.name}: {e}')
        destino.unlink(missing_ok=True)
        return False


def _extrair_csvs_v2008(zip_path: Path, csv_dir: Path) -> int:
    """Extrai e normaliza cada CSV do ZIP: latin-1 → utf-8-sig, ; → ,"""
    csv_dir.mkdir(parents=True, exist_ok=True)
    convertidos = 0

    with zipfile.ZipFile(zip_path, 'r') as z:
        membros = [n for n in z.namelist() if n.upper().endswith('.CSV')]
        for membro in membros:
            nome_saida = Path(membro).name.upper().replace('.CSV', '.csv')
            destino = csv_dir / nome_saida

            if destino.exists():
                print(f'  [SKIP] {nome_saida}')
                convertidos += 1
                continue

            try:
                raw = z.read(membro).decode('latin-1')
                df = pd.read_csv(io.StringIO(raw), sep=';', dtype=str)
                # remover coluna vazia gerada pelo ; final do cabeçalho
                df = df.loc[:, ~df.columns.str.match(r'^Unnamed')]
                df.to_csv(destino, index=False, encoding='utf-8-sig')
                print(f'  [OK]   {nome_saida}  ({len(df):,} linhas, {len(df.columns)} colunas)')
                convertidos += 1
            except Exception as e:
                print(f'  [ERR]  {nome_saida}: {e}')
                destino.unlink(missing_ok=True)

    return convertidos


def executar_v2008(apenas_converter: bool):
    total_membros = 6  # número de CSVs dentro do ZIP

    print(f'\n{"=" * 60}')
    print(f'CID-10 — Fonte: v2008 (HTTP)')
    print(f'URL     : {V2008_URL}')
    print(f'Destino : {V2008_BASE}/')
    print(f'{"=" * 60}\n')

    zip_path = V2008_BASE / 'zip' / V2008_ZIP

    # ── Etapa 1: Download ──────────────────────────────────────────
    if not apenas_converter:
        print('[ Etapa 1/2 — Download ZIP ]\n')
        if not _baixar_zip_v2008(zip_path):
            print('\nDownload falhou. Abortando.\n')
            return
        print()
    else:
        print('[ Etapa 1/2 — Download ignorado (--apenas-converter) ]\n')

    # ── Etapa 2: Extração e normalização ──────────────────────────
    print('[ Etapa 2/2 — Extração e normalização CSV ]\n')

    if not zip_path.exists():
        print(f'  [--]   ZIP não encontrado em {zip_path}\n')
        return

    convertidos = _extrair_csvs_v2008(zip_path, V2008_BASE / 'csv')
    print(f'\nConcluído: {convertidos}/{total_membros} arquivo(s) processado(s).')
    print(f'CSVs em: {V2008_BASE / "csv"}/\n')


# ═══════════════════════════════════════════════════════════════════════════════
# FONTE: ftp
# ═══════════════════════════════════════════════════════════════════════════════

def _conectar_ftp() -> ftplib.FTP:
    print(f'Conectando ao FTP {FTP_HOST}...')
    ftp = ftplib.FTP(FTP_HOST, timeout=60)
    ftp.login()
    ftp.set_pasv(True)
    print('Conectado.\n')
    return ftp


def _baixar_arquivo_ftp(ftp: ftplib.FTP, arquivo: str, destino: Path) -> bool:
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


def _dbf_para_csv(dbf_path: Path, csv_path: Path) -> bool:
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


def executar_ftp(apenas_converter: bool):
    print(f'\n{"=" * 60}')
    print(f'CID-10 — Fonte: ftp (DATASUS FTP)')
    print(f'FTP     : ftp://{FTP_HOST}{FTP_PATH}')
    print(f'Tabelas : {", ".join(FTP_TABELAS)}')
    print(f'Destino : {FTP_BASE}/')
    print(f'{"=" * 60}\n')

    # ── Etapa 1: Download ──────────────────────────────────────────
    if not apenas_converter:
        print('[ Etapa 1/2 — Download DBF ]\n')
        ftp = _conectar_ftp()
        for arquivo in FTP_TABELAS:
            _baixar_arquivo_ftp(ftp, arquivo, FTP_BASE / 'dbf' / arquivo)
        ftp.quit()
        print()
    else:
        print('[ Etapa 1/2 — Download ignorado (--apenas-converter) ]\n')

    # ── Etapa 2: Conversão DBF → CSV ─────────────────────────────
    print('[ Etapa 2/2 — Conversão DBF → CSV ]\n')
    convertidos = 0
    for arquivo in FTP_TABELAS:
        dbf_path = FTP_BASE / 'dbf' / arquivo
        csv_path = FTP_BASE / 'csv' / arquivo.replace('.DBF', '.csv')
        if not dbf_path.exists():
            print(f'  [--]   {arquivo} não encontrado, pulando conversão')
            continue
        if _dbf_para_csv(dbf_path, csv_path):
            convertidos += 1

    print(f'\nConcluído: {convertidos}/{len(FTP_TABELAS)} tabela(s) convertida(s).')
    print(f'CSVs em: {FTP_BASE / "csv"}/\n')


# ═══════════════════════════════════════════════════════════════════════════════
# Validação de layout
# ═══════════════════════════════════════════════════════════════════════════════

def validar_layout(fontes: list[str]):
    mapa_base = {'v2008': V2008_BASE, 'ftp': FTP_BASE}

    for fonte in fontes:
        base = mapa_base[fonte]
        csv_dir = base / 'csv'
        csvs = sorted(csv_dir.glob('*.csv'))

        print(f'\n{"=" * 60}')
        print(f'Validação de layout — CID-10 ({fonte})')
        print(f'Diretório : {csv_dir}/')
        print(f'{"=" * 60}\n')

        if not csvs:
            print(f'  Nenhum CSV encontrado.\n')
            continue

        for csv in csvs:
            try:
                with open(csv, encoding='utf-8-sig') as f:
                    cabecalho = f.readline().rstrip('\n')
                colunas = cabecalho.split(',')
                print(f'  {csv.name:<35}  {len(colunas)} colunas: {", ".join(colunas)}')
            except Exception as e:
                print(f'  {csv.name:<35}  [ERR] {e}')

        print()


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description='Baixa tabelas de referência CID-10 do DATASUS (duas fontes disponíveis)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Fontes disponíveis:\n'
            '  v2008  ZIP com CSVs via HTTP — mais completo (capítulos, grupos,\n'
            '         categorias, subcategorias, CID-O). Padrão.\n'
            '  ftp    DBFs via FTP DATASUS — estrutura mais compacta.\n\n'
            'Exemplos:\n'
            '  python3 datasus_cid10.py                         # ambas as fontes (padrão)\n'
            '  python3 datasus_cid10.py --fonte v2008           # só v2008\n'
            '  python3 datasus_cid10.py --fonte ftp             # só FTP\n'
            '  python3 datasus_cid10.py --fonte ftp --apenas-converter\n'
            '  python3 datasus_cid10.py --fonte v2008 --validacao\n'
            '  python3 datasus_cid10.py --fonte v2008 ftp --validacao\n'
        ),
    )
    parser.add_argument(
        '--fonte',
        nargs='+',
        choices=FONTES_DISPONIVEIS,
        default=['v2008', 'ftp'],
        metavar='FONTE',
        help=(
            'Fonte(s) de download: v2008 e/ou ftp '
            '(padrão: ambas). Pode informar um único valor para restringir.'
        ),
    )
    parser.add_argument(
        '--apenas-converter',
        action='store_true',
        help='Pula o download e reprocessa a partir dos arquivos já baixados',
    )
    parser.add_argument(
        '--validacao',
        action='store_true',
        help='Exibe o layout (colunas) dos CSVs de cada fonte informada',
    )

    args = parser.parse_args()
    fontes = list(dict.fromkeys(args.fonte))  # deduplica mantendo ordem

    if args.validacao:
        validar_layout(fontes)
        sys.exit(0)

    for fonte in fontes:
        if fonte == 'v2008':
            executar_v2008(args.apenas_converter)
        elif fonte == 'ftp':
            executar_ftp(args.apenas_converter)


if __name__ == '__main__':
    main()
