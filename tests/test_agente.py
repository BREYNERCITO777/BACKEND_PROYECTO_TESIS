"""Endpoint que recibe las detecciones del agente local.

Es el camino crítico del sistema: si esto falla, la municipalidad deja de
registrar detecciones.
"""
import base64
import time

import pytest

from conftest import PREFIJO


def deteccion(camera_id="cam-pruebas", tipo="arma_fuego", conf=0.93, **extra):
    cuerpo = {
        "camera_id": camera_id,
        "camera_name": "Camara de pruebas",
        "type": tipo,
        "confidence": conf,
        "timestamp": "2026-08-21T10:00:00+00:00",
        "source": "pruebas-automatizadas",
        "image_base64": base64.b64encode(b"imagen-de-prueba").decode(),
    }
    cuerpo.update(extra)
    return cuerpo


class TestAutenticacionDelAgente:
    def test_sin_cabecera(self, cliente):
        assert cliente.post(f"{PREFIJO}/agent/detections",
                            json=deteccion()).status_code == 401

    def test_token_equivocado(self, cliente):
        r = cliente.post(f"{PREFIJO}/agent/detections", json=deteccion(),
                         headers={"Authorization": "Bearer token-malo"})
        assert r.status_code == 401

    def test_el_token_publicado_ya_no_sirve(self, cliente):
        """Estuvo escrito en el codigo y llego a GitHub; no debe funcionar."""
        r = cliente.post(f"{PREFIJO}/agent/detections", json=deteccion(),
                         headers={"Authorization": "Bearer SentinelLocalAgent2026_MPSM"})
        assert r.status_code == 401

    def test_un_jwt_de_usuario_no_sirve(self, cliente, admin):
        """El agente es una maquina: usa token compartido, no sesion de usuario."""
        r = cliente.post(f"{PREFIJO}/agent/detections", json=deteccion(), headers=admin)
        assert r.status_code == 401


class TestValidacionDeDatos:
    """Antes solo se comprobaba el token: cualquier payload con la forma
    correcta se convertia en incidente y alerta."""

    @pytest.mark.parametrize("caso,cuerpo", [
        ("confianza mayor que 1", deteccion(conf=1.5)),
        ("confianza negativa", deteccion(conf=-0.1)),
        ("confianza como porcentaje", deteccion(conf=93)),
        ("fecha que no es ISO", deteccion(timestamp="ayer")),
        ("base64 corrupto", deteccion(image_base64="%%%")),
        ("camara sin identificar", deteccion(camera_id="")),
        ("tipo vacio", deteccion(tipo="")),
    ])
    def test_payloads_invalidos(self, cliente, agente, caso, cuerpo):
        r = cliente.post(f"{PREFIJO}/agent/detections", json=cuerpo, headers=agente)
        assert r.status_code == 422, f"{caso} deberia rechazarse"

    def test_evidencia_demasiado_grande(self, cliente, agente):
        """Mongo rechaza documentos de mas de 16 MB."""
        enorme = base64.b64encode(b"x" * (5 * 1024 * 1024)).decode()
        r = cliente.post(f"{PREFIJO}/agent/detections",
                         json=deteccion(image_base64=enorme), headers=agente)
        assert r.status_code == 422

    def test_fecha_con_sufijo_z(self, cliente, agente):
        """datetime.fromisoformat de Python 3.9 no acepta la Z; debe tratarse."""
        r = cliente.post(f"{PREFIJO}/agent/detections",
                         json=deteccion(camera_id="cam-z",
                                        timestamp="2026-08-21T10:00:00Z"),
                         headers=agente)
        assert r.status_code == 200


class TestFlujoCompleto:
    def test_deteccion_crea_incidente_y_alerta(self, cliente, agente, admin, db):
        cliente.patch(f"{PREFIJO}/settings",
                      json={"confidence_threshold": 0.65}, headers=admin)

        antes_i = db["incidents"].count_documents({})
        antes_a = db["alerts"].count_documents({})

        r = cliente.post(f"{PREFIJO}/agent/detections",
                         json=deteccion(camera_id="cam-flujo"), headers=agente)
        assert r.status_code == 200
        cuerpo = r.json()
        assert cuerpo["ignorada"] is False
        assert cuerpo["incident_id"] and cuerpo["alert_id"]

        assert db["incidents"].count_documents({}) == antes_i + 1
        assert db["alerts"].count_documents({}) == antes_a + 1

        inc = db["incidents"].find_one({"camera_id": "cam-flujo"})
        assert inc["weapon_type"] == "arma_fuego"
        assert inc["status"] == "new"
        assert inc["evidence_type"] == "base64"
        # La hora es la de la deteccion, no la de recepcion
        assert inc["timestamp"].startswith("2026-08-21T10:00")
        assert inc["created_at"] != inc["timestamp"]

    def test_camara_no_registrada_queda_marcada(self, cliente, agente):
        time.sleep(5.5)   # cooldown del backend
        r = cliente.post(f"{PREFIJO}/agent/detections",
                         json=deteccion(camera_id="camara-que-no-existe"),
                         headers=agente)
        assert r.status_code == 200
        assert r.json()["camera_registered"] is False


class TestUmbralYCooldown:
    def test_por_debajo_del_umbral_se_descarta(self, cliente, agente, admin, db):
        cliente.patch(f"{PREFIJO}/settings",
                      json={"confidence_threshold": 0.90}, headers=admin)
        time.sleep(5.5)

        antes = db["incidents"].count_documents({})
        r = cliente.post(f"{PREFIJO}/agent/detections",
                         json=deteccion(camera_id="cam-umbral", conf=0.55),
                         headers=agente)

        assert r.status_code == 200          # no es un error: se acepta y se descarta
        assert r.json()["ignorada"] is True
        assert r.json()["motivo"] == "confianza_bajo_umbral"
        assert db["incidents"].count_documents({}) == antes

        cliente.patch(f"{PREFIJO}/settings",
                      json={"confidence_threshold": 0.65}, headers=admin)

    def test_cooldown_evita_la_avalancha(self, cliente, agente, db):
        """Un agente detectando a 10 fps generaria 10 incidentes por segundo."""
        time.sleep(5.5)
        primera = cliente.post(f"{PREFIJO}/agent/detections",
                               json=deteccion(camera_id="cam-avalancha"), headers=agente)
        assert primera.json()["ignorada"] is False

        antes = db["incidents"].count_documents({})
        for _ in range(8):
            r = cliente.post(f"{PREFIJO}/agent/detections",
                             json=deteccion(camera_id="cam-avalancha"), headers=agente)
            assert r.json()["ignorada"] is True
            assert r.json()["motivo"] == "cooldown_activo"

        assert db["incidents"].count_documents({}) == antes

    def test_el_cooldown_es_por_camara(self, cliente, agente):
        """Silenciar una camara no debe silenciar las demas."""
        cliente.post(f"{PREFIJO}/agent/detections",
                     json=deteccion(camera_id="cam-a"), headers=agente)
        r = cliente.post(f"{PREFIJO}/agent/detections",
                         json=deteccion(camera_id="cam-b"), headers=agente)
        assert r.json()["ignorada"] is False
