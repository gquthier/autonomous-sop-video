#!/usr/bin/env python3
"""Initialize and validate a SOP project, export captions/chapters, or mux chapters.
No network, credentials, TTS generation, uploads, or third-party Python packages.
"""
from __future__ import annotations
import argparse
from datetime import date
import html
import json
import os
import unicodedata
import math
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET

STARTER = Path(__file__).resolve().parents[1] / "assets" / "starter"
ID = re.compile(r"^[a-z][a-z0-9-]*$")


# Keep millisecond arithmetic exact enough for captions and FFmpeg metadata.
MAX_TIME = (2**53 - 1) / 1000


def number(value, label, minimum=0):
    try:
        valid = not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value >= minimum
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f"{label}: expected a finite number >= {minimum}")
    return value


def timing(value, label, minimum=0):
    value = number(value, label, minimum)
    if value > MAX_TIME:
        raise ValueError(f"{label}: timing exceeds safe millisecond range")
    return value


def milliseconds(value):
    """Match JavaScript Math.round for nonnegative export timestamps."""
    return math.floor(timing(value, 'timestamp') * 1000 + 0.5)


def rounded_time(value):
    return milliseconds(value) / 1000


def mapping(value, label):
    if not isinstance(value, dict):
        raise ValueError(f"{label}: expected an object")
    return value


def items(value, label):
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label}: expected a non-empty list")
    return value


def slug(value, label, seen):
    if not isinstance(value, str) or not ID.fullmatch(value) or value in seen:
        raise ValueError(f"{label}: IDs must be unique lowercase slugs")
    return value


def choice(value, allowed, label):
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{label}: expected one of {', '.join(sorted(allowed))}")
    return value


def asset(root, value):
    if not isinstance(value, str) or not value or any(unicodedata.category(c) in {'Cc', 'Cs'} for c in value) or '\\' in value or Path(value).is_absolute() or any(p in {'', '.', '..'} for p in value.split('/')) or ":" in value:
        raise ValueError("asset paths must be relative project paths without '..' or URL schemes")
    result = (root / value).resolve()
    if not result.is_relative_to(root.resolve()) or not result.is_file():
        raise ValueError(f"missing or out-of-project asset: {value}")
    return result


def media_probe(path):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def image_dimensions(path, probe=False):
    if path.suffix.lower() not in {'.png', '.svg', '.jpg', '.jpeg', '.webp'}:
        raise ValueError('screenshots must be static PNG/SVG/JPEG/WebP images')
    if path.suffix.lower() == ".png":
        with path.open("rb") as stream:
            header = stream.read(24)
        if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b'IHDR':
            raise ValueError("invalid PNG header")
        return struct.unpack(">II", header[16:24])
    if path.suffix.lower() == ".svg":
        try:
            xml = ET.parse(path).getroot()
            if xml.get("viewBox"):
                values = [float(item) for item in xml.get("viewBox").replace(",", " ").split()]
                if len(values) != 4 or not all(math.isfinite(v) for v in values):
                    raise ValueError("viewBox needs four finite numbers")
                dimensions = values[2:]
            else:
                dimensions = [float(xml.attrib["width"]), float(xml.attrib["height"])]
            return tuple(number(v, "SVG dimension", 1) for v in dimensions)
        except (ValueError, KeyError, ET.ParseError) as error:
            raise ValueError(f"{path.name}: invalid SVG dimensions: {error}") from error
    if probe:
        streams = media_probe(path)["streams"]
        video = next((s for s in streams if s.get("codec_type") == "video"), None)
        if video and video.get('codec_name') in {'mjpeg', 'png', 'webp'}:
            return video["width"], video["height"]
    raise ValueError("use PNG/SVG images, or --probe for formats supported by ffprobe")


def nonempty(value, label):
    if not isinstance(value, str) or not plain_line(value.replace('\ufeff', '')):
        raise ValueError(f"{label}: expected non-empty text")
    if any(unicodedata.category(c) == 'Cs' or (unicodedata.category(c) == 'Cc' and c not in '\t\n\r') for c in value):
        raise ValueError(f"{label}: expected valid Unicode text without control characters or lone surrogates")


def validate(path, probe=False):
    data = json.loads(path.read_text(encoding="utf-8"))
    root = path.parent
    mapping(data, "manifest")
    if type(data.get("version")) is not int or data["version"] != 1:
        raise ValueError("manifest version must be integer 1")
    for field in ("title", "language"):
        nonempty(data.get(field), field)
    if "series" in data:
        nonempty(data["series"], "series")
        if len(data['series']) > 100:
            raise ValueError('series: shorten to 100 characters for the starter layout')
    canvas = mapping(data.get("canvas"), "canvas")
    if any(type(canvas.get(k)) is not int or canvas[k] != v for k, v in {"width": 1920, "height": 1080, "fps": 30}.items()):
        raise ValueError("canvas: this starter supports integer 1920x1080 at 30 fps")
    mode = choice(mapping(data.get("narration"), "narration").get("mode"), {"demo-silent", "provided", "elevenlabs", "native"}, "narration.mode")
    screens = {}
    for index, screen in enumerate(items(data.get("screenshots"), "screenshots")):
        mapping(screen, f"screenshots[{index}]")
        sid = slug(screen.get("id"), f"screenshots[{index}].id", screens)
        choice(screen.get("kind"), {"synthetic", "capture"}, f"{sid}.kind")
        if "redacted" in screen and type(screen["redacted"]) is not bool:
            raise ValueError(f"{sid}.redacted: expected a boolean")
        for field in ("source", "capturedAt"):
            nonempty(screen.get(field), f"{sid}.{field}")
        try:
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", screen["capturedAt"]):
                raise ValueError("invalid format")
            date.fromisoformat(screen["capturedAt"])
        except ValueError as error:
            raise ValueError(f"{sid}.capturedAt: expected a valid calendar date YYYY-MM-DD") from error
        if screen.get("kind") == "capture" and screen.get("redacted") is not True:
            raise ValueError(f"{sid}: review privacy and explicitly set redacted=true")
        image = asset(root, screen.get("path"))
        if image.suffix.lower() == ".svg" and screen["kind"] != "synthetic":
            raise ValueError("SVG is reserved for visibly labeled synthetic examples; use raster captures for real UI")
        width = number(screen.get("width"), f"{sid}.width", 1)
        height = number(screen.get("height"), f"{sid}.height", 1)
        if image_dimensions(image, probe) != (width, height):
            raise ValueError(f"{sid}: declared dimensions differ from image")
        screens[sid] = screen
    if not screens:
        raise ValueError("at least one screenshot is required")
    steps = data.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("at least one step is required")
    seen, cursor, timeline, captions = set(), 0.0, [], []
    for index, step in enumerate(steps):
        mapping(step, f"steps[{index}]")
        sid = slug(step.get("id"), f"steps[{index}].id", seen)
        seen.add(sid)
        if "tip" in step:
            nonempty(step["tip"], f"{sid}.tip")
            if len(step["tip"]) > 180:
                raise ValueError(f"{sid}.tip: shorten to 180 characters for the starter layout")
        for field in ("title", "instruction", "chapter"):
            nonempty(step.get(field), f"{sid}.{field}")
        if len(step["title"]) > 65 or len(step["instruction"]) > 180:
            raise ValueError(f"{sid}: shorten title (65 chars) or instruction (180 chars) for the starter layout")
        checklist = step.get("checklist")
        if not isinstance(checklist, list) or not 1 <= len(checklist) <= 4:
            raise ValueError(f"{sid}: use 1–4 checklist items")
        for item_index, item in enumerate(checklist):
            mapping(item, f"{sid}.checklist[{item_index}]")
            nonempty(item.get("text"), f"{sid}.checklist.text")
            choice(item.get("state"), {"todo", "current", "done"}, f"{sid}.checklist.state")
            if len(item["text"]) > 74:
                raise ValueError(f"{sid}: checklist text <=74 characters")
        duration = timing(step.get("duration"), f"{sid}.duration", 2)
        step_end = timing(cursor + duration, f"{sid}.cumulative duration")
        nonempty(step.get("screenshot"), f"{sid}.screenshot")
        screen = screens.get(step["screenshot"])
        if not screen:
            raise ValueError(f"{sid}: unknown screenshot")
        target = mapping(step.get("target"), f"{sid}.target")
        x = number(target.get("x"), f"{sid}.target.x")
        y = number(target.get("y"), f"{sid}.target.y")
        w = number(target.get("width"), f"{sid}.target.width", 1)
        h = number(target.get("height"), f"{sid}.target.height", 1)
        if x + w > screen["width"] or y + h > screen["height"]:
            raise ValueError(f"{sid}: target extends outside native screenshot bounds")
        zoom = number(step.get("zoom", 1.5), f"{sid}.zoom", 1)
        if zoom > 3:
            raise ValueError(f"{sid}: zoom exceeds 3x; use a higher-resolution capture")
        voice = step.get("voice")
        if "voice" in step:
            mapping(voice, f"{sid}.voice")
        if mode != "demo-silent" and voice is None:
            raise ValueError(f"{sid}: narrated projects require a voice asset for every step")
        if mode == "demo-silent" and voice is not None:
            raise ValueError("demo-silent cannot contain voice clips; choose the actual narration mode")
        if voice is not None:
            audio = asset(root, voice.get("path"))
            voice_duration = timing(voice.get("duration"), f"{sid}.voice.duration", 0.01)
            offset = timing(voice.get("offset", 0.5), f"{sid}.voice.offset")
            if number(voice.get("volume", 0.88), f"{sid}.voice.volume") > 1:
                raise ValueError(f"{sid}.voice.volume: expected a number between 0 and 1")
            if offset + voice_duration > duration - 0.25:
                raise ValueError(f"{sid}: voice is clipped or has less than 0.25s of trailing hold")
            if probe:
                info = media_probe(audio)
                if not any(s.get("codec_type") == "audio" for s in info["streams"]):
                    raise ValueError(f"{sid}: voice asset has no audio stream")
                try:
                    actual = timing(float(info["format"]["duration"]), f"{sid}.voice measured duration", 0.01)
                except (KeyError, TypeError, ValueError, OverflowError) as error:
                    raise ValueError(f"{sid}.voice: invalid ffprobe duration") from error
                if abs(actual - voice_duration) > 0.08:
                    raise ValueError(f"{sid}: voice duration differs from ffprobe ({actual:.3f}s)")
        previous_end = 0
        if not step.get("captions"):
            raise ValueError(f"{sid}: captions are required, including in a silent demo")
        for caption_index, caption in enumerate(items(step["captions"], f"{sid}.captions")):
            mapping(caption, f"{sid}.captions[{caption_index}]")
            start = timing(caption.get("start"), f"{sid}.caption.start")
            end = timing(caption.get("end"), f"{sid}.caption.end")
            nonempty(caption.get("text"), f"{sid}.caption.text")
            if start < previous_end or start >= end or end > duration:
                raise ValueError(f"{sid}: captions overlap, have zero length, or exceed the step")
            if len(caption["text"]) > 145:
                raise ValueError(f"{sid}: split caption into shorter timed cues")
            global_start, global_end = rounded_time(cursor + start), rounded_time(cursor + end)
            if global_start >= global_end:
                raise ValueError(f"{sid}: caption collapses at millisecond export precision")
            captions.append({"start": global_start, "end": global_end, "text": caption["text"]})
            previous_end = end
        timeline.append({"id": sid, "start": rounded_time(cursor), "end": rounded_time(step_end), "title": step["chapter"]})
        cursor = step_end
    return data, {"ok": True, "steps": len(steps), "duration": rounded_time(cursor), "narration": mode, "mediaProbed": probe, "timeline": timeline, "captions": captions}


def timestamp(seconds, srt=False):
    millis = milliseconds(seconds)
    hours, remaining = divmod(millis, 3600000)
    minutes, remaining = divmod(remaining, 60000)
    secs, millis = divmod(remaining, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02}{',' if srt else '.'}{millis:03}"


def plain_line(value):
    # One physical payload line: no blank-line cue, timestamp, or metadata injection.
    return ' '.join(''.join(' ' if unicodedata.category(c) in {'Cc', 'Zl', 'Zp'} else c for c in value).split())


def cue_text(value):
    # VTT entities preserve literal markup and arrows; SRT readers commonly support
    # the same HTML entities. Never interpret manifest text as subtitle markup.
    return html.escape(plain_line(value), quote=False)


def metadata_escape(value):
    return plain_line(value).replace("\\", "\\\\").replace("=", "\\=").replace(";", "\\;").replace("#", "\\#")


def write_exports(output, files):
    """Create new sidecars only; reject symlinks in every output component.

    Directory-relative, exclusive opens keep a path-swap from redirecting writes
    into assets/manifest or outside the chosen directory. No overwrite mode.
    """
    absolute = Path(os.path.abspath(output))
    directory = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY)
    handles = []
    try:
        for component in absolute.parts[1:]:
            try:
                os.mkdir(component, dir_fd=directory)
            except FileExistsError:
                pass
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        # Check the whole bundle first, avoiding partial exports for ordinary conflicts.
        for name in files:
            try:
                os.stat(name, dir_fd=directory, follow_symlinks=False)
            except FileNotFoundError:
                continue
            raise ValueError(f"export refuses existing destination: {name}; choose a new output directory")
        for name in files:
            descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o666, dir_fd=directory)
            handles.append(descriptor)
        for descriptor, content in zip(handles, files.values()):
            payload = (content + '\n').encode('utf-8')
            with os.fdopen(os.dup(descriptor), 'wb') as stream:
                stream.write(payload)
    except OSError as error:
        raise ValueError(f"unsafe or unwritable export destination: {error}") from error
    finally:
        for descriptor in handles:
            os.close(descriptor)
        os.close(directory)


def export(manifest, output, probe=False):
    data, report = validate(manifest, probe)
    srt = []
    subtitles = ["WEBVTT", ""]
    chapter_vtt = ["WEBVTT", ""]
    metadata = [";FFMETADATA1", f"title={metadata_escape(data['title'])}"]
    chapters = []
    for i, caption in enumerate(report["captions"], 1):
        srt.append(f"{i}\n{timestamp(caption['start'], True)} --> {timestamp(caption['end'], True)}\n{cue_text(caption['text'])}\n")
        subtitles.append(f"{timestamp(caption['start'])} --> {timestamp(caption['end'])}\n{cue_text(caption['text'])}\n")
    for chapter in report["timeline"]:
        start, end, title = chapter["start"], chapter["end"], chapter["title"]
        chapters.append(f"{timestamp(start).split('.')[0]} {plain_line(title)}")
        chapter_vtt.append(f"{timestamp(start)} --> {timestamp(end)}\n{cue_text(title)}\n")
        metadata.extend(["[CHAPTER]", "TIMEBASE=1/1000", f"START={milliseconds(start)}", f"END={milliseconds(end)}", f"title={metadata_escape(title)}"])
    files = {"captions.srt": "\n".join(srt), "captions.vtt": "\n".join(subtitles), "chapters.vtt": "\n".join(chapter_vtt), "chapters.txt": "\n".join(chapters), "chapters.ffmetadata": "\n".join(metadata), "validation.json": json.dumps(report, ensure_ascii=False, indent=2)}
    write_exports(output, files)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="copy the synthetic demo into a new/empty directory")
    init.add_argument("directory", type=Path)
    for name in ("validate", "chapters"):
        command = sub.add_parser(name)
        command.add_argument("manifest", type=Path)
        command.add_argument("--probe", action="store_true", help="also verify audio duration with ffprobe")
        if name == "chapters":
            command.add_argument("--output", required=True, type=Path)
    embed = sub.add_parser("embed", help="copy streams and embed chapter metadata; requires ffmpeg")
    embed.add_argument("video", type=Path)
    embed.add_argument("metadata", type=Path)
    embed.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "init":
            if args.directory.exists() and any(args.directory.iterdir()):
                raise ValueError("init destination must be new or empty")
            shutil.copytree(STARTER, args.directory, dirs_exist_ok=True)
            print(json.dumps({"ok": True, "next": "npm ci --ignore-scripts --no-audit --no-fund && node build.mjs", "demo": "Synthetic UI, silent"}))
        elif args.command == "validate":
            _, report = validate(args.manifest, args.probe)
            print(json.dumps(report, ensure_ascii=False, indent=2))
        elif args.command == "chapters":
            report = export(args.manifest, args.output, args.probe)
            print(json.dumps({"ok": True, "chapters": len(report["timeline"]), "captions": len(report["captions"])}))
        else:
            if not args.video.is_file() or not args.metadata.is_file() or args.output.exists() or args.video.resolve() == args.output.resolve():
                raise ValueError("embed needs existing video/metadata and a new output path")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["ffmpeg", "-v", "error", "-n", "-i", str(args.video), "-f", "ffmetadata", "-i", str(args.metadata), "-map", "0", "-map_metadata", "0", "-map_chapters", "1", "-codec", "copy", "-movflags", "+faststart", str(args.output)], check=True)
            print(json.dumps({"ok": True, "action": "chapters embedded without re-encoding"}))
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError, ET.ParseError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
