"""Carga y preparación de las bases del tablero (Autorizaciones, PQR, Tutelas, Total)."""
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
# Base única y verídica de autorizaciones: pendientes + no prestadas + anuladas, adultos y menores.
CSV_AUT = (BASE_DIR.parent / "2. Creados" /
           "08202026_Consolidado_Autorizaciones_Adultos_Menores_Anuladas.csv")


def _mas_reciente(patron: str) -> Path:
    """Archivo más reciente que cumpla el patrón (tolera copias tipo 'archivo (1).xlsx')."""
    candidatos = sorted((BASE_DIR.parent / "2. Creados").glob(patron), key=lambda f: f.stat().st_mtime)
    if not candidatos:
        raise FileNotFoundError(f"No se encontró ningún archivo '{patron}' en '2. Creados'")
    return candidatos[-1]


XLSX_PQ = _mas_reciente("*PQ_CRUCEV2_CON_DX_PATOLOGIA_DX_Ac*.xlsx")
XLSX_TUT = BASE_DIR.parent / "2. Creados" / "Tutelasv2_CON_DX_PATOLOGIA_DX_Ac.xlsx"
CACHE_DIR = BASE_DIR / ".cache"
FECHA_CORTE = pd.Timestamp("2026-08-20")

EDAD_BINS = [0, 29, 39, 49, 59, 69, 79, 200]
EDAD_LABELS = ["<30", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"]
ANTIG_BINS = [-1, 7, 15, 30, 60, 90, 180, 365, 100000]
ANTIG_LABELS = ["0-7", "8-15", "16-30", "31-60", "61-90", "91-180", "181-365", ">365"]

CATEGORICAS = [
    "Grupo", "Archivo_Origen", "Estado", "Regimen_Afiliacion", "Estado_Afiliacion",
    "Region_Afiliado", "Municipio_Afiliado", "Genero", "Tipo_Tecnologia",
    "Cobertura_Tecnologia", "Razon_Social_Prestador_Solicita", "Tipo_Cruce_Valor",
    "Medio", "Grupo_Tecnologia", "Nombre_Origen_Atencion", "Servicio_solicitado", "Cohorte",
    "Anulada_Despues", "Tecnologia", "Poblacion", "Fuente_Datos_Afiliado",
]
ORIGEN_ANULADAS = "Anuladas"
MARCA_ANULADA = {"si": "Sí, figura anulada", "no": "No", "na": "No aplica"}
SEP_COHORTE = r"\s*\|\s*"  # un registro puede tener varias cohortes: "A | B"


def _preparar(df: pd.DataFrame) -> pd.DataFrame:
    # Valor_Contratado = valor unitario; Valor_Total = unitario × cantidad (el que se suma).
    for c in ("Valor_Contratado", "Valor_Total", "Cantidad"):
        df[c] = pd.to_numeric(df[c].str.replace(",", ".", regex=False), errors="coerce")

    # Las anuladas no traen número de solicitud: cada autorización anulada es un caso propio.
    sin_sol = df["Numero_Solicitud"].isna() & (df["Archivo_Origen"] == ORIGEN_ANULADAS)
    df.loc[sin_sol, "Numero_Solicitud"] = "AUT-" + df.loc[sin_sol, "Numero_Autorizacion"].astype(str)

    f_sol = pd.to_datetime(df["Fecha_Solicitud"], format="%d/%m/%Y", errors="coerce")
    f_ord = pd.to_datetime(df["Fecha_Orden_Medica"], format="%d/%m/%Y", errors="coerce")
    f_aut = pd.to_datetime(df["Fecha_Autorizacion"], format="%d/%m/%Y", errors="coerce")
    # Pendientes: Fecha_Solicitud; Autorizadas No Prestadas: Fecha_Orden_Medica;
    # Anuladas: Fecha_Autorizacion.
    df["Fecha_Referencia"] = f_sol.fillna(f_ord).fillna(f_aut)
    df["Dias_Antiguedad"] = (FECHA_CORTE - df["Fecha_Referencia"]).dt.days
    df["Rango_Antiguedad"] = pd.cut(df["Dias_Antiguedad"], ANTIG_BINS, labels=ANTIG_LABELS)

    nac = pd.to_datetime(df["Fecha_Nacimiento_Afiliado"], format="%d/%m/%Y", errors="coerce")
    df["Edad"] = ((FECHA_CORTE - nac).dt.days // 365.25).astype("Int64")
    df["Rango_Edad"] = pd.cut(df["Edad"].astype(float), EDAD_BINS, labels=EDAD_LABELS)
    df["Tecnologia"] = df["Cod_Tecnologia"].astype(str) + " · " + df["Desc_Tecnologia"].astype(str)

    # Autorizadas No Prestadas cuyo número de autorización figura en la base de anuladas.
    num_aut = df["Numero_Autorizacion"].astype(str).str.strip()
    anuladas = set(num_aut[df["Archivo_Origen"] == ORIGEN_ANULADAS])
    no_prest = df["Archivo_Origen"] == "Autorizadas No Prestadas"
    df["Anulada_Despues"] = np.select(
        [no_prest & num_aut.isin(anuladas), no_prest],
        [MARCA_ANULADA["si"], MARCA_ANULADA["no"]], MARCA_ANULADA["na"])

    for c in CATEGORICAS:
        df[c] = df[c].fillna("Sin información").astype("category")
    # ~1 M de filas: las columnas de texto repetitivo pasan a category para ahorrar memoria.
    for c in df.columns[df.dtypes == object]:
        if df[c].nunique() < len(df) * 0.05:
            df[c] = df[c].astype("category")
    return df


COLS_COHORTE = ["Cohorte_F", "alto_costo_Numero_Documento", "AltoC_Estado_Afiliacion", "AltoC_CIE10"]


def _colapsar_cohortes(df: pd.DataFrame) -> pd.DataFrame:
    """Un afiliado con varias cohortes llega repetido (una fila por cohorte).

    Se deja una fila por registro y las cohortes (y datos de alto costo) unidas con " | ",
    igual que la columna Cohorte de Autorizaciones. Así no se inflan servicios ni valor.
    """
    extra = [c for c in COLS_COHORTE if c in df.columns]
    if not extra:
        return df
    base = [c for c in df.columns if c not in extra]
    unir = lambda s: " | ".join(sorted(set(s.dropna().astype(str)))) or np.nan  # noqa: E731
    out = df.groupby(base, dropna=False, sort=False, as_index=False)[extra].agg(unir)
    out = out[df.columns]
    out["Cohorte"] = out["Cohorte_F"].fillna("SIN COHORTE") if "Cohorte_F" in out else "SIN COHORTE"
    return out


def _con_cache(nombre: str, fuente: Path, leer, depende_codigo=True) -> pd.DataFrame:
    """Devuelve la caché en pickle si ni la fuente ni (opcionalmente) este archivo han cambiado."""
    CACHE_DIR.mkdir(exist_ok=True)
    cache = CACHE_DIR / f"{nombre}.pkl"
    fuente_mtime = fuente.stat().st_mtime
    if depende_codigo:
        fuente_mtime = max(fuente_mtime, Path(__file__).stat().st_mtime)
    if cache.exists() and cache.stat().st_mtime > fuente_mtime:
        return pd.read_pickle(cache)
    df = leer()
    df.to_pickle(cache)
    return df


def cargar_autorizaciones() -> pd.DataFrame:
    """Consolidado único: pendientes + no prestadas + anuladas; adultos, menores y sin dato."""
    return _con_cache("autorizaciones", CSV_AUT, lambda: _preparar(
        pd.read_csv(CSV_AUT, sep=";", encoding="utf-8-sig", dtype=str, low_memory=False)))


# ------------------------------------------------------------------ PQR
FECHA_CORTE_PQ = pd.Timestamp("2026-09-01")
_EPOCH_EXCEL = pd.Timestamp("1899-12-30")
IDENT_LABELS = ["Con código y con valor", "Con código sin valor", "Sin código de servicio"]
CATEGORICAS_PQ = [
    "tipo_solicitud", "origen_pqrd", "ente_control", "estado_caso", "clasificacion_de_riesgo",
    "oportunidad_respuesta", "oportunidad_respuesta_prestador", "motivo_especifico",
    "tipo_motivo_especifico", "estado_servicio", "motivo_de_respuesta", "region_afiliacion",
    "mpio_afiliacion", "regimen_afiliacion", "sexo_afectado", "DX_Grupo_PATOLOGIAS", "Capítulo",
    "IPS_responsable_respuesta", "responsable_caso", "medicamento", "ambito_servicio",
    "estado_afiliacion", "Zona_Residencia", "discapacidad_afectado", "grupo_poblacional",
    "especialidad", "servicio_atribuido_ips", "Identificacion",
]


def _fecha_excel(serie: pd.Series) -> pd.Series:
    """Las fechas vienen como días desde 1899-12-30 en texto ('46248 days, 14:16:17')."""
    return _EPOCH_EXCEL + pd.to_timedelta(serie, errors="coerce")


def _preparar_pq(df: pd.DataFrame) -> pd.DataFrame:
    # Filas idénticas en todas las columnas son duplicados del cruce de origen, no servicios nuevos.
    df = _colapsar_cohortes(df.drop_duplicates(ignore_index=True)).copy()
    # 5_valor_contratado = valor contratado cuando existe, si no el p75 (columna final del cruce).
    df["Valor"] = pd.to_numeric(df["5_valor_contratado"], errors="coerce")
    # Misma segmentación de la tabla "PQRS con Valor Contratado" (Tableau).
    con_cod = df["codigo_servicio_pqrd"].notna()
    df["Identificacion"] = np.select(
        [con_cod & df["Valor"].notna(), con_cod],
        [IDENT_LABELS[0], IDENT_LABELS[1]], IDENT_LABELS[2])

    fechas = [c for c in df.columns if c.startswith("fecha_") and c != "fecha_nacimiento_afectado"]
    for c in fechas:
        df[c] = _fecha_excel(df[c])
    df["Fecha_Creacion"] = df["fecha_creacion_caso"].fillna(df["fecha_cargue_sistema"]).dt.normalize()
    fin = df["fecha_cierre_caso"].fillna(FECHA_CORTE_PQ)
    df["Dias_Gestion"] = (fin - df["Fecha_Creacion"]).dt.days.clip(lower=0)
    df["Rango_Dias"] = pd.cut(df["Dias_Gestion"], ANTIG_BINS, labels=ANTIG_LABELS)
    for c in fechas:  # legible en la tabla
        df[c] = df[c].dt.strftime("%d/%m/%Y %H:%M")
    df["fecha_nacimiento_afectado"] = pd.to_datetime(
        df["fecha_nacimiento_afectado"], errors="coerce").dt.strftime("%d/%m/%Y")

    df["Edad"] = pd.to_numeric(df["edad_calculada"], errors="coerce").astype("Int64")
    df["Rango_Edad"] = pd.cut(df["Edad"].astype(float), [-1] + EDAD_BINS[1:], labels=EDAD_LABELS)
    for c in ("region_afiliacion", "mpio_afiliacion"):  # vienen con mayúsculas mezcladas
        df[c] = df[c].str.strip().str.upper()
    df["sexo_afectado"] = df["sexo_afectado"].map({"F": "Femenino", "M": "Masculino"})

    for c in CATEGORICAS_PQ:
        df[c] = df[c].fillna("Sin información").astype("category")
    return df


def cargar_pq() -> pd.DataFrame:
    """Lee el Excel de PQR (~30 s la primera vez; luego usa la caché)."""
    return _con_cache("pq", XLSX_PQ, lambda: _preparar_pq(pd.read_excel(XLSX_PQ, dtype=str)))


def mascaras_cohorte(df: pd.DataFrame, col: str = "Cohorte") -> dict[str, np.ndarray]:
    """Una máscara booleana por cohorte individual (un registro puede estar en varias)."""
    partes = df[col].astype(str).str.split(SEP_COHORTE, regex=True).explode().str.strip()
    cohortes = partes.value_counts().index
    return {c: df.index.isin(partes.index[partes == c]) for c in cohortes}


def opciones(serie: pd.Series) -> list[dict]:
    vals = serie.dropna().unique()
    return [{"label": str(v), "value": str(v)} for v in sorted(vals, key=str)]


def fmt_num(n) -> str:
    return f"{n:,.0f}".replace(",", ".")


def fmt_pesos(n) -> str:
    if n is None or (isinstance(n, float) and np.isnan(n)):
        return "$0"
    if abs(n) >= 1e9:
        return "$" + fmt_num(n / 1e6) + " M"
    if abs(n) >= 1e6:
        return f"${n / 1e6:,.1f} M".replace(",", "X").replace(".", ",").replace("X", ".")
    return "$" + fmt_num(n)


# ------------------------------------------------------------------ Tutelas
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
CATEGORICAS_TUT = [
    "clasificacion edad", "Año de Fecha notificacion", "Tipo servicio", "Tipo tecnologia",
    "Grupo_PATOLOGIA", "Capítulo", "BDT Municipio Afiliado", "AltoC_Estado_Afiliacion",
    "Ips destino", "Ips prescriptora", "Clasificación crónica (archivo previo)", "Identificacion",
]


def _preparar_tut(df: pd.DataFrame) -> pd.DataFrame:
    df = _colapsar_cohortes(df).copy()
    # Valor_Total = 5_valor_contratado × Cantidad (valor real de lo ordenado).
    df["Valor"] = pd.to_numeric(df["Valor_Total"], errors="coerce")
    con_cod = df["Servicio"].notna()
    df["Identificacion"] = np.select(
        [con_cod & df["Valor"].notna(), con_cod],
        [IDENT_LABELS[0], IDENT_LABELS[1]], IDENT_LABELS[2])

    # Solo hay año y mes de notificación: se usa el primer día del mes.
    mes = df["Mes de Fecha notificacion"].str.strip().str.lower().map(
        {m: i + 1 for i, m in enumerate(MESES)})
    df["Fecha_Notificacion"] = pd.to_datetime(
        dict(year=pd.to_numeric(df["Año de Fecha notificacion"], errors="coerce"), month=mes, day=1),
        errors="coerce")
    df["Mes de Fecha notificacion"] = pd.Categorical(
        df["Mes de Fecha notificacion"].str.strip().str.lower(), categories=MESES, ordered=True)

    df["Edad"] = pd.to_numeric(df["EDAD"], errors="coerce").astype("Int64")
    df["BDT Municipio Afiliado"] = df["BDT Municipio Afiliado"].str.strip().str.upper()
    for c in CATEGORICAS_TUT:
        df[c] = df[c].fillna("Sin información").astype("category")
    return df


def cargar_tutelas() -> pd.DataFrame:
    """Lee el Excel de Tutelas (~15 s la primera vez; luego usa la caché)."""
    return _con_cache("tutelas", XLSX_TUT, lambda: _preparar_tut(pd.read_excel(XLSX_TUT, dtype=str)))


# ------------------------------------------------------------------ Consolidado
FUENTES = ["Autorizaciones", "PQR", "Tutelas", "Medicamentos"]


def _norm(serie: pd.Series) -> pd.Series:
    """Normaliza documentos y códigos para cruzar bases (sin espacios ni ceros a la izquierda)."""
    s = serie.astype("string").str.strip().str.upper().str.lstrip("0")
    return s.mask(s.isin(["", "NAN", "NONE"]))


def cargar_consolidado() -> pd.DataFrame:
    """Une las 4 bases en un formato común: una fila por registro con su valor.

    Cruce = mismo documento + mismo código de servicio en más de una base.
    """
    from data_medicamentos import cargar_medicamentos  # import local: módulo aparte con caché propia

    a, p, t = cargar_autorizaciones(), cargar_pq(), cargar_tutelas()  # Autorizaciones incluye anuladas
    m = cargar_medicamentos()
    partes = [
        pd.DataFrame({
            "Fuente": "Autorizaciones", "Id_Caso": "A-" + a["Numero_Solicitud"].astype(str),
            "Documento": _norm(a["Documento_Afiliado"]), "Codigo": _norm(a["Cod_Tecnologia"]),
            "Descripcion": a["Desc_Tecnologia"], "Valor": a["Valor_Total"],
            "Grupo": a["Grupo"].astype(str), "Municipio": a["Municipio_Afiliado"].astype(str),
            "Cohorte": a["Cohorte"].astype(str), "Anulada": a["Archivo_Origen"] == ORIGEN_ANULADAS,
        }),
        pd.DataFrame({
            "Fuente": "PQR", "Id_Caso": "P-" + p["numero_solicitud_pqrsf"].astype(str),
            "Documento": _norm(p["identificacion_afectado"]), "Codigo": _norm(p["codigo_servicio_pqrd"]),
            "Descripcion": p["descripcion_servicio_pqrd"], "Valor": p["Valor"],
            "Grupo": p["DX_Grupo_PATOLOGIAS"].astype(str), "Municipio": p["mpio_afiliacion"].astype(str),
            "Cohorte": p["Cohorte"].astype(str), "Anulada": False,
        }),
        pd.DataFrame({
            "Fuente": "Tutelas", "Id_Caso": "T-" + t["BDT Num Tutela"].astype(str),
            "Documento": _norm(t["BDT Identificacion"]), "Codigo": _norm(t["servicio_corregidos"]),
            "Descripcion": t["Descripcion servicio"], "Valor": t["Valor"],
            "Grupo": t["Grupo_PATOLOGIA"].astype(str), "Municipio": t["BDT Municipio Afiliado"].astype(str),
            "Cohorte": t["Cohorte"].astype(str), "Anulada": False,
        }),
        pd.DataFrame({  # faltantes de medicamentos: caso = fórmula; código = CUM (cruza con PQR/Tutelas)
            "Fuente": "Medicamentos",
            "Id_Caso": "M-" + m["Gestor"].astype(str) + "-"
                       + m["Consecutivo_Formula"].fillna(m["Numero_Formula"]).astype(str),
            "Documento": _norm(m["Documento_Afiliado"]), "Codigo": _norm(m["Codigo_CUM"]),
            "Descripcion": m["Nombre_Medicamento"].astype(str), "Valor": m["Valor_Faltante_Estimado"],
            "Grupo": "Sin información", "Municipio": m["Municipio_Afiliado"].astype(str),
            "Cohorte": "Sin información", "Anulada": False,
        }),
    ]
    df = pd.concat(partes, ignore_index=True)
    df["Municipio"] = (df["Municipio"].str.strip().str.upper()
                       .str.normalize("NFKD").str.encode("ascii", "ignore").str.decode("ascii"))

    # Bases en las que aparece cada afiliado y cada afiliado+servicio.
    df["N_Bases_Afiliado"] = df.groupby("Documento")["Fuente"].transform("nunique")
    clave = df["Documento"] + "|" + df["Codigo"]
    df["Clave"] = clave
    n_bases = df[clave.notna()].groupby("Clave")["Fuente"].nunique()
    df["N_Bases_Servicio"] = clave.map(n_bases).fillna(1).astype(int)
    df["En_Cruce"] = df["N_Bases_Servicio"] > 1
    df["Fuente"] = pd.Categorical(df["Fuente"], categories=FUENTES)
    for c in ("Grupo", "Municipio", "Cohorte", "Id_Caso"):
        df[c] = df[c].astype("category")
    return df


def valor_duplicado(d: pd.DataFrame) -> float:
    """Valor que sobra si cada afiliado+servicio en cruce se contara una sola vez.

    Para cada clave en varias bases: suma de las bases − el mayor valor entre bases.
    """
    c = d[d["En_Cruce"] & d["Valor"].notna()]
    if c.empty:
        return 0.0
    por_base = c.groupby(["Clave", "Fuente"], observed=True)["Valor"].sum()
    por_clave = por_base.groupby(level=0).agg(["sum", "max"])
    return float((por_clave["sum"] - por_clave["max"]).sum())
