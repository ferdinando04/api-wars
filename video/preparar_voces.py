"""Prepara las voces del video pitch → src/firebox/voces.json del proyecto Remotion.

Modo real (cuando David y Dylan mandan sus audios a video/voces/, uno por escena: E1_david.m4a, E2_dylan.ogg…):
  1. ffmpeg: a WAV 48 kHz mono, quita el silencio del principio y del final (deja 0,15 s), nivela a −16 LUFS por escena
     (dos voces distintas: nivelar cada escena por separado, no el audio unido).
  2. faster-whisper (small, español) con tiempo por palabra.
  3. Escribe voces.json con: audio, duración, narrador, texto del libreto, texto oído y palabras con su segundo.
Modo provisional (--provisional): sin audio; tiempos estimados desde el libreto para construir y revisar el video antes.

Uso:  python video/preparar_voces.py --provisional
      python video/preparar_voces.py
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
REMOTION = Path(r"C:\Users\FERNANDO VEGA\Desktop\proyecto-video-ai")
FFMPEG = r"C:\Users\FERNANDO VEGA\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffmpeg.exe"
VOCES = RAIZ / "video" / "voces"
SALIDA_AUDIO = REMOTION / "public" / "firebox" / "voces"
JSON = REMOTION / "src" / "firebox" / "voces.json"


def libretos() -> dict[str, dict]:
    escenas, actual = {}, None
    for linea in (RAIZ / "video" / "LIBRETOS.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"## (E\d+b?) - (\w+) \(\d+ s\) · (.+)", linea)
        if m:
            actual = m.group(1)
            escenas[actual] = {"narrador": m.group(2), "titulo": m.group(3), "guion": ""}
        elif actual and linea.startswith(">"):
            texto = linea.lstrip("> ").strip()
            if texto:
                escenas[actual]["guion"] += (" " if escenas[actual]["guion"] else "") + texto.replace("**", "")
    return escenas


VEXON_ENV = Path(r"C:\Users\FERNANDO VEGA\Desktop\vexon-project\.env")
CACHE = RAIZ / "video" / "voces" / "_cache_elevenlabs"


def voz_clonada(k: str, texto: str) -> dict:
    """Escena narrada con la voz clonada de Fernando (ElevenLabs IVC). Devuelve audio + palabras con su segundo (alineación de
    ElevenLabs). Caché por texto: regenerar no vuelve a gastar caracteres. La llave se LEE del .env de Vexon y no se imprime."""
    import base64
    import hashlib
    import httpx
    env = dict(l.split("=", 1) for l in VEXON_ENV.read_text(encoding="utf-8").splitlines() if "=" in l and not l.startswith("#"))
    clave, voz = env["ELEVENLABS_API_KEY_VOCES"].strip(), env["ELEVENLABS_VOICE_FERNANDO_IVC"].strip()
    CACHE.mkdir(parents=True, exist_ok=True)
    sha = hashlib.sha256(f"{voz}|{texto}".encode()).hexdigest()[:16]
    guardado = CACHE / f"{k}_{sha}.json"
    if guardado.exists():
        r = json.loads(guardado.read_text(encoding="utf-8"))
    else:
        resp = httpx.post(f"https://api.elevenlabs.io/v1/text-to-speech/{voz}/with-timestamps?output_format=mp3_44100_128",
                          headers={"xi-api-key": clave}, timeout=120,
                          json={"text": texto, "model_id": "eleven_multilingual_v2",
                                "voice_settings": {"stability": 0.45, "similarity_boost": 0.85, "style": 0.15, "use_speaker_boost": True}})
        if resp.status_code != 200:
            raise SystemExit(f"ElevenLabs respondió {resp.status_code}: {resp.text[:200]}")
        r = resp.json()
        guardado.write_text(json.dumps(r), encoding="utf-8")
    SALIDA_AUDIO.mkdir(parents=True, exist_ok=True)
    mp3 = CACHE / f"{k}_{sha}.mp3"
    mp3.write_bytes(base64.b64decode(r["audio_base64"]))
    wav = SALIDA_AUDIO / f"{k}.wav"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(mp3), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", "-ac", "1",
                    str(wav)], check=True)
    al = r["alignment"]
    palabras, actual, t0 = [], "", None
    for ch, a, b in zip(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]):
        if ch.isspace():
            if actual:
                palabras.append({"w": actual, "t0": round(t0, 3), "t1": round(fin, 3)})
            actual, t0 = "", None
            continue
        if t0 is None:
            t0 = a
        actual, fin = actual + ch, b
    if actual:
        palabras.append({"w": actual, "t0": round(t0, 3), "t1": round(fin, 3)})
    duracion = al["character_end_times_seconds"][-1] + 0.2
    print(f"{k} (Fernando, voz clonada): {duracion:5.1f} s · {len(palabras)} palabras · {len(texto)} caracteres")
    return {"audio": f"firebox/voces/{k}.wav", "duracion": round(duracion, 3), "texto": texto, "palabras": palabras, "provisional": False}


def provisional(escenas: dict) -> dict:
    datos = {}
    for k, e in escenas.items():
        if e["narrador"] == "Fernando":
            datos[k] = {**e, **voz_clonada(k, e["guion"])}
            continue
        t, palabras = 0.25, []
        for w in e["guion"].split():
            dur = 0.30 + 0.022 * len(w)
            palabras.append({"w": w, "t0": round(t, 3), "t1": round(t + dur, 3)})
            t += dur + 0.06 + (0.45 if re.search(r"[.…!?]$", w) else 0.22 if re.search(r"[,:;]$", w) else 0)
        datos[k] = {**e, "audio": None, "duracion": round(t + 0.3, 3), "texto": e["guion"], "palabras": palabras, "provisional": True}
    return datos


def transcribir(wav: Path, pista: str) -> tuple[list[dict], float]:
    """Whisper large-v3 en la nube (Groq) con tiempo por palabra: no carga el PC. La llave se LEE del .env de Vexon."""
    import httpx
    env = dict(l.split("=", 1) for l in VEXON_ENV.read_text(encoding="utf-8").splitlines() if "=" in l and not l.startswith("#"))
    liviano = wav.with_suffix(".16k.wav")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(wav), "-ar", "16000", "-ac", "1", str(liviano)], check=True)
    with open(liviano, "rb") as f:
        r = httpx.post("https://api.groq.com/openai/v1/audio/transcriptions", timeout=180,
                       headers={"Authorization": "Bearer " + env["GROQ_API_KEY"].strip()},
                       files={"file": (liviano.name, f, "audio/wav")},
                       data={"model": "whisper-large-v3", "language": "es", "response_format": "verbose_json",
                             "timestamp_granularities[]": "word"})
    liviano.unlink(missing_ok=True)
    if r.status_code != 200:
        raise SystemExit(f"Groq respondió {r.status_code}: {r.text[:200]}")
    j = r.json()
    palabras = [{"w": w["word"].strip(), "t0": round(w["start"], 3), "t1": round(w["end"], 3)} for w in j.get("words", [])]
    return palabras, float(j.get("duration", palabras[-1]["t1"] if palabras else 0))


# Whisper no conoce las marcas del proyecto: se corrige la PALABRA (el tiempo queda igual). Medido el 06-oct con los audios de Dylan.
CORRECCIONES = {"firebots": "Firebox", "faribots": "Firebox", "firebox": "Firebox", "fatus": "Factus", "factus": "Factus",
                "aut": "OAuth", "caf": "CUFE", "cufe": "CUFE", "cms": "SMS", "validante": "validada", "breve": "Bre-B",
                "rondo": "redondeo", "arramamos": "armamos", "bills": "bills", "validate": "validate",
                "happywars": "API WARS", "factospay": "Factus Pay", "factos": "Factus"}
CONTEXTO = [(("validada", "a"), 1, "ante"), (("la", "app", "oficial"), 1, "API"), (("en", "la", "app", "oficial"), 2, "API"),
            (("para", "curar", "un"), 1, "cobrar"), (("para", "cobrar", "un"), 2, "con")]
# Frases que el narrador dijo y no van: se cortan del audio y se corren las palabras siguientes.
# E9: David dijo «y un panel para el vendedor» como algo futuro, justo después de la escena que muestra el panel funcionando.
CORTES = {"E9": ["y un panel para el vendedor"]}


def corregir(palabras: list[dict]) -> list[dict]:
    limpia = lambda w: re.sub(r"[^\wáéíóúñü.-]", "", w.lower()).strip(".")
    out = []
    for p in palabras:
        m = re.match(r"^([¿¡\"(]*)(.*?)([.,:;!?…\")]*)$", p["w"])
        pre, nucleo, post = m.groups() if m else ("", p["w"], "")
        nuevo = CORRECCIONES.get(nucleo.lower(), nucleo)
        out.append({**p, "w": f"{pre}{nuevo}{post}"})
    for i in range(1, len(out)):  # mayúscula después de punto (Whisper a veces la pierde)
        if re.search(r"[.!?]$", out[i - 1]["w"]) and out[i]["w"][:1].islower():
            out[i]["w"] = out[i]["w"][:1].upper() + out[i]["w"][1:]
    for patron, idx, reemplazo in CONTEXTO:
        n = len(patron)
        for i in range(len(out) - n + 1):
            if tuple(limpia(out[i + j]["w"]) for j in range(n)) == patron:
                w = out[i + idx]["w"]
                out[i + idx]["w"] = re.sub(r"[\wáéíóúñ]+", reemplazo, w, count=1)
    return out


def recortar_despedida(wav: Path, palabras: list[dict], guion: str) -> tuple[list[dict], float | None]:
    """Si el narrador agregó un «Gracias» al final y su libreto no lo tiene, se corta del audio (el cierre es de otra escena)."""
    if not palabras or re.search(r"gracias", guion, re.I):
        return palabras, None
    ultimo = re.sub(r"[^\w]", "", palabras[-1]["w"].lower())
    if ultimo != "gracias" or len(palabras) < 2:
        return palabras, None
    corte = round(palabras[-2]["t1"] + 0.35, 3)
    tmp = wav.with_suffix(".tmp.wav")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(wav), "-t", str(corte), "-af", f"afade=t=out:st={corte - 0.15}:d=0.15",
                    str(tmp)], check=True)
    tmp.replace(wav)
    return palabras[:-1], corte


def cortar_frase(wav: Path, palabras: list[dict], frase: str) -> tuple[list[dict], float]:
    """Quita `frase` del audio (de la pausa antes a la pausa después) y corre las palabras siguientes. Devuelve los segundos quitados.
    La puntuación final de la frase quitada pasa a la palabra anterior («número» → «número.»)."""
    limpia = lambda w: re.sub(r"[^\wáéíóúñü]", "", w.lower())
    obj = [limpia(w) for w in frase.split()]
    n = len(obj)
    for i in range(1, len(palabras) - n):
        if [limpia(palabras[i + j]["w"]) for j in range(n)] == obj:
            antes, despues = palabras[i - 1], palabras[i + n]
            a, b = round(antes["t1"] + 0.10, 3), round(despues["t0"] - 0.10, 3)
            tmp = wav.with_suffix(".tmp.wav")
            subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(wav), "-af",
                            f"aselect='not(between(t\\,{a}\\,{b}))',asetpts=N/SR/TB", str(tmp)], check=True)
            tmp.replace(wav)
            quitado = round(b - a, 3)
            punto = re.search(r"[.,:;!?…]+$", palabras[i + n - 1]["w"])
            nuevas = palabras[:i]
            if punto and not re.search(r"[.,:;!?…]$", nuevas[-1]["w"]):
                nuevas[-1] = {**nuevas[-1], "w": nuevas[-1]["w"] + punto.group(0)}
            nuevas += [{**p, "t0": round(p["t0"] - quitado, 3), "t1": round(p["t1"] - quitado, 3)} for p in palabras[i + n:]]
            if re.search(r"[.!?]$", nuevas[i - 1]["w"]) and nuevas[i]["w"][:1].islower():
                nuevas[i]["w"] = nuevas[i]["w"][:1].upper() + nuevas[i]["w"][1:]
            return nuevas, quitado
    raise SystemExit(f"No encontré «{frase}» en la transcripción: no se cortó nada (revisar el audio)")


def real(escenas: dict, mixto: bool = False) -> dict:
    SALIDA_AUDIO.mkdir(parents=True, exist_ok=True)
    datos = {}
    for k, e in escenas.items():
        if e["narrador"] == "Fernando":
            datos[k] = {**e, **voz_clonada(k, e["guion"])}
            continue
        fuentes = sorted(p for p in VOCES.glob(f"{k}_*.*") if p.is_file())
        if not fuentes:
            if mixto:
                datos[k] = provisional({k: e})[k]
                print(f"{k} ({e['narrador']}): sin audio todavía → tiempos provisionales")
                continue
            raise SystemExit(f"Falta el audio de {k} ({e['narrador']}) en {VOCES}")
        wav = SALIDA_AUDIO / f"{k}.wav"
        filtro = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.15,"
                  "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.15,areverse,"
                  "highpass=f=80,loudnorm=I=-16:TP=-1.5:LRA=11")
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(fuentes[-1]), "-af", filtro, "-ar", "48000", "-ac", "1", str(wav)],
                       check=True)
        palabras, duracion = transcribir(wav, e["guion"])
        palabras = corregir(palabras)
        palabras, corte = recortar_despedida(wav, palabras, e["guion"])
        if corte:
            duracion = corte
            print(f"   {k}: se recortó un «Gracias» final que no está en el libreto (audio hasta {corte} s)")
        for frase in CORTES.get(k, []):
            palabras, quitado = cortar_frase(wav, palabras, frase)
            duracion = round(duracion - quitado, 3)
            print(f"   {k}: se cortó «{frase}» ({quitado} s)")
        datos[k] = {**e, "audio": f"firebox/voces/{k}.wav", "duracion": round(duracion, 3),
                    "texto": " ".join(p["w"] for p in palabras), "palabras": palabras, "provisional": False}
        print(f"{k} ({e['narrador']}): {duracion:5.1f} s · {len(palabras)} palabras · fuente {fuentes[-1].name}")
    return datos


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--provisional", action="store_true")
    a.add_argument("--mixto", action="store_true", help="usa los audios que ya llegaron y tiempos provisionales para los que faltan")
    args = a.parse_args()
    escenas = libretos()
    datos = provisional(escenas) if args.provisional else real(escenas, mixto=args.mixto)
    JSON.parent.mkdir(parents=True, exist_ok=True)
    JSON.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(d["duracion"] for d in datos.values())
    print(f"voces.json: {len(datos)} escenas · {total:.1f} s de voz · {'PROVISIONAL' if args.provisional else 'REAL'}")
