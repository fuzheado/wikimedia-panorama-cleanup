"""
Panorama Photo Classifier — Automatically classify 360° and panoramic
photos for Wikimedia Commons categorization.

Usage:
    python -m panorama_classifier image.jpg
    python -m panorama_classifier --json image.jpg
    python -m panorama_classifier --wikitext image.jpg
"""

from .cli import main

if __name__ == "__main__":
    main()
