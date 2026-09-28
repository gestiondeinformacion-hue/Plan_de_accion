"""Página: Autorizaciones (Pendientes por Autorizar + Autorizadas No Prestadas)."""
import dash
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html

from componentes import (AZUL, VERDE, abreviar_tecnologia, barras_h, etiqueta_cohorte, fig_con_valor,
                         tabla_por_cohorte, card_grafico, figura_vacia,
                         filtro_dropdown, kpi, layout_base, tabla_detalle)
from data import (ANTIG_LABELS, EDAD_LABELS, MARCA_ANULADA, ORIGEN_ANULADAS, cargar_autorizaciones,
                  fmt_num, fmt_pesos, mascaras_cohorte, opciones)

dash.register_page(__name__, path="/", name="Autorizaciones", order=0)

DF = cargar_autorizaciones()
COHORTES = mascaras_cohorte(DF)  # {cohorte: máscara booleana alineada con DF}
P = "aut-"  # prefijo de ids de esta página

COLOR_ORIGEN = {"Pendientes por Autorizar": VERDE, "Autorizadas No Prestadas": AZUL,
                ORIGEN_ANULADAS: "#7FCFC8"}
COLOR_GENERO = {"FEMENINO": VERDE, "MASCULINO": AZUL}

# Filtros de selección múltiple: (id, etiqueta, columna, ancho)
FILTROS = [
    ("poblacion", "Población", "Poblacion", False),
    ("origen", "Origen", "Archivo_Origen", False),
    ("anulada", "No prestada anulada", "Anulada_Despues", False),
    ("estado", "Estado", "Estado", False),
    ("grupo", "Grupo", "Grupo", False),
    ("region", "Región afiliado", "Region_Afiliado", False),
    ("municipio", "Municipio afiliado", "Municipio_Afiliado", False),
    ("regimen", "Régimen", "Regimen_Afiliacion", False),
    ("genero", "Género", "Genero", False),
    ("estado_afil", "Estado afiliación", "Estado_Afiliacion", False),
    ("cobertura", "Cobertura", "Cobertura_Tecnologia", False),
    ("tipo_tec", "Tipo tecnología", "Tipo_Tecnologia", False),
    ("cruce", "Cruce de valor", "Tipo_Cruce_Valor", False),
    ("prestador", "Prestador que solicita", "Razon_Social_Prestador_Solicita", True),
    ("servicio", "Servicio solicitado", "Servicio_solicitado", True),
]
FILTRO_IDS = [P + f[0] for f in FILTROS]

EDAD_MIN, EDAD_MAX = int(DF["Edad"].min()), int(DF["Edad"].max())
F_MIN, F_MAX = DF["Fecha_Referencia"].min().date(), DF["Fecha_Referencia"].max().date()

METRICAS = {
    "sol": ("Solicitudes", "Solicitudes: %{x:,.0f}"),
    "reg": ("Tecnologías", "Tecnologías: %{x:,.0f}"),
    "val": ("Valor total", "Valor: $%{x:,.0f}"),
}

COLS_TABLA = [c for c in DF.columns
              if c not in ("Fecha_Referencia", "Rango_Antiguedad", "Rango_Edad", "Tecnologia")]
COLS_BUSQUEDA = ["Numero_Solicitud", "Cohorte", "Documento_Afiliado", "Primer_Apellido", "Primer_Nombre",
                 "Desc_Tecnologia", "Cod_Tecnologia", "Nombre_Diagnostico_Principal",
                 "Codigo_Diagnostico_Principal", "Razon_Social_Prestador_Solicita",
                 "Numero_Autorizacion"]
PAGE_SIZE = 15


# ------------------------------------------------------------------ layout
def _filtros():
    items = [
        html.Div(className="filtro filtro-ancho", children=[
            html.Label("Fecha de referencia"),
            dcc.DatePickerRange(
                id=P + "fechas", min_date_allowed=F_MIN, max_date_allowed=F_MAX,
                start_date=F_MIN, end_date=F_MAX, display_format="DD/MM/YYYY",
                first_day_of_week=1, start_date_placeholder_text="Desde",
                end_date_placeholder_text="Hasta", minimum_nights=0),
        ]),
    ]
    items.append(filtro_dropdown("Cohorte", P + "cohorte",
                                 [{"label": c, "value": c} for c in COHORTES]))
    items += [filtro_dropdown(lbl, P + id_, opciones(DF[col]), ancho=ancho)
              for id_, lbl, col, ancho in FILTROS]
    items.append(html.Div(className="filtro filtro-ancho", children=[
        html.Label("Edad"),
        dcc.RangeSlider(id=P + "edad", min=EDAD_MIN, max=EDAD_MAX, step=1,
                        value=[EDAD_MIN, EDAD_MAX], allowCross=False,
                        marks={v: str(v) for v in range(0, EDAD_MAX + 1, 10) if v >= EDAD_MIN},
                        tooltip={"placement": "bottom", "always_visible": False}),
    ]))
    return html.Div(className="filtros", children=[
        html.Div(items, className="filtros-grid"),
        html.Div(className="filtros-acciones", children=[
            html.Div(className="toggle-metrica", children=[
                html.Span("Medir gráficos por:"),
                dcc.RadioItems(id=P + "metrica", value="sol", className="radio-items",
                               options=[{"label": v[0], "value": k} for k, v in METRICAS.items()],
                               inline=True),
            ]),
            html.Button("Limpiar filtros", id=P + "limpiar", className="btn"),
        ]),
    ])


layout = html.Div([
    html.Div(className="header", children=[
        html.Div([
            html.H1("Autorizaciones"),
            html.Div("Pendientes, no prestadas y anuladas · adultos y menores · Análisis exploratorio",
                     className="sub"),
        ]),
        html.Div(className="corte", children=["Fecha de corte: ", html.B("20/08/2026")]),
    ]),
    _filtros(),

    # Nivel 1: BANs
    dcc.Loading(html.Div(id=P + "kpis", className="kpis kpis-7"), color=VERDE, type="dot"),

    # Nivel 2: contexto y tendencia
    html.Div(className="fila fila-2-1", children=[
        card_grafico("Tendencia por fecha de referencia", P + "g-tendencia",
                     "Pendientes: fecha de solicitud · No prestadas: orden médica · Anuladas: fecha de autorización"),
        card_grafico("Antigüedad al corte", P + "g-antig", "Días entre la fecha de referencia y el 20/08/2026"),
    ]),
    html.Div(className="fila fila-1-1", children=[
        card_grafico("Por grupo", P + "g-grupo",
                     "Cantidad · valor total · valor promedio (por solicitud; por tecnología si mides tecnologías)"),
        card_grafico("Por cohorte", P + "g-cohorte",
                     "Igual que grupo · un registro con varias cohortes suma en cada una"),
    ]),
    html.Div(className="fila fila-1-1", children=[
        card_grafico("Por región del afiliado", P + "g-region"),
        card_grafico("Edad y género", P + "g-edad", "Afiliados únicos"),
    ]),
    html.Div(className="fila fila-1-1", children=[
        card_grafico("Top 10 prestadores que solicitan", P + "g-prestador"),
        card_grafico("Top 10 tecnologías", P + "g-tecnologia"),
    ]),

    # Nivel 3: detalle
    html.Div(className="card", children=[
        html.Div(className="tabla-top", children=[
            html.Div([html.Div("Detalle de registros", className="card-titulo"),
                      html.Div(id=P + "tabla-info", className="card-sub")]),
            html.Div(style={"display": "flex", "gap": "8px"}, children=[
                dcc.Input(id=P + "buscar", type="text", debounce=True, className="buscar",
                          placeholder="Buscar solicitud, documento, nombre, CUPS, prestador…"),
                html.Button("Descargar CSV", id=P + "descargar", className="btn btn-solido"),
                dcc.Download(id=P + "download"),
            ]),
        ]),
        tabla_detalle(P + "tabla", COLS_TABLA, PAGE_SIZE),
    ]),
])


# ------------------------------------------------------------------ lógica
def filtrar(fechas_ini, fechas_fin, edad, cohortes, *valores):
    m = pd.Series(True, index=DF.index)
    if cohortes:
        m &= np.logical_or.reduce([COHORTES[c] for c in cohortes])
    if fechas_ini:
        m &= DF["Fecha_Referencia"] >= pd.Timestamp(fechas_ini)
    if fechas_fin:
        m &= DF["Fecha_Referencia"] <= pd.Timestamp(fechas_fin)
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
    if metrica == "sol":
        s = g["Numero_Solicitud"].nunique()
    elif metrica == "reg":
        s = g.size()
    else:
        s = g["Valor_Total"].sum()
    return s[s > 0].sort_values(ascending=False)


def texto_metrica(valores, metrica):
    return [fmt_pesos(v) if metrica == "val" else fmt_num(v) for v in valores]


def fig_barras(d, col, metrica, top=None, height=300, max_chars=45):
    s = agregar(d, col, metrica)
    if top:
        s = s.head(top)
    if s.empty:
        return figura_vacia(height=height)
    return barras_h([str(i) for i in s.index], s.values, texto_metrica(s.values, metrica),
                    METRICAS[metrica][1], height=height, max_chars=max_chars)


def _medidas(sub: pd.DataFrame) -> dict:
    return {"sol": sub["Numero_Solicitud"].nunique(), "reg": len(sub),
            "val": sub["Valor_Total"].sum()}


def _con_valor(t, metrica, etiqueta=str):
    """Promedio por tecnología si se mide por tecnologías; si no, por solicitud."""
    unidad, nombre = ("reg", "tecnología") if metrica == "reg" else ("sol", "solicitud")
    return fig_con_valor(t, metrica, METRICAS[metrica][1], unidad, nombre, etiqueta=etiqueta)


def fig_grupo(d, metrica):
    g = d.groupby("Grupo", observed=True)
    t = pd.DataFrame({"sol": g["Numero_Solicitud"].nunique(), "reg": g.size(),
                      "val": g["Valor_Total"].sum()})
    return _con_valor(t, metrica)


def fig_cohortes(d, metrica):
    """Un registro con varias cohortes suma en cada una."""
    return _con_valor(tabla_por_cohorte(d, COHORTES, _medidas), metrica, etiqueta=etiqueta_cohorte)


def fig_tecnologias(d, metrica, top=10, height=340):
    s = agregar(d, "Tecnologia", metrica).head(top)
    if s.empty:
        return figura_vacia(height=height)
    completos = [str(i) for i in s.index]
    cortos = [abreviar_tecnologia(c) for c in completos]
    return barras_h(cortos, s.values, texto_metrica(s.values, metrica), METRICAS[metrica][1],
                    height=height, max_chars=36, hover_labels=completos)


def fig_tendencia(d, metrica):
    if d.empty:
        return figura_vacia()
    f = d["Fecha_Referencia"]
    rango = (f.max() - f.min()).days
    freq, nombre = ("D", "día") if rango <= 45 else (("W-SUN", "semana") if rango <= 240 else ("M", "mes"))
    d = d.assign(Periodo=f.dt.to_period(freq).dt.start_time)
    fig = go.Figure()
    for origen, color in COLOR_ORIGEN.items():
        sub = d[d["Archivo_Origen"] == origen]
        if sub.empty:
            continue
        s = agregar(sub, "Periodo", metrica).sort_index()
        fig.add_bar(x=s.index, y=s.values, name=origen, marker=dict(color=color, cornerradius=3),
                    hovertemplate=f"<b>{origen}</b><br>%{{x|%d/%m/%Y}}<br>"
                    + METRICAS[metrica][1].replace("%{x", "%{y") + "<extra></extra>")
    layout_base(fig, barmode="stack")
    fig.update_layout(bargap=0.15, hovermode="closest")
    fig.add_annotation(text=f"Agrupado por {nombre}", xref="paper", yref="paper", x=1, y=1.08,
                       showarrow=False, font=dict(size=10, color="#8899A6"), xanchor="right")
    fig.update_xaxes(tickformat="%d/%m/%Y" if freq == "D" else "%m/%Y")
    if metrica == "val":
        fig.update_yaxes(tickprefix="$")
    return fig


def fig_antiguedad(d, metrica):
    s = agregar(d, "Rango_Antiguedad", metrica).reindex(ANTIG_LABELS).fillna(0)
    if s.sum() == 0:
        return figura_vacia()
    fig = go.Figure(go.Bar(
        x=s.index, y=s.values, marker=dict(color=VERDE, cornerradius=4),
        text=texto_metrica(s.values, metrica), textposition="outside", cliponaxis=False,
        textfont=dict(size=10, color=AZUL),
        hovertemplate="<b>%{x}</b><br>" + METRICAS[metrica][1].replace("%{x", "%{y") + "<extra></extra>"))
    layout_base(fig)
    fig.update_xaxes(tickangle=0, title=dict(text="días", font=dict(size=10, color="#8899A6")))
    fig.update_yaxes(showticklabels=False, showgrid=False)
    fig.update_layout(margin=dict(l=8, r=8, t=20, b=8))
    return fig


def fig_edad_genero(d):
    if d.empty:
        return figura_vacia()
    t = (d.drop_duplicates("Documento_Afiliado")
         .groupby(["Rango_Edad", "Genero"], observed=True).size().unstack(fill_value=0)
         .reindex(EDAD_LABELS).fillna(0))
    fig = go.Figure()
    for gen, color in COLOR_GENERO.items():
        if gen in t:
            fig.add_bar(x=t.index, y=t[gen], name=gen.capitalize(),
                        marker=dict(color=color, cornerradius=3),
                        hovertemplate=f"<b>{gen.capitalize()}</b> · %{{x}}<br>Afiliados: %{{y:,.0f}}<extra></extra>")
    layout_base(fig, barmode="group")
    fig.update_layout(bargap=0.2, bargroupgap=0.08)
    return fig


@callback(
    Output(P + "kpis", "children"),
    Output(P + "g-tendencia", "figure"), Output(P + "g-antig", "figure"),
    Output(P + "g-grupo", "figure"), Output(P + "g-cohorte", "figure"), Output(P + "g-region", "figure"),
    Output(P + "g-prestador", "figure"), Output(P + "g-tecnologia", "figure"),
    Output(P + "g-edad", "figure"),
    Input(P + "metrica", "value"), *FILTRO_INPUTS,
)
def actualizar(metrica, *args):
    d = filtrar(*args)

    n_sol = d["Numero_Solicitud"].nunique()
    n_afi = d["Documento_Afiliado"].nunique()
    valor = d["Valor_Total"].sum()
    sin_valor = int(d["Valor_Total"].isna().sum())
    mediana = d["Dias_Antiguedad"].median() if len(d) else 0
    pct_30 = (d["Dias_Antiguedad"] > 30).mean() * 100 if len(d) else 0
    pct_pend = (d["Archivo_Origen"] == "Pendientes por Autorizar").mean() * 100 if len(d) else 0
    n_anuladas = (d["Archivo_Origen"] == ORIGEN_ANULADAS).sum()
    marcadas = d[d["Anulada_Despues"] == MARCA_ANULADA["si"]]

    kpis = [
        kpi("Solicitudes", fmt_num(n_sol), f"Incluye {fmt_num(n_anuladas)} autorizaciones anuladas"),
        kpi("Afiliados", fmt_num(n_afi),
            f"{fmt_num((d['Poblacion'] == 'SIN DATO').sum())} registros sin dato de afiliado"),
        kpi("Tecnologías", fmt_num(len(d)), f"{pct_pend:.0f}% pendientes por autorizar"),
        kpi("Valor total", fmt_pesos(valor), f"Valor × cantidad · {fmt_num(sin_valor)} sin valor"),
        kpi("Antigüedad mediana", f"{0 if pd.isna(mediana) else mediana:.0f} días", "Al corte 20/08/2026"),
        kpi("Más de 30 días", f"{pct_30:.1f}%".replace(".", ","), "De los registros filtrados", alerta=True),
        kpi("No prestadas anuladas", fmt_num(len(marcadas)),
            f"{fmt_pesos(marcadas['Valor_Total'].sum())} aún sumando en el valor", alerta=True),
    ]
    return (
        kpis,
        fig_tendencia(d, metrica),
        fig_antiguedad(d, metrica),
        fig_grupo(d, metrica),
        fig_cohortes(d, metrica),
        fig_barras(d, "Region_Afiliado", metrica, height=340),
        fig_barras(d, "Razon_Social_Prestador_Solicita", metrica, top=10, height=340, max_chars=45),
        fig_tecnologias(d, metrica),
        fig_edad_genero(d),
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
    pag["Fecha_Nacimiento_Afiliado"] = pag["Fecha_Nacimiento_Afiliado"].astype(str)
    for col in ("Valor_Contratado", "Valor_Total"):
        pag[col] = pag[col].map(
        lambda v: "" if pd.isna(v) else fmt_pesos(v) if v < 1e6 else "$" + fmt_num(v))
    pag = pag.astype(object).where(pag.notna(), "")
    registros = pag.to_dict("records")
    tooltips = [{c: {"value": str(r[c]), "type": "text"} for c in
                 ("Desc_Tecnologia", "Nombre_Diagnostico_Principal", "Razon_Social_Prestador_Solicita",
                  "Direccion_Residencia")} for r in registros]
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
    return dcc.send_data_frame(d.to_csv, "autorizaciones_filtrado.csv", sep=";",
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
    d = DF if not regiones else DF[DF["Region_Afiliado"].isin(regiones)]
    return opciones(d["Municipio_Afiliado"].astype(str))
