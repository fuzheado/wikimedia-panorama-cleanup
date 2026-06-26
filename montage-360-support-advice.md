# Montage 360° Panorama Support: Implementation Advice

> **GitHub Issue:** [hatnote/montage#154](https://github.com/hatnote/montage/issues/154)  
> **Related Phabricator:** [T151749 — 360 Photo support](https://phabricator.wikimedia.org/T151749)  
> **Date:** 2026-06-26  
> **Context:** Panorama taxonomy research for Wikimedia Commons

---

## Problem

Montage renders all campaign images as flat `<img>` tags via `CommonsImage.vue`. For 360° equirectangular photos (2:1 aspect ratio), this shows jurors a wildly distorted image — the top and bottom are stretched beyond recognition, and the 360° wrap is invisible. A Wiki Loves Monuments juror evaluating a 360° interior of a cathedral sees an unreadable smear instead of the full-surround view the photographer captured.

**Example:** [Basilique Saint-Patrick 360°](https://commons.wikimedia.org/wiki/File:Panorama_360_of_Basilique_Saint-Patrick,_Montreal,_Quebec,_Canada.jpg) — as a flat image it's incomprehensible. As an [interactive panorama](https://panoviewer.toolforge.org/#Panorama_360_of_Basilique_Saint-Patrick,_Montreal,_Quebec,_Canada.jpg) it shows the complete church interior.

## Current Architecture

| File | Role |
|------|------|
| `frontend/src/components/CommonsImage.vue` | Universal image renderer — all images rendered as `<img>` |
| `frontend/src/components/Vote/VoteYesNo.vue` | Yes/No voting view — uses `CommonsImage` |
| `frontend/src/components/Vote/VoteRating.vue` | 1-5 star rating view — uses `CommonsImage` |
| `frontend/src/components/Vote/VoteRanking.vue` | Ranking view — uses `CommonsImage` |
| `frontend/src/components/Vote/ImageReviewDialog.vue` | Individual image review dialog — uses `CommonsImage` |
| `frontend/src/utils.js` | `getCommonsImageUrl()` — constructs thumbnail URLs |
| `montage/loaders.py` | Backend entry loading — already includes `img_width` and `img_height` in entry data |
| `frontend/src/services/jurorService.js` | API client for fetching round tasks |

**Key fact:** The frontend already receives image dimensions (`entry.width`, `entry.height`) from the backend. No backend changes are needed for aspect-ratio-based detection.

---

## Recommended Approach: Three Phases

### Phase 1 — Quick Win: "View in 360°" Link (~ 1 hour)

Add a button that opens the image in the `panoviewer.toolforge.org` interactive viewer in a new tab. This gives jurors a way to actually see 360° photos today, with minimal code change.

#### Detection Logic

```javascript
// Add to VoteYesNo.vue, VoteRating.vue, VoteRanking.vue
const isEquirectangular360 = computed(() => {
  const w = rating.value.current?.entry?.width
  const h = rating.value.current?.entry?.height
  if (!w || !h) return false
  // Equirectangular full-sphere photos have exactly 2:1 aspect ratio
  // ±2% tolerance for non-standard sizes (e.g., cropped, slightly off)
  const ratio = w / h
  return Math.abs(ratio - 2.0) < 0.02 && w >= 2000
})
```

#### Button Placement

In each vote component's sidebar, add a third link alongside the existing "Show full-size" and "Commons page" links:

```html
<div class="vote-file-links">
  <a :href="getCommonsImageUrl(rating.current, null)" target="_blank">
    <cdx-button weight="quiet">
      <image-icon class="icon-small" /> {{ $t('montage-vote-show-full-size') }}
    </cdx-button>
  </a>
  <a :href="'https://commons.wikimedia.org/wiki/File:' + rating.current.entry.name" target="_blank">
    <cdx-button weight="quiet" class="vote-commons-button">
      <link-icon class="icon-small" /> {{ $t('montage-vote-commons-page') }}
    </cdx-button>
  </a>
  <!-- NEW: 360° viewer link, only shown for detected equirectangular photos -->
  <a
    v-if="isEquirectangular360"
    :href="'https://panoviewer.toolforge.org/#' + rating.current.entry.name"
    target="_blank"
  >
    <cdx-button weight="quiet">
      <panorama-variant class="icon-small" />
      {{ $t('montage-vote-view-360') }}
    </cdx-button>
  </a>
</div>
```

#### i18n String

Add to `frontend/src/i18n/en.json`:

```json
"montage-vote-view-360": "View in 360°"
```

#### Pros & Cons

| ✅ Pros | ❌ Cons |
|---------|---------|
| Trivial — ~30 lines of code, pure frontend | Context switch — juror leaves voting flow |
| Works immediately, no backend changes | Doesn't handle cubemap or polar projections |
| Uses existing panoviewer infrastructure | False positives possible (non-panorama 2:1 images) |
| No new dependencies | `panoviewer.toolforge.org` is on deprecated GridEngine (T319953) |

---

### Phase 2 — Inline Pannellum Viewer (~ 1-2 days)

Replace the flat `<img>` with an embedded [Pannellum](https://pannellum.org/) WebGL viewer for detected 360° images. Jurors stay in the voting interface and can pan/zoom the 360° photo interactively.

#### How Pannellum Works

Pannellum is a lightweight (~21 kB gzipped), open-source WebGL panorama viewer. Its standalone mode (`pannellum.htm`) can load equirectangular images directly via URL hash parameters — no server-side config needed:

```
https://cdn.jsdelivr.net/npm/pannellum@2.5.7/build/pannellum.htm
  #panorama=https://example.com/pano.jpg&autoLoad=true
```

#### Modified `CommonsImage.vue`

```vue
<template>
  <!-- Branch 1: 360° equirectangular → Pannellum iframe -->
  <iframe
    v-if="isPanorama"
    :src="pannellumUrl"
    :width="displayWidth"
    :height="pannellumHeight"
    allowfullscreen
    style="border: none;"
    :class="imageClass"
    @load="$emit('load')"
    @error="$emit('error')"
  />
  <!-- Branch 2: Normal image → existing <img> -->
  <img
    v-else
    :src="currentSrc"
    :alt="alt"
    :class="imageClass"
    @load="handleLoad"
    @error="handleError"
    v-bind="$attrs"
  />
</template>

<script setup>
import { ref, watch, computed } from 'vue'

const props = defineProps({
  image: {
    type: [Object, String],
    required: true
  },
  width: {
    type: Number,
    default: 1280
  },
  isPanorama: {
    type: Boolean,
    default: false
  },
  alt: {
    type: String,
    default: ''
  },
  imageClass: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['load', 'error'])

const imageName = computed(() => {
  return props.image?.entry?.name || props.image?.name || props.image
})

const displayWidth = computed(() => {
  // When used inside vote-image-container, use max-width from CSS
  // When width prop is explicit, use that
  return props.width
})

const pannellumHeight = computed(() => {
  // For 2:1 equirectangular, height = width / 2
  return Math.round(displayWidth.value / 2)
})

const pannellumUrl = computed(() => {
  const name = encodeURIComponent(imageName.value)
  // Use Commons thumbnail at 2048px width for reasonable load time
  const thumbUrl = encodeURIComponent(
    `https://commons.wikimedia.org/w/index.php?title=Special:Redirect/file/${name}&width=2048`
  )
  return 'https://cdn.jsdelivr.net/npm/pannellum@2.5.7/build/pannellum.htm' +
    `#panorama=${thumbUrl}&autoLoad=true&showFullscreenCtrl=true&showZoomCtrl=false`
})

// ... existing img fallback logic (urlStrategies, handleLoad, handleError) ...
</script>
```

#### Usage in Vote Components

```vue
<!-- VoteYesNo.vue / VoteRating.vue -->
<CommonsImage
  :image="rating.current"
  :width="1280"
  :is-panorama="isEquirectangular360"
  :image-class="`vote-image ${imageLoading ? 'vote-image-hide' : ''}`"
  @load="handleImageLoad"
  @error="handleImageLoad"
/>
```

#### CORS Consideration

Pannellum's iframe mode loads the panorama image via the browser's standard image loading, which must be same-origin or CORS-accessible. Commons thumbnail URLs via `Special:Redirect` should work because Commons serves proper CORS headers. **Test this before deploying.** If CORS is an issue, the fallback is:

1. Keep the Phase 1 "View in 360°" button as the universal fallback
2. Use Pannellum only when CORS works (browser-dependent)

#### Keyboard Interaction

The Pannellum iframe doesn't capture keyboard events until the user clicks inside it. So the existing keyboard voting shortcuts (`↑` = accept, `↓` = decline, `→` = skip, `1`-`5` = rating) will continue working as long as the juror hasn't focused the iframe. This is the correct behavior — jurors should be able to vote without removing their hands from the keyboard.

#### Pros & Cons

| ✅ Pros | ❌ Cons |
|---------|---------|
| Immersive — juror stays in voting flow | Requires CORS testing with Commons thumbnails |
| Same keyboard shortcuts still work | Pannellum CDN dependency |
| No server-side processing needed | 2:1 detection still has false positives |
| Pannellum handles mobile touch | Cubemap/polar projections not handled |
| Bypasses deprecated panoviewer infra | Slightly more complex loading state |

---

### Phase 3 — Backend GPano Metadata Detection (~ 3-5 days)

The most accurate approach: query the Commons API for GPano XMP metadata during campaign entry loading, and store an explicit `is_panorama` flag on each entry. This eliminates false positives and handles edge cases.

#### Why GPano Metadata is the Gold Standard

Most 360° cameras (Ricoh Theta, Insta360, Samsung Gear 360, Google Photo Sphere, etc.) embed GPano XMP metadata. Key fields:

| GPano Tag | Meaning |
|-----------|---------|
| `UsePanoramaViewer` | Boolean — is this a panorama? |
| `ProjectionType` | `equirectangular` (the standard format) |
| `FullPanoWidthPixels` | Full stitched width |
| `FullPanoHeightPixels` | Full stitched height |
| `CroppedAreaImageWidthPixels` | Actual image width |
| `CroppedAreaImageHeightPixels` | Actual image height |

**Key insight:** If `FullPanoHeightPixels == CroppedAreaImageHeightPixels`, it's a full sphere (zenith+nadir present). If `CroppedAreaImageHeightPixels` is significantly smaller, it's a cylindrical ring panorama (missing sky/ground).

#### Backend Detection Code

Add to `montage/loaders.py` or a new utility module:

```python
"""
montage/pano_detect.py — Detect 360° equirectangular photos via GPano XMP.
"""
import json
from .utils import requests_get

COMMONS_API = 'https://commons.wikimedia.org/w/api.php'
BATCH_SIZE = 50  # Commons API max titles per query

def detect_panoramas(entries):
    """
    Given a list of Entry objects, query Commons API for GPano metadata
    and set entry.is_panorama = True for 360° equirectangular images.

    Returns modified entries list and a count of detected panoramas.
    """
    filenames = [e.name for e in entries]

    # Batch queries to respect API limits
    panorama_names = set()

    for i in range(0, len(filenames), BATCH_SIZE):
        batch = filenames[i:i + BATCH_SIZE]
        params = {
            'action': 'query',
            'format': 'json',
            'titles': '|'.join([f'File:{f}' for f in batch]),
            'prop': 'imageinfo',
            'iiprop': 'extmetadata',
            'iiextmetadatafilter': 'GPano',
            'iiextmetadatalanguage': 'en',
        }

        url = f"{COMMONS_API}?{_encode_params(params)}"
        headers = {'User-Agent': 'Montage/1.0 (https://montage.toolforge.org; panorama detection)'}

        try:
            resp = requests_get(url, headers=headers)
            data = resp.json()
        except Exception:
            continue  # API failure → skip batch gracefully

        pages = data.get('query', {}).get('pages', {})
        for page_id, page in pages.items():
            title = page.get('title', '').replace('File:', '')
            imageinfo = page.get('imageinfo', [{}])[0]
            extmetadata = imageinfo.get('extmetadata', {})

            gpano = extmetadata.get('GPano', {})
            if not gpano:
                continue

            # GPano value is a JSON string embedded in the extmetadata value
            gpano_value = gpano.get('value', '')
            if not gpano_value:
                continue

            try:
                gpano_data = json.loads(gpano_value)
            except json.JSONDecodeError:
                continue

            # Check: is it a panorama viewer image?
            if gpano_data.get('UsePanoramaViewer') != 'True':
                continue

            # Check: is it equirectangular projection?
            if gpano_data.get('ProjectionType') != 'equirectangular':
                continue

            # It's a 360° equirectangular panorama
            panorama_names.add(title)

    # Tag entries
    count = 0
    for entry in entries:
        if entry.name in panorama_names:
            entry.is_panorama = True
            count += 1

    return entries, count


def _encode_params(params):
    """URL-encode params dict for GET request."""
    from urllib.parse import urlencode
    return urlencode(params)
```

#### Database Schema Change

Add an `is_panorama` column to the entry table (or use the existing `flags` JSON field):

```sql
ALTER TABLE entry ADD COLUMN is_panorama BOOLEAN DEFAULT FALSE;
```

Or, less invasively, add it to the existing `flags` JSON:

```python
# In make_entry() in loaders.py
if edict.get('flags'):
    raw_entry['flags'] = edict['flags']
# Add panorama flag
raw_entry.setdefault('flags', {})['is_panorama'] = False
```

#### Integration Point

Call `detect_panoramas()` after entries are loaded, before they're stored:

```python
# In the campaign creation / round setup flow
entries, warnings = load_name_list(file_obj, source=source)
entries, pano_count = detect_panoramas(entries)
# store entries with is_panorama flag set
```

#### Frontend Usage

```javascript
// In vote components
const isEquirectangular360 = computed(() => {
  // Phase 3: use explicit backend flag if available
  if (rating.value.current?.entry?.flags?.is_panorama) {
    return true
  }
  // Fallback: aspect ratio heuristic (Phase 1/2 logic)
  const w = rating.value.current?.entry?.width
  const h = rating.value.current?.entry?.height
  if (!w || !h) return false
  const ratio = w / h
  return Math.abs(ratio - 2.0) < 0.02 && w >= 2000
})
```

#### Pros & Cons

| ✅ Pros | ❌ Cons |
|---------|---------|
| Authoritative — GPano metadata is definitive | Requires backend changes + DB migration |
| Zero false positives | Adds Commons API call during campaign loading |
| Handles all GPano-equipped cameras | Older stitched photos without GPano fall through to heuristic |
| Enables future features (e.g., filter by panorama) | Slower campaign setup (batch API queries) |
| Distinguishes full-sphere from cylindrical ring | Phase 1/2 detection needed as fallback anyway |

---

## What NOT To Do

- ❌ **Don't try to auto-detect from filename patterns** — `pano_360.jpg`, `DSC_0042.jpg`, and `IMG_2024.jpg` are all valid filenames for both panorama and non-panorama images
- ❌ **Don't transcode or server-side process the images** — Commons already handles thumbnailing efficiently via its thumbnail cache. Point the viewer at the thumbnail URL
- ❌ **Don't use Pannellum's JavaScript API** (`pannellum.viewer()`) instead of the iframe approach — the iframe is sandboxed, avoids JS dependency conflicts with Vue's reactivity system, and is simpler to maintain
- ❌ **Don't require jury coordinators to manually flag 360° images** — it defeats the purpose of automation and coordinators often don't know which images are 360°
- ❌ **Don't attempt to detect cubemap or polar projections in Phase 1 or 2** — they're much rarer in WLM campaigns and require different detection methods. Leave for a future enhancement

---

## Edge Cases & Considerations

| Scenario | Handling |
|----------|----------|
| **Non-panorama 2:1 image** (e.g., astrophotography crop, banner) | Phase 1/2: false positive — "View in 360°" button appears but panoviewer will show a weird result. Juror clicks back. Phase 3: no false positive (GPano absent). |
| **Cubemap representation** (6 separate square images) | Not detected by any phase. These are individually uploaded faces (front.jpg, back.jpg, etc.) with 1:1 aspect ratio. Requires separate detection (filename patterns like `_front`, `_back`, `_left`). |
| **Polar/little-planet projection** (1:1, circular content) | Not detected. Usually has 1:1 aspect ratio. Pannellum doesn't support stereographic projection natively. |
| **360° video** | Not detected (different MIME type). Montage already filters for images only. |
| **Partial cylindrical ring** (360° horizontal, <180° vertical) | GPano: `FullPanoHeightPixels > CroppedAreaImageHeightPixels`. These aren't full spheres and the viewer will show black at top/bottom. Phase 3 should NOT flag these as panoramas for inline viewing (show the "View in 360°" link instead). |
| **AI-generated 360° "photos"** | May or may not have GPano metadata. If they don't, they fall through to manual juror detection (no false positive). |
| **Very large panoramas** (gigapixel) | Commons `Special:Redirect?width=2048` handles this — it serves a pre-cached thumbnail. Pannellum loads the thumbnail, not the full file. |
| **Non-JPEG formats** (PNG, TIFF) | Commons `Special:Redirect/file/` automatically converts TIFF to JPEG for display. Pannellum handles PNG fine but it's slower to load. |
| **Mobile jurors** | Pannellum has WebGL support on mobile browsers. Touch-to-pan works. Fullscreen button available. |
| **Slow connections** | The 2048px Commons thumbnail is typically 1-3 MB. Pannellum shows a loading spinner. Acceptable for jury tools. |
| **`panoviewer.toolforge.org` outage or deprecation** | Phase 1 depends on panoviewer. Phase 2+3 use jsDelivr CDN Pannellum directly — no Toolforge dependency for the viewer itself. |

---

## Implementation Priority & Effort Estimate

| Phase | Effort | Files Changed | Risk | Value |
|-------|--------|---------------|------|-------|
| **Phase 1** | ~1 hour | 3 Vue files + i18n | Very low | High — makes 360° photos evaluable immediately |
| **Phase 2** | ~1-2 days | `CommonsImage.vue` + 3 vote components | Low-Medium (CORS testing) | High — immersive in-flow viewing |
| **Phase 3** | ~3-5 days | Backend + DB + frontend | Medium (API dependency) | Highest — authoritative detection, no false positives |

**Recommended rollout:** Ship Phase 1 immediately (it's trivial and solves the core problem of "jurors can't evaluate 360° photos at all"). Follow with Phase 2 after testing Commons CORS headers. Plan Phase 3 as a future enhancement when there's bandwidth for backend changes.

---

## Related Resources

- [Pannellum 2.5.7 documentation](https://pannellum.org/)
- [Pannellum CDN (jsDelivr)](https://cdn.jsdelivr.net/npm/pannellum@2.5.7/build/pannellum.htm)
- [panoviewer Toolforge tool](https://github.com/toollabs/panoviewer) — the existing Commons 360° viewer (on deprecated GridEngine)
- [T319953 — Migrate panoviewer to Kubernetes](https://phabricator.wikimedia.org/T319953)
- [T151749 — 360 Photo support in MediaWiki](https://phabricator.wikimedia.org/T151749)
- [T138933 — Explore moving Panoviewer into production](https://phabricator.wikimedia.org/T138933)
- [Commons:Montage documentation](https://commons.wikimedia.org/wiki/Commons:Montage)
- [Commons panorama taxonomy analysis](../commons-panorama-taxonomy-analysis.md)
- [Panorama classifier design document](../panorama-classifier-design.md)
