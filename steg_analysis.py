"""
steg_analysis.py  -  NEW feature module (does not modify the trained model)

Detection report for an image, combining:
  1. the ORIGINAL trained model (stego_model.pkl, unchanged) -> probability
  2. payload-signature scan   (finds the length header + Fernet token that
                               hide_message.py / steg_core.py write)
  3. periodic-LSB test        (base64 text has bit-7 = 0 in every byte, which
                               leaves a period-8 pattern in the LSB plane)
  4. plain LSB statistics     (mean, transition rate)

Why not only the model?  Global variance / edge count / mean intensity barely
change when LSBs flip, so the ML model alone cannot see the embedding.  The
extra checks are cheap and far more reliable for this tool's own output.
"""
import os
import pickle
import warnings

import cv2
import numpy as np

from hide_message import _read_image_array

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(HERE, "stego_model.pkl")
FEATURE_NAMES = ["variance", "edge_count", "mean_intensity"]      # model inputs

# Extended feature names (used by build_dataset.py / evaluation_v2.py)
EXT_FEATURE_NAMES = FEATURE_NAMES + [
    "lsb_mean", "lsb_transition", "trans_gap_max", "phase_bias",
]

_WINDOWS = (0.005, 0.01, 0.02, 0.05, 0.10)
_model_cache = {}


# ---------------------------------------------------------------------------
# 1. Original model (unchanged)
# ---------------------------------------------------------------------------
def model_features(img_rgb):
    """The exact 3 features used by create_dataset.py / train_model.py."""
    gray = cv2.cvtColor(np.ascontiguousarray(img_rgb), cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    return [float(np.var(gray)), int(np.sum(edges > 0)), float(np.mean(gray))]


def load_model(path=MODEL_PATH):
    if path not in _model_cache:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")          # sklearn version notice
            with open(path, "rb") as f:
                _model_cache[path] = pickle.load(f)
    return _model_cache[path]


def model_predict(img_rgb, model_path=MODEL_PATH):
    """Return (label 0/1, probability of 'stego') or None if model missing."""
    try:
        import pandas as pd
        model = load_model(model_path)
        row = pd.DataFrame([model_features(img_rgb)], columns=FEATURE_NAMES)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            proba = model.predict_proba(row)[0]
            classes = list(model.classes_)
        p_stego = float(proba[classes.index(1)]) if 1 in classes else 0.0
        return int(p_stego >= 0.5), p_stego
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 2. Payload signature scan
# ---------------------------------------------------------------------------
def signature_scan(img_rgb):
    """
    Look for the sequential payload written by this project:
      first 32 LSBs  = plausible length,   next 32 LSBs = b"gAAA"
    (every Fernet token starts with 'gAAA'). False-positive chance ~ 1e-13.
    """
    flat = np.ascontiguousarray(img_rgb, dtype=np.uint8).reshape(-1)
    max_token = flat.size // 8 - 4
    if max_token <= 0:
        return {"found": False, "payload_bytes": 0}
    lsb = flat[:64] & 1
    n = int.from_bytes(np.packbits(lsb[:32]).tobytes(), "big")
    tag = np.packbits(lsb[32:64]).tobytes()
    found = 0 < n <= max_token and tag == b"gAAA"
    return {"found": bool(found), "payload_bytes": int(n) if found else 0}


# ---------------------------------------------------------------------------
# 3 + 4. LSB statistics
# ---------------------------------------------------------------------------
def lsb_statistics(img_rgb):
    flat = np.ascontiguousarray(img_rgb, dtype=np.uint8).reshape(-1)
    if flat.size == 0:
        raise ValueError("Cannot calculate LSB statistics for an empty image.")
    lsb = (flat & 1).astype(np.int8)
    n = lsb.size
    trans = (lsb[1:] != lsb[:-1])

    mean_all = float(lsb.mean())
    trans_all = float(trans.mean())

    # transition-rate gap between the start of the image and the rest
    gaps, biases = [], []
    for w in _WINDOWS:
        k = max(64, int(n * w))
        k -= k % 8
        if k >= n:
            continue
        gaps.append(float(trans[:k - 1].mean() - trans[k:].mean()))
        # period-8 pattern: bit 7 of base64 ASCII is always 0
        phase = lsb[:k].reshape(-1, 8).mean(axis=0)
        biases.append(float(phase.mean() - phase.min()))
    return {
        "lsb_mean": mean_all,
        "lsb_transition": trans_all,
        "trans_gap_max": max(gaps) if gaps else 0.0,
        "phase_bias": max(biases) if biases else 0.0,
    }


def extended_features(img_rgb):
    """[variance, edge_count, mean_intensity, lsb_mean, ...] for v2 datasets."""
    base = model_features(img_rgb)
    s = lsb_statistics(img_rgb)
    return base + [s["lsb_mean"], s["lsb_transition"], s["trans_gap_max"], s["phase_bias"]]


# ---------------------------------------------------------------------------
# Combined report
# ---------------------------------------------------------------------------
PHASE_BIAS_THRESHOLD = 0.25


def analyze_array(img_rgb):
    img_rgb = np.asarray(img_rgb)
    if img_rgb.ndim != 3 or img_rgb.shape[2] != 3 or img_rgb.size == 0:
        raise ValueError("Expected a non-empty RGB image array.")

    sig = signature_scan(img_rgb)
    stats = lsb_statistics(img_rgb)
    model = model_predict(img_rgb)

    periodic = stats["phase_bias"] > PHASE_BIAS_THRESHOLD
    if sig["found"]:
        verdict, level = "STEGO", "high"
        reason = f"hidden payload header found ({sig['payload_bytes']} bytes)"
    elif periodic:
        verdict, level = "SUSPICIOUS", "medium"
        reason = "periodic LSB pattern typical of embedded encoded data"
    elif model is not None and model[1] >= 0.5:
        verdict, level = "SUSPICIOUS", "low"
        reason = "ML model score >= 50% (weak evidence on its own)"
    else:
        verdict, level = "CLEAN", "low"
        reason = ("no known signature found - random-position embedding or a "
                  "very short message cannot be ruled out")
    return {
        "verdict": verdict,
        "confidence": level,
        "reason": reason,
        "signature": sig,
        "stats": stats,
        "model": model,          # (label, prob) or None
    }


def analyze_file(path):
    img = _read_image_array(path)
    if img is None:
        raise FileNotFoundError(f"Could not open image: {path}")
    return analyze_array(img)


def format_report(name, r):
    lines = [f"DETECTION REPORT - {name}", "-" * 34,
             f"Verdict     : {r['verdict']}  ({r['confidence']} confidence)",
             f"Reason      : {r['reason']}"]
    if r["model"] is not None:
        lines.append(f"ML model    : {'stego' if r['model'][0] else 'cover'}"
                     f"  (P[stego] = {r['model'][1] * 100:.1f}%)")
    else:
        lines.append("ML model    : stego_model.pkl not available")
    s = r["stats"]
    lines += [
        f"Signature   : {'FOUND, ' + str(r['signature']['payload_bytes']) + ' bytes' if r['signature']['found'] else 'not found'}",
        f"LSB mean    : {s['lsb_mean']:.4f}   (0.5000 = random)",
        f"LSB transit.: {s['lsb_transition']:.4f}   (0.5000 = random)",
        f"Period-8 bias: {s['phase_bias']:.3f}   (> {PHASE_BIAS_THRESHOLD} = suspicious)",
    ]
    return "\n".join(lines)
