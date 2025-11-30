import io
import math
import requests
from PIL import Image


def download_image(url: str) -> Image.Image:
    """Download an image from a URL and return a PIL image."""
    resp = requests.get(url)
    resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content)).convert("RGB")


def resize_image(img: Image.Image, max_size: int = 512) -> Image.Image:
    """
    Resize image while keeping aspect ratio.
    max_size applies to the longer side.
    """
    w, h = img.size
    scale = max_size / max(w, h)
    if scale >= 1:
        return img  # already small
    new_size = (int(w * scale), int(h * scale))
    return img.resize(new_size, Image.LANCZOS)


def compose_images(urls: list[str], max_single_size: int = 512) -> Image.Image:
    """
    Download multiple images from URLs and compose them into a single grid image.
    
    Args:
        urls: List of image URLs.
        max_single_size: Maximum width/height for each image before combining.
    
    Returns:
        A single PIL image with all images arranged in a grid.
    """
    if not urls:
        raise ValueError("No image URLs provided.")

    # Step 1: Download & resize
    images = [resize_image(download_image(url), max_single_size) for url in urls]

    # Decide grid layout: square-ish
    n = len(images)
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)

    # Determine grid cell size (use max width/height among resized images)
    max_w = max(img.size[0] for img in images)
    max_h = max(img.size[1] for img in images)

    # Step 2: Create canvas
    combined_w = cols * max_w
    combined_h = rows * max_h

    combined = Image.new("RGB", (combined_w, combined_h), color=(255, 255, 255))

    # Step 3: Paste into grid
    for idx, img in enumerate(images):
        row = idx // cols
        col = idx % cols
        x = col * max_w
        y = row * max_h
        combined.paste(img, (x, y))

    return combined


def compose_images_to_bytes(urls: list[str], format: str = "JPEG") -> bytes:
    """
    Convenience function to return the composed image as raw bytes
    for LLM agents that expect binary images.
    """
    img = compose_images(urls)
    buf = io.BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    return buf.read()
