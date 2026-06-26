"""
Layer 1: Metadata extraction — GPano XMP and EXIF via exiftool.

This is the gold standard for classification.  When GPano metadata is
present, classification is near-certain (confidence ≥ 0.99).
"""

import json
import subprocess
import re


def extract_metadata(image_path):
    """Extract GPano XMP and basic EXIF from an image using exiftool.

    Returns a dict with keys:
        gpano: dict of GPano namespace tags (empty if none)
        exif: dict with Make, Model, Software, ImageWidth, ImageHeight
    """
    result = {"gpano": {}, "exif": {}}

    try:
        # Run exiftool once with -j (JSON output) for all needed tags
        proc = subprocess.run(
            [
                "exiftool", "-j",
                "-GPano:all",
                "-EXIF:Make", "-EXIF:Model", "-EXIF:Software",
                "-EXIF:ImageWidth", "-EXIF:ImageHeight",
                "-EXIF:ExifImageWidth", "-EXIF:ExifImageHeight",
                "-File:ImageWidth", "-File:ImageHeight",
                image_path,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if proc.returncode != 0:
            return result

        data = json.loads(proc.stdout)
        if not data:
            return result

        meta = data[0]

        # Extract GPano tags (prefixed with GPano)
        gpano = {}
        for key, value in meta.items():
            if key.startswith("GPano"):
                short_key = key.split(":")[-1] if ":" in key else key
                gpano[short_key] = value

        result["gpano"] = gpano

        # Extract key EXIF fields
        result["exif"] = {
            "make": meta.get("EXIF:Make", meta.get("Make", "")),
            "model": meta.get("EXIF:Model", meta.get("Model", "")),
            "software": meta.get("EXIF:Software", meta.get("Software", "")),
            "image_width": _first_int(
                meta.get("EXIF:ExifImageWidth")
                or meta.get("EXIF:ImageWidth")
                or meta.get("File:ImageWidth")
                or meta.get("ImageWidth")
            ),
            "image_height": _first_int(
                meta.get("EXIF:ExifImageHeight")
                or meta.get("EXIF:ImageHeight")
                or meta.get("File:ImageHeight")
                or meta.get("ImageHeight")
            ),
        }

    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass

    return result


def _first_int(value):
    """Safely convert a value to int, handling None and empty strings."""
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return 0


def classify_from_gpano(gpano_tags):
    """Classify image using GPano XMP metadata.

    GPano is the definitive signal. Returns a dict with type, projection,
    coverage info, and confidence.
    """
    if not gpano_tags:
        return None

    # Must have UsePanoramaViewer = True
    use_pano = str(gpano_tags.get("UsePanoramaViewer", "")).strip().lower()
    if use_pano != "true":
        return None

    projection = str(gpano_tags.get("ProjectionType", "equirectangular")).strip()

    full_w = _safe_float(gpano_tags.get("FullPanoWidthPixels", 0))
    full_h = _safe_float(gpano_tags.get("FullPanoHeightPixels", 0))
    crop_w = _safe_float(gpano_tags.get("CroppedAreaImageWidthPixels", full_w))
    crop_h = _safe_float(gpano_tags.get("CroppedAreaImageHeightPixels", full_h))

    if full_w <= 0 or full_h <= 0:
        return None

    h_coverage = crop_w / full_w if full_w > 0 else 0
    v_coverage = crop_h / full_h if full_h > 0 else 0

    is_full_sphere = h_coverage >= 0.98 and v_coverage >= 0.98
    is_ring_only = h_coverage >= 0.98 and v_coverage < 0.90

    if is_full_sphere:
        pano_type = "spherical"
    elif is_ring_only:
        pano_type = "cylindrical"
    else:
        pano_type = "partial"

    source_count = gpano_tags.get("SourcePhotosCount", "")

    return {
        "type": pano_type,
        "projection": projection,
        "h_coverage": round(h_coverage, 3),
        "v_coverage": round(v_coverage, 3),
        "confidence": 0.99,
        "source": "gpano_xmp",
        "frame_count": int(source_count) if str(source_count).isdigit() else None,
    }


def _safe_float(value):
    """Safely convert value to float."""
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0
