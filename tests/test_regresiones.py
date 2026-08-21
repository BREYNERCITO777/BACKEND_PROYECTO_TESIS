"""Fallos concretos que ya ocurrieron una vez.

Cada prueba de este archivo corresponde a un problema real detectado en el
sistema. Existen para que no vuelva a pasar en silencio.
"""
import base64
import time

from bson import ObjectId

from conftest import PREFIJO


def test_usuarios_devuelven_id_con_guion_bajo(cliente, admin):
    """UserOut declaraba un campo '_id', pero Pydantic v2 descarta en silencio
    los nombres que empiezan por guion bajo: los trata como atributos privados.

    La API devolvia solo 'id'. El frontend leia u._id sin alternativa, asi que
    obtenia cadena vacia y fallaban editar, cambiar rol, activar y eliminar
    usuarios, ademas de las protecciones sobre la propia cuenta.
    """
    r = cliente.get(f"{PREFIJO}/users", headers=admin)
    assert r.status_code == 200
    for usuario in r.json():
        assert "_id" in usuario, "UserOut volvio a perder el campo _id"
        assert usuario["_id"] == usuario["id"]


def test_la_evidencia_del_agente_persiste_en_la_base(cliente, agente, db):
    """La evidencia guardada como archivo desaparece al redesplegar: el
    sistema de archivos del contenedor se descarta. Habia incidentes en Mongo
    apuntando a imagenes inexistentes.

    La copia en base64 vive en la base de datos y sobrevive.
    """
    time.sleep(5.5)
    r = cliente.post(f"{PREFIJO}/agent/detections", headers=agente, json={
        "camera_id": "cam-persistencia",
        "camera_name": "Camara de pruebas",
        "type": "arma_fuego",
        "confidence": 0.93,
        "source": "pruebas",
        "image_base64": base64.b64encode(b"contenido-de-la-evidencia").decode(),
    })
    assert r.status_code == 200

    inc = db["incidents"].find_one({"_id": ObjectId(r.json()["incident_id"])})
    assert inc.get("image_base64"), "La evidencia no quedo guardada en la base"
    assert inc.get("evidence_type") == "base64"


def test_las_alertas_se_enlazan_con_su_incidente(cliente, agente, db):
    """Una alerta sin incident_id queda huerfana: el operador ve el aviso pero
    no puede llegar al incidente ni a su evidencia. El endpoint del agente si
    los enlazaba; el de deteccion por foto no lo hacia.
    """
    time.sleep(5.5)
    r = cliente.post(f"{PREFIJO}/agent/detections", headers=agente, json={
        "camera_id": "cam-enlace",
        "camera_name": "Camara de pruebas",
        "type": "arma_blanca",
        "confidence": 0.91,
        "source": "pruebas",
    })
    assert r.status_code == 200
    cuerpo = r.json()

    alerta = db["alerts"].find_one({"_id": ObjectId(cuerpo["alert_id"])})
    assert alerta.get("incident_id") == cuerpo["incident_id"], \
        "La alerta no apunta a su incidente"


def test_las_credenciales_rtsp_se_guardan_cifradas(cliente, admin, db):
    """Las URL de camara llevan usuario y contrasena. Se guardaban en texto
    plano, visibles para cualquiera con acceso a la base o a un respaldo.
    """
    url = f"rtsp://usuario:clave-secreta@10.0.0.99:554/canal-{int(time.time())}"
    r = cliente.post(f"{PREFIJO}/cameras", headers=admin,
                     json={"name": f"Camara cifrado {int(time.time())}", "rtsp_url": url})
    assert r.status_code == 201
    cam_id = r.json()["_id"]

    try:
        crudo = db["cameras"].find_one({"_id": ObjectId(cam_id)})
        assert crudo["rtsp_url"].startswith("enc:v1:"), "La URL no quedo cifrada"
        assert "clave-secreta" not in str(crudo), "La contrasena aparece en la base"

        # La API tampoco debe exponerla
        listado = cliente.get(f"{PREFIJO}/cameras", headers=admin).json()
        assert "clave-secreta" not in str(listado)
        cam = next(c for c in listado if c["_id"] == cam_id)
        assert "***" in cam["rtsp_url"], "La URL deberia mostrarse enmascarada"
    finally:
        cliente.delete(f"{PREFIJO}/cameras/{cam_id}", headers=admin)


def test_el_indice_unico_detecta_camaras_duplicadas(cliente, admin):
    """El cifrado no es determinista: dos cifrados de la misma URL son
    distintos. Un indice unico sobre el texto cifrado nunca detectaria un
    duplicado, por eso el indice va sobre una huella estable.
    """
    url = f"rtsp://u:c@10.0.0.98:554/dup-{int(time.time())}"
    nombre = f"Camara dup {int(time.time())}"
    r1 = cliente.post(f"{PREFIJO}/cameras", headers=admin,
                      json={"name": nombre, "rtsp_url": url})
    assert r1.status_code == 201
    try:
        r2 = cliente.post(f"{PREFIJO}/cameras", headers=admin,
                          json={"name": nombre + " bis", "rtsp_url": url})
        assert r2.status_code == 409, "Se acepto una camara con la misma URL"
    finally:
        cliente.delete(f"{PREFIJO}/cameras/{r1.json()['_id']}", headers=admin)


def test_email_notifications_esta_documentado_como_no_implementado(cliente):
    """El panel ofrecia un interruptor de notificaciones por correo, pero no
    existe ninguna linea que envie un email. Si el jurado lo activa esperando
    que funcione, no ocurre nada.
    """
    esquema = cliente.get("/openapi.json").json()
    campo = esquema["components"]["schemas"]["SettingsOut"]["properties"]["email_notifications"]
    assert "NO IMPLEMENTADO" in campo.get("description", "")


def test_un_solo_umbral_gobierna_todo_el_sistema(cliente, admin, agente):
    """Habia tres umbrales distintos conviviendo: 0.5 en la configuracion,
    0.70 escrito en inference.py y el del panel. Mover el control del panel no
    afectaba a la inferencia interna.
    """
    cliente.patch(f"{PREFIJO}/settings",
                  json={"confidence_threshold": 0.80}, headers=admin)
    time.sleep(5.5)

    r = cliente.post(f"{PREFIJO}/agent/detections", headers=agente, json={
        "camera_id": "cam-umbral-unico", "camera_name": "X",
        "type": "arma_fuego", "confidence": 0.70, "source": "pruebas",
    })
    assert r.json()["umbral"] == 0.80, "El agente no lee el umbral del panel"

    cliente.patch(f"{PREFIJO}/settings",
                  json={"confidence_threshold": 0.65}, headers=admin)


def test_los_indices_de_mongo_existen(db):
    """Los indices unicos son la ultima defensa contra datos duplicados."""
    indices_usuarios = db["users"].index_information()
    assert any(i.get("key") == [("email", 1)] and i.get("unique")
               for i in indices_usuarios.values()), "Falta el indice unico de email"

    indices_camaras = db["cameras"].index_information()
    assert any(i.get("key") == [("rtsp_hash", 1)] and i.get("unique")
               for i in indices_camaras.values()), "Falta el indice unico de camaras"
