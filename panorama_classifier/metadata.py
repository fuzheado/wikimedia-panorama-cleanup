"""
Layer 1: Metadata extraction — GPano XMP and EXIF.

Python's XMP library ecosystem is sparse.  exiftool (a single portable
Perl binary) is the gold standard for reading XMP/GPano metadata and is
used as the primary method when available.

When exiftool is not installed, a pure-Python JPEG APP1 parser (stdlib
only) extracts XMP directly from the JPEG byte stream.  Pillow's getxmp()
serves as a tertiary fallback.

GPano XMP is the gold standard for 360° photo classification.
When present, confidence ≥ 0.99.
"""

import struct
import json
import subprocess
from xml.etree import ElementTree as ET

# GPano XMP namespace URI
GPANO_NS = "http://ns.google.com/photos/1.0/panorama/"
XMP_ID = b"http://ns.adobe.com/xap/1.0/\x00"


def extract_metadata(image_path):
    """Extract GPano XMP and basic EXIF from an image.

    Tries three methods in order:
      1. Pure Python JPEG APP1 XMP parser (fast, no deps)
      2. Pillow's getxmp() method
      3. exiftool subprocess (fallback if installed)

    Returns a dict with keys:
        gpano: dict of GPano namespace tags (empty if none found)
        exif: dict with Make, Model, Software, ImageWidth, ImageHeight
    """
    result = {"gpano": {}, "exif": {}}

    # --- Extract GPano XMP ---
    # Try methods in order of reliability:
    #   1. exiftool (most robust, handles all edge cases)
    #   2. Pure Python JPEG APP1 parser (no deps, works everywhere)
    #   3. Pillow getxmp() (convenient but version-dependent)
    gpano = _extract_gpano_via_exiftool(image_path)
    if not gpano:
        gpano = _extract_gpano_pure_python(image_path)
    if not gpano:
        gpano = _extract_gpano_via_pillow(image_path)

    result["gpano"] = gpano or {}

    # --- Extract EXIF ---
    result["exif"] = _extract_exif(image_path)

    return result


def _extract_gpano_pure_python(image_path):
    """Extract GPano tags by parsing JPEG APP1 XMP markers directly.

    Zero external dependencies — just stdlib struct + xml.etree.
    This is the primary method and works on any platform.
    """
    try:
        with open(image_path, "rb") as f:
            data = f.read()
    except (IOError, OSError):
        return {}

    # Scan for APP1 XMP markers
    i = 0
    while i < len(data) - 4:
        if data[i] == 0xFF and data[i + 1] == 0xE1:
            seg_len = struct.unpack(">H", data[i + 2 : i + 4])[0]
            seg_id = data[i + 4 : i + 4 + len(XMP_ID)]

            if seg_id.startswith(XMP_ID):
                # Extract XMP XML bytes
                xmp_start = i + 4 + len(XMP_ID)
                xmp_end = i + 2 + seg_len
                xmp_bytes = data[xmp_start:xmp_end]

                # Clean: strip leading non-XML bytes (BOM, nulls, etc.)
                xml_start = xmp_bytes.find(b"<")
                if xml_start < 0:
                    i += 2 + seg_len
                    continue
                xmp_bytes = xmp_bytes[xml_start:]

                # Parse XML
                try:
                    xmp_str = xmp_bytes.decode("utf-8", errors="replace")
                    root = ET.fromstring(xmp_str)
                except ET.ParseError:
                    i += 2 + seg_len
                    continue

                # Extract GPano tags using namespace-aware search
                # GPano elements have tags like:
                # {http://ns.google.com/photos/1.0/panorama/}UsePanoramaViewer
                gpano = {}
                for elem in root.iter():
                    tag = str(elem.tag)
                    if GPANO_NS in tag:
                        name = tag.split("}")[1] if "}" in tag else tag
                        gpano[name] = elem.text or ""

                return gpano

            i += 2 + seg_len
        else:
            i += 1

    return {}


def _extract_gpano_via_pillow(image_path):
    """Extract GPano via Pillow's getxmp() — works with defusedxml installed."""
    try:
        from PIL import Image

        img = Image.open(image_path)
        xmp = img.getxmp()
    except Exception:
        return {}

    if not xmp:
        return {}

    # Pillow >= 10.0 returns XMP as a dict; older returns bytes
    if isinstance(xmp, dict):
        # Newer Pillow — XMP is already parsed into a dict structure
        # Try to extract GPano from nested dict
        return _extract_gpano_from_pillow_dict(xmp)

    if isinstance(xmp, bytes) and len(xmp) > 10:
        # Older Pillow — raw XMP XML bytes
        try:
            xml_start = xmp.find(b"<")
            if xml_start >= 0:
                xmp_str = xmp[xml_start:].decode("utf-8", errors="replace")
                root = ET.fromstring(xmp_str)
                gpano = {}
                for elem in root.iter():
                    tag = str(elem.tag)
                    if GPANO_NS in tag:
                        name = tag.split("}")[1] if "}" in tag else tag
                        gpano[name] = elem.text or ""
                return gpano
        except (ET.ParseError, UnicodeDecodeError):
            pass

    return {}


def _extract_gpano_from_pillow_dict(xmp_dict):
    """Extract GPano tags from Pillow's parsed XMP dict structure."""
    # Pillow >= 10 returns XMP like:
    # {'xmpmeta': [{'rdf:RDF': [{'rdf:Description': [{
    #     'GPano:UsePanoramaViewer': 'True',
    #     'GPano:ProjectionType': 'equirectangular', ...
    # }]}]}]}
    gpano = {}

    def _search(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key.startswith("GPano:") or "GPano:" in key:
                    # "GPano:UsePanoramaViewer" → "UsePanoramaViewer"
                    name = key.split("GPano:")[-1]
                    if isinstance(value, list) and value:
                        gpano[name] = str(value[0])
                    elif isinstance(value, str):
                        gpano[name] = value
                _search(value)
        elif isinstance(obj, list):
            for item in obj:
                _search(item)

    _search(xmp_dict)
    return gpano


def _extract_gpano_via_exiftool(image_path):
    """Extract GPano via exiftool subprocess (primary method).

    exiftool is a single static binary — no runtime deps beyond Perl.
    Install: brew install exiftool / apt install libimage-exiftool-perl
    Or download from https://exiftool.org/
    """
    try:
        proc = subprocess.run(
            ["exiftool", "-j", "-GPano:all", image_path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode != 0:
            return {}

        data = json.loads(proc.stdout)
        if not data:
            return {}

        gpano = {}
        for key, value in data[0].items():
            if "GPano" in key:
                short_key = key.split(":")[-1] if ":" in key else key
                gpano[short_key] = str(value) if value is not None else ""
        return gpano

    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError, OSError):
        return {}


def _extract_exif(image_path):
    """Extract basic EXIF tags using Pillow."""
    exif = {
        "make": "",
        "model": "",
        "software": "",
        "image_width": 0,
        "image_height": 0,
    }

    try:
        from PIL import Image
        from PIL.ExifTags import TAGS

        # Allow large equirectangular images (can exceed default 89MP limit)
        Image.MAX_IMAGE_PIXELS = None

        img = Image.open(image_path)
        exif["image_width"], exif["image_height"] = img.size

        raw_exif = img.getexif()
        if raw_exif:
            for tag_id, value in raw_exif.items():
                tag_name = TAGS.get(tag_id, str(tag_id))
                if tag_name == "Make":
                    exif["make"] = str(value).strip()
                elif tag_name == "Model":
                    exif["model"] = str(value).strip()
                elif tag_name == "Software":
                    exif["software"] = str(value).strip()

    except Exception:
        pass

    return exif


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
