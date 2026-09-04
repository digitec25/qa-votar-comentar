"""
Diagnóstico robusto de Buggy Cars Rating.
No asume ninguna estructura; explora la home y /overall e imprime
todos los enlaces a autos y la estructura de la ficha.

Ejecutar:  py diagnostico.py
Copiar TODA la salida y enviarla.
"""
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

BASE = "https://buggy.justtestit.org/"

opts = Options()
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1400,1000")
opts.add_argument("--headless=new")

drv = webdriver.Chrome(options=opts)
drv.implicitly_wait(2)


def dump_car_links(nombre):
    print("\n" + "#" * 70)
    print(f"# PAGINA: {nombre}  ->  {drv.current_url}")
    print("#" * 70)
    enlaces = drv.find_elements(By.TAG_NAME, "a")
    print(f"Total de <a> en la pagina: {len(enlaces)}")
    modelos = []
    for a in enlaces:
        href = a.get_attribute("href") or ""
        txt = (a.text or "").strip()
        if "/model/" in href:
            modelos.append((href, txt))
    print(f"Enlaces con '/model/' encontrados: {len(modelos)}")
    for href, txt in modelos[:10]:
        print(f"   href={href}  texto={txt!r}")
    return modelos


try:
    drv.get(BASE)
    time.sleep(4)
    print("Titulo de la pestana:", drv.title)
    modelos = dump_car_links("HOME")

    drv.get(BASE + "overall")
    time.sleep(4)
    m2 = dump_car_links("OVERALL")
    if not modelos:
        modelos = m2

    if not modelos:
        print("\n!!! No se hallaron enlaces /model/. Volcado del <body>:")
        print(drv.find_element(By.TAG_NAME, "body").get_attribute("innerHTML")[:3000])
    else:
        url_auto = modelos[0][0]
        drv.get(url_auto)
        time.sleep(4)
        print("\n" + "=" * 70)
        print("FICHA DEL AUTO:", drv.current_url)
        print("=" * 70)

        print("\n--- Encabezados (h1..h5) ---")
        for tag in ("h1", "h2", "h3", "h4", "h5"):
            for e in drv.find_elements(By.TAG_NAME, tag):
                if e.text.strip():
                    print(f"  <{tag}> {e.text.strip()!r}")

        print("\n--- Tablas y sus encabezados ---")
        for i, t in enumerate(drv.find_elements(By.TAG_NAME, "table")):
            ths = [th.text.strip() for th in t.find_elements(By.TAG_NAME, "th")]
            print(f"  Tabla #{i}: headers = {ths}")

        print("\n--- dl / dt / dd ---")
        for sel in ("dt", "dd"):
            for e in drv.find_elements(By.CSS_SELECTOR, sel):
                if e.text.strip():
                    print(f"  [{sel}] {e.text.strip()!r}")

        print("\n--- botones ---")
        for b in drv.find_elements(By.TAG_NAME, "button"):
            print(f"  <button> class={b.get_attribute('class')!r} text={b.text.strip()!r} disabled={b.get_attribute('disabled')}")

        print("\n--- textareas ---")
        for ta in drv.find_elements(By.TAG_NAME, "textarea"):
            print(f"  <textarea> name={ta.get_attribute('name')!r} placeholder={ta.get_attribute('placeholder')!r}")

        print("\n--- HTML del contenedor principal (2500 chars) ---")
        try:
            cont = drv.find_element(By.CSS_SELECTOR, "app-model")
        except Exception:
            cont = drv.find_element(By.TAG_NAME, "body")
        print(cont.get_attribute("outerHTML")[:2500])

finally:
    drv.quit()
    print("\n>>> Diagnostico terminado.")
