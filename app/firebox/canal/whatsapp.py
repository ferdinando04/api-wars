"""Adaptador del canal WhatsApp (Meta Cloud API, Graph v25.0).

El resto del sistema solo usa esta interfaz; cambiar de proveedor no toca la conversación (FR-006).
"""
import httpx

from firebox.config import USER_AGENT, requerido


class ErrorWhatsApp(Exception):
    def __init__(self, estado: int, detalle):
        error = detalle.get("error", {}) if isinstance(detalle, dict) else {}
        self.codigo = error.get("code")
        super().__init__(f"WhatsApp respondió {estado} (código {self.codigo}): {error.get('message', detalle)}")
        self.estado = estado


class CanalWhatsApp:
    def __init__(self, base_url: str, version: str, phone_number_id: str, token: str):
        self._url = f"{base_url.rstrip('/')}/{version}/{phone_number_id}"
        self._http = httpx.Client(timeout=60, headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT})

    @classmethod
    def desde_entorno(cls) -> "CanalWhatsApp":
        return cls(requerido("META_GRAPH_BASE_URL"), requerido("META_GRAPH_API_VERSION"),
                   requerido("META_PHONE_NUMBER_ID"), requerido("META_ACCESS_TOKEN"))

    def _enviar(self, para: str, tipo: str, contenido: dict) -> str:
        r = self._http.post(f"{self._url}/messages", json={
            "messaging_product": "whatsapp", "recipient_type": "individual", "to": para, "type": tipo, tipo: contenido})
        if r.status_code >= 400:
            raise ErrorWhatsApp(r.status_code, r.json())
        return r.json()["messages"][0]["id"]

    def subir_medio(self, contenido: bytes, mime: str, nombre: str) -> str:
        r = self._http.post(f"{self._url}/media", data={"messaging_product": "whatsapp", "type": mime},
                            files={"file": (nombre, contenido, mime)})
        if r.status_code >= 400:
            raise ErrorWhatsApp(r.status_code, r.json())
        return r.json()["id"]

    def enviar_texto(self, para: str, texto: str) -> str:
        return self._enviar(para, "text", {"body": texto, "preview_url": False})

    def enviar_imagen(self, para: str, media_id: str, pie: str = "") -> str:
        return self._enviar(para, "image", {"id": media_id, "caption": pie})

    def enviar_documento(self, para: str, media_id: str, nombre_archivo: str, pie: str = "") -> str:
        return self._enviar(para, "document", {"id": media_id, "filename": nombre_archivo, "caption": pie})
