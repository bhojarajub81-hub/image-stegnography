"""
steg_core.py  -  NEW feature module (does not modify any original file)

Adds on top of hide_message.py:
  * capacity calculation (max characters / file size for an image)
  * password-seeded RANDOM pixel-position embedding
  * hiding / extracting FILES (not only text)
  * quality metrics: MSE, PSNR, SSIM, number of changed samples
  * visual maps: difference map and LSB-plane view

Payload format is identical to hide_message.py:
    [4-byte big-endian length][Fernet token]   written into the LSBs of R,G,B
so images made by the original encode_image() can be read by this module and
vice-versa (sequential mode).
"""
import hashlib
import os
from dataclasses import dataclass

import numpy as np
from PIL import Image
from cryptography.fernet import InvalidToken
from skimage.metrics import structural_similarity

# Re-use the project's single source of truth for image reading + cipher
from hide_message import _get_cipher, _read_image_array

HEADER_BYTES = 4                       # length prefix
FILE_MAGIC = b"\x00STEGFILE\x00"       # marks a hidden *file* (text has no magic)


class StegoError(Exception):
    """Readable error for the GUI / CLI."""


# ---------------------------------------------------------------------------
# Capacity
# ---------------------------------------------------------------------------
def capacity_bits(shape):
    """Number of usable LSB slots (1 bit per R/G/B sample)."""
    return int(shape[0]) * int(shape[1]) * 3


def max_plaintext_bytes(shape):
    """
    Largest plaintext (bytes) that fits in an image of this shape once it has
    been Fernet-encrypted (+base64) and given the 4-byte length header.
    Fernet raw size = 57 + 16*(n//16 + 1); token = base64 -> 4*ceil(raw/3).
    """
    max_token = capacity_bits(shape) // 8 - HEADER_BYTES
    if max_token <= 0:
        return 0
    raw_max = (max_token // 4) * 3
    blocks = (raw_max - 57) // 16
    return max(0, blocks * 16 - 1)


def max_text_chars(shape):
    """Conservative capacity for plain ASCII text (1 byte per character)."""
    return max_plaintext_bytes(shape)


def max_file_bytes(shape, filename="file.bin"):
    overhead = len(FILE_MAGIC) + 2 + len(os.path.basename(filename).encode("utf-8"))
    return max(0, max_plaintext_bytes(shape) - overhead)


def image_capacity(path):
    """(width, height, max_text_bytes) for an image file, or None."""
    img = _read_image_array(path)
    if img is None:
        return None
    return img.shape[1], img.shape[0], max_plaintext_bytes(img.shape)


# ---------------------------------------------------------------------------
# Random position generator (password seeded)
# ---------------------------------------------------------------------------
def _position_permutation(n_samples, password):
    """
    Deterministic permutation of sample indices derived from the password.
    np.random.RandomState is a *frozen* legacy generator, so the same password
    gives the same order on every NumPy version (important for decoding).
    """
    digest = hashlib.sha256(b"stego-positions:" + password.encode("utf-8")).digest()
    seed = np.frombuffer(digest[:16], dtype="<u4")
    return np.random.RandomState(seed).permutation(n_samples)


# ---------------------------------------------------------------------------
# Embed / extract raw bytes
# ---------------------------------------------------------------------------
def embed_bytes(img, plaintext, password=None, random_positions=False):
    """Return a NEW uint8 array with `plaintext` hidden in the LSBs."""
    if random_positions and not password:
        raise StegoError("Random-position mode needs a password.")

    token = _get_cipher(password).encrypt(plaintext)
    payload = len(token).to_bytes(HEADER_BYTES, "big") + token
    bits = np.unpackbits(np.frombuffer(payload, dtype=np.uint8))

    flat = np.ascontiguousarray(img, dtype=np.uint8).reshape(-1).copy()
    if bits.size > flat.size:
        raise StegoError(
            f"Message too large: needs {bits.size} bits, image holds {flat.size}."
        )

    if random_positions:
        idx = _position_permutation(flat.size, password)[: bits.size]
        flat[idx] = (flat[idx] & 0xFE) | bits
    else:
        flat[: bits.size] = (flat[: bits.size] & 0xFE) | bits
    return flat.reshape(img.shape)


def _read_lsbs(flat, perm, start, count):
    seg = flat[start:start + count] if perm is None else flat[perm[start:start + count]]
    return seg & 1


def _try_layout(flat, perm, cipher):
    """
    Try to read one payload using either sequential (perm=None) or random order.
    Returns (plaintext | None, header_was_plausible).
    """
    max_token = flat.size // 8 - HEADER_BYTES
    if max_token <= 0:
        return None, False
    n = int.from_bytes(np.packbits(_read_lsbs(flat, perm, 0, 32)).tobytes(), "big")
    if n <= 0 or n > max_token:
        return None, False
    token = np.packbits(_read_lsbs(flat, perm, 32, n * 8)).tobytes()
    try:
        return cipher.decrypt(token), True
    except InvalidToken:
        return None, True


def extract_bytes(img, password=None):
    """
    Return the hidden plaintext bytes. Tries sequential order first, then the
    password-seeded random order. Raises StegoError with a helpful reason.
    """
    flat = np.ascontiguousarray(img, dtype=np.uint8).reshape(-1)
    cipher = _get_cipher(password)

    plain, plausible = _try_layout(flat, None, cipher)
    if plain is not None:
        return plain

    if password:
        perm = _position_permutation(flat.size, password)
        plain2, plausible2 = _try_layout(flat, perm, cipher)
        if plain2 is not None:
            return plain2
        plausible = plausible or plausible2

    if plausible:
        raise StegoError("A hidden payload seems to exist but could not be "
                         "decrypted - wrong password?")
    if password:
        raise StegoError("No hidden message found - or the password is wrong.")
    raise StegoError("No hidden message found in this image.")


# ---------------------------------------------------------------------------
# Plaintext <-> text / file
# ---------------------------------------------------------------------------
def pack_text(text):
    return text.encode("utf-8")


def pack_file(file_path):
    name = os.path.basename(file_path).encode("utf-8")
    with open(file_path, "rb") as f:
        data = f.read()
    if len(name) > 65535:
        raise StegoError("File name too long.")
    return FILE_MAGIC + len(name).to_bytes(2, "big") + name + data


@dataclass
class Extracted:
    kind: str                # "text" or "file"
    text: str = ""
    filename: str = ""
    data: bytes = b""


def unpack(plaintext):
    if plaintext.startswith(FILE_MAGIC):
        p = len(FILE_MAGIC)
        n = int.from_bytes(plaintext[p:p + 2], "big")
        name = plaintext[p + 2:p + 2 + n].decode("utf-8", "replace")
        name = os.path.basename(name) or "extracted.bin"      # no path tricks
        return Extracted("file", filename=name, data=plaintext[p + 2 + n:])
    try:
        return Extracted("text", text=plaintext.decode("utf-8"))
    except UnicodeDecodeError:
        return Extracted("file", filename="extracted.bin", data=plaintext)


# ---------------------------------------------------------------------------
# Metrics and visual maps
# ---------------------------------------------------------------------------
def _matching_rgb_images(cover, stego):
    cover = np.asarray(cover)
    stego = np.asarray(stego)
    if (cover.shape != stego.shape or cover.ndim != 3 or cover.shape[2] != 3
            or cover.size == 0):
        raise ValueError("Images must be non-empty RGB arrays of identical dimensions.")
    return cover, stego


def compare_images(cover, stego):
    """MSE, PSNR, SSIM and change statistics between two RGB arrays."""
    cover, stego = _matching_rgb_images(cover, stego)
    a = cover.astype(np.float64)
    b = stego.astype(np.float64)
    mse = float(np.mean((a - b) ** 2))
    psnr = 100.0 if mse == 0 else float(20 * np.log10(255.0 / np.sqrt(mse)))
    if min(cover.shape[:2]) >= 7:
        ssim = float(structural_similarity(cover, stego, channel_axis=2, data_range=255))
    else:
        ssim = 1.0 if mse == 0 else float("nan")
    changed = int(np.count_nonzero(cover != stego))
    return {
        "mse": mse,
        "psnr": psnr,
        "ssim": ssim,
        "samples_changed": changed,
        "samples_total": int(cover.size),
    }


def difference_mask(cover, stego):
    """Boolean HxW mask: True where any channel differs."""
    cover, stego = _matching_rgb_images(cover, stego)
    return np.any(cover != stego, axis=2)


def density_preview(mask, max_w=300, max_h=190, color=(255, 43, 214)):
    """
    Turn a boolean change-mask into a neon heat-map preview. Down-scaling uses
    an area average so even single-pixel changes stay visible, then the
    contrast is stretched.
    """
    h, w = mask.shape
    scale = min(max_w / w, max_h / h, 1.0)
    size = (max(1, round(w * scale)), max(1, round(h * scale)))
    small = np.asarray(
        Image.fromarray((mask * 255).astype(np.uint8), "L").resize(size, Image.Resampling.BOX),
        dtype=np.float64,
    ) / 255.0
    peak = small.max()
    dens = small / peak if peak > 0 else small
    dens = np.clip(dens, 0, 1) ** 0.6
    bg = np.array([3, 5, 10], dtype=np.float64)
    fg = np.array(color, dtype=np.float64)
    out = bg + (fg - bg) * dens[..., None]
    return Image.fromarray(out.astype(np.uint8), "RGB")


def lsb_plane_preview(img, max_w=300, max_h=190):
    """Image made from the R,G,B least-significant-bit planes (0 or 255)."""
    plane = ((img & 1) * 255).astype(np.uint8)
    pil = Image.fromarray(plane, "RGB")
    scale = min(max_w / pil.width, max_h / pil.height, 1.0)
    size = (max(1, round(pil.width * scale)), max(1, round(pil.height * scale)))
    return pil.resize(size, Image.Resampling.NEAREST)


# ---------------------------------------------------------------------------
# High-level API used by GUI / CLI
# ---------------------------------------------------------------------------
@dataclass
class EmbedResult:
    cover: np.ndarray
    stego: np.ndarray
    out_path: str
    bits_used: int
    capacity_bits: int
    mode: str
    metrics: dict


def load_image(path):
    """Read any image as an RGB uint8 array (raises StegoError if unreadable)."""
    img = _read_image_array(path)
    if img is None:
        raise StegoError(f"Could not open image: {path}")
    return img


_load = load_image       # backwards-compatible internal alias


def embed_and_save(image_path, plaintext, out_path, password=None,
                   random_positions=False):
    cover = _load(image_path)
    limit = max_plaintext_bytes(cover.shape)
    if len(plaintext) > limit:
        raise StegoError(
            f"Payload is {len(plaintext)} bytes but this image can hold only "
            f"{limit} bytes. Use a larger image or a shorter payload."
        )
    stego = embed_bytes(cover, plaintext, password, random_positions)

    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    Image.fromarray(stego).save(out_path, format="PNG")      # lossless only

    token_len = len(_get_cipher(password).encrypt(plaintext))
    return EmbedResult(
        cover=cover,
        stego=stego,
        out_path=out_path,
        bits_used=(HEADER_BYTES + token_len) * 8,
        capacity_bits=capacity_bits(cover.shape),
        mode="random positions" if random_positions else "sequential",
        metrics=compare_images(cover, stego),
    )


def encode_text(image_path, text, out_path, password=None, random_positions=False):
    return embed_and_save(image_path, pack_text(text), out_path, password, random_positions)


def encode_file(image_path, file_path, out_path, password=None, random_positions=False):
    return embed_and_save(image_path, pack_file(file_path), out_path, password, random_positions)


def decode(image_path, password=None):
    return unpack(extract_bytes(_load(image_path), password))
