import io, os, time
import math
import base64
import requests
from PIL import Image
from app.core.database import get_database
from bson.objectid import ObjectId

def download_image(url: str) -> Image.Image:
    headers = {"User-Agent": "Mozilla/5.0 ..."}
    for _ in range(3):
        try:
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()
            return Image.open(io.BytesIO(resp.content)).convert("RGB")
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 403:
                raise  # forbidden, don’t retry
            time.sleep(1)


def resize_image(img: Image.Image, max_size: int = 512) -> Image.Image:
    w, h = img.size
    scale = max_size / max(w, h)
    if scale >= 1:
        return img
    new_size = (int(w * scale), int(h * scale))
    return img.resize(new_size, Image.LANCZOS)


def round_to_multiple_of_16(x: int) -> int:
    return ((x + 15) // 16) * 16


def compose_images(urls: list[str], max_single_size: int = 512) -> Image.Image:
    if not urls:
        raise ValueError("No image URLs provided.")

    images = [resize_image(download_image(url), max_single_size) for url in urls]

    n = len(images)
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)

    max_w = max(img.size[0] for img in images)
    max_h = max(img.size[1] for img in images)

    combined_w = cols * max_w
    combined_h = rows * max_h

    # --- Ensure multiples of 16 (Flux requirement)
    combined_w_16 = round_to_multiple_of_16(combined_w)
    combined_h_16 = round_to_multiple_of_16(combined_h)

    combined = Image.new("RGB", (combined_w_16, combined_h_16), color=(255, 255, 255))

    # Paste at top-left corner; extra padded space (if any) stays white
    for idx, img in enumerate(images):
        row = idx // cols
        col = idx % cols
        x = col * max_w
        y = row * max_h
        combined.paste(img, (x, y))

    # --- Enforce 4MP max (Flux max size)
    max_pixels = 4_000_000  # ~4MP
    if combined.width * combined.height > max_pixels:
        scale = (max_pixels / (combined.width * combined.height)) ** 0.5
        new_w = round_to_multiple_of_16(int(combined.width * scale))
        new_h = round_to_multiple_of_16(int(combined.height * scale))
        combined = combined.resize((new_w, new_h), Image.LANCZOS)

    # --- Enforce minimum size 64×64
    if combined.width < 64 or combined.height < 64:
        combined = combined.resize(
            (
                max(64, round_to_multiple_of_16(combined.width)),
                max(64, round_to_multiple_of_16(combined.height))
            ),
            Image.LANCZOS
        )

    return combined


def compose_images_to_base64(urls: list[str], format: str = "JPEG") -> str:
    """Return Flux-compatible Base64 encoded image."""
    img = compose_images(urls)
    os.makedirs(os.path.dirname("./test.jpg"), exist_ok=True)
    print("Saving test image to ./test.jpg")
    img.save("./test.jpg", format="JPEG", quality=95)

    buffer = io.BytesIO()
    img.save(buffer, format=format, quality=95)
    buffer.seek(0)

    return base64.b64encode(buffer.read()).decode("utf-8")


# TODO: Find good file for this...
def retrieve_srcs_from_mongo(image_ids: list[str]) -> str:
    """Retrieve image source URL from MongoDB by image ID."""
    # Get database connection
    db = get_database()
    collection = db.inventory
    object_ids = [ObjectId(id) for id in image_ids]

    # Query documents with IDs in the list
    docs = list(collection.find({"_id": {"$in": object_ids}}))

    urls = [doc.get("src") for doc in docs]
    return urls