"""Componentes reutilizables (tema de gráficos, tarjetas, filtros) para todas las páginas."""
import plotly.graph_objects as go
from dash import dash_table, dcc, html

VERDE = "#00A499"
AZUL = "#1D4E59"
TEXTO_2 = "#8899A6"
GRID = "#EEF2F3"
FUENTE = '"Segoe UI", -apple-system, Roboto, Arial, sans-serif'

GRAPH_CONFIG = {"displaylogo": False, "responsive": True,
                "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
                "locale": "es"}


def layout_base(fig: go.Figure, height=300, **kw) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=16, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FUENTE, size=11, color=AZUL),
        separators=",.",
        hoverlabel=dict(bgcolor="#fff", bordercolor="#E0E0E0", font=dict(family=FUENTE, color=AZUL)),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0,
                    font=dict(size=11), title=None),
        bargap=0.25,
        **kw,
    )
    fig.update_xaxes(showgrid=False, linecolor="#D5DDE0", tickfont=dict(color=TEXTO_2), title=None)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickfont=dict(color=TEXTO_2), title=None)
    return fig


def barras_h(etiquetas, valores, texto_valor, hover_fmt, height=300, max_chars=45, hover_labels=None,
             hover_extra=None, espacio_texto=None):
    """Barras horizontales de una sola serie, mayor arriba.

    `hover_extra`: texto adicional por barra para el tooltip; `espacio_texto`: factor sobre el
    máximo del eje x para dejar lugar a etiquetas largas a la derecha de las barras.
    """
    # Categorías únicas por posición; el texto recortado va solo en ticktext para no fusionar barras.
    corto = [e if len(e) <= max_chars else e[:max_chars - 1] + "…" for e in etiquetas]
    pos = list(range(len(etiquetas)))
    fig = go.Figure(go.Bar(
        y=pos, x=valores, orientation="h", marker=dict(color=VERDE, cornerradius=4),
        text=texto_valor, textposition="outside", cliponaxis=False,
        textfont=dict(color=AZUL, size=10.5),
        customdata=list(zip(hover_labels or etiquetas, hover_extra or [""] * len(etiquetas))),
        hovertemplate="<b>%{customdata[0]}</b><br>" + hover_fmt + "%{customdata[1]}<extra></extra>",
    ))
    layout_base(fig, height=height)
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)", tickfont=dict(color=AZUL, size=10.5),
                     tickmode="array", tickvals=pos, ticktext=corto, automargin=True)
    fig.update_xaxes(showticklabels=False, showline=False)
    if espacio_texto and len(valores):
        fig.update_xaxes(range=[0, max(valores) * espacio_texto])
    fig.update_layout(margin=dict(l=8, r=60, t=4, b=4))
    return fig


def figura_vacia(msg="Sin datos para los filtros seleccionados", height=300):
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font=dict(color=TEXTO_2, size=13))
    layout_base(fig, height=height)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


def card_grafico(titulo, graph_id, sub=None, className="card"):
    return html.Div(className=className, children=[
        html.Div(titulo, className="card-titulo"),
        html.Div(sub, className="card-sub") if sub else None,
        dcc.Loading(dcc.Graph(id=graph_id, config=GRAPH_CONFIG), color=VERDE, type="dot"),
    ])


def kpi(label, valor, nota=None, alerta=False):
    return html.Div(className="card kpi" + (" kpi-alerta" if alerta else ""), children=[
        html.Div(label, className="kpi-label"),
        html.Div(valor, className="kpi-valor"),
        html.Div(nota, className="kpi-nota") if nota else None,
    ])


def filtro_dropdown(label, id_, options, placeholder="Todos", ancho=False):
    return html.Div(className="filtro" + (" filtro-ancho" if ancho else ""), children=[
        html.Label(label),
        dcc.Dropdown(id=id_, options=options, multi=True, placeholder=placeholder,
                     optionHeight=30, maxHeight=320),
    ])


def tabla_detalle(id_, columnas, page_size=15):
    """DataTable con paginación y orden del lado del servidor (page_action/sort_action='custom')."""
    return dash_table.DataTable(
        id=id_,
        columns=[{"name": c.replace("_", " "), "id": c} for c in columnas],
        page_current=0, page_size=page_size, page_action="custom",
        sort_action="custom", sort_mode="single", sort_by=[],
        fixed_columns={"headers": True, "data": 1},
        style_table={"overflowX": "auto", "minWidth": "100%"},
        style_header={"backgroundColor": AZUL, "color": "#fff", "fontWeight": 600,
                      "fontSize": "11px", "border": "none", "whiteSpace": "normal",
                      "height": "auto", "padding": "6px 8px"},
        style_cell={"fontFamily": '"Segoe UI", Roboto, Arial, sans-serif', "fontSize": "11.5px",
                    "color": AZUL, "padding": "5px 8px", "border": "none",
                    "borderBottom": "1px solid #EEF2F3", "textAlign": "left",
                    "minWidth": "90px", "maxWidth": "260px", "overflow": "hidden", "textOverflow": "ellipsis",
                    "whiteSpace": "nowrap"},
        style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#F8FBFB"}],
        tooltip_delay=400, tooltip_duration=None,
    )


def abreviar_tecnologia(texto: str) -> str:
    """Acorta los prefijos largos de consultas para que la etiqueta muestre la especialidad."""
    return (texto.replace("CONSULTA DE PRIMERA VEZ POR ESPECIALISTA EN ", "1ª VEZ ")
            .replace("CONSULTA DE CONTROL O DE SEGUIMIENTO POR ESPECIALISTA EN ", "CONTROL ")
            .replace("CONSULTA DE PRIMERA VEZ POR ", "1ª VEZ "))


def tabla_por_cohorte(d, mascaras, medidas) -> "pd.DataFrame":
    """Una fila por cohorte con las medidas de `medidas(sub)` (dict); un registro puede sumar en varias."""
    import pandas as pd
    return pd.DataFrame({c: medidas(d[m[d.index]]) for c, m in mascaras.items()}).T.astype(float)


def etiqueta_cohorte(c):
    return c.capitalize().replace("Hiv", "HIV").replace("Hepatitis c", "Hepatitis C")


def fig_con_valor(t, metrica, hover_fmt, unidad, nombre_unidad, etiqueta=str, height=480):
    """Barras de la métrica con cantidad · valor total · valor promedio en etiqueta y tooltip.

    `t`: una fila por categoría con una columna por métrica y la columna 'val' (valor).
    El promedio es 'val' / `unidad` (p. ej. por solicitud, por PQ o por servicio).
    """
    t = t[t[metrica] > 0].sort_values(metrica, ascending=False)
    if t.empty:
        return figura_vacia(height=height)
    prom = (t["val"] / t[unidad]).replace([float("inf")], 0).fillna(0)
    textos, extras = [], []
    for (_, r), p in zip(t.iterrows(), prom):
        partes = [] if metrica == "val" else [_fmt_num(r[metrica])]
        textos.append(" · ".join(partes + [_fmt_pesos(r["val"]), f"prom. {_fmt_pesos(p)}"]))
        extras.append(f"<br>Valor total: ${_fmt_num(r['val'])}<br>Promedio por {nombre_unidad}: ${_fmt_num(p)}")
    nombres = [str(i) for i in t.index]
    return barras_h([etiqueta(n) for n in nombres], t[metrica].values, textos, hover_fmt,
                    height=height, max_chars=30, hover_labels=nombres, hover_extra=extras,
                    espacio_texto=2.3)


def _fmt_num(n):
    return f"{n:,.0f}".replace(",", ".")


def _fmt_pesos(n):
    from data import fmt_pesos
    return fmt_pesos(n)
