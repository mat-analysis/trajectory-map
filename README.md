# Estudando Math Model - Visualização de Trajetórias e Movelets

Este projeto implementa uma aplicação web interativa para visualização de trajetórias geográficas e descoberta de movelets (padrões de movimento) usando o framework Dash e bibliotecas de modelagem matemática.

## Funcionalidades

- **Visualização de Mapa Interativo**: Exibe trajetórias no mapa.
- **Upload de Dados**: Suporte para carregamento de arquivos CSV, Parquet, ZIP, TS, XES e JSON.
- **Filtros Dinâmicos**: Seleção de colunas para tooltips personalizados.
- **Destaque de Movelets**: Segmentos de movelets são destacados em vermelho no mapa.

## Estrutura do Projeto

```
EstudandoMathModel/
├── funcoesAuxiliares.py    # Funções auxiliares para formatação e extração
├── mapa.py                 # Aplicação principal Dash
├── mov.py                  # Módulo de descoberta e carregamento de movelets
├── uploadArquivo.py        # Parsing de arquivos carregados
├── sample/                 # Dados de exemplo
│   ├── data/
│   └── results/
└── README.md               # Este arquivo
```

## Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/PedroVilbert/FerramentaVisualizacaoMATs
   cd EstudandoMathModel
   ```

2. Instale as dependências:
   ```bash
   pip install dash plotly pandas matdata matmodel
   ```

3. Certifique-se de ter Java instalado para execução do algoritmo de movelets.

## Como Usar

1. Execute a aplicação:
   ```bash
   python mapa.py
   ```

2. Abra o navegador em `http://127.0.0.1:8050/`

3. Use os controles para:
   - Selecionar colunas para tooltips
   - Definir intervalo de trajetórias
   - Carregar novos dados via upload

## Módulos

### funcoesAuxiliares.py
- `icone_avaliacao(av)`: Converte pontuação numérica em estrelas
- `icones_clima(clima)`: Mapeia condição meteorológica para emoji
- `extrair_valor(coluna, p, data_desc)`: Extrai valores de pontos de trajetória

### mov.py
- `executar_descoberta_movelets()`: Executa descoberta de movelets
- `carregar_movelets_disponveis()`: Carrega movelets de arquivos JSON

### uploadArquivo.py
- `parse_contents(contents, filename, date)`: Processa arquivos carregados

### mapa.py
Aplicação Dash principal com callbacks para atualização do mapa, processamento de upload e controle de filtros.

## Dependências

- dash
- plotly
- pandas
- matdata
- matmodel

## Dataset

O projeto usa o dataset FoursquareNYC por padrão, mas suporta upload de dados customizados.

