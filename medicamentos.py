"""Página: Medicamentos · faltantes de los gestores farmacéuticos (MEDIC, TODO DROGAS, COHAN)."""
import dash
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html

from componentes import (AZUL, VERDE, barras_h, card_grafico, figura_vacia, filtro_dropdown, kpi,
                         layout_base, tabla_detalle)
from data import fmt_num, fmt_pesos, opciones
from data_medicamentos import DIAS_LABELS, HOMOLOGACION, cargar_medicamentos

dash.register_page(__name__, path="/medicamentos", name="Medicamentos", order=3)

DF = cargar_medicamentos()
# Una fórmula se identifica por gestor + consecutivo (COHAN usa NUMERO FORMULA como fecha; TODO DROGAS no trae consecutivo)
DF["Formula_Id"] = (DF["Gestor"].astype(str) + "-"
                    + DF["Consecutivo_Formula"].fillna(DF["Numero_Formula"]).astype(str))
P = "med-"
CORTE = DF["Fecha_Faltante"].max()

COLOR_GESTOR = {"MEDIC": VERDE, "COHAN": AZUL, "TODO DROGAS": "#7FCFC8"}

FILTROS = [
    ("gestor", "Gestor farmacéutico", "Gestor", False),
    ("municipio", "Municipio afiliado", "Municipio_Afiliado", False),
    ("tipo", "Tipo fórmula", "Tipo_Formula", False),
    ("contrato", "Contrato", "Descripcion_Contrato", False),
    ("motivo", "Motivo faltante", "Motivo_Faltante", False),
    ("dias", "Días en faltante", "Rango_Dias", False),
    ("bodega", "Bodega", "Nombre_Bodega", True),
    ("medicamento", "Medicamento", "Nombre_Medicamento", True),
    ("diagnostico", "Diagnóstico", "Diagnostico", True),
]
FILTRO_IDS = [P + f[0] for f in FILTROS]
F_MIN, F_MAX = DF["Fecha_Faltante"].min().date(), DF["Fecha_Faltante"].max().date()

METRICAS = {
    "reg": ("Registros", "Registros: %{x:,.0f}"),
    "und": ("Unidades faltantes", "Unidades: %{x:,.0f}"),
    "val": ("Valor faltante estimado", "Valor: $%{x:,.0f}"),
}

COLS_TABLA = (["Gestor"] + list(HOMOLOGACION)
              + ["Valor_Faltante_Estimado", "Dias_Faltante", "Faltante_Corregido", "Cantidad_Faltante_Original"])
COLS_BUSQUEDA = ["Documento_Afiliado", "Nombre_Afiliado", "Numero_Formula", "Consecutivo_Formula",
                 "Nombre_Medicamento", "Codigo_Medicamento", "Codigo_DCI", "Codigo_Diagnostico"]
PAGE_SIZE = 15


def _opciones(col):
    if col == "Rango_Dias":
        return [{"label": f"{r} días", "value": r} for r in DIAS_LABELS]
    return opciones(DF[col].astype(str))


# ------------------------------------------------------------------ layout
def _filtros():
    items = [html.Div(className="filtro filtro-ancho", children=[
        html.Label("Fecha del faltante"),
        dcc.DatePickerRange(id=P + "fechas", min_date_allowed=F_MIN, max_date_allowed=F_MAX,
                            start_date=F_MIN, end_date=F_MAX, display_format="DD/MM/YYYY",
                            first_day_of_week=1, minimum_nights=0),
    ])]
    items += [filtro_dropdown(lbl, P + id_, _opciones(col), ancho=ancho) for id_, lbl, col, ancho in FILTROS]
    return html.Div(className="filtros", children=[
        html.Div(items, className="filtros-grid"),
        html.Div(className="filtros-acciones", children=[
            html.Div(className="toggle-metrica", children=[
                html.Span("Medir gráficos por:"),
                dcc.RadioItems(id=P + "metrica", value="reg", className="radio-items",
                               options=[{"label": v[0], "value": k} for k, v in METRICAS.items()],
                               inline=True),
            ]),
            html.Button("Limpiar filtros", id=P + "limpiar", className="btn"),
        ]),
    ])


layout = html.Div([
    html.Div(className="header", children=[
        html.Div([
            html.H1("Medicamentos · Faltantes"),
            html.Div("Gestores farmacéuticos MEDIC, TODO DROGAS y COHAN · variables homologadas · "
                     "Análisis exploratorio", className="sub"),
        ]),
        html.Div(className="corte", children=["Último faltante: ", html.B(CORTE.strftime("%d/%m/%Y"))]),
    ]),
    _filtros(),

    dcc.Loading(html.Div(id=P + "kpis", className="kpis kpis-7"), color=VERDE, type="dot"),

    html.Div(className="fila fila-2-1", children=[
        card_grafico("Tendencia por fecha del faltante", P + "g-tendencia", "Agrupado por semana"),
        card_grafico("Días en faltante", P + "g-dias", f"Desde la fecha del faltante hasta el {CORTE:%d/%m/%Y}"),
    ]),
    html.Div(className="fila fila-1-1", children=[
        card_grafico("Top 15 medicamentos faltantes", P + "g-medicamento"),
        card_grafico("Top 15 diagnósticos", P + "g-diagnostico"),
    ]),
    html.Div(className="fila fila-1-1", children=[
        card_grafico("Por gestor farmacéutico", P + "g-gestor",
                     "Valor estimado = valor unitario × cantidad faltante (COHAN no trae valores)"),
        card_grafico("Motivo del faltante", P + "g-motivo", "Solo COHAN y TODO DROGAS lo reportan"),
    ]),
    html.Div(className="fila fila-1-1", children=[
        card_grafico("Top 10 bodegas", P + "g-bodega"),
        card_grafico("Top 10 municipios del afiliado", P + "g-municipio"),
    ]),

    html.Div(className="card", children=[
        html.Div(className="tabla-top", children=[
            html.Div([html.Div("Detalle de faltantes (variables homologadas)", className="card-titulo"),
                      html.Div(id=P + "tabla-info", className="card-sub")]),
            html.Div(style={"display": "flex", "gap": "8px"}, children=[
                dcc.Input(id=P + "buscar", type="text", debounce=True, className="buscar",
                          placeholder="Buscar documento, nombre, fórmula, medicamento, DCI, CIE-10…"),
                html.Button("Descargar CSV", id=P + "descargar", className="btn btn-solido"),
                dcc.Download(id=P + "download"),
            ]),
        ]),
        tabla_detalle(P + "tabla", COLS_TABLA, PAGE_SIZE),
    ]),
])


# ------------------------------------------------------------------ lógica
def filtrar(fecha_ini, fecha_fin, *valores):
    m = pd.Series(True, index=DF.index)
    if fecha_ini:
        m &= DF["Fecha_Faltante"] >= pd.Timestamp(fecha_ini)
    if fecha_fin:
        m &= DF["Fecha_Faltante"] <= pd.Timestamp(fecha_fin)
    for (_, _, col, _), sel in zip(FILTROS, valores):
        if sel:
            m &= DF[col].astype(str).isin(sel)
    return DF[m]


FILTRO_INPUTS = ([Input(P + "fechas", "start_date"), Input(P + "fechas", "end_date")]
                 + [Input(i, "value") for i in FILTRO_IDS])


def agregar(d: pd.DataFrame, col: str, metrica: str) -> pd.Series:
    g = d.groupby(col, observed=True)
    s = g.size() if metrica == "reg" else g["Cantidad_Faltante"].sum() if metrica == "und" \
        else g["Valor_Faltante_Estimado"].sum()
    return s[s > 0].sort_values(ascending=False)


def texto_metrica(valores, metrica):
    return [fmt_pesos(v) if metrica == "val" else fmt_num(v) for v in valores]


def fig_barras(d, col, metrica, top=None, height=340, max_chars=45, excluir=None):
    if excluir:
        d = d[~d[col].astype(str).isin(excluir)]
    s = agregar(d, col, metrica)
    if top:
        s = s.head(top)
    if s.empty:
        return figura_vacia(height=height)
    etiquetas = [str(i) for i in s.index]
    return barras_h(etiquetas, s.values, texto_metrica(s.values, metrica), METRICAS[metrica][1],
                    height=height, max_chars=max_chars)


def fig_tendencia(d, metrica):
    if d.empty:
        return figura_vacia()
    d = d.assign(Semana=d["Fecha_Faltante"].dt.to_period("W-SUN").dt.start_time)
    fig = go.Figure()
    for gestor, color in COLOR_GESTOR.items():
        sub = d[d["Gestor"] == gestor]
        if sub.empty:
            continue
        s = agregar(sub, "Semana", metrica).sort_index()
        fig.add_bar(x=s.index, y=s.values, name=gestor, marker=dict(color=color, cornerradius=3),
                    hovertemplate=f"<b>{gestor}</b><br>Semana del %{{x|%d/%m/%Y}}<br>"
                    + METRICAS[metrica][1].replace("%{x", "%{y") + "<extra></extra>")
    layout_base(fig, barmode="stack")
    fig.update_layout(bargap=0.15, legend=dict(traceorder="normal"))
    fig.update_xaxes(tickformat="%d/%m")
    if metrica == "val":
        fig.update_yaxes(tickprefix="$")
    return fig


def fig_dias(d, metrica):
    s = agregar(d, "Rango_Dias", metrica).reindex(DIAS_LABELS).fillna(0)
    if s.sum() == 0:
        return figura_vacia()
    fig = go.Figure(go.Bar(
        x=s.index, y=s.values, marker=dict(color=VERDE, cornerradius=4),
        text=texto_metrica(s.values, metrica), textposition="outside", cliponaxis=False,
        textfont=dict(size=10, color=AZUL),
        hovertemplate="<b>%{x} días</b><br>" + METRICAS[metrica][1].replace("%{x", "%{y") + "<extra></extra>"))
    layout_base(fig)
    fig.update_xaxes(tickangle=0, title=dict(text="días", font=dict(size=10, color="#8899A6")))
    fig.update_yaxes(showticklabels=False, showgrid=False)
    fig.update_layout(margin=dict(l=8, r=8, t=20, b=8))
    return fig


@callback(
    Output(P + "kpis", "children"),
    Output(P + "g-tendencia", "figure"), Output(P + "g-dias", "figure"),
    Output(P + "g-medicamento", "figure"), Output(P + "g-diagnostico", "figure"),
    Output(P + "g-gestor", "figure"), Output(P + "g-motivo", "figure"),
    Output(P + "g-bodega", "figure"), Output(P + "g-municipio", "figure"),
    Input(P + "metrica", "value"), *FILTRO_INPUTS,
)
def actualizar(metrica, *args):
    d = filtrar(*args)
    valor = d["Valor_Faltante_Estimado"].sum()
    sin_valor = d["Valor_Faltante_Estimado"].isna().sum()
    mediana = d["Dias_Faltante"].median() if len(d) else 0
    pct_sin_entregar = (d["Entregado"] == "Sin entregar").mean() * 100 if len(d) else 0
    kpis = [
        kpi("Registros faltantes", fmt_num(len(d)), f"{d['Gestor'].nunique()} gestores"),
        kpi("Pacientes", fmt_num(d["Documento_Afiliado"].nunique()),
            f"{len(d) / d['Documento_Afiliado'].nunique():.1f} faltantes por paciente".replace(".", ",")
            if len(d) else None),
        kpi("Fórmulas", fmt_num(d["Formula_Id"].nunique())),
        kpi("Medicamentos distintos", fmt_num(d["Nombre_Medicamento"].nunique())),
        kpi("Unidades faltantes", fmt_num(d["Cantidad_Faltante"].sum()),
            f"de {fmt_num(d['Cantidad_Solicitada'].sum())} solicitadas · "
            f"{fmt_num((d['Faltante_Corregido'] == 'Sí').sum())} corregidas"),
        kpi("Valor faltante estimado", fmt_pesos(valor), f"{fmt_num(sin_valor)} registros sin valor (COHAN)"),
        kpi("Sin entregar", f"{pct_sin_entregar:.1f}%".replace(".", ","),
            f"Mediana {0 if pd.isna(mediana) else mediana:.0f} días en faltante", alerta=True),
    ]
    return (
        kpis,
        fig_tendencia(d, metrica),
        fig_dias(d, metrica),
        fig_barras(d, "Nombre_Medicamento", metrica, top=15, height=440, max_chars=50),
        fig_barras(d, "Diagnostico", metrica, top=15, height=440, max_chars=50),
        fig_barras(d, "Gestor", metrica, height=260),
        fig_barras(d, "Motivo_Faltante", metrica, height=260, excluir=["Sin información"]),
        fig_barras(d, "Nombre_Bodega", metrica, top=10, max_chars=45),
        fig_barras(d, "Municipio_Afiliado", metrica, top=10),
    )


def _tabla_filtrada(buscar, sort_by, args):
    d = filtrar(*args)
    if buscar:
        q = buscar.strip().upper()
        m = pd.Series(False, index=d.index)
        for c in COLS_BUSQUEDA:
            m |= d[c].astype(str).str.upper().str.contains(q, regex=False, na=False)
        d = d[m]
    if sort_by:
        d = d.sort_values(sort_by[0]["column_id"], ascending=sort_by[0]["direction"] == "asc")
    return d


@callback(
    Output(P + "tabla", "data"), Output(P + "tabla", "page_count"),
    Output(P + "tabla", "tooltip_data"), Output(P + "tabla-info", "children"),
    Input(P + "tabla", "page_current"), Input(P + "tabla", "sort_by"),
    Input(P + "buscar", "value"), *FILTRO_INPUTS,
)
def actualizar_tabla(page, sort_by, buscar, *args):
    d = _tabla_filtrada(buscar, sort_by, args)
    page = page or 0
    pag = d.iloc[page * PAGE_SIZE:(page + 1) * PAGE_SIZE][COLS_TABLA].copy()
    for c in ("Fecha_Formula", "Fecha_Faltante", "Fecha_Entrega_Faltante"):
        pag[c] = pag[c].dt.strftime("%d/%m/%Y")
    for c in ("Valor_Unitario", "Valor_Total", "Valor_Faltante_Estimado"):
        pag[c] = pag[c].map(lambda v: "" if pd.isna(v) else "$" + fmt_num(v))
    pag = pag.astype(object).where(pag.notna(), "")
    registros = pag.to_dict("records")
    tooltips = [{c: {"value": str(r[c]), "type": "text"} for c in
                 ("Nombre_Medicamento", "Descripcion_Diagnostico", "Nombre_Bodega")} for r in registros]
    return (registros, max(1, -(-len(d) // PAGE_SIZE)), tooltips,
            f"{fmt_num(len(d))} registros · ordena haciendo clic en el encabezado")


@callback(
    Output(P + "tabla", "page_current"),
    Input(P + "buscar", "value"), Input(P + "tabla", "sort_by"), *FILTRO_INPUTS,
    prevent_initial_call=True,
)
def reiniciar_pagina(*_):
    return 0


@callback(
    Output(P + "download", "data"),
    Input(P + "descargar", "n_clicks"),
    State(P + "buscar", "value"), State(P + "tabla", "sort_by"),
    *[State(i.component_id, i.component_property) for i in FILTRO_INPUTS],
    prevent_initial_call=True,
)
def descargar(_, buscar, sort_by, *args):
    d = _tabla_filtrada(buscar, sort_by, args)[COLS_TABLA]
    return dcc.send_data_frame(d.to_csv, "medicamentos_faltantes_filtrado.csv", sep=";",
                               index=False, encoding="utf-8-sig", decimal=",")


@callback(
    Output(P + "fechas", "start_date"), Output(P + "fechas", "end_date"),
    *[Output(i, "value") for i in FILTRO_IDS],
    Input(P + "limpiar", "n_clicks"),
    prevent_initial_call=True,
)
def limpiar(_):
    return (F_MIN, F_MAX, *([None] * len(FILTRO_IDS)))
