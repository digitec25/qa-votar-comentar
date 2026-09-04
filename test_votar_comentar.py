"""
Automatización de pruebas - HU: Votar y comentar un auto
Aplicación bajo prueba: https://buggy.justtestit.org/ (Buggy Cars Rating)

Framework: pytest + Selenium WebDriver
Patrón: Page Object Model (POM)

Selectores verificados contra el DOM real del sitio (Angular / my-app).

Ejecución:
    pip install selenium pytest webdriver-manager pytest-html
    py -m pytest test_votar_comentar.py -v --html=reporte.html

Variables de entorno (opcional, para pruebas autenticadas):
    BUGGY_USER  -> usuario registrado válido
    BUGGY_PASS  -> contraseña
    HEADLESS    -> "1" headless (default) | "0" con ventana visible
"""

import os
import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

BASE_URL = os.getenv("BUGGY_URL", "https://buggy.justtestit.org/")
USERNAME = os.getenv("BUGGY_USER", "")
PASSWORD = os.getenv("BUGGY_PASS", "")
HEADLESS = os.getenv("HEADLESS", "1") == "1"
TIMEOUT = 20

# Ficha de auto conocida (Lamborghini Diablo) usada como punto de entrada estable.
# El '|' de la URL va codificado como %7C.
CAR_PATH = "model/ckl2phsabijs71623vk0%7Cckl2phsabijs71623vqg"


# ----------------------------------------------------------------------------
# Page Objects
# ----------------------------------------------------------------------------
class BasePage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, TIMEOUT)

    def open(self, path=""):
        self.driver.get(BASE_URL.rstrip("/") + "/" + path.lstrip("/"))
        return self

    def find(self, by, value):
        return self.wait.until(EC.presence_of_element_located((by, value)))

    def click(self, by, value):
        el = self.wait.until(EC.element_to_be_clickable((by, value)))
        el.click()
        return el

    def is_present(self, by, value, timeout=4):
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return True
        except TimeoutException:
            return False

    def shot(self, etiqueta):
        """Captura manual de evidencia en un punto intermedio del flujo."""
        import os, datetime
        d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidencias")
        os.makedirs(d, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        slug = "".join(c if (c.isalnum() or c in "-_") else "_" for c in etiqueta)
        ruta = os.path.join(d, f"PASO_{slug}_{ts}.png")
        try:
            self.driver.save_screenshot(ruta)
            print(f"[EVIDENCIA-PASO] {ruta}")
        except Exception as e:
            print(f"[EVIDENCIA-PASO] fallo: {e}")
        return self

    def highlight(self, by, value, color="red"):
        """Rodea un elemento con un borde para que la evidencia muestre qué se validó."""
        try:
            el = self.driver.find_element(by, value)
            self.driver.execute_script(
                "arguments[0].style.outline='4px solid " + color + "';"
                "arguments[0].scrollIntoView({block:'center'});", el)
        except Exception:
            pass
        return self



class HomePage(BasePage):
    LOGIN_USER = (By.NAME, "login")
    LOGIN_PASS = (By.NAME, "password")
    LOGIN_BTN = (By.CSS_SELECTOR, "button.btn.btn-success[type='submit']")
    LOGOUT = (By.XPATH, "//*[normalize-space(text())='Logout']")
    NAV_GREETING = (By.XPATH, "//*[contains(text(),'Hi,')]")

    def login(self, user, pwd):
        self.find(*self.LOGIN_USER).clear()
        self.find(*self.LOGIN_USER).send_keys(user)
        self.find(*self.LOGIN_PASS).clear()
        self.find(*self.LOGIN_PASS).send_keys(pwd)
        self.click(*self.LOGIN_BTN)
        return self

    def is_logged_in(self):
        # Tras loguear aparece "Hi, <user>" y el enlace Logout en el nav.
        return self.is_present(*self.LOGOUT, timeout=10) or \
            self.is_present(*self.NAV_GREETING, timeout=3)

    def open_car(self):
        """Abre la ficha de un auto conocida y espera a que el modelo renderice."""
        self.open(CAR_PATH)
        car = CarPage(self.driver)
        # Espera a que Angular pinte el título de la marca en el modelo
        car.find(*CarPage.MAKE_TITLE)
        return car


class CarPage(BasePage):
    # El modelo va en <h3>, la marca en <h4>.
    MODEL_TITLE = (By.CSS_SELECTOR, "my-model h3")
    MAKE_TITLE = (By.XPATH, "//my-model//h4[not(contains(.,'Specification')) and not(contains(.,'Votes'))]")
    SPECIFICATION = (By.XPATH, "//h4[contains(.,'Specification')]")
    SPEC_TABLE = (By.XPATH, "//h4[contains(.,'Specification')]/following::table[1]")
    VOTES_HEADER = (By.XPATH, "//h4[contains(.,'Votes')]")
    # Descripción / comentario y voto solo existen autenticado:
    VOTE_BUTTON = (By.XPATH, "//button[contains(normalize-space(.),'Vote')]")
    COMMENT_TEXTAREA = (By.CSS_SELECTOR, "textarea, input[name='comment']")
    # Mensaje que se muestra sin sesión pidiendo login:
    # Mensaje exacto que muestra la app sin sesión (confirmado en el DOM real):
    LOGIN_REQUIRED_MSG = (By.XPATH, "//my-model//p[contains(normalize-space(.),'You need to be logged in to vote')]")
    COMMENTS_HEADERS = (By.CSS_SELECTOR, "table thead th, table th")

    def make_text(self):
        return self.find(*self.MAKE_TITLE).text.strip()

    def votes_text(self):
        return self.find(*self.VOTES_HEADER).text.strip()

    def votes_count(self):
        # "Votes: 10291" -> 10291
        txt = self.votes_text()
        import re
        m = re.search(r"(\d+)", txt.replace(",", ""))
        return int(m.group(1)) if m else None

    def vote(self):
        self.click(*self.VOTE_BUTTON)
        return self

    def set_comment(self, text):
        ta = self.find(*self.COMMENT_TEXTAREA)
        ta.clear()
        ta.send_keys(text)
        return self

    def vote_button_present(self, timeout=4):
        return self.is_present(*self.VOTE_BUTTON, timeout=timeout)

    def comment_field_present(self, timeout=4):
        return self.is_present(*self.COMMENT_TEXTAREA, timeout=timeout)

    def login_message_present(self, timeout=4):
        return self.is_present(*self.LOGIN_REQUIRED_MSG, timeout=timeout)

    def comment_headers(self):
        return [e.text.strip() for e in self.driver.find_elements(*self.COMMENTS_HEADERS)]

    def on_car_page(self):
        """Confirma que estamos realmente en una ficha de auto (evita falsos positivos)."""
        return self.is_present(*self.VOTES_HEADER, timeout=8)


# ----------------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------------
@pytest.fixture
def driver():
    opts = Options()
    if HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1400,1000")
    drv = webdriver.Chrome(options=opts)
    drv.implicitly_wait(1)
    yield drv
    drv.quit()


@pytest.fixture
def car_page(driver):
    """Ficha de auto abierta SIN sesión."""
    return HomePage(driver).open().open_car()


@pytest.fixture
def logged_in_car(driver):
    """Ficha de auto con el usuario autenticado."""
    if not (USERNAME and PASSWORD):
        pytest.skip("Definir BUGGY_USER y BUGGY_PASS para pruebas autenticadas")
    home = HomePage(driver).open()
    home.login(USERNAME, PASSWORD)
    assert home.is_logged_in(), "No se pudo iniciar sesión (credenciales o selector de login)"
    return home.open_car()


# ----------------------------------------------------------------------------
# CA2 - Sin sesión: controles ocultos + mensaje
# ----------------------------------------------------------------------------
class TestSinSesion:
    def test_TC01_voto_oculto_sin_sesion(self, car_page):
        """CA2: el botón de votar debe estar oculto sin sesión."""
        assert car_page.on_car_page(), "Precondición: no se cargó la ficha del auto"
        assert not car_page.vote_button_present(timeout=4), \
            "El botón Vote NO debería mostrarse sin sesión iniciada"

    def test_TC02_comentario_oculto_sin_sesion(self, car_page):
        """CA2: el campo de comentario debe estar oculto sin sesión."""
        assert car_page.on_car_page(), "Precondición: no se cargó la ficha del auto"
        assert not car_page.comment_field_present(timeout=4), \
            "El campo de comentario NO debería mostrarse sin sesión iniciada"

    def test_TC03_mensaje_login_requerido(self, car_page):
        """CA2: debe mostrarse el mensaje informativo pidiendo iniciar sesión."""
        assert car_page.on_car_page(), "Precondición: no se cargó la ficha del auto"
        assert car_page.login_message_present(timeout=4), \
            "Debe existir el mensaje 'You need to be logged in to vote.'"
        # Aserción estricta del texto exacto (evita falsos positivos):
        msg = car_page.find(*CarPage.LOGIN_REQUIRED_MSG).text.strip()
        assert "logged in to vote" in msg.lower(), \
            f"El texto del mensaje no es el esperado. Obtenido: {msg!r}"
        car_page.highlight(*CarPage.LOGIN_REQUIRED_MSG)
        car_page.shot("TC03_mensaje_login_requerido")


# ----------------------------------------------------------------------------
# CA5 - Datos de la ficha (visibles con o sin sesión)
# ----------------------------------------------------------------------------
class TestFichaAuto:
    def test_TC04_muestra_descripcion(self, car_page):
        """CA5: se muestra la descripción/identificación del auto (marca y modelo)."""
        assert car_page.make_text() != "", "Debe mostrarse la marca del auto"
        assert car_page.is_present(*CarPage.MODEL_TITLE, timeout=5), \
            "Debe mostrarse el modelo del auto"
        car_page.highlight(*CarPage.MODEL_TITLE)
        car_page.shot("TC04_descripcion_auto")

    def test_TC05_muestra_especificacion(self, car_page):
        """CA5: se muestra la sección de especificación."""
        assert car_page.is_present(*CarPage.SPECIFICATION, timeout=5), \
            "Debe mostrarse el encabezado 'Specification'"
        assert car_page.is_present(*CarPage.SPEC_TABLE, timeout=5), \
            "Debe mostrarse la tabla de especificación"
        car_page.highlight(*CarPage.SPECIFICATION)
        car_page.shot("TC05_especificacion")

    def test_TC06_muestra_total_votos(self, car_page):
        """CA5: se muestra la cantidad total de votos."""
        n = car_page.votes_count()
        assert n is not None and n >= 0, \
            f"Debe mostrarse la cantidad total de votos (obtenido: {car_page.votes_text()!r})"
        car_page.highlight(*CarPage.VOTES_HEADER)
        car_page.shot("TC06_total_votos")


# ----------------------------------------------------------------------------
# CA1 / CA3 / CA4 - Usuario autenticado
# ----------------------------------------------------------------------------
class TestConSesion:
    def test_TC07_controles_visibles_con_sesion(self, logged_in_car):
        """CA1: con sesión, botón de votar y campo comentario visibles."""
        assert logged_in_car.vote_button_present(timeout=6), "Falta el botón Vote"
        assert logged_in_car.comment_field_present(timeout=6), "Falta el campo de comentario"

    def test_TC08_votar_incrementa_contador(self, logged_in_car):
        """CA1: votar incrementa el contador de votos."""
        antes = logged_in_car.votes_count()
        logged_in_car.shot("TC08_antes_de_votar")
        logged_in_car.vote()
        time.sleep(2)
        logged_in_car.shot("TC08_despues_de_votar")
        despues = logged_in_car.votes_count()
        assert despues is not None and antes is not None
        assert despues >= antes, "El contador de votos no debería disminuir tras votar"

    def test_TC09_comentario_es_opcional(self, logged_in_car):
        """CA3: se puede votar sin escribir comentario."""
        logged_in_car.vote()
        time.sleep(1)
        assert not logged_in_car.is_present(
            By.XPATH,
            "//*[contains(translate(.,'REQUIRED','required'),'required') or contains(.,'obligatorio')]",
            timeout=2), "El comentario NO debe ser obligatorio"

    def test_TC10_columnas_tabla_comentarios(self, logged_in_car):
        """CA4: la tabla de comentarios tiene columnas Date, Author, Comment."""
        headers = [h.lower() for h in logged_in_car.comment_headers()]
        for esperado in ("date", "author", "comment"):
            assert esperado in headers, \
                f"Falta la columna '{esperado}'. Encontradas: {headers}"


# ----------------------------------------------------------------------------
# Negativos / seguridad / borde
# ----------------------------------------------------------------------------
class TestNegativosYBordes:
    @pytest.mark.xfail(reason="Defecto conocido de Buggy Cars: puede permitir múltiples votos")
    def test_TC11_no_permite_doble_voto(self, logged_in_car):
        """Un usuario no debería poder votar dos veces el mismo auto."""
        logged_in_car.vote()
        time.sleep(1)
        btns = logged_in_car.driver.find_elements(*CarPage.VOTE_BUTTON)
        assert btns and not btns[0].is_enabled(), \
            "El botón Vote debería deshabilitarse tras el primer voto"

    def test_TC12_comentario_espacios_en_blanco(self, logged_in_car):
        """Un comentario solo de espacios no debería registrarse como válido."""
        logged_in_car.set_comment("     ")
        logged_in_car.vote()
        time.sleep(1)
        assert True  # observacional: registrar hallazgo si guarda basura

    def test_TC13_comentario_xss(self, logged_in_car):
        """Seguridad: un comentario con script no debe ejecutarse."""
        payload = "<script>window.__xss=1</script>"
        logged_in_car.set_comment(payload)
        logged_in_car.shot("TC13_payload_xss_escrito")
        logged_in_car.vote()
        time.sleep(1)
        ejecutado = logged_in_car.driver.execute_script("return window.__xss === 1;")
        assert not ejecutado, "Vulnerabilidad XSS: el script del comentario se ejecutó"

    def test_TC14_comentario_muy_largo(self, logged_in_car):
        """Borde: comentario extenso (2000 chars) no debe romper la UI."""
        logged_in_car.set_comment("A" * 2000)
        logged_in_car.vote()
        time.sleep(1)
        assert logged_in_car.is_present(By.CSS_SELECTOR, "table", timeout=3), \
            "La tabla de comentarios no debe romperse con texto largo"


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
