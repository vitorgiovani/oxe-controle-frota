import pandas as pd

def clean_placa(p):
    if pd.isna(p):
        return None
    return str(p).strip().upper()

def to_date(x):
    if pd.isna(x):
        return None
    try:
        return pd.to_datetime(x, dayfirst=True).strftime('%Y-%m-%d')
    except:
        return None

def to_float(x):
    if pd.isna(x):
        return None
    try:
        return float(str(x).replace(',', '.'))
    except:
        return None