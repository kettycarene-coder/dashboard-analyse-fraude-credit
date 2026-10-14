"""Indicator definitions shared by the application and its checks."""
import pandas as pd

def validate(df):
    required = {'request_id', 'DAT_CRE_DMD', 'age_client', 'MNT_ACH', 'nb_dmd', 'ACC', 'RFS', 'top_susp_frd_fnc', 'tranche_age', 'tranche_montant', 'FAM_STN', 'SOF_CAT', 'Gp_FAM', 'Gp_CSP'}
    if not required.issubset(df.columns):
        raise ValueError('Missing required columns')
    if df[list(required)].isna().any().any() or df.request_id.duplicated().any():
        raise ValueError('Missing values or duplicate requests')
    if not df.ACC.isin([0, 1]).all() or not df.top_susp_frd_fnc.isin([0, 1]).all():
        raise ValueError('Indicators must be binary')
    if (df.top_susp_frd_fnc > df.ACC).any():
        raise ValueError('Fraud indicator is defined only among accepted requests')
    if not df.RFS.isin([0, 1]).all() or ((df.ACC + df.RFS) > 1).any():
        raise ValueError('Accepted and refused cannot both equal 1')
    if not df.nb_dmd.eq(1).all():
        raise ValueError('Each row must represent one request')
    for column in ['POL_SCO', 'POL_SCO_grp', 'RSK_RNG', 'region_acc', 'region_shg', 'RVN', 'VAL_STT_CUS']:
        if column not in df or df[column].isna().any():
            raise ValueError(f'Missing demonstration field: {column}')
    if not df.POL_SCO.between(-100, 100).all():
        raise ValueError('Invalid demonstration score')
    if not df.age_client.between(18, 98).all() or (df.MNT_ACH <= 0).any():
        raise ValueError('Invalid age or amount')
    if pd.to_datetime(df.DAT_CRE_DMD, errors='coerce').isna().any():
        raise ValueError('Invalid date')

def kpis(df):
    n = len(df)
    accepted = int(df.ACC.sum())
    fraud = int(df.top_susp_frd_fnc.sum())
    return {'requests': n, 'ACC': accepted, 'top_susp_frd_fnc': fraud,
        'acceptance_rate': 100 * accepted / n if n else None,
        'fraud_rate': 100 * fraud / accepted if accepted else None}

def weekly(df):
    if df.empty:
        return pd.DataFrame(columns=['week', 'requests', 'ACC', 'top_susp_frd_fnc', 'fraud_rate'])
    d = df.copy()
    # Monday dates keep ISO years distinct, including December/January.
    d['week'] = d.DAT_CRE_DMD - pd.to_timedelta(d.DAT_CRE_DMD.dt.weekday, unit='D')
    out = d.groupby('week').agg(requests=('request_id', 'size'), ACC=('ACC', 'sum'), top_susp_frd_fnc=('top_susp_frd_fnc', 'sum')).reset_index()
    out['fraud_rate'] = out.top_susp_frd_fnc.div(out.ACC.where(out.ACC > 0)) * 100
    return out
