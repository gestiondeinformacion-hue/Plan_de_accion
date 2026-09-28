"""Página: Tutelas (cruzadas con valor contratado y diagnóstico)."""
import dash
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html

from componentes import (VERDE, abreviar_tecnologia, barras_h, card_grafico, etiqueta_cohorte, fig_con_valor,
                         figura_vacia, filtro_dropdown, kpi, tabla_por_cohorte,
                         layout_base, tabla_detalle)
from data import IDENT_LABELS, MESES, cargar_tutelas, fmt_num, fmt_pesos, mascaras_cohorte, opciones

dash.register_page(__name__, path="/tutelas", name="Tutelas", order=2)

DF = cargar_tutelas()
COHORTES = mascaras_cohorte(DF)  # {cohorte: máscara}; un registro puede tener varias
P = "tut-"

# Filtros de selección múltiple: (id, etiqueta, columna, ancho)
FILTROS = [
    ("anio", "Año notificación", "Año de Fecha notificacion", False),
    ("mes", "Mes notificación", "Mes de Fecha notificacion", False),
    ("ident", "Identificación servicio", "Identificacion", False),
    ("clas_edad", "Clasificación edad", "clasificacion edad", False),
    ("tipo_serv", "Tipo de servicio", "Tipo servicio", False),
    ("tipo_tec", "Tipo tecnología", "Tipo tecnologia", False),
    ("grupo", "Grupo patología (DX)", "Grupo_PATOLOGIA", False),
    ("municipio", "Municipio afiliado", "BDT Municipio Afiliado", False),
    ("estado_afil", "Estado afil. alto costo", "AltoC_Estado_Afiliacion", False),
    ("capitulo", "Capítulo CIE-10", "Capítulo", True),
    ("ips_dest", "IPS destino", "Ips destino", True),
    ("ips_presc", "IPS prescriptora", "Ips prescriptora", True),
]
FILTRO_IDS = [P + f[0] for f in FILTROS]

EDAD_MIN, EDAD_MAX = int(DF["Edad"].min()), int(DF["Edad"].max())

METRICAS = {
    "tut": ("Tutelas únicas", "Tutelas: %{x:,.0f}"),
    "serv": ("Servicios identificados", "Servicios: %{x:,.0f}"),
    "val": ("Valor total", "Valor: $%{x:,.0f}"),
}

COLS_TABLA = (["BDT Num Tutela", "Identificacion", "Valor"]
              + [c for c in DF.columns[19:58] if c != "BDT Num Tutela"]
              + list(DF.columns[:19]))
COLS_BUSQUEDA = ["BDT Num Tutela", "Cohorte", "BDT Identificacion", "BDT Nombres", "BDT Apellidos", "Servicio",
                 "Descripcion servicio", "Cod dx principal", "Nom dx principal", "Ips destino",
                 "Ips prescriptora"]
PAGE_SIZE = 15


def _opciones_filtro(col):
    if col == "Mes de Fecha notificacion":  # orden calendario, no alfabético
        presentes = set(DF[col].dropna().astype(str))
        return [{"label": m.capitalize(), "value": m} for m in MESES if m in presentes]
    return opciones(DF[col])


# ------------------------------------------------------------------ layout
def _filtros():
    items = [filtro_dropdown("Cohorte", P + "cohorte", [{"label": c, "value": c} for c in COHORTES])]
    items += [filtro_dropdown(lbl, P + id_, _opciones_filtro(col), ancho=ancho)
              for id_, lbl, col, ancho in FILTROS]
    items.append(html.Div(className="filtro filtro-ancho", children=[
        html.Label("Edad"),
        dcc.RangeSlider(id=P + "edad", min=EDAD_MIN, max=EDAD_MAX, step=1,
                        value=[EDAD_MIN, EDAD_MAX], allowCross=False,
                        marks={v: str(v) for v in range(0, EDAD_MAX + 1, 10)},
                        tooltip={"placement": "bottom", "always_visible": False}),
    ]))
    return html.Div(className="filtros", children=[
        html.Div(items, className="filtros-grid"),
        html.Div(className="filtros-acciones", children=[
            html.Div(className="toggle-metrica", children=[
                html.Span("Medir gráficos por:"),
                dcc.RadioItems(id=P + "metrica", value="tut", className="radio-items",
                               options=[{"label": v[0], "value": k} for k, v in METRICAS.items()],
                               inline=True),
            ]),
            html.Button("Limpiar filtros", id=P + "limpiar", className="btn"),
        ]),
    ])


layout = html.Div([
    html.Div(className="header", children=[
        html.Div([
            html.H1("Tutelas · Adultos"),
            html.Div("Tutelas cruzadas con valor contratado y diagnóstico · Análisis exploratorio",
                     className="sub"),
        ]),
        html.Div(className="corte", children=["Notificación: ", html.B("01/2022 – 07/2026")]),
    ]),
    _filtros(),

    # Nivel 1: BANs
    dcc.Loading(html.Div(id=P + "kpis", className="kpis"), color=VERDE, type="dot"),

    # Nivel 2: contexto y tendencia
    html.Div(className="fila fila-2-1", children=[
        card_grafico("Tendencia por mes de notificación", P + "g-tendencia"),
        html.Div(className="card", children=[
            html.Div("Tutelas con valor contratado", className="card-titulo"),
            html.Div("Identificación del código de servicio y del valor", className="card-sub"),
            dcc.Loading(html.Div(id=P + "resumen"), color=VERDE, type="dot"),
        ]),
    ]),
    html.Div(className="fila fila-1-1", children=[
        card_grafico("Top 10 servicios", P + "g-servicio", "Excluye el código 101010101 (NO APLICA)"),
        card_grafico("Top 10 IPS destino", P + "g-ips"),
    ]),
    html.Div(className="fila fila-1-1", children=[
        card_grafico("Por grupo de patología (DX)", P + "g-grupo",
                     "Cantidad · valor total · valor promedio (por tutela; por servicio si mides servicios)"),
        card_grafico("Por cohorte", P + "g-cohorte",
                     "Igual que grupo · un registro con varias cohortes suma en cada una"),
    ]),
    html.Div(className="fila fila-1-1", children=[
        card_grafico("Top 10 municipios del afiliado", P + "g-municipio"),
        card_grafico("Por tipo de servicio", P + "g-tipo"),
    ]),
    html.Div(className="fila", children=[
        card_grafico("Top 10 capítulos CIE-10", P + "g-capitulo"),
    ]),

    # Nivel 3: detalle
    html.Div(className="card", children=[
        html.Div(className="tabla-top", children=[
            html.Div([html.Div("Detalle de registros", className="card-titulo"),
                      html.Div(id=P + "tabla-info", className="card-sub")]),
            html.Div(style={"display": "flex", "gap": "8px"}, children=[
                dcc.Input(id=P + "buscar", type="text", debounce=True, className="buscar",
                          placeholder="Buscar tutela, documento, nombre, servicio, CIE-10, IPS…"),
                html.Button("Descargar CSV", id=P + "descargar", className="btn btn-solido"),
                dcc.Download(id=P + "download"),
            ]),
        ]),
        tabla_detalle(P + "tabla", COLS_TABLA, PAGE_SIZE),
    ]),
])


# ------------------------------------------------------------------ lógica
def filtrar(edad, cohortes, *valores):
    m = pd.Series(True, index=DF.index)
    if cohortes:
        m &= np.logical_or.reduce([COHORTES[c] for c in cohortes])
    if edad and (edad[0] > EDAD_MIN or edad[1] < EDAD_MAX):
        m &= DF["Edad"].between(edad[0], edad[1]).fillna(False).astype(bool)
    for (_, _, col, _), sel in zip(FILTROS, valores):
        if sel:
            m &= DF[col].astype(str).isin(sel)
    return DF[m]


FILTRO_INPUTS = ([Input(P + "edad", "value"), Input(P + "cohorte", "value")]
                 + [Input(i, "value") for i in FILTRO_IDS])


def agregar(d: pd.DataFrame, col: str, metrica: str) -> pd.Series:
    g = d.groupby(col, observed=True)
    if metrica == "tut":
        s = g["BDT Num Tutela"].nunique()
    elif metrica == "serv":
        s = g["Servicio"].count()
    else:
        s = g["Valor"].sum()
    return s[s > 0].sort_values(ascending=False)


def _medidas(sub: pd.DataFrame) -> dict:
    return {"tut": sub["BDT Num Tutela"].nunique(), "serv": sub["Servicio"].count(),
            "val": sub["Valor"].sum()}


def _con_valor(t, metrica, etiqueta=str):
    """Promedio por servicio si se mide por servicios; si no, por tutela."""
    unidad, nombre = ("serv", "servicio") if metrica == "serv" else ("tut", "tutela")
    return fig_con_valor(t, metrica, METRICAS[metrica][1], unidad, nombre, etiqueta=etiqueta)


def fig_grupo(d, metrica):
    g = d.groupby("Grupo_PATOLOGIA", observed=True)
    t = pd.DataFrame({"tut": g["BDT Num Tutela"].nunique(), "serv": g["Servicio"].count(),
                      "val": g["Valor"].sum()})
    return _con_valor(t, metrica)


def fig_cohortes(d, metrica):
    return _con_valor(tabla_por_cohorte(d, COHORTES, _medidas), metrica, etiqueta=etiqueta_cohorte)


def texto_metrica(valores, metrica):
    return [fmt_pesos(v) if metrica == "val" else fmt_num(v) for v in valores]


def fig_barras(d, col, metrica, top=None, height=340, max_chars=40, excluir=None, formato=None):
    if excluir:
        d = d[~d[col].isin(excluir)]
    s = agregar(d, col, metrica)
    if top:
        s = s.head(top)
    if s.empty:
        return figura_vacia(height=height)
    completos = [str(i) for i in s.index]
    etiquetas = [formato(e) for e in completos] if formato else completos
    return barras_h(etiquetas, s.values, texto_metrica(s.values, metrica), METRICAS[metrica][1],
                    height=height, max_chars=max_chars, hover_labels=completos)


def fig_tendencia(d, metrica):
    if d.empty:
        return figura_vacia()
    s = agregar(d, "Fecha_Notificacion", metrica).sort_index()
    fig = go.Figure(go.Bar(
        x=s.index, y=s.values, marker=dict(color=VERDE, cornerradius=3),
        hovertemplate="%{x|%m/%Y}<br>" + METRICAS[metrica][1].replace("%{x", "%{y") + "<extra></extra>"))
    layout_base(fig)
    fig.update_layout(bargap=0.15)
    fig.update_xaxes(tickformat="%m/%Y")
    if metrica == "val":
        fig.update_yaxes(tickprefix="$")
    return fig


def tabla_resumen(d):
    g = d.groupby("Identificacion", observed=False).agg(
        tut=("BDT Num Tutela", "nunique"), serv=("Servicio", "count"),
        valor=("Valor", "sum")).reindex(IDENT_LABELS).fillna(0)
    filas = [html.Tr([html.Td(lbl), html.Td(fmt_num(r.tut)), html.Td(fmt_num(r.serv)),
                      html.Td(fmt_pesos(r.valor) if r.valor else "—")])
             for lbl, r in g.iterrows()]
    filas.append(html.Tr(className="total", children=[
        html.Td("Total general"), html.Td(fmt_num(d["BDT Num Tutela"].nunique())),
        html.Td(fmt_num(d["Servicio"].count())), html.Td(fmt_pesos(d["Valor"].sum()))]))
    return html.Div([
        html.Table(className="tabla-resumen", children=[
            html.Thead(html.Tr([html.Th("Identificación"), html.Th("Tutelas"),
                                html.Th("Servicios"), html.Th("Valor total")])),
            html.Tbody(filas),
        ]),
        html.Div("Una tutela puede tener registros en varias filas; por eso las tutelas por fila "
                 "suman más que el total.", className="card-sub", style={"marginTop": "8px"}),
    ])


def _capitulo_corto(c):
    """'ENFERMEDADES DEL SISTEMA CIRCULATORIO (I00-I99)' -> 'I00-I99 · Enfermedades del sistema…'."""
    if c.endswith(")") and "(" in c:
        nombre, rango = c.rsplit("(", 1)
        return f"{rango[:-1]} · {nombre.strip().capitalize()}"
    return c


@callback(
    Output(P + "kpis", "children"),
    Output(P + "g-tendencia", "figure"), Output(P + "resumen", "children"),
    Output(P + "g-servicio", "figure"), Output(P + "g-ips", "figure"),
    Output(P + "g-grupo", "figure"), Output(P + "g-cohorte", "figure"),
    Output(P + "g-tipo", "figure"),
    Output(P + "g-municipio", "figure"), Output(P + "g-capitulo", "figure"),
    Input(P + "metrica", "value"), *FILTRO_INPUTS,
)
def actualizar(metrica, *args):
    d = filtrar(*args)
    n_tut = d["BDT Num Tutela"].nunique()
    n_per = d["BDT Identificacion"].nunique()
    n_serv = d["Servicio"].count()
    valor = d["Valor"].sum()
    tut_con_valor = d.loc[d["Valor"].notna(), "BDT Num Tutela"].nunique()
    tut_sin_serv = n_tut - d.loc[d["Servicio"].notna(), "BDT Num Tutela"].nunique()
    pct_sin = tut_sin_serv / n_tut * 100 if n_tut else 0
    menores = d.loc[d["clasificacion edad"] == "Menores de edad", "BDT Num Tutela"].nunique()

    kpis = [
        kpi("Tutelas únicas", fmt_num(n_tut), f"{fmt_num(menores)} de menores de edad"),
        kpi("Personas", fmt_num(n_per),
            f"{n_tut / n_per:.1f} tutelas por persona".replace(".", ",") if n_per else None),
        kpi("Servicios identificados", fmt_num(n_serv),
            f"{fmt_num(d['Valor'].notna().sum())} con valor contratado"),
        kpi("Valor total", fmt_pesos(valor), "Valor contratado × cantidad"),
        kpi("Valor promedio por tutela", fmt_pesos(valor / tut_con_valor) if tut_con_valor else "$0",
            f"Sobre {fmt_num(tut_con_valor)} tutelas con valor"),
        kpi("Tutelas sin servicio", f"{pct_sin:.1f}%".replace(".", ","),
            f"{fmt_num(tut_sin_serv)} sin ningún código de servicio", alerta=True),
    ]
    d_serv = d.assign(Serv=d["Servicio"].astype(str) + " · " + d["Descripcion servicio"].astype(str))
    # 101010101 "NO APLICA" es un código de relleno, no un servicio.
    d_serv = d_serv[d["Servicio"].notna() & (d["Servicio"].astype(str).str.lstrip("0") != "101010101")]
    return (
        kpis,
        fig_tendencia(d, metrica),
        tabla_resumen(d),
        fig_barras(d_serv, "Serv", metrica, top=10, max_chars=48, formato=abreviar_tecnologia),
        fig_barras(d, "Ips destino", metrica, top=10, max_chars=48, excluir=["Sin información"]),
        fig_grupo(d, metrica),
        fig_cohortes(d, metrica),
        fig_barras(d, "Tipo servicio", metrica, height=340),
        fig_barras(d, "BDT Municipio Afiliado", metrica, top=10),
        fig_barras(d, "Capítulo", metrica, top=10, max_chars=70, excluir=["Sin información"],
                   formato=_capitulo_corto),
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
    pag["Valor"] = pag["Valor"].map(lambda v: "" if pd.isna(v) else "$" + fmt_num(v))
    pag = pag.astype(object).where(pag.notna(), "")
    registros = pag.to_dict("records")
    tooltips = [{c: {"value": str(r[c]), "type": "text"} for c in
                 ("Descripcion servicio", "Nom dx principal", "Ips destino", "Ips prescriptora",
                  "Capítulo")} for r in registros]
    paginas = max(1, -(-len(d) // PAGE_SIZE))
    return registros, paginas, tooltips, f"{fmt_num(len(d))} registros · ordena haciendo clic en el encabezado"


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
    return dcc.send_data_frame(d.to_csv, "tutelas_filtrado.csv", sep=";",
                               index=False, encoding="utf-8-sig", decimal=",")


@callback(
    Output(P + "edad", "value"), Output(P + "cohorte", "value"),
    *[Output(i, "value") for i in FILTRO_IDS],
    Input(P + "limpiar", "n_clicks"),
    prevent_initial_call=True,
)
def limpiar(_):
    return ([EDAD_MIN, EDAD_MAX], None, *([None] * len(FILTRO_IDS)))
