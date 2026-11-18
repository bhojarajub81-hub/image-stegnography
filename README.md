# Image Steganography

A Python application for hiding and extracting text or files in lossless PNG images. `run.py` provides the desktop interface, while `run1.py` provides a two-column message and file-analysis dashboard. `stego_cli.py` provides the same core workflows in a terminal.

## Setup

Python 3.10 or newer is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run

```powershell
python run.py
python run1.py
python stego_cli.py --help
```

In `run1.py`, the left side selects a cover image and encodes or decodes text. The right side opens images for decoding or detection, hides files, and displays the analysis report.

CLI examples:

```powershell
python stego_cli.py capacity stego_image.png
python stego_cli.py encode cover.png output.png --text "hidden text" --password "your password" --random
python stego_cli.py decode output.png --password "your password"
python stego_cli.py detect output.png
python stego_cli.py compare cover.png output.png
```

Use PNG for encoded images. JPEG compression or resizing can destroy the hidden data.

## Dataset And Model

`create_dataset.py` extracts image features from `dataset/cover` and `dataset/stego` and overwrites `training_data.csv`. `train_model.py` trains a random-forest model and overwrites `stego_model.pkl`.

```powershell
python create_dataset.py
python train_model.py
python detect.py stego_image.png
python evaluation.py
```

`evaluation.py` evaluates the model against the full CSV, so its reported metrics are not held-out test results.

## Notes

The GUI and CLI support text, file payloads, password-based encoding, optional password-seeded random positions, capacity estimates, image quality metrics, difference previews, and LSB analysis. Password-free encoding remains available for compatibility with images produced by `hide_message.py`.

A detector cannot prove that an image contains no hidden content. Random-position embedding is intentionally harder for the sequential payload-signature scan to identify.
