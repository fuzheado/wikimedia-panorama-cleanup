# Panorama Photo Classification Guide for Wikimedia Commons

> **Draft for: Commons:Panorama_photo_guidelines**  
> **Date: 2026-06-26**

## Quick Decision Tree

When uploading a panoramic or 360° photo to Commons, follow this tree to find the right categories:

### Step 1: Is it a panorama?

Your image is probably a **panorama** if:
- It covers a field of view wider than ~160° (roughly what the human eye sees), **OR**
- Its aspect ratio is 2:1 or wider (at least twice as wide as tall), **OR**
- It was captured with a 360° camera or stitched from multiple images using panorama software

→ **Start with: `Category:Panoramic_photographs`**

### Step 2: How much does it cover?

| Coverage | Category | Description |
|----------|----------|-------------|
| Less than 360° horizontally | `Panoramic_photographs` + angle subcat | Partial panorama. Add `180°_panoramas` or `270°_panoramas` if known |
| Full 360° horizontally, but NOT full sky/ground | `360°_panoramas` | "Cylindrical" / "ring" panorama. You can look all around but not straight up or down. |
| Full 360° horizontally AND full sky+ground (zenith+nadir) | `Spherical_panoramas` | "Full sphere" / "photosphere." Nothing missing. |

### Step 3: If spherical (360°×180°), what projection?

| What the file looks like | Additional Category |
|--------------------------|---------------------|
| Single image, exactly 2× wider than tall (e.g., 8000×4000) | `360°_panoramas_with_equirectangular_projection` |
| Six separate square images (front, back, left, right, up, down) | `Cubemap_representation_of_360°_panorama` |
| Circular "little planet" or "tiny planet" effect | `Polar_coordinates_panoramic_photographs` |

### Step 4: What camera or app?

| Camera / App | Category |
|-------------|----------|
| Google Photo Sphere (Android app) | `Photo_Sphere` |
| Ricoh Theta | `Taken with Ricoh Theta series` |
| Insta360 | `Taken with Insta360` |
| Samsung Gear 360 | `Taken with Samsung Gear 360` |
| Nikon KeyMission 360 | `Taken with Nikon KeyMission 360` |
| Stitched from multiple DSLR/mirrorless shots | `Stitched_panoramic_photographs` |

### Step 5: Add template(s)

```
{{Pano360}}                              ← adds interactive viewer link. Uses default category.
{{Pano360|cat=[[Category:Spherical_panoramas]]}}  ← override to spherical category
{{Panorama|1=View of X from Y|4=equirectangular}} ← metadata: description + projection type
```

---

## Visual Examples

### ❌ NOT Spherical (just 360° ring)
```
┌────────────────────────────────────────────────┐
│  ← ← ← ← 360° horizontal panorama → → → →     │  ← sky missing /
│  [  scene fills the entire width  ]            │     no zenith
│  ← ← ← ← 360° horizontal panorama → → → →     │
└────────────────────────────────────────────────┘  ← ground missing /
  Category: 360°_panoramas                           no nadir
```

### ✅ Spherical (360°×180°)
```
┌────────────────────────────────────────────────┐
│  [zenith - straight up]                         │  ← sky present
│  [                                            ] │
│  [  full 360° horizontal + full vertical     ] │  ← 2:1 aspect ratio
│  [                                            ] │     (equirectangular)
│  [nadir - straight down]                        │  ← ground present
└────────────────────────────────────────────────┘
  Category: Spherical_panoramas
  + 360°_panoramas_with_equirectangular_projection
```

### ✅ Little Planet (polar projection of a spherical panorama)
```
         ╭──────────╮
        ╱            ╲
       │   circular   │
       │   scene      │     ← Created by remapping
       │   with       │       an equirectangular
       ╲   planet     ╱       spherical photo to
        ╰──────────╯         stereographic projection
  Category: Polar_coordinates_panoramic_photographs
  Category: Spherical_panoramas
```

### ✅ Cube Map
```
  ┌────┐
  │ UP │
 ┌┼────┼───┬────┐
 │LEFT│FRONT│RIGHT│BACK│   ← 6 square faces
 └────┼────┼────┴────┘
      │DOWN│
      └────┘
  Category: Cubemap_representation_of_360°_panorama
  Category: Spherical_panoramas
```

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Uploading a "little planet" and only tagging it `Polar_coordinates` | Also add `Spherical_panoramas` — it IS a spherical panorama, just in polar projection |
| Tagging a horizontal ring panorama as `Spherical_panoramas` | Only true spherical (zenith+nadir) belongs there. Ring panos go in `360°_panoramas` |
| Tagging a standard wide photo (e.g., 16:9 landscape) as a panorama | Panoramas must show unusually wide field of view. A normal wide-angle shot is not a panorama |
| Confusing `Photosphere` (the Sun) with `Photo_Sphere` (360° photography) | These are completely different things! |
| Using `Photo_Sphere` for any 360° photo regardless of camera | `Photo_Sphere` is specifically for images captured with Google's Photo Sphere app. Others go in `Spherical_panoramas` or camera-specific categories |

---

## Help — I'm Still Not Sure!

**Check your file's metadata:** Many 360° cameras embed GPano XMP metadata. Look for:
- `ProjectionType: equirectangular` → it's likely spherical if dimensions are 2:1
- `FullPanoWidthPixels` and `FullPanoHeightPixels` → if height = width/2, it's full sphere

**When in doubt, ask at:**
- [Commons:Village pump](https://commons.wikimedia.org/wiki/Commons:Village_pump)
- [Commons talk:Categories for discussion](https://commons.wikimedia.org/wiki/Commons_talk:Categories_for_discussion)
