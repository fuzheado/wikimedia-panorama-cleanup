# Panorama Photo Auto-Classifier: Design Document

> **Goal:** A Python CLI utility that takes a single image file and outputs a structured classification — what type of panorama it is, which Commons categories it should get, which templates to use, and what metadata to add or fix.

---

## 1. Architecture Overview

```
                    ┌─────────────────────────────┐
   image.jpg ──────►│       Classification        │──────► JSON report
                    │        Pipeline              │       + suggested
                    │                             │       wikitext
                    │  Layer 0: File stats         │
                    │  Layer 1: Metadata (EXIF,    │
                    │           XMP, GPano)        │
                    │  Layer 2: Heuristics         │
                    │           (aspect ratio,     │
                    │            camera DB)        │
                    │  Layer 3: Pixel analysis     │
                    │           (OpenCV/numpy)     │
                    │  Layer 4: ML vision model    │
                    │           (optional, heavy)  │
                    └─────────────────────────────┘
```

**Key principle:** Start with zero-cost checks (file size, dimensions) and escalate only when earlier layers are inconclusive. Most images will be classified at Layer 1 or 2 with high confidence.

**Output:** A JSON report + optional wikitext block ready to paste into a Commons file page.

---

## 2. Layer 0: File Statistics (milliseconds)

Zero parsing. Just `os.stat()` and a quick header peek.

| Check | Method | What it tells us |
|-------|--------|-----------------|
| File size | `os.path.getsize()` | Heuristic: files under ~50KB are unlikely to be stitch-quality panoramas |
| File extension | path suffix | `.jpg`/`.jpeg` → can embed GPano XMP. `.png` → probably not a 360° photo (XMP less common). `.tif` → possibly high-res stitch |
| Magic bytes | first 4 bytes | Verify it's actually a JPEG/PNG/TIFF, not misnamed |
| Image dimensions | `PIL.Image.open()` (header only, no decode) | aspect ratio is the single strongest feature |

**Fast path at this layer:** If aspect ratio is, say, 1.33:1 (standard 4:3) and the file isn't from a known 360° camera, we can already say "probably not a panorama" with medium confidence. But we never stop here — always proceed to metadata.

### Optional pre-check: is it even a photo?

Use `PIL.Image.open()` mode: `1` or `L` (grayscale) is unusual for modern panoramas but possible. `RGB` or `YCbCr` is expected. `CMYK` suggests a print-ready file, not a panorama.

---

## 3. Layer 1: Metadata Extraction (milliseconds)

This is the **gold standard** — when GPano XMP metadata is present, classification is near-certain.

### 3.1 GPano XMP Namespace

Google's Photo Sphere XMP schema, now used by virtually all 360° cameras (Ricoh Theta, Insta360, Samsung Gear 360, etc.):

```python
# Extract using pyexiv2, exiftool, or PIL + xml.etree
GPANO_TAGS = {
    "UsePanoramaViewer":    bool,     # True → it's a panorama
    "ProjectionType":       str,      # "equirectangular" (virtually always)
    "FullPanoWidthPixels":  int,      # stitched width (e.g., 8000)
    "FullPanoHeightPixels": int,      # stitched height (e.g., 4000)
    "CroppedAreaImageWidthPixels":  int,   # actual image width
    "CroppedAreaImageHeightPixels": int,   # actual image height
    "CroppedAreaLeftPixels":   int,        # crop offset from left
    "CroppedAreaTopPixels":    int,        # crop offset from top
    "PoseHeadingDegrees":      float,      # compass direction
    "PosePitchDegrees":        float,
    "PoseRollDegrees":         float,
    "FirstPhotoDate":          str,        # when capture started
    "LastPhotoDate":           str,        # when capture ended
    "SourcePhotosCount":       int,        # number of frames
}
```

**Classification from GPano:**

```python
def classify_from_gpano(tags):
    if not tags.get("UsePanoramaViewer"):
        return {"type": "not_panorama"}  # explicitly marked as not one

    full_w = tags["FullPanoWidthPixels"]
    full_h = tags["FullPanoHeightPixels"]
    crop_w = tags.get("CroppedAreaImageWidthPixels", full_w)
    crop_h = tags.get("CroppedAreaImageHeightPixels", full_h)

    # Full sphere check: full 360° horizontal AND 180° vertical
    h_coverage = crop_w / full_w   # 1.0 = full 360°
    v_coverage = crop_h / full_h   # 1.0 = full 180°

    spherical = (h_coverage >= 0.98 and v_coverage >= 0.98)

    # If height is only, say, 40% of full height → it's a ring panorama
    # (zenith and/or nadir missing)
    ring_only = (h_coverage >= 0.98 and v_coverage < 0.90)

    projection = tags.get("ProjectionType", "equirectangular")

    return {
        "type": "spherical" if spherical else ("cylindrical" if ring_only else "partial"),
        "projection": projection,
        "h_coverage": h_coverage,
        "v_coverage": v_coverage,
        "confidence": 0.99,
        "source": "gpano_xmp"
    }
```

### 3.2 EXIF Data

```python
EXIF_TAGS_OF_INTEREST = {
    "Make":        str,    # Camera manufacturer
    "Model":       str,    # Camera model
    "Software":    str,    # Stitching software (Hugin, PTGui, AutoPano, Photoshop)
    "ImageWidth":  int,
    "ImageHeight": int,
    "Orientation": int,    # 1=normal, 6=rotated 90° CW, etc.
    "DateTimeOriginal": str,
    "GPSInfo":     dict,   # GPS coordinates
    "ExifImageWidth":  int,   # sometimes different from ImageWidth
    "ExifImageHeight": int,
}
```

### 3.3 Known Camera Database

Many 360° cameras produce consistent output patterns. A lookup table:

```python
KNOWN_360_CAMERAS = {
    # (Make, Model substring) → {output_projection, typical_full_sphere, category}
    ("RICOH", "THETA"): {
        "projection": "equirectangular",
        "full_sphere": True,
        "typical_resolution": [(5376, 2688), (6720, 3360)],
        "commons_category": "Taken with Ricoh Theta series"
    },
    ("Insta360", None): {
        "projection": "equirectangular",
        "full_sphere": True,
        "typical_resolution": [(6080, 3040), (6912, 3456), (7680, 3840)],
        "commons_category": "Taken with Insta360"
    },
    ("SAMSUNG", "Gear 360"): {
        "projection": "equirectangular",
        "full_sphere": True,
        "typical_resolution": [(7776, 3888), (5792, 2896)],
        "commons_category": "Taken with Samsung Gear 360"
    },
    ("NIKON", "KeyMission 360"): {
        "projection": "equirectangular",
        "full_sphere": True,
        "typical_resolution": [(7744, 3872)],
        "commons_category": "Taken with Nikon KeyMission 360"
    },
    ("GoPro", "MAX"): {
        "projection": "equirectangular",
        "full_sphere": True,
        "typical_resolution": [(5376, 2688), (5760, 2880)],
        "commons_category": None  # no Commons category yet
    },
    # Smartphones that do Photo Sphere
    ("Google", "Pixel"): {
        "projection": "equirectangular",
        "full_sphere": True,  # but quality varies — sometimes ring only
        "commons_category": "Photo_Sphere"
    },
    # ... expand as needed
}
```

Camera identification alone gives us a strong prior, but we still check GPano for the actual field-of-view coverage (a phone can do a partial Photo Sphere).

---

## 4. Layer 2: Heuristics & Database Lookups (milliseconds)

When GPano metadata is absent (older files, stitched from DSLR, non-standard cameras), fall back to heuristics.

### 4.1 Aspect Ratio Classifier

```python
def classify_by_aspect_ratio(width, height):
    ar = width / height

    if 1.98 <= ar <= 2.02:
        # Near-perfect 2:1 → VERY likely equirectangular spherical
        return {"type": "likely_spherical_equirectangular", "confidence": 0.75}
    elif 2.02 < ar <= 3.0:
        # Wider than 2:1 but not extreme → could be cropped equirectangular
        # or a cylindrical panorama with some vertical coverage
        return {"type": "likely_cylindrical_or_cropped_spherical", "confidence": 0.50}
    elif 3.0 < ar <= 8.0:
        # Wide strip → cylindrical panorama (360° ring, limited vertical)
        return {"type": "likely_cylindrical", "confidence": 0.70}
    elif ar > 8.0:
        # Very wide strip → multi-frame horizontal panorama
        return {"type": "likely_partial_stitched", "confidence": 0.80}
    elif 0.95 <= ar <= 1.05:
        # Square → could be cubemap face, little planet, or just a square crop
        return {"type": "ambiguous_square", "confidence": 0.20}
    else:
        # Standard or portrait aspect ratio → unlikely to be a panorama
        return {"type": "likely_not_panorama", "confidence": 0.60}
```

### 4.2 FileName Heuristics

Many users name their files descriptively. Pattern matching:

```python
FILENAME_PATTERNS = [
    (r"(?i)(pano|panorama|360|photosphere|equirect|equirectangular)"
     r"(?!.*(thumb|preview|icon))", "panorama_keyword", 0.15),
    (r"(?i)(little.planet|tiny.planet|planet.pano)", "little_planet", 0.60),
    (r"(?i)(nadir|zenith|cube.?map|cubemap|face\.(jpg|png))", "cubemap_face", 0.70),
    (r"(?i)(stitch)", "stitched", 0.40),
    (r"(?i)(IMG_\d{4}|DSC\d+|P\d{7})", "default_camera_name", -0.10),
]
```

Low weight — never decisive alone, but can break ties.

### 4.3 Software Detection

The EXIF `Software` tag often reveals how the image was made:

```python
STITCHING_SOFTWARE = {
    "Hugin":        {"stitched": True,  "projection": None},
    "PTGui":        {"stitched": True,  "projection": None},
    "AutoPano":     {"stitched": True,  "projection": None},
    "Adobe Photoshop": {"stitched": False, "projection": None},  # could be anything
    "Photo Sphere": {"stitched": True,  "projection": "equirectangular", "full_sphere": True},
    "RICOH THETA":  {"stitched": True,  "projection": "equirectangular", "full_sphere": True},
}
```

---

## 5. Layer 3: Pixel Analysis with OpenCV (milliseconds to seconds)

When metadata is absent or inconclusive, we analyze the actual image content. This is the most interesting layer.

### 5.1 Edge Continuity Check (360° Seam Detection)

For an equirectangular panorama, the left and right edges should match because they're the same meridian.

```python
import cv2
import numpy as np

def check_edge_continuity(image, sample_width=10):
    """Check if left edge matches right edge (indicates 360° wrap)."""
    h, w = image.shape[:2]

    # Sample a strip from left edge
    left_strip = image[:, :sample_width]
    # Sample a strip from right edge
    right_strip = image[:, -sample_width:]

    # Compute mean absolute difference along each row
    diff = np.mean(np.abs(left_strip.astype(float) - right_strip.astype(float)))

    # Normalize by 255
    normalized_diff = diff / 255.0

    # If diff < threshold → edges match → 360° panorama
    # Typical threshold: 0.05-0.10 for well-stitched, 0.10-0.20 for okay
    if normalized_diff < 0.08:
        return {"is_360": True, "confidence": 0.90, "edge_diff": normalized_diff}
    elif normalized_diff < 0.15:
        return {"is_360": True, "confidence": 0.60, "edge_diff": normalized_diff}
    else:
        return {"is_360": False, "confidence": 0.70, "edge_diff": normalized_diff}
```

**Caveat:** This can produce false positives if the image just happens to have uniform edges (e.g., a blue sky photo). But for actual classification pipelines, the confidence should be combined with other signals.

### 5.2 Polar/Circular Content Detection (Little Planet)

Little planet images have content in a circular region with dark/blank corners:

```python
def detect_polar_projection(image):
    """Detect if image is a polar/little-planet projection."""
    h, w = image.shape[:2]

    # Create circular mask
    center = (w // 2, h // 2)
    radius = min(w, h) // 2

    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(mask, center, radius, 255, -1)

    # Invert to get corner mask
    corners = cv2.bitwise_not(mask)

    # Analyze corners: are they dark or nearly uniform?
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    corner_pixels = gray[corners == 255]

    if len(corner_pixels) == 0:
        return {"is_polar": False, "confidence": 0.0}

    mean_corner = np.mean(corner_pixels)
    std_corner = np.std(corner_pixels)

    # Corners of little planet should be dark and uniform
    is_dark_uniform = (mean_corner < 30 and std_corner < 15)

    # Additional check: is the content circular?
    # Compute gradient at circle boundary
    if is_dark_uniform:
        return {"is_polar": True, "confidence": 0.85}
    else:
        return {"is_polar": False, "confidence": 0.0}
```

### 5.3 Zenith/Nadir Presence Detection (Spherical vs. Cylindrical)

For an equirectangular image, the **topmost row** represents the zenith (straight up) — it should be a compressed version of what's directly overhead. The **bottommost row** represents the nadir (straight down). In a cylindrical/ring panorama, these areas are simply missing.

```python
def detect_zenith_nadir(image):
    """Check if an equirectangular image has zenith (top) and nadir (bottom)."""
    h, w = image.shape[:2]

    # Sample top strip (zenith region, top ~5% of image)
    top_band = image[0:h//20, :]
    # Sample bottom strip (nadir region, bottom ~5%)
    bottom_band = image[-h//20:, :]

    # For a true spherical equirectangular:
    # - The top row should be highly compressed (all zenith points map to a line)
    # - It should show reasonable variation (not just a solid color, unless sky was uniform)

    top_std = np.std(top_band)
    bottom_std = np.std(bottom_band)

    # If both top and bottom have some variation but are compressed,
    # it suggests zenith/nadir are present
    # If one or both are extremely uniform (like solid black) → missing

    # Check for large black areas (missing zenith/nadir)
    gray_top = cv2.cvtColor(top_band, cv2.COLOR_BGR2GRAY) if len(top_band.shape) == 3 else top_band
    gray_bottom = cv2.cvtColor(bottom_band, cv2.COLOR_BGR2GRAY) if len(bottom_band.shape) == 3 else bottom_band

    top_black_fraction = np.mean(gray_top < 10)
    bottom_black_fraction = np.mean(gray_bottom < 10)

    has_zenith = top_black_fraction < 0.30   # less than 30% black → probably has zenith
    has_nadir = bottom_black_fraction < 0.30

    if has_zenith and has_nadir:
        return {"is_full_sphere": True, "confidence": 0.75}
    elif has_zenith or has_nadir:
        return {"is_full_sphere": False, "partial_sphere": True, "confidence": 0.60}
    else:
        return {"is_full_sphere": False, "confidence": 0.70,
                "reason": "zenith and/or nadir appear absent"}
```

### 5.4 Cubemap Face Detection

Cube map faces are square 1:1 images. They have specific characteristics:

```python
def detect_cubemap_face(image):
    """Detect if a square image is a cube map face."""
    h, w = image.shape[:2]

    if abs(w - h) > max(w, h) * 0.02:  # not square within 2% tolerance
        return {"is_cubemap_face": False, "confidence": 0.0}

    # Cube map faces typically have:
    # - No strong vignetting (processed from stitched equirectangular)
    # - Uniform sharpness (no lens blur at edges)
    # - Content with perspective projection (straight lines stay straight)

    # Edge analysis: cubemap faces don't have the distortion pattern of
    # equirectangular images at top/bottom
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Check edge sharpness at corners vs center
    center_region = gray[h//4:3*h//4, w//4:3*w//4]
    center_sharpness = cv2.Laplacian(center_region, cv2.CV_64F).var()

    corners = [
        gray[0:h//10, 0:w//10],
        gray[0:h//10, -w//10:],
        gray[-h//10:, 0:w//10],
        gray[-h//10:, -w//10:]
    ]
    corner_sharpness = np.mean([cv2.Laplacian(c, cv2.CV_64F).var() for c in corners])

    # If corners are as sharp as center → consistent with cubemap
    sharpness_ratio = corner_sharpness / max(center_sharpness, 1)
    if 0.5 < sharpness_ratio < 2.0:
        return {"is_cubemap_face": True, "confidence": 0.55}
    else:
        return {"is_cubemap_face": False, "confidence": 0.0}
```

### 5.5 Distortion Pattern Analysis

Equirectangular images have a characteristic distortion: the top and bottom are stretched horizontally.

```python
def detect_equirectangular_distortion(image):
    """Look for equirectangular-typical stretching at top/bottom."""
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Sample horizontal gradients at different vertical positions
    # In equirectangular, horizontal detail should be more "smeared" at top/bottom

    def horizontal_gradient_energy(strip):
        gx = cv2.Sobel(strip, cv2.CV_64F, 1, 0)
        return np.mean(np.abs(gx))

    top_strip = gray[0:h//10, :]
    mid_strip = gray[h//3:2*h//3, :]
    bottom_strip = gray[-h//10:, :]

    top_h_energy = horizontal_gradient_energy(top_strip)
    mid_h_energy = horizontal_gradient_energy(mid_strip)
    bottom_h_energy = horizontal_gradient_energy(bottom_strip)

    # In equirectangular: middle has more sharp horizontal detail
    # Top/bottom are stretched → less horizontal gradient energy
    if mid_h_energy > 1.5 * max(top_h_energy, bottom_h_energy):
        return {"is_equirectangular": True, "confidence": 0.65}
    else:
        return {"is_equirectangular": False, "confidence": 0.0}
```

### 5.6 Stitch Seam Detection

Panoramas often have visible seams or ghosting where frames were stitched:

```python
def detect_stitch_artifacts(image):
    """Look for vertical seam lines characteristic of stitched panoramas."""
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Compute vertical gradient (strong vertical edges = possible seams)
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0)  # horizontal gradient
    abs_sobel_x = np.abs(sobel_x)

    # Sum horizontally to find columns with strong vertical edges
    column_edges = np.sum(abs_sobel_x, axis=0)

    # In stitched panoramas, seams appear at regular intervals
    # Look for regularly spaced peaks in column_edges

    # Normalize
    column_edges = column_edges / max(np.max(column_edges), 1)

    # Find peaks (columns where edge strength is > 2x local average)
    local_avg = np.convolve(column_edges, np.ones(50)/50, mode='same')
    peaks = np.where(column_edges > 2.0 * local_avg)[0]

    if len(peaks) >= 2:
        # Check if peaks are roughly evenly spaced
        spacings = np.diff(peaks)
        if len(spacings) >= 2:
            spacing_std = np.std(spacings)
            spacing_mean = np.mean(spacings)
            if spacing_mean > 100 and spacing_std / spacing_mean < 0.3:
                return {"is_stitched": True, "confidence": 0.70,
                        "seam_count": len(peaks)}
    return {"is_stitched": False, "confidence": 0.0}
```

---

## 6. Layer 4: ML Vision Model (seconds, optional)

For cases where all heuristics are inconclusive, we could use a pre-trained vision model. This is heavyweight but could handle edge cases like:
- Distinguishing between equirectangular and a wide landscape photo
- Detecting "little planet" vs. a circular fisheye photo of a round object
- Identifying whether an image is actually a photograph vs. a 3D render

```python
# Using CLIP, a relatively lightweight multimodal model
# pip install open-clip-torch

def classify_with_clip(image_path):
    """
    Use CLIP zero-shot classification to determine panorama type.
    """
    import open_clip
    import torch

    model, _, preprocess = open_clip.create_model_and_transforms(
        'ViT-B-32', pretrained='laion2b_s34b_b79k'
    )
    tokenizer = open_clip.get_tokenizer('ViT-B-32')

    image = preprocess(Image.open(image_path)).unsqueeze(0)

    labels = [
        "an equirectangular 360 degree spherical panorama photograph",
        "a cylindrical 360 degree panorama photograph (horizontal band only)",
        "a little planet stereographic projection photograph",
        "a cube map face of a 360 degree panorama",
        "a standard wide-angle landscape photograph (not a panorama)",
        "a stitched panoramic photograph wider than 180 degrees",
        "a fisheye lens photograph",
        "a computer generated 3D render",
    ]

    text = tokenizer(labels)

    with torch.no_grad():
        image_features = model.encode_image(image)
        text_features = model.encode_text(text)
        image_features /= image_features.norm(dim=-1, keepdim=True)
        text_features /= text_features.norm(dim=-1, keepdim=True)
        similarity = (100.0 * image_features @ text_features.T).softmax(dim=-1)

    # Return top label with confidence
    probs = similarity[0].tolist()
    best_idx = probs.index(max(probs))

    return {
        "classification": labels[best_idx],
        "confidence": probs[best_idx],
        "all_probs": dict(zip(labels, probs))
    }
```

**When to use:** Only when Layers 0-3 all return confidence < 0.70, or when the file has no EXIF/GPano at all and the aspect ratio is ambiguous (~2.0-3.0 range).

---

## 7. Fusion: Combining All Signals

### 7.1 Weighted Voting System

Each layer produces a set of `(type, confidence)` pairs. We combine them with a hierarchical rule engine:

```python
def fuse_classifications(layer_results):
    """
    Combine results from all layers into a final classification.

    Priority order (most to least reliable):
      1. GPano XMP metadata (confidence 0.99)
      2. Known 360° camera EXIF + standard resolution (confidence 0.90)
      3. Aspect ratio + edge continuity (confidence 0.75-0.85)
      4. Pixel content analysis (confidence 0.55-0.75)
      5. Filename heuristics (confidence 0.15-0.60)
      6. ML vision model (confidence 0.60-0.90, but expensive)
    """

    # If GPano says something, it overrides everything
    gpano = layer_results.get("gpano")
    if gpano and gpano["confidence"] > 0.95:
        return gpano

    # If camera DB says full sphere AND aspect ratio matches, high confidence
    camera = layer_results.get("camera")
    ar = layer_results.get("aspect_ratio")
    if camera and camera["full_sphere"] and ar and ar["confidence"] > 0.70:
        return {"type": "spherical", "projection": camera["projection"],
                "confidence": 0.90, "source": "camera_db+aspect"}

    # If edge continuity says 360° AND zenith/nadir says full, high confidence
    edge = layer_results.get("edge_continuity")
    zn = layer_results.get("zenith_nadir")
    if edge and edge["is_360"] and zn and zn["is_full_sphere"]:
        return {"type": "spherical", "confidence": 0.85,
                "source": "edge+zenith_nadir"}

    # If edge continuity says 360° but zenith/nadir says partial → cylindrical
    if edge and edge["is_360"] and zn and not zn["is_full_sphere"]:
        return {"type": "cylindrical", "confidence": 0.75,
                "source": "edge+zenith_nadir"}

    # If polar detection says yes, it's a little planet
    polar = layer_results.get("polar")
    if polar and polar["is_polar"]:
        return {"type": "polar_little_planet", "confidence": polar["confidence"],
                "source": "polar_detection"}

    # Fallback: use ML if available
    ml = layer_results.get("ml_vision")
    if ml and ml["confidence"] > 0.60:
        return {"type": ml["classification"], "confidence": ml["confidence"],
                "source": "ml_vision"}

    # Last resort: aspect ratio guess
    if ar:
        return ar

    return {"type": "unknown", "confidence": 0.0, "source": "none"}
```

### 7.2 Confidence Tiers

| Tier | Confidence | Action |
|------|-----------|--------|
| **Certain** | ≥ 0.90 | Auto-classify. Add categories + templates. |
| **High** | 0.75–0.89 | Auto-classify but suggest human review. |
| **Medium** | 0.50–0.74 | Suggest categories, flag for human decision. |
| **Low** | < 0.50 | No automatic categorization. "Unknown — please classify manually." |

---

## 8. Output: Generating Commons Wikitext

The ultimate output is copy-paste-ready wikitext for a Commons file page:

```python
def generate_commons_wikitext(classification):
    """Generate suggested wikitext block for Commons file page."""
    cats = []
    templates = []

    t = classification["type"]
    proj = classification.get("projection", "")

    # --- Categories ---
    if t == "spherical":
        cats.append("[[Category:Spherical panoramas]]")
        if proj == "equirectangular" or classification.get("aspect_ratio") == "2:1":
            cats.append("[[Category:360° panoramas with equirectangular projection]]")
        cats.append("[[Category:360° panoramic photographs]]")

    elif t == "cylindrical":
        cats.append("[[Category:360° panoramas]]")
        cats.append("[[Category:360° panoramic photographs]]")

    elif t == "polar_little_planet":
        cats.append("[[Category:Polar coordinates panoramic photographs]]")
        cats.append("[[Category:Spherical panoramas]]")  # it IS spherical

    elif t == "cubemap_face" or t == "cubemap":
        cats.append("[[Category:Cubemap representation of 360° panorama]]")
        cats.append("[[Category:Spherical panoramas]]")

    elif t == "partial_panorama":
        # Determine angle
        angle = classification.get("estimated_angle", 180)
        if angle <= 100:
            cats.append("[[Category:90° panoramas]]")
        elif angle <= 200:
            cats.append("[[Category:180° panoramas]]")
        elif angle <= 300:
            cats.append("[[Category:270° panoramas]]")
        else:
            cats.append("[[Category:Panoramic photographs]]")

    elif t == "likely_not_panorama":
        # Don't add panorama categories
        pass

    # --- Camera-specific ---
    camera_cat = classification.get("camera_category")
    if camera_cat:
        cats.append(f"[[Category:{camera_cat}]]")

    # --- Templates ---
    if t in ("spherical", "cylindrical"):
        cat_param = "cat=[[Category:Spherical panoramas]]" if t == "spherical" else ""
        templates.append(f"{{{{Pano360{f'|{cat_param}' if cat_param else ''}}}}}")

    # --- Metadata template ---
    projection_param = classification.get("projection", "")
    projection_mapping = {
        "equirectangular": "equirectangular",
        "cylindrical": "cylindric",
        "rectilinear": "rectilinear" 
    }
    proj_value = projection_mapping.get(projection_param, "")
    templates.append(f"{{{{Panorama|1={{{{int:description}}}}|4={proj_value}}}}}")

    # --- Assemble ---
    output = "== {{int:filedesc}} ==\n"
    output += "{{Information\n"
    output += "|description=\n"
    output += "|date=\n"
    output += "|source={{own}}\n"
    output += "|author=\n"
    output += "}}\n\n"
    if templates:
        output += "\n".join(templates) + "\n\n"
    if cats:
        output += "\n".join(cats) + "\n"

    return output
```

---

## 9. Complete Pipeline Code Skeleton

```python
#!/usr/bin/env python3
"""
panorama-classifier — Classify a photo by panorama type and suggest
Commons categories, templates, and metadata.

Usage:
    panorama-classifier image.jpg
    panorama-classifier --json image.jpg  # machine-readable output
    panorama-classifier --wikitext image.jpg  # copy-paste for Commons
    panorama-classifier --full image.jpg  # all layers, verbose
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS


@dataclass
class ClassificationResult:
    """Unified classification output."""
    # Core classification
    complete_type: str         # "spherical" | "cylindrical" | "polar_little_planet"
                               # | "cubemap_face" | "partial_panorama" | "likely_not_panorama"
                               # | "unknown"
    projection: str            # "equirectangular" | "cubemap" | "stereographic" | "cylindrical" | "rectilinear" | "unknown"
    confidence: float          # 0.0 to 1.0
    source: str                # which layer determined the result

    # Optional details
    h_coverage: Optional[float] = None    # fraction of 360° (1.0 = full)
    v_coverage: Optional[float] = None    # fraction of 180° (1.0 = full)
    estimated_angle: Optional[int] = None # horizontal degrees
    aspect_ratio: Optional[float] = None
    is_stitched: Optional[bool] = None
    camera_model: Optional[str] = None
    software: Optional[str] = None

    # Commons suggestions
    suggested_categories: list = field(default_factory=list)
    suggested_templates: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    # All layer results for debugging
    layer_results: dict = field(default_factory=dict)


class PanoramaClassifier:
    """Main classifier pipeline."""

    def __init__(self, image_path: str):
        self.path = image_path
        self.image = None  # PIL Image, lazy-loaded
        self.cv_image = None  # OpenCV image, lazy-loaded
        self.exif = {}
        self.xmp = {}
        self.gpano = {}

    def classify(self, use_ml: bool = False) -> ClassificationResult:
        """Run full classification pipeline."""
        result = ClassificationResult(
            complete_type="unknown",
            projection="unknown",
            confidence=0.0,
            source="none"
        )

        # Layer 0: File stats
        if not self._check_valid_file():
            result.warnings.append("Not a valid image file")
            return result

        # Layer 1: Metadata
        self._extract_metadata()

        # Check GPano first — highest authority
        if self.gpano:
            gpano_result = self._classify_from_gpano()
            result.layer_results["gpano"] = gpano_result
            if gpano_result["confidence"] > 0.95:
                result = self._apply_classification(result, gpano_result, "gpano")
                self._generate_suggestions(result)
                return result

        # Camera database lookup
        if self.exif:
            camera_result = self._classify_from_camera_db()
            result.layer_results["camera"] = camera_result

        # Aspect ratio
        ar_result = self._classify_by_aspect_ratio()
        result.layer_results["aspect_ratio"] = ar_result

        # Filename heuristics
        fname_result = self._classify_by_filename()
        result.layer_results["filename"] = fname_result

        # Layer 3: Pixel analysis (only if needed)
        if result.confidence < 0.70:
            self._load_cv_image()
            edge_result = self._check_edge_continuity()
            result.layer_results["edge_continuity"] = edge_result
            zn_result = self._detect_zenith_nadir()
            result.layer_results["zenith_nadir"] = zn_result
            polar_result = self._detect_polar()
            result.layer_results["polar"] = polar_result

        # Layer 4: ML (optional, expensive)
        if use_ml and result.confidence < 0.70:
            ml_result = self._classify_with_ml()
            result.layer_results["ml_vision"] = ml_result

        # Fuse all results
        result = self._fuse_results(result)
        self._generate_suggestions(result)
        return result

    def _load_cv_image(self):
        """Load image with OpenCV for pixel analysis."""
        if self.cv_image is None:
            self.cv_image = cv2.imread(self.path)
            if self.cv_image is None:
                raise ValueError(f"Cannot read image: {self.path}")

    # ... (implement all _classify_from_* methods as described above)

    def _generate_suggestions(self, result: ClassificationResult):
        """Generate Commons categories and templates from classification."""
        t = result.complete_type

        mapping = {
            "spherical": {
                "categories": [
                    "Spherical panoramas",
                    "360° panoramas",
                    "360° panoramic photographs"
                ],
                "templates": ["{{Pano360|cat=[[Category:Spherical panoramas]]}}"]
            },
            "cylindrical": {
                "categories": [
                    "360° panoramas",
                    "360° panoramic photographs"
                ],
                "templates": ["{{Pano360}}"]
            },
            "polar_little_planet": {
                "categories": [
                    "Polar coordinates panoramic photographs",
                    "Spherical panoramas"
                ],
                "templates": []
            },
            "cubemap_face": {
                "categories": [
                    "Cubemap representation of 360° panorama",
                    "Spherical panoramas"
                ],
                "templates": []
            },
            "partial_panorama": {
                "categories": ["Panoramic photographs"],
                "templates": ["{{Panorama|1=|4=}}"]
            },
            "likely_not_panorama": {
                "categories": [],
                "templates": []
            },
        }

        info = mapping.get(t, {"categories": [], "templates": []})
        result.suggested_categories = info["categories"]
        result.suggested_templates = info["templates"]

        # Add projection-specific category
        if t == "spherical" and result.projection == "equirectangular":
            result.suggested_categories.append(
                "360° panoramas with equirectangular projection"
            )

        # Add camera category
        if result.camera_model:
            cam_cat = self._lookup_camera_category(result.camera_model)
            if cam_cat:
                result.suggested_categories.append(cam_cat)


def main():
    parser = argparse.ArgumentParser(
        description="Classify a photo by panorama type for Wikimedia Commons"
    )
    parser.add_argument("image", help="Path to image file")
    parser.add_argument("--json", action="store_true",
                        help="Output machine-readable JSON")
    parser.add_argument("--wikitext", action="store_true",
                        help="Output Commons wikitext block")
    parser.add_argument("--full", action="store_true",
                        help="Show all layer results for debugging")
    parser.add_argument("--ml", action="store_true",
                        help="Use ML vision model (slower)")
    args = parser.parse_args()

    classifier = PanoramaClassifier(args.image)
    result = classifier.classify(use_ml=args.ml)

    if args.json:
        import dataclasses
        print(json.dumps(dataclasses.asdict(result), indent=2))
    elif args.wikitext:
        print(generate_commons_wikitext(result))
    else:
        print(f"Classification: {result.complete_type}")
        print(f"Projection:     {result.projection}")
        print(f"Confidence:     {result.confidence:.2f}")
        print(f"Source:         {result.source}")
        print(f"Categories:     {', '.join(result.suggested_categories)}")
        print(f"Templates:      {', '.join(result.suggested_templates)}")
        if result.warnings:
            print(f"Warnings:       {', '.join(result.warnings)}")

        if args.full:
            print(f"\n--- Layer Results ---")
            for layer_name, layer_result in result.layer_results.items():
                print(f"\n{layer_name}:")
                for k, v in layer_result.items():
                    if isinstance(v, float):
                        print(f"  {k}: {v:.4f}")
                    else:
                        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
```

---

## 10. Dependencies

```
# Core (required)
Pillow>=10.0           # Image loading, basic EXIF
numpy>=1.24            # Array operations
opencv-python>=4.8     # Pixel analysis, gradient computation

# Metadata (pick one or both)
pyexiv2>=0.10          # Full EXIF/XMP extraction (preferred, handles GPano cleanly)
exiftool (system)      # Alternative via subprocess

# ML (optional)
open-clip-torch>=2.20  # CLIP vision model for last-resort classification
torch>=2.0             # Required by open-clip

# Development
pytest>=7.0            # Testing
pre-commit>=3.0        # Linting
```

---

## 11. Testing Strategy

### Unit Tests Per Layer

```python
# test_layer1_metadata.py
def test_gpano_full_sphere():
    """A Ricoh Theta image with GPano FullPanoWidth=8000, FullPanoHeight=4000
    should classify as spherical with 0.99+ confidence."""
    ...

def test_gpano_ring_panorama():
    """An image with cropped height (FullPanoHeightPixels=4000,
    CroppedAreaImageHeightPixels=2000) should classify as cylindrical."""
    ...

# test_layer3_pixel.py
def test_edge_continuity_360():
    """Equirectangular image with matching left/right edges should
    return is_360=True."""
    ...

def test_polar_detection():
    """Little planet image with dark corners should return is_polar=True."""
    ...
```

### Integration Tests

Use a curated test set of known images:
- `spherical_equirectangular_theta.jpg` — Ricoh Theta, full sphere, 2:1
- `cylindrical_ring_pano.jpg` — Stitched DSLR, 360°×~65°, 5:1
- `little_planet.jpg` — Polar projection, 1:1, dark corners
- `cubemap_front.jpg` — Single cube face, 1:1
- `normal_landscape.jpg` — Regular 3:2 photo, not a panorama
- `partial_180_pano.jpg` — 180° stitch, 4:1
- `photo_sphere_google.jpg` — Google Photo Sphere, GPano tags present
- `no_metadata_equirect.jpg` — Equirectangular 2:1 but EXIF stripped

---

## 12. Limitations & Edge Cases

| Scenario | Problem | Mitigation |
|----------|---------|------------|
| AI-generated 360° "photos" | No EXIF, may fool visual heuristics | EXIF `Software` tag often reveals "Midjourney" etc. GPano will be absent. Flag as "possible AI-generated" |
| Equirectangular of an indoor white room | Edge continuity gives false positive (white walls match) | Combine with aspect ratio + absence of GPano → lower confidence |
| Ultrawide monitor screenshot of a panorama viewer | Looks like equirectangular but isn't a photo | Detection of UI chrome, uniform resolution. Could add "screenshot" detection |
| 360° video frame extraction | Single frame of equirectangular video, may lack GPano | EXIF may show video software. File size often smaller. 2:1 AR but unusual content |
| Nadir patched with logo | Zenith/nadir detector may miss nadir (it's an image, not black) | Still correctly classified as spherical because pixels are present |
| Non-standard equirectangular ratios | Some tools produce 1.99:1 or 2.01:1 | Use tolerance bands (±2%) |
| TIF/PSD files | Large, layered, may not have JPEG-style EXIF/XMP | Handle TIFF tags separately; Photoshop metadata in ImageResourceBlocks |
