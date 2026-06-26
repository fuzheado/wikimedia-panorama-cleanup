"""
Layer 3: Pixel analysis with OpenCV.

Five visual detectors for when metadata is absent or inconclusive:
1. Edge continuity — do left/right edges match? (360° wrap)
2. Polar/little planet — circular content with dark corners?
3. Zenith/nadir presence — are top/bottom 5% black? (spherical vs. cylindrical)
4. Equirectangular distortion — is horizontal detail smeared at top/bottom?
5. Stitch seam detection — regular vertical edge peaks?
"""

import cv2
import numpy as np


def analyze_pixels(image_path):
    """Run all pixel-level detectors on an image.

    Returns a dict with results from each detector.
    Only runs if earlier layers were inconclusive.
    """
    img = cv2.imread(image_path)
    if img is None:
        return {"error": "could_not_read_image"}

    h, w = img.shape[:2]

    return {
        "edge_continuity": _check_edge_continuity(img),
        "polar": _detect_polar(img),
        "zenith_nadir": _detect_zenith_nadir(img),
        "equirect_distortion": _detect_equirectangular_distortion(img),
        "stitch_seams": _detect_stitch_seams(img),
    }


def _check_edge_continuity(img, sample_width=10):
    """Check if left and right edges match (indicates 360° wrap).

    Samples N-pixel strips from left and right edges, computes mean
    absolute difference. If diff < 8%, the edges match → 360° panorama.
    """
    h, w = img.shape[:2]
    if w < sample_width * 2:
        return {"is_360": False, "confidence": 0.0, "reason": "image too narrow"}

    left_strip = img[:, :sample_width].astype(float)
    right_strip = img[:, -sample_width:].astype(float)

    diff = np.mean(np.abs(left_strip - right_strip)) / 255.0

    if diff < 0.08:
        return {"is_360": True, "confidence": 0.85, "edge_diff": round(diff, 4)}
    elif diff < 0.15:
        return {"is_360": True, "confidence": 0.55, "edge_diff": round(diff, 4)}
    else:
        return {"is_360": False, "confidence": 0.70, "edge_diff": round(diff, 4)}


def _detect_polar(img):
    """Detect if image is a polar/little-planet projection.

    Little planet images have content in a circular region with
    dark or uniform corners.
    """
    h, w = img.shape[:2]

    # Create circular mask
    center = (w // 2, h // 2)
    radius = min(w, h) // 2

    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(mask, center, radius, 255, -1)

    # Invert: corners = outside the circle
    corners_mask = cv2.bitwise_not(mask)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    corner_pixels = gray[corners_mask == 255]

    if len(corner_pixels) == 0:
        return {"is_polar": False, "confidence": 0.0}

    mean_corner = float(np.mean(corner_pixels))
    std_corner = float(np.std(corner_pixels))

    # Dark + uniform corners → little planet
    is_dark_uniform = mean_corner < 30 and std_corner < 15

    return {
        "is_polar": is_dark_uniform,
        "confidence": 0.85 if is_dark_uniform else 0.0,
        "corner_mean": round(mean_corner, 1),
        "corner_std": round(std_corner, 1),
    }


def _detect_zenith_nadir(img):
    """Check if equirectangular image has zenith (top) and nadir (bottom).

    In a true spherical equirectangular, the top/bottom rows show
    compressed zenith/nadir content — they shouldn't be all black.
    """
    h, w = img.shape[:2]
    if h < 40 or w < 40:
        return {"is_full_sphere": False, "confidence": 0.0}

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Sample top 5% and bottom 5%
    band_height = max(h // 20, 1)
    top_band = gray[:band_height, :]
    bottom_band = gray[-band_height:, :]

    # Black fraction: how much is near-black (< 10)?
    top_black = float(np.mean(top_band < 10))
    bottom_black = float(np.mean(bottom_band < 10))

    has_zenith = top_black < 0.30
    has_nadir = bottom_black < 0.30

    if has_zenith and has_nadir:
        return {
            "is_full_sphere": True,
            "confidence": 0.75,
            "top_black_pct": round(top_black * 100, 1),
            "bottom_black_pct": round(bottom_black * 100, 1),
        }
    elif has_zenith or has_nadir:
        return {
            "is_full_sphere": False,
            "partial_sphere": True,
            "confidence": 0.60,
            "top_black_pct": round(top_black * 100, 1),
            "bottom_black_pct": round(bottom_black * 100, 1),
            "reason": "one of zenith/nadir appears absent",
        }
    else:
        return {
            "is_full_sphere": False,
            "confidence": 0.70,
            "top_black_pct": round(top_black * 100, 1),
            "bottom_black_pct": round(bottom_black * 100, 1),
            "reason": "zenith and/or nadir appear absent",
        }


def _detect_equirectangular_distortion(img):
    """Detect equirectangular-typical stretching at image top/bottom.

    In equirectangular, horizontal detail is smeared at the poles.
    Horizontal gradient energy should be lower at top/bottom than middle.
    """
    h, w = img.shape[:2]
    if h < 30:
        return {"is_equirectangular": False, "confidence": 0.0}

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    strip_h = max(h // 10, 1)

    def h_gradient_energy(strip):
        gx = cv2.Sobel(strip, cv2.CV_64F, 1, 0)
        return float(np.mean(np.abs(gx)))

    top_energy = h_gradient_energy(gray[:strip_h, :])
    mid_energy = h_gradient_energy(gray[h // 3 : 2 * h // 3, :])
    bottom_energy = h_gradient_energy(gray[-strip_h:, :])

    top_bottom_max = max(top_energy, bottom_energy)

    if mid_energy > 1.5 * top_bottom_max:
        return {
            "is_equirectangular": True,
            "confidence": 0.65,
            "mid_energy": round(mid_energy, 1),
            "top_energy": round(top_energy, 1),
            "bottom_energy": round(bottom_energy, 1),
        }

    return {"is_equirectangular": False, "confidence": 0.0}


def _detect_stitch_seams(img):
    """Look for vertical seam lines characteristic of stitched panoramas."""
    h, w = img.shape[:2]
    if w < 200:
        return {"is_stitched": False, "confidence": 0.0}

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Horizontal gradient → vertical edges
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0)
    abs_sobel_x = np.abs(sobel_x)

    # Sum vertically to find columns with strong vertical edges
    column_edges = np.sum(abs_sobel_x, axis=0).astype(float)
    col_max = float(np.max(column_edges))
    if col_max == 0:
        return {"is_stitched": False, "confidence": 0.0}

    column_edges /= col_max

    # Local average over 50px window
    window = 50
    kernel = np.ones(window) / window
    local_avg = np.convolve(column_edges, kernel, mode="same")

    # Peaks: columns where edge strength > 2x local average
    peaks = np.where(column_edges > 2.0 * local_avg)[0]

    if len(peaks) >= 2:
        spacings = np.diff(peaks)
        if len(spacings) >= 2:
            spacing_mean = float(np.mean(spacings))
            spacing_std = float(np.std(spacings))
            if spacing_mean > 100 and spacing_std / max(spacing_mean, 1) < 0.3:
                return {
                    "is_stitched": True,
                    "confidence": 0.70,
                    "seam_count": int(len(peaks)),
                    "mean_spacing": round(spacing_mean, 1),
                }

    return {"is_stitched": False, "confidence": 0.0}
