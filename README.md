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

---

## Fontes de Dados

| Fonte | Descrição | Acesso | Formato bruto |
|-------|-----------|--------|---------------|
| **DataSUS / SIM** | Sistema de Informações sobre Mortalidade — declarações de óbito com causas por CID-10, por município, estado e ano | FTP `ftp.datasus.gov.br` | DBC |
| **DataSUS / CID-10 v2008** | Tabelas de referência CID-10: capítulos, grupos, categorias e subcategorias | HTTP `www2.datasus.gov.br` | ZIP/CSV |
| **DataSUS / CID-10 FTP** | Tabelas de referência CID-10 em DBF | FTP `ftp.datasus.gov.br` | DBF |
| **IBGE / POPSVS** | Projeções populacionais por município via FTP do DataSUS | FTP `ftp.datasus.gov.br` | ZIP/DBF |
| **IBGE API REST** | Cadastro oficial de municípios com código IBGE, microrregião, mesorregião e UF | API `servicodados.ibge.gov.br` | JSON |

Todos os dados são secundários, já agregados e anonimizados pelos órgãos responsáveis — o projeto está em conformidade com a LGPD.

---

## Arquitetura Medallion

O pipeline segue a arquitetura Medallion com três camadas, implementado integralmente no notebook [`projeto_cd_2026_01.ipynb`](projeto_cd_2026_01.ipynb):

```
🥉 Bronze  →  🥈 Prata  →  🥇 Ouro
(coleta)      (limpeza)    (análise)
```

| Camada | Pasta de dados | Descrição |
|--------|----------------|-----------|
| **Bronze** | `dados/1-bronze/` | Dados brutos coletados das fontes, convertidos para Parquet sem transformação de conteúdo |
| **Prata** | `dados/2-prata/` | Dados limpos, padronizados e filtrados por fonte |
| **Ouro** | `dados/3-ouro/` | Dataset analítico enriquecido com joins entre todas as fontes |

> A pasta `dados/` é gerada localmente pela execução do notebook e **não é versionada no repositório**.

---

## Pipeline de Execução

Todo o pipeline é executado no notebook [`projeto_cd_2026_01.ipynb`](projeto_cd_2026_01.ipynb). Execute as células em ordem.

### Pré-requisitos

```bash
pip install pandas pyarrow pyreaddbc dbfread
```

---

## Camada Bronze — Coleta e Conversão

### Bronze 1/4 — DataSUS SIM (Declarações de Óbito)

Acessa o FTP `ftp.datasus.gov.br` no diretório `/dissemin/publicos/SIM/CID10/DORES/` e baixa um arquivo DBC por estado por ano no formato `DO{UF}{ANO}.dbc`. Cada DBC é convertido para Parquet via `pyreaddbc` + `dbfread`. O DBC é excluído após conversão bem-sucedida.

- **Período:** 2010–2024 (15 exercícios)
- **Estados:** 27 UFs
- **Saída:** `dados/1-bronze/SIM/parquet/{ANO}/DO{UF}{ANO}.parquet`

### Bronze 2/4 — IBGE Municípios (API REST)

Consulta a API REST do IBGE e baixa o cadastro completo de 5.570 municípios com código IBGE, nome, UF e região.

- **Saída:** `dados/1-bronze/ibge_dados_municipios/parquet/municipios.parquet`

### Bronze 3/4 — IBGE Projeções Populacionais

Baixa do FTP do DataSUS os arquivos ZIP de projeções populacionais, extrai os DBFs e converte para Parquet.

- **Período:** 2010–2024 (15 exercícios)
- **Saída:** `dados/1-bronze/ibge_populacao/parquet/{ANO}/POP{AA}.parquet`

### Bronze 4/4 — CID-10 (tabelas de referência)

Baixa as tabelas de referência CID-10 de duas fontes independentes:

| Fonte | Acesso | Saída |
|-------|--------|-------|
| `v2008` | HTTP `www2.datasus.gov.br` | `dados/1-bronze/cid_10_datasus_v2008/parquet/` |
| `ftp` | FTP `ftp.datasus.gov.br` | `dados/1-bronze/cid_10_datasus_ftp/parquet/` |

**Estrutura Bronze gerada:**

```
dados/1-bronze/
├── SIM/
│   └── parquet/
│       ├── 2010/  DO{UF}2010.parquet  (até 27 arquivos)
│       ├── ···
│       └── 2024/  DO{UF}2024.parquet
├── ibge_dados_municipios/
│   └── parquet/municipios.parquet
├── ibge_populacao/
│   └── parquet/
│       ├── 2010/  POP10.parquet
│       ├── ···
│       └── 2024/  POP24.parquet
├── cid_10_datasus_v2008/
│   └── parquet/  (CID-10-CAPITULOS, GRUPOS, CATEGORIAS, SUBCATEGORIAS, CID-O-*)
└── cid_10_datasus_ftp/
    └── parquet/  (CID10.parquet, CIDCAP10.parquet)
```

---

## Camada Prata — Limpeza, Normalização e Filtros

### Prata 1/4 — CID-10

Consolida as tabelas CID-10 do Bronze em um único dataset normalizado com hierarquia completa.

- **Ajustes:** remoção de prefixos numéricos das descrições, derivação de capítulo e grupo por intervalo de código
- **Schema:** `codigo_capitulo`, `descricao_capitulo`, `codigo_grupo`, `descricao_grupo`, `codigo_categoria`, `descricao_categoria`, `codigo_cid10`, `descricao_cid10`
- **Saída:** `dados/2-prata/CID10/cid10.parquet` + `.csv`

### Prata 2/4 — IBGE Municípios

Normaliza o cadastro de municípios e gera o código IBGE de 6 dígitos (`codigo_municipio_6c`) necessário para o join com o SIM.

- **Ajustes:** conversão de tipos, strip de espaços, extração de `codigo_municipio_6c = codigo_municipio[:6]`
- **Schema:** `codigo_municipio` (7c), `codigo_municipio_6c`, `nome_municipio`, `codigo_estado`, `sigla_estado`, `nome_estado`, `codigo_regiao`, `sigla_regiao`, `nome_regiao`
- **Saída:** `dados/2-prata/IBGE/ibge_municipios.parquet` + `.csv`

### Prata 3/4 — IBGE Projeções Populacionais

Agrega população por município, exercício e sexo (soma todas as faixas etárias de cada arquivo anual).

- **Mapeamento de sexo:** `1→M`, `2→F`, `0/9→I`
- **Schema:** `codigo_municipio`, `exercicio`, `sexo` (M/F/I), `populacao`
- **Ordenação:** `exercicio → codigo_municipio → sexo`
- **Saída:** `dados/2-prata/IBGE/ibge_populacao.parquet` + `.csv`

### Prata 4/4 — DataSUS SIM (Declarações de Óbito)

Agrega óbitos por município, causa básica (CID-10), sexo e exercício. Classifica cada grupo como DCNT ou não. Gera um arquivo por exercício, consolidando todos os estados.

**Filtros aplicados (registros removidos, em ordem):**

| # | Filtro | Campo | Critério |
|---|--------|-------|----------|
| 1 | Apenas óbitos não-fetais | `TIPOBITO` | ≠ `2` |
| 2 | Município de ocorrência preenchido | `CODMUNOCOR` | vazio ou `nan` |
| 3 | Causa básica preenchida | `CAUSABAS` | vazio ou `nan` |
| 4 | Município válido no IBGE | `CODMUNOCOR` | código não existe na tabela de municípios Prata |

Ao final do processamento é exibido um **resumo consolidado** com a contagem e o percentual de cada filtro sobre o total bruto de registros lidos.

**Critério de classificação DCNT (`dcnt = 'S'`):**

| Faixa CID-10 | Grupo |
|---|---|
| I00–I99 | Doenças cardiovasculares |
| C00–C97 | Neoplasias malignas |
| J30–J98 (exceto J36) | Doenças respiratórias crônicas |
| E10–E14 | Diabetes mellitus |

- **Schema:** `sexo`, `codigo_municipio`, `cid10`, `exercicio`, `dcnt`, `arquivo_origem`, `obitos`
- **Ordenação:** `codigo_municipio → cid10 → sexo`
- **Saída:** `dados/2-prata/SIM/{ANO}/datasus_sim_{ANO}.parquet` + `.csv`

**Estrutura Prata gerada:**

```
dados/2-prata/
├── CID10/
│   ├── cid10.parquet
│   └── cid10.csv
├── IBGE/
│   ├── ibge_municipios.parquet  ├── ibge_municipios.csv
│   ├── ibge_populacao.parquet   └── ibge_populacao.csv
└── SIM/
    ├── 2010/  datasus_sim_2010.parquet + .csv
    ├── ···
    └── 2024/  datasus_sim_2024.parquet + .csv
```

---

## Camada Ouro — Integração e Dataset Analítico

### Ouro 1/2 — SIM × Municípios × CID-10

Para cada exercício, realiza joins entre os três datasets prata, enriquece com hierarquia geográfica e classificação CID-10, e gera o arquivo analítico final.

**Joins realizados:**

| Join | Chave esquerda | Chave direita |
|------|---------------|---------------|
| SIM × Municípios | `sim.codigo_municipio` | `mun.codigo_municipio_6c` |
| resultado × CID-10 | `sim.cid10` | `cid.codigo_cid10` |

Todos os municípios na Prata são garantidamente válidos (filtro 4 aplicado em Prata 4/4), portanto o join com `mun` é sempre resolvido. O merge funciona como inner join efetivo — qualquer linha sem correspondência indica problema nos dados de origem e é reportado como `[ERRO]`.

**Ordenação:** `codigo_municipio → codigo_cid10 → sexo`

### Ouro 2/2 — Populacao × Municípios

Enriquece a população Prata com a hierarquia geográfica completa (códigos de 6 e 7 dígitos, estado, região). Serve como referência de população para o cálculo de taxas na camada Ouro — o atributo derivado de taxa usa este arquivo.

**Join:** `pop.codigo_municipio (6c) = mun.codigo_municipio_6c`

- **Schema:** `exercicio`, `codigo_municipio_6c`, `codigo_municipio` (7c), `nome_municipio`, `sigla_estado`, `nome_estado`, `sigla_regiao`, `nome_regiao`, `sexo`, `populacao`
- **Ordenação:** `exercicio → sigla_estado → codigo_municipio_6c → sexo`
- **Saída:** `dados/3-ouro/IBGE/populacao_municipio.parquet` + `.csv`

| # | Coluna | Tipo | Descrição |
|---|--------|------|-----------|
| 1 | `exercicio` | string | Ano da projeção populacional |
| 2 | `codigo_municipio_6c` | string | Código IBGE 6 dígitos (chave de join com SIM) |
| 3 | `codigo_municipio` | string | Código IBGE 7 dígitos oficial |
| 4 | `nome_municipio` | string | Nome oficial do município |
| 5 | `sigla_estado` | string | Sigla da UF |
| 6 | `nome_estado` | string | Nome completo da UF |
| 7 | `sigla_regiao` | string | Sigla da grande região |
| 8 | `nome_regiao` | string | Nome da grande região |
| 9 | `sexo` | string | M / F / I |
| 10 | `populacao` | int | Projeção populacional para o exercício |

**Estrutura Ouro gerada:**

```
dados/3-ouro/
├── SIM/
│   ├── 2010/  sim_ouro_2010.parquet + .csv
│   ├── ···
│   ├── 2024/  sim_ouro_2024.parquet + .csv
│   └── taxa_dcnt_municipio.parquet / .csv   ← atributo derivado
└── IBGE/
    ├── populacao_municipio.parquet
    └── populacao_municipio.csv
```

---

## Dicionário de Dados — Dataset Ouro (`sim_ouro_{ANO}`)

Granularidade: **uma linha por combinação de** município × CID-10 × sexo × arquivo de origem.

| # | Coluna | Tipo | Origem | Descrição |
|---|--------|------|--------|-----------|
| 1 | `sexo` | string | SIM | Sexo do falecido: `M` · `F` · `I` (ignorado) |
| 2 | `codigo_municipio` | string | SIM | Código IBGE 6 dígitos do município de ocorrência (CODMUNOCOR) |
| 3 | `codigo_municipio_6c` | string | Municípios | Código IBGE 6 dígitos validado na tabela de municípios |
| 4 | `nome_municipio` | string | Municípios | Nome oficial do município |
| 5 | `sigla_estado` | string | Municípios | Sigla da UF |
| 6 | `nome_estado` | string | Municípios | Nome completo da UF |
| 7 | `sigla_regiao` | string | Municípios | Sigla da grande região |
| 8 | `nome_regiao` | string | Municípios | Nome da grande região |
| 9 | `codigo_cid10` | string | CID-10 | Código da causa básica do óbito |
| 10 | `descricao_cid10` | string | CID-10 | Descrição da causa básica |
| 11 | `exercicio` | string | SIM | Ano de ocorrência do óbito |
| 12 | `dcnt` | string | Calculado | `S` = causa DCNT · `N` = demais causas |
| 13 | `arquivo_origem` | string | SIM | Arquivo bronze de origem (ex.: `DOSP2010` = São Paulo 2010) |
| 14 | `obitos` | int | SIM | Contagem de óbitos agregada por grupo |

---

## Atributo Derivado — Taxa de Mortalidade DCNT por 100 mil habitantes

Calcula a taxa epidemiológica padrão para cada município e exercício (soma ambos os sexos).

**Fórmula:** `taxa_dcnt_100k = (obitos_dcnt / populacao) × 100.000`

| # | Coluna | Tipo | Descrição |
|---|--------|------|-----------|
| 1 | `exercicio` | string | Ano |
| 2 | `codigo_municipio` | string | Código IBGE 6 dígitos |
| 3 | `nome_municipio` | string | Nome do município |
| 4 | `sigla_estado` | string | Sigla da UF |
| 5 | `nome_estado` | string | Nome da UF |
| 6 | `sigla_regiao` | string | Sigla da região |
| 7 | `nome_regiao` | string | Nome da região |
| 8 | `obitos_dcnt` | int | Total de óbitos por DCNT |
| 9 | `populacao` | int | População total do município no exercício |
| 10 | `taxa_dcnt_100k` | float | Taxa de mortalidade DCNT por 100 mil habitantes |

- **Ordenação:** exercício ascendente, taxa descendente
- **Fonte de população:** `dados/3-ouro/IBGE/populacao_municipio.parquet` (Ouro 2/2)
- **Saída:** `dados/3-ouro/SIM/taxa_dcnt_municipio.parquet` + `.csv`

---

## Estrutura do Repositório

```
.
├── projeto_cd_2026_01.ipynb          # Notebook principal — executa todo o pipeline
├── documentos/
│   └── projeto/
│       ├── Contexto_Projeto_Ciencia_de_Dados.pdf
│       ├── Cronograma_Projeto_Ciencia_de_Dados.pdf
│       └── Roteiro do projeto de Ciência de Dados.pdf
└── dados/                            # Gerado localmente — NÃO versionado
    ├── 1-bronze/
    ├── 2-prata/
    └── 3-ouro/
```

---

## Cronograma

| Semana | Período | Etapa | Marco | Status |
|--------|---------|-------|-------|--------|
| 1 | 02/06–08/06 | Seleção e coleta das fontes | Repositório + coleta Bronze implementada | ✅ |
| 2–3 | 09/06–22/06 | Preparação, integração e consolidação | Prata + Ouro + dicionário de dados | ✅ |
| 4 | 23/06–29/06 | Análise e modelagem | EDA, clustering e visualizações | 🔜 |
| 5 | 30/06–06/07 | Redação e fechamento | Relatório final + notebook reproduzível | 🔜 |
| 6 | 07/07–14/07 | Apresentação | Slides e apresentação oral | 🔜 |

**Marcos-chave:**

| Data | Marco | Status |
|------|-------|--------|
| 22/06/2026 | Dados limpos e prontos para integração | ✅ |
| 22/06/2026 | Dataset final consolidado e dicionário fechado | ✅ |
| 29/06/2026 | Análises e visualizações concluídas | 🔜 |
| 06/07/2026 | Entrega do relatório final, notebook e artefatos | 🔜 |
| 07/07 ou 14/07/2026 | Apresentação do projeto | 🔜 |
