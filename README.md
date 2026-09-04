# QA · Votar y comentar un auto (HU-CAR-VOTE-01)

Automatización de pruebas con **Selenium WebDriver + pytest** para la HU de votar
y comentar un auto en [Buggy Cars Rating](https://buggy.justtestit.org/), con
generación de un **dashboard web** de resultados y evidencias que se publica
automáticamente en **GitHub Pages**.

## Archivos del proyecto

| Archivo | Qué hace |
|---|---|
| `test_votar_comentar.py` | Suite de pruebas (14 casos, Page Object Model). |
| `conftest.py` | Captura una evidencia (PNG) por cada test y la incrusta en el reporte. |
| `generar_dashboard.py` | Construye el sitio web (`sitio/index.html`) con resultados + evidencias. |
| `diagnostico.py` / `diagnostico2.py` | Utilidades para inspeccionar el DOM del sitio. |
| `requirements.txt` | Dependencias de Python. |
| `.github/workflows/qa-dashboard.yml` | CI: corre las pruebas y publica el dashboard. |

## Ejecución local

```bash
pip install -r requirements.txt

# (opcional) credenciales para los casos que requieren sesión
export BUGGY_USER="tu_usuario"      # en Windows PowerShell: $env:BUGGY_USER="..."
export BUGGY_PASS="tu_password"     # en Windows PowerShell: $env:BUGGY_PASS="..."

py.test test_votar_comentar.py -v \
  --html=reporte.html --self-contained-html \
  --json-report --json-report-file=reporte.json

python generar_dashboard.py
# Abre sitio/index.html en el navegador
```

## Publicación automática en GitHub Pages

### 1. Subir el proyecto a un repositorio

```bash
git init
git add .
git commit -m "QA: pruebas y dashboard de Votar y comentar un auto"
git branch -M main
git remote add origin https://github.com/<usuario>/<repositorio>.git
git push -u origin main
```

> Sube los archivos `.py` de la suite junto a estos. Las carpetas `evidencias/`
> y `sitio/` están en `.gitignore` porque se regeneran en cada ejecución de CI.

### 2. Activar GitHub Pages

En el repositorio: **Settings → Pages → Build and deployment → Source:
"GitHub Actions"**. No hace falta elegir rama; el workflow se encarga del
despliegue.

### 3. (Opcional) Configurar credenciales como Secrets

Solo si quieres que en CI se ejecuten también los casos que requieren sesión.
En **Settings → Secrets and variables → Actions → New repository secret**, crea:

- `BUGGY_USER` — usuario registrado en el sitio.
- `BUGGY_PASS` — su contraseña.

Si no los defines, esos casos aparecerán como *skipped* (no rompen el flujo).

### 4. Ver el resultado

Cada `git push` a `main` (o un lanzamiento manual desde la pestaña **Actions →
QA Tests & Dashboard → Run workflow**) ejecuta las pruebas y publica el sitio.
La URL aparece en la pestaña **Actions**, en el job `deploy`, y también en
**Settings → Pages**. Suele tener la forma:

```
https://<usuario>.github.io/<repositorio>/
```

El dashboard incluye el resumen de casos, los KPIs, las evidencias por caso y
el reporte HTML de pytest (en `.../reporte.html`).

## Notas

- El workflow usa `continue-on-error` en el paso de pruebas: aunque haya casos
  en rojo (por ejemplo, defectos reales del sitio), el dashboard se publica
  igualmente para reflejar esos resultados.
- Chrome se instala en el runner de CI automáticamente; no requiere
  configuración adicional.
- Las credenciales nunca se escriben en el código: se leen de variables de
  entorno (local) o de Secrets (CI).
