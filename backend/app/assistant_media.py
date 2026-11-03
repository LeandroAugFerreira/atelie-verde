"""Prepare owned conversation photos for private multimodal inference."""

import base64
import io
import re

from PIL import Image, ImageOps, UnidentifiedImageError

from .database import DATA_DIR

FOLDER = DATA_DIR / "assistant-photos"


def model_images(rows):
    result = []
    for row in rows[:3]:
        if not re.fullmatch(r"[a-f0-9]{32}\.(?:jpg|png|webp|gif)", row.filename):
            continue
        path = FOLDER / row.filename
        if not path.is_file() or path.stat().st_size > 5 * 1024 * 1024:
            continue
        try:
            with Image.open(path) as opened:
                if opened.width * opened.height > 16000000 or getattr(opened, "is_animated", False):
                    continue
                image = ImageOps.exif_transpose(opened).convert("RGBA")
                image.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
                opaque = Image.new("RGB", image.size, "white")
                opaque.paste(image, mask=image.getchannel("A"))
                output = io.BytesIO()
                opaque.save(output, format="JPEG", quality=90, optimize=True)
                result.append(
                    {
                        "type": "input_image",
                        "image_url": "data:image/jpeg;base64,"
                        + base64.b64encode(output.getvalue()).decode("ascii"),
                        "detail": "high",
                    }
                )
        except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
            continue
    return result
