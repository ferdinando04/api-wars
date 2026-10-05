"""Lee el .env de la raíz del repositorio. Los secretos nunca se imprimen ni se devuelven."""
from functools import lru_cache
from pathlib import Path

RAIZ_REPO = Path(__file__).resolve().parents[2]
USER_AGENT = "Firebox/1.0"  # Factus exige un User-Agent propio: sin él Cloudflare responde 403 (medido 05-oct-2026)


@lru_cache
def entorno() -> dict[str, str]:
    valores: dict[str, str] = {}
    archivo = RAIZ_REPO / ".env"
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            if "=" in linea and not linea.lstrip().startswith("#"):
                clave, valor = linea.split("=", 1)
                valores[clave.strip()] = valor.strip().strip('"').strip("'")
    return valores


def requerido(clave: str) -> str:
    valor = entorno().get(clave, "")
    if not valor:
        raise RuntimeError(f"Falta {clave} en el .env")
    return valor
