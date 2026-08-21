"""Autenticación y control de acceso por rol."""
from conftest import PREFIJO


class TestInicioSesion:
    def test_credenciales_correctas(self, cliente):
        r = cliente.post(f"{PREFIJO}/auth/login",
                         data={"username": "admin@example.com", "password": "Admin123!"})
        assert r.status_code == 200
        assert r.json().get("access_token")

    def test_password_incorrecta(self, cliente):
        r = cliente.post(f"{PREFIJO}/auth/login",
                         data={"username": "admin@example.com", "password": "equivocada"})
        assert r.status_code == 401

    def test_usuario_inexistente(self, cliente):
        r = cliente.post(f"{PREFIJO}/auth/login",
                         data={"username": "nadie@example.com", "password": "x"})
        assert r.status_code == 401

    def test_no_filtra_el_hash_de_la_password(self, cliente, admin):
        r = cliente.get(f"{PREFIJO}/auth/me", headers=admin)
        assert r.status_code == 200
        assert "password_hash" not in r.text

    def test_token_invalido(self, cliente):
        r = cliente.get(f"{PREFIJO}/auth/me",
                        headers={"Authorization": "Bearer esto-no-es-un-token"})
        assert r.status_code == 401

    def test_modulos_segun_rol(self, cliente):
        """El backend decide qué módulos ve cada rol; el frontend solo obedece."""
        r = cliente.post(f"{PREFIJO}/auth/login",
                         data={"username": "admin@example.com", "password": "Admin123!"})
        assert "users" in r.json()["allowed_modules"]

        r = cliente.post(f"{PREFIJO}/auth/login",
                         data={"username": "operador@example.com", "password": "Oper123!"})
        assert "users" not in r.json()["allowed_modules"]
        assert "settings" not in r.json()["allowed_modules"]


class TestControlDeAcceso:
    """El operador no debe poder hacer lo que es exclusivo del admin.

    Se comprueba en el backend, no en la interfaz: aunque alguien manipule el
    navegador, el servidor tiene que negarse igual.
    """

    def test_sin_token_no_se_entra(self, cliente):
        assert cliente.get(f"{PREFIJO}/users").status_code == 401

    def test_operador_no_lista_usuarios(self, cliente, operador):
        assert cliente.get(f"{PREFIJO}/users", headers=operador).status_code == 403

    def test_operador_no_modifica_configuracion(self, cliente, operador):
        r = cliente.patch(f"{PREFIJO}/settings",
                          json={"confidence_threshold": 0.5}, headers=operador)
        assert r.status_code == 403

    def test_operador_no_borra_incidentes(self, cliente, operador):
        r = cliente.delete(f"{PREFIJO}/incidents/000000000000000000000000",
                           headers=operador)
        assert r.status_code == 403

    def test_operador_no_registra_camaras(self, cliente, operador):
        r = cliente.post(f"{PREFIJO}/cameras", headers=operador,
                         json={"name": "X", "rtsp_url": "rtsp://x/y"})
        assert r.status_code == 403

    def test_operador_si_consulta_incidentes(self, cliente, operador):
        assert cliente.get(f"{PREFIJO}/incidents", headers=operador).status_code == 200

    def test_operador_si_consulta_configuracion(self, cliente, operador):
        assert cliente.get(f"{PREFIJO}/settings", headers=operador).status_code == 200

    def test_admin_si_lista_usuarios(self, cliente, admin):
        assert cliente.get(f"{PREFIJO}/users", headers=admin).status_code == 200
