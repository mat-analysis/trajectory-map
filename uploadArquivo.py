"""Módulo para parsing de arquivos enviados via upload na aplicação Dash.

Suporta extensões: parquet, csv, zip, ts, xes, json.
"""

import base64
from dash import html
import pandas as pd
from matdata.converter import csv2df, parquet2df, read_zip#, load_from_tsfile, xes2df
from matdata.converter import xes2df
from matdata.inc.ts_io import load_from_tsfile
import io
from matdata.preprocess import readDataset, organizeFrame

def parse_contents(contents, filename, date):
    """Decodifica conteúdo base64 e retorna DataFrame ou componente de erro."""
    
    content_type, content_string = contents.split(',')

    # DECODE DATAFRAME:
    decoded = base64.b64decode(content_string)
    try:
        ext = filename.split('.')[-1].lower()
        if ext in ['parquet','csv', 'zip', 'mat', 'ts']:

            df = pd.DataFrame()
            if ext == 'parquet':
                # Usa pandas diretamente (mais seguro para upload)
                df = pd.read_parquet(io.BytesIO(decoded))
            elif ext == 'csv':
#                from matdata.converter import csv2df
                decoded = io.StringIO(decoded.decode('utf-8'))
                df = csv2df(decoded, missing='?')
            elif ext == 'zip':
#                from matdata.converter import read_zip
                from zipfile import ZipFile
                decoded = io.BytesIO(decoded)
                df = read_zip(ZipFile(decoded, "r"))
#             elif ext == 'mat':
# #                from matdata.converter import read_mat
#                 decoded = io.StringIO(decoded.decode('utf-8'))
#                 df = read_mat(decoded, missing='?')
            elif ext == 'ts':
#                from matdata.inc.ts_io import load_from_tsfile
                decoded = io.StringIO(decoded.decode('utf-8'))
                df = load_from_tsfile(decoded, replace_missing_vals_with="?")
            elif ext == 'xes':
#                from matdata.converter import xes2df
                decoded = io.StringIO(decoded.decode('utf-8'))
                df = xes2df(decoded, missing='?')

            df.columns = df.columns.astype(str)

            df, columns_order_zip, columns_order_csv = organizeFrame(df)
            return df
        elif ext == 'json':        
                df = pd.read_json(io.BytesIO(decoded))
                df, columns_order_zip, columns_order_csv = organizeFrame(df)
                return df
                
    except Exception as e:
        return html.Div([f"Erro ao processar o arquivo: {str(e)}"])

    return None

        