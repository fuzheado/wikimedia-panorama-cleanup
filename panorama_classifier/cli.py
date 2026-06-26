"""
panorama-classifier — Classify a photo by panorama type and suggest
Commons categories, templates, and metadata.

Usage:
    panorama-classifier image.jpg
    panorama-classifier --json image.jpg        # machine-readable output
    panorama-classifier --wikitext image.jpg    # copy-paste for Commons
    panorama-classifier --verbose image.jpg     # show all layer results
    panorama-classifier --no-pixels image.jpg   # skip pixel analysis (faster)
"""

import argparse
import json
import os
import sys

from .metadata import extract_metadata, classify_from_gpano
from .heuristics import (
    classify_by_aspect_ratio,
    classify_by_camera,
    classify_by_software,
    classify_by_filename,
)
from .pixel_analysis import analyze_pixels
from .fusion import fuse_results
from .output import generate_wikitext, generate_summary


def classify_image(image_path, use_pixels=True):
    """Run full classification pipeline on a single image.

    Returns a dict with:
        classification: final fused result
        metadata: raw GPano + EXIF
        heuristics: individual heuristic results
        pixel_results: pixel analysis (if run)
        wikitext: suggested Commons wikitext
        summary: human-readable summary
    """
    if not os.path.isfile(image_path):
        return {"error": f"File not found: {image_path}"}

    filename = os.path.basename(image_path)

    # ---- Layer 0: File stats ----
    file_size = os.path.getsize(image_path)

    # ---- Layer 1: Metadata extraction ----
    meta = extract_metadata(image_path)
    gpano_classification = classify_from_gpano(meta["gpano"])
    exif = meta["exif"]

    # ---- Layer 2: Heuristics ----
    # Get dimensions (prefer EXIF, fall back to PIL)
    width = exif.get("image_width", 0)
    height = exif.get("image_height", 0)

    if not width or not height:
        try:
            from PIL import Image
            with Image.open(image_path) as img:
                width, height = img.size
        except Exception:
            width, height = 0, 0

    heuristic_results = {
        "aspect_ratio": classify_by_aspect_ratio(width, height),
        "camera": classify_by_camera(exif),
        "software": classify_by_software(exif),
        "filename": classify_by_filename(image_path),
        "file_size": file_size,
        "dimensions": {"width": width, "height": height},
    }

    # ---- Layer 3: Pixel analysis (optional, expensive) ----
    pixel_results = None
    if use_pixels:
        # Only run if previous layers were inconclusive
        if (gpano_classification is None and
                heuristic_results["camera"] is None and
                (heuristic_results["aspect_ratio"] or {}).get("confidence", 0) < 0.85):
            pixel_results = analyze_pixels(image_path)

    # ---- Fusion ----
    classification = fuse_results(gpano_classification, heuristic_results, pixel_results)

    # ---- Output generation ----
    wikitext = generate_wikitext(classification, filename)
    summary = generate_summary(classification, filename)

    return {
        "classification": classification,
        "metadata": {"gpano": meta["gpano"], "exif": exif},
        "heuristics": heuristic_results,
        "pixel_results": pixel_results,
        "wikitext": wikitext,
        "summary": summary,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Classify a photo by panorama type for Wikimedia Commons",
        epilog="Examples:\n"
               "  panorama-classifier photo.jpg\n"
               "  panorama-classifier --json photo.jpg\n"
               "  panorama-classifier --wikitext photo.jpg\n"
               "  panorama-classifier --verbose --no-pixels photo.jpg",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("image", help="Path to image file")
    parser.add_argument("--json", action="store_true",
                        help="Output machine-readable JSON")
    parser.add_argument("--wikitext", action="store_true",
                        help="Output Commons wikitext block")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show all layer results")
    parser.add_argument("--no-pixels", action="store_true",
                        help="Skip pixel analysis (faster, less accurate)")
    parser.add_argument("--version", action="version", version="panorama-classifier 0.1.0")

    args = parser.parse_args()

    result = classify_image(args.image, use_pixels=not args.no_pixels)

    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        # Remove wikitext block from JSON output (it's multi-line and messy)
        json_output = {
            "classification": result["classification"],
            "metadata": result["metadata"],
            "heuristics": {k: v for k, v in result["heuristics"].items()
                           if k != "file_size"},
        }
        if args.verbose:
            json_output["pixel_results"] = result["pixel_results"]
        print(json.dumps(json_output, indent=2, default=str))

    elif args.wikitext:
        print(result["wikitext"])

    else:
        print(result["summary"])
        print()

        if args.verbose:
            print("─" * 50)
            print("Metadata (EXIF):")
            exif = result["metadata"]["exif"]
            for k, v in exif.items():
                if v:
                    print(f"  {k}: {v}")

            print(f"\nHeuristic results:")
            for key, val in result["heuristics"].items():
                if val and key != "file_size":
                    print(f"  {key}: {val.get('type', val.get('reason', str(val)[:100]))}")

            if result["pixel_results"]:
                print(f"\nPixel analysis:")
                for key, val in result["pixel_results"].items():
                    if isinstance(val, dict) and val:
                        relevant = {k: v for k, v in val.items()
                                    if k not in ("confidence", "source")}
                        print(f"  {key}: {relevant}")

        print("─" * 50)
        conf = result["classification"]["confidence"]
        if conf >= 0.90:
            print(f"✓ High confidence ({conf:.0%}) — auto-classification reliable")
        elif conf >= 0.70:
            print(f"⚠ Medium confidence ({conf:.0%}) — suggest human review")
        elif conf >= 0.40:
            print(f"⚡ Low confidence ({conf:.0%}) — please verify manually")
        else:
            print(f"✗ Could not classify confidently ({conf:.0%})")


if __name__ == "__main__":
    main()
