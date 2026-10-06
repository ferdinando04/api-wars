// Video pitch de Firebox (API WARS 2026). Narran David y Dylan con su propia voz; cada cosa aparece en el segundo en que la nombran.
// Datos: voces.json (preparar_voces.py: tiempo por palabra con Whisper) y codigo.json (preparar_material.py: código REAL del repo).
import React from "react";
import {AbsoluteFill, Audio, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from "remotion";
import {F_MONO, F_TEXTO, F_TITULO, Palabra} from "../vexon/base";
import voces from "./voces.json";
import codigo from "./codigo.json";
import recorrido from "./panel_recorrido.json";

// ---------- paleta (la de la presentación de David) ----------
export const K = {
  crema: "#F5F0E8", papel: "#FFFDF9", tinta: "#13241D", verde: "#0F3D2E", coral: "#E8613C", coralSuave: "#F8D3C3",
  verdeClaro: "#CFE8B9", gris: "#5E6B64", linea: "#E3DACD", codFondo: "#0D1915", codTexto: "#E4ECE8",
};

type Voz = {narrador: string; titulo: string; guion: string; audio: string | null; duracion: number; palabras: Palabra[]};
type Trozo = {archivo: string; desde: number; lineas: string[]};
const V = voces as unknown as Record<string, Voz>;
const COD = codigo as unknown as Record<string, Trozo> & {evidencia: string[]; control_negativo: {sano: string; roto: string[]; restaurado: string}};

const ORDEN = ["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E8b", "E9"].filter((k) => V[k]);
const INTRO = 3.4;
const GAP = 0.6;
const OUTRO = 7;
const INI: Record<string, number> = {};
let _t = INTRO;
for (const k of ORDEN) {
  INI[k] = _t;
  _t += V[k].duracion + GAP;
}
const FIN_VOZ = _t;
export const DURACION_FIREBOX = FIN_VOZ + OUTRO;
const fin = (k: string) => INI[k] + V[k].duracion;

// Integrantes para los créditos (nombres completos que dieron en el grupo del equipo el 6-oct)
const EQUIPO = ["Juan David Vargas Aparicio", "Dylan Gerhard Arce Triviño", "Fernando Vega Benavides"];

// ---------- tiempo ----------
const useT = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return {t: frame / fps, frame, fps};
};
const clamp = {extrapolateLeft: "clamp", extrapolateRight: "clamp"} as const;
const quita = (s: string) => s.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9ñ ]/g, " ");

/** Segundo ABSOLUTO en que el narrador empieza `frase` en la escena k. Si Whisper la oyó distinto, se ubica por su posición en el libreto. */
const cue = (k: string, frase: string, n = 1): number => {
  const v = V[k];
  const obj = quita(frase).split(/\s+/).filter(Boolean);
  let vistas = 0;
  for (let i = 0; i < v.palabras.length; i++) {
    let ok = true;
    for (let j = 0; j < obj.length; j++) {
      const w = v.palabras[i + j];
      if (!w || !quita(w.w).replace(/\s/g, "").includes(obj[j])) {
        ok = false;
        break;
      }
    }
    if (ok && ++vistas === n) return INI[k] + v.palabras[i].t0;
  }
  const g = quita(v.guion).replace(/\s+/g, " ");
  const pos = g.indexOf(obj.join(" "));
  return INI[k] + (pos >= 0 ? pos / g.length : 0) * v.duracion;
};

/** 0→1→0: visible entre a y b con fundidos. */
const vis = (t: number, a: number, b: number, f = 0.35) =>
  Math.min(interpolate(t, [a, a + f], [0, 1], clamp), interpolate(t, [b - f, b], [1, 0], clamp));
const entra = (t: number, a: number, d = 0.5) => interpolate(t, [a, a + d], [0, 1], {...clamp, easing: (x) => 1 - Math.pow(1 - x, 3)});

// ---------- piezas ----------
const Fondo: React.FC = () => (
  <AbsoluteFill style={{background: K.crema}}>
    <div style={{position: "absolute", right: -260, top: -220, width: 760, height: 760, borderRadius: "50%", background: K.coralSuave, opacity: 0.45}} />
    <div style={{position: "absolute", left: -180, bottom: -260, width: 520, height: 520, borderRadius: "50%", background: K.verdeClaro, opacity: 0.35}} />
  </AbsoluteFill>
);

const Diapo: React.FC<{src: string; a: number; b: number; zoom?: [number, number]}> = ({src, a, b, zoom = [1, 1.045]}) => {
  const {t} = useT();
  const o = vis(t, a, b, 0.4);
  if (o <= 0) return null;
  const s = interpolate(t, [a, b], zoom, clamp);
  return (
    <AbsoluteFill style={{opacity: o}}>
      <Img src={staticFile(`firebox/${src}`)} style={{width: 1920, height: 1080, objectFit: "cover", transform: `scale(${s})`}} />
    </AbsoluteFill>
  );
};

const Kicker: React.FC<{texto: string; color?: string}> = ({texto, color = K.coral}) => (
  <div style={{fontFamily: F_TEXTO, fontWeight: 700, fontSize: 24, letterSpacing: 3, color, textTransform: "uppercase"}}>{texto}</div>
);

const Titulo: React.FC<{kicker: string; texto: string; a: number; b: number}> = ({kicker, texto, a, b}) => {
  const {t} = useT();
  const o = vis(t, a, b);
  if (o <= 0) return null;
  return (
    <div style={{position: "absolute", left: 90, top: 110, width: 620, opacity: o, transform: `translateY(${(1 - entra(t, a)) * 30}px)`}}>
      <Kicker texto={kicker} />
      <div style={{fontFamily: F_TITULO, fontWeight: 800, fontSize: 64, lineHeight: 1.02, color: K.tinta, marginTop: 14}}>{texto}</div>
    </div>
  );
};

/** Lista de pasos a la izquierda: el activo en coral, los anteriores con chulo. */
const Pasos: React.FC<{items: {texto: string; nota?: string; desde: number}[]; a: number; b: number; top?: number}> = ({items, a, b, top = 330}) => {
  const {t} = useT();
  const o = vis(t, a, b);
  if (o <= 0) return null;
  let activo = -1;
  items.forEach((it, i) => {
    if (t >= it.desde - 0.05) activo = i;
  });
  return (
    <div style={{position: "absolute", left: 90, top, width: 600, opacity: o}}>
      {items.map((it, i) => {
        const e = entra(t, it.desde - 0.1, 0.45);
        const esActivo = i === activo;
        const hecho = i < activo;
        return (
          <div key={i} style={{display: "flex", gap: 20, alignItems: "flex-start", marginBottom: 22, opacity: 0.35 + 0.65 * e,
            transform: `translateX(${(1 - e) * -20}px)`}}>
            <div style={{width: 46, height: 46, borderRadius: 23, flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center",
              background: esActivo ? K.coral : hecho ? K.verde : K.papel, border: `2px solid ${esActivo ? K.coral : hecho ? K.verde : K.linea}`,
              color: esActivo || hecho ? "#fff" : K.gris, fontFamily: F_TITULO, fontWeight: 800, fontSize: 22}}>
              {hecho ? "✓" : i + 1}
            </div>
            <div>
              <div style={{fontFamily: F_TITULO, fontWeight: 700, fontSize: 31, color: esActivo ? K.tinta : K.gris, lineHeight: 1.15}}>{it.texto}</div>
              {it.nota && <div style={{fontFamily: F_MONO, fontSize: 21, color: esActivo ? K.coral : K.gris, marginTop: 6}}>{it.nota}</div>}
            </div>
          </div>
        );
      })}
    </div>
  );
};

// --- resaltado de Python (simple y suficiente para mostrar el código real) ---
const PALABRAS_CLAVE = new Set(["def", "return", "if", "else", "elif", "for", "in", "while", "raise", "try", "except", "finally", "with", "as",
  "not", "and", "or", "is", "None", "True", "False", "class", "import", "from", "continue", "break", "lambda", "assert"]);
const colorear = (linea: string): React.ReactNode[] => {
  const out: React.ReactNode[] = [];
  const re = /(#.*$)|([rbf]?"(?:[^"\\]|\\.)*"|[rbf]?'(?:[^'\\]|\\.)*')|(\b\d[\d_.]*\b)|(\b[A-Za-z_][A-Za-z_0-9]*\b)|(\s+)|(.)/g;
  let m: RegExpExecArray | null;
  let previa = "";
  let i = 0;
  while ((m = re.exec(linea)) !== null) {
    const [tok, com, str, num, id] = m;
    let color = K.codTexto;
    if (com) color = "#7F938A";
    else if (str) color = "#B9E59F";
    else if (num) color = "#F7C97E";
    else if (id && PALABRAS_CLAVE.has(id)) color = "#FF8E6B";
    else if (id && previa === "def") color = "#FFD98A";
    else if (id === "self") color = "#9FC9FF";
    out.push(<span key={i++} style={{color}}>{tok}</span>);
    if (id) previa = id;
  }
  return out;
};

type Vista = {desde: number; id: string; foco?: [number, number]; titulo?: string};
/** Tarjeta de código REAL: cambia de fragmento según la voz; resalta las líneas que se están explicando. */
const Codigo: React.FC<{vistas: Vista[]; a: number; b: number; x?: number; y?: number; ancho?: number; tam?: number}> = ({
  vistas, a, b, x = 760, y = 150, ancho = 1070, tam = 25}) => {
  const {t} = useT();
  const o = vis(t, a, b);
  if (o <= 0) return null;
  let k = 0;
  vistas.forEach((v, i) => {
    if (t >= v.desde - 0.05) k = i;
  });
  const v = vistas[k];
  const tr = COD[v.id] as Trozo;
  const cambio = entra(t, v.desde - 0.05, 0.35);
  // la letra se ajusta para que ninguna línea real se corte (0,6 em por carácter en mono)
  const masLarga = Math.max(...tr.lineas.map((l) => l.length), 20);
  const tamReal = Math.min(tam, Math.floor((ancho - 120) / (masLarga * 0.6)));
  const alto = tamReal * 1.55;
  return (
    <div style={{position: "absolute", left: x, top: y, width: ancho, opacity: o, transform: `translateY(${(1 - entra(t, a)) * 40}px)`,
      borderRadius: 22, background: K.codFondo, boxShadow: "0 30px 70px rgba(15,61,46,0.28)", overflow: "hidden"}}>
      <div style={{display: "flex", alignItems: "center", gap: 10, padding: "16px 22px", background: "#13241D", borderBottom: "1px solid #24372F"}}>
        {["#FF6159", "#FFBD2E", "#28C941"].map((c) => <div key={c} style={{width: 14, height: 14, borderRadius: 7, background: c}} />)}
        <div style={{fontFamily: F_MONO, fontSize: 20, color: "#A9BDB4", marginLeft: 14}}>{tr.archivo}</div>
        {v.titulo && <div style={{marginLeft: "auto", fontFamily: F_TEXTO, fontWeight: 700, fontSize: 19, color: K.coral, letterSpacing: 1.5,
          textTransform: "uppercase"}}>{v.titulo}</div>}
      </div>
      <div style={{padding: "18px 0", opacity: 0.25 + 0.75 * cambio}}>
        {tr.lineas.map((l, i) => {
          const enFoco = v.foco ? i + 1 >= v.foco[0] && i + 1 <= v.foco[1] : false;
          return (
            <div key={i} style={{display: "flex", height: alto, alignItems: "center", fontFamily: F_MONO, fontSize: tamReal, whiteSpace: "pre",
              fontVariantLigatures: "none",
              background: enFoco ? "rgba(232,97,60,0.16)" : "transparent", borderLeft: `5px solid ${enFoco ? K.coral : "transparent"}`,
              opacity: v.foco && !enFoco ? 0.55 : 1}}>
              <span style={{width: 70, textAlign: "right", paddingRight: 22, color: "#5C7268"}}>{tr.desde + i}</span>
              <span>{colorear(l)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/** Captura real dentro de un marco. */
const Captura: React.FC<{src: string; a: number; b: number; x: number; y: number; ancho: number; rotar?: number; etiqueta?: string; zoom?: number}> = ({
  src, a, b, x, y, ancho, rotar = 0, etiqueta, zoom = 1.03}) => {
  const {t} = useT();
  const o = vis(t, a, b);
  if (o <= 0) return null;
  const e = entra(t, a, 0.55);
  const s = interpolate(t, [a, b], [1, zoom], clamp);
  return (
    <div style={{position: "absolute", left: x, top: y, width: ancho, opacity: o,
      transform: `translateY(${(1 - e) * 50}px) rotate(${rotar}deg) scale(${s})`, transformOrigin: "center top"}}>
      <div style={{borderRadius: 20, overflow: "hidden", background: "#fff", boxShadow: "0 28px 70px rgba(15,61,46,0.28)", border: `1px solid ${K.linea}`}}>
        <Img src={staticFile(`firebox/${src}`)} style={{width: "100%", display: "block"}} />
      </div>
      {etiqueta && <div style={{marginTop: 14, fontFamily: F_TEXTO, fontWeight: 600, fontSize: 22, color: K.gris}}>{etiqueta}</div>}
    </div>
  );
};

const Chip: React.FC<{texto: string; a: number; b: number; x: number; y: number; fondo?: string; color?: string; tam?: number}> = ({
  texto, a, b, x, y, fondo = K.verde, color = "#fff", tam = 26}) => {
  const {t, frame, fps} = useT();
  const o = vis(t, a, b, 0.25);
  if (o <= 0) return null;
  const pop = spring({frame: frame - Math.round(a * fps), fps, config: {damping: 12, stiffness: 180}, durationInFrames: 14});
  return (
    <div style={{position: "absolute", left: x, top: y, opacity: o, transform: `scale(${0.8 + 0.2 * pop})`, transformOrigin: "left center",
      background: fondo, color, fontFamily: F_MONO, fontWeight: 700, fontSize: tam, padding: "12px 22px", borderRadius: 14,
      boxShadow: "0 12px 30px rgba(15,61,46,0.22)"}}>{texto}</div>
  );
};

/** Terminal que muestra líneas reales en el segundo que se nombran. */
const Terminal: React.FC<{lineas: {texto: string; desde: number; color?: string}[]; a: number; b: number; x: number; y: number; ancho: number;
  titulo: string; tam?: number}> = ({lineas, a, b, x, y, ancho, titulo, tam = 23}) => {
  const {t} = useT();
  const o = vis(t, a, b);
  if (o <= 0) return null;
  return (
    <div style={{position: "absolute", left: x, top: y, width: ancho, opacity: o, transform: `translateY(${(1 - entra(t, a)) * 40}px)`,
      borderRadius: 20, background: "#0B1310", boxShadow: "0 30px 70px rgba(15,61,46,0.3)", overflow: "hidden"}}>
      <div style={{padding: "14px 22px", background: "#13241D", fontFamily: F_MONO, fontSize: 19, color: "#A9BDB4"}}>{titulo}</div>
      <div style={{padding: "18px 26px", minHeight: 120}}>
        {lineas.filter((l) => t >= l.desde - 0.05).map((l, i) => (
          <div key={i} style={{fontFamily: F_MONO, fontSize: tam, lineHeight: 1.55, color: l.color ?? "#D6E2DC", whiteSpace: "pre-wrap",
            fontVariantLigatures: "none",
            opacity: entra(t, l.desde - 0.05, 0.25)}}>{l.texto}</div>
        ))}
      </div>
    </div>
  );
};

/** Burbuja con el texto EXACTO que Firebox envió (demo_corte_vertical.py), estilo WhatsApp. */
const Burbuja: React.FC<{a: number; b: number; x: number; y: number; texto: React.ReactNode; hora?: string}> = ({a, b, x, y, texto, hora = "12:51"}) => {
  const {t, frame, fps} = useT();
  const o = vis(t, a, b, 0.25);
  if (o <= 0) return null;
  const pop = spring({frame: frame - Math.round(a * fps), fps, config: {damping: 13, stiffness: 170}, durationInFrames: 16});
  return (
    <div style={{position: "absolute", left: x, top: y, width: 720, opacity: o, transform: `scale(${0.85 + 0.15 * pop})`, transformOrigin: "left top"}}>
      <div style={{background: "#1F2C33", borderRadius: "6px 20px 20px 20px", padding: "20px 26px", boxShadow: "0 20px 50px rgba(0,0,0,0.3)"}}>
        <div style={{fontFamily: F_TEXTO, fontSize: 30, color: "#E9EDEF", lineHeight: 1.35}}>{texto}</div>
        <div style={{textAlign: "right", fontFamily: F_TEXTO, fontSize: 19, color: "#8696A0", marginTop: 6}}>{hora}</div>
      </div>
      <div style={{fontFamily: F_TEXTO, fontWeight: 600, fontSize: 21, color: K.gris, marginTop: 12}}>Mensaje enviado por Firebox · +57 324 350 2241</div>
    </div>
  );
};

/** Recuadro que llama la atención sobre una zona de la diapositiva. */
const Marco: React.FC<{a: number; b: number; x: number; y: number; w: number; h: number}> = ({a, b, x, y, w, h}) => {
  const {t} = useT();
  const o = vis(t, a, b, 0.25);
  if (o <= 0) return null;
  const e = entra(t, a, 0.4);
  return (
    <div style={{position: "absolute", left: x - 12, top: y - 12, width: w + 24, height: h + 24, opacity: o, borderRadius: 30,
      border: `6px solid ${K.coral}`, boxShadow: "0 0 0 9999px rgba(19,36,29,0.38)", transform: `scale(${1.06 - 0.06 * e})`}} />
  );
};

// ---------- capa fija: quién habla y subtítulos ----------
const Narrador: React.FC = () => {
  const {t, frame} = useT();
  const k = ORDEN.find((x) => t >= INI[x] - 0.2 && t <= fin(x) + 0.3);
  if (!k) return null;
  const v = V[k];
  const local = t - INI[k];
  const hablando = v.palabras.some((p) => local >= p.t0 - 0.05 && local <= p.t1 + 0.05);
  const o = vis(t, INI[k] - 0.2, fin(k) + 0.3, 0.3);
  const color = v.narrador === "David" ? K.coral : v.narrador === "Dylan" ? K.verde : K.tinta;
  return (
    <div style={{position: "absolute", left: 60, bottom: 150, opacity: o, display: "flex", alignItems: "center", gap: 16,
      background: "rgba(255,253,249,0.96)", border: `1px solid ${K.linea}`, borderRadius: 40, padding: "10px 26px 10px 10px",
      boxShadow: "0 14px 34px rgba(15,61,46,0.18)"}}>
      <div style={{width: 56, height: 56, borderRadius: 28, background: color, color: "#fff", display: "flex", alignItems: "center",
        justifyContent: "center", fontFamily: F_TITULO, fontWeight: 800, fontSize: 28}}>{v.narrador[0]}</div>
      <div>
        <div style={{fontFamily: F_TITULO, fontWeight: 800, fontSize: 27, color: K.tinta, lineHeight: 1}}>{v.narrador}</div>
        <div style={{fontFamily: F_TEXTO, fontWeight: 600, fontSize: 18, color: K.gris, marginTop: 4}}>Equipo Firebox</div>
      </div>
      <div style={{display: "flex", gap: 5, alignItems: "center", height: 36, marginLeft: 8}}>
        {[0, 1, 2, 3, 4].map((i) => {
          const h = hablando ? 10 + 22 * Math.abs(Math.sin(frame / 3.1 + i * 1.7)) : 6;
          return <div key={i} style={{width: 6, height: h, borderRadius: 3, background: color}} />;
        })}
      </div>
    </div>
  );
};

const Subtitulos: React.FC = () => {
  const {t} = useT();
  const k = ORDEN.find((x) => t >= INI[x] && t <= fin(x) + 0.6);
  if (!k) return null;
  const ps = V[k].palabras.map((p) => ({...p, t0: p.t0 + INI[k], t1: p.t1 + INI[k]}));
  const bloques: Palabra[][] = [];
  let actual: Palabra[] = [];
  ps.forEach((p, i) => {
    actual.push(p);
    const largo = actual.map((x) => x.w).join(" ").length;
    const sig = ps[i + 1];
    if (largo > 46 || /[.:;?!…]$/.test(p.w) || (largo > 26 && /,$/.test(p.w)) || (sig && sig.t0 - p.t1 > 0.7)) {
      bloques.push(actual);
      actual = [];
    }
  });
  if (actual.length) bloques.push(actual);
  let i = -1;
  bloques.forEach((bq, j) => {
    if (bq[0].t0 <= t + 0.02) i = j;
  });
  if (i < 0) return null;
  const bq = bloques[i];
  const hasta = Math.min(i + 1 < bloques.length ? bloques[i + 1][0].t0 : Infinity, bq[bq.length - 1].t1 + 0.6);
  if (t > hasta) return null;
  return (
    <div style={{position: "absolute", left: 0, right: 0, bottom: 52, display: "flex", justifyContent: "center"}}>
      <div style={{background: "rgba(15,61,46,0.93)", borderRadius: 18, padding: "14px 30px", maxWidth: 1300, fontFamily: F_TEXTO,
        fontWeight: 600, fontSize: 40, lineHeight: 1.25, color: "#fff", textAlign: "center"}}>
        {bq.map((p, j) => (
          <span key={j} style={{color: t >= p.t0 - 0.02 && t <= p.t1 + 0.12 ? "#FFB79C" : "#fff"}}>{p.w}{j < bq.length - 1 ? " " : ""}</span>
        ))}
      </div>
    </div>
  );
};

const Cabecera: React.FC = () => {
  const {t} = useT();
  const k = ORDEN.find((x) => t >= INI[x] - 0.3 && t <= fin(x) + GAP);
  if (!k) return null;
  const n = ORDEN.indexOf(k);
  return (
    <div style={{position: "absolute", left: 60, right: 60, top: 34, display: "flex", alignItems: "center", gap: 18}}>
      <div style={{fontFamily: F_TITULO, fontWeight: 800, fontSize: 26, color: K.verde}}>Firebox<span style={{color: K.coral}}>.</span></div>
      <div style={{display: "flex", gap: 6, flex: 1}}>
        {ORDEN.map((x, i) => (
          <div key={x} style={{flex: 1, height: 6, borderRadius: 3, background: i < n ? K.verde : i === n ? K.coral : "rgba(15,61,46,0.14)"}} />
        ))}
      </div>
      <div style={{fontFamily: F_TEXTO, fontWeight: 700, fontSize: 21, color: K.gris, letterSpacing: 1.5, textTransform: "uppercase"}}>
        {String(n + 1).padStart(2, "0")} · {V[k].titulo}
      </div>
    </div>
  );
};

// ---------- escenas ----------
const Intro: React.FC = () => {
  const {t} = useT();
  const o = vis(t, 0, INTRO + 0.2, 0.4);
  if (o <= 0) return null;
  return (
    <AbsoluteFill style={{opacity: o, alignItems: "center", justifyContent: "center"}}>
      <div style={{textAlign: "center", transform: `translateY(${(1 - entra(t, 0.1, 0.8)) * 40}px)`}}>
        <Kicker texto="API WARS 2026 · Factus · Universidad Distrital" />
        <div style={{fontFamily: F_TITULO, fontWeight: 800, fontSize: 210, color: K.verde, lineHeight: 1, marginTop: 20}}>
          Firebox<span style={{color: K.coral}}>.</span>
        </div>
        <div style={{fontFamily: F_TEXTO, fontWeight: 600, fontSize: 40, color: K.tinta, marginTop: 26, opacity: entra(t, 0.7)}}>
          Compra, factura y paga en una sola conversación de WhatsApp
        </div>
        <div style={{display: "flex", gap: 18, justifyContent: "center", marginTop: 40, opacity: entra(t, 1.2)}}>
          {["WhatsApp Cloud API", "Factus API v2", "Factus Pay · Bre-B"].map((x, i) => (
            <div key={x} style={{fontFamily: F_TEXTO, fontWeight: 700, fontSize: 26, padding: "14px 28px", borderRadius: 14,
              background: i === 0 ? K.verde : "transparent", color: i === 0 ? "#fff" : i === 2 ? K.coral : K.tinta,
              border: `2px solid ${i === 0 ? K.verde : i === 2 ? K.coral : K.tinta}`}}>{x}</div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const E1: React.FC = () => {
  const c = cue("E1", "Pero la compra");
  return (
    <>
      <Diapo src="diapositiva_01.png" a={INI.E1 - 0.3} b={c + 0.2} />
      <Diapo src="diapositiva_02.png" a={c} b={fin("E1") + GAP} />
    </>
  );
};

const E2: React.FC = () => {
  const c1 = cue("E2", "El cliente compra");
  const c2 = cue("E2", "Y cuando paga");
  return (
    <>
      <Diapo src="diapositiva_03.png" a={INI.E2 - 0.2} b={c1 + 0.3} />
      <Titulo kicker="La solución" texto="Factura y QR en el mismo chat" a={c1} b={fin("E2") + GAP} />
      <Pasos a={c1} b={fin("E2") + GAP} items={[
        {texto: "El cliente compra por WhatsApp", desde: c1},
        {texto: "Recibe su factura validada ante la DIAN", desde: cue("E2", "recibe su factura")},
        {texto: "Con su QR Bre-B en el mismo PDF", desde: cue("E2", "con una página de pago")},
        {texto: "Paga y el chat se lo confirma", desde: c2},
      ]} />
      <Captura src="whatsapp_factura_recibida.png" a={c1 + 0.2} b={c2 + 0.3} x={820} y={150} ancho={960} etiqueta="WhatsApp real del cliente · 05-oct-2026" />
      <Burbuja a={c2} b={fin("E2") + GAP} x={900} y={380} texto={<>✅ Pago recibido. Tu factura <b>SETP990023179</b> quedó pagada.<br />¡Gracias por comprar en Relojes NovaMarket!</>} />
    </>
  );
};

const E3: React.FC = () => {
  // coordenadas medidas sobre la diapositiva 4 a 1920×1080
  return (
    <>
      <Diapo src="diapositiva_04.png" a={INI.E3 - 0.2} b={fin("E3") + GAP} zoom={[1, 1]} />
      <Marco a={cue("E3", "WhatsApp Cloud API")} b={cue("E3", "Factus API versión")} x={91} y={302} w={410} h={425} />
      <Marco a={cue("E3", "Factus API versión")} b={cue("E3", "Y Factus Pay")} x={533} y={302} w={405} h={425} />
      <Marco a={cue("E3", "Y Factus Pay")} b={cue("E3", "Firebox, escrito")} x={972} y={302} w={420} h={425} />
      <Marco a={cue("E3", "Firebox, escrito")} b={cue("E3", "Y el número")} x={737} y={785} w={400} h={218} />
      <Marco a={cue("E3", "Y el número")} b={fin("E3") + GAP} x={1426} y={302} w={403} h={425} />
    </>
  );
};

const E4: React.FC = () => {
  const a = INI.E4 - 0.2;
  const b = fin("E4") + GAP;
  const cTok = cue("E4", "pedimos un token");
  const cRan = cue("E4", "rango de numeración");
  const cVal = cue("E4", "bills validate");
  const cCufe = cue("E4", "el CUFE");
  const cPdf = cue("E4", "descargamos el PDF");
  const cUa = cue("E4", "User-Agent");
  return (
    <>
      <Titulo kicker="API 02 · Factus v2" texto="Así conectamos Factus" a={a} b={b} />
      <Pasos a={a} b={b} items={[
        {texto: "Token OAuth 2.0", nota: "POST /oauth/token", desde: cTok},
        {texto: "Rango de numeración activo", nota: "GET /v2/numbering-ranges", desde: cRan},
        {texto: "Emitir y validar la factura", nota: "POST /v2/bills/validate", desde: cVal},
        {texto: "Descargar el PDF", nota: "GET /v2/bills/{numero}/download-pdf", desde: cPdf},
        {texto: "User-Agent propio", nota: "sin él: 403 de Cloudflare", desde: cUa},
      ]} />
      <Codigo a={a + 0.3} b={cCufe + 0.2} vistas={[
        {desde: a, id: "factus_token", foco: [3, 3], titulo: "OAuth 2.0"},
        {desde: cTok, id: "factus_token", foco: [3, 7], titulo: "OAuth 2.0"},
        {desde: cRan, id: "factus_rango", foco: [2, 5], titulo: "Rango activo"},
        {desde: cVal, id: "factus_emitir", foco: [2, 2], titulo: "Emitir y validar"},
      ]} />
      <Captura src="pdf_factura.png" a={cCufe} b={cUa + 0.2} x={980} y={130} ancho={620} rotar={-1.5} etiqueta="Factura SETP990023179 · validada · con CUFE" />
      <Chip texto="validada DIAN: True · CUFE c0480313…" a={cCufe + 0.4} b={cUa + 0.2} x={800} y={760} fondo={K.verde} />
      <Codigo a={cUa} b={b} y={260} tam={28} vistas={[{desde: cUa, id: "user_agent", foco: [1, 1], titulo: "Hallazgo"}]} />
      <Chip texto="Sin User-Agent → 403 (Cloudflare)" a={cUa + 0.5} b={b} x={760} y={430} fondo={K.coral} />
      <Chip texto="Con User-Agent → 200 ✓" a={cUa + 1.2} b={b} x={760} y={515} fondo={K.verde} />
      <Chip texto="medido el 05-oct-2026" a={cUa + 1.6} b={b} x={760} y={600} fondo={K.papel} color={K.gris} tam={22} />
    </>
  );
};

const E5: React.FC = () => {
  const a = INI.E5 - 0.2;
  const b = fin("E5") + GAP;
  const cRec = cue("E5", "creamos un recaudo");
  const cQr = cue("E5", "el código QR al instante");
  const cPaga = cue("E5", "Paga aquí");
  const cVig = cue("E5", "Como Factus Pay no avisa");
  const cPag = cue("E5", "Apenas aparece pagado");
  return (
    <>
      <Titulo kicker="API 03 · Factus Pay" texto="Así cobramos con QR Bre-B" a={a} b={b} />
      <Pasos a={a} b={b} items={[
        {texto: "Autenticación", nota: "POST /auth", desde: a + 0.4},
        {texto: "Recaudo = número de factura", nota: "POST /v1/collections", desde: cRec},
        {texto: "QR al instante", nota: "status: ready", desde: cQr},
        {texto: "Página \"Paga aquí\" en el PDF", desde: cPaga},
        {texto: "Vigilante cada 5 segundos", nota: "GET /v1/collections/{ref}", desde: cVig},
      ]} />
      <Codigo a={a + 0.3} b={cPaga + 0.2} vistas={[
        {desde: a, id: "pay_crear", foco: [1, 1], titulo: "Recaudo"},
        {desde: cRec, id: "pay_crear", foco: [4, 5], titulo: "Referencia = factura"},
        {desde: cQr, id: "pay_crear", foco: [6, 7], titulo: "QR"},
      ]} />
      <Captura src="pdf_paga_aqui.png" a={cPaga} b={cVig + 0.2} x={1040} y={120} ancho={560} rotar={1.2} etiqueta="Página 2 del PDF que recibe el cliente" />
      <Codigo a={cVig} b={b} vistas={[
        {desde: cVig, id: "vigilante", foco: [1, 3], titulo: "Vigilante"},
        {desde: cPag, id: "vigilante", foco: [3, 9], titulo: "¡Pagado!"},
      ]} />
      <Chip texto="ready" a={cVig + 0.6} b={cPag} x={1560} y={700} fondo={K.papel} color={K.gris} />
      <Chip texto="paid ✓" a={cPag} b={b} x={1560} y={700} fondo={K.verde} />
    </>
  );
};

const E6: React.FC = () => {
  const a = INI.E6 - 0.2;
  const b = fin("E6") + GAP;
  const cSms = cue("E6", "código por SMS");
  const cApp = cue("E6", "creamos la app");
  const cTok = cue("E6", "token permanente");
  const cSub = cue("E6", "subimos a WhatsApp");
  const cEnv = cue("E6", "enviamos al cliente");
  return (
    <>
      <Titulo kicker="API 01 · WhatsApp Cloud API" texto="Así conectamos WhatsApp" a={a} b={b} />
      <Pasos a={a} b={b} items={[
        {texto: "Número propio en Meta", nota: "+57 324 350 2241", desde: a + 0.4},
        {texto: "Verificado por SMS", desde: cSms},
        {texto: "App Firebox", desde: cApp},
        {texto: "Token permanente", nota: "solo 2 permisos de WhatsApp", desde: cTok},
        {texto: "Subir y enviar PDF y QR", nota: "POST /media · /messages", desde: cSub},
      ]} />
      <Captura src="meta_numero_no_verificado.png" a={a + 0.3} b={cSms + 0.2} x={760} y={200} ancho={1080} etiqueta="Administrador de WhatsApp · el número recién agregado" />
      <Captura src="meta_verificacion.png" a={cSms} b={cApp + 0.2} x={880} y={140} ancho={840} etiqueta="Verificación obligatoria por SMS" />
      <Captura src="meta_app_firebox.png" a={cApp} b={cTok + 0.2} x={760} y={150} ancho={1080} etiqueta="La app Firebox en Meta for Developers" />
      <Captura src="meta_permisos_token.png" a={cTok} b={cSub + 0.2} x={860} y={170} ancho={900} etiqueta="Token del usuario del sistema: mínimo privilegio" />
      <Codigo a={cSub} b={cEnv + 0.2} vistas={[
        {desde: cSub, id: "wa_subir", foco: [1, 3], titulo: "Subir el PDF"},
        {desde: cSub + 2.2, id: "wa_documento", foco: [1, 2], titulo: "Enviar"},
      ]} />
      <Captura src="whatsapp_factura_recibida.png" a={cEnv} b={b} x={860} y={130} ancho={900} etiqueta="Así le llega al cliente" />
    </>
  );
};

const E7: React.FC = () => {
  const a = INI.E7 - 0.2;
  const b = fin("E7") + GAP;
  const c88 = cue("E7", "ocho coma ocho");
  const c17 = cue("E7", "diecisiete segundos");
  const cSim = cue("E7", "Simulamos el pago");
  const cConf = cue("E7", "Pago recibido");
  const cCiclo = cue("E7", "El ciclo completo");
  const ev = COD.evidencia;
  const verde = "#9BE07A";
  return (
    <>
      <Titulo kicker="Demo real · sandbox" texto="Una corrida de punta a punta" a={a} b={cCiclo + 0.2} />
      <Terminal titulo="$ python app/demo_corte_vertical.py --para 57313XXXXXXX" a={a + 0.3} b={cCiclo + 0.2} x={90} y={350} ancho={1000} tam={20}
        lineas={[
          {texto: ev[0], desde: a + 0.6},
          {texto: ev[1], desde: c88, color: verde},
          {texto: ev[2], desde: c88 + 0.3},
          {texto: ev[3], desde: c88 + 0.6, color: verde},
          {texto: ev[5], desde: c17, color: verde},
          {texto: ev[6], desde: c17 + 0.6},
          {texto: ev[7], desde: cConf - 0.3, color: "#FFB79C"},
          {texto: ev[8], desde: cConf + 0.5, color: verde},
        ]} />
      <Captura src="whatsapp_factura_recibida.png" a={c17} b={cSim + 0.2} x={1130} y={150} ancho={700} etiqueta="17,2 s: factura, PDF y QR en el chat" />
      <Captura src="factus_pay_simulador.png" a={cSim} b={cConf + 0.2} x={1130} y={250} ancho={700} etiqueta="Simulador de Factus Pay: monto y llave Bre-B leídos del QR" />
      <Burbuja a={cConf} b={cCiclo + 0.2} x={1130} y={300} texto={<>✅ Pago recibido. Tu factura <b>SETP990023179</b> quedó pagada.</>} />
      <Diapo src="diapositiva_07.png" a={cCiclo} b={b} zoom={[1, 1.03]} />
    </>
  );
};

const E8: React.FC = () => {
  const a = INI.E8 - 0.2;
  const b = fin("E8") + GAP;
  const cRed = cue("E8", "redondeo bancario");
  const cTot = cue("E8", "Antes de cobrar");
  const cRango = cue("E8", "Si el monto");
  const cRomp = cue("E8", "rompiendo el código");
  const cn = COD.control_negativo;
  return (
    <>
      <Titulo kicker="Calidad" texto="El dinero lo calcula el código" a={a} b={b} />
      <Pasos a={a} b={b} items={[
        {texto: "Decimales exactos", nota: "decimal.Decimal, nunca float", desde: a + 0.4},
        {texto: "Redondeo bancario por línea", nota: "ROUND_HALF_EVEN (DIAN)", desde: cRed},
        {texto: "Total idéntico en 3 sistemas", desde: cTot},
        {texto: "Monto dentro del rango de Factus Pay", desde: cRango},
        {texto: "Pruebas con control negativo", desde: cRomp},
      ]} />
      <Codigo a={a + 0.3} b={cTot + 0.2} vistas={[
        {desde: a, id: "dinero_linea", foco: [1, 4], titulo: "IVA por línea"},
        {desde: cRed, id: "dinero_redondear", foco: [1, 2], titulo: "Half-even"},
      ]} />
      {[["Firebox (calculado)", K.verde], ["Factus (factura)", K.tinta], ["Factus Pay (recaudo)", K.coral]].map(([n, c], i) => (
        <Chip key={n} texto={`${n}  ·  $202.181 ✓`} a={cTot + 0.3 + i * 0.5} b={cRango + 0.2} x={800} y={240 + i * 120} fondo={c} tam={34} />
      ))}
      <Codigo a={cRango} b={cRomp + 0.2} y={240} tam={28} vistas={[
        {desde: cRango, id: "dinero_rango", foco: [1, 2], titulo: "Rango permitido"},
        {desde: cRango + 2.5, id: "demo_igualdad", foco: [1, 2], titulo: "Si no cuadra, no cobra"},
      ]} />
      <Terminal titulo="$ pytest  ·  control negativo (Regla 2)" a={cRomp} b={b} x={760} y={200} ancho={1080} tam={22} lineas={[
        {texto: `sano:        ${cn.sano}`, desde: cRomp + 0.2, color: "#9BE07A"},
        {texto: "rompo:       ROUND_HALF_EVEN → ROUND_HALF_UP", desde: cRomp + 1.4, color: "#FFB79C"},
        ...cn.roto.map((l, i) => ({texto: l.length > 72 ? l.slice(0, 72) + "…" : l, desde: cRomp + 2.4 + i * 0.5, color: "#FF7A6B"})),
        {texto: `restaurado:  ${cn.restaurado}`, desde: cRomp + 4.2, color: "#9BE07A"},
        {texto: "DETECTA el bug ← test_redondeo_bancario_y_no_hacia_arriba", desde: cRomp + 5.0, color: "#FFD98A"},
      ]} />
    </>
  );
};

// ---------- E8b: recorrido del panel botón por botón ----------
// Capturas REALES del panel en 5 estados (video/capturar_recorrido_panel.py) con la caja de cada botón en píxeles de la imagen.
// La cámara se acerca a cada zona y el cursor llega a cada botón en el segundo en que la voz clonada de Fernando lo nombra.
type Caja = [number, number, number, number];
type EstadoPanel = {imagen: string; cajas: Record<string, Caja | null>};
const PR = recorrido as unknown as {ancho: number; alto: number; estados: Record<string, EstadoPanel>; factura: string; xml: string[]; csv: string[]};
type Paso = {t: number; estado: string; foco: string; cursor?: string; clic?: boolean; zoom?: number};
const VISTA = {cx: 960, cy: 490, w: 1920, h: 840}; // zona útil: entre la barra de progreso y los subtítulos
const suave = (x: number) => (x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x));

const cajaDe = (estado: string, k: string): Caja => {
  const c = PR.estados[estado]?.cajas[k] ?? PR.estados.base.cajas[k];
  return (c ?? [0, 0, PR.ancho, PR.alto]) as Caja;
};
const camDe = (p: Paso) => {
  const general = Math.min(VISTA.w / PR.ancho, VISTA.h / PR.alto) * 0.95;
  if (p.foco === "todo") return {s: general, cx: PR.ancho / 2, cy: PR.alto / 2};
  const [x, y, w, h] = cajaDe(p.estado, p.foco);
  const s = Math.max(general, Math.min(p.zoom ?? 1.75, (VISTA.w * 0.8) / w, (VISTA.h * 0.72) / h));
  let cx = x + w / 2;
  let cy = y + h / 2;
  const mw = VISTA.w / 2 / s;
  const mh = VISTA.h / 2 / s;
  cx = PR.ancho * s >= VISTA.w ? Math.min(Math.max(cx, mw), PR.ancho - mw) : PR.ancho / 2;
  cy = PR.alto * s >= VISTA.h ? Math.min(Math.max(cy, mh), PR.alto - mh) : PR.alto / 2;
  return {s, cx, cy};
};
const punto = (c: Caja): [number, number] => {
  const [x, y, w, h] = c;
  return w > 260 ? [x + w * 0.28, y + Math.min(h * 0.42, 70)] : [x + w / 2, y + h / 2];
};

const Cursor: React.FC<{x: number; y: number; pulso: number}> = ({x, y, pulso}) => (
  <>
    {pulso > 0 && pulso < 1 && (
      <div style={{position: "absolute", left: x - 34, top: y - 34, width: 68, height: 68, borderRadius: 34,
        border: `5px solid ${K.coral}`, opacity: 1 - pulso, transform: `scale(${0.4 + pulso * 1.1})`}} />
    )}
    <svg width={46} height={54} viewBox="0 0 23 27" style={{position: "absolute", left: x - 3, top: y - 2,
      transform: `scale(${pulso > 0 && pulso < 0.35 ? 0.86 : 1})`, transformOrigin: "3px 2px", filter: "drop-shadow(0 6px 10px rgba(0,0,0,0.35))"}}>
      <path d="M2 1 L2 22 L7.5 17 L11 25.5 L14.6 24 L11.2 15.8 L18.5 15.8 Z" fill="#13241D" stroke="#fff" strokeWidth={1.6} strokeLinejoin="round" />
    </svg>
  </>
);

/** Tarjeta oscura con contenido real (XML firmado, CSV) sobre el panel atenuado. */
const Tarjeta: React.FC<{a: number; b: number; titulo: string; lineas: string[]; ancho: number; tam: number; colorear?: (l: string, i: number) => string}> = ({
  a, b, titulo, lineas, ancho, tam, colorear}) => {
  const {t} = useT();
  const o = vis(t, a, b, 0.3);
  if (o <= 0) return null;
  return (
    <AbsoluteFill style={{opacity: o, background: "rgba(19,36,29,0.62)", alignItems: "center", justifyContent: "center"}}>
      <div style={{width: ancho, marginTop: -60, borderRadius: 22, background: "#0B1310", overflow: "hidden", boxShadow: "0 40px 90px rgba(0,0,0,0.45)",
        transform: `translateY(${(1 - entra(t, a, 0.45)) * 40}px)`}}>
        <div style={{padding: "16px 26px", background: "#13241D", fontFamily: F_MONO, fontSize: 21, color: "#A9BDB4"}}>{titulo}</div>
        <div style={{padding: "22px 30px"}}>
          {lineas.map((l, i) => (
            <div key={i} style={{fontFamily: F_MONO, fontSize: tam, lineHeight: 1.6, whiteSpace: "pre", fontVariantLigatures: "none",
              color: colorear ? colorear(l, i) : "#D6E2DC", opacity: entra(t, a + 0.25 + i * 0.12, 0.25)}}>{l}</div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const E8b: React.FC = () => {
  const {t} = useT();
  if (!V.E8b) return null;
  const a = INI.E8b - 0.2;
  const b = fin("E8b") + GAP;
  const o = vis(t, a, b);
  if (o <= 0) return null;
  const P = (frase: string, n = 1) => cue("E8b", frase, n);
  const pasos: Paso[] = [
    {t: a, estado: "base", foco: "todo"},
    {t: P("Arriba están las métricas"), estado: "base", foco: "kpis1", cursor: "kpi_ventas"},
    {t: P("lo facturado"), estado: "base", foco: "kpis1", cursor: "kpi_facturado"},
    {t: P("lo cobrado"), estado: "base", foco: "kpis1", cursor: "kpi_cobrado"},
    {t: P("lo que falta"), estado: "base", foco: "kpis1", cursor: "kpi_pendiente"},
    {t: P("Debajo"), estado: "base", foco: "kpis2", cursor: "kpi_tasa"},
    {t: P("el ticket promedio"), estado: "base", foco: "kpis2", cursor: "kpi_ticket"},
    {t: P("y el IVA"), estado: "base", foco: "kpis2", cursor: "kpi_iva"},
    {t: P("cada cinco segundos"), estado: "base", foco: "kpis2", cursor: "kpi_hora"},
    {t: P("Con las pestañas"), estado: "base", foco: "tabla", cursor: "pestanas", zoom: 1.3},
    {t: P("solo las pagadas"), estado: "pagadas", foco: "tabla", cursor: "pagadas", clic: true, zoom: 1.3},
    {t: P("están por cobrar"), estado: "pagadas", foco: "tabla", cursor: "porcobrar", zoom: 1.3},
    {t: P("el buscador"), estado: "busqueda", foco: "tabla", cursor: "buscar", clic: true, zoom: 1.3},
    {t: P("Cada factura tiene"), estado: "base", foco: "fila", cursor: "acciones"},
    {t: P("PDF descarga"), estado: "base", foco: "fila", cursor: "pdf", clic: true},
    {t: P("XML trae"), estado: "base", foco: "fila", cursor: "xml", clic: true},
    {t: P("QR abre"), estado: "base", foco: "fila", cursor: "qr", clic: true},
    {t: P("QR abre") + 0.45, estado: "qr", foco: "dialogo", zoom: 1.45},
    {t: P("Y Consultar"), estado: "base", foco: "fila", cursor: "consultar"},
    {t: P("le pregunta"), estado: "consultar", foco: "aviso_fila", cursor: "consultar", clic: true},
    {t: P("A la derecha"), estado: "consultar", foco: "conexiones", cursor: "conexiones"},
    {t: P("Probar ahora"), estado: "consultar", foco: "conexiones", cursor: "probar", clic: true},
    {t: P("En Nueva venta"), estado: "consultar", foco: "venta", cursor: "campo"},
    {t: P("el sistema factura"), estado: "consultar", foco: "venta", cursor: "vender"},
    {t: P("En Actividad"), estado: "consultar", foco: "actividad", cursor: "actividad"},
    {t: P("Por último"), estado: "consultar", foco: "csv", cursor: "csv", zoom: 1.5},
    {t: P("Exportar descarga"), estado: "consultar", foco: "csv", cursor: "csv", clic: true, zoom: 1.5},
    {t: P("listo para la contabilidad"), estado: "consultar", foco: "todo"},
  ];
  // cámara: llega a cada zona justo cuando se nombra (empieza a moverse 0,35 s antes)
  let i = 0;
  pasos.forEach((p, j) => {
    if (t >= p.t - 0.35) i = j;
  });
  const c0 = camDe(pasos[Math.max(0, i - 1)]);
  const c1 = camDe(pasos[i]);
  const k = i === 0 ? 1 : suave((t - (pasos[i].t - 0.35)) / 0.85);
  const s = Math.exp(Math.log(c0.s) + (Math.log(c1.s) - Math.log(c0.s)) * k);
  const cx = c0.cx + (c1.cx - c0.cx) * k;
  const cy = c0.cy + (c1.cy - c0.cy) * k;
  const aPantalla = (x: number, y: number): [number, number] => [VISTA.cx + (x - cx) * s, VISTA.cy + (y - cy) * s];
  // estado de la pantalla: cambia en el instante del clic, con un fundido corto
  let e = 0;
  pasos.forEach((p, j) => {
    if (t >= p.t) e = j;
  });
  const actual = pasos[e].estado;
  const anterior = pasos[Math.max(0, e - 1)].estado;
  const fundido = entra(t, pasos[e].t, 0.22);
  // cursor: viaja al botón y llega en el segundo de la palabra
  const conCursor = pasos.map((p, j) => ({...p, j})).filter((p) => p.cursor);
  let ci = -1;
  conCursor.forEach((p, j) => {
    if (t >= p.t - 0.55) ci = j;
  });
  let cursor: React.ReactNode = null;
  let marco: React.ReactNode = null;
  if (ci >= 0) {
    const p1 = conCursor[ci];
    const desde = ci > 0 ? punto(cajaDe(conCursor[ci - 1].estado, conCursor[ci - 1].cursor as string)) : [PR.ancho * 0.55, PR.alto * 0.62];
    const hasta = punto(cajaDe(p1.estado, p1.cursor as string));
    const m = suave((t - (p1.t - 0.55)) / 0.55);
    const [sx, sy] = aPantalla(desde[0] + (hasta[0] - desde[0]) * m, desde[1] + (hasta[1] - desde[1]) * m);
    const pulso = p1.clic ? (t - p1.t) / 0.5 : -1;
    const oc = Math.min(entra(t, conCursor[0].t - 0.55, 0.3), 1 - entra(t, P("listo para la contabilidad"), 0.4));
    cursor = <div style={{opacity: oc}}><Cursor x={sx} y={sy} pulso={pulso} /></div>;
    const [bx, by, bw, bh] = cajaDe(p1.estado, p1.cursor as string);
    const [mx, my] = aPantalla(bx, by);
    const om = vis(t, p1.t - 0.1, (conCursor[ci + 1]?.t ?? b) - 0.45, 0.2) * oc;
    if (om > 0 && pasos[e].estado !== "qr")
      marco = <div style={{position: "absolute", left: mx - 7, top: my - 7, width: bw * s + 14, height: bh * s + 14, borderRadius: 16,
        border: `4px solid ${K.coral}`, opacity: om, boxShadow: "0 0 0 6px rgba(232,97,60,0.16)"}} />;
  }
  const imagen = (estado: string, op: number) => (
    <Img key={estado} src={staticFile(PR.estados[estado].imagen)} style={{position: "absolute", left: 0, top: 0, width: PR.ancho, height: PR.alto, opacity: op}} />
  );
  const cPdf = P("PDF descarga");
  const cXml = P("XML trae");
  const cQr = P("QR abre");
  const cCsv = P("Exportar descarga");
  return (
    <AbsoluteFill style={{opacity: o}}>
      <div style={{position: "absolute", left: 0, top: 0, width: PR.ancho, height: PR.alto, transformOrigin: "0 0",
        transform: `translate(${VISTA.cx - cx * s}px, ${VISTA.cy - cy * s}px) scale(${s})`,
        borderRadius: 22, overflow: "hidden", boxShadow: "0 30px 90px rgba(15,61,46,0.30)", background: "#fff"}}>
        {anterior !== actual && imagen(anterior, 1)}
        {imagen(actual, anterior !== actual ? fundido : 1)}
      </div>
      {marco}
      {cursor}
      {/* PDF: la factura electrónica real (página 1 del PDF que entrega Factus) */}
      {(() => {
        const op = vis(t, cPdf + 0.55, cXml - 0.05, 0.3);
        if (op <= 0) return null;
        return (
          <AbsoluteFill style={{opacity: op, background: "rgba(19,36,29,0.8)", alignItems: "center", justifyContent: "center"}}>
            <div style={{display: "flex", alignItems: "center", gap: 46, marginTop: -60, transform: `translateY(${(1 - entra(t, cPdf + 0.55, 0.45)) * 40}px)`}}>
              <div style={{width: 560, borderRadius: 16, overflow: "hidden", boxShadow: "0 40px 90px rgba(0,0,0,0.45)", background: "#fff", height: 700}}>
                <Img src={staticFile("firebox/pdf_factura.png")} style={{width: "100%", display: "block"}} />
              </div>
              <div style={{width: 520, color: "#fff"}}>
                <Kicker texto="PDF · Factus API v2" color={K.coralSuave} />
                <div style={{fontFamily: F_TITULO, fontWeight: 800, fontSize: 54, lineHeight: 1.05, marginTop: 12}}>La factura electrónica, tal como la entrega Factus</div>
                <div style={{fontFamily: F_MONO, fontSize: 24, marginTop: 22, color: K.verdeClaro}}>GET /v2/bills/{PR.factura}/download-pdf</div>
              </div>
            </div>
          </AbsoluteFill>
        );
      })()}
      <Tarjeta a={cXml + 0.5} b={cQr - 0.05} ancho={1180} tam={25}
        titulo={`${PR.factura}.xml · documento firmado que recibe la DIAN (extracto real)`} lineas={PR.xml}
        colorear={(l) => (l.includes("SignatureValue") ? "#FFD98A" : l.includes("UUID") || l.includes("PayableAmount") ? "#9BE07A" : "#D6E2DC")} />
      <Tarjeta a={cCsv + 0.5} b={b} ancho={1500} tam={21} titulo="ventas.csv · descargado del panel (cufe recortado en pantalla)" lineas={PR.csv}
        colorear={(_, i) => (i === 0 ? "#FFD98A" : "#D6E2DC")} />
    </AbsoluteFill>
  );
};

const E9: React.FC = () => {
  const a = INI.E9 - 0.2;
  const b = fin("E9") + GAP;
  const cSand = cue("E9", "Esto corre");
  const cSigue = cue("E9", "Lo que sigue");
  const cCierre = cue("E9", "de elegir a pagar");
  const docs = [
    ".specify/memory/constitution.md · 8 reglas",
    "specs/001-tienda-whatsapp/spec.md · historias y requisitos",
    "docs/documentacion/01_SRS · 28 RF · 13 RNF",
    "docs/documentacion/02_Casos_de_Uso · 10 casos",
    "docs/documentacion/07_Integraciones_Conexiones",
    "docs/documentacion/evidencias/ · corrida real",
    "app/ · código + pruebas",
  ];
  return (
    <>
      <Titulo kicker="Repositorio" texto="Todo documentado" a={a} b={cSigue + 0.2} />
      <Terminal titulo="github.com/ferdinando04/api-wars" a={a + 0.3} b={cSigue + 0.2} x={760} y={170} ancho={1080} tam={25}
        lineas={docs.map((d, i) => ({texto: `▸ ${d}`, desde: a + 0.8 + i * 0.55, color: i === 4 ? "#FFD98A" : "#D6E2DC"}))} />
      <Chip texto="Sandbox · sin validez fiscal ni dinero real" a={cSand} b={cSigue + 0.2} x={90} y={420} fondo={K.coral} tam={26} />
      <Diapo src="diapositiva_08.png" a={cSigue} b={cCierre + 0.3} zoom={[1, 1.03]} />
      <CierreMarca a={cCierre} b={b + OUTRO} />
    </>
  );
};

const CierreMarca: React.FC<{a: number; b: number}> = ({a, b}) => {
  const {t} = useT();
  const o = vis(t, a, b, 0.5);
  if (o <= 0) return null;
  const creditos = t > FIN_VOZ + 0.4;
  return (
    <AbsoluteFill style={{opacity: o, background: K.crema, alignItems: "center", justifyContent: "center"}}>
      <div style={{textAlign: "center", transform: `translateY(${(1 - entra(t, a, 0.7)) * 40}px)`}}>
        <div style={{fontFamily: F_TITULO, fontWeight: 800, fontSize: 190, color: K.verde, lineHeight: 1}}>Firebox<span style={{color: K.coral}}>.</span></div>
        <div style={{fontFamily: F_TEXTO, fontWeight: 600, fontSize: 42, color: K.tinta, marginTop: 24}}>De elegir a pagar, con factura, en una sola conversación.</div>
        <div style={{opacity: creditos ? entra(t, FIN_VOZ + 0.4, 0.6) : 0, marginTop: 56}}>
          <Kicker texto="Equipo Firebox" color={K.gris} />
          <div style={{display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "8px 44px", maxWidth: 1700, margin: "14px auto 0"}}>
            {EQUIPO.map((n) => <div key={n} style={{fontFamily: F_TITULO, fontWeight: 700, fontSize: 38, color: K.verde}}>{n}</div>)}
          </div>
          <div style={{fontFamily: F_MONO, fontSize: 30, color: K.coral, marginTop: 26}}>github.com/ferdinando04/api-wars</div>
          <div style={{fontFamily: F_TEXTO, fontSize: 24, color: K.gris, marginTop: 18}}>API WARS 2026 · Semillero Pegasus · Universidad Distrital · IEEE · Factus</div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const FireboxPitch: React.FC = () => {
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill style={{background: K.crema, overflow: "hidden"}}>
      <Fondo />
      <Intro />
      <E1 />
      <E2 />
      <E3 />
      <E4 />
      <E5 />
      <E6 />
      <E7 />
      <E8 />
      <E8b />
      <E9 />
      <Cabecera />
      <Narrador />
      <Subtitulos />
      <Audio src={staticFile("vexon/sonido/musica-d05_piloto.mp3")} loop
        volume={(f) => {
          const s = f / fps;
          // más alta en la entrada y el cierre, baja (~18 dB bajo la voz) mientras hablan, con transiciones suaves
          const base = interpolate(s, [INTRO - 1, INTRO - 0.2, FIN_VOZ + 0.2, FIN_VOZ + 1.2], [0.17, 0.065, 0.065, 0.17], clamp);
          const entrada = interpolate(s, [0, 1.2], [0, 1], clamp);
          const salida = interpolate(s, [DURACION_FIREBOX - 2.5, DURACION_FIREBOX], [1, 0], clamp);
          return base * entrada * salida;
        }} />
      {ORDEN.filter((k) => V[k].audio).map((k) => (
        <Sequence key={k} from={Math.round(INI[k] * fps)}>
          <Audio src={staticFile(V[k].audio as string)} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
