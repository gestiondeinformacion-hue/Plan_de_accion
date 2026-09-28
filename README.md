# Tablero Adultos · Savia Salud

Tablero en Dash con el estándar de diseño Savia Salud.

## Ejecutar
```bash
cd "4. Tablero"
python3 app.py
```
Abrir http://127.0.0.1:8050 (en este equipo) o http://<IP-de-este-equipo>:8050 desde otro equipo de la misma red (`ipconfig getifaddr en0`).

La primera carga lee las bases (~3 s el CSV, ~30 s el Excel de PQR) y deja una caché en `.cache/`. Se regenera sola si cambia el CSV o `data.py`.

## Estructura
- `app.py`: layout general (menú lateral y navegación).
- `data.py`: carga (CSV `..._con_Grupo_Valor_y_Cohorte.csv`) y columnas derivadas (Fecha_Referencia, Dias_Antiguedad, Edad, rangos, máscaras por cohorte).
- `componentes.py`: tema de gráficos, tarjetas KPI y filtros reutilizables.
- `assets/style.css`: colores y estilos Savia.
- `pages/autorizaciones.py`: página de Autorizaciones.
- `pages/pqr.py`: página de PQR (el Excel más reciente `PQ_CRUCEV2_CON_DX_PATOLOGIA_DX_Ac*.xlsx`, se eliminan filas duplicadas exactas; la primera carga tarda ~30 s).
- `pages/total.py`: consolidado de las 3 bases con desviación ajustable (±15 % por defecto).
- `pages/tutelas.py`: página de Tutelas (Excel `Tutelasv2_CON_DX_PATOLOGIA_DX_Ac.xlsx`; ~18 s la primera carga).

## Notas de datos
- **Fecha de referencia**: Pendientes → `Fecha_Solicitud`; Autorizadas No Prestadas → `Fecha_Orden_Medica` (no traen fecha de solicitud).
- **Antigüedad**: días desde la fecha de referencia hasta el corte 20/08/2026.
- **Solicitudes** = `Numero_Solicitud` únicos; **Tecnologías** = filas (solicitud × CUPS); **Afiliados** = `Documento_Afiliado` únicos.
- **Cohorte**: un registro puede tener varias cohortes (`A | B`). El filtro trae registros que tengan *alguna* de las seleccionadas y el gráfico cuenta el registro en cada cohorte (la suma de barras puede superar el total).

### PQR
- Medidas iguales a Tableau: **PQ únicas** = `numero_solicitud_pqrsf` distintos; **Servicios identificados** = conteo de `codigo_servicio_pqrd` no vacío; **Valor** = suma de `5_valor_contratado`.
- **Identificación**: con código y con valor / con código sin valor / sin código de servicio.
- Fechas vienen como serial de Excel y se convierten. **Días de gestión** = creación → cierre (o → 01/09/2026 si el caso sigue abierto).
- `region_afiliacion` y `mpio_afiliacion` se normalizan a mayúsculas (venían mezcladas).

### Tutelas
- **Tutelas únicas** = `BDT Num Tutela` distintos; **Servicios identificados** = conteo de `Servicio` no vacío; **Valor total** = suma de `Valor_Total` (= `5_valor_contratado` × `Cantidad`).
- Solo hay año y mes de notificación: la tendencia es mensual.
- Incluye menores de edad; se separan con el filtro "Clasificación edad".
- El top de servicios excluye el código 101010101 (NO APLICA).
- `BDT Num Radicado` viene del Excel en notación científica (5.0014e+21): se perdieron dígitos en el origen.

### Total
- **Valor total** = Autorizaciones (`Valor_Contratado`) + PQR (`5_valor_contratado`) + Tutelas (`Valor_Total`).
- **Desviación**: control deslizante (0–50 %, por defecto 15 %). Mínimo = total × (1 − %), máximo = total × (1 + %).
- **Cruce**: mismo documento y mismo código de servicio en más de una base (documentos y códigos sin ceros a la izquierda).
- **Valor repetido**: para cada afiliado+servicio en cruce, suma de las bases − el mayor valor entre bases (lo que sobraría si se contara una sola vez).

### Autorizaciones (fuente única)
- Única fuente: `2. Creados/08202026_Consolidado_Autorizaciones_Adultos_Menores_Anuladas.csv` (pendientes + no prestadas + anuladas; población Adultos / Menores / SIN DATO). Ya no se usan los CSV/Excel anteriores de autorizaciones ni de anuladas.
- **Valor** = `Valor_Total` (= `Valor_Contratado` unitario × `Cantidad`).
- Anuladas sin número de solicitud: cada autorización anulada cuenta como un caso (`AUT-<número>`). Las que no traen afiliado quedan con población "SIN DATO".
- **No prestada anulada**: Autorizadas No Prestadas cuyo `Numero_Autorizacion` también figura como anulada. Se marcan (filtro + KPI) y siguen sumando en el valor.
- La página Total incluye las anuladas dentro de Autorizaciones.

### Cohortes en PQR y Tutelas
- `Cohorte_F` llega con una fila por cohorte (duplica servicios y valor). Se colapsa a una fila por registro con las cohortes unidas por " | " (columna `Cohorte`), igual que Autorizaciones.

### Medicamentos (faltantes de gestores farmacéuticos)
- Fuente: el `2. Creados/Faltantes gestores*.xlsx` más reciente, hojas MEDIC, TODO DROGAS y COHAN (se ignora `Hoja1`). Carga en `data_medicamentos.py` (caché propia `.cache/medicamentos.pkl`).
- Se unen con la tabla de variables homologadas (`HOMOLOGACION`) + columnas de apoyo: Gestor, Código/Nombre del medicamento, Motivo del faltante.
- Rellenos: Bodega vacía → `PuntoVenta`; Tipo fórmula vacío (MEDIC/TODO DROGAS) → `TipoAutorizacion`.
- **Valor faltante estimado** = `Valor_Unitario` × `Cantidad_Faltante` (el `Valor_Total` de las hojas es lo dispensado, ≈0 en faltantes). COHAN no trae valores.
- **Corrección de origen:** 317 filas de MEDIC traen el faltante como solicitada × entregada (> solicitada); se corrige a solicitada − entregada (mín. 0). Trazabilidad en `Faltante_Corregido` y `Cantidad_Faltante_Original`.
- `CodigoDCI` solo viene en COHAN; `FechaEntregaFaltante` no trae fechas (todos "Sin entregar").
- **En la página Total** entra como cuarta fuente: caso = fórmula (gestor + consecutivo), valor = valor faltante estimado, y cruza con PQR/Tutelas por afiliado + `Codigo_CUM` (COHAN no trae CUM). Grupo y cohorte quedan "Sin información".
