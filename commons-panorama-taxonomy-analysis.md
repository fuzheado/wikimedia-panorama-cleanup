# Wikimedia Commons Panorama Photo Taxonomy: Analysis & Rationalization

> **Date:** 2026-06-26  
> **Scope:** Category structure for 360° photography, spherical panoramas, photospheres, and related projection types on Wikimedia Commons  
> **Status:** Research complete; recommendations proposed

---

## Executive Summary

Wikimedia Commons has accumulated several overlapping and confusingly-named categories for 360° and spherical photographs. The current hierarchy conflates **two independent dimensions** — completeness of the field of view (partial ring → full ring → full sphere) and projection type (equirectangular, cubemap, polar/stereographic) — in ways that mislead contributors and produce inconsistent categorization. Additionally, a name collision exists between `Category:Photosphere` (astronomy — the Sun's visible surface) and `Category:Photo_Sphere` (Google's Android 360° photo format). Over a million files sit in the top-level `Category:360° panoramas` because the `{{Pano360}}` template defaults there. 

This report documents the current state, identifies eight concrete problems, and proposes pragmatic short-term fixes plus a long-term rationalization plan, including a contributor decision tree.

---

## 1. Current Category Landscape

### 1.1 The Full Hierarchy (Actual, from Commons API)

```
Category:Panoramas .................................. 918 total (includes paintings, drawings, etc.)
│
├── Category:Panoramic_photographs .................. 848 total (photographs only)
│   ├── Category:360°_panoramic_photographs ......... 587 files + 8 subcats
│   │   ├── Category:Polar_coordinates_panoramic_photographs ... 204 files
│   │   ├── Category:Taken with Insta360
│   │   ├── Category:Taken with Ricoh Theta series
│   │   ├── Category:Taken with Samsung Gear 360
│   │   ├── Category:Taken with Nikon KeyMission 360
│   │   ├── Category:Taken with NCTECH iSTAR Pulsar
│   │   ├── Category:Photospheres taken by Sdkb
│   │   └── Category:Outdoor HDRIs by ambientCG
│   ├── Category:Panoramic photographs by technology
│   ├── Category:Stitched panoramic photographs
│   └── ... (by-country, by-subject branches)
│
├── Category:360°_panoramas ......................... 1,046,219 total (!!)
│   ├── Category:360°_panoramic_photographs .......... (also a child of Panoramic_photographs)
│   ├── Category:360°_panoramas_with_equirectangular_projection ... 543 files
│   │   └── Category:Spherical_panoramas .............. 10 direct files + 7 subcats
│   │       ├── Category:Photo_Sphere ................. 88 files + 3 subcats
│   │       │   └── Category:Cubemap_representation_of_360°_panorama .. 168 files
│   │       ├── Category:Spherical panoramics by country
│   │       ├── Category:Spherical Panoramas by Martin Kraft
│   │       ├── Category:Spherical panoramas from European Parliament
│   │       ├── Category:Spherical panoramics by Domob
│   │       ├── Category:Spherical Panoramics by Joachim Köhler
│   │       └── Category:Spherical panoramics of unidentified locations
│   ├── Category:Cubemap_representation_of_360°_panorama .. (also child of Photo_Sphere)
│   ├── Category:360-degree_videos
│   ├── Category:360°_panoramas by country / by continent
│   └── ... (Ricoh Theta, Omnioramics, Mars, nightclubs, etc.)
│
├── Category:180°_panoramas .......................... 6 files
├── Category:270°_panoramas .......................... 0 files (empty)
├── Category:90°_panoramas ........................... 0 files (empty)
├── Category:Partial_spherical_panoramas ............. 1 file (!)
├── Category:Fisheye_images
└── ... (painted panoramas, buildings, icons, etc.)
```

### 1.2 Name Collision Categories

| Category | Wikidata | Meaning | Files |
|----------|----------|---------|-------|
| `Category:Photosphere` (one word) | Q6372 | The Sun's visible surface (astronomy) | ~20 |
| `Category:Photo_Sphere` (underscore) | — | Google Android "Photo Sphere" 360° photos | 88 |
| `Category:Android_Photosphere` | — | The Google app/feature itself (discontinued 2023) | 0 files |

### 1.3 "Little Planet" Categories

| Category | Files | Notes |
|----------|-------|-------|
| `Category:Polar_coordinates_panoramic_photographs` | 204 | Main category; well-described; uses stereographic/azimuthal projection |
| `Category:Little_planet` | 0 | **Empty.** Subcategory of nothing in the panorama tree |
| `Category:Tiny_planet` | 0 | **Empty.** Subcategory of nothing in the panorama tree |

### 1.4 Key Templates

| Template | Default Category | Notes |
|----------|-----------------|-------|
| `{{Pano360}}` | `Category:360° panoramas` | Has optional `cat=` param to override to Spherical panoramas |
| `{{PanoViewer}}` | (none, for article embedding) | Links to panoviewer.toolforge.org |
| `{{Panorama}}` | (none) | Metadata: description, frames, software, **projection type** (spherical/cylindrical/rectilinear/mercator) |
| `{{Photo_Sphere}}` | **DOES NOT EXIST** | Page is a redlink |

### 1.5 Actual File Analysis

| Category | Typical aspect ratio | Typical dimensions | Likely content |
|----------|---------------------|-------------------|----------------|
| `Photo_Sphere` | 2:1 | 8704×4352 | Google Photo Sphere equirectangular output |
| `360°_panoramas_with_equirectangular_projection` | 2:1 | 6528×3264, 14142×7071 | Stitched full-sphere equirectangular (Diliff, etc.) |
| `360°_panoramic_photographs` | Mixed | 5:1 strips, 2:1, 0.63:1 | Everything: ring panos, full spheres, mis-categorized strips |
| `Polar_coordinates_panoramic_photographs` | Mixed (0.67:1 to 1:1) | Various | Little planet effect images |
| `Cubemap_representation_of_360°_panorama` | 1:1 | 2200×2200 | Individual cube faces (left, right, up, down, front, back) |
| `Spherical_panoramas` | Mixed (1:1, 2:1) | Various | Full 360°×180° images |

---

## 2. Taxonomy Definitions (Proposed Canonical)

To rationalize the categories, we need clear definitions. Here are the key concepts:

### 2.1 Completeness of Field of View (FoV)

| Term | Horizontal | Vertical | Description |
|------|-----------|----------|-------------|
| **Partial panorama** | <360° | any | Any stitched/cropped wide image; aspect ratio ≥ 2:1 or FoV ≥ 160° |
| **Cylindrical panorama** (full ring) | 360° | <180° | Complete 360° around the horizon, but missing sky zenith and/or ground nadir. Often looks like a "horizontal band." |
| **Full spherical panorama** (photosphere) | 360° | 180° | Complete sphere — zenith (straight up) to nadir (straight down). No missing areas (though nadir may be patched with a logo). |

### 2.2 Projection Types

| Projection | Aspect Ratio | Storage Format | Used By |
|-----------|-------------|----------------|---------|
| **Equirectangular** (plate carrée) | 2:1 exactly | Single JPEG | Pannellum, Google Photo Sphere, Ricoh Theta, most 360° cameras |
| **Cube map** | 1:1 per face (×6), or 3:2 or 4:3 strip | 6 separate JPEGs OR single strip with all faces | QuickTime VR, some game engines, Pannellum (cubemap type) |
| **Polar / Stereographic** ("little planet") | Usually 1:1 | Single JPEG | Artistic effect; remaps equirectangular to azimuthal projection |
| **Cylindrical** | Variable (>2:1) | Single JPEG | Traditional stitched panoramas (horizontal band only) |
| **Rectilinear** | Variable | Single JPEG | "Flat" stitch; no spherical distortion |

### 2.3 Key Insight: Completeness ⊥ Projection

**These two dimensions are orthogonal.** A full spherical panorama can be stored in equirectangular, cubemap, or polar projection. A cylindrical 360° panorama is usually cylindrical or rectilinear projection but could be polar. The current Commons hierarchy incorrectly nests them:

```
360°_panoramas_with_equirectangular_projection
    └── Spherical_panoramas     ← WRONG: spherical is about completeness, not projection
```

The correct relationship would be that `Spherical_panoramas` is a sibling branching on completeness, and `Equirectangular_spherical_panoramas` is a child intersecting both dimensions. Or, as a flat category system, files tagged with BOTH `Spherical_panoramas` AND `Equirectangular_projection`.

---

## 3. Problems Identified

### Problem 1: Inverted Hierarchy
**Severity: High**

`Category:Spherical_panoramas` is a subcategory of `Category:360°_panoramas_with_equirectangular_projection`. This implies all spherical panoramas are equirectangular — which is false. The hierarchy should have them as sibling branches (or `Spherical_panoramas` should be the broader parent, with `Equirectangular_spherical_panoramas` as a child).

**Current:** `360° → 360° equirectangular → Spherical`  
**Should be:** `360° → Spherical` (with `Equirectangular_spherical_panoramas` as optional subcat)

### Problem 2: Name Collision — Photosphere vs Photo Sphere
**Severity: High**

- `Category:Photosphere` = the Sun's visible surface (astronomy, Wikidata Q6372)
- `Category:Photo_Sphere` = Google's 360° photo format

The underscore vs. no-space distinction is invisible in many UIs. The `Photo_Sphere` category page even starts with: *"Not to be confused with Photosphere, Spherical panoramas or Polar coordinates panoramic photographs"*. This is a constant source of miscategorization and confusion.

### Problem 3: Brand Name as Category Name
**Severity: Medium**

"Photo Sphere" is a Google trademark for a specific Android camera feature. Using it as a category for all full-sphere 360° images is like having `Category:iPhone_Photos` for all smartphone photography. It should be restricted to images actually captured with the Google Photo Sphere app, or better yet, renamed to a generic term.

### Problem 4: Massive 360°_panoramas Category
**Severity: Medium**

`Category:360°_panoramas` contains over 1 million files — it's completely unusable for browsing. This is primarily because `{{Pano360}}` defaults `cat=` to this category. The template should be changed to either:
- Not auto-categorize, OR
- Use a more specific category based on file metadata

### Problem 5: Empty / Orphan Categories
**Severity: Low**

- `Category:Little_planet` (0 files) — should redirect to `Polar_coordinates_panoramic_photographs`
- `Category:Tiny_planet` (0 files) — same
- `Category:Partial_spherical_panoramas` (1 file) — orphaned; no one knows to use it
- `Category:270°_panoramas` (0 files) — exists but unused
- `Category:90°_panoramas` (0 files) — exists but unused

### Problem 6: Missing Template for Photo_Sphere Category
**Severity: Low**

`Template:Photo_Sphere` is a redlink (never created), yet `Category:Photo_Sphere` has 88 files. There's no template to help contributors correctly tag these images.

### Problem 7: No Clear Contributor Guidance
**Severity: High**

There is no decision tree, guideline page, or upload wizard help text that tells a contributor:
- Whether their image is a panorama, a spherical panorama, a photo sphere, or a little planet
- What projection type to specify
- Which categories to use
- What template to add

The `Commons:Panoramas` page exists but is minimal. The `Commons:Project to create spherical panoramas of important monuments` page has excellent distinctions (ring vs. spherical vs. polar) but is buried as a project page from 2014–2015.

### Problem 8: Inconsistent Naming Conventions
**Severity: Low**

- "360°" with degree symbol vs. "360" without
- "Panorama" (singular) vs. "Panoramas" (plural) vs. "Panoramics" vs. "Panoramic photographs"
- "Photo Sphere" (space, title case) for Google's feature vs. "photospheres" (lowercase, plural) in `Category:Photospheres_taken_by_Sdkb`

---

## 4. Proposed Solutions

### 4.1 Short-Term (Low Effort, High Impact)

These can be done immediately with minimal disruption:

#### A. Fix `{{Pano360}}` Default Category
**Action:** Change the default `cat=` parameter from `Category:360° panoramas` to auto-detect or use no default.  
**Rationale:** The current default adds every Pano360-tagged file to a 1M+ monster category. At minimum, don't auto-add; require explicit categorization.

#### B. Add Hatnotes and "See Also" Cross-References
**Action:** Ensure EVERY category in the panorama tree has clear hatnotes distinguishing it from confusable siblings:
- `Category:Photo_Sphere` already has one → good
- `Category:Spherical_panoramas` already says "Not to be confused with Photo Sphere" → good
- `Category:Polar_coordinates_panoramic_photographs` says "Not to be confused with Spherical panoramics" → good
- Add to `Category:360°_panoramic_photographs`: "For full spherical images (zenith+nadir), see Spherical panoramas. For equirectangular projection, see 360° panoramas with equirectangular projection."

#### C. Redirect Empty Duplicate Categories
**Action:** Make `Category:Little_planet` and `Category:Tiny_planet` redirect to `Category:Polar_coordinates_panoramic_photographs`.  
**Rationale:** "Little planet" and "tiny planet" are colloquial terms; the existing category is the canonical one.

#### D. Create `Template:Photo_Sphere`
**Action:** Create the missing template to match the category. Should add files to `Category:Photo_Sphere` and include explanatory text about what a photo sphere is.

#### E. Fix the Hierarchy
**Action:** Remove `Category:Spherical_panoramas` as a child of `Category:360°_panoramas_with_equirectangular_projection`. Instead:
- Make `Category:Spherical_panoramas` a direct child of `Category:360°_panoramas`  
- Create `Category:Equirectangular_spherical_panoramas` as a child of BOTH `Category:Spherical_panoramas` AND `Category:360°_panoramas_with_equirectangular_projection`
- Make `Category:Cubemap_representation_of_360°_panorama` a child of `Category:Spherical_panoramas` as well

#### F. Decide the Fate of `Photo_Sphere` Category
Three options:
1. **Keep as is** but with strict scope: only images taken with the Google Photo Sphere app. Move others to `Spherical_panoramas`.
2. **Rename** to something generic like `Category:Photospheres` or `Category:Full-sphere_360°_photographs` and absorb the contents.
3. **Make it a subcategory** of `Spherical_panoramas` but rename to `Category:Taken_with_Google_Photo_Sphere` (camera-specific, like the Ricoh Theta category).

**Recommendation:** Option 3 — treat it like `Category:Taken with Ricoh Theta series`. "Photo Sphere" is a camera/app feature, not a type of photograph. A broader generic term should house full-sphere images regardless of capture method.

### 4.2 Long-Term (Requires Discussion / CfD)

#### A. Comprehensive Category Restructuring

Proposed target hierarchy:

```
Category:Panoramas
├── Category:Panoramic_photographs
│   ├── Category:360°_panoramic_photographs ........ [ALL 360° horizontal photos]
│   │   ├── Category:Spherical_panoramas ............ [360°×180°; zenith+nadir]
│   │   │   ├── Category:Equirectangular_spherical_panoramas
│   │   │   ├── Category:Cubemap_spherical_panoramas
│   │   │   └── Category:Polar_coordinates_panoramic_photographs [little planet]
│   │   ├── Category:Cylindrical_360°_panoramas ..... [360° horizontal, <180° vertical]
│   │   └── Category:360°_panoramic_photographs_from_specific_cameras
│   │       ├── Category:Taken with Google Photo Sphere [renamed from Photo_Sphere]
│   │       ├── Category:Taken with Ricoh Theta series
│   │       ├── Category:Taken with Insta360
│   │       ├── Category:Taken with Samsung Gear 360
│   │       └── ...
│   ├── Category:180°_panoramas
│   ├── Category:270°_panoramas
│   ├── Category:90°_panoramas
│   └── ...
├── Category:360°_panoramas ......................... [metadata-only, not for direct file use?]
│   └── ... (by-country branches for browsing)
└── ...
```

#### B. Deprecate `Category:Photo_Sphere` in Favor of `Spherical_panoramas`

Open a CfD to either:
- **Merge** `Category:Photo_Sphere` into `Category:Spherical_panoramas` (since they're functionally the same — full-sphere images), OR
- **Restrict** `Category:Photo_Sphere` to images specifically captured with the Google Photo Sphere app (like other `Taken with X` categories)

#### C. Create `Commons:Panorama_photo_guidelines`

A clear guideline page with:
- Definitions of key terms (cylindrical, spherical, equirectangular, cubemap, polar/little-planet)
- A visual decision tree (see §5 below)
- Template usage guide
- Category selection guide
- Examples of correct/incorrect categorization

#### D. Structured Data on Commons (SDC) Integration

The Wikidata properties `P4291` (panoramic view), `P4640` (spherical panorama image), and `P5282` (ground level 360 degree view URL) should be promoted in upload workflows and templates. SDC could eventually automate some categorization.

#### E. Address the Photosphere/Photo_Sphere Name Collision

- `Category:Photosphere` (astronomy) → add explicit disambiguation hatnote  
- `Category:Photo_Sphere` (photography) → if kept, rename to something less collision-prone like `Category:Google_Photo_Sphere_photographs`

---

## 5. Contributor Decision Tree

Here's a practical decision tree for contributors uploading a wide-angle or 360° photo:

```
START: You have a wide-angle or stitched photo to upload to Commons.

Q1: Is it a PHOTOGRAPH?
├── YES → Category:Panoramic_photographs
└── NO (painting, illustration, render) → Category:Panoramas (or appropriate subcat)

Q2: What is the ASPECT RATIO? Is the image at least 2× wider than tall,
    OR does it cover more than ~160° field of view?
├── NO → This may not be a panorama. Use normal photo categories.
└── YES → It's a panoramic photograph. Continue.

Q3: Does it cover a FULL 360° HORIZONTALLY?
├── NO → It's a PARTIAL PANORAMA.
│   └── What angle does it cover?
│       ├── ~90° → Category:90°_panoramas
│       ├── ~180° → Category:180°_panoramas
│       ├── ~270° → Category:270°_panoramas
│       └── Other → Category:Panoramic_photographs (or by-location cats)
│
└── YES → It's a 360° PANORAMA. Continue.
    │
    Q4: Does it include the ZENITH (straight up) AND NADIR (straight down)?
    ├── NO → It's a CYLINDRICAL 360° PANORAMA (horizontal ring).
    │   │    Category:360°_panoramas (the main 360° category is fine for ring panos)
    │   └── Also consider: Category:360°_panoramic_photographs
    │
    └── YES → It's a FULL SPHERICAL PANORAMA (photosphere).
        │    Category:Spherical_panoramas
        │
        Q5: What PROJECTION / FILE FORMAT is it stored in?
        ├── Single 2:1 image (width = 2× height)
        │   → ADD: Category:360°_panoramas_with_equirectangular_projection
        │
        ├── Six separate 1:1 images (front, back, left, right, up, down)
        │   → ADD: Category:Cubemap_representation_of_360°_panorama
        │
        └── Circular "little planet" look (1:1, stereographic projection)
            → ADD: Category:Polar_coordinates_panoramic_photographs

Q6: What CAMERA / SOFTWARE was used?
├── Google Photo Sphere app → Category:Photo_Sphere (+ above cats)
├── Ricoh Theta → Category:Taken with Ricoh Theta series
├── Insta360 → Category:Taken with Insta360
├── Samsung Gear 360 → Category:Taken with Samsung Gear 360
├── Nikon KeyMission 360 → Category:Taken with Nikon KeyMission 360
├── Stitched from multiple DSLR shots → Category:Stitched_panoramic_photographs
└── Other / Unknown → no camera-specific cat needed

Q7: ADD TEMPLATES:
├── For ANY 360° photo → {{Pano360}} with appropriate cat= parameter
│   └── For spherical → {{Pano360|cat=[[Category:Spherical_panoramas]]}}
├── For metadata → {{Panorama|1=description|4=projection_type}}
└── For linking to interactive viewer → {{PanoViewer|filename.jpg|caption}}
```

### Visual Summary Table

| What you have | Aspect Ratio | Horizontal | Vertical | Primary Category | Additional Category |
|---|---|---|---|---|---|
| Narrow wide shot | >2:1 | <180° | normal | `Panoramic_photographs` | — |
| Wide landscape stitch | >3:1 | ~160°-270° | normal | `Panoramic_photographs` | `180°_panoramas` or `270°_panoramas` |
| Full 360° ring, no sky/ground | >3:1 | 360° | <100° | `360°_panoramas` | `360°_panoramic_photographs` |
| Full 360° sphere, 2:1 image | 2:1 | 360° | 180° | `Spherical_panoramas` | `360°_panoramas_with_equirectangular_projection` |
| Full sphere, 6 cube face files | 1:1 (×6) | 360° | 180° | `Spherical_panoramas` | `Cubemap_representation_of_360°_panorama` |
| Little planet effect (circular) | 1:1 | 360° | 180° | `Polar_coordinates_panoramic_photographs` | `Spherical_panoramas` |
| Google Photo Sphere app, 2:1 | 2:1 | 360° | 180° | `Spherical_panoramas` | `Photo_Sphere` + `360°_panoramas_with_equirectangular_projection` |

---

## 6. Discussion History

### 6.1 CfD: Category:Spherical panoramas (2025-04)
**Participants:** Sdkb, Domob  
**Status:** Open / unresolved  

Sdkb argued that `Spherical_panoramas` appears identical to `360°_panoramic_photographs` and should either be clearly distinguished or merged. Domob replied that the distinction is zenith+nadir inclusion (spherical = full sphere; 360° panorama may be just a horizontal band). Sdkb noted that recategorization and modification of `{{Pano360}}` is due.

**Impact on proposals:** This CfD confirms exactly the confusion this report addresses. The resolution should make the "spherical = zenith+nadir" definition explicit and enforceable.

### 6.2 CfD: Category:Panoramic photographs (2019-10)
**Participants:** Themightyquill, Auntof6, XRay, Banaticus  
**Status:** Closed — `Stitched_panoramic_photographs` created as intersection category  

Key takeaway: Not all panoramas are stitched, and not all stitched images are panoramas. This was correctly resolved.

---

## 7. Recommended Next Steps (Prioritized)

### Immediate (no CfD needed):
1. **Create `Commons:Panorama_photo_guidelines`** with the decision tree from §5
2. **Redirect `Little_planet` and `Tiny_planet`** to `Polar_coordinates_panoramic_photographs`
3. **Create `Template:Photo_Sphere`** (currently a redlink)
4. **Add hatnotes** to all panorama categories cross-referencing confusable siblings
5. **File a Phabricator task** to change `{{Pano360}}` default category behavior

### Requires CfD (short-term):
6. **Restructure the hierarchy** (§4.2 A) — make `Spherical_panoramas` a child of `360°_panoramas`, not of `360°_panoramas_with_equirectangular_projection`
7. **Decide fate of `Category:Photo_Sphere`** — restrict to Google app, or merge into `Spherical_panoramas`
8. **Rename** or better-disambiguate to prevent "Photosphere"/"Photo Sphere" confusion
9. **Delete or merge** unused angle categories (`90°`, `270°`) if no one adopts them

### Long-term:
10. **SDC integration** — use Wikidata properties for projection type and completeness
11. **Upload Wizard integration** — guide contributors through the decision tree during upload
12. **Bot-assisted recategorization** — using aspect ratio + GPano XMP metadata to detect projection types automatically

---

## 8. Appendix: GPano XMP Metadata

Images captured with Google Photo Sphere, Ricoh Theta, Samsung Gear 360, and similar cameras contain XMP metadata under the `GPano` namespace that could be used for automated categorization:

| GPano Tag | Meaning |
|-----------|---------|
| `GPano:UsePanoramaViewer` | True if the image is a panorama |
| `GPano:ProjectionType` | `equirectangular` (most common) |
| `GPano:FullPanoWidthPixels` | Width of the full panorama |
| `GPano:FullPanoHeightPixels` | Height of the full panorama |
| `GPano:CroppedAreaImageWidthPixels` | Width of the cropped area |
| `GPano:CroppedAreaImageHeightPixels` | Height of the cropped area |
| `GPano:PoseHeadingDegrees` | Compass heading |
| `GPano:FirstPhotoDate` | When the first frame was shot |
| `GPano:LastPhotoDate` | When the last frame was shot |

A bot could read `FullPanoHeightPixels / FullPanoWidthPixels` to determine if the image is full-sphere (ratio = 0.5 = 180°/360°) or a partial ring, and auto-suggest categories.

---

## 9. Appendix: Related Wikipedia Articles

- [VR photography](https://en.wikipedia.org/wiki/VR_photography) — Good overview; covers "photo sphere" and "spherical panorama" as synonyms
- [Equirectangular projection](https://en.wikipedia.org/wiki/Equirectangular_projection) — The standard storage format for 360° photos
- [Spherical panorama](https://en.wikipedia.org/wiki/Spherical_panorama) — Wikipedia article; map projection concept
- [Photosphere](https://en.wikipedia.org/wiki/Photosphere) — Astronomy article (not photography)
- [Image stitching](https://en.wikipedia.org/wiki/Image_stitching) — How panoramas are made
- [Stereographic projection § Photography](https://en.wikipedia.org/wiki/Stereographic_projection#Photography) — The "little planet" effect

---

*Report prepared by Pi coding agent for Commons category rationalization. All data verified against the Commons API on 2026-06-26.*
