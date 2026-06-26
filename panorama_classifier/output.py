"""
Commons wikitext output generator.

Takes a final classification and produces copy-paste-ready wikitext
for a Wikimedia Commons file page, including suggested categories
and templates.
"""


def generate_wikitext(classification, filename="", extra_cats=None):
    """Generate Commons wikitext block from classification result.

    Args:
        classification: dict from fusion.fuse_results()
        filename: original filename (for PanoViewer template)
        extra_cats: optional list of additional category strings

    Returns:
        str: wikitext ready for a Commons file description page
    """
    pano_type = classification.get("type", "unknown")
    projection = classification.get("projection", "unknown")
    confidence = classification.get("confidence", 0.0)
    details = classification.get("details", {})

    cats = []
    templates = []
    notes = []

    # ---- Category logic ----
    if pano_type == "spherical":
        cats.append("[[Category:Spherical panoramas]]")
        if projection == "equirectangular":
            cats.append("[[Category:360° panoramas with equirectangular projection]]")
        cats.append("[[Category:360° panoramic photographs]]")
        cats.append("[[Category:360° panoramas]]")

    elif pano_type == "cylindrical":
        cats.append("[[Category:360° panoramas]]")
        cats.append("[[Category:360° panoramic photographs]]")

    elif pano_type == "polar_little_planet":
        cats.append("[[Category:Polar coordinates panoramic photographs]]")
        cats.append("[[Category:Spherical panoramas]]")

    elif pano_type == "cubemap_face":
        cats.append("[[Category:Cubemap representation of 360° panorama]]")
        cats.append("[[Category:Spherical panoramas]]")

    elif pano_type == "stitched_panorama":
        cats.append("[[Category:Stitched panoramic photographs]]")
        cat_by_angle = _angle_category(details)
        if cat_by_angle:
            cats.append(cat_by_angle)
        else:
            cats.append("[[Category:Panoramic photographs]]")

    elif pano_type in ("partial", "likely_cylindrical"):
        cats.append("[[Category:Panoramic photographs]]")
        cat_by_angle = _angle_category(details)
        if cat_by_angle:
            cats.append(cat_by_angle)

    elif pano_type in ("likely_spherical_equirectangular", "likely_360"):
        # High confidence heuristics → treat as probable spherical/360
        if confidence >= 0.70:
            if pano_type == "likely_spherical_equirectangular":
                cats.append("[[Category:Spherical panoramas]]")
                cats.append("[[Category:360° panoramas with equirectangular projection]]")
            cats.append("[[Category:360° panoramas]]")
            cats.append("[[Category:360° panoramic photographs]]")
            notes.append("<!-- Auto-detected as panorama. Please verify. -->")
        else:
            notes.append("<!-- Possible panorama — please verify and add appropriate categories. -->")

    elif pano_type == "likely_not_panorama":
        notes.append("<!-- This file does not appear to be a panorama. -->")

    # ---- Camera-specific category ----
    camera_cat = details.get("commons_category")
    if camera_cat:
        cats.append(f"[[Category:{camera_cat}]]")

    # ---- Extra categories from caller ----
    if extra_cats:
        cats.extend(extra_cats)

    # ---- Template logic ----
    if pano_type in ("spherical", "likely_spherical_equirectangular"):
        templates.append("{{Pano360|cat=[[Category:Spherical panoramas]]}}")
    elif pano_type in ("cylindrical", "likely_cylindrical", "likely_360", "stitched_panorama"):
        templates.append("{{Pano360}}")

    # Add metadata template if projection is known
    proj_map = {
        "equirectangular": "equirectangular",
        "cylindrical": "cylindric",
        "rectilinear": "rectilinear",
        "stereographic": "stereographic",
    }
    proj_value = proj_map.get(projection, "")
    if proj_value:
        templates.append(f"{{{{Panorama|1=|4={proj_value}}}}}")

    # ---- Assemble ----
    parts = []

    if notes:
        parts.append("\n".join(notes))
        parts.append("")

    parts.append("== {{int:filedesc}} ==")
    parts.append("{{Information")
    parts.append("|description=")
    parts.append("|date=")
    parts.append("|source={{own}}")
    parts.append("|author=")
    parts.append("}}")

    if templates:
        parts.append("")
        parts.extend(templates)

    if cats:
        parts.append("")
        parts.extend(cats)

    parts.append("")
    return "\n".join(parts)


def _angle_category(details):
    """Suggest an angle-based category from image details."""
    # Try to determine angle from aspect ratio or GPano coverage
    ar = details.get("aspect_ratio")
    h_coverage = details.get("h_coverage")

    if h_coverage:
        angle = int(h_coverage * 360)
    elif ar and ar > 2.0:
        # Rough estimate: wider AR → wider angle
        if ar > 6.0:
            angle = 360
        elif ar > 3.5:
            angle = 270
        elif ar > 2.5:
            angle = 180
        else:
            angle = 90
    else:
        return None

    if angle >= 330:
        return None  # already covered by 360° categories
    elif angle >= 240:
        return "[[Category:270° panoramas]]"
    elif angle >= 150:
        return "[[Category:180° panoramas]]"
    elif angle >= 70:
        return "[[Category:90° panoramas]]"
    return None


def generate_summary(classification, filename=""):
    """Generate a human-readable summary of the classification."""
    pano_type = classification.get("type", "unknown")
    projection = classification.get("projection", "unknown")
    confidence = classification.get("confidence", 0.0)
    source = classification.get("source", "unknown")
    details = classification.get("details", {})

    type_names = {
        "spherical": "Full spherical panorama (360°×180°)",
        "cylindrical": "360° cylindrical (ring) panorama",
        "polar_little_planet": "Polar/little planet projection",
        "cubemap_face": "Cube map face",
        "stitched_panorama": "Stitched panorama",
        "partial": "Partial panorama",
        "likely_spherical_equirectangular": "Likely spherical equirectangular (2:1)",
        "likely_cylindrical": "Likely cylindrical panorama",
        "likely_360": "Likely 360° panorama",
        "likely_partial_stitched": "Wide stitched partial panorama",
        "ambiguous_wide": "Ambiguous wide image",
        "ambiguous_square": "Ambiguous square image",
        "likely_not_panorama": "Does not appear to be a panorama",
        "unknown": "Unknown — could not classify",
    }

    lines = []
    lines.append(f"File: {filename}")
    lines.append(f"Classification: {type_names.get(pano_type, pano_type)}")
    lines.append(f"Projection: {projection}")
    lines.append(f"Confidence: {confidence:.0%}")
    lines.append(f"Detection source: {source}")

    # Relevant details
    for key, value in details.items():
        if key in ("reason",):
            lines.append(f"  {key}: {value}")

    return "\n".join(lines)
