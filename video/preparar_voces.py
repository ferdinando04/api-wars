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
        m = re.match(r"## (E\d) - (\w+) \(\d+ s\) · (.+)", linea)
        if m:
            actual = m.group(1)
            escenas[actual] = {"narrador": m.group(2), "titulo": m.group(3), "guion": ""}
        elif actual and linea.startswith(">"):
            texto = linea.lstrip("> ").strip()
            if texto:
                escenas[actual]["guion"] += (" " if escenas[actual]["guion"] else "") + texto.replace("**", "")
    return escenas


def provisional(escenas: dict) -> dict:
    datos = {}
    for k, e in escenas.items():
        t, palabras = 0.25, []
        for w in e["guion"].split():
            dur = 0.30 + 0.022 * len(w)
            palabras.append({"w": w, "t0": round(t, 3), "t1": round(t + dur, 3)})
            t += dur + 0.06 + (0.45 if re.search(r"[.…!?]$", w) else 0.22 if re.search(r"[,:;]$", w) else 0)
        datos[k] = {**e, "audio": None, "duracion": round(t + 0.3, 3), "texto": e["guion"], "palabras": palabras, "provisional": True}
    return datos


def real(escenas: dict) -> dict:
    from faster_whisper import WhisperModel
    modelo = WhisperModel("small", device="cpu", compute_type="int8")
    SALIDA_AUDIO.mkdir(parents=True, exist_ok=True)
    datos = {}
    for k, e in escenas.items():
        fuentes = sorted(VOCES.glob(f"{k}_*.*"))
        if not fuentes:
            raise SystemExit(f"Falta el audio de {k} ({e['narrador']}) en {VOCES}")
        wav = SALIDA_AUDIO / f"{k}.wav"
        filtro = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.15,"
                  "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.15,areverse,"
                  "highpass=f=80,loudnorm=I=-16:TP=-1.5:LRA=11")
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(fuentes[-1]), "-af", filtro, "-ar", "48000", "-ac", "1", str(wav)],
                       check=True)
        segmentos, info = modelo.transcribe(str(wav), language="es", word_timestamps=True, beam_size=5,
                                            initial_prompt=e["guion"][:220])
        palabras = [{"w": p.word.strip(), "t0": round(p.start, 3), "t1": round(p.end, 3)} for s in segmentos for p in s.words]
        datos[k] = {**e, "audio": f"firebox/voces/{k}.wav", "duracion": round(info.duration, 3),
                    "texto": " ".join(p["w"] for p in palabras), "palabras": palabras, "provisional": False}
        print(f"{k} ({e['narrador']}): {info.duration:5.1f} s · {len(palabras)} palabras · fuente {fuentes[-1].name}")
    return datos


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--provisional", action="store_true")
    args = a.parse_args()
    escenas = libretos()
    datos = provisional(escenas) if args.provisional else real(escenas)
    JSON.parent.mkdir(parents=True, exist_ok=True)
    JSON.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(d["duracion"] for d in datos.values())
    print(f"voces.json: {len(datos)} escenas · {total:.1f} s de voz · {'PROVISIONAL' if args.provisional else 'REAL'}")
