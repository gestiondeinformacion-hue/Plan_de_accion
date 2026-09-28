"""Tablero Savia Salud - Cruce Adultos 08/2026.

Ejecutar:  python3 app.py   ->  http://127.0.0.1:8050  (red local: http://<IP>:8050)
"""
import dash
from dash import Dash, Input, Output, dcc, html

app = Dash(__name__, use_pages=True, title="Tablero Adultos | Savia Salud",
           suppress_callback_exceptions=True)

NAV = [
    ("/", "Autorizaciones", "▣"),
    ("/pqr", "PQR", "✉"),
    ("/tutelas", "Tutelas", "⚖"),
    ("/medicamentos", "Medicamentos", "℞"),
    ("/total", "Total", "Σ"),
]


def sidebar():
    return html.Aside(className="sidebar", children=[
        html.Div(className="logo", children=[
            html.Span("savia", className="logo-savia"),
            html.Span("SALUD EPS", className="logo-sub"),
        ]),
        html.Div("Tableros", className="nav-titulo"),
        html.Nav(id="nav", children=[
            dcc.Link([html.Span(ico, className="nav-ico"), nombre],
                     href=href, className="nav-link", id=f"nav-{nombre}")
            for href, nombre, ico in NAV
        ]),
        html.Div(className="sidebar-pie", children=[
            "Cruce Adultos 2026", html.Br(),
            "Equipo de Datos y BI",
        ]),
    ])


app.layout = html.Div(className="app", children=[
    dcc.Location(id="url"),
    sidebar(),
    html.Main(dash.page_container, className="main"),
])


@app.callback(
    [Output(f"nav-{nombre}", "className") for _, nombre, _ in NAV],
    Input("url", "pathname"),
)
def marcar_activo(path):
    return ["nav-link activo" if path == href else "nav-link" for href, _, _ in NAV]


if __name__ == "__main__":
    # host 0.0.0.0: accesible desde otros equipos de la misma red (http://<IP-de-este-equipo>:8050)
    app.run(debug=False, port=8050, host="0.0.0.0")
