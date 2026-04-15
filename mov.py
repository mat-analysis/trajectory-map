"""Módulo de utilidades para descoberta e carregamento de movelets.

- executar_descoberta_movelets: processa dataset, executa jar externo e cria dicionário de movelets
- carregar_movelets_disponveis: lê arquivos de resultados e converte em dicionário por tid
"""

import pandas as pd
import os
import subprocess
from matdata.dataset import *  # Importa funções para carregar datasets do pacote matdata
from matmodel.util.parsers import df2trajectory  # Importa função para converter DataFrame em trajetórias
from matdata.dataset import load_ds
from matdata.converter import df2csv
from matdata.preprocess import klabels_stratify
from matmodel.util.parsers import json2movelet


def executar_descoberta_movelets():
    """
    Executa o processo de descoberta de movelets e retorna um dicionário
    de trajetórias com suas respectivas movelets.
    """
    # Carrega dados para as movelets
    dataset='mat.FoursquareNYC'
    data = load_ds(dataset, missing='-999')
    train, test = klabels_stratify(data, kl=10)

    data_path = 'sample/data/FoursquareNYC'
    if not os.path.exists(data_path):
        os.makedirs(data_path)

    df2csv(train, data_path, 'train')
    df2csv(test, data_path, 'test')

    prog_path = 'sample/programs'
    if not os.path.exists(prog_path):
        print(os.makedirs(prog_path))

    # Criar pastas se não existirem
    os.makedirs("sample/programs", exist_ok=True)
    os.makedirs("sample/data/FoursquareNYC", exist_ok=True)
        
    cmd = [
        "java", "-Xmx7G", "-jar", "./sample/programs/MoveletDiscovery.jar",
        "-curpath", "./sample/data/FoursquareNYC",
        "-respath", "./sample/results/hiper",
        "-descfile", "./sample/data/FoursquareNYC/FoursquareNYC.json",
        "-nt", "1", "-version", "hiper", "-ms", "-1", "-Ms", "-3", "-TC", "1d"
    ]

    subprocess.run(cmd, check=True)
    movelets_train = pd.read_csv('./sample/data/FoursquareNYC/train.csv')
    movelets_test = pd.read_csv('./sample/data/FoursquareNYC/test.csv')

    T, data_desc = df2trajectory(data, data_desc='sample/data/FoursquareNYC/FoursquareNYC.json')

    # Lendo movelets como objetos de mat-model
    mov_file = './sample/results/hiper/Movelets/HIPER_Log_FoursquareNYC_LSP_ED/164/moveletsOnTrain.json'

    with open(mov_file, 'r') as f:
        M = json2movelet(f)
           
    # Cria dicionário de trajetórias com movelets
    traj_movelets = {}
    for mov in M:  # M é a lista de movelets extraídas pelo json2movelet
        tid = mov.tid  # ID da trajetória da qual movelet foi extraída
        if tid not in traj_movelets.keys():
            traj_movelets[tid] = []
        traj_movelets[tid].append(mov)
    
    print("Dicionario criado!")
    return traj_movelets


def carregar_movelets_disponveis():
    """
    Carrega movelets disponíveis dos arquivos JSON gerados.
    Retorna um dicionário com informações detalhadas sobre quais pontos
    de cada trajetória formam movelets.
    
    Estrutura retornada:
    {
        tid: [
            {'movelet': movelet_obj, 'start': 17, 'end': 20},
            {'movelet': movelet_obj, 'start': 5, 'end': 8}
        ]
    }
    """
    traj_movelets = {}
    
    # Caminho base para resultados
    results_base = './sample/results/hiper/Movelets/HIPER_Log_FoursquareNYC_LSP_ED'
    
    if os.path.exists(results_base):
        # Itera sobre todas as pastas numéricas de resultados
        for folder in os.listdir(results_base):
            folder_path = os.path.join(results_base, folder)
            if os.path.isdir(folder_path):
                mov_file = os.path.join(folder_path, 'moveletsOnTrain.json')
                
                if os.path.exists(mov_file):
                    try:
                        with open(mov_file, 'r') as f:
                            M = json2movelet(f)
                        
                        for mov in M:
                            tid = mov.tid
                            if tid not in traj_movelets:
                                traj_movelets[tid] = []
                            
                            # Extrai informações da movelet
                            start_idx = mov.start  # Índice do primeiro ponto
                            size = mov.size  # Tamanho da movelet
                            end_idx = start_idx + size - 1  # Índice do último ponto
                            
                            traj_movelets[tid].append({
                                'movelet': mov,
                                'start': start_idx,
                                'end': end_idx,
                                'size': size
                            })
                        
                        print(f"Movelets carregadas de {mov_file}")
                    except Exception as e:
                        print(f"Erro ao carregar movelets de {mov_file}: {e}")
    
    if traj_movelets:
        print(f"Total de trajetórias com movelets carregadas: {len(traj_movelets)}")
    else:
        print("Nenhuma movelet encontrada no diretório de resultados.")
    
    return traj_movelets


if __name__ == '__main__':
    # Se executado diretamente, executa a descoberta
    traj_movelets = executar_descoberta_movelets()

