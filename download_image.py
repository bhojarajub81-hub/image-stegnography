from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image

URL = (
    "https://images.unsplash.com/photo-1506744038136-46273834b3fb"
    "?auto=format&fit=crop&w=800&q=80"
)
DOWNLOAD_DIR = Path.home() / "Downloads"
DOWNLOAD_PATH = DOWNLOAD_DIR / "input.png"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
}


def download_png(url=URL, save_path=DOWNLOAD_PATH):
    """Download an image, convert it to PNG, and return its saved path."""
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    request = Request(url, headers=HEADERS)
    with urlopen(request, timeout=30) as response:
        image_data = response.read()

    with Image.open(BytesIO(image_data)) as image:
        image.convert("RGBA").save(save_path, format="PNG")

    with Image.open(save_path) as saved_image:
        if saved_image.format != "PNG":
            raise ValueError(f"Downloaded file is not a PNG: {save_path}")

    return save_path


if __name__ == "__main__":
    saved_path = download_png()
    print("Image downloaded and saved as PNG at:", saved_path)