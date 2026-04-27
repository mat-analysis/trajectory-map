"""Aplicação Dash para visualização de trajetórias e movelets.

- Carrega dataset e movelets
- Renderiza mapa interativo com linhas e pontos
- Destaca segmentos de movelets em vermelho
- Suporta upload de CSV/parquet/zip/ts/json e atualização dinâmica de colunas de tooltip
"""

from io import StringIO
import dash  # Importa a biblioteca Dash para criação da aplicação web interativa
from collections import defaultdict
import plotly.graph_objects as go  # Importa plotly.graph_objects para gráficos customizados
from dash import Dash, dcc, html, Input, Output, State  # Importa componentes do Dash para construir layout e callbacks
import os
from dash import dcc
import re
import pandas as pd  # Importa pandas explicitamente

#bibliotecas mat
from matdata.dataset import *  # Importa funções para carregar datasets do pacote matdata
from matmodel.util.parsers import df2trajectory  # Importa função para converter DataFrame em trajetórias
from matdata.dataset import load_ds

#outros arquivos 
import funcoesAuxiliares as fca #Funções auxiliares para o mapa
import uploadArquivo as upa #Funções para o upload de arquivos
import mov #Módulo para carregar movelets

# os.system('cls')
# import inspect
# print(inspect.getsource(df2trajectory))

# Carregando dados das trajetorias
ds = 'mat.FoursquareNYC'  # Define o nome do dataset a ser carregado
df = load_ds(ds, sample_size=0.25)  # Carrega uma amostra de 25% do dataset
T, data_desc = df2trajectory(df)  # Converte DataFrame em múltiplas trajetórias (lista T)

# Carregando movelets disponíveis
traj_movelets = mov.carregar_movelets_disponveis()  # Carrega dicionário de movelets por trajetória

#-----------------------------------
# Inicia app
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css'] #Estilo para o botão
app = Dash(__name__, external_stylesheets=external_stylesheets)  # Instancia aplicação Dash

# Layout
app.layout = html.Div([  # Define layout principal como uma Div
    
    dcc.Dropdown(  # Checklist para seleção das colunas a mostrar no tooltip
        id='filtros-hover',  # Id do componente para callbacks
        options=[],
        value=[],  # Opções pré-selecionadas no checklist
        multi=True, # permite multiplas opções
        searchable=True
    ),
    html.Div([
        html.Button('Remover Todas', id='remover-button', n_clicks=0),
        html.Button('Preencher Todas', id='preencher-todos-button', n_clicks=0),
        dcc.Upload(
            id='upload-data',
            children=html.Button('Upload File'),
            multiple=False
        ),
    ], style={
        'display': 'flex',
        'gap': '10px',
        'alignItems': 'center',
        'flexWrap': 'wrap',
        'marginTop': '10px'
    }),
    html.Div(id='upload-output'),  # Aqui aparecerá o resultado (mensagem de sucesso/erro)
    dcc.Store(id='store-data', storage_type='memory'),
    dcc.Store(id='selected-trajectory', storage_type='memory', data=None),  # Store para trajetória selecionada

    html.Div([
        
        html.Label("Intervalo de trajetórias:"),

        html.Div([
            dcc.Input(
                id="inicio-input",
                type="number",
                min=0,
                step=1,
                value=0,
                debounce=True,
                style={"width": "100px"}
            ),
            html.Span(" até "),
            dcc.Input(
                id="fim-input",
                type="number",
                min=0,
                step=1,
                value=10,
                debounce=True,
                style={"width": "100px"}
            ),
        ], style={"marginBottom": "5px"}),

        html.Div(id="info-limites-traj")

    ]),

 
    dcc.Graph(id='mapa', style={'height': '700px'}, config={'scrollZoom': True}), # Componente gráfico para mostrar o mapa
])


#-------------------------------------------------------------------------
# CALLBACK 1 – Atualiza o mapa com múltiplas trajetórias
@app.callback(
    Output('mapa', 'figure'),
    Input('filtros-hover', 'value'),
    Input('store-data', 'data'),  # Novo input
    Input('inicio-input', 'value'),
    Input('fim-input', 'value')    
)
def update_map(colunas_selecionadas, json_data, inicio, fim):  # Função que atualiza o mapa com base nas colunas selecionadas
    """Atualiza a figura do mapa com trajetórias e movelets baseados nos filtros selecionados.

    Args:
        colunas_selecionadas (list): Lista de colunas para tooltip.
        json_data (str): Dados JSON do arquivo carregado via upload.
        inicio (int): Índice inicial das trajetórias a exibir.
        fim (int): Índice final das trajetórias a exibir.

    Returns:
        go.Figure: Figura Plotly com o mapa renderizado.
    """
    
    if not colunas_selecionadas:
        colunas_selecionadas = []

    # Se houve upload
    if json_data is not None:

        df_base = pd.read_json(StringIO(json_data), orient='split')

        # CASO 1 — já tem lat/lon
        if "lat" in df_base.columns and "lon" in df_base.columns:

            df_base["lat"] = pd.to_numeric(df_base["lat"], errors="coerce")
            df_base["lon"] = pd.to_numeric(df_base["lon"], errors="coerce")
            df_base = df_base.dropna(subset=["lat", "lon"])
            df_base["space"] = (
                df_base["lat"].astype(str) + " " +
                df_base["lon"].astype(str)
            )
        
        # CASO 2 — já tem LAT/LON
        elif "LAT" in df_base.columns and "LON" in df_base.columns:

            df_base["LAT"] = pd.to_numeric(df_base["LAT"], errors="coerce")
            df_base["LON"] = pd.to_numeric(df_base["LON"], errors="coerce")
            df_base = df_base.dropna(subset=["LAT", "LON"])
            df_base["lat"] = df_base["LAT"]
            df_base["lon"] = df_base["LON"]
            df_base["space"] = (
                df_base["LAT"].astype(str) + " " +
                df_base["LON"].astype(str)
            )

        # CASO 3 — tem coluna space
        elif "space" in df_base.columns:

            df_base = df_base.dropna(subset=["space"]) # Remove linhas onde "space" é NaN, pois não tem como extrair coordenadas
            df_base["space"] = df_base["space"].astype(str) # Garante que "space" é string para aplicar regex

            # extrai todos os números (inclusive negativos e decimais)
            coords = df_base["space"].str.extract(r'(-?\d+\.?\d*)[^0-9\-]+(-?\d+\.?\d*)')

            if coords.isna().any().any(): # Se alguma linha não conseguiu extrair coordenadas, mostra aviso e retorna mapa vazio
                return go.Figure() # Retorna figura vazia

            # Converte para numérico, forçando erros a NaN, e depois remove linhas com NaN
            df_base["lat"] = pd.to_numeric(coords[0], errors="coerce")
            df_base["lon"] = pd.to_numeric(coords[1], errors="coerce")

            # Remove linhas onde não conseguiu extrair coordenadas válidas
            df_base = df_base.dropna(subset=["lat", "lon"])

            print("Linhas após tratamento:", len(df_base))

        else:
            return go.Figure()


        T_local, data_desc_local = df2trajectory(
            df_base,
            data_desc=None,
            tid_col='tid',
            label_col='label'
        )

    else:
        # sem upload -> usa dataset original
        T_local = T
        data_desc_local = data_desc
        
    fig = go.Figure() # Cria uma nova figura plotly
    cores = ['blue', 'green', 'orange', 'purple', 'brown']  # Lista de cores para trajetórias

    all_lats = []  # Lista para armazenar todas latitudes dos pontos para centralizar mapa
    all_lons = []  # Lista para armazenar todas longitudes
    
    print("Quantidade de trajetórias:", len(T_local))

    inicio, fim = fca.normalizar_intervalo_trajetorias(inicio, fim, len(T_local))

    if fim < inicio:
        fig.update_layout(
            map_style="open-street-map",
            margin={"r": 0, "t": 30, "l": 0, "b": 0},
            height=700,
            title="Múltiplas Trajetórias no Mapa",
            showlegend=True
        )
        return fig

    for i in range(inicio, fim + 1):
        traj = T_local[i]
        
        if not traj.points:
            continue

        # Descobre qual índice é o aspecto espacial
        aspecto_espacial = fca.obter_aspecto_espacial(traj.points[0])

        if aspecto_espacial is None:
            continue  # não encontrou aspecto espacial

        pontos_com_aspecto_espacial = []
        for p in traj.points:
            aspecto_ponto = fca.obter_aspecto_espacial(p)
            if aspecto_ponto is not None:
                pontos_com_aspecto_espacial.append(aspecto_ponto)

        lats = [aspecto.x for aspecto in pontos_com_aspecto_espacial]
        lons = [aspecto.y for aspecto in pontos_com_aspecto_espacial]

        if not lats or not lons:
            continue
            
        all_lats.extend(lats)  # Adiciona latitudes à lista geral
        all_lons.extend(lons)  # Adiciona longitudes à lista geral

        # Verifica se a trajetória possui algum movelet e obtém informações
        movelets_info = traj_movelets.get(traj.tid, [])
        tem_movelet = len(movelets_info) > 0

        # Cor padrão da trajetória (mantém cor original, e highlight vermelho só para segmentos de movelet)
        cor_traj = cores[i % len(cores)]
        espessura = 2
        pontos_traj_por_local = defaultdict(list)

        for j, p in enumerate(traj.points):  # Para cada ponto na trajetória
            titulo_local = fca.obter_titulo_local(p, data_desc_local)

            # Lista de movelets que incluem este ponto
            movelet_nums = []
            for idx_mov, mov_info in enumerate(movelets_info):
                if mov_info['start'] <= j <= mov_info['end']:
                    mov_obj = mov_info.get('movelet')
                    if mov_obj is not None and hasattr(mov_obj, 'mid'):
                        try:
                            movelet_num = int(mov_obj.mid) + 1
                        except Exception:
                            movelet_num = idx_mov + 1
                    else:
                        movelet_num = idx_mov + 1
                    movelet_nums.append(movelet_num)

            movelets_do_ponto = [f"M.{n}" for n in sorted(set(movelet_nums))]

            if movelets_do_ponto:
                titulo = f"T.{traj.tid} p{j+1} - {' '.join([f'M[{n}]' for n in sorted(set(movelet_nums))])}"
            else:
                titulo = f"T.{traj.tid} p{j+1}"

            atributos_ponto = {}
            movelets_por_atributo = {}
            for c in colunas_selecionadas:
                valor = str(fca.extrair_valor(c, p, data_desc_local))

                movelets_do_atributo = []
                if movelets_do_ponto:
                    if c in ['lat', 'lon']:
                        movelets_do_atributo.extend(movelets_do_ponto)
                    elif c != 'Ponto':
                        for idx_mov, mov_info in enumerate(movelets_info):
                            if mov_info['start'] <= j <= mov_info['end']:
                                mov_obj = mov_info.get('movelet')
                                if mov_obj is not None and hasattr(mov_obj, 'attribute_names'):
                                    if c in mov_obj.attribute_names:
                                        if mov_obj is not None and hasattr(mov_obj, 'mid'):
                                            try:
                                                movelet_num = int(mov_obj.mid) + 1
                                            except Exception:
                                                movelet_num = idx_mov + 1
                                        else:
                                            movelet_num = idx_mov + 1
                                        movelets_do_atributo.append(f"M.{movelet_num}")

                atributos_ponto[c] = valor
                movelets_por_atributo[c] = sorted(set(movelets_do_atributo))

            point_key = (lats[j], lons[j])
            pontos_traj_por_local[point_key].append({
                "traj_tid": traj.tid,
                "point_index": j,
                "titulo": titulo,
                "titulo_local": titulo_local,
                "atributos": atributos_ponto,
                "movelets_por_atributo": movelets_por_atributo,
                "cor_traj": cor_traj,
            })

        # Desenha a trajetória completa como base (sinaliza no nome se há movelet)
        label_traj = f"Trajetória {traj.tid}"
        if tem_movelet:
            label_traj += " 🚩"  # sinal visual de presence de movelet

        fig.add_trace(go.Scattermap(
            mode='lines',
            lon=lons,
            lat=lats,
            line={'width': espessura, 'color': cor_traj},
            name=label_traj,
            legendgroup=f"traj{i}",
            hoverinfo='skip',
            showlegend=True
        ))

        marker_lats = []
        marker_lons = []
        hover_texts = []

        for (lat, lon), registros in pontos_traj_por_local.items():
            marker_lats.append(lat)
            marker_lons.append(lon)
            hover_texts.append(fca.montar_hover_ponto_grupo(registros, colunas_selecionadas))

        fig.add_trace(go.Scattermap(
            mode='markers',
            lon=marker_lons,
            lat=marker_lats,
            marker={'size': 12, 'color': cor_traj, 'opacity': 0.9, 'symbol': 'circle', 'allowoverlap': True},
            name=f'Pontos trajetória {traj.tid}',
            legendgroup=f"traj{i}",
            hovertext=hover_texts,
            hovertemplate="%{hovertext}<extra></extra>",
            hoverlabel={'align': 'left'},
            showlegend=False
        ))

        # Se houver movelets, desenha apenas o(s) trecho(s) de movelet em destaque vermelho
        if tem_movelet:
            movelet_legend_shown = False
            for idx_mov, mov_info in enumerate(movelets_info):
                start = int(mov_info.get('start', 0))
                end = int(mov_info.get('end', -1))

                if start < 0 or end >= len(lats) or start >= len(lats):
                    continue

                seg_lats = lats[start:end + 1]
                seg_lons = lons[start:end + 1]

                # Se movelet tem apenas um ponto, usa markers; senão, lines
                if len(seg_lats) == 1:
                    mode = 'markers'
                    marker = {'size': 10, 'color': 'red'}
                    line = {}
                else:
                    mode = 'lines'
                    line = {'width': 6, 'color': 'red'}
                    marker = {}

                # Extrai os atributos e número da movelet
                mov_obj = mov_info.get('movelet')
                if mov_obj is not None and hasattr(mov_obj, 'attribute_names'):
                    atributos_str = ', '.join(mov_obj.attribute_names)
                else:
                    atributos_str = 'N/A'
                
                # Extrai o número do movelet (mid)
                if mov_obj is not None and hasattr(mov_obj, 'mid'):
                    try:
                        movelet_num = int(mov_obj.mid) + 1
                    except Exception:
                        movelet_num = idx_mov + 1
                else:
                    movelet_num = idx_mov + 1

                fig.add_trace(go.Scattermap(
                    mode=mode,
                    lon=seg_lons,
                    lat=seg_lats,
                    line=line,
                    marker=marker,
                    name=f'Movelets trajetória {traj.tid}',
                    legendgroup=f"movelets{traj.tid}",
                    hoverinfo='skip',
                    showlegend=not movelet_legend_shown,
                    hovertemplate=f'[M {movelet_num}] Movelet {idx_mov+1} da Trajetória {traj.tid}<br>Índice inicial: {start}<br>Índice final: {end}<br>Tamanho: {mov_info["size"]}<br>Atributos: {atributos_str}<extra></extra>'
                ))

                movelet_legend_shown = True

    print("Total latitudes coletadas:", len(all_lats))
    
    # Centraliza o mapa
    if all_lats and all_lons:
        center_lat = sum(all_lats) / len(all_lats)
        center_lon = sum(all_lons) / len(all_lons)
    else:
        center_lat, center_lon = 0, 0

    fig.update_layout(
        map_style="open-street-map",
        map_zoom=5,
        map_center={"lat": center_lat, "lon": center_lon},
        margin={"r": 0, "t": 30, "l": 0, "b": 0},
        height=700,
        title="Múltiplas Trajetórias no Mapa",
        showlegend=True,
        hovermode='closest'
    )

    return fig

@app.callback(
    Output('store-data', 'data'),  # Salva o DataFrame no Store
    Output('upload-output', 'children'),  # Mostra mensagem
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    State('upload-data', 'last_modified'),
    prevent_initial_call=True
)
def process_uploaded_file(contents, filename, date):
    """Processa arquivo carregado via upload e armazena no store.

    Args:
        contents (str): Conteúdo base64 do arquivo.
        filename (str): Nome do arquivo.
        date: Data de modificação.

    Returns:
        tuple: (json_data, mensagem) ou (None, erro)
    """

    if contents is not None:

        df = upa.parse_contents(contents, filename, date)

        if isinstance(df, pd.DataFrame):

            # Padroniza nomes das colunas
            df.columns = df.columns.str.strip().str.lower()

            print("Colunas recebidas:", df.columns.tolist())

            # Converte colunas de texto automaticamente
            for col in df.select_dtypes(include=['object']).columns:
                if col == "space":
                    continue  # NÃO mexe na coluna space
                
                df[col] = df[col].astype(str).str.strip()

            # Tenta converter colunas numéricas automaticamente
            for col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col])
                except:
                    pass

            # Normaliza linhas vazias
            df = df.replace({"": None, "nan": None})

            return df.to_json(date_format='iso', orient='split'), f"✅ Arquivo {filename} carregado com sucesso!"

        else:
            return None, f"⚠️ Erro ao processar o arquivo: {df}"

    return None, ''


#callback 3 – Atualiza opções do dropdown com base no DataFrame carregado
@app.callback(
    Output('filtros-hover', 'options'), # Atualiza opções do dropdown com base no DataFrame carregado
    Output('filtros-hover', 'value'), # Atualiza valores selecionados no dropdown
    Input('store-data', 'data'), # Novo input para o JSON do DataFrame carregado
    Input('remover-button', 'n_clicks'), # Novo input para o botão de controle
    Input('preencher-todos-button', 'n_clicks'), # Novos inputs para os botões de controle
    State('filtros-hover', 'value'),
)
def controlar_dropdown(json_data, n_remover, n_preencher, valores_atuais): # Função para controlar opções do dropdown com base no upload e botões de controle
    """Controla as opções do dropdown de filtros baseado no upload e botões.

    Args:
        json_data (str): Dados JSON do arquivo carregado.
        n_remover (int): Cliques no botão remover.
        n_preencher (int): Cliques no botão preencher.
        valores_atuais (list): Colunas atualmente selecionadas no dropdown.

    Returns:
        tuple: (options, value) para o dropdown.
    """

    ctx = dash.callback_context # Contexto do callback para identificar qual input disparou a função

    # Se não houve trigger ainda (primeira execução)
    if not ctx.triggered: # Se nenhum input disparou o callback, usa colunas do dataset inicial para preencher opções do dropdown
        # Usa o dataset inicial carregado no começo do script
        colunas = [col for col in df.columns if col not in ['tid', 'label', 'space']] # Exclui colunas de identificação e rótulo
        if 'lat' not in colunas:
            colunas.append('lat')
        if 'lon' not in colunas:
            colunas.append('lon')
        options = [{'label': col, 'value': col} for col in colunas] # Cria opções para o dropdown com base nas colunas do dataset inicial
        return options, colunas # Seleciona todas as colunas do dataset inicial por padrão

    trigger = ctx.triggered[0]['prop_id'].split('.')[0] # Identifica qual input disparou o callback

    # Se veio do upload
    if trigger == 'store-data' and json_data is not None: # Se o trigger foi o upload e tem dados, atualiza opções com as colunas do dataset carregado
        df_upload = pd.read_json(StringIO(json_data), orient='split') # Converte JSON de volta para DataFrame
        colunas = [col for col in df_upload.columns if col not in ['tid', 'label', 'space']] # Exclui colunas de identificação e rótulo
        if any(col in df_upload.columns for col in ['lat', 'lon', 'LAT', 'LON', 'space']):
            if 'lat' not in colunas:
                colunas.append('lat')
            if 'lon' not in colunas:
                colunas.append('lon')
        options = [{'label': col, 'value': col} for col in colunas] # Cria opções para o dropdown com base nas colunas do DataFrame carregado

        return options, colunas # Reseta a seleção ao fazer upload e seleciona as colunas do novo arquivo

    # Remover
    if trigger == 'remover-button': # Se o botão "Remover Todas" foi clicado, desmarca todas as colunas
        return dash.no_update, [] # Retorna opções atuais mas desmarca todas as colunas

    # Preencher
    if trigger == 'preencher-todos-button': # Se o botão "Preencher Todas" foi clicado, seleciona todas as colunas disponíveis
        if json_data is not None: # Se tiver upload, usa colunas do dataset carregado
            df_upload = pd.read_json(StringIO(json_data), orient='split') # Se tiver upload, usa colunas do dataset carregado
            colunas = [col for col in df_upload.columns if col not in ['tid', 'label', 'space']] # Se tiver upload, usa colunas do dataset carregado
            if any(col in df_upload.columns for col in ['lat', 'lon', 'LAT', 'LON', 'space']):
                if 'lat' not in colunas:
                    colunas.append('lat')
                if 'lon' not in colunas:
                    colunas.append('lon')
        else: # Se não tiver upload, usa colunas do dataset inicial
            colunas = [col for col in df.columns if col not in ['tid', 'label', 'space']] # Se não tiver upload, usa colunas do dataset inicial
            if 'lat' not in colunas:
                colunas.append('lat')
            if 'lon' not in colunas:
                colunas.append('lon')

        return dash.no_update, colunas # Retorna opções atuais mas seleciona todas as colunas

    raise dash.exceptions.PreventUpdate # Se nenhum trigger válido, não atualiza nada

# Atualiza limite máximo e texto informativo
@app.callback(
    Output('inicio-input', 'max'),
    Output('fim-input', 'max'),
    Output('info-limites-traj', 'children'),
    Input('store-data', 'data')
)
def atualizar_limites_inputs(json_data):
    """Atualiza os limites dos inputs de intervalo e texto informativo.

    Args:
        json_data (str): Dados JSON do arquivo carregado.

    Returns:
        tuple: (max_inicio, max_fim, texto_info)
    """

    if json_data is not None:
        df_base = pd.read_json(StringIO(json_data), orient='split')
        T_local, _ = df2trajectory(
            df_base,
            data_desc=None,
            tid_col='tid',
            label_col='label'
        )
    else:
        T_local = T

    total = len(T_local)
    ultimo_indice = max(0, total - 1)

    texto_info = f"Total de trajetórias: {total} | Índices válidos: 0 a {ultimo_indice}"

    return ultimo_indice, ultimo_indice, texto_info

# Callback para capturar cliques na legenda e selecionar uma trajetória
@app.callback(
    Output('selected-trajectory', 'data'),
    Input('mapa', 'clickData'),
    prevent_initial_call=True
)
def selecionar_trajetoria(clickData):
    """Captura cliques na legenda para selecionar uma trajetória específica.
    
    Args:
        clickData: Dados do clique no gráfico.
        
    Returns:
        int ou None: Índice da trajetória selecionada ou None.
    """
    
    # Se clicou no mapa mas não em um ponto de dados válido (clique em área vazia)
    if not clickData or 'points' not in clickData or len(clickData['points']) == 0:
        return None  # Desseleciona
    
    point_data = clickData['points'][0]
    
    # Tenta extrair informação da trajetória do hover text ou do legendgroup
    hover_text = point_data.get('hovertext', '')
    legend_group = point_data.get('legendgroup', '')
    
    
    # Tenta extrair o índice de trajetória do legendgroup (formato: "traj5" ou "movelets123")
    if 'traj' in legend_group:
        match = re.search(r'traj(\d+)', legend_group)
        if match:
            traj_index = int(match.group(1))
            return traj_index
    
    # Tenta extrair do hover text (formato: "T.123 p5")
    if 'T.' in hover_text:
        match = re.search(r'T\.(\d+)', hover_text)
        if match:
            tid = match.group(1)
            # Tenta encontrar o índice correspondente ao tid na lista de trajetórias
            return tid
    
    return dash.no_update

# Callback para atualizar os inputs quando uma trajetória é selecionada
@app.callback(
    Output('inicio-input', 'value'),
    Output('fim-input', 'value'),
    Input('selected-trajectory', 'data'),
    State('store-data', 'data'),
    prevent_initial_call=True
)
def atualizar_inputs_com_selecao(traj_selecionada, json_data):
    """Atualiza os inputs de início e fim quando uma trajetória é selecionada.
    
    Args:
        traj_selecionada: Índice da trajetória selecionada ou None para desselecionar.
        json_data: Dados do upload (se houver).
        
    Returns:
        tuple: (novo_inicio, novo_fim)
    """
    
    
    if traj_selecionada is None:
        # Desselecionar - volta aos valores padrão
        if json_data is not None:
            df_base = pd.read_json(StringIO(json_data), orient='split')
            T_local, _ = df2trajectory(
                df_base,
                data_desc=None,
                tid_col='tid',
                label_col='label'
            )
        else:
            T_local = T

        _, fim = fca.normalizar_intervalo_trajetorias(0, 10, len(T_local))
        return 0, fim
    
    # Se é um inteiro, é um índice direto
    if isinstance(traj_selecionada, int):
        return traj_selecionada, traj_selecionada
    
    # Se é uma string, é um tid (id da trajetória)
    if isinstance(traj_selecionada, str):
        # Carrega trajetórias para encontrar o índice correspondente
        if json_data is not None:
            df_base = pd.read_json(StringIO(json_data), orient='split')
            T_local, _ = df2trajectory(
                df_base,
                data_desc=None,
                tid_col='tid',
                label_col='label'
            )
        else:
            T_local = T
        
        # Procura pelo tid na lista de trajetórias
        for i, traj in enumerate(T_local):
            if str(traj.tid) == str(traj_selecionada):

                return i, i

    raise dash.exceptions.PreventUpdate

if __name__ == '__main__':  # Só executa quando rodar o script diretamente
    app.run(debug=True)  # Roda o servidor do Dash em modo debug para desenvolvimento
    
    
    
