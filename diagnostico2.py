"""
Diagnóstico 2: estado de la ficha SIN sesión.
Verifica exactamente qué controles y mensajes existen, para ajustar
las aserciones y detectar falsos positivos.

Ejecutar:  py diagnostico2.py
Copiar TODA la salida.
"""
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

BASE = "https://buggy.justtestit.org/"
CAR = "model/ckl2phsabijs71623vk0%7Cckl2phsabijs71623vqg"

opts = Options()
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1400,1000")
opts.add_argument("--headless=new")

drv = webdriver.Chrome(options=opts)
drv.implicitly_wait(2)

try:
    drv.get(BASE + CAR)
    time.sleep(5)
    print("URL:", drv.current_url)

    print("\n=== ¿Existe botón con texto 'Vote'? ===")
    votes = drv.find_elements(By.XPATH, "//button[contains(.,'Vote') or contains(.,'vote')]")
    print(f"  Botones 'Vote' encontrados: {len(votes)}")
    for b in votes:
        print(f"    text={b.text!r} displayed={b.is_displayed()}")

    print("\n=== ¿Existe textarea o input de comentario? ===")
    tas = drv.find_elements(By.TAG_NAME, "textarea")
    print(f"  textareas: {len(tas)}")
    for t in tas:
        print(f"    name={t.get_attribute('name')!r} displayed={t.is_displayed()}")

    print("\n=== Texto completo del componente my-model ===")
    try:
        modelo = drv.find_element(By.TAG_NAME, "my-model")
        print(repr(modelo.text))
    except Exception as e:
        print("  no se encontró my-model:", e)

    print("\n=== ¿Hay algún texto tipo 'log in / login to vote / sign in'? ===")
    palabras = ["log in", "login", "sign in", "vote", "iniciar", "sesión", "sesion"]
    encontrados = []
    for p in palabras:
        els = drv.find_elements(
            By.XPATH,
            f"//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{p}')]"
        )
        for e in els:
            t = e.text.strip()
            if t and t not in [x[1] for x in encontrados]:
                encontrados.append((p, t, e.tag_name))
    if encontrados:
        for p, t, tag in encontrados:
            print(f"    match '{p}' en <{tag}>: {t!r}")
    else:
        print("    NINGÚN texto de login/vote encontrado en el cuerpo de la ficha.")

    print("\n=== Encabezados h3/h4 del modelo ===")
    for tag in ("h3", "h4"):
        for e in drv.find_elements(By.CSS_SELECTOR, f"my-model {tag}"):
            if e.text.strip():
                print(f"    <{tag}> {e.text.strip()!r}")

finally:
    drv.quit()
    print("\n>>> Diagnóstico 2 terminado.")
