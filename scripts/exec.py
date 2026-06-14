#!/usr/bin/env python3
"""
Executa os scripts de ingestão da camada Bronze em sequência.

Os argumentos informados aqui são repassados automaticamente a cada script
conforme o que cada um aceita:

    --anos            → datasus_dados.py, ibge_populacao.py
    --estados         → datasus_dados.py, ibge_dados_municipios.py
    --apenas-converter→ datasus_dados.py, ibge_populacao.py, datasus_cid10.py
    --validacao       → datasus_dados.py, ibge_populacao.py, datasus_cid10.py

Uso:
    python3 scripts/exec.py
    python3 scripts/exec.py --anos 2020 2021 2022
    python3 scripts/exec.py --estados SP RJ MG PB
    python3 scripts/exec.py --anos 2022 2023 --estados PB PE CE RN
    python3 scripts/exec.py --apenas-converter
    python3 scripts/exec.py --validacao
"""

import subprocess
import sys
import argparse
from pathlib import Path

BRONZE = Path(__file__).parent / '1-bronze'


def run(script: Path, *args: str):
    cmd = [sys.executable, str(script), *args]
    print(f'\n{"=" * 60}')
    print(f'Iniciando: {script.name}' + (f'  [{" ".join(args)}]' if args else ''))
    print(f'{"=" * 60}\n')
    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser(
        description='Executa os scripts da camada Bronze em sequência',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Os argumentos são repassados apenas aos scripts que os aceitam.\n\n'
            'Exemplos:\n'
            '  python3 scripts/exec.py\n'
            '  python3 scripts/exec.py --anos 2020 2021 2022\n'
            '  python3 scripts/exec.py --estados SP RJ MG PB\n'
            '  python3 scripts/exec.py --anos 2022 2023 --estados PB PE CE RN\n'
            '  python3 scripts/exec.py --apenas-converter\n'
            '  python3 scripts/exec.py --validacao\n'
        ),
    )
    parser.add_argument(
        '--anos',
        nargs='+',
        type=int,
        metavar='ANO',
        help='Anos a processar (padrão: 2010–2024). Repassado a datasus_dados.py e ibge_populacao.py.',
    )
    parser.add_argument(
        '--estados',
        nargs='+',
        metavar='UF',
        help='Siglas dos estados (padrão: todos os 27). Repassado a datasus_dados.py e ibge_dados_municipios.py.',
    )
    parser.add_argument(
        '--apenas-converter',
        action='store_true',
        help='Pula downloads e converte apenas arquivos já baixados. Repassado a datasus_dados.py e ibge_populacao.py.',
    )
    parser.add_argument(
        '--validacao',
        action='store_true',
        help='Verifica consistência dos layouts de coluna. Repassado a datasus_dados.py, ibge_populacao.py e datasus_cid10.py.',
    )

    args = parser.parse_args()

    anos_args     = ['--anos']            + [str(a) for a in args.anos] if args.anos else []
    estados_args  = ['--estados']         + args.estados                if args.estados else []
    conv_args     = ['--apenas-converter']                              if args.apenas_converter else []
    valid_args    = ['--validacao']                                     if args.validacao else []

    # datasus_dados.py aceita: --sistema, --anos, --estados, --apenas-converter, --validacao
    run(BRONZE / 'datasus_dados.py', '--sistema', 'SIM', *anos_args, *estados_args, *conv_args, *valid_args)

    # ibge_dados_municipios.py aceita: --estados
    run(BRONZE / 'ibge_dados_municipios.py', *estados_args)

    # ibge_populacao.py aceita: --anos, --apenas-converter, --validacao
    run(BRONZE / 'ibge_populacao.py', *anos_args, *conv_args, *valid_args)

    # datasus_cid10.py aceita: --apenas-converter, --validacao
    run(BRONZE / 'datasus_cid10.py', *conv_args, *valid_args)


if __name__ == '__main__':
    main()