"""Página: PQR (PQRSD cruzadas con valor contratado y diagnóstico)."""
import dash
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html

from componentes import (AZUL, VERDE, barras_h, card_grafico, etiqueta_cohorte, fig_con_valor,
                         figura_vacia, tabla_por_cohorte,
                         filtro_dropdown, kpi, layout_base, tabla_detalle)
from data import (ANTIG_LABELS, IDENT_LABELS, cargar_pq, fmt_num, fmt_pesos, mascaras_cohorte,
                  opciones)

dash.register_page(__name__, path="/pqr", name="PQR", order=1)

DF = cargar_pq()
COHORTES = mascaras_cohorte(DF)  # {cohorte: máscara}; un registro puede tener varias
P = "pq-"

# Filtros de selección múltiple: (id, etiqueta, columna, ancho)
FILTROS = [
    ("ident", "Identificación servicio", "Identificacion", False),
    ("tipo", "Tipo de solicitud", "tipo_solicitud", False),
    ("origen", "Origen PQRD", "origen_pqrd", False),
    ("ente", "Ente de control", "ente_control", False),
    ("estado", "Estado del caso", "estado_caso", False),
    ("riesgo", "Clasificación de riesgo", "clasificacion_de_riesgo", False),
    ("oportunidad", "Oportunidad respuesta", "oportunidad_respuesta", False),
    ("estado_serv", "Estado del servicio", "estado_servicio", False),
    ("region", "Región afiliación", "region_afiliacion", False),
    ("municipio", "Municipio afiliación", "mpio_afiliacion", False),
    ("regimen", "Régimen", "regimen_afiliacion", False),
    ("sexo", "Sexo", "sexo_afectado", False),
    ("grupo", "Grupo patología (DX)", "DX_Grupo_PATOLOGIAS", False),
    ("tipo_motivo", "Tipo de motivo", "tipo_motivo_especifico", False),
    ("responsable", "Responsable del caso", "responsable_caso", False),
    ("medicamento", "Medicamento", "medicamento", False),
    ("motivo", "Motivo específico", "motivo_especifico", True),
    ("ips", "IPS responsable de respuesta", "IPS_responsable_respuesta", True),
    ("capitulo", "Capítulo CIE-10", "Capítulo", True),
]
FILTRO_IDS = [P + f[0] for f in FILTROS]

EDAD_MIN, EDAD_MAX = int(DF["Edad"].min()), int(DF["Edad"].max())
F_MIN, F_MAX = DF["Fecha_Creacion"].min().date(), DF["Fecha_Creacion"].max().date()

# Medidas iguales a las de Tableau: RECDIST(numero_solicitud_pqrsf), REC(codigo_servicio_pqrd),
# SUMA(5_valor_contratado).
METRICAS = {
    "pq": ("PQ únicas", "PQ: %{x:,.0f}"),
    "serv": ("Servicios identificados", "Servicios: %{x:,.0f}"),
    "val": ("Valor contratado", "Valor: $%{x:,.0f}"),
}

DERIVADAS = ["Identificacion", "Fecha_Creacion", "Dias_Gestion", "Edad", "Valor"]
COLS_TABLA = (["numero_solicitud_pqrsf", "Identificacion", "Dias_Gestion", "Valor"]
              + [c for c in DF.columns[57:] if c not in DERIVADAS + ["numero_solicitud_pqrsf",
                                                                   "Rango_Dias", "Rango_Edad"]]
              + list(DF.columns[:57]))
COLS_BUSQUEDA = ["numero_solicitud_pqrsf", "Cohorte", "radicado_SNS", "identificacion_afectado",
                 "nombre_afectado", "codigo_servicio_pqrd", "descripcion_servicio_pqrd",
                 "codigo_CIE10", "IPS_responsable_respuesta", "descripcion_caso"]
PAGE_SIZE = 15


# ------------------------------------------------------------------ layout
def _filtros():
    items = [html.Div(className="filtro filtro-ancho", children=[
        html.Label("Fecha de creación del caso"),
        dcc.DatePickerRange(
            id=P + "fechas", min_date_allowed=F_MIN, max_date_allowed=F_MAX,
            start_date=F_MIN, end_date=F_MAX, display_format="DD/MM/YYYY",
            first_day_of_week=1, minimum_nights=0),
    ])]
    items.append(filtro_dropdown("Cohorte", P + "cohorte",
                                 [{"label": c, "value": c} for c in COHORTES]))
    items += [filtro_dropdown(lbl, P + id_, opciones(DF[col]), ancho=ancho)
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
                dcc.RadioItems(id=P + "metrica", value="pq", className="radio-items",
                               options=[{"label": v[0], "value": k} for k, v in METRICAS.items()],
                               inline=True),
            ]),
            html.Button("Limpiar filtros", id=P + "limpiar", className="btn"),
        ]),
    ])


layout = html.Div([
    html.Div(className="header", children=[
        html.Div([
            html.H1("PQR"),
            html.Div("PQRSD cruzadas con valor contratado y diagnóstico · Análisis exploratorio",
                     className="sub"),
        ]),
        html.Div(className="corte", children=["Fecha de corte: ", html.B("01/09/2026")]),
    ]),
    _filtros(),

    # Nivel 1: BANs
    dcc.Loading(html.Div(id=P + "kpis", className="kpis"), color=VERDE, type="dot"),

    # Nivel 2: contexto y tendencia
    html.Div(className="fila fila-2-1", children=[
        card_grafico("Tendencia por fecha de creación del caso", P + "g-tendencia"),
        card_grafico("Días de gestión", P + "g-dias",
                     "Creación → cierre; casos abiertos: creación → 01/09/2026"),
    ]),
    html.Div(className="fila fila-1-1", children=[
        card_grafico("Top 10 motivos específicos", P + "g-motivo"),
        card_grafico("Motivo de respuesta del prestador", P + "g-respuesta",
                     "Solo servicios con motivo registrado"),
    ]),
    html.Div(className="fila fila-1-1", children=[
        card_grafico("Por grupo de patología (DX)", P + "g-grupo",
                     "Cantidad · valor total · valor promedio (por PQ; por servicio si mides servicios)"),
        card_grafico("Por cohorte", P + "g-cohorte",
                     "Igual que grupo · un registro con varias cohortes suma en cada una"),
    ]),
    html.Div(className="fila fila-1-1", children=[
        card_grafico("Por región de afiliación", P + "g-region"),
        card_grafico("Por origen de la PQRD", P + "g-origen"),
    ]),
    html.Div(className="fila fila-2-1", children=[
        card_grafico("Top 10 IPS responsables de respuesta", P + "g-ips"),
        html.Div(className="card", children=[
            html.Div("PQRS con valor contratado", className="card-titulo"),
            html.Div("Identificación del código de servicio y del valor", className="card-sub"),
            dcc.Loading(html.Div(id=P + "resumen"), color=VERDE, type="dot"),
        ]),
    ]),

    # Nivel 3: detalle
    html.Div(className="card", children=[
        html.Div(className="tabla-top", children=[
            html.Div([html.Div("Detalle de registros", className="card-titulo"),
                      html.Div(id=P + "tabla-info", className="card-sub")]),
            html.Div(style={"display": "flex", "gap": "8px"}, children=[
                dcc.Input(id=P + "buscar", type="text", debounce=True, className="buscar",
                          placeholder="Buscar PQ, radicado, documento, nombre, servicio, CIE-10…"),
                html.Button("Descargar CSV", id=P + "descargar", className="btn btn-solido"),
                dcc.Download(id=P + "download"),
            ]),
        ]),
        tabla_detalle(P + "tabla", COLS_TABLA, PAGE_SIZE),
    ]),
])


# ------------------------------------------------------------------ lógica
def filtrar(fecha_ini, fecha_fin, edad, cohortes, *valores):
    m = pd.Series(True, index=DF.index)
    if cohortes:
        m &= np.logical_or.reduce([COHORTES[c] for c in cohortes])
    if fecha_ini:
        m &= DF["Fecha_Creacion"] >= pd.Timestamp(fecha_ini)
    if fecha_fin:
        m &= DF["Fecha_Creacion"] <= pd.Timestamp(fecha_fin)
    if edad and (edad[0] > EDAD_MIN or edad[1] < EDAD_MAX):
        m &= DF["Edad"].between(edad[0], edad[1]).fillna(False).astype(bool)
    for (_, _, col, _), sel in zip(FILTROS, valores):
        if sel:
            m &= DF[col].isin(sel)
    return DF[m]


FILTRO_INPUTS = ([Input(P + "fechas", "start_date"), Input(P + "fechas", "end_date"),
                  Input(P + "edad", "value"), Input(P + "cohorte", "value")]
                 + [Input(i, "value") for i in FILTRO_IDS])


def agregar(d: pd.DataFrame, col: str, metrica: str) -> pd.Series:
    g = d.groupby(col, observed=True)
    if metrica == "pq":
        s = g["numero_solicitud_pqrsf"].nunique()
    elif metrica == "serv":
        s = g["codigo_servicio_pqrd"].count()
    else:
        s = g["Valor"].sum()
    return s[s > 0].sort_values(ascending=False)


def _medidas(sub: pd.DataFrame) -> dict:
    return {"pq": sub["numero_solicitud_pqrsf"].nunique(), "serv": sub["codigo_servicio_pqrd"].count(),
            "val": sub["Valor"].sum()}


def _con_valor(t, metrica, etiqueta=str):
    """Promedio por servicio si se mide por servicios; si no, por PQ."""
    unidad, nombre = ("serv", "servicio") if metrica == "serv" else ("pq", "PQ")
    return fig_con_valor(t, metrica, METRICAS[metrica][1], unidad, nombre, etiqueta=etiqueta)


def fig_grupo(d, metrica):
    g = d.groupby("DX_Grupo_PATOLOGIAS", observed=True)
    t = pd.DataFrame({"pq": g["numero_solicitud_pqrsf"].nunique(),
                      "serv": g["codigo_servicio_pqrd"].count(), "val": g["Valor"].sum()})
    return _con_valor(t, metrica)


def fig_cohortes(d, metrica):
    return _con_valor(tabla_por_cohorte(d, COHORTES, _medidas), metrica, etiqueta=etiqueta_cohorte)


def texto_metrica(valores, metrica):
    return [fmt_pesos(v) if metrica == "val" else fmt_num(v) for v in valores]


def fig_barras(d, col, metrica, top=None, height=340, max_chars=40, excluir=None):
    if excluir:
        d = d[~d[col].isin(excluir)]
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
    f = d["Fecha_Creacion"]
    rango = (f.max() - f.min()).days
    freq, nombre = ("D", "día") if rango <= 45 else (("W-SUN", "semana") if rango <= 240 else ("M", "mes"))
    s = agregar(d.assign(Periodo=f.dt.to_period(freq).dt.start_time), "Periodo", metrica).sort_index()
    fig = go.Figure(go.Bar(
        x=s.index, y=s.values, marker=dict(color=VERDE, cornerradius=3),
        hovertemplate="%{x|%d/%m/%Y}<br>" + METRICAS[metrica][1].replace("%{x", "%{y") + "<extra></extra>"))
    layout_base(fig)
    fig.update_layout(bargap=0.15, margin=dict(l=8, r=16, t=24, b=8))
    fig.update_xaxes(tickformat="%d/%m/%Y" if freq == "D" else "%m/%Y")
    fig.add_annotation(text=f"Agrupado por {nombre}", xref="paper", yref="paper", x=1, y=1.08,
                       showarrow=False, font=dict(size=10, color="#8899A6"), xanchor="right")
    if metrica == "val":
        fig.update_yaxes(tickprefix="$")
    return fig


def fig_dias(d, metrica):
    s = agregar(d, "Rango_Dias", metrica).reindex(ANTIG_LABELS).fillna(0)
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


def tabla_resumen(d):
    """Réplica de la tabla 'PQRS con Valor Contratado' (Tableau) sobre los datos filtrados."""
    g = d.groupby("Identificacion", observed=False).agg(
        pq=("numero_solicitud_pqrsf", "nunique"), serv=("codigo_servicio_pqrd", "count"),
        valor=("Valor", "sum")).reindex(IDENT_LABELS).fillna(0)
    filas = [html.Tr([html.Td(lbl), html.Td(fmt_num(r.pq)), html.Td(fmt_num(r.serv)),
                      html.Td(fmt_pesos(r.valor) if r.valor else "—")])
             for lbl, r in g.iterrows()]
    filas.append(html.Tr(className="total", children=[
        html.Td("Total general"), html.Td(fmt_num(d["numero_solicitud_pqrsf"].nunique())),
        html.Td(fmt_num(d["codigo_servicio_pqrd"].count())), html.Td(fmt_pesos(d["Valor"].sum()))]))
    return html.Table(className="tabla-resumen", children=[
        html.Thead(html.Tr([html.Th("Identificación"), html.Th("PQ únicas"),
                            html.Th("Servicios"), html.Th("Valor")])),
        html.Tbody(filas),
    ])


@callback(
    Output(P + "kpis", "children"),
    Output(P + "g-tendencia", "figure"), Output(P + "g-dias", "figure"),
    Output(P + "g-motivo", "figure"), Output(P + "g-respuesta", "figure"),
    Output(P + "g-grupo", "figure"), Output(P + "g-cohorte", "figure"),
    Output(P + "g-region", "figure"),
    Output(P + "g-origen", "figure"), Output(P + "g-ips", "figure"),
    Output(P + "resumen", "children"),
    Input(P + "metrica", "value"), *FILTRO_INPUTS,
)
def actualizar(metrica, *args):
    d = filtrar(*args)
    casos = d.drop_duplicates("numero_solicitud_pqrsf")
    n_pq = len(casos)
    n_serv = d["codigo_servicio_pqrd"].count()
    n_con_valor = d["Valor"].notna().sum()
    n_afe = d["identificacion_afectado"].nunique()
    mediana = casos["Dias_Gestion"].median() if n_pq else 0
    pct_ext = (casos["oportunidad_respuesta"] == "Extemporáneo").mean() * 100 if n_pq else 0

    kpis = [
        kpi("PQ únicas", fmt_num(n_pq), "Número de solicitud PQRSF distintos"),
        kpi("Servicios identificados", fmt_num(n_serv),
            f"{fmt_num(n_con_valor)} con valor contratado"),
        kpi("Valor contratado", fmt_pesos(d["Valor"].sum()), "Suma de 5_valor_contratado"),
        kpi("Afectados", fmt_num(n_afe),
            f"{n_pq / n_afe:.1f} PQ por afectado".replace(".", ",") if n_afe else None),
        kpi("Días de gestión (mediana)", f"{0 if pd.isna(mediana) else mediana:.0f} días", "Por caso"),
        kpi("Extemporáneas", f"{pct_ext:.1f}%".replace(".", ","), "De las PQ filtradas", alerta=True),
    ]
    return (
        kpis,
        fig_tendencia(d, metrica),
        fig_dias(d, metrica),
        fig_barras(d, "motivo_especifico", metrica, top=10, max_chars=48),
        fig_barras(d, "motivo_de_respuesta", metrica, top=10, max_chars=40, excluir=["Sin información"]),
        fig_grupo(d, metrica),
        fig_cohortes(d, metrica),
        fig_barras(d, "region_afiliacion", metrica, height=380),
        fig_barras(d, "origen_pqrd", metrica, height=380),
        fig_barras(d, "IPS_responsable_respuesta", metrica, top=10, height=380, max_chars=48),
        tabla_resumen(d),
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
                 ("motivo_especifico", "descripcion_caso", "descripcion_ult_gest_caso",
                  "descripcion_gestion_servicio", "descripcion_rechazo_servicio",
                  "descripcion_servicio_pqrd", "Nombre diagnóstico")} for r in registros]
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
    return dcc.send_data_frame(d.to_csv, "pqr_filtrado.csv", sep=";",
                               index=False, encoding="utf-8-sig", decimal=",")


@callback(
    Output(P + "fechas", "start_date"), Output(P + "fechas", "end_date"), Output(P + "edad", "value"),
    Output(P + "cohorte", "value"),
    *[Output(i, "value") for i in FILTRO_IDS],
    Input(P + "limpiar", "n_clicks"),
    prevent_initial_call=True,
)
def limpiar(_):
    return (F_MIN, F_MAX, [EDAD_MIN, EDAD_MAX], None, *([None] * len(FILTRO_IDS)))


@callback(
    Output(P + "municipio", "options"),
    Input(P + "region", "value"),
)
def municipios_por_region(regiones):
    d = DF if not regiones else DF[DF["region_afiliacion"].isin(regiones)]
    return opciones(d["mpio_afiliacion"].astype(str))
