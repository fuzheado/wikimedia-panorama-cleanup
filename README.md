# Making Sense of 360° Photos on Wikimedia Commons

**A research repo about immersive photography, the confusing vocabulary
that surrounds it, and how to clean up the mess.**

---

## Why this exists

People want to share immersive photos — the kind where you can look all
around a scene, not just at a flat rectangle.  Over the past two decades,
the technology to capture these has exploded: dedicated 360° cameras,
smartphone apps, multi-shot DSLR rigs, computer-generated renders.  Each
camera and technique produces files that look different, use different
projections, and need different software to view.

The vocabulary didn't keep up.  Is it a *panorama*, a *photo sphere*, a
*spherical photo*, a *360° photo*, a *VR photo*, a *little planet*?  These
terms are sometimes synonyms, sometimes slightly different things, and
sometimes completely unrelated (one of them means the surface of the Sun).

Wikimedia Commons — the media repository behind Wikipedia — has accumulated
over a million of these photos across a tangle of categories with
overlapping names, unclear boundaries, and a hierarchy that puts things in
the wrong places.  A juror trying to judge these in a photo contest can't
even view them properly.  A contributor uploading one has no guide for what
to call it or where to put it.

**This repo tries to make sense of what exists and propose remedies.**

---

## The 30-second version of the problem

| You have… | Commons calls it… | But it might also be called… |
|-----------|-------------------|------------------------------|
| A single 2:1 image from a Ricoh Theta | Spherical panorama | 360° photo, equirectangular, photosphere |
| A flat wide strip stitched from 4 DSLR shots | Panoramic photograph | 360° panorama (but it's only 90° tall!) |
| A circular "tiny planet" image | Polar coordinates panoramic photograph | Little planet, stereographic projection |
| Six square images (front, back, left, right, up, down) | Cubemap representation of 360° panorama | Cube map faces, QTVR |
| A Google Photo Sphere from an Android phone | Photo Sphere | Photosphere (wait, that's the Sun?!) |

The categories overlap, the hierarchy is backwards, some categories are
empty, one has a million files, and nobody wrote down the rules.

---

## What's in this repo

### [`commons-panorama-taxonomy-analysis.md`](commons-panorama-taxonomy-analysis.md)
**The deep dive.**  A complete analysis of every relevant Commons category:
`Photo_Sphere`, `Spherical_panoramas`, `360°_panoramic_photographs`,
`Polar_coordinates_panoramic_photographs`,
`360°_panoramas_with_equirectangular_projection`, and a dozen more.

Covers:
- The full category hierarchy (mapped from the Commons API)
- File counts and cross-categorization patterns
- Eight specific problems identified (inverted hierarchy, name collisions,
  empty categories, the 1M-file monster category)
- Short-term fixes (redirects, hatnotes, template changes)
- A long-term restructuring proposal
- A contributor decision tree for classifying new uploads

**Read this if you want to understand exactly what's wrong on Commons today.**

### [`panorama-classification-guide.md`](panorama-classification-guide.md)
**The field guide.**  A practical, visual decision tree for anyone uploading
a panoramic or 360° photo to Commons.  Walks through: is it even a
panorama?  How much does it cover?  What projection?  What camera?
Includes visual examples, common mistakes, and a quick-reference table.

**Read this if you're uploading a 360° photo and don't know which categories
to use.**  It's written to become a `Commons:Panorama_photo_guidelines` page.

### [`panorama-classifier-design.md`](panorama-classifier-design.md)
**The automation plan.**  A design for a Python CLI tool that takes a single
image file and determines what type of panorama it is — by reading the
camera's embedded metadata (GPano XMP), checking aspect ratio, and if
necessary, analyzing the actual pixels with OpenCV.  Outputs suggested
Commons categories, templates, and wikitext.

Covers:
- A four-layer detection pipeline (cheap → expensive)
- GPano XMP parsing (the gold standard — most 360° cameras embed this)
- Pixel analysis techniques: edge continuity for 360° wrap detection,
  zenith/nadir presence for spherical-vs-cylindrical, circular corner
  detection for little planets, distortion patterns
- An optional CLIP vision model for last-resort cases
- A fusion strategy that combines all signals
- Full code skeleton and dependency list

**Read this if you want to build a tool that classifies these photos
automatically.**

### [`montage-360-support-advice.md`](montage-360-support-advice.md)
**The jury tool fix.**  Montage is the jury tool used by Wiki Loves
Monuments and other Wikimedia photo contests.  It currently shows 360°
photos as flat, distorted images that jurors can't evaluate.  This
document proposes a three-phase fix:

1. **Phase 1** (~1 hour): Add a "View in 360°" button that opens the
   interactive viewer
2. **Phase 2** (~1-2 days): Embed the Pannellum WebGL viewer inline so
   jurors stay in the voting flow
3. **Phase 3** (~3-5 days): Backend GPano metadata detection for
   authoritative classification

Includes concrete code changes for `CommonsImage.vue`, `VoteYesNo.vue`,
and the Python backend.

**Read this if you work on Montage, or any tool that needs to display 360°
photos properly.**

---

## Key concepts (if you're new to this)

### The two independent dimensions

Panorama photos vary along two axes that Commons currently conflates:

**Completeness** — how much of the scene is captured?
- *Partial* (< 360° horizontal) — a wide landscape stitch
- *Cylindrical* / *ring* (360° horizontal, < 180° vertical) — you can look
  all the way around, but the sky and ground are missing
- *Full spherical* (360° × 180°) — ceiling to floor, nothing missing

**Projection** — how is the sphere flattened into a file?
- *Equirectangular* — a 2:1 image, the standard format.  Looks like a
  squashed world map.
- *Cube map* — six square images (front, back, left, right, up, down)
- *Polar / stereographic* — a circular "little planet" image
- *Cylindrical* — a wide strip, no wrapping at top/bottom

A full spherical panorama can be stored in equirectangular, cubemap, *or*
polar projection.  These dimensions are independent — but Commons nests
them inside each other as if they weren't.

### GPano XMP metadata

Most 360° cameras embed a standardized chunk of metadata called GPano XMP.
It answers the important questions directly:

```
UsePanoramaViewer: True           ← yes, this is a panorama
ProjectionType: equirectangular   ← stored as 2:1
FullPanoWidthPixels: 8000         ← the full 360° is 8000px wide
FullPanoHeightPixels: 4000        ← the full 180° is 4000px tall
CroppedAreaImageHeightPixels: 4000 ← nothing cropped off → full sphere
```

If `CroppedAreaImageHeightPixels` is less than `FullPanoHeightPixels`, the
sky or ground was cropped out — it's a ring panorama, not a full sphere.
This single detail is the most reliable signal for automated classification.

---

## Quickstart: Panorama Classifier CLI Tool

This repo includes `panorama-classifier`, a Python CLI tool that
analyzes an image and tells you what type of panorama it is — and
what Commons categories and templates it needs.

### Prerequisites

**Python 3.9+** is all you strictly need.  The classifier uses a pure-Python
JPEG parser as a fallback when `exiftool` isn't available.

**For best results** (and to handle edge cases like non-standard XMP
placement, TIFF files, and PNG metadata), install `exiftool` — a single
portable binary available on all platforms:

```bash
# macOS:
brew install exiftool

# Debian/Ubuntu:
sudo apt install libimage-exiftool-perl

# Windows / portable:
# Download the standalone exiftool.exe from https://exiftool.org/
```

The classifier auto-detects whether exiftool is installed and falls back
to pure Python if it's not.  Everything works either way — exiftool just
handles more edge cases.

### Setup

```bash
# Clone the repo
git clone https://github.com/fuzheado/wikimedia-panorama-cleanup.git
cd wikimedia-panorama-cleanup

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Install the CLI tool itself
pip install -e .
```

### Usage

```bash
# Basic classification — tells you what type of panorama you have
panorama-classifier my_photo.jpg

# Get Commons-ready wikitext (categories + templates)
panorama-classifier --wikitext my_photo.jpg

# Machine-readable JSON output
panorama-classifier --json my_photo.jpg

# Verbose — see what each detection layer found
panorama-classifier --verbose my_photo.jpg

# Skip pixel analysis for faster results
panorama-classifier --no-pixels my_photo.jpg
```

### Example output

```
$ panorama-classifier cathedral_360.jpg

File: cathedral_360.jpg
Classification: Full spherical panorama (360°×180°)
Projection: equirectangular
Confidence: 85%
Detection source: edge+zenith_nadir

──────────────────────────────────────────────────
⚠ Medium confidence (85%) — suggest human review
```

### How it works

The tool runs a four-layer detection pipeline, from cheapest to most
expensive:

| Layer | What it checks | Speed | Reliability |
|-------|---------------|-------|------------|
| 1. GPano XMP metadata | Embedded 360° camera tags (exiftool, or pure Python fallback) | Instant | ★★★★★ Gold standard |
| 2. Heuristics | Aspect ratio, camera model DB, filename patterns | Instant | ★★★★☆ Strong signal |
| 3. Pixel analysis | OpenCV: edge continuity, zenith/nadir, distortion, seams | 1–3 sec | ★★★☆☆ Confirms heuristics |
| 4. ML vision model | CLIP zero-shot classification (optional) | 5–15 sec | ★★★☆☆ Edge cases only |

When GPano metadata is present (Ricoh Theta, Insta360, Samsung Gear 360,
Google Photo Sphere — most modern 360° cameras), classification is near
certain.  For older stitched panoramas without metadata, the tool falls
back to aspect ratio and pixel analysis.

### Optional: ML Vision Model

For edge cases where all other layers are inconclusive, you can add a
CLIP-based zero-shot classifier:

```bash
pip install torch open-clip-torch
panorama-classifier --verbose mystery_photo.jpg
```

This needs ~2 GB of model downloads on first run.  It's entirely
optional — the other three layers handle 90%+ of real-world cases.

---

## Status

This is research and design work — analysis of the problem and concrete
proposals for solutions.  The prototype classifier is functional and
correctly identifies common panorama types.  The next steps are:

1. **On Commons:** Open CfD discussions for the proposed category changes
2. **On Commons:** Create `Commons:Panorama_photo_guidelines` from the
   classification guide
3. **In Montage:** Implement Phase 1 360° support
4. **Classifier tool:** Add GPano parsing directly from JPEG XMP (removing
   exiftool dependency), improve pixel analysis thresholds with more test data,
   add batch mode for processing multiple files

Contributions, corrections, and additional data points welcome.

---

## License

This research and documentation is released under
[CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/).
Do whatever you want with it — use it in Commons guideline pages, adapt
the code, argue about the category names.
