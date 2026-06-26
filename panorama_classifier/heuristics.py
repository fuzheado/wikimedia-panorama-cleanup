"""
Layer 2: Heuristic classification — aspect ratio, camera database,
filenames, and stitching software detection.
"""

import os
import re

from .camera_db import lookup_camera, lookup_stitching_software


def classify_by_aspect_ratio(width, height):
    """Classify image type using aspect ratio heuristics.

    This is the strongest zero-cost signal when GPano is absent.
    """
    if not width or not height or height <= 0:
        return None

    ar = width / height

    if 1.98 <= ar <= 2.02:
        return {
            "type": "likely_spherical_equirectangular",
            "projection": "equirectangular",
            "confidence": 0.75,
            "source": "aspect_ratio",
            "aspect_ratio": round(ar, 3),
            "reason": "perfect 2:1 ratio → strong equirectangular signal",
        }

    if 2.02 < ar <= 3.0:
        return {
            "type": "ambiguous_wide",
            "projection": "unknown",
            "confidence": 0.45,
            "source": "aspect_ratio",
            "aspect_ratio": round(ar, 3),
            "reason": "wider than 2:1 → could be cropped equirectangular or cylindrical",
        }

    if 3.0 < ar <= 8.0:
        return {
            "type": "likely_cylindrical",
            "projection": "cylindrical",
            "confidence": 0.70,
            "source": "aspect_ratio",
            "aspect_ratio": round(ar, 3),
            "reason": "wide strip → likely 360° cylindrical panorama",
        }

    if ar > 8.0:
        return {
            "type": "likely_partial_stitched",
            "projection": "rectilinear",
            "confidence": 0.80,
            "source": "aspect_ratio",
            "aspect_ratio": round(ar, 3),
            "reason": "very wide strip → multi-frame partial panorama",
        }

    if 0.95 <= ar <= 1.05:
        return {
            "type": "ambiguous_square",
            "projection": "unknown",
            "confidence": 0.20,
            "source": "aspect_ratio",
            "aspect_ratio": round(ar, 3),
            "reason": "square → could be cubemap face, little planet, or normal photo",
        }

    if ar < 1.9:
        return {
            "type": "likely_not_panorama",
            "projection": "unknown",
            "confidence": 0.60,
            "source": "aspect_ratio",
            "aspect_ratio": round(ar, 3),
            "reason": f"standard/portrait aspect ratio ({ar:.2f}:1) → unlikely panorama",
        }

    return {
        "type": "likely_not_panorama",
        "projection": "unknown",
        "confidence": 0.50,
        "source": "aspect_ratio",
        "aspect_ratio": round(ar, 3),
    }


def classify_by_camera(exif_data):
    """Identify 360° camera from EXIF Make/Model."""
    make = exif_data.get("make", "")
    model = exif_data.get("model", "")

    if not make and not model:
        return None

    cam = lookup_camera(make, model)
    if cam:
        return {
            "type": "spherical" if cam["full_sphere"] else "panorama",
            "projection": cam.get("projection", "equirectangular"),
            "confidence": 0.90,
            "source": "camera_db",
            "camera": f"{make} {model}".strip(),
            "commons_category": cam.get("commons_category"),
        }

    return None


def classify_by_software(exif_data):
    """Detect stitching software from EXIF Software field."""
    software = exif_data.get("software", "")
    if not software:
        return None

    sw_info = lookup_stitching_software(software)
    if not sw_info:
        return None

    result = {
        "stitched": sw_info.get("stitched", True),
        "confidence": 0.60,
        "source": "software_tag",
        "software": software,
    }

    if sw_info.get("full_sphere"):
        result["type"] = "spherical"
        result["projection"] = sw_info.get("projection", "equirectangular")
        result["confidence"] = 0.85
    else:
        result["type"] = "stitched_panorama"

    return result


def classify_by_filename(image_path):
    """Heuristic classification from filename patterns.  Low weight."""
    basename = os.path.basename(image_path)
    basename_lower = basename.lower()

    patterns = [
        (r"(little[._-]?planet|tiny[._-]?planet|planet[._-]?pano)", "polar_little_planet", 0.60),
        (r"(nadir|zenith|cube[._-]?map|cubemap)", "cubemap_face", 0.55),
        (r"(stitch)", "stitched", 0.40),
        (r"(equirect|equirectangular)", "spherical_equirectangular", 0.50),
        (r"(pano|panorama|360\d*|photosphere|vr[._-]?photo)", "panorama", 0.15),
    ]

    for pattern, pano_type, confidence in patterns:
        if re.search(pattern, basename_lower):
            return {
                "type": pano_type,
                "confidence": confidence,
                "source": "filename",
                "matched_pattern": pattern,
                "filename": basename,
            }

    # Negative signal: default camera filenames
    if re.search(r"(img_\d{4}|dsc\d+|p\d{7})", basename_lower):
        return {
            "type": "unknown",
            "confidence": -0.10,
            "source": "filename",
            "reason": "default camera filename → not informative",
        }

    return None
