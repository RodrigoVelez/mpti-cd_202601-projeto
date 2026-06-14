# Análise de Mortalidade por DCNT nos Municípios Brasileiros

**Disciplina:** Ciência de Dados — MPTI/IFPB — 2026.1  
**Docentes:** Damires Souza e Alex Cunha  
**Equipe:** Rodrigo de Queiroz Gonçalves Velez · Caio Jordan de Lima Maia

---

## Contexto

As Doenças Crônicas Não Transmissíveis (DCNT) — cardiovasculares, diabetes, câncer e doenças respiratórias crônicas — são responsáveis por uma parcela significativa da mortalidade no Brasil. A análise desses dados em nível municipal é fundamental para apoiar políticas públicas de saúde, permitindo identificar desigualdades regionais e orientar a distribuição de recursos.

Este projeto integra bases de dados públicas (DataSUS e IBGE) para identificar padrões e perfis municipais de mortalidade por DCNT, aplicando técnicas de ciência de dados: limpeza e integração de dados heterogêneos, análise exploratória, clustering e visualização de resultados.

## Problema de Ciência de Dados

Identificar padrões e perfis de municípios brasileiros em relação à mortalidade por DCNT, a partir da integração de diferentes bases de dados públicas. Especificamente:

- Analisar a distribuição da mortalidade por DCNT em nível municipal
- Identificar agrupamentos de municípios com características semelhantes (clustering)
- Explorar relações entre indicadores de mortalidade e variáveis demográficas

## Fontes de Dados

| Fonte | Descrição | Acesso | Formato bruto |
|-------|-----------|--------|---------------|
| **DataSUS / SIM** | Sistema de Informações sobre Mortalidade — declarações de óbito com causas por CID-10, por município, estado e ano | FTP `ftp.datasus.gov.br` | DBC |
| **IBGE / POPSVS** | Projeções populacionais por município, disponibilizadas via FTP do DataSUS | FTP `ftp.datasus.gov.br` | ZIP/DBF |
| **IBGE API REST** | Cadastro oficial de municípios com código IBGE, microrregião, mesorregião e UF | API `servicodados.ibge.gov.br` | JSON |

Todos os dados são secundários, já agregados e anonimizados pelos órgãos responsáveis — o projeto está em conformidade com a LGPD.

## Entrega da Semana 1 (02/06–08/06): Seleção e Coleta das Fontes

Esta etapa corresponde ao **marco inicial do projeto**: repositório configurado, fontes documentadas e scripts de coleta implementados e validados.

A pasta `dados/` é gerada localmente pela execução dos scripts e **não é versionada no repositório**. Para reproduzir o ambiente de dados, execute o `exec.py` ou os scripts individualmente conforme descrito na seção [Execução dos Scripts de Coleta](#execução-dos-scripts-de-coleta).

Scripts entregues nesta etapa:

| Script | Descrição |
|--------|-----------|
| [`scripts/exec.py`](scripts/exec.py) | Orquestrador — executa os três scripts da camada Bronze em sequência. |
| [`scripts/1-bronze/datasus.py`](scripts/1-bronze/datasus.py) | Baixa arquivos DBC do FTP do DataSUS (SIM/CID-10) e converte para CSV. Cobre todos os 27 estados, de 2010 a 2024. |
| [`scripts/1-bronze/ibge_dados_municipios.py`](scripts/1-bronze/ibge_dados_municipios.py) | Coleta o cadastro completo de municípios via API REST do IBGE, grava o JSON bruto e o CSV tabular com colunas normalizadas. |
| [`scripts/1-bronze/ibge_populacao.py`](scripts/1-bronze/ibge_populacao.py) | Baixa ZIPs de projeções populacionais do IBGE via FTP do DataSUS, extrai os DBFs e converte para CSV. Período: 2010–2024. |

## Arquitetura de Dados — Medallion

Os scripts e dados seguem a arquitetura Medallion com três camadas:

| Camada | Pasta de scripts | Pasta de dados | Descrição |
|--------|-----------------|----------------|-----------|
| **Bronze** | scripts/1-bronze/ | dados/1-bronze/ | Dados brutos coletados das fontes, sem transformação |
| **Prata** | scripts/2-prata/ | dados/2-prata/ | Dados limpos, padronizados e integrados *(próximas semanas)* |
| **Ouro** | scripts/3-ouro/ | dados/3-ouro/ | Dataset analítico consolidado, pronto para análise *(próximas semanas)* |

## Estrutura do Repositório

```
.
├── scripts/
│   ├── exec.py                      # Orquestrador — executa toda a camada Bronze
│   ├── 1-bronze/
│   │   ├── datasus.py               # Coleta SIM/CID-10 via FTP DataSUS
│   │   ├── ibge_dados_municipios.py # Coleta cadastro de municípios via API IBGE
│   │   └── ibge_populacao.py        # Coleta projeções populacionais via FTP DataSUS
│   ├── 2-prata/                     # Scripts de limpeza e integração (próximas semanas)
│   └── 3-ouro/                      # Scripts de consolidação analítica (próximas semanas)
├── documentos/
│   ├── Contexto_Projeto_Coencis_de_Dados.pdf
│   └── Cronograma_Projeto_Ciencia_de_Dados.pdf
└── dados/                           # Gerado localmente — NÃO versionado
    ├── 1-bronze/
    │   ├── SIM/
    │   │   ├── dbc/YYYY/            # Arquivos brutos do DataSUS por ano
    │   │   └── csv/YYYY/            # Declarações de óbito convertidas para CSV
    │   ├── ibge_dados_municipios/
    │   │   ├── json/                # Resposta bruta da API IBGE
    │   │   └── csv/                 # Cadastro de municípios em CSV
    │   └── ibge_populacao/
    │       ├── zip/YYYY/            # ZIPs baixados do FTP
    │       ├── dbf/YYYY/            # DBFs extraídos dos ZIPs
    │       └── csv/YYYY/            # Projeções populacionais em CSV
    ├── 2-prata/                     # Dados limpos e integrados (próximas semanas)
    └── 3-ouro/                      # Dataset analítico consolidado (próximas semanas)
```

## Pré-requisitos

Python 3.11+ instalado e disponível no PATH.

**macOS / Linux**
```bash
pip3 install pandas pyreaddbc dbfread
```

**Windows** (Prompt de Comando ou PowerShell)
```bat
pip install pandas pyreaddbc dbfread
```

> No Windows, `python` e `pip` já apontam para o Python 3 instalado. No macOS/Linux, use sempre `python3` e `pip3` para evitar conflito com o Python 2 do sistema.

## Execução dos Scripts de Coleta

### Carregar todos os datasets de uma vez com exec.py

O `exec.py` executa os três scripts da camada Bronze em sequência (DataSUS SIM → municípios IBGE → população IBGE) e repassa automaticamente cada argumento apenas aos scripts que o aceitam:

| Argumento | datasus.py | ibge_populacao.py | ibge_dados_municipios.py |
|-----------|:---:|:---:|:---:|
| *--anos* | ✓ | ✓ | — |
| *--estados* | ✓ | — | ✓ |
| *--apenas-converter* | ✓ | ✓ | — |
| *--validacao* | ✓ | ✓ | — |

**macOS / Linux**
```bash
# Carga completa (todos os estados, 2010–2024)
python3 scripts/exec.py

# Limitar anos e estados (útil para testes)
python3 scripts/exec.py --anos 2022 2023 --estados PB PE CE RN

# Apenas converter arquivos já baixados, sem novo download
python3 scripts/exec.py --apenas-converter

# Verificar consistência dos layouts de coluna
python3 scripts/exec.py --validacao
```

**Windows** (Prompt de Comando ou PowerShell)
```bat
python scripts/exec.py
python scripts/exec.py --anos 2022 2023 --estados PB PE CE RN
python scripts/exec.py --apenas-converter
python scripts/exec.py --validacao
```

> O download do SIM para todos os estados e anos (2010–2024) pode demorar bastante, pois são ~375 arquivos DBC via FTP. Use `--estados` e `--anos` para reduzir o escopo durante testes.

### 1. DataSUS — Mortalidade (SIM/CID-10)

**macOS / Linux**
```bash
# Todos os estados, 2010–2024 (padrão)
python3 scripts/1-bronze/datasus.py --sistema SIM

# Filtrar estados e anos específicos
python3 scripts/1-bronze/datasus.py --sistema SIM --anos 2020 2021 2022 --estados SP RJ MG PB

# Apenas converter DBCs já baixados (sem novo download)
python3 scripts/1-bronze/datasus.py --sistema SIM --apenas-converter

# Verificar consistência dos layouts de coluna entre os CSVs gerados
python3 scripts/1-bronze/datasus.py --sistema SIM --validacao

# Listar todos os sistemas disponíveis no script
python3 scripts/1-bronze/datasus.py --listar-sistemas
```

**Windows**
```bat
python scripts/1-bronze/datasus.py --sistema SIM
python scripts/1-bronze/datasus.py --sistema SIM --anos 2020 2021 2022 --estados SP RJ MG PB
python scripts/1-bronze/datasus.py --sistema SIM --apenas-converter
python scripts/1-bronze/datasus.py --sistema SIM --validacao
python scripts/1-bronze/datasus.py --listar-sistemas
```

Saída: `dados/1-bronze/SIM/dbc/YYYY/DO{UF}{YYYY}.dbc` → `dados/1-bronze/SIM/csv/YYYY/DO{UF}{YYYY}.csv`

### 2. IBGE — Cadastro de Municípios (API REST)

**macOS / Linux**
```bash
python3 scripts/1-bronze/ibge_dados_municipios.py                       # todos os municípios (5.570)
python3 scripts/1-bronze/ibge_dados_municipios.py --estados PB PE CE RN # filtrar por estado(s)
```

**Windows**
```bat
python scripts/1-bronze/ibge_dados_municipios.py
python scripts/1-bronze/ibge_dados_municipios.py --estados PB PE CE RN
```

Saída: `dados/1-bronze/ibge_dados_municipios/json/municipios.json` e `dados/1-bronze/ibge_dados_municipios/csv/municipios.csv`

### 3. IBGE — Projeções Populacionais (POPSVS)

**macOS / Linux**
```bash
python3 scripts/1-bronze/ibge_populacao.py                        # todos os anos, 2010–2024 (padrão)
python3 scripts/1-bronze/ibge_populacao.py --anos 2020 2021 2022  # anos específicos
python3 scripts/1-bronze/ibge_populacao.py --apenas-converter     # sem novo download
python3 scripts/1-bronze/ibge_populacao.py --validacao            # verificar consistência
```

**Windows**
```bat
python scripts/1-bronze/ibge_populacao.py
python scripts/1-bronze/ibge_populacao.py --anos 2020 2021 2022
python scripts/1-bronze/ibge_populacao.py --apenas-converter
python scripts/1-bronze/ibge_populacao.py --validacao
```

Saída: `dados/1-bronze/ibge_populacao/csv/YYYY/POP{YY}.csv`

## Cronograma

| Semana | Período | Etapa | Marco |
|--------|---------|-------|-------|
| 1 | 02/06–08/06 | Seleção e coleta das fontes | Repositório + scripts de coleta ✓ |
| 2–3 | 09/06–22/06 | Preparação e integração dos dados | Datasets limpos + dataset consolidado + dicionário de dados |
| 4 | 23/06–29/06 | Análise e modelagem | Notebook de EDA, clustering e visualizações |
| 5 | 30/06–06/07 | Redação e fechamento | Relatório final + notebook reproduzível |
| 6 | 07/07–14/07 | Apresentação | Slides e apresentação oral |

**Entrega final:** 06/07/2026 · **Apresentação:** 07/07 ou 14/07/2026