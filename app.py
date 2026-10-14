"""Three-page Dash demonstration, using synthetic data exclusively."""
from pathlib import Path
import pandas as pd
from dash import Dash, dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go
from analysis import validate, kpis, weekly
from generate_data import generate

ROOT = Path(__file__).resolve().parent
data_path = ROOT / 'data' / 'synthetic_requests.csv'
df = pd.read_csv(data_path, parse_dates=['DAT_CRE_DMD']) if data_path.exists() else generate()
validate(df)
app = Dash(__name__)
app.title = 'Ketty Kaze | Démonstration data'
app.layout = html.Main([
    html.P('PORTFOLIO · KETTY CARÈNE KAZE', className='eyebrow'),
    html.H1('Analyse de demandes de crédit'),
    html.P('Cette démonstration reprend la démarche de mon projet de stage avec des données entièrement fictives, afin de protéger la confidentialité des données de l’entreprise.', className='notice'),
    html.P('Une démonstration pédagogique de préparation, exploration et visualisation des données.'),
    html.Div([html.Label('Période analysée'), dcc.DatePickerRange(id='period',
        start_date=df.DAT_CRE_DMD.min().date(), end_date=df.DAT_CRE_DMD.max().date(),
        min_date_allowed=df.DAT_CRE_DMD.min().date(), max_date_allowed=df.DAT_CRE_DMD.max().date(),
        display_format='DD/MM/YYYY')], className='filters'),
    dcc.Tabs(id='page', value='overview', children=[
        dcc.Tab(label='1. Analyse des demandes', value='overview'),
        dcc.Tab(label='2. Comparaison des profils', value='profiles'),
        dcc.Tab(label='3. Évolution hebdomadaire', value='time')]),
    html.Div([html.Label('Date pour la semaine analysée (page Évolution)'),
        dcc.DatePickerSingle(id='week-date', date='2025-06-25', display_format='DD/MM/YYYY')], className='filters'),
    html.Div(id='content'),
])

def graph(fig):
    fig.update_layout(template='plotly_white', colorway=['#137c70', '#d18435'], margin=dict(t=55, l=45, r=25, b=50))
    return dcc.Graph(figure=fig, config={'displaylogo': False})

@app.callback(Output('content', 'children'), Input('page', 'value'), Input('period', 'start_date'), Input('period', 'end_date'), Input('week-date', 'date'))
def render(page, start, end, selected_week='2025-06-25'):
    if not start or not end:
        return html.P('Sélectionnez les deux dates.')
    d = df[(df.DAT_CRE_DMD >= pd.Timestamp(start)) & (df.DAT_CRE_DMD < pd.Timestamp(end) + pd.Timedelta(days=1))]
    if d.empty and page != 'time':
        return html.P('Aucune demande pour cette période.')
    k = kpis(d)
    fmt = lambda v: 'Non calculable' if v is None else f'{v:.2f} %'
    if page == 'overview':
        cards = [("Demandes", k['requests']), ('Acceptées', k['ACC']), ('Dossiers topés fraude', k['top_susp_frd_fnc']),
            ('Âge moyen', f'{d.age_client.mean():.1f} ans'), ('Âge médian', f'{d.age_client.median():.1f} ans'), ('Revenu moyen', f'{d.RVN.mean():.0f} €')]
        charts = []
        for column, title in [('Gp_FAM','Répartition par situation familiale'),('Gp_CSP','Répartition par profession')]:
            counts = d.groupby(column, observed=True).size().reset_index(name='demandes')
            charts.append(graph(px.pie(counts, names=column, values='demandes', hole=.4, title=title)))
        for column, title, order in [('tranche_age','Répartition par tranche d’âge',['18-24','25-35','36-48','49-55','56-98']),
            ('tranche_montant','Répartition par tranche de montant',['0-250','250-500','500-750','750-1000','1000-1500','1500-3000'])]:
            counts = d.groupby(['période',column], observed=True).size().reset_index(name='demandes')
            charts.append(graph(px.bar(counts,x='période',y='demandes',color=column,barmode='stack',category_orders={column:order},title=title)))
        for column,title in [('region_acc','Catégorie de région d’habitation'),('region_shg','Catégorie de région de livraison')]:
            charts.append(graph(px.histogram(d,x=column,title=title)))
        return [html.Div([html.Div([html.Small(label), html.Strong(str(value))], className='kpi') for label, value in cards], className='kpis'),
            html.P('Acceptation = acceptées / demandes. Fraude = dossiers acceptés topés fraude / acceptées.'),
            html.Div(charts, className='charts')]
    if page == 'profiles':
        groups = [('Topés fraude', d[(d.ACC == 1) & (d.top_susp_frd_fnc == 1)]), ('Non topés fraude', d[(d.ACC == 1) & (d.top_susp_frd_fnc == 0)])]
        values = [('Nb Accepté', [str(len(g)) for _,g in groups])]
        for label, col, unit in [('Âge moyen', 'age_client', ' ans'), ('Montant moyen', 'MNT_ACH', ' €')]:
            values.append((label,[f'{g[col].mean():.1f}{unit}' if len(g) else 'Non calculable' for _,g in groups]))
        for label, col in [('Profession dominante', 'Gp_CSP'), ('Score dominant', 'POL_SCO_grp'), ('Région dominante', 'region_acc')]:
            values.append((label,[', '.join(map(str,g[col].mode().tolist())) if len(g) else 'Non calculable' for _,g in groups]))
        rows=[html.Tr([html.Th('Profil Fraudeur'),html.Th('Indicateur'),html.Th('Profil Bon Client')])]
        rows.extend(html.Tr([html.Td(v[0]),html.Td(label),html.Td(v[1])]) for label,v in values)
        return [html.H2('Comparaison des Profils Clients'),html.P(f'Analyse réalisée sur {k["ACC"]} demandes acceptées'), html.Table(rows,className='profile-comparison'),
            html.P('Score dominant : intervalle de démonstration le plus fréquent. Les égalités sont affichées.')]
    if not selected_week:
        return html.P('Choisissez une date pour sélectionner la semaine.')
    chosen=pd.Timestamp(selected_week).normalize()
    last=chosen-pd.Timedelta(days=chosen.weekday())
    weeks=pd.date_range(end=last,periods=8,freq='7D')
    d=df.copy();d['week']=d.DAT_CRE_DMD-pd.to_timedelta(d.DAT_CRE_DMD.dt.weekday,unit='D')
    selected=d[d.week.isin(weeks)]
    accepted=selected[selected.ACC==1]
    totals=accepted.groupby('week').size().reindex(weeks,fill_value=0)
    figures=[]
    for column,title in [('tranche_montant','Répartition des acceptés par tranche de montant'),('POL_SCO_grp','Répartition des acceptés par score'),('RSK_RNG','Répartition des acceptés par risque rating'),('region_acc','Répartition des acceptés par région d’habitation'),('region_shg','Répartition des acceptés par région de livraison')]:
        fig=go.Figure()
        for label in sorted(df[column].unique()):
            counts=accepted[accepted[column]==label].groupby('week').size().reindex(weeks,fill_value=0)
            fig.add_bar(x=weeks,y=100*counts/totals.where(totals>0),name=str(label))
        fig.update_layout(title=title,barmode='stack',yaxis={'title':'% des acceptés','range':[0,100]},xaxis={'title':'Semaine débutant le'})
        figures.append(graph(fig))
    annual=d[d.DAT_CRE_DMD.dt.year==chosen.year]
    ranking=annual.groupby('week').agg(accepted=('ACC','sum'),fraud=('top_susp_frd_fnc','sum'))
    ranking['rate']=100*ranking.fraud/ranking.accepted.where(ranking.accepted>0)
    ranking=ranking.dropna(subset=['rate']).sort_values('rate',ascending=False).head(6)
    rows=[html.Tr([html.Th('Semaine débutant le'),html.Th('Taux de fraude'),html.Th('Topés fraude / acceptés')])]
    rows.extend(html.Tr([html.Td(f'{week:%d/%m/%Y}'),html.Td(f'{row.rate:.2f} %'),html.Td(f'{int(row.fraud)} / {int(row.accepted)}')]) for week,row in ranking.iterrows())
    legend=html.P('Regroupements du projet : risque faible — Grand Est, Nouvelle-Aquitaine, DOM ; moyen — Hauts-de-France, Provence-Alpes-Côte d’Azur, Occitanie, Normandie, Centre-Val de Loire, Bretagne, Pays de la Loire ; élevé — Île-de-France, Bourgogne-Franche-Comté, Auvergne-Rhône-Alpes.')
    return [html.H2('Évolution de la fraude — démonstration'),
        html.Div(figures[:2],className='charts'),html.H3('Semaines aux taux les plus élevés'),html.Table(rows),
        html.Div(figures[2:],className='charts'),legend,html.P('Les intervalles de score sont propres à la démonstration. Les semaines sans acceptés restent vides.')]

if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=8050)
