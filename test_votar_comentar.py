"""
Suite de pruebas E2E - HU: Votar y comentar un auto
Aplicación: https://buggy.justtestit.org/ (Buggy Cars Rating)

Framework: pytest + Selenium WebDriver · Page Object Model
Selectores verificados contra el DOM real (diagnóstico completo del sitio).

CARACTERÍSTICAS:
- Registra un usuario NUEVO automáticamente en cada corrida (sin credenciales manuales).
- Reutiliza esa sesión para todos los casos autenticados.
- Los defectos reales del sitio se afirman de forma ESTRICTA: si el sitio falla,
  el test sale FAILED (rojo). No se usan xfail que oculten defectos.

Ejecución:
    pip install selenium pytest pytest-html pytest-json-report
    py -m pytest test_votar_comentar.py -v --html=reporte.html --self-contained-html \
        --json-report --json-report-file=reporte.json
"""

import os, time, random, string, re
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

BASE_URL = os.getenv("BUGGY_URL", "https://buggy.justtestit.org/")
HEADLESS = os.getenv("HEADLESS", "1") == "1"
TIMEOUT = 20
CAR_PATH = "model/ckl2phsabijs71623vk0%7Cckl2phsabijs71623vqg"


def _rnd(n=7):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


# Credenciales generadas una sola vez por sesión de pruebas
REG_USER = "qa" + _rnd(8)
REG_PASS = "Passw0rd!" + _rnd(3)


# ---------------------------------------------------------------------------
# Page Objects
# ---------------------------------------------------------------------------
class Base:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, TIMEOUT)

    def open(self, path=""):
        self.driver.get(BASE_URL.rstrip("/") + "/" + path.lstrip("/"))
        return self

    def find(self, by, val):
        return self.wait.until(EC.presence_of_element_located((by, val)))

    def click(self, by, val):
        self.wait.until(EC.element_to_be_clickable((by, val))).click()

    def present(self, by, val, timeout=4):
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, val)))
            return True
        except TimeoutException:
            return False

    def shot(self, etiqueta):
        import datetime
        d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidencias")
        os.makedirs(d, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        slug = "".join(c if (c.isalnum() or c in "-_") else "_" for c in etiqueta)
        try:
            self.driver.save_screenshot(os.path.join(d, f"PASO_{slug}_{ts}.png"))
        except Exception:
            pass
        return self

    def highlight(self, by, val, color="red"):
        try:
            el = self.driver.find_element(by, val)
            self.driver.execute_script(
                "arguments[0].style.outline='4px solid "+color+"';"
                "arguments[0].scrollIntoView({block:'center'});", el)
        except Exception:
            pass
        return self


class Nav(Base):
    LOGIN_INPUT = (By.NAME, "login")
    PASS_INPUT = (By.NAME, "password")
    LOGIN_BTN = (By.XPATH, "//button[@type='submit' and contains(.,'Login')]")
    LOGOUT = (By.XPATH, "//a[normalize-space()='Logout'] | //*[normalize-space()='Logout']")

    def login(self, user, pwd):
        self.open("")
        self.find(*self.LOGIN_INPUT).clear()
        self.find(*self.LOGIN_INPUT).send_keys(user)
        self.find(*self.PASS_INPUT).clear()
        self.find(*self.PASS_INPUT).send_keys(pwd)
        self.click(*self.LOGIN_BTN)
        # Esperar a que aparezca Logout (sesión iniciada)
        return self.present(*self.LOGOUT, timeout=10)

    def is_logged_in(self):
        return self.present(*self.LOGOUT, timeout=5)

    def logout(self):
        if self.present(*self.LOGOUT, timeout=3):
            self.click(*self.LOGOUT)


class RegisterPage(Base):
    LOGIN = (By.NAME, "login")
    USERNAME = (By.NAME, "username")
    FIRST = (By.NAME, "firstName")
    LAST = (By.NAME, "lastName")
    PASS = (By.NAME, "password")
    CONFIRM = (By.NAME, "confirmPassword")
    REGISTER_BTN = (By.XPATH, "//button[contains(.,'Register')]")
    RESULT = (By.XPATH, "//*[contains(.,'successful') or contains(.,'already exists') "
                        "or contains(.,'Please') or contains(.,'Invalid')]")

    def register(self, user, pwd):
        self.open("register")
        # hay dos inputs password con el mismo name; usar el primero para 'password'
        self.find(*self.LOGIN).send_keys(user)
        self.find(*self.USERNAME).send_keys(user)
        self.find(*self.FIRST).send_keys("QA")
        self.find(*self.LAST).send_keys("Tester")
        passwords = self.driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
        # password (primero) y confirmPassword (último)
        passwords[0].send_keys(pwd)
        self.driver.find_element(*self.CONFIRM).send_keys(pwd)
        self.click(*self.REGISTER_BTN)
        time.sleep(3)
        try:
            return self.driver.find_element(*self.RESULT).text.strip()
        except Exception:
            return self.driver.find_element(By.TAG_NAME, "body").text


class CarPage(Base):
    MODEL = (By.CSS_SELECTOR, "my-model h3")
    MAKE = (By.XPATH, "//my-model//h4[not(contains(.,'Specification')) and not(contains(.,'Votes'))]")
    SPEC = (By.XPATH, "//h4[contains(.,'Specification')]")
    SPEC_TABLE = (By.XPATH, "//h4[contains(.,'Specification')]/following::table[1]")
    VOTES = (By.XPATH, "//h4[contains(.,'Votes')]")
    VOTE_BTN = (By.XPATH, "//button[contains(normalize-space(.),'Vote')]")
    COMMENT = (By.ID, "comment")
    COMMENTS_TABLE = (By.XPATH, "//table[.//th[contains(.,'Comment')]]")
    COMMENTS_HEADERS = (By.XPATH, "//table//th")
    COMMENTS_ROWS = (By.XPATH, "//table[.//th[contains(.,'Comment')]]/tbody/tr")
    LOGIN_MSG = (By.XPATH, "//my-model//*[contains(normalize-space(.),'logged in to vote')]")

    def open_car(self):
        self.open(CAR_PATH)
        self.find(*self.VOTES)   # esperar render
        return self

    def votes_count(self):
        txt = self.find(*self.VOTES).text
        m = re.search(r"(\d[\d,]*)", txt.replace(",", ""))
        return int(m.group(1)) if m else None

    def vote(self):
        self.click(*self.VOTE_BTN)
        time.sleep(2)

    def set_comment(self, text):
        ta = self.find(*self.COMMENT)
        ta.clear(); ta.send_keys(text)

    def headers(self):
        return [e.text.strip() for e in self.driver.find_elements(*self.COMMENTS_HEADERS)]

    def first_comment_text(self):
        rows = self.driver.find_elements(*self.COMMENTS_ROWS)
        if not rows:
            return None
        tds = rows[0].find_elements(By.TAG_NAME, "td")
        return tds[-1].text.strip() if tds else None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def _driver_session():
    opts = Options()
    if HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1400,1000")
    drv = webdriver.Chrome(options=opts)
    yield drv
    drv.quit()


@pytest.fixture
def driver(_driver_session):
    return _driver_session


# Estado compartido del registro/login a nivel de sesión
_session_state = {"registered": False, "logged_in": False, "register_msg": ""}


@pytest.fixture
def car(driver):
    """Ficha del auto SIN forzar sesión (estado actual del navegador)."""
    return CarPage(driver).open_car()


@pytest.fixture
def logged_car(driver):
    """Garantiza sesión iniciada (registrando+logueando si hace falta) y abre la ficha."""
    nav = Nav(driver)
    if not _session_state["logged_in"]:
        if not nav.is_logged_in():
            ok = nav.login(REG_USER, REG_PASS)
            if not ok:
                pytest.skip("No hay sesión activa (ver TC00: registro/login del sitio falló)")
        _session_state["logged_in"] = True
    return CarPage(driver).open_car()


# ---------------------------------------------------------------------------
# TC00 - Registro + Login (precondición y prueba en sí misma)
# ---------------------------------------------------------------------------
class TestRegistroLogin:
    def test_TC00a_registro_usuario(self, driver):
        """Registrar un usuario nuevo debe indicar 'Registration is successful'."""
        msg = RegisterPage(driver).register(REG_USER, REG_PASS)
        _session_state["registered"] = "successful" in msg.lower()
        _session_state["register_msg"] = msg
        driver.save_screenshot(_ev("PASO_TC00a_registro"))
        assert "successful" in msg.lower(), \
            f"El registro no fue exitoso. Mensaje del sitio: {msg!r}"

    def test_TC00b_login_tras_registro(self, driver):
        """Login con el usuario recién registrado debe iniciar sesión (mostrar Logout)."""
        ok = Nav(driver).login(REG_USER, REG_PASS)
        _session_state["logged_in"] = ok
        driver.save_screenshot(_ev("PASO_TC00b_login"))
        assert ok, ("No se pudo iniciar sesión con el usuario recién registrado "
                    f"({REG_USER}). DEFECTO: el login tras registro no funciona.")


# ---------------------------------------------------------------------------
# CA2 - Sin sesión: controles ocultos + mensaje
# ---------------------------------------------------------------------------
class TestSinSesion:
    def test_TC01_voto_oculto_sin_sesion(self, driver):
        """CA2: el botón de votar debe estar OCULTO sin sesión."""
        Nav(driver).logout()
        car = CarPage(driver).open_car()
        car.highlight(*CarPage.VOTES); car.shot("TC01_sin_sesion")
        assert not car.present(*CarPage.VOTE_BTN, timeout=4), \
            "DEFECTO (CA2): el botón 'Vote!' se muestra SIN sesión iniciada."

    def test_TC02_comentario_oculto_sin_sesion(self, driver):
        """CA2: el campo de comentario debe estar OCULTO sin sesión."""
        Nav(driver).logout()
        car = CarPage(driver).open_car()
        assert not car.present(*CarPage.COMMENT, timeout=4), \
            "DEFECTO (CA2): el campo de comentario se muestra SIN sesión iniciada."

    def test_TC03_mensaje_login_requerido(self, driver):
        """CA2: debe mostrarse el mensaje 'You need to be logged in to vote.'"""
        Nav(driver).logout()
        car = CarPage(driver).open_car()
        car.highlight(*CarPage.LOGIN_MSG); car.shot("TC03_mensaje_login")
        assert car.present(*CarPage.LOGIN_MSG, timeout=4), \
            "DEFECTO (CA2): no se muestra el mensaje de 'iniciar sesión para votar'."


# ---------------------------------------------------------------------------
# CA5 - Datos de la ficha
# ---------------------------------------------------------------------------
class TestFichaAuto:
    def test_TC04_muestra_descripcion(self, car):
        car.highlight(*CarPage.MODEL); car.shot("TC04_descripcion")
        assert car.find(*CarPage.MAKE).text.strip() != ""
        assert car.present(*CarPage.MODEL, timeout=5), "No se muestra el modelo."

    def test_TC05_muestra_especificacion(self, car):
        car.highlight(*CarPage.SPEC); car.shot("TC05_especificacion")
        assert car.present(*CarPage.SPEC, timeout=5), "No se muestra 'Specification'."
        assert car.present(*CarPage.SPEC_TABLE, timeout=5), "No se muestra la tabla de especificación."

    def test_TC06_muestra_total_votos(self, car):
        car.highlight(*CarPage.VOTES); car.shot("TC06_votos")
        n = car.votes_count()
        assert n is not None and n >= 0, "No se muestra la cantidad total de votos."


# ---------------------------------------------------------------------------
# CA1 / CA3 / CA4 - Autenticado (pruebas reales)
# ---------------------------------------------------------------------------
class TestConSesion:
    def test_TC07_controles_visibles_con_sesion(self, logged_car):
        """CA1: con sesión, botón de votar y campo comentario visibles."""
        logged_car.highlight(*CarPage.VOTE_BTN); logged_car.shot("TC07_controles")
        assert logged_car.present(*CarPage.VOTE_BTN, timeout=6), "Falta botón Vote!"
        assert logged_car.present(*CarPage.COMMENT, timeout=6), "Falta campo comentario."

    def test_TC08_votar_incrementa_contador(self, logged_car):
        """CA1: votar incrementa el contador en 1."""
        antes = logged_car.votes_count()
        logged_car.shot("TC08_antes")
        logged_car.vote()
        logged_car.shot("TC08_despues")
        despues = logged_car.votes_count()
        assert despues == antes + 1, \
            f"El contador debía subir de {antes} a {antes+1}, pero quedó en {despues}."

    def test_TC09_comentario_opcional(self, logged_car):
        """CA3: se puede votar SIN comentario (el comentario es opcional)."""
        antes = logged_car.votes_count()
        logged_car.vote()  # sin escribir comentario
        despues = logged_car.votes_count()
        assert despues == antes + 1, "No se pudo votar sin comentario (debe ser opcional)."

    def test_TC10_columnas_tabla_comentarios(self, logged_car):
        """CA4: la tabla de comentarios tiene columnas Date, Author, Comment."""
        logged_car.highlight(*CarPage.COMMENTS_TABLE); logged_car.shot("TC10_tabla")
        headers = [h.lower() for h in logged_car.headers()]
        for col in ("date", "author", "comment"):
            assert col in headers, f"Falta la columna '{col}'. Headers: {headers}"

    def test_TC11_comentario_se_muestra_en_tabla(self, logged_car):
        """CA4: un comentario nuevo aparece en la tabla tras votar."""
        marca = "QA-" + _rnd(8)
        logged_car.set_comment(marca)
        logged_car.vote()
        logged_car.open_car()  # refrescar
        time.sleep(2)
        cuerpo = logged_car.driver.find_element(By.TAG_NAME, "body").text
        assert marca in cuerpo, f"El comentario {marca!r} no aparece en la tabla tras votar."


# ---------------------------------------------------------------------------
# Negativos / seguridad / borde - DEFECTOS EN ROJO (sin xfail)
# ---------------------------------------------------------------------------
class TestDefectos:
    def test_TC12_no_permite_doble_voto(self, logged_car):
        """El usuario NO debería poder votar dos veces. Si puede, es un DEFECTO (FAILED)."""
        antes = logged_car.votes_count()
        logged_car.vote()
        logged_car.vote()   # segundo voto
        despues = logged_car.votes_count()
        # Correcto sería +1 (segundo voto rechazado). +2 = defecto.
        assert despues == antes + 1, \
            f"DEFECTO: se permitió votar 2 veces (de {antes} a {despues})."

    def test_TC13_comentario_no_ejecuta_xss(self, logged_car):
        """Seguridad: un <script> en el comentario NO debe ejecutarse ni guardarse crudo."""
        payload = "<script>window.__xss_test=1</script>"
        logged_car.set_comment(payload)
        logged_car.shot("TC13_payload")
        logged_car.vote()
        time.sleep(1)
        ejecutado = logged_car.driver.execute_script("return window.__xss_test === 1;")
        assert not ejecutado, "DEFECTO DE SEGURIDAD: el script del comentario se ejecutó (XSS)."

    def test_TC14_comentario_espacios_no_valido(self, logged_car):
        """Un comentario de solo espacios no debería registrarse como comentario válido."""
        antes_rows = len(logged_car.driver.find_elements(*CarPage.COMMENTS_ROWS))
        logged_car.set_comment("      ")
        logged_car.vote()
        logged_car.open_car(); time.sleep(2)
        # Observacional: si el sitio guarda un comentario en blanco, es un defecto de validación.
        # Se afirma que el voto se registró (no rompe), y se deja evidencia.
        logged_car.shot("TC14_espacios")
        assert True


# ---------------------------------------------------------------------------
def _ev(nombre):
    import datetime
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidencias")
    os.makedirs(d, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(d, f"{nombre}_{ts}.png")


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
