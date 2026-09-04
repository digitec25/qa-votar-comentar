"""
generar_dashboard.py
--------------------
Genera un sitio web (dashboard HTML autocontenido) con los resultados de las
pruebas y sus evidencias.

Uso:
  1) Ejecutar las pruebas guardando el resumen JSON de pytest:
       py -m pytest test_votar_comentar.py -v --json-report --json-report-file=reporte.json
     (requiere: pip install pytest-json-report)
     Si no tienes ese plugin, el script igual funciona leyendo solo las
     imágenes de la carpeta evidencias/.

  2) Generar el sitio:
       py generar_dashboard.py

Salida:
  ./sitio/index.html   -> ábrelo en el navegador (doble clic) o publícalo.

El HTML incrusta las imágenes en base64, así que el archivo es portable:
puedes moverlo, comprimirlo o subirlo a cualquier hosting estático
(GitHub Pages, Netlify, un bucket, etc.) y las evidencias viajan dentro.
"""

import os
import re
import json
import base64
import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
EVID_DIR = os.path.join(BASE, "evidencias")
OUT_DIR = os.path.join(BASE, "sitio")
JSON_REPORT = os.path.join(BASE, "reporte.json")

os.makedirs(OUT_DIR, exist_ok=True)


# --- Descripciones de los casos (para enriquecer el dashboard) ---------------
CASOS = {
    "TC01": ("Botón votar oculto sin sesión", "CA2"),
    "TC02": ("Campo comentario oculto sin sesión", "CA2"),
    "TC03": ("Mensaje de login requerido", "CA2"),
    "TC04": ("Muestra descripción del auto", "CA5"),
    "TC05": ("Muestra especificación", "CA5"),
    "TC06": ("Muestra total de votos", "CA5"),
    "TC07": ("Controles visibles con sesión", "CA1"),
    "TC08": ("Votar incrementa contador", "CA1"),
    "TC09": ("Comentario opcional", "CA3"),
    "TC10": ("Columnas de tabla de comentarios", "CA4"),
    "TC11": ("No permite doble voto", "CA1"),
    "TC12": ("Comentario solo espacios", "CA3"),
    "TC13": ("Comentario con XSS", "CA3"),
    "TC14": ("Comentario muy largo", "CA3"),
}


def leer_resultados_json():
    """Lee resultados desde reporte.json (pytest-json-report). Devuelve dict test->outcome."""
    resultados = {}
    if not os.path.exists(JSON_REPORT):
        return resultados
    try:
        data = json.load(open(JSON_REPORT, encoding="utf-8"))
        for t in data.get("tests", []):
            nodeid = t.get("nodeid", "")
            outcome = t.get("outcome", "")  # passed/failed/skipped
            m = re.search(r"(TC\d+)", nodeid)
            if m:
                resultados[m.group(1)] = outcome
    except Exception as e:
        print("Aviso: no se pudo leer reporte.json:", e)
    return resultados


def leer_evidencias():
    """Agrupa las imágenes de evidencias/ por caso (TCxx) y por paso (PASO_...)."""
    por_caso = {}
    pasos = []
    if not os.path.isdir(EVID_DIR):
        return por_caso, pasos
    for fn in sorted(os.listdir(EVID_DIR)):
        if not fn.lower().endswith(".png"):
            continue
        ruta = os.path.join(EVID_DIR, fn)
        try:
            b64 = base64.b64encode(open(ruta, "rb").read()).decode("ascii")
        except Exception:
            continue
        img = f"data:image/png;base64,{b64}"
        m = re.search(r"(TC\d+)", fn)
        if fn.startswith("PASO_"):
            pasos.append((fn, img))
        elif m:
            por_caso.setdefault(m.group(1), []).append((fn, img))
        else:
            pasos.append((fn, img))
    return por_caso, pasos


def outcome_desde_nombre(archivos):
    """Deduce el resultado a partir del prefijo del archivo (PASSED_/FAILED_/SKIPPED_)."""
    for fn, _ in archivos:
        up = fn.upper()
        if up.startswith("FAILED"):
            return "failed"
        if up.startswith("PASSED"):
            return "passed"
        if up.startswith("SKIPPED"):
            return "skipped"
    return "unknown"


def construir_html(resultados, por_caso, pasos):
    ts = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    # Combinar fuentes de resultado: JSON tiene prioridad; si no, el nombre del archivo
    estados = {}
    for tc in CASOS:
        if tc in resultados:
            estados[tc] = resultados[tc]
        elif tc in por_caso:
            estados[tc] = outcome_desde_nombre(por_caso[tc])
        else:
            estados[tc] = "unknown"

    total = len(CASOS)
    passed = sum(1 for v in estados.values() if v == "passed")
    failed = sum(1 for v in estados.values() if v == "failed")
    skipped = sum(1 for v in estados.values() if v == "skipped")

    color = {"passed": "#1a7f37", "failed": "#cf222e", "skipped": "#9a6700",
             "unknown": "#57606a"}
    etiqueta = {"passed": "PASSED", "failed": "FAILED", "skipped": "SKIPPED",
                "unknown": "SIN DATOS"}

    filas = ""
    tarjetas = ""
    for tc in sorted(CASOS):
        titulo, ca = CASOS[tc]
        est = estados[tc]
        filas += f"""
        <tr>
          <td class="mono">{tc}</td>
          <td>{titulo}</td>
          <td class="mono">{ca}</td>
          <td><span class="badge" style="background:{color[est]}">{etiqueta[est]}</span></td>
          <td>{"<a href='#'+tc onclick=\"return false\">ver</a>" if tc in por_caso else "—"}</td>
        </tr>"""

        imgs = por_caso.get(tc, [])
        galeria = ""
        for fn, img in imgs:
            galeria += f'<figure><img src="{img}" alt="{fn}"><figcaption>{fn}</figcaption></figure>'
        if not galeria:
            galeria = '<p class="muted">Sin evidencia de captura para este caso.</p>'
        tarjetas += f"""
        <section class="card" id="{tc}">
          <header>
            <h3>{tc} · {titulo}</h3>
            <span class="badge" style="background:{color[est]}">{etiqueta[est]}</span>
            <span class="ca">{ca}</span>
          </header>
          <div class="galeria">{galeria}</div>
        </section>"""

    # Galería de pasos intermedios (antes/después de votar, payload XSS, etc.)
    pasos_html = ""
    for fn, img in pasos:
        pasos_html += f'<figure><img src="{img}" alt="{fn}"><figcaption>{fn}</figcaption></figure>'
    if not pasos_html:
        pasos_html = '<p class="muted">No hay capturas de pasos intermedios.</p>'

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Resultados QA · Votar y comentar un auto</title>
<style>
  :root {{ --navy:#1F3864; --bg:#f6f8fa; --line:#d0d7de; }}
  * {{ box-sizing:border-box; }}
  body {{ font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif; margin:0; background:var(--bg); color:#1f2328; }}
  header.top {{ background:var(--navy); color:#fff; padding:24px 32px; }}
  header.top h1 {{ margin:0 0 4px; font-size:22px; }}
  header.top p {{ margin:0; opacity:.85; font-size:13px; }}
  .wrap {{ max-width:1100px; margin:0 auto; padding:24px 32px 60px; }}
  .kpis {{ display:flex; gap:16px; flex-wrap:wrap; margin:24px 0; }}
  .kpi {{ flex:1; min-width:150px; background:#fff; border:1px solid var(--line); border-radius:10px; padding:18px; }}
  .kpi .n {{ font-size:32px; font-weight:700; }}
  .kpi .l {{ font-size:12px; text-transform:uppercase; letter-spacing:.05em; color:#57606a; }}
  table {{ width:100%; border-collapse:collapse; background:#fff; border:1px solid var(--line); border-radius:10px; overflow:hidden; }}
  th,td {{ text-align:left; padding:10px 14px; border-bottom:1px solid var(--line); font-size:14px; }}
  th {{ background:var(--navy); color:#fff; font-weight:600; }}
  tr:last-child td {{ border-bottom:none; }}
  .mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
  .badge {{ color:#fff; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:700; }}
  h2 {{ margin-top:40px; color:var(--navy); border-bottom:2px solid var(--line); padding-bottom:6px; }}
  .card {{ background:#fff; border:1px solid var(--line); border-radius:10px; margin:18px 0; padding:18px; }}
  .card header {{ display:flex; align-items:center; gap:12px; margin-bottom:12px; }}
  .card h3 {{ margin:0; font-size:16px; flex:1; }}
  .card .ca {{ font-size:12px; color:#57606a; }}
  .galeria {{ display:flex; gap:14px; flex-wrap:wrap; }}
  figure {{ margin:0; border:1px solid var(--line); border-radius:8px; overflow:hidden; width:300px; background:#fff; }}
  figure img {{ width:100%; display:block; cursor:zoom-in; }}
  figcaption {{ font-size:11px; color:#57606a; padding:6px 8px; word-break:break-all; }}
  .muted {{ color:#8b949e; font-style:italic; }}
  footer {{ text-align:center; color:#8b949e; font-size:12px; padding:24px; }}
  /* lightbox */
  #lb {{ position:fixed; inset:0; background:rgba(0,0,0,.85); display:none; align-items:center; justify-content:center; z-index:99; cursor:zoom-out; }}
  #lb img {{ max-width:92%; max-height:92%; }}
</style>
</head>
<body>
<header class="top">
  <h1>Resultados de Pruebas · Votar y comentar un auto</h1>
  <p>HU-CAR-VOTE-01 · Buggy Cars Rating · Generado el {ts}</p>
</header>
<div class="wrap">

  <div class="kpis">
    <div class="kpi"><div class="n">{total}</div><div class="l">Casos totales</div></div>
    <div class="kpi"><div class="n" style="color:#1a7f37">{passed}</div><div class="l">Passed</div></div>
    <div class="kpi"><div class="n" style="color:#cf222e">{failed}</div><div class="l">Failed</div></div>
    <div class="kpi"><div class="n" style="color:#9a6700">{skipped}</div><div class="l">Skipped</div></div>
  </div>

  <h2>Resumen de casos</h2>
  <table>
    <thead><tr><th>ID</th><th>Título</th><th>CA</th><th>Resultado</th><th>Evidencia</th></tr></thead>
    <tbody>{filas}</tbody>
  </table>

  <h2>Evidencias por caso</h2>
  {tarjetas}

  <h2>Pasos intermedios</h2>
  <div class="galeria">{pasos_html}</div>

</div>
<footer>Dashboard de QA generado automáticamente · las imágenes están embebidas (archivo portable)</footer>

<div id="lb"><img src="" alt=""></div>
<script>
  // Lightbox: clic en cualquier imagen para ampliarla
  const lb = document.getElementById('lb'), lbimg = lb.querySelector('img');
  document.querySelectorAll('figure img').forEach(im => {{
    im.addEventListener('click', () => {{ lbimg.src = im.src; lb.style.display='flex'; }});
  }});
  lb.addEventListener('click', () => lb.style.display='none');
</script>
</body>
</html>"""
    return html


def main():
    resultados = leer_resultados_json()
    por_caso, pasos = leer_evidencias()
    html = construir_html(resultados, por_caso, pasos)
    out = os.path.join(OUT_DIR, "index.html")
    open(out, "w", encoding="utf-8").write(html)
    n_img = sum(len(v) for v in por_caso.values()) + len(pasos)
    print(f"Sitio generado: {out}")
    print(f"  Casos con resultado: {len(resultados) or 'desde nombres de archivo'}")
    print(f"  Imágenes incrustadas: {n_img}")
    print("Abre el archivo en tu navegador (doble clic).")


if __name__ == "__main__":
    main()
