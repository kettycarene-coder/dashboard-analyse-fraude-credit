"""Generate reproducible, entirely invented observations; no company data."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent

def generate(seed=42, n=6000):
    rng = np.random.default_rng(seed)
    dates = pd.Timestamp('2024-01-01') + pd.to_timedelta(rng.integers(0, 731, n), unit='D')
    age = rng.integers(18, 99, n)
    amount = np.round(rng.uniform(1, 3000, n), 2)
    # Simulation assumptions, deliberately independent of age or location.
    accepted = rng.random(n) < .68
    week = dates.isocalendar().week.to_numpy(dtype=int)
    probability = np.where((week >= 22) & (week <= 26), .065, .025)
    fraud = accepted & (rng.random(n) < probability)
    df = pd.DataFrame({'request_id': [f'DEMO-{i:05}' for i in range(n)],
        'DAT_CRE_DMD': dates, 'age_client': age, 'MNT_ACH': amount,
        'nb_dmd': 1, 'ACC': accepted.astype(int), 'RFS': (~accepted).astype(int),
        'top_susp_frd_fnc': fraud.astype(int)})
    # Grouping rules transcribed from Figure 3.10 of the supplied report.
    df['tranche_age'] = pd.cut(df.age_client, [18, 24, 35, 48, 55, 98],
        labels=['18-24', '25-35', '36-48', '49-55', '56-98'], include_lowest=True, right=True).astype(str)
    df['tranche_montant'] = pd.cut(df.MNT_ACH, [0, 250, 500, 750, 1000, 1500, 3000],
        labels=['0-250', '250-500', '500-750', '750-1000', '1000-1500', '1500-3000'],
        include_lowest=True, right=True).astype(str)
    gp_fam = {'C':'seul', 'V':'seul', 'M':'en couple', 'P':'en couple',
        'K':'en couple', 'S':'séparé', 'D':'séparé'}
    gp_csp = {2300:'Revenu élevé', 3100:'Revenu élevé', 3300:'Revenu élevé', 3800:'Revenu élevé',
        1100:'Revenu moyen', 2100:'Revenu moyen', 2200:'Revenu moyen', 4500:'Revenu moyen', 4600:'Revenu moyen',
        5200:'Revenu modeste', 5300:'Revenu modeste', 5400:'Revenu modeste', 5500:'Revenu modeste', 5600:'Revenu modeste',
        7700:'Inactifs', 8100:'Inactifs', 8200:'Inactifs', 8300:'Inactifs', 8400:'Inactifs', 8500:'Inactifs'}
    df['FAM_STN'] = rng.choice(list(gp_fam), n)
    df['SOF_CAT'] = rng.choice(list(gp_csp), n)
    df['Gp_FAM'] = df.FAM_STN.map(gp_fam)
    df['Gp_CSP'] = df.SOF_CAT.map(gp_csp)
    df['POL_SCO'] = rng.integers(-100, 101, n)
    # Demonstration bins, not the undisclosed original score-grouping rules.
    df['POL_SCO_grp'] = pd.cut(df.POL_SCO, [-100, -50, 0, 50, 100],
        labels=['[-100, -50]', ']-50, 0]', ']0, 50]', ']50, 100]'],
        include_lowest=True, right=True).astype(str)
    df['RSK_RNG'] = rng.choice(['High', 'Medium', 'Low', 'Neutral', 'Trust'], n)
    # Fixed groupings shown in the original legend. Observations alone are fictional.
    regional_groups = {
        'Grand Est':'région risque faible', 'Nouvelle-Aquitaine':'région risque faible', 'DOM':'région risque faible',
        'Hauts-de-France':'région risque moyen', 'Provence-Alpes-Côte d’Azur':'région risque moyen',
        'Occitanie':'région risque moyen', 'Normandie':'région risque moyen', 'Centre-Val de Loire':'région risque moyen',
        'Bretagne':'région risque moyen', 'Pays de la Loire':'région risque moyen',
        'Île-de-France':'région risque élevé', 'Bourgogne-Franche-Comté':'région risque élevé', 'Auvergne-Rhône-Alpes':'région risque élevé'}
    df['region_habitation'] = rng.choice(list(regional_groups), n)
    df['region_livraison'] = rng.choice(list(regional_groups), n)
    df['region_acc'] = df.region_habitation.map(regional_groups)
    df['region_shg'] = df.region_livraison.map(regional_groups)
    df['RVN'] = np.round(rng.uniform(800, 6500, n), 2)
    df['VAL_STT_CUS'] = rng.choice(['A', 'AC', 'P', 'PR'], n)
    df['annee_mois'] = df.DAT_CRE_DMD.dt.year * 100 + df.DAT_CRE_DMD.dt.month
    df['période'] = df.DAT_CRE_DMD.dt.to_period('M').astype(str)
    return df.sort_values('DAT_CRE_DMD').reset_index(drop=True)

if __name__ == '__main__':
    path = ROOT / 'data' / 'synthetic_requests.csv'
    path.parent.mkdir(exist_ok=True)
    generate().to_csv(path, index=False)
    print('Created 6,000 fictional requests.')
