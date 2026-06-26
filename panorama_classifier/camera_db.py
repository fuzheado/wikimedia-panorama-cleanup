"""
Known 360° camera database.

Each entry maps (Make, Model_substring) → camera info.
Used by heuristics.py to identify 360° cameras from EXIF data.
"""

KNOWN_360_CAMERAS = [
    {
        "make": "RICOH",
        "model_substr": "THETA",
        "full_sphere": True,
        "projection": "equirectangular",
        "commons_category": "Taken with Ricoh Theta series",
        "typical_resolutions": [(5376, 2688), (6720, 3360)],
    },
    {
        "make": "Insta360",
        "model_substr": None,
        "full_sphere": True,
        "projection": "equirectangular",
        "commons_category": "Taken with Insta360",
        "typical_resolutions": [(6080, 3040), (6912, 3456), (7680, 3840), (8192, 4096)],
    },
    {
        "make": "SAMSUNG",
        "model_substr": "Gear 360",
        "full_sphere": True,
        "projection": "equirectangular",
        "commons_category": "Taken with Samsung Gear 360",
        "typical_resolutions": [(7776, 3888), (5792, 2896)],
    },
    {
        "make": "NIKON",
        "model_substr": "KeyMission 360",
        "full_sphere": True,
        "projection": "equirectangular",
        "commons_category": "Taken with Nikon KeyMission 360",
        "typical_resolutions": [(7744, 3872)],
    },
    {
        "make": "GoPro",
        "model_substr": "MAX",
        "full_sphere": True,
        "projection": "equirectangular",
        "commons_category": None,
        "typical_resolutions": [(5376, 2688), (5760, 2880)],
    },
    {
        "make": "NCTECH",
        "model_substr": "iSTAR",
        "full_sphere": True,
        "projection": "equirectangular",
        "commons_category": "Taken with NCTECH iSTAR Pulsar",
        "typical_resolutions": None,
    },
    {
        "make": "KANDAO",
        "model_substr": None,
        "full_sphere": True,
        "projection": "equirectangular",
        "commons_category": None,
        "typical_resolutions": None,
    },
    {
        "make": "Huawei",
        "model_substr": "360",
        "full_sphere": True,
        "projection": "equirectangular",
        "commons_category": "Taken with Huawei Panorama 360 Camera CV60",
        "typical_resolutions": None,
    },
    # Smartphones known to produce Photo Spheres
    {
        "make": "Google",
        "model_substr": None,
        "full_sphere": True,
        "projection": "equirectangular",
        "commons_category": "Photo Sphere",
        "typical_resolutions": None,
    },
]

# Stitching software that indicates a panorama
STITCHING_SOFTWARE = {
    "Hugin": {"stitched": True},
    "PTGui": {"stitched": True},
    "PTGui Pro": {"stitched": True},
    "AutoPano": {"stitched": True},
    "AutoPano Giga": {"stitched": True},
    "PanoramaStudio": {"stitched": True},
    "Microsoft ICE": {"stitched": True},
    "Image Composite Editor": {"stitched": True},
    "Photo Sphere": {"stitched": True, "full_sphere": True, "projection": "equirectangular"},
    "RICOH THETA": {"stitched": True, "full_sphere": True, "projection": "equirectangular"},
}


def lookup_camera(make, model):
    """Check if a camera make/model matches a known 360° camera."""
    if not make and not model:
        return None

    make_upper = (make or "").upper().strip()
    model_upper = (model or "").upper().strip()

    for cam in KNOWN_360_CAMERAS:
        cam_make = cam["make"].upper()
        cam_model = (cam.get("model_substr") or "").upper()

        # Make must match exactly
        if cam_make not in make_upper and make_upper not in cam_make:
            # Allow partial match like "RICOH" in "RICOH COMPANY, LTD."
            if cam_make not in make_upper and make_upper not in cam_make:
                continue

        # If camera has a model substring requirement, check it
        if cam_model and cam_model not in model_upper:
            continue

        return cam

    return None


def lookup_stitching_software(software):
    """Check if software string indicates stitching."""
    if not software:
        return None
    return STITCHING_SOFTWARE.get(software.strip())
