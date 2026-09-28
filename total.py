"""Página: Total consolidado (Autorizaciones + PQR + Tutelas) con rango de desviación ajustable."""
import dash
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html

import numpy as np

from componentes import (AZUL, VERDE, abreviar_tecnologia, card_grafico, etiqueta_cohorte,
                         fig_con_valor, figura_vacia, filtro_dropdown, kpi, layout_base,
                         tabla_por_cohorte)
from data import (FUENTES, cargar_consolidado, fmt_num, fmt_pesos, mascaras_cohorte, opciones,
                  valor_duplicado)

dash.register_page(__name__, path="/total", name="Total", order=4)

DF = cargar_consolidado()
COHORTES = mascaras_cohorte(DF)  # un registro puede tener varias cohortes
P = "tot-"
DESVIACION_DEFECTO = 15

COLOR_FUENTE = {"Autorizaciones": VERDE, "PQR": AZUL, "Tutelas": "#7FCFC8", "Medicamentos": "#8A6FB0"}
INICIAL = {"Autorizaciones": "A", "PQR": "P", "Tutelas": "T", "Medicamentos": "M"}

FILTROS = [
    ("fuente", "Fuente", "Fuente", False),
    ("grupo", "Grupo patología", "Grupo", False),
    ("municipio", "Municipio afiliado", "Municipio", False),
]
FILTRO_IDS = [P + f[0] for f in FILTROS]


# ------------------------------------------------------------------ layout
def _filtros():
    items = [html.Div(className="filtro filtro-ancho", children=[
        html.Label("Desviación (±%)"),
        dcc.Slider(id=P + "desv", min=0, max=50, step=1, value=DESVIACION_DEFECTO,
                   marks={v: f"{v}%" for v in range(0, 51, 10)},
                   tooltip={"placement": "bottom", "always_visible": False}),
    ])]
    items += [filtro_dropdown(lbl, P + id_, opciones(DF[col]), ancho=ancho)
              for id_, lbl, col, ancho in FILTROS]
    items.append(filtro_dropdown("Cohorte", P + "cohorte", [{"label": c, "value": c} for c in COHORTES]))
    items.append(html.Div(className="filtro", children=[
        html.Label("Registros"),
        dcc.Dropdown(id=P + "cruce", clearable=False, value="todos", options=[
            {"label": "Todos", "value": "todos"},
            {"label": "Solo en cruce", "value": "cruce"},
            {"label": "Sin cruce", "value": "sin"},
        ]),
    ]))
    return html.Div(className="filtros", children=[
        html.Div(items, className="filtros-grid"),
        html.Div(className="filtros-acciones", children=[
            html.Div("Cruce = mismo documento y mismo código de servicio en más de una base.",
                     className="card-sub"),
            html.Button("Restablecer", id=P + "limpiar", className="btn"),
        ]),
    ])


layout = html.Div([
    html.Div(className="header", children=[
        html.Div([
            html.H1("Total consolidado"),
            html.Div("Autorizaciones (incluye anuladas) + PQR + Tutelas + Medicamentos (faltantes) · "
                     "Valor con rango de desviación ajustable",
                     className="sub"),
        ]),
        html.Div(className="corte", id=P + "corte-desv"),
    ]),
    _filtros(),

    dcc.Loading(html.Div(id=P + "kpis", className="kpis"), color=VERDE, type="dot"),

    html.Div(className="fila fila-1-1", children=[
        card_grafico("Valor por fuente con rango de desviación", P + "g-fuente",
                     "La barra es el valor; la línea marca el mínimo y el máximo"),
        html.Div(className="card", children=[
            html.Div("Resumen por fuente", className="card-titulo"),
            dcc.Loading(html.Div(id=P + "resumen", style={"overflowX": "auto"}), color=VERDE, type="dot"),
        ]),
    ]),
    html.Div(className="fila fila-1-1", children=[
        card_grafico("Por grupo de patología", P + "g-grupo",
                     "Casos (solicitudes, PQ, tutelas y fórmulas) · valor total · valor promedio por caso"),
        card_grafico("Por cohorte", P + "g-cohorte",
                     "Igual que grupo · un registro con varias cohortes suma en cada una"),
    ]),
    html.Div(className="fila fila-1-1", children=[
        card_grafico("Afiliados según número de bases en que aparecen", P + "g-nbases"),
        html.Div(className="card", children=[
            html.Div("Cruces entre bases", className="card-titulo"),
            html.Div("Combinación exacta de bases (A = Autorizaciones, P = PQR, T = Tutelas, M = Medicamentos)",
                     className="card-sub"),
            dcc.Loading(html.Div(id=P + "cruces"), color=VERDE, type="dot"),
        ]),
    ]),
    html.Div(className="fila", children=[
        card_grafico("Top 10 municipios por valor", P + "g-municipio",
                     "Sin registros sin municipio (las anuladas no traen datos del afiliado)"),
    ]),
    html.Div(className="card", children=[
        html.Div("Top 15 servicios en cruce por valor", className="card-titulo"),
        html.Div("Afiliado + servicio presente en más de una base", className="card-sub"),
        dcc.Loading(html.Div(id=P + "top-cruce"), color=VERDE, type="dot"),
    ]),
])


# ------------------------------------------------------------------ lógica
def filtrar(cruce, cohortes, *valores):
    m = pd.Series(True, index=DF.index)
    if cohortes:
        m &= np.logical_or.reduce([COHORTES[c] for c in cohortes])
    for (_, _, col, _), sel in zip(FILTROS, valores):
        if sel:
            m &= DF[col].astype(str).isin(sel)
    if cruce == "cruce":
        m &= DF["En_Cruce"]
    elif cruce == "sin":
        m &= ~DF["En_Cruce"]
    return DF[m]


def _tabla(encabezados, filas, total=None, izquierda=(0,)):
    """Tabla HTML; las columnas en `izquierda` se alinean a la izquierda (texto)."""
    def celdas(valores, tag):
        return [tag(v, className="izq" if i in izquierda else None) for i, v in enumerate(valores)]
    cuerpo = [html.Tr(celdas(f, html.Td)) for f in filas]
    if total:
        cuerpo.append(html.Tr(celdas(total, html.Td), className="total"))
    return html.Table(className="tabla-resumen", children=[
        html.Thead(html.Tr(celdas(encabezados, html.Th))), html.Tbody(cuerpo)])


def fig_fuente(d, pct):
    s = d.groupby("Fuente", observed=False)["Valor"].sum().reindex(FUENTES).fillna(0)
    if s.sum() == 0:
        return figura_vacia()
    f = pct / 100
    millones = s.values / 1e6
    fig = go.Figure(go.Bar(
        x=s.index, y=millones, marker=dict(color=[COLOR_FUENTE[x] for x in s.index], cornerradius=4),
        error_y=dict(type="data", array=millones * f, color=AZUL, thickness=1.5, width=10),
        text=[fmt_pesos(v) for v in s.values], textposition="inside", insidetextanchor="start",
        textfont=dict(color=[AZUL if x == "Tutelas" else "#fff" for x in s.index], size=11),
        customdata=list(zip(s.values, s.values * (1 - f), s.values * (1 + f))),
        hovertemplate="<b>%{x}</b><br>Valor: $%{customdata[0]:,.0f}<br>Mínimo: $%{customdata[1]:,.0f}"
                      "<br>Máximo: $%{customdata[2]:,.0f}<extra></extra>"))
    layout_base(fig, height=320)
    fig.update_yaxes(tickprefix="$", ticksuffix=" M", tickformat=",.0f")
    return fig


def fig_nbases(d):
    if d.empty:
        return figura_vacia()
    s = d.drop_duplicates("Documento")["Documento"].map(
        d.groupby("Documento")["Fuente"].nunique()).value_counts().reindex(range(1, len(FUENTES) + 1)).fillna(0)
    fig = go.Figure(go.Bar(
        x=[f"{i} base" + ("s" if i > 1 else "") for i in s.index], y=s.values,
        marker=dict(color=VERDE, cornerradius=4), text=[fmt_num(v) for v in s.values],
        textposition="outside", cliponaxis=False, textfont=dict(color=AZUL, size=11),
        hovertemplate="%{x}<br>Afiliados: %{y:,.0f}<extra></extra>"))
    layout_base(fig, height=300)
    fig.update_yaxes(showticklabels=False, showgrid=False)
    fig.update_layout(margin=dict(l=8, r=8, t=24, b=8))
    return fig


BIT_FUENTE = {f: 2 ** i for i, f in enumerate(FUENTES)}
# Todas las combinaciones de 2 o más bases, de menos a más bases (A+P, A+T, …, A+P+T+M)
COMBOS = {bits: "+".join(INICIAL[f] for f in FUENTES if bits & BIT_FUENTE[f])
          for bits in sorted(range(1, 2 ** len(FUENTES)), key=lambda b: (bin(b).count("1"), b))
          if bin(bits).count("1") >= 2}


def _combinacion(d, clave):
    """Código de bases (suma de bits A=1, P=2, T=4) en que aparece cada clave."""
    u = d.dropna(subset=[clave]).drop_duplicates([clave, "Fuente"])
    return u["Fuente"].astype(str).map(BIT_FUENTE).groupby(u[clave]).sum()


def tabla_cruces(d):
    combo_afil = _combinacion(d, "Documento")
    combo_srv = _combinacion(d, "Clave")
    valor_srv = d.dropna(subset=["Clave"]).groupby("Clave")["Valor"].sum()
    filas = []
    for bits, nombre in COMBOS.items():
        claves = combo_srv.index[combo_srv == bits]
        n_afil = (combo_afil == bits).sum()
        if n_afil or len(claves):  # solo combinaciones que ocurren
            filas.append([nombre, fmt_num(n_afil), fmt_num(len(claves)),
                          fmt_pesos(valor_srv.reindex(claves).sum())])
    return _tabla(["Bases", "Afiliados", "Afiliado + servicio", "Valor en cruce"], filas)


def fig_apilado(d, col, top=None, height=430):
    t = d.groupby([col, "Fuente"], observed=True)["Valor"].sum().unstack(fill_value=0)
    t = t.reindex(columns=FUENTES, fill_value=0)
    t = t[t.sum(axis=1) > 0]
    t = t.loc[t.sum(axis=1).sort_values(ascending=False).index]
    if top:
        t = t.head(top)
    if t.empty:
        return figura_vacia(height=height)
    etiquetas = [str(i) if len(str(i)) <= 30 else str(i)[:29] + "…" for i in t.index]
    fig = go.Figure()
    for f in FUENTES:
        fig.add_bar(y=etiquetas, x=t[f] / 1e6, name=f, orientation="h",
                    marker=dict(color=COLOR_FUENTE[f], line=dict(color="#fff", width=1)),
                    customdata=list(zip(t.index, t[f])),
                    hovertemplate=f"<b>%{{customdata[0]}}</b><br>{f}: $%{{customdata[1]:,.0f}}<extra></extra>")
    layout_base(fig, height=height, barmode="stack")
    fig.update_layout(legend=dict(traceorder="normal"))
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)", tickfont=dict(color=AZUL, size=10.5))
    fig.update_xaxes(tickprefix="$", ticksuffix=" M", tickformat=",.0f", showgrid=True, gridcolor="#EEF2F3")
    return fig


def _medidas(sub):
    return {"casos": sub["Id_Caso"].nunique(), "val": sub["Valor"].sum()}


def _con_valor(t, etiqueta=str):
    return fig_con_valor(t, "casos", "Casos: %{x:,.0f}", "casos", "caso", etiqueta=etiqueta)


def fig_grupo(d):
    g = d.groupby("Grupo", observed=True)
    return _con_valor(pd.DataFrame({"casos": g["Id_Caso"].nunique(), "val": g["Valor"].sum()}))


def fig_cohortes(d):
    return _con_valor(tabla_por_cohorte(d, COHORTES, _medidas), etiqueta=etiqueta_cohorte)


def tabla_top_cruce(d):
    c = d[d["En_Cruce"]]
    if c.empty:
        return html.Div("Sin servicios en cruce para los filtros seleccionados", className="card-sub")
    desc = c.dropna(subset=["Descripcion"]).groupby("Codigo")["Descripcion"].first()
    g = c.groupby("Codigo").agg(afil=("Documento", "nunique"), valor=("Valor", "sum"),
                                bases=("Fuente", lambda s: "+".join(INICIAL[f] for f in FUENTES
                                                                    if f in set(s))))
    g = g.sort_values("valor", ascending=False).head(15)
    filas = [[cod, abreviar_tecnologia(str(desc.get(cod, "")))[:70], r.bases, fmt_num(r.afil),
              fmt_pesos(r.valor)] for cod, r in g.iterrows()]
    return _tabla(["Código", "Descripción", "Bases", "Afiliados", "Valor"], filas, izquierda=(0, 1, 2))


@callback(
    Output(P + "kpis", "children"), Output(P + "corte-desv", "children"),
    Output(P + "g-fuente", "figure"), Output(P + "resumen", "children"),
    Output(P + "g-nbases", "figure"), Output(P + "cruces", "children"),
    Output(P + "g-grupo", "figure"), Output(P + "g-cohorte", "figure"), Output(P + "g-municipio", "figure"),
    Output(P + "top-cruce", "children"),
    Input(P + "desv", "value"), Input(P + "cruce", "value"), Input(P + "cohorte", "value"),
    *[Input(i, "value") for i in FILTRO_IDS],
)
def actualizar(pct, cruce, cohortes, *valores):
    pct = pct if pct is not None else DESVIACION_DEFECTO
    f = pct / 100
    d = filtrar(cruce, cohortes, *valores)
    total = d["Valor"].sum()
    en_cruce = d.loc[d["En_Cruce"], "Valor"].sum()
    dup = valor_duplicado(d)

    kpis = [
        kpi("Total general", fmt_pesos(total),
            f"Incluye {fmt_pesos(d.loc[d['Anulada'], 'Valor'].sum())} de anuladas"),
        kpi(f"Mínimo (−{pct}%)", fmt_pesos(total * (1 - f)), "Escenario bajo"),
        kpi(f"Máximo (+{pct}%)", fmt_pesos(total * (1 + f)), "Escenario alto"),
        kpi("Afiliados únicos", fmt_num(d["Documento"].nunique()), "En cualquiera de las bases"),
        kpi("Valor en cruce", fmt_pesos(en_cruce),
            f"{en_cruce / total * 100:.1f}% del total".replace(".", ",") if total else None),
        kpi("Valor repetido", fmt_pesos(dup), "Sobra si cada cruce se cuenta una vez", alerta=True),
    ]

    s = d.groupby("Fuente", observed=False).agg(
        reg=("Valor", "size"), afil=("Documento", "nunique"), valor=("Valor", "sum")).reindex(FUENTES)
    filas = [[fu, fmt_num(r.reg), fmt_num(r.afil), fmt_pesos(r.valor),
              fmt_pesos(r.valor * (1 - f)), fmt_pesos(r.valor * (1 + f)),
              f"{r.valor / total * 100:.1f}%".replace(".", ",") if total else "—"]
             for fu, r in s.fillna(0).iterrows()]
    total_fila = ["Total", fmt_num(len(d)), fmt_num(d["Documento"].nunique()), fmt_pesos(total),
                  fmt_pesos(total * (1 - f)), fmt_pesos(total * (1 + f)), "100%"]
    resumen = _tabla(["Fuente", "Registros", "Afiliados", "Valor", "Mínimo", "Máximo", "%"],
                     filas, total_fila)

    return (
        kpis, ["Desviación: ", html.B(f"±{pct}%")],
        fig_fuente(d, pct), resumen,
        fig_nbases(d), tabla_cruces(d),
        fig_grupo(d), fig_cohortes(d), fig_apilado(d[d["Municipio"] != "SIN INFORMACION"], "Municipio", top=10, height=380),
        tabla_top_cruce(d),
    )


@callback(
    Output(P + "desv", "value"), Output(P + "cruce", "value"), Output(P + "cohorte", "value"),
    *[Output(i, "value") for i in FILTRO_IDS],
    Input(P + "limpiar", "n_clicks"),
    prevent_initial_call=True,
)
def limpiar(_):
    return (DESVIACION_DEFECTO, "todos", None, *([None] * len(FILTRO_IDS)))
