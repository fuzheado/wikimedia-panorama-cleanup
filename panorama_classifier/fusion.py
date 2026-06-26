"""
Fusion engine: combine signals from all layers into a final classification.

Hierarchical voting — more reliable sources override less reliable ones.
Priority: GPano XMP > Camera DB + aspect > Pixel analysis > Filename > Unknown
"""


def fuse_results(metadata_result, heuristic_results, pixel_results):
    """Combine all layer results into a final classification.

    Args:
        metadata_result: dict from metadata.py classify_from_gpano()
        heuristic_results: dict with 'aspect_ratio', 'camera', 'software', 'filename'
        pixel_results: dict from pixel_analysis.py analyze_pixels()

    Returns:
        dict with final classification
    """
    # ---- Layer 1: GPano metadata is the gold standard ----
    if metadata_result and metadata_result.get("confidence", 0) >= 0.99:
        return _finalize(metadata_result)

    # ---- Camera DB + aspect ratio agreement → high confidence ----
    camera = heuristic_results.get("camera")
    ar_result = heuristic_results.get("aspect_ratio")

    if camera and camera.get("confidence", 0) >= 0.85:
        if ar_result and (
            ar_result.get("type") == "likely_spherical_equirectangular"
            or ar_result.get("confidence", 0) >= 0.60
        ):
            return _finalize(
                {
                    "type": "spherical",
                    "projection": camera.get("projection", "equirectangular"),
                    "confidence": 0.92,
                    "source": "camera_db+aspect",
                    "camera": camera.get("camera"),
                    "commons_category": camera.get("commons_category"),
                }
            )
        # Camera says 360° but aspect ratio doesn't confirm → trust camera
        return _finalize(
            {**camera, "confidence": 0.85, "source": "camera_db_only"}
        )

    # ---- Software tag (e.g., "Photo Sphere" or "Hugin") ----
    software = heuristic_results.get("software")
    if software and software.get("confidence", 0) >= 0.80:
        return _finalize(software)

    # ---- Pixel analysis: edge continuity + zenith/nadir ----
    if pixel_results and "error" not in pixel_results:
        edge = pixel_results.get("edge_continuity", {})
        zn = pixel_results.get("zenith_nadir", {})
        polar = pixel_results.get("polar", {})
        distort = pixel_results.get("equirect_distortion", {})
        seams = pixel_results.get("stitch_seams", {})

        # Edge match + zenith/nadir present → BUT check aspect ratio first
        # A true spherical equirectangular MUST be ~2:1. If AR is far from 2:1,
        # the zenith/nadir detector is fooled by sky/ground content, not real zenith.
        ar = (ar_result or {}).get("aspect_ratio", 0)
        is_2to1 = 1.90 <= ar <= 2.15 if ar else False

        if edge.get("is_360") and zn.get("is_full_sphere") and is_2to1:
            return _finalize(
                {
                    "type": "spherical",
                    "projection": "equirectangular",
                    "confidence": 0.85,
                    "source": "edge+zenith_nadir",
                    "edge_diff": edge.get("edge_diff"),
                }
            )

        # Edge match + zenith/nadir says full sphere but AR is NOT 2:1 →
        # it's a cylindrical ring with sky/ground visible (zenith/nadir fooled)
        if edge.get("is_360") and zn.get("is_full_sphere") and not is_2to1:
            return _finalize(
                {
                    "type": "cylindrical",
                    "projection": "cylindrical",
                    "confidence": 0.75,
                    "source": "edge+ar_correction",
                    "edge_diff": edge.get("edge_diff"),
                    "reason": "zenith/nadir detector fooled by sky/ground; AR is not 2:1",
                }
            )

        # Edge match but zenith/nadir missing → cylindrical
        if edge.get("is_360") and not zn.get("is_full_sphere"):
            return _finalize(
                {
                    "type": "cylindrical",
                    "projection": "cylindrical",
                    "confidence": 0.78,
                    "source": "edge+zenith_nadir",
                    "edge_diff": edge.get("edge_diff"),
                }
            )

        # Polar/little planet detected
        if polar.get("is_polar"):
            return _finalize(
                {
                    "type": "polar_little_planet",
                    "projection": "stereographic",
                    "confidence": polar.get("confidence", 0.80),
                    "source": "polar_detection",
                }
            )

        # Edge match alone (zenith/nadir inconclusive)
        if edge.get("is_360") and edge.get("confidence", 0) >= 0.80:
            return _finalize(
                {
                    "type": "likely_360",
                    "projection": "unknown",
                    "confidence": 0.70,
                    "source": "edge_continuity_only",
                }
            )

        # Equirectangular distortion pattern
        if distort.get("is_equirectangular") and ar_result and ar_result.get("type") == "likely_spherical_equirectangular":
            return _finalize(
                {
                    "type": "spherical",
                    "projection": "equirectangular",
                    "confidence": 0.78,
                    "source": "distortion+aspect",
                }
            )

        # Stitch seams detected
        if seams.get("is_stitched"):
            return _finalize(
                {
                    "type": "stitched_panorama",
                    "projection": "unknown",
                    "confidence": seams.get("confidence", 0.65),
                    "source": "stitch_detection",
                    "seam_count": seams.get("seam_count"),
                }
            )

    # ---- Fallback: software says stitched ----
    if software and software.get("stitched"):
        return _finalize(
            {
                "type": "stitched_panorama",
                "projection": "unknown",
                "confidence": 0.55,
                "source": "software_tag_stitched",
                "software": software.get("software"),
            }
        )

    # ---- Fallback: aspect ratio heuristic ----
    if ar_result:
        return _finalize(ar_result)

    # ---- Last resort ----
    return _finalize(
        {
            "type": "unknown",
            "projection": "unknown",
            "confidence": 0.0,
            "source": "none",
        }
    )


def _finalize(result):
    """Add standard fields and normalize the result dict."""
    return {
        "type": result.get("type", "unknown"),
        "projection": result.get("projection", "unknown"),
        "confidence": round(result.get("confidence", 0.0), 3),
        "source": result.get("source", "unknown"),
        "details": {k: v for k, v in result.items()
                    if k not in ("type", "projection", "confidence", "source")},
    }
