"""Explicit, sequential preparation of supplied AUBAR videos. Originals are read-only.

Requires Pillow, NumPy, SciPy and a supplied FFmpeg executable. No network calls.
All native video frames are kept as WebP and in the 24 fps atlas.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "newAUBAR"


def cut_background(image, settings):
    """Offline silhouette matte for these light-room clips, not a general AI matte.

    Keep the largest dark/chromatic subject inside an authored search region;
    fill interior highlights and preserve the laptop/table via authored polygons.
    These fixed masks are specific to the approved camera/crop of each video.
    """
    rgb = np.asarray(image.convert("RGB")).astype(np.int16)
    region = Image.new("L", image.size)
    ImageDraw.Draw(region).polygon([tuple(p) for p in settings["subjectRegion"]], fill=255)
    foreground = ((rgb.min(axis=2) < settings["darkThreshold"]) | (
        (rgb.max(axis=2) - rgb.min(axis=2) > settings["chroma"]) &
        (rgb.min(axis=2) < 220))) & (np.asarray(region) > 0)
    foreground = ndimage.binary_closing(foreground, iterations=1)
    labels, _ = ndimage.label(foreground)
    counts = np.bincount(labels.ravel())
    counts[0] = 0
    if not counts.any():
        raise ValueError("No foreground detected; review crop and matte settings")
    foreground = ndimage.binary_fill_holes(labels == counts.argmax())
    alpha = Image.fromarray((foreground * 255).astype("uint8"))
    draw = ImageDraw.Draw(alpha)
    draw.polygon([tuple(p) for p in settings["laptop"]], fill=255)
    draw.rectangle((0, settings["deskY"], image.width, image.height), fill=255)
    alpha = alpha.filter(ImageFilter.GaussianBlur(0.35))
    rgba = image.convert("RGBA")
    rgba.putalpha(alpha)
    return rgba


def contact(frames, output, indices, columns=6):
    tile_w, tile_h = 160, 190
    sheet = Image.new("RGB", (columns * tile_w,
        ((len(indices) + columns - 1) // columns) * tile_h), "#243448")
    draw = ImageDraw.Draw(sheet)
    for n, i in enumerate(indices):
        im = frames[i].copy()
        im.thumbnail((tile_w, tile_h - 22))
        x, y = n % columns * tile_w, n // columns * tile_h
        sheet.paste(im, (x + (tile_w - im.width) // 2, y),
                    im if im.mode == "RGBA" else None)
        draw.text((x + 4, y + tile_h - 19), f"{i:03d} / {i/24:.2f}s", fill="white")
    sheet.save(output, quality=90)


def prepare(ffmpeg, config, reuse):
    output = ASSETS / "frames-preparados"
    output.mkdir(exist_ok=True)
    manifest = {"schemaVersion": 1, "sourceFps": 24, "atlasFps": 24,
        "clips": [], "notes": [
            "Clips are independent sources; no cross-clip identity or pose alignment is assumed.",
            "Authored silhouette matte; desk and laptop retained. Hair/contours may need refinement.",
            "No firmware integration or audio-driven mouth animation is included."]}
    for clip in config["clips"]:
        name = clip["id"]
        work = ASSETS / "revision-video" / name
        work.mkdir(parents=True, exist_ok=True)
        width, height = clip["size"]
        x, y, w, h = clip["crop"]
        if not reuse:
            subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin",
                "-y", "-threads", "1", "-i", str(ASSETS / clip["source"]),
                "-an", "-vf", f"crop={w}:{h}:{x}:{y},scale={width}:{height}:flags=lanczos",
                "-filter_threads", "1", "-fps_mode", "passthrough", "-frames:v", "240",
                "-start_number", "0", str(work / "%03d.png")], check=True, timeout=120)
        frames = []
        masked = []
        original_dir = output / name / "con-fondo"
        masked_dir = output / name / "sin-fondo"
        original_dir.mkdir(parents=True, exist_ok=True)
        masked_dir.mkdir(parents=True, exist_ok=True)
        for i in range(240):
            with Image.open(work / f"{i:03d}.png") as source:
                im = source.convert("RGB")
            rgba = cut_background(im, clip["matte"])
            im.save(original_dir / f"{i:03d}.webp", lossless=True, method=2)
            rgba.save(masked_dir / f"{i:03d}.webp", lossless=True, method=2)
            frames.append(im)
            masked.append(rgba)
        selected = list(range(240))
        columns = 8
        rows = (len(selected) + columns - 1) // columns
        atlas = Image.new("RGBA", (columns * width, rows * height))
        for tile, index in enumerate(selected):
            atlas.paste(masked[index], (tile % columns * width, tile // columns * height))
        atlas_name = f"{name}/atlas.webp"
        atlas.save(output / atlas_name, lossless=True, method=2)
        masked[clip["neutral"]].save(output / name / "neutral.webp", lossless=True, method=2)
        contact(frames, output / name / "revision-con-fondo.jpg", list(range(0, 240, 6)))
        contact(masked, output / name / "revision-sin-fondo.jpg", list(range(0, 240, 12)))
        contact(masked, output / name / "poses.jpg", clip["poseFrames"], columns=4)
        # Animated preview is an authoring artifact, not a runtime video dependency.
        previews = []
        for i in selected:
            frame = Image.new("RGB", (width, height), "#0d1117")
            frame.paste(masked[i], (0, 0), masked[i])
            previews.append(frame)
        previews[0].save(output / name / "vista-previa.webp", save_all=True,
            append_images=previews[1:],
            duration=[round((i+1)*1000/24)-round(i*1000/24) for i in selected],
            loop=0, quality=85, method=2)
        manifest["clips"].append({**clip, "sourceFrameCount": 240,
            "frameDurationMs": 1000 / 24, "atlas": atlas_name,
            "columns": columns, "rows": rows, "sourceFrames": selected,
            "neutralImage": f"{name}/neutral.webp",
            "tracks": {key: {"sourceFrames": list(range(a, b + 1)),
                "atlasTiles": [selected.index(i) for i in selected if a <= i <= b],
                "durationMs": (b-a+1)*1000/24}
                for key, (a, b) in clip["ranges"].items()}})
        print(f"{name}: 240 source frames, {len(selected)} atlas tiles", flush=True)
    # Supplied transparent WebP stills remain independent assets, never inserted
    # into a video track (their identity/scale can differ from generated video).
    stills = sorted((ASSETS / "animaciones-sin-fondo" / "formato webp").glob("*.webp"))
    still_atlas = Image.new("RGBA", (180 * len(stills), 320))
    manifest["stills"] = []
    for index, source in enumerate(stills):
        with Image.open(source) as im:
            frame = im.convert("RGBA")
            frame.thumbnail((180, 320), Image.Resampling.LANCZOS)
        x = index * 180 + (180 - frame.width) // 2
        still_atlas.paste(frame, (x, (320 - frame.height) // 2))
        manifest["stills"].append({"id": source.stem.removesuffix("-Photoroom"),
            "source": source.relative_to(ASSETS).as_posix(), "tile": index})
    manifest["stillAtlas"] = {"image": "poses-estaticas.webp", "width": 180,
        "height": 320, "columns": len(stills)}
    still_atlas.save(output / "poses-estaticas.webp", lossless=True, method=2)
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)
        + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--config", type=Path,
        default=ASSETS / "aubar-assets.json")
    parser.add_argument("--reuse-frames", action="store_true")
    args = parser.parse_args()
    prepare(args.ffmpeg, json.loads(args.config.read_text(encoding="utf-8")), args.reuse_frames)
