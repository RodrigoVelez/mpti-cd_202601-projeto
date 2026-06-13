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

A pasta `dados/` é gerada localmente pela execução dos scripts e **não é versionada no repositório**. Para reproduzir o ambiente de dados, execute os scripts descritos na seção [Execução dos Scripts de Coleta](#execução-dos-scripts-de-coleta).

Scripts entregues nesta etapa:

| Script | Descrição |
|--------|-----------|
| [`datasus.py`](datasus.py) | Baixa arquivos DBC do FTP do DataSUS (SIM/CID-10) e converte para CSV. Cobre todos os 27 estados, de 2010 a 2024. |
| [`ibge_populacao.py`](ibge_populacao.py) | Baixa ZIPs de projeções populacionais do IBGE via FTP do DataSUS, extrai os DBFs e converte para CSV. Período: 2010–2024. |
| [`ibge_dados_municipios.py`](ibge_dados_municipios.py) | Coleta o cadastro completo de municípios via API REST do IBGE, grava o JSON bruto e o CSV tabular com colunas normalizadas. |

## Estrutura do Repositório

```
.
├── datasus.py                  # Coleta do DataSUS (SIM/CID-10) via FTP
├── ibge_populacao.py           # Coleta de população IBGE via FTP DataSUS
├── ibge_dados_municipios.py    # Coleta do cadastro de municípios via API IBGE
├── documentos/
│   ├── Contexto_Projeto_Coencis_de_Dados.pdf
│   └── Cronograma_Projeto_Ciencia_de_Dados.pdf
└── dados/                      # Gerado localmente — NÃO versionado
    ├── SIM/
    │   ├── dbc/YYYY/           # Arquivos brutos do DataSUS por ano
    │   └── csv/YYYY/           # Declarações de óbito convertidas para CSV
    ├── ibge_populacao/
    │   ├── zip/YYYY/           # ZIPs baixados do FTP
    │   ├── dbf/YYYY/           # DBFs extraídos dos ZIPs
    │   └── csv/YYYY/           # Projeções populacionais em CSV
    └── ibge_dados_municipios/
        ├── json/               # Resposta bruta da API IBGE
        └── csv/                # Cadastro de municípios em CSV
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

### Carregar todos os datasets de uma vez

**macOS / Linux**
```bash
python3 datasus.py --sistema SIM && \
python3 ibge_populacao.py && \
python3 ibge_dados_municipios.py
```

**Windows** (Prompt de Comando)
```bat
python datasus.py --sistema SIM && python ibge_populacao.py && python ibge_dados_municipios.py
```

**Windows** (PowerShell)
```powershell
python datasus.py --sistema SIM; python ibge_populacao.py; python ibge_dados_municipios.py
```

> O download do SIM para todos os estados e anos (2010–2024) pode demorar bastante, pois são ~375 arquivos DBC via FTP. Use `--estados` e `--anos` para limitar o escopo durante testes.

### 1. DataSUS — Mortalidade (SIM/CID-10)

**macOS / Linux**
```bash
# Todos os estados, 2010–2024 (padrão)
python3 datasus.py --sistema SIM

# Filtrar estados e anos específicos
python3 datasus.py --sistema SIM --anos 2020 2021 2022 --estados SP RJ MG PB

# Apenas converter DBCs já baixados (sem novo download)
python3 datasus.py --sistema SIM --apenas-converter

# Verificar consistência dos layouts de coluna entre os CSVs gerados
python3 datasus.py --sistema SIM --validacao

# Listar todos os sistemas disponíveis no script
python3 datasus.py --listar-sistemas
```

**Windows**
```bat
python datasus.py --sistema SIM
python datasus.py --sistema SIM --anos 2020 2021 2022 --estados SP RJ MG PB
python datasus.py --sistema SIM --apenas-converter
python datasus.py --sistema SIM --validacao
python datasus.py --listar-sistemas
```

Saída: `dados/SIM/dbc/YYYY/DO{UF}{YYYY}.dbc` → `dados/SIM/csv/YYYY/DO{UF}{YYYY}.csv`

### 2. IBGE — Projeções Populacionais (POPSVS)

**macOS / Linux**
```bash
python3 ibge_populacao.py                        # todos os anos, 2010–2024 (padrão)
python3 ibge_populacao.py --anos 2020 2021 2022  # anos específicos
python3 ibge_populacao.py --apenas-converter     # sem novo download
python3 ibge_populacao.py --validacao            # verificar consistência
```

**Windows**
```bat
python ibge_populacao.py
python ibge_populacao.py --anos 2020 2021 2022
python ibge_populacao.py --apenas-converter
python ibge_populacao.py --validacao
```

Saída: `dados/ibge_populacao/csv/YYYY/POP{YY}.csv`

### 3. IBGE — Cadastro de Municípios (API REST)

**macOS / Linux**
```bash
python3 ibge_dados_municipios.py                       # todos os municípios (5.570)
python3 ibge_dados_municipios.py --estados PB PE CE RN # filtrar por estado(s)
```

**Windows**
```bat
python ibge_dados_municipios.py
python ibge_dados_municipios.py --estados PB PE CE RN
```

Saída: `dados/ibge_dados_municipios/json/municipios.json` e `dados/ibge_dados_municipios/csv/municipios.csv`

## Cronograma

| Semana | Período | Etapa | Marco |
|--------|---------|-------|-------|
| 1 | 02/06–08/06 | Seleção e coleta das fontes | Repositório + scripts de coleta ✓ |
| 2–3 | 09/06–22/06 | Preparação e integração dos dados | Datasets limpos + dataset consolidado + dicionário de dados |
| 4 | 23/06–29/06 | Análise e modelagem | Notebook de EDA, clustering e visualizações |
| 5 | 30/06–06/07 | Redação e fechamento | Relatório final + notebook reproduzível |
| 6 | 07/07–14/07 | Apresentação | Slides e apresentação oral |

**Entrega final:** 06/07/2026 · **Apresentação:** 07/07 ou 14/07/2026
