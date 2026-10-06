import httpx

from firebox.pagos.factus_pay import ClienteFactusPay


class FactusPaySimulado:
    """Imita lo medido el 06-oct-2026: cada POST /auth emite un token nuevo e INVALIDA el anterior."""

    def __init__(self):
        self.vigente = None
        self.emitidos = 0

    def __call__(self, req: httpx.Request) -> httpx.Response:
        if req.url.path == "/auth":
            self.emitidos += 1
            self.vigente = f"token-{self.emitidos}"
            return httpx.Response(200, json={"token": self.vigente})
        if req.headers.get("Authorization") != f"Bearer {self.vigente}":
            return httpx.Response(401, json={"message": "Unauthenticated."})
        return httpx.Response(200, json={"data": [{"reference_code": "SETP1", "amount": 10000, "status": "ready"}]})


def test_otra_sesion_invalida_el_token_y_el_cliente_se_recupera_solo():
    servidor = FactusPaySimulado()
    http = httpx.Client(transport=httpx.MockTransport(servidor), base_url="https://pay.test")
    panel = ClienteFactusPay("https://pay.test", "c@x.co", "clave", http=http)
    assert len(panel.listar()) == 1                      # sesión 1
    servidor.vigente = "token-de-otra-sesion"            # el vigilante o un compañero inició otra sesión
    assert len(panel.listar()) == 1                      # 401 → re-autentica una vez → funciona
    assert servidor.emitidos == 2
