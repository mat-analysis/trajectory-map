"""Módulo de funções auxiliares para formato de exibição e extração de valores.

Contém:
- icone_avaliacao: converte pontuação numérica em sequência de estrelas
- icones_clima: converte nome de condição meteorológica em emoji
- extrair_valor: extrai valores de atributos de pontos de trajetórias
"""

import pandas as pd


def icone_avaliacao(av):  # Função para converter valor numérico de avaliação em estrelas
    """Retorna uma string de avaliação em formato de estrelas (5) com suporte a meia estrela.

    av pode ser None, 0, '-' ou strings de NaN. O valor numérico é dividido por 2 para escala 0-5.
    """

    if av is None or av == 0 or av == "-" or av == "Nan" or av == "NaN": # Verifica se a avaliação é nula, zero ou "Nan"
        return "\t -"  # Retorna símbolo de ausência de avaliação
    else:
        avaliacao = av / 2  # Divide avaliação por 2 para escalar de 0 a 5
        
        # Decide se meia estrela deve aparecer 
        if avaliacao - int(avaliacao)>= 0.5:
            meia_estrela = "⯪" # Se avaliação tem parte decimal maior ou igual a 0.5, meia estrela é representada por símbolo de meia estrela
        elif avaliacao - int(avaliacao) == 0: 
            meia_estrela = "" # Se avaliação é um número inteiro, não há meia estrela
        else:
            meia_estrela = "☆" # Se avaliação tem parte decimal menor que 0.5, meia estrela é representada por estrela cinza
    
        estrela_cinza = int(5 - avaliacao)  # Quantidade de estrelas cinzas para completar até 5

        if avaliacao >= 1:  # Se avaliação >= 1, monta string com estrelas cheias, meia e cinzas
            return (int(avaliacao) * "★") + meia_estrela + (estrela_cinza * "☆")
        elif avaliacao == 0:  # Se avaliação 0, retorna só estrelas cinzas
            return estrela_cinza * "☆"
        else:  # Caso contrário, retorna símbolo de ausência de avaliação
            return "\t -"

def icones_clima(clima):  # Função para converter string clima em emoji correspondente
    """Retorna emoji correspondente à condição meteorológica informada."""
    clima_icones = {
        "Clouds": "☁️",  # Nuvens
        "Clear": "☀️",   # Sol
        "Rain": "🌧️",    # Chuva
        "Snow": "❄️",    # Neve
        "Fog": "🌫️",     # Névoa
        "Unknown": "-"   # Desconhecido
    }
    return clima_icones.get(clima, '-')  # Retorna emoji ou '-' se não encontrado


def obter_aspecto_espacial(p):
    """Retorna o aspecto espacial do ponto, quando existir."""
    for aspecto in getattr(p, "aspects", []):
        if hasattr(aspecto, "x") and hasattr(aspecto, "y"):
            return aspecto
    return None


def extrair_valor(coluna, p, data_desc):  # Função que retorna o valor de uma coluna para um ponto p da trajetória
    """Extrai o valor de uma coluna específica para um ponto de trajetória.

    Args:
        coluna (str): Nome da coluna a extrair (ex: 'lat', 'lon', 'rating', 'weather').
        p: Objeto ponto da trajetória.
        data_desc: Descrição dos dados do dataset.

    Returns:
        Valor formatado da coluna para o ponto.
    """
    
    # Latitude (coordenada x)
    if coluna == "lat":
        aspecto_espacial = obter_aspecto_espacial(p)
        return aspecto_espacial.x if aspecto_espacial is not None else ""
    
    # Longitude (coordenada y)
    if coluna == "lon":
        aspecto_espacial = obter_aspecto_espacial(p)
        return aspecto_espacial.y if aspecto_espacial is not None else ""

    # Número sequencial do ponto
    if coluna == "Ponto":
        return p.seq  

    # Lista de atributos do dataset para encontrar o índice da coluna desejada
    atributos = [attr.name for attr in data_desc.attributes]

    try:
        idx = atributos.index(coluna)
    except ValueError:
        return ''

    aspecto = p.aspects[idx]

    # Alguns aspects possuem atributo .value
    valor = aspecto.value if hasattr(aspecto, "value") else aspecto  

    # Cria a versão numérica da avaliação indo de 0 até 5
    if coluna == "rating":
        
        if valor == "Nan" or valor == "NaN" or valor == "-" or valor is None:
            valor = 0
            
        if valor and valor > 0:
            num_avaliacao = str(valor / 2)
        else:
            num_avaliacao = "-"
        return icone_avaliacao(valor) + "\t(" + num_avaliacao + ")"

    # Clima formatado com emoji correspondente
    if coluna == "weather":
        return icones_clima(valor)

    return valor


def extrair_valores_limpos_unicos(valores):
    """Remove vazios e repeticoes preservando a ordem."""
    valores_limpos = []
    vistos = set()

    for valor in valores:
        valor_str = str(valor).strip()
        if not valor_str or valor_str.lower() in {"none", "nan"}:
            continue
        if valor_str not in vistos:
            vistos.add(valor_str)
            valores_limpos.append(valor_str)

    return valores_limpos


def formatar_valor_unico(valores):
    """Formata valores unicos para exibicao no tooltip."""
    valores_limpos = extrair_valores_limpos_unicos(valores)

    if not valores_limpos:
        return "-"

    if len(valores_limpos) == 1:
        return valores_limpos[0]

    return "{" + ", ".join(valores_limpos) + "}"


def coluna_parece_temporal(coluna):
    """Heuristica simples para colunas de data/hora."""
    coluna_lower = str(coluna).strip().lower()
    termos_temporais = ["time", "date", "datetime", "timestamp", "hour", "minute", "second"]
    return any(termo in coluna_lower for termo in termos_temporais)


def formatar_intervalo_temporal(valores):
    """Resume valores temporais como intervalo <inicio ... fim>."""
    valores_limpos = extrair_valores_limpos_unicos(valores)
    if not valores_limpos:
        return "-"

    if len(valores_limpos) == 1:
        return valores_limpos[0]

    serie = pd.to_datetime(pd.Series(valores_limpos), errors="coerce")
    if serie.isna().any():
        return None

    pares = list(zip(valores_limpos, serie.tolist()))
    pares_ordenados = sorted(pares, key=lambda item: item[1])
    inicio = pares_ordenados[0][0]
    fim = pares_ordenados[-1][0]

    if inicio == fim:
        return inicio

    return f"<{inicio} ... {fim}>"


def formatar_valor_atributo(coluna, valores):
    """Formata valores de atributo, usando intervalo para dados temporais."""
    if coluna_parece_temporal(coluna):
        intervalo = formatar_intervalo_temporal(valores)
        if intervalo is not None:
            return intervalo

    return formatar_valor_unico(valores)


def formatar_codigos_atributo(traj_tid, movelets):
    """Formata codigos de movelets para o fim da linha."""
    movelets_formatadas = formatar_valor_unico(movelets)
    if movelets_formatadas == "-":
        return ""
    return f"{movelets_formatadas}"


def formatar_trajetorias_e_pontos(registros):
    """Agrupa trajetorias e pontos para exibicao em locais sobrepostos."""
    agrupado = {}

    for registro in registros:
        traj_label = f"T.{registro['traj_tid']}"
        ponto_label = f"p{registro['point_index'] + 1}"
        agrupado.setdefault(traj_label, []).append(ponto_label)

    partes = []
    for traj_label, pontos in agrupado.items():
        partes.append(f"{traj_label}: {formatar_valor_unico(pontos)}")

    if not partes:
        return "-"

    if len(partes) == 1:
        return partes[0]

    return " | ".join(partes)


def filtrar_colunas_tooltip(colunas_selecionadas):
    """Remove colunas redundantes da tooltip."""
    return [coluna for coluna in colunas_selecionadas if str(coluna).strip().lower() != "space"]


def obter_titulo_local(ponto, data_desc_local):
    """Tenta obter um titulo amigavel do ponto sem depender de atributo fixo."""
    colunas_preferidas = ["poi", "place", "name", "location", "local"]

    for coluna in colunas_preferidas:
        try:
            valor = str(extrair_valor(coluna, ponto, data_desc_local)).strip()
        except Exception:
            valor = ""

        if valor and valor.lower() not in {"none", "nan"}:
            return valor

    try:
        for aspecto in ponto.aspects:
            valor = getattr(aspecto, "value", None)
            if valor is None:
                continue
            valor_str = str(valor).strip()
            if valor_str and valor_str.lower() not in {"none", "nan"}:
                return valor_str
    except Exception:
        pass

    return "Local"


def montar_hover_ponto_grupo(registros, colunas_selecionadas):
    """Monta hover para um ou mais pontos na mesma coordenada."""
    if not registros:
        return ""

    colunas_tooltip = filtrar_colunas_tooltip(colunas_selecionadas)
    traj_tid = registros[0]["traj_tid"]

    if len(registros) == 1:
        registro = registros[0]
        partes = [registro["titulo"]]

        for coluna in colunas_tooltip:
            valor = formatar_valor_atributo(coluna, [registro["atributos"].get(coluna, "-")])
            movelets = registro["movelets_por_atributo"].get(coluna, [])
            codigos = formatar_codigos_atributo(registro["traj_tid"], movelets)
            if codigos:
                partes.append(f"{coluna}: {valor} | {codigos}")
            else:
                partes.append(f"{coluna}: {valor}")


        return "<br>".join(partes)

    partes = [f"Trajetorias/Pontos: {formatar_trajetorias_e_pontos(registros)}"]

    for coluna in colunas_tooltip:
        valores = [r["atributos"].get(coluna, "-") for r in registros]
        movelets = []
        for registro in registros:
            movelets.extend(registro["movelets_por_atributo"].get(coluna, []))
        valor_formatado = formatar_valor_atributo(coluna, valores)
        codigos = formatar_codigos_atributo(traj_tid, movelets)
        if codigos:
            partes.append(f"{coluna}: {valor_formatado} | {codigos}")
        else:
            partes.append(f"{coluna}: {valor_formatado}")

    return "<br>".join(partes)


def normalizar_intervalo_trajetorias(inicio, fim, total):
    """Normaliza intervalo de trajetórias para índices válidos."""
    if total <= 0:
        return 0, -1

    ultimo_indice = total - 1

    if inicio is None:
        inicio = 0
    if fim is None:
        fim = ultimo_indice

    try:
        inicio = int(inicio)
    except (TypeError, ValueError):
        inicio = 0

    try:
        fim = int(fim)
    except (TypeError, ValueError):
        fim = ultimo_indice

    inicio = max(0, min(inicio, ultimo_indice))
    fim = max(0, min(fim, ultimo_indice))

    if inicio > fim:
        inicio, fim = fim, inicio

    return inicio, fim
