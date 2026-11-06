#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SLT-Core v2: Traductor bilingüe de lengua de señas (ES/EN) por cámara -> texto + voz.

Tubería:
  cámara -> MediaPipe Tasks (landmarks 21x3 por mano; modelo pre-entrenado de Google, Apache-2.0)
         -> ventana temporal (~1.2 s) -> rasgos espacio-temporales (forma + ángulos + trayectoria)
         -> TinyMLP propio en NumPy puro (Adam, dropout, label smoothing)
         -> decodificador de glosas (suavizado + histéresis) -> gramática bilingüe ES/EN
         -> voz nativa (Windows SAPI5 / pyttsx3) en un hilo que no bloquea la cámara.

Modos (python src/slt_core.py --mode ...):
  setup      descarga el modelo de manos, prueba cámara y voces
  calibrate  graba TODAS tus señas del diccionario (guiado) y entrena al final
  collect    graba una seña concreta (--sign HOLA --samples 20)
  train      entrena el clasificador con tus grabaciones (data/samples)
  eval       validación cruzada por clip + latencia
  run        traductor en vivo (sin calibrar usa el modo básico de gestos universales)
  translate  prueba la gramática sin cámara (--glosses "YO QUERER AGUA")
  say/voices prueba la voz / lista voces instaladas
"""
import os, sys, time, json, queue, argparse, threading, unicodedata, urllib.request
from collections import deque
from pathlib import Path
import numpy as np

os.environ.setdefault("GLOG_minloglevel", "2"); os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
for _st in (sys.stdout, sys.stderr):  # la consola de Windows (cp1252) rompe con ¿ ñ → etc.
    try: _st.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

# --- 0. RUTAS Y CONSTANTES ---------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
SAMPLES_DIR, MODEL_PATH = ROOT / "data" / "samples", ROOT / "models" / "slt_model.npz"
TASK_PATH, LEXICON_PATH = ROOT / "models" / "gesture_recognizer.task", ROOT / "config" / "lexicon.json"
TASK_URL = "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/latest/gesture_recognizer.task"
NADA, K_STEPS, CLIP_S, FEAT_VERSION = "_NADA_", 8, 1.2, 2
CHAINS = ((0, 1, 2, 3, 4), (0, 5, 6, 7, 8), (0, 9, 10, 11, 12), (0, 13, 14, 15, 16), (0, 17, 18, 19, 20))
CH = np.array(CHAINS)
EDGES = [(c[i], c[i + 1]) for c in CHAINS for i in range(4)] + [(5, 9), (9, 13), (13, 17)]
f32 = np.float32

def norm_gloss(g):
    """'baño ' -> 'BANO' (nombre seguro para carpetas y claves del diccionario)."""
    g = unicodedata.normalize("NFKD", str(g)).encode("ascii", "ignore").decode()
    return "_".join(g.upper().split()) if g.strip("_ ") or g == NADA else ""

# --- 1. DICCIONARIO Y GRAMÁTICA BILINGÜE (glosas -> oraciones ES/EN) ---------------------------
class Translator:
    """Convierte una secuencia de glosas en oraciones naturales en español e inglés.

    Reglas: frases fijas (coincidencia más larga), interjecciones como oración propia,
    deletreo dactilológico unido en palabras, reordenamiento SOV/OSV (típico de LSC/LSM/ASL)
    a SVO, concordancia verbo-sujeto y sujeto implícito (pro-drop en ES, 'I' en EN)."""

    def __init__(s, path=LEXICON_PATH):
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        s.words = {norm_gloss(k): v for k, v in d.get("words", {}).items()}
        s.phrases = sorted(([tuple(map(norm_gloss, p["glosses"])), p] for p in d.get("phrases", [])), key=lambda x: -len(x[0]))
        s.gesture_map = {k: norm_gloss(v) for k, v in d.get("gesture_map", {}).items() if not k.startswith("_")}

    def info(s, g):
        return s.words.get(g) or ({"type": "letter"} if len(g) == 1 and g.isalpha() else {"type": "word", "es": g.lower().replace("_", " "), "en": g.lower().replace("_", " ")})

    def hint(s, g):
        w = s.info(g)
        if g == NADA: return "Sin seña: manos quietas, bajándolas o moviéndolas sin significado"
        if w["type"] == "letter": return f"Letra {g} del alfabeto manual"
        f = lambda l: w.get(f"solo_{l}") or (w[l]["1"] if isinstance(w.get(l), dict) else w.get(l, ""))
        return f"{f('es')}  /  {f('en')}"

    def translate(s, glosses, lang="es"):
        gl = [norm_gloss(g) for g in glosses if norm_gloss(g) and norm_gloss(g) != NADA]
        out, clause, i = [], [], 0
        while i < len(gl):
            ph = next((p for k, p in s.phrases if tuple(gl[i:i + len(k)]) == k), None)
            if ph:
                s._flush(clause, out, lang); out.append(ph[lang]); i += len(ph["glosses"]); continue
            g, w = gl[i], s.info(gl[i])
            if w["type"] == "letter":  # deletreo: letras consecutivas -> una palabra
                j = i
                while j < len(gl) and s.info(gl[j])["type"] == "letter": j += 1
                clause.append(("word", "".join(gl[i:j]).lower(), None)); i = j; continue
            if w["type"] == "interj": s._flush(clause, out, lang); out.append(w[lang])
            elif w["type"] == "tail": s._flush(clause, out, lang, tail=w[lang]) if clause else out.append(w.get(f"solo_{lang}", w[lang]))
            else: clause.append((w["type"], g, w))
            i += 1
        s._flush(clause, out, lang)
        return " ".join(out)

    def _flush(s, clause, out, lang, tail=None):
        if not clause: return
        if len(clause) == 1 and clause[0][2] and clause[0][2].get(f"solo_{lang}") and not tail:
            out.append(clause[0][2][f"solo_{lang}"]); clause.clear(); return
        subj = next((c for c in clause if c[0] == "pron"), None)
        person = str(subj[2].get("person", 3)) if subj else "1"
        verbs = [c for c in clause if c[0] == "verb"]
        rest = [c for c in clause if c is not subj and c[0] != "verb"]
        txt = lambda c: c[1] if c[2] is None else (c[2][lang][person] if isinstance(c[2][lang], dict) else c[2][lang])
        words = ([txt(subj)] if subj else (["I"] if verbs and lang == "en" else [])) + [txt(v) for v in verbs] + [txt(r) for r in rest]
        sent = " ".join(words)
        sent = sent[:1].upper() + sent[1:] + (f", {tail}" if tail else "")
        out.append(sent if sent[-1:] in ".!?" else sent + "."); clause.clear()

# --- 2. GEOMETRÍA DE LA MANO Y RASGOS ESPACIO-TEMPORALES ---------------------------------------
def palm_size(P):  # (...,21,3) -> (...)  promedio de muñeca-medio y ancho de nudillos
    return 0.5 * (np.linalg.norm(P[..., 9, :] - P[..., 0, :], axis=-1) + np.linalg.norm(P[..., 5, :] - P[..., 17, :], axis=-1))

def finger_angles(P):  # (...,21,3) -> (...,15) flexión entre falanges consecutivas (radianes)
    u = P[..., CH[:, 1:4], :] - P[..., CH[:, :3], :]; v = P[..., CH[:, 2:5], :] - P[..., CH[:, 1:4], :]
    cos = (u * v).sum(-1) / (np.linalg.norm(u, axis=-1) * np.linalg.norm(v, axis=-1) + 1e-8)
    return np.arccos(np.clip(cos, -1, 1)).reshape(*P.shape[:-2], 15)

def resample(fr, pr, ts, K=K_STEPS):
    """Remuestrea un clip (F,2,21,3) a K pasos equiespaciados en el tiempo (independiente de los FPS)."""
    tk = np.linspace(ts[0], ts[-1], K); P = np.zeros((K, 2, 21, 3), f32); pres = np.zeros((K, 2), f32)
    for s in range(2):
        idx = np.flatnonzero(pr[:, s]); pres[:, s] = np.interp(tk, ts, pr[:, s].astype(f32))
        if len(idx) == 0: continue
        X, ti = fr[idx, s].reshape(len(idx), 63), ts[idx]
        if len(idx) == 1: P[:, s] = X[0].reshape(21, 3); continue
        hi = np.searchsorted(ti, tk).clip(1, len(idx) - 1); lo = hi - 1
        w = ((tk - ti[lo]) / np.maximum(ti[hi] - ti[lo], 1e-9)).clip(0, 1)[:, None]
        P[:, s] = (X[lo] * (1 - w) + X[hi] * w).reshape(K, 21, 3)
    return P, pres

def clip_features(fr, pr, ts, K=K_STEPS):
    """Vector de K*(2*84+2) rasgos: por paso y mano -> forma normalizada (63), ángulos (15),
    posición de muñeca (2), trayectoria relativa (2), cambio de escala/profundidad (1), presencia (1);
    más la posición relativa entre ambas manos (2)."""
    fr, pr, ts = np.asarray(fr, f32), np.asarray(pr, bool), np.asarray(ts, np.float64)
    P, pres = resample(fr, pr, ts, K); on = (pres >= 0.5).astype(f32)
    sz = np.where(on > 0, palm_size(P), 1.0).astype(f32)
    shape = (P - P[:, :, :1]) / sz[..., None, None]
    wr = P[:, :, 0, :2]; cnt = np.maximum(on.sum(0), 1)
    msz = np.where(on.sum(0) > 0, (sz * on).sum(0) / cnt, 1.0)
    mwr = (wr * on[..., None]).sum(0) / cnt[:, None]
    rel = (wr - mwr) / msz[None, :, None]; dsc = np.log(np.maximum(sz / msz, 1e-3))[..., None]
    inter = (wr[:, 1] - wr[:, 0]) / msz[0] * (on[:, 0] * on[:, 1])[:, None]
    per = np.concatenate([shape.reshape(K, 2, 63), finger_angles(P), wr, rel, dsc, on[..., None]], -1) * on[..., None]
    return np.concatenate([per.reshape(K, -1), inter], 1).ravel().astype(f32)

FEAT_DIM = K_STEPS * (2 * 84 + 2)

def augment(fr, pr, ts, rng):
    """Aumento de datos realista sobre el clip crudo: recorte/deformación temporal, pérdida de
    cuadros, rotación/escala/traslación de cámara, variación anatómica por mano y ruido."""
    fr, pr, ts = fr.copy(), pr.copy(), ts.copy(); T = ts[-1] - ts[0]
    u = rng.uniform(0.75, 1.0); st = ts[0] + rng.uniform(0, (1 - u) * T)
    m = (ts >= st) & (ts <= st + u * T)
    if m.sum() >= 4: fr, pr, ts = fr[m], pr[m], ts[m]
    keep = rng.random(len(ts)) > 0.07; keep[[0, -1]] = True; fr, pr, ts = fr[keep], pr[keep], ts[keep]
    span = max(ts[-1] - ts[0], 1e-6); ts = ts[0] + ((ts - ts[0]) / span) ** rng.uniform(0.8, 1.25) * span
    for s in range(2):  # variación anatómica alrededor de cada muñeca
        a = np.deg2rad(rng.uniform(-8, 8)); R = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]], f32)
        w = fr[:, s, :1]; loc = fr[:, s] - w; loc[..., :2] = loc[..., :2] @ R.T; fr[:, s] = w + loc * rng.uniform(0.93, 1.07)
    a = np.deg2rad(rng.uniform(-10, 10)); R = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]], f32)
    sc = rng.uniform(0.85, 1.15); fr[..., :2] = (fr[..., :2] @ R.T) * sc + rng.uniform(-0.08, 0.08, 2); fr[..., 2] *= sc
    fr += rng.normal(0, 0.003, fr.shape).astype(f32); fr[~pr] = 0
    return fr, pr, ts

# --- 3. RED NEURONAL TinyMLP EN NUMPY PURO (desde cero) ----------------------------------------
relu = lambda z: np.maximum(0.0, z)
smax = lambda z: (lambda e: e / e.sum(-1, keepdims=True))(np.exp(z - z.max(-1, keepdims=True)))

class TinyMLP:
    """MLP denso (ReLU + softmax) con Adam, L2, dropout, label smoothing y early stopping."""

    def __init__(s, sizes=(FEAT_DIM, 128, 64, 2), seed=42):
        r = np.random.default_rng(seed); s.sizes = tuple(int(x) for x in sizes)
        s.W = [r.normal(0, np.sqrt(2 / a), (a, b)).astype(f32) for a, b in zip(s.sizes[:-1], s.sizes[1:])]
        s.b = [np.zeros((1, b), f32) for b in s.sizes[1:]]
        s.mu, s.sd, s.meta = np.zeros((1, s.sizes[0]), f32), np.ones((1, s.sizes[0]), f32), {}

    def _fwd(s, X, drop=0.0, rng=None):
        A, Z, M = [((X - s.mu) / s.sd).astype(f32)], [], []
        for i, (W, b) in enumerate(zip(s.W, s.b)):
            z = A[-1] @ W + b; Z.append(z)
            if i < len(s.W) - 1:
                m = (rng.random(z.shape) >= drop).astype(f32) / (1 - drop) if drop > 0 else None
                A.append(relu(z) * (m if m is not None else 1)); M.append(m)
        return A, Z, M, smax(Z[-1])

    def proba(s, X): return s._fwd(np.atleast_2d(np.asarray(X, f32)))[3]

    def fit(s, X, Y, Xv=None, Yv=None, epochs=60, lr=2e-3, bs=64, l2=1e-4, drop=0.25, smooth=0.05, patience=15, seed=0, log=print):
        rng = np.random.default_rng(seed); C = s.sizes[-1]; N = len(Y)
        s.mu = X.mean(0, keepdims=True).astype(f32); s.sd = np.maximum(X.std(0, keepdims=True), 0.05).astype(f32)
        Yoh = np.full((N, C), smooth / C, f32); Yoh[np.arange(N), Y] += 1 - smooth
        P = s.W + s.b; Mo = [np.zeros_like(p) for p in P]; Vo = [np.zeros_like(p) for p in P]
        t, best, best_ep, best_params, wait, L = 0, (-1, 1e9), 0, None, 0, len(s.W)
        for ep in range(1, epochs + 1):
            perm = rng.permutation(N); tl = 0.0
            for i in range(0, N, bs):
                idx = perm[i:i + bs]; A, Z, M, pr = s._fwd(X[idx], drop, rng); m = len(idx)
                tl += -float((Yoh[idx] * np.log(pr + 1e-9)).sum()); d = (pr - Yoh[idx]) / m; gW, gb = [None] * L, [None] * L
                for k in reversed(range(L)):
                    gW[k] = A[k].T @ d + l2 * s.W[k]; gb[k] = d.sum(0, keepdims=True)
                    if k > 0: d = (d @ s.W[k].T) * (Z[k - 1] > 0) * (M[k - 1] if M[k - 1] is not None else 1)
                t += 1
                for j, (p, g) in enumerate(zip(s.W + s.b, gW + gb)):
                    Mo[j] = 0.9 * Mo[j] + 0.1 * g; Vo[j] = 0.999 * Vo[j] + 0.001 * g * g
                    p -= lr * (Mo[j] / (1 - 0.9 ** t)) / (np.sqrt(Vo[j] / (1 - 0.999 ** t)) + 1e-8)
            msg = f"  época {ep:3d}  pérdida={tl / N:.4f}"
            if Xv is not None and len(Yv):
                pv = s.proba(Xv); acc = float((pv.argmax(1) == Yv).mean()); vl = -float(np.log(pv[np.arange(len(Yv)), Yv] + 1e-9).mean())
                msg += f"  val_acc={acc * 100:6.2f}%  val_loss={vl:.4f}"
                if (acc, -vl) > (best[0], -best[1]): best, best_ep, wait, best_params = (acc, vl), ep, 0, ([w.copy() for w in s.W], [b.copy() for b in s.b])
                else: wait += 1
                if wait >= patience: log(msg + "  (parada temprana)"); break
            if ep == 1 or ep % 10 == 0: log(msg)
        if best_params: s.W, s.b = best_params
        return best_ep or ep, (best[0] if best_params else None)

    def save(s, path=MODEL_PATH, **meta):
        s.meta.update(meta); Path(path).parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, mu=s.mu, sd=s.sd, sizes=np.array(s.sizes), meta=np.array(json.dumps(s.meta, ensure_ascii=False)),
                            **{f"W{i}": w for i, w in enumerate(s.W)}, **{f"b{i}": b for i, b in enumerate(s.b)})

    @classmethod
    def load(cls, path=MODEL_PATH):
        d = np.load(path); net = cls(tuple(d["sizes"])); net.mu, net.sd = d["mu"], d["sd"]
        net.W = [d[f"W{i}"] for i in range(len(net.W))]; net.b = [d[f"b{i}"] for i in range(len(net.b))]
        net.meta = json.loads(str(d["meta"]))
        if net.meta.get("feat_version") != FEAT_VERSION: raise ValueError("Modelo de otra versión: vuelve a entrenar (--mode train).")
        return net

# --- 4. DATASET PERSONAL (clips crudos de landmarks por seña) ----------------------------------
def save_clip(gloss, fr, pr, ts, left_handed=False):
    d = SAMPLES_DIR / gloss; d.mkdir(parents=True, exist_ok=True)
    p = d / f"clip_{time.strftime('%Y%m%d_%H%M%S')}_{int(time.time() * 1000) % 1000:03d}.npz"
    np.savez_compressed(p, frames=np.asarray(fr, f32), present=np.asarray(pr, bool), times=np.asarray(ts, np.float64), left_handed=left_handed)
    return p

def load_samples(root=SAMPLES_DIR):
    out = []
    for d in sorted(Path(root).glob("*")) if Path(root).exists() else []:
        for f in sorted(d.glob("*.npz")):
            try:
                z = np.load(f); out.append((d.name, z["frames"], z["present"], z["times"]))
            except Exception as e: print(f"[!] Clip dañado ignorado {f.name}: {e}")
    return out

def count_samples(gloss): d = SAMPLES_DIR / gloss; return len(list(d.glob("*.npz"))) if d.exists() else 0

def build_xy(samples, classes, n_aug, rng, include_orig=True):
    X, Y = [], []
    for g, fr, pr, ts in samples:
        y = classes.index(g)
        if include_orig: X.append(clip_features(fr, pr, ts)); Y.append(y)
        for _ in range(n_aug[g] if isinstance(n_aug, dict) else n_aug): X.append(clip_features(*augment(fr, pr, ts, rng))); Y.append(y)
    return np.array(X, f32).reshape(-1, FEAT_DIM), np.array(Y, np.int64)

def split_clips(samples, val_frac, rng):
    tr, va = [], []
    for g in sorted({s[0] for s in samples}):
        cs = [s for s in samples if s[0] == g]; idx = rng.permutation(len(cs)); nv = int(round(len(cs) * val_frac)) if len(cs) >= 5 else 0
        va += [cs[i] for i in idx[:nv]]; tr += [cs[i] for i in idx[nv:]]
    return tr, va

def train_model(samples, epochs=80, seed=42, log=print, final_refit=True):
    """Entrena con validación por clip (sin fuga de aumentos) y reentrena con todos los datos."""
    classes = sorted({s[0] for s in samples}); rng = np.random.default_rng(seed)
    per = {g: sum(1 for s in samples if s[0] == g) for g in classes}
    n_aug = {g: int(np.clip(np.ceil(320 / per[g]), 8, 40)) for g in classes}
    tr, va = split_clips(samples, 0.2, rng)
    log(f"[*] {len(classes)} clases, {len(samples)} clips ({len(tr)} entrenamiento / {len(va)} validación). Generando aumentos...")
    Xtr, Ytr = build_xy(tr, classes, n_aug, rng); Xv, Yv = build_xy(va, classes, 2, rng) if va else (None, None)
    net = TinyMLP((FEAT_DIM, 128, 64, len(classes)), seed)
    best_ep, val_acc = net.fit(Xtr, Ytr, Xv, Yv, epochs=epochs, seed=seed, log=log)
    if final_refit and va:
        log(f"[*] Reentrenando con el 100% de los clips durante {max(best_ep, 15)} épocas...")
        Xa, Ya = build_xy(samples, classes, n_aug, rng); net = TinyMLP((FEAT_DIM, 128, 64, len(classes)), seed)
        net.fit(Xa, Ya, epochs=max(best_ep, 15), seed=seed, log=log)
    net.meta = dict(classes=classes, feat_version=FEAT_VERSION, k_steps=K_STEPS, val_acc=val_acc, clips=per, trained=time.strftime("%Y-%m-%d %H:%M"))
    return net, val_acc

# --- 5. SEGUIMIENTO DE MANOS (MediaPipe Tasks: GestureRecognizer = landmarks + gestos) ----------
def ensure_task(path=TASK_PATH):
    path = Path(path)
    if path.exists() and path.stat().st_size > 1_000_000: return path
    path.parent.mkdir(parents=True, exist_ok=True); tmp = path.with_suffix(".part")
    print(f"[*] Descargando modelo de manos de MediaPipe (~8 MB) -> {path.name}")
    urllib.request.urlretrieve(TASK_URL, tmp); tmp.replace(path); return path

class Obs:
    __slots__ = ("hands", "present", "gestures", "raw")
    def __init__(s): s.hands, s.present, s.gestures, s.raw = np.zeros((2, 21, 3), f32), np.zeros(2, bool), [None, None], [None, None]

class HandTracker:
    """Ranura 0 = mano dominante, 1 = la otra. Coordenadas centradas e isotrópicas
    (x,y,z escalados por la altura de imagen). Para zurdos se espeja el eje x."""

    def __init__(s, left_handed=False, min_conf=0.6):
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision
        s.mp, s.left, s.ts = mp, left_handed, 0
        opts = vision.GestureRecognizerOptions(base_options=BaseOptions(model_asset_path=str(ensure_task())), running_mode=vision.RunningMode.VIDEO,
                                               num_hands=2, min_hand_detection_confidence=min_conf, min_hand_presence_confidence=min_conf, min_tracking_confidence=0.5)
        s.rec = vision.GestureRecognizer.create_from_options(opts)

    def process(s, frame_bgr):
        import cv2
        h, w = frame_bgr.shape[:2]; img = s.mp.Image(image_format=s.mp.ImageFormat.SRGB, data=np.ascontiguousarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)))
        s.ts = max(s.ts + 1, int(time.monotonic() * 1000)); r = s.rec.recognize_for_video(img, s.ts); o = Obs(); cands = []
        for i, lm in enumerate(r.hand_landmarks):
            P = np.array([[p.x, p.y, p.z] for p in lm], f32)
            lab = r.handedness[i][0].category_name if r.handedness and r.handedness[i] else "Right"
            g = r.gestures[i][0] if r.gestures and i < len(r.gestures) and r.gestures[i] else None
            cands.append([lab, P, (g.category_name, float(g.score)) if g else None])
        dom = "Left" if s.left else "Right"
        if len(cands) == 2 and cands[0][0] == cands[1][0]:  # misma etiqueta: decide por posición (imagen espejada)
            cands.sort(key=lambda c: c[1][:, 0].mean(), reverse=not s.left); cands[0][0], cands[1][0] = dom, "x"
        for lab, P, g in cands:
            k = 0 if lab == dom else 1
            if o.present[k]: k = 1 - k
            Q = np.stack([(P[:, 0] - 0.5) * w / h, P[:, 1] - 0.5, P[:, 2] * w / h], 1)
            if s.left: Q[:, 0] = -Q[:, 0]
            o.hands[k], o.present[k], o.gestures[k], o.raw[k] = Q, True, g, P
        return o

    def close(s):
        try: s.rec.close()
        except Exception: pass

def open_camera(idx=0, width=1280, height=720):
    import cv2
    backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY] if sys.platform == "win32" else [cv2.CAP_ANY]
    for b in backends:
        cap = cv2.VideoCapture(idx, b)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width); cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            ok, _ = cap.read()
            if ok: return cap
        cap.release()
    raise RuntimeError(f"No se pudo abrir la cámara {idx}. Revisa que esté conectada, que otra app no la use y los permisos de privacidad de cámara.")

# --- 6. VOZ BILINGÜE ASÍNCRONA (SAPI5 nativo en Windows, pyttsx3 en macOS/Linux) ---------------
class Speaker:
    """Hilo de voz con cola. En Windows usa SAPI5 vía COM (estable en hilos, a diferencia de
    pyttsx3.runAndWait que se cuelga tras la primera frase) y elige la voz por idioma (LCID)."""

    def __init__(s, rate=0):
        s.rate, s.q, s.ready, s.voices, s.backend = rate, queue.Queue(), threading.Event(), {}, "ninguno"
        threading.Thread(target=s._run, daemon=True).start(); s.ready.wait(10)

    def say(s, text, lang="es"):
        if text: s.q.put((text, lang))

    def wait(s): s.q.join()

    def _run(s):
        speak = None
        if sys.platform == "win32":
            try: speak = s._sapi()
            except Exception as e: print(f"[!] SAPI no disponible ({e}); probando pyttsx3.")
        if speak is None:
            try: speak = s._pyttsx3()
            except Exception as e: print(f"[!] Sin motor de voz ({e}). Solo se mostrará texto.")
        s.ready.set()
        while True:
            text, lang = s.q.get()
            try:
                if speak: speak(text, lang)
                else: print(f"[VOZ {lang.upper()}] {text}")
            except Exception as e: print(f"[!] Error de voz: {e}")
            finally: s.q.task_done()

    def _sapi(s):
        import comtypes, comtypes.client
        comtypes.CoInitialize(); sp = comtypes.client.CreateObject("SAPI.SpVoice"); toks = sp.GetVoices()
        for i in range(toks.Count):
            t = toks.Item(i)
            try: lang = {0x0A: "es", 0x09: "en"}.get(int(t.GetAttribute("Language").split(";")[0], 16) & 0x3FF)
            except Exception: lang = None
            if lang and lang not in s.voices: s.voices[lang] = (t, t.GetDescription())
        sp.Rate = int(s.rate); s.backend = "SAPI5"
        def speak(text, lang):
            if lang in s.voices: sp.Voice = s.voices[lang][0]
            sp.Speak(text, 0)
        return speak

    def _pyttsx3(s):
        import pyttsx3
        keys = {"es": ("spanish", "español", "es_", "es-", "helena", "sabina", "monica", "paulina"), "en": ("english", "en_", "en-", "zira", "david", "samantha", "alex")}
        eng = pyttsx3.init()
        for v in eng.getProperty("voices"):
            nm = f"{v.name} {v.id} {v.languages}".lower()
            for lang, ks in keys.items():
                if lang not in s.voices and any(k in nm for k in ks): s.voices[lang] = (v.id, v.name)
        eng.stop(); s.backend = "pyttsx3"
        def speak(text, lang):  # motor nuevo por frase: evita el bloqueo conocido de runAndWait
            e = pyttsx3.init(); e.setProperty("rate", 165 + 15 * s.rate)
            if lang in s.voices: e.setProperty("voice", s.voices[lang][0])
            e.say(text); e.runAndWait(); e.stop()
        return speak

# --- 7. HUD (subtítulos UTF-8 con tildes/ñ sobre el video) --------------------------------------
class HUD:
    def __init__(s):
        from PIL import ImageFont
        s.fonts = {}
        for size in (20, 26, 40):
            for name in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf"):
                try: s.fonts[size] = ImageFont.truetype(name, size); break
                except Exception: continue
            else: s.fonts[size] = ImageFont.load_default(size=size)

    def render(s, frame, obs=None, top=(), bottom=(), center=None, bar=None, rec=False):
        import cv2
        from PIL import Image, ImageDraw
        h, w = frame.shape[:2]
        if obs is not None:
            for k, col in ((0, (90, 230, 120)), (1, (60, 170, 255))):
                if obs.raw[k] is None: continue
                pts = [(int(x * w), int(y * h)) for x, y, _ in obs.raw[k]]
                for a, b in EDGES: cv2.line(frame, pts[a], pts[b], col, 2, cv2.LINE_AA)
                for p in pts: cv2.circle(frame, p, 3, (255, 255, 255), -1, cv2.LINE_AA)
        hb = 30 * max(len(bottom), 1) + 16; ov = frame.copy()
        cv2.rectangle(ov, (0, 0), (w, 30 * max(len(top), 1) + 14), (20, 20, 20), -1); cv2.rectangle(ov, (0, h - hb), (w, h), (12, 12, 12), -1)
        frame = cv2.addWeighted(ov, 0.72, frame, 0.28, 0)
        if bar is not None: cv2.rectangle(frame, (0, h - hb - 6), (int(w * float(np.clip(bar[0], 0, 1))), h - hb), bar[1], -1)
        if rec: cv2.circle(frame, (w - 30, 30 * len(top) + 40), 12, (0, 0, 255), -1)
        im = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)); dr = ImageDraw.Draw(im)
        for i, (t, c) in enumerate(top): dr.text((14, 8 + 30 * i), t, fill=c, font=s.fonts[20])
        for i, (t, c) in enumerate(bottom): dr.text((14, h - hb + 8 + 30 * i), t, fill=c, font=s.fonts[26 if i else 20])
        if center:
            f = s.fonts[40]; tw = dr.textlength(center[0], font=f)
            dr.text(((w - tw) / 2 + 2, h / 2 - 18), center[0], fill=(0, 0, 0), font=f); dr.text(((w - tw) / 2, h / 2 - 20), center[0], fill=center[1], font=f)
        return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)

# --- 8. DECODIFICADOR DE GLOSAS (suavizado EMA + histéresis + liberación) ----------------------
class GlossDecoder:
    def __init__(s, classes, thr=0.7, hold=3, alpha=0.55, cooldown=0.35, repeat_s=2.5):
        s.classes, s.thr, s.hold, s.alpha, s.cooldown, s.repeat_s = list(classes), thr, hold, alpha, cooldown, repeat_s
        s.ema, s.cand, s.streak, s.last, s.last_t, s.released = None, None, 0, None, -1e9, True
        s.label, s.conf, s.active = None, 0.0, False

    def update(s, probs, now, hands_visible=True):
        if probs is None:
            s.ema, s.streak, s.label, s.conf, s.active = None, 0, None, 0.0, False
            if not hands_visible: s.released = True
            return None
        s.ema = probs if s.ema is None else s.alpha * s.ema + (1 - s.alpha) * probs
        i = int(np.argmax(s.ema)); s.label, s.conf = s.classes[i], float(s.ema[i])
        s.active = s.label != NADA and s.conf >= s.thr
        if not s.active:
            s.streak = 0
            if s.label == NADA and s.conf >= 0.5: s.released = True
            return None
        s.streak, s.cand = (s.streak + 1, s.cand) if s.label == s.cand else (1, s.label)
        if s.streak >= s.hold and now - s.last_t >= s.cooldown and (s.label != s.last or s.released or now - s.last_t >= s.repeat_s):
            s.last, s.last_t, s.released, s.streak, s.ema = s.label, now, False, 0, None
            return s.last
        return None

def basic_probs(obs, classes, gmap, min_score=0.6):
    """Modo básico: convierte el gesto universal de MediaPipe en una distribución sobre las glosas."""
    if not obs.present.any(): return None
    p = np.zeros(len(classes), f32); best = max((g for g in obs.gestures if g and g[0] in gmap and gmap[g[0]] in classes), key=lambda g: g[1], default=None)
    if best and best[1] >= min_score: p[classes.index(gmap[best[0]])] = best[1]; p[0] = 1 - best[1]
    else: p[0] = 1.0
    return p

# --- 9. MODOS DE USO -----------------------------------------------------------------------------
GREEN, BLUE, WHITE, YELLOW, RED, GRAY = (90, 240, 150), (150, 200, 255), (255, 255, 255), (255, 220, 90), (255, 110, 110), (170, 170, 170)

class Session:
    """Cámara + seguimiento + HUD reutilizados por los modos de grabación y traducción."""
    WIN = "SLT-Core | Traductor de Señas ES/EN"

    def __init__(s, args):
        import cv2
        s.cv2, s.cap, s.tracker, s.hud = cv2, open_camera(args.cam), HandTracker(args.left_handed), HUD()
        cv2.namedWindow(s.WIN, cv2.WINDOW_NORMAL); cv2.resizeWindow(s.WIN, 1280, 720)

    def step(s):
        ok, frame = s.cap.read()
        if not ok:
            time.sleep(0.05); ok, frame = s.cap.read()
            if not ok: raise RuntimeError("La cámara dejó de enviar imágenes.")
        frame = s.cv2.flip(frame, 1); return frame, s.tracker.process(frame), time.monotonic()

    def show(s, img):
        s.cv2.imshow(s.WIN, img); k = s.cv2.waitKey(1) & 0xFF
        try:
            if s.cv2.getWindowProperty(s.WIN, s.cv2.WND_PROP_VISIBLE) < 1: return 27
        except Exception: pass
        return k

    def close(s): s.cap.release(); s.tracker.close(); s.cv2.destroyAllWindows()

def record_session(glosses, n, args, tr):
    """Grabación guiada: por cada glosa espera ESPACIO, luego graba n clips de --clip segundos."""
    S = Session(args); saved = {}
    try:
        for gi, g in enumerate(glosses):
            while True:  # pantalla de espera
                frame, obs, _ = S.step()
                k = S.show(S.hud.render(frame, obs, top=[(f"Seña {gi + 1}/{len(glosses)}: {g}   ({count_samples(g)} clips guardados)", GREEN), (tr.hint(g), BLUE)],
                                        bottom=[("ESPACIO = empezar a grabar   S = saltar seña   Q = salir", YELLOW)], center=(f"Prepárate: {g}", WHITE)))
                if k in (ord("q"), 27): return saved
                if k in (ord("s"),): break
                if k == 32: break
            if k == ord("s"): continue
            done = 0
            while done < n:
                t_end = time.monotonic() + (3.0 if done == 0 else args.gap)
                while (now := time.monotonic()) < t_end:  # cuenta regresiva
                    frame, obs, now = S.step()
                    k = S.show(S.hud.render(frame, obs, top=[(f"{g}: clip {done + 1}/{n}", GREEN), (tr.hint(g), BLUE)], bottom=[("Q = salir", GRAY)],
                                            center=(f"{g} en {t_end - now:0.1f} s", YELLOW)))
                    if k in (ord("q"), 27): return saved
                frs, prs, tss, t0 = [], [], [], time.monotonic()
                while (now := time.monotonic()) - t0 < args.clip:  # grabación
                    frame, obs, now = S.step(); frs.append(obs.hands); prs.append(obs.present); tss.append(now - t0)
                    S.show(S.hud.render(frame, obs, top=[(f"GRABANDO {g}: clip {done + 1}/{n}", RED), (tr.hint(g), BLUE)], bottom=[("Haz la seña completa ahora", WHITE)],
                                        bar=((now - t0) / args.clip, (0, 0, 255)), rec=True))
                prs = np.array(prs, bool); vis = prs.any(1).mean() if len(prs) else 0
                if g != NADA and (len(tss) < 6 or vis < 0.6):
                    msg = "No se vieron bien tus manos: repite el clip"
                else:
                    save_clip(g, frs, prs, tss, args.left_handed); done += 1; saved[g] = saved.get(g, 0) + 1; msg = f"Guardado ({count_samples(g)} clips de {g})"
                t_msg = time.monotonic() + 0.6
                while time.monotonic() < t_msg:
                    frame, obs, _ = S.step(); S.show(S.hud.render(frame, obs, top=[(g, GREEN)], bottom=[(msg, YELLOW)], center=(msg.split(":")[0], YELLOW)))
    finally:
        S.close()
    return saved

def mode_train(args, log=print):
    samples = load_samples()
    classes = sorted({s[0] for s in samples})
    if len(classes) < 2: sys.exit("[X] Necesitas al menos 2 señas grabadas. Usa --mode calibrate o --mode collect --sign HOLA.")
    if NADA not in classes: log(f"[!] Recomendado: graba la clase {NADA} (manos sin seña) para evitar falsos positivos: --mode collect --sign {NADA}")
    for g in classes:
        if count_samples(g) < 8: log(f"[!] {g} tiene solo {count_samples(g)} clips; se recomiendan 15 o más.")
    t0 = time.time(); net, val = train_model(samples, epochs=args.epochs, log=log)
    net.save(MODEL_PATH, clip_s=args.clip, left_handed=args.left_handed)
    vtxt = f"{val * 100:.1f}%" if val is not None else "n/d (graba ≥5 clips por seña)"
    log(f"[OK] Modelo guardado en {MODEL_PATH.relative_to(ROOT)}  |  clases={len(classes)}  |  exactitud validación={vtxt}  |  {time.time() - t0:.1f} s")
    return net

def mode_eval(args):
    samples = load_samples(); classes = sorted({s[0] for s in samples})
    if len(classes) < 2: sys.exit("[X] No hay suficientes señas grabadas para evaluar.")
    rng = np.random.default_rng(0); folds = 4; conf = np.zeros((len(classes), len(classes)), int)
    by = {g: [s for s in samples if s[0] == g] for g in classes}; order = {g: rng.permutation(len(v)) for g, v in by.items()}
    print(f"[*] Validación cruzada {folds}-fold por clip ({len(samples)} clips, {len(classes)} clases)...")
    for f in range(folds):
        te = [by[g][i] for g in classes for j, i in enumerate(order[g]) if j % folds == f]
        trn = [by[g][i] for g in classes for j, i in enumerate(order[g]) if j % folds != f]
        if not te or len({s[0] for s in trn}) < len(classes): continue
        net, _ = train_model(trn, epochs=args.epochs, seed=f, log=lambda *_: None, final_refit=False)
        for g, fr, pr, ts in te: conf[classes.index(g), int(net.proba(clip_features(fr, pr, ts)).argmax())] += 1
        print(f"  fold {f + 1}: acumulado {np.trace(conf) / max(conf.sum(), 1) * 100:.1f}%")
    print(f"\n[EVAL] Exactitud por clip (datos no vistos): {np.trace(conf) / max(conf.sum(), 1) * 100:.2f}%")
    for i, g in enumerate(classes):
        errs = ", ".join(f"{classes[j]}×{conf[i, j]}" for j in np.argsort(-conf[i]) if j != i and conf[i, j])
        print(f"  {g:>12s}: {conf[i, i]}/{conf[i].sum()}  {('confunde con ' + errs) if errs else ''}")
    if MODEL_PATH.exists():
        net = TinyMLP.load(MODEL_PATH); x = clip_features(*samples[0][1:]); t0 = time.perf_counter()
        for _ in range(200): net.proba(x)
        t1 = time.perf_counter()
        for _ in range(50): clip_features(*samples[0][1:])
        print(f"[EVAL] Latencia: clasificador {(t1 - t0) / 200 * 1000:.3f} ms + rasgos {(time.perf_counter() - t1) / 50 * 1000:.3f} ms  |  modelo {MODEL_PATH.stat().st_size / 1024:.0f} KB")

def mode_run(args):
    tr, spk = Translator(), Speaker(args.rate)
    net = None
    if MODEL_PATH.exists():
        try: net = TinyMLP.load(MODEL_PATH)
        except Exception as e: print(f"[!] {e}")
    if net:
        classes, clip_s = net.meta["classes"], float(net.meta.get("clip_s", CLIP_S)); args.left_handed = args.left_handed or net.meta.get("left_handed", False)
        mode_txt = f"PERSONAL ({len(classes) - (NADA in classes)} señas)"
    else:
        classes, clip_s = [NADA] + sorted(set(tr.gesture_map.values())), CLIP_S
        mode_txt = "BÁSICO (gestos universales; calibra con --mode calibrate)"; print("[i] Sin modelo personal: modo básico con gestos universales de MediaPipe.")
    print(f"[i] Voz: {spk.backend}  |  voces: " + ", ".join(f"{k}={v[1]}" for k, v in spk.voices.items()))
    for lg in ("es", "en"):
        if lg not in spk.voices: print(f"[!] No hay voz instalada para '{lg}': se leerá con la voz por defecto. (Windows: Configuración > Hora e idioma > Voz)")
    dec = GlossDecoder(classes, thr=args.thr); S = Session(args); buf = deque(); glosses = []
    lang_cycle = ["es", "en", "both"]; out_lang = args.lang; tx = {"es": "", "en": ""}; last_active = time.monotonic()

    def speak_now():
        nonlocal glosses
        if not glosses: return
        tx.update(es=tr.translate(glosses, "es"), en=tr.translate(glosses, "en"))
        for lg in (("es", "en") if out_lang == "both" else (out_lang,)): spk.say(tx[lg], lg)
        print(f"[{' '.join(glosses)}]  ES: {tx['es']}  |  EN: {tx['en']}"); glosses = []
    try:
        while True:
            frame, obs, now = S.step(); probs = None; vis = bool(obs.present.any())
            if net:
                buf.append((now, obs.hands, obs.present))
                while buf and now - buf[0][0] > clip_s: buf.popleft()
                if len(buf) >= 4 and buf[-1][0] - buf[0][0] >= 0.6 * clip_s:
                    pr = np.array([b[2] for b in buf])
                    if pr.any(1).mean() >= 0.5:
                        probs = net.proba(clip_features(np.array([b[1] for b in buf]), pr, np.array([b[0] for b in buf])))[0]
            else:
                probs = basic_probs(obs, classes, tr.gesture_map)
            g = dec.update(probs, now, vis)
            if dec.active or vis and dec.label not in (None, NADA): last_active = now
            if g:
                glosses.append(g); buf.clear(); last_active = now
                tx.update(es=tr.translate(glosses, "es"), en=tr.translate(glosses, "en"))
            if glosses and now - last_active >= args.pause: speak_now()
            seña = f"{dec.label} {dec.conf * 100:.0f}%" if dec.label and dec.label != NADA else ("(sin seña)" if vis else "(sin manos)")
            img = S.hud.render(frame, obs,
                               top=[(f"SLT-Core  |  Modo {mode_txt}  |  Voz: {out_lang.upper()}  |  Seña: {seña}", GREEN),
                                    ("L = idioma voz   ESPACIO = hablar ya   RETROCESO = borrar   C = limpiar   Q = salir", GRAY)],
                               bottom=[(f"Glosas: {' → '.join(glosses) if glosses else '(haz tus señas; pausa para hablar)'}", BLUE),
                                       (f"[ES] {tx['es']}", WHITE), (f"[EN] {tx['en']}", (200, 255, 190))],
                               bar=((now - last_active) / args.pause, (0, 200, 255)) if glosses else (dec.conf if dec.active else 0, (90, 230, 120)))
            k = S.show(img)
            if k in (ord("q"), 27): break
            elif k == ord("l"): out_lang = lang_cycle[(lang_cycle.index(out_lang) + 1) % 3]
            elif k == 32: speak_now()
            elif k == 8 and glosses: glosses.pop(); tx.update(es=tr.translate(glosses, "es"), en=tr.translate(glosses, "en"))
            elif k == ord("c"): glosses, tx["es"], tx["en"] = [], "", ""
    finally:
        S.close()

def mode_setup(args):
    import cv2, mediapipe as mp
    print(f"[i] Python {sys.version.split()[0]} | NumPy {np.__version__} | OpenCV {cv2.__version__} | MediaPipe {mp.__version__}")
    print(f"[OK] Modelo de manos: {ensure_task().relative_to(ROOT)}")
    HandTracker().close(); print("[OK] MediaPipe GestureRecognizer inicializado.")
    try:
        cap = open_camera(args.cam); print(f"[OK] Cámara {args.cam}: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}"); cap.release()
    except Exception as e: print(f"[!] {e}")
    mode_voices(args, test=not args.no_voice)
    print(f"[i] Señas grabadas: {len(load_samples())} clips  |  Modelo personal: {'sí' if MODEL_PATH.exists() else 'no (usa --mode calibrate)'}")

def mode_voices(args, test=False):
    spk = Speaker(args.rate); print(f"[i] Motor de voz: {spk.backend}")
    for lg in ("es", "en"): print(f"    {lg}: {spk.voices[lg][1] if lg in spk.voices else 'NO INSTALADA (se usará la voz por defecto)'}")
    if test: spk.say("Hola, el traductor está listo.", "es"); spk.say("Hello, the translator is ready.", "en"); spk.wait()

def main(argv=None):
    ap = argparse.ArgumentParser(description="SLT-Core: traductor bilingüe de lengua de señas (ES/EN)")
    ap.add_argument("--mode", choices=["setup", "calibrate", "collect", "train", "eval", "run", "translate", "say", "voices"], default="run")
    ap.add_argument("--sign", default="HOLA", help="glosa a grabar en --mode collect (ej. HOLA, AGUA, _NADA_)")
    ap.add_argument("--signs", default="", help="lista de glosas para calibrate separadas por coma (por defecto: todo el diccionario)")
    ap.add_argument("--samples", type=int, default=15, help="clips por seña")
    ap.add_argument("--clip", type=float, default=CLIP_S, help="duración de cada clip/ventana en segundos")
    ap.add_argument("--gap", type=float, default=1.2, help="pausa entre clips al grabar")
    ap.add_argument("--epochs", type=int, default=80)
    ap.add_argument("--cam", type=int, default=0)
    ap.add_argument("--lang", choices=["es", "en", "both"], default="es", help="idioma de la voz al iniciar")
    ap.add_argument("--thr", type=float, default=0.7, help="confianza mínima para aceptar una seña")
    ap.add_argument("--pause", type=float, default=2.0, help="segundos sin señas para pronunciar la frase")
    ap.add_argument("--rate", type=int, default=0, help="velocidad de voz (-10..10)")
    ap.add_argument("--left-handed", action="store_true", help="mano dominante izquierda")
    ap.add_argument("--glosses", default="", help="glosas para --mode translate")
    ap.add_argument("--text", default="Hola, ¿cómo estás?", help="texto para --mode say")
    ap.add_argument("--no-voice", action="store_true")
    a = ap.parse_args(argv)
    if a.mode == "setup": mode_setup(a)
    elif a.mode in ("collect", "calibrate"):
        tr = Translator()
        if a.mode == "collect": gl = [norm_gloss(a.sign)]
        else: gl = [norm_gloss(x) for x in a.signs.split(",") if norm_gloss(x)] or [g for g, w in tr.words.items() if w["type"] != "letter"] + [NADA]
        if not all(gl): sys.exit("[X] Glosa inválida.")
        saved = record_session(gl, a.samples, a, tr); print(f"[OK] Clips guardados: {saved or 'ninguno'}")
        if a.mode == "calibrate" and saved: mode_train(a)
    elif a.mode == "train": mode_train(a)
    elif a.mode == "eval": mode_eval(a)
    elif a.mode == "run": mode_run(a)
    elif a.mode == "translate":
        tr = Translator(); g = a.glosses.replace(",", " ").split()
        print(f"Glosas: {g}\n  ES: {tr.translate(g, 'es')}\n  EN: {tr.translate(g, 'en')}")
    elif a.mode == "say":
        spk = Speaker(a.rate); spk.say(a.text, a.lang if a.lang != "both" else "es"); spk.wait()
    elif a.mode == "voices": mode_voices(a)

if __name__ == "__main__":
    main()
