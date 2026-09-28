"""Faltantes de medicamentos de los gestores farmacéuticos (MEDIC, TODO DROGAS, COHAN) en una sola base.

Las tres hojas del Excel se llevan a las variables homologadas (tabla de homologación del equipo) y se
agregan columnas de apoyo: Gestor, Nombre/Código del medicamento, Motivo del faltante y Valor faltante estimado.
Módulo aparte de `data.py` para no invalidar las cachés de las otras bases.
"""
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
CACHE = BASE_DIR / ".cache" / "medicamentos.pkl"
HOJAS = ["MEDIC", "TODO DROGAS", "COHAN"]


def _archivo() -> Path:
    candidatos = sorted((BASE_DIR.parent / "2. Creados").glob("Faltantes gestores*.xlsx"),
                        key=lambda f: f.stat().st_mtime)
    if not candidatos:
        raise FileNotFoundError("No se encontró 'Faltantes gestores*.xlsx' en '2. Creados'")
    return candidatos[-1]


# Variable homologada: (MEDIC, TODO DROGAS, COHAN). None = la hoja no la trae.
HOMOLOGACION = {
    "Tipo_Documento": ("TipoDocumentoPaciente", "TipoDocumentoPaciente", "TIPO DOCUMENTO"),
    "Documento_Afiliado": ("DocumentoPaciente", "DocumentoPaciente", "DOCUMENTO AFILIADO"),
    "Nombre_Afiliado": ("NombresApellidosPaciente", "NombrePaciente", "NOMBRE FILIADO"),
    "Direccion_Afiliado": ("DireccionPaciente", "DireccionPaciente", "DIRECCION AFILIADO"),
    "Telefono_Afiliado": ("TelefonoPaciente", "TelefonoPaciente", "TELEFONO AFILIADO"),
    "Municipio_Afiliado": ("NombreMunicipio", "NombreMunicipio", "CIUDAD AFILIADO"),
    "Numero_Formula": ("NumeroFormula", "NumeroFormula", "NUMERO FORMULA"),
    "Consecutivo_Formula": ("ConsecutivoFormula", "ConsecutivoFormula", "CONSECUTIVO FORMULA"),
    "Tipo_Formula": ("TipoFormula", "TipoFormula", "TIPO FORMULA"),
    "Duracion_Tratamiento": ("DuracionTratamiento", "DuracionTratamiento", "DURACION TRATAMIENTO"),
    "Cantidad_Solicitada": ("CantidadSolicitada", "CantidadSolicitada", "CANTIDAD SOLICITADA"),
    "Cantidad_Entregada": ("CantidadEntregada", "CantidadEntregada", "CANTIDAD ENTREGADA_TOTAL"),
    "Cantidad_Pendiente": ("CantidadPendiente_RestaEntrega", "CantidadPendiente (resta de entrega)",
                           "CANTIDAD PENDIENTE"),
    "Cantidad_Faltante": ("CantidadFaltante_Pendiente", "CantidadFaltante (pendiente)", "CANTIDAD FALTANTE"),
    "Fecha_Formula": ("FechaFormula", "FechaFormula", "FECHA FORMULA"),
    "Fecha_Faltante": ("FechaFaltante", "FechaFaltante", "FECHA FALTANTE"),
    "Fecha_Entrega_Faltante": ("FechaEntregaFaltante", "FechaEntregaFaltante", "FECHA ENTREGA FALTANTE"),
    "Codigo_DCI": ("CodigoDCI", "CodigoDCI", "CODIGO DCI"),
    "Codigo_Bodega": ("CodigoBodega", "CodigoBodega", "CODIGO BODEGA"),
    "Nombre_Bodega": ("Bodega", "Bodega", "NOMBRE BODEGA"),
    "Codigo_Diagnostico": ("CodigoCIE10", "CodigoCIE10", "CODIGO CIE"),
    "Descripcion_Diagnostico": ("DescripcionCIE10", "DescripcionCIE10", "DESCRIPCION CIE"),
    "Descripcion_Contrato": ("DescripcionContrato", "DescripcionContrato", "DESCRIPCION CONTRATO"),
    "Valor_Unitario": ("ValorUnitarioMedicamentosDispensados", "ValorUnitarioMedicamentosDispensados", None),
    "Valor_Total": ("ValorTotalMedicamentosDispensados", "ValorTotalMedicamentosDispensados", None),
    # Apoyo (no están en la tabla de homologación, necesarias para el análisis)
    "Codigo_Medicamento": ("CodigoProducto", "CodigoProducto", "CODIGO STONE"),
    "Codigo_CUM": ("CodigoCUM", "CodigoCUM", None),  # permite cruzar con PQR/Tutelas en la página Total
    "Nombre_Medicamento": ("NombreProductoFaltante", "DescripcionMedicamentosDispensados", "NOMBRE PRODUCTO"),
    "Motivo_Faltante": (None, "Motivo faltante", "MOTIVO GENERACION"),
}
# Relleno cuando la columna homologada viene vacía en la hoja: (MEDIC, TODO DROGAS, COHAN)
RELLENO = {
    "Nombre_Bodega": ("PuntoVenta", "PuntoVenta", None),
    "Tipo_Formula": ("TipoAutorizacion", "TipoAutorizacion", None),
    "Nombre_Medicamento": ("DescripcionMedicamentosDispensados", None, None),
}
NUMERICAS = ["Duracion_Tratamiento", "Cantidad_Solicitada", "Cantidad_Entregada", "Cantidad_Pendiente",
             "Cantidad_Faltante", "Valor_Unitario", "Valor_Total"]
FECHAS = ["Fecha_Formula", "Fecha_Faltante", "Fecha_Entrega_Faltante"]
CATEGORICAS = ["Gestor", "Tipo_Documento", "Municipio_Afiliado", "Tipo_Formula", "Nombre_Bodega",
               "Descripcion_Contrato", "Motivo_Faltante", "Nombre_Medicamento", "Diagnostico", "Entregado",
               "Faltante_Corregido"]
DIAS_BINS = [-1, 7, 15, 30, 60, 90, 100000]
DIAS_LABELS = ["0-7", "8-15", "16-30", "31-60", "61-90", ">90"]


def _homologar(hojas: dict) -> pd.DataFrame:
    partes = []
    for i, gestor in enumerate(HOJAS):
        df = hojas[gestor]
        out = pd.DataFrame(index=df.index)
        for var, cols in HOMOLOGACION.items():
            col = cols[i]
            out[var] = df[col] if col in df.columns else np.nan
            relleno = RELLENO.get(var, (None,) * 3)[i]
            if relleno in df.columns:
                out[var] = out[var].fillna(df[relleno])
        out.insert(0, "Gestor", gestor)
        partes.append(out)
    return pd.concat(partes, ignore_index=True)


def _preparar(df: pd.DataFrame) -> pd.DataFrame:
    for c in NUMERICAS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in FECHAS:  # textos como "/ /" o "FALTANTE SIN ENTREGAR" quedan vacíos
        df[c] = pd.to_datetime(df[c], errors="coerce", format="mixed")
    df["Entregado"] = np.where(df["Fecha_Entrega_Faltante"].notna(), "Entregado", "Sin entregar")
    # Error de origen (MEDIC): en algunas filas el faltante viene como solicitada × entregada y supera lo
    # solicitado. Se corrige a solicitada − entregada (mín. 0) y se deja trazabilidad.
    df["Cantidad_Faltante_Original"] = df["Cantidad_Faltante"]
    inconsistente = df["Cantidad_Faltante"] > df["Cantidad_Solicitada"]
    df.loc[inconsistente, "Cantidad_Faltante"] = (
        df.loc[inconsistente, "Cantidad_Solicitada"] - df.loc[inconsistente, "Cantidad_Entregada"]).clip(lower=0)
    df["Faltante_Corregido"] = np.where(inconsistente, "Sí", "No")
    # El valor total de las hojas es lo dispensado (≈0 en faltantes): se estima el valor de lo que falta.
    df["Valor_Faltante_Estimado"] = df["Valor_Unitario"] * df["Cantidad_Faltante"]
    corte = df["Fecha_Faltante"].max()
    df["Dias_Faltante"] = (corte - df["Fecha_Faltante"]).dt.days
    df["Rango_Dias"] = pd.cut(df["Dias_Faltante"], DIAS_BINS, labels=DIAS_LABELS)
    df["Documento_Afiliado"] = df["Documento_Afiliado"].astype("string").str.strip()
    df["Municipio_Afiliado"] = (df["Municipio_Afiliado"].astype("string").str.strip().str.upper()
                                .str.normalize("NFKD").str.encode("ascii", "ignore").str.decode("ascii"))
    df["Nombre_Bodega"] = df["Nombre_Bodega"].astype("string").str.strip()
    df["Nombre_Medicamento"] = df["Nombre_Medicamento"].astype("string").str.strip().str.upper()
    df["Tipo_Formula"] = df["Tipo_Formula"].astype("string").str.strip().str.upper().replace(
        {"FORMULACIÓN": "FORMULACION", "FORMULA": "FORMULACION"})
    df["Diagnostico"] = (df["Codigo_Diagnostico"].astype("string").str.strip() + " · "
                         + df["Descripcion_Diagnostico"].astype("string").str.strip().str.upper())
    for c in CATEGORICAS:
        df[c] = df[c].astype("string").fillna("Sin información").astype("category")
    return df


def cargar_medicamentos() -> pd.DataFrame:
    """Lee el Excel (o la caché si ni el Excel ni este archivo cambiaron)."""
    fuente = _archivo()
    mtime = max(fuente.stat().st_mtime, Path(__file__).stat().st_mtime)
    if CACHE.exists() and CACHE.stat().st_mtime > mtime:
        return pd.read_pickle(CACHE)
    hojas = pd.read_excel(fuente, sheet_name=HOJAS, dtype=str)
    df = _preparar(_homologar(hojas))
    CACHE.parent.mkdir(exist_ok=True)
    df.to_pickle(CACHE)
    return df
