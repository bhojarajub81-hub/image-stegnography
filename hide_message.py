import base64
import hashlib
import os

import cv2
import numpy as np
from PIL import Image
from cryptography.fernet import Fernet

# =====================================
# FIXED FERNET KEY
# =====================================

key = b'6I_-mh53g0BqoCEzGpen9-FJwtpjt_onta-Ejeo5NHg='
cipher = Fernet(key)

# Use one consistent output location for every script in the project.
DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
STEGO_IMAGE_PATH = os.path.join(DOWNLOAD_DIR, "stego.png")


def _get_cipher(password=None):
    if not password:
        return cipher
    password_key = hashlib.sha256(password.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(password_key))


def _read_image_array(image_path):
    try:
        with Image.open(image_path) as img:
            return np.array(img.convert("RGB"), dtype=np.uint8, copy=True)
    except Exception:
        img = cv2.imread(image_path)
        if img is None:
            return None
        return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def _save_image_array(image_path, img_array):
    img_array = np.asarray(img_array)
    if img_array.ndim != 3 or img_array.shape[2] != 3:
        return False
    Image.fromarray(img_array.astype(np.uint8)).save(image_path)
    return True


# =====================================
# HIDE MESSAGE
# =====================================

def encode_image(image_path, message, output_path=None, password=None):
    img = _read_image_array(image_path)

    if img is None:
        print("Error: Image not found")
        return False

    encrypted = _get_cipher(password).encrypt(message.encode())
    payload = len(encrypted).to_bytes(4, byteorder='big', signed=False) + encrypted
    bits = np.array([bit for byte in payload for bit in format(byte, '08b')], dtype=np.uint8)
    bits = bits.astype(np.uint8)
    bits = (bits == 1).astype(np.uint8)

    capacity = img.shape[0] * img.shape[1] * 3

    print("Message Bits :", len(bits))
    print("Capacity     :", capacity)

    if len(bits) > capacity:
        print("Message too large for image")
        return False

    flat = img.reshape(-1)
    mask = np.uint8(254)
    flat[:len(bits)] = (flat[:len(bits)] & mask) | bits.astype(np.uint8)
    img = flat.reshape(img.shape)

    if output_path is None:
        output_path = STEGO_IMAGE_PATH

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    if not _save_image_array(output_path, img):
        print("Error: Failed to save stego image")
        return False

    print(f"Message hidden successfully. Stego image saved at: {output_path}")
    return True


# =====================================
# EXTRACT MESSAGE
# =====================================

def decode_image(image_path, password=None):
    img = _read_image_array(image_path)

    if img is None:
        return "Image not found"

    flat = img.reshape(-1)
    bits = (flat & 1).astype(np.uint8)
    if bits.size == 0:
        return "No Message Found"

    total_bytes = bits.size // 8
    if total_bytes == 0:
        return "No Message Found"

    packed = np.packbits(bits[: total_bytes * 8].reshape(-1, 8), axis=1, bitorder="big")
    extracted = bytearray(packed.flatten().tolist())

    if len(extracted) < 4:
        return "No Message Found"

    try:
        payload_length = int.from_bytes(extracted[:4], byteorder="big", signed=False)
    except Exception:
        return "No Message Found"

    if payload_length <= 0 or payload_length > len(extracted) - 4:
        return "No Message Found"

    encrypted = bytes(extracted[4:4 + payload_length])
    try:
        return _get_cipher(password).decrypt(encrypted).decode()
    except Exception:
        return "Decryption Error"


# =====================================
# IMAGE QUALITY METRICS
# =====================================

def calculate_metrics(original, stego):
    img1 = _read_image_array(original)
    img2 = _read_image_array(stego)

    if img1 is None or img2 is None:
        return None, None

    mse = np.mean((img1.astype(float) - img2.astype(float)) ** 2)
    psnr = 100 if mse == 0 else 20 * np.log10(255.0 / np.sqrt(mse))
    return mse, psnr


# =====================================
# MAIN PROGRAM
# =====================================

if __name__ == "__main__":
    print("===================================")
    print("INTELLIGENT IMAGE STEGANOGRAPHY")
    print("===================================")

    image_path = input("Enter image path: ")
    message = input("Enter secret message: ")

    if not message.strip():
        print("Error: Secret message cannot be empty")
        raise SystemExit(1)

    success = encode_image(image_path, message)

    if success:
        decoded = decode_image(STEGO_IMAGE_PATH)
        mse, psnr = calculate_metrics(image_path, STEGO_IMAGE_PATH)

        print("\n==============================")
        print("FINAL RESULT")
        print("==============================")
        print("Original Image :", image_path)
        print("Stego Image    :", STEGO_IMAGE_PATH)
        print("Secret Message :", message)
        print("Decoded Message:", decoded)

        print("\nPerformance")
        print("----------------")
        print("MSE  :", mse)
        print("PSNR :", round(psnr, 2), "dB")
        print("\nStatus : SUCCESS")