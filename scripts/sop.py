#!/usr/bin/env python3
"""Initialize and validate a SOP project, export captions/chapters, or mux chapters.
No network, credentials, TTS generation, uploads, or third-party Python packages.
"""
from __future__ import annotations
import argparse
import json
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


def number(value, label, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < minimum:
        raise ValueError(f"{label}: expected a finite number >= {minimum}")
    return value


def asset(root, value):
    if not isinstance(value, str) or not value or Path(value).is_absolute() or ".." in Path(value).parts or ":" in value:
        raise ValueError("asset paths must be relative project paths without '..' or URL schemes")
    result = (root / value).resolve()
    if not result.is_relative_to(root.resolve()) or not result.is_file():
        raise ValueError(f"missing or out-of-project asset: {value}")
    return result


def media_probe(path):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def image_dimensions(path, probe=False):
    if path.suffix.lower() == ".png":
        with path.open("rb") as stream:
            header = stream.read(24)
        if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError("invalid PNG header")
        return struct.unpack(">II", header[16:24])
    if path.suffix.lower() == ".svg":
        xml = ET.parse(path).getroot()
        if xml.get("viewBox"):
            values = [float(item) for item in xml.get("viewBox").replace(",", " ").split()]
            return values[2], values[3]
        return float(xml.attrib["width"]), float(xml.attrib["height"])
    if probe:
        streams = media_probe(path)["streams"]
        video = next((s for s in streams if s.get("codec_type") == "video"), None)
        if video:
            return video["width"], video["height"]
    raise ValueError("use PNG/SVG images, or --probe for formats supported by ffprobe")


def nonempty(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}: expected non-empty text")


def validate(path, probe=False):
    data = json.loads(path.read_text(encoding="utf-8"))
    root = path.parent
    if data.get("version") != 1:
        raise ValueError("manifest version must be 1")
    for field in ("title", "language"):
        nonempty(data.get(field), field)
    if data.get("canvas") != {"width": 1920, "height": 1080, "fps": 30}:
        raise ValueError("this starter supports 1920x1080 at 30 fps")
    mode = data.get("narration", {}).get("mode")
    if mode not in {"demo-silent", "provided", "elevenlabs", "native"}:
        raise ValueError("narration.mode must be demo-silent, provided, elevenlabs, or native")
    screens = {}
    for screen in data.get("screenshots", []):
        sid = screen.get("id", "")
        if not ID.fullmatch(sid) or sid in screens:
            raise ValueError("screenshot IDs must be unique lowercase slugs")
        if screen.get("kind") not in {"synthetic", "capture"}:
            raise ValueError(f"{sid}: kind must be synthetic or capture")
        for field in ("source", "capturedAt"):
            nonempty(screen.get(field), f"{sid}.{field}")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", screen["capturedAt"]):
            raise ValueError(f"{sid}: capturedAt must use YYYY-MM-DD")
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
    for step in steps:
        sid = step.get("id", "")
        if not ID.fullmatch(sid) or sid in seen:
            raise ValueError("step IDs must be unique lowercase slugs")
        seen.add(sid)
        for field in ("title", "instruction", "chapter"):
            nonempty(step.get(field), f"{sid}.{field}")
        if len(step["title"]) > 65 or len(step["instruction"]) > 180:
            raise ValueError(f"{sid}: shorten title (65 chars) or instruction (180 chars) for the starter layout")
        checklist = step.get("checklist")
        if not isinstance(checklist, list) or not 1 <= len(checklist) <= 4:
            raise ValueError(f"{sid}: use 1–4 checklist items")
        for item in checklist:
            nonempty(item.get("text"), f"{sid}.checklist.text")
            if len(item["text"]) > 74 or item.get("state") not in {"todo", "current", "done"}:
                raise ValueError(f"{sid}: checklist text <=74 characters; state todo/current/done")
        duration = number(step.get("duration"), f"{sid}.duration", 2)
        screen = screens.get(step.get("screenshot"))
        if not screen:
            raise ValueError(f"{sid}: unknown screenshot")
        target = step.get("target", {})
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
        if mode != "demo-silent" and not voice:
            raise ValueError(f"{sid}: narrated projects require a voice asset for every step")
        if mode == "demo-silent" and voice:
            raise ValueError("demo-silent cannot contain voice clips; choose the actual narration mode")
        if voice:
            audio = asset(root, voice.get("path"))
            voice_duration = number(voice.get("duration"), f"{sid}.voice.duration", 0.01)
            offset = number(voice.get("offset", 0.5), f"{sid}.voice.offset")
            if offset + voice_duration > duration - 0.25:
                raise ValueError(f"{sid}: voice is clipped or has less than 0.25s of trailing hold")
            if probe:
                info = media_probe(audio)
                if not any(s.get("codec_type") == "audio" for s in info["streams"]):
                    raise ValueError(f"{sid}: voice asset has no audio stream")
                actual = float(info["format"]["duration"])
                if abs(actual - voice_duration) > 0.08:
                    raise ValueError(f"{sid}: voice duration differs from ffprobe ({actual:.3f}s)")
        previous_end = 0
        if not step.get("captions"):
            raise ValueError(f"{sid}: captions are required, including in a silent demo")
        for caption in step["captions"]:
            start = number(caption.get("start"), f"{sid}.caption.start")
            end = number(caption.get("end"), f"{sid}.caption.end")
            nonempty(caption.get("text"), f"{sid}.caption.text")
            if start < previous_end or start >= end or end > duration:
                raise ValueError(f"{sid}: captions overlap, have zero length, or exceed the step")
            if len(caption["text"]) > 145:
                raise ValueError(f"{sid}: split caption into shorter timed cues")
            captions.append({"start": round(cursor + start, 3), "end": round(cursor + end, 3), "text": caption["text"]})
            previous_end = end
        timeline.append({"id": sid, "start": round(cursor, 3), "end": round(cursor + duration, 3), "title": step["chapter"]})
        cursor += duration
    return data, {"ok": True, "steps": len(steps), "duration": round(cursor, 3), "narration": mode, "mediaProbed": probe, "timeline": timeline, "captions": captions}


def timestamp(seconds, srt=False):
    milliseconds = round(seconds * 1000)
    hours, remaining = divmod(milliseconds, 3600000)
    minutes, remaining = divmod(remaining, 60000)
    secs, millis = divmod(remaining, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02}{',' if srt else '.'}{millis:03}"


def metadata_escape(value):
    return value.replace("\\", "\\\\").replace("\n", " ").replace("\r", " ").replace("=", "\\=").replace(";", "\\;").replace("#", "\\#")


def export(manifest, output, probe=False):
    data, report = validate(manifest, probe)
    output.mkdir(parents=True, exist_ok=True)
    srt = []
    subtitles = ["WEBVTT", ""]
    chapter_vtt = ["WEBVTT", ""]
    metadata = [";FFMETADATA1", f"title={metadata_escape(data['title'])}"]
    chapters = []
    for i, caption in enumerate(report["captions"], 1):
        srt.append(f"{i}\n{timestamp(caption['start'], True)} --> {timestamp(caption['end'], True)}\n{caption['text']}\n")
        subtitles.append(f"{timestamp(caption['start'])} --> {timestamp(caption['end'])}\n{caption['text']}\n")
    for chapter in report["timeline"]:
        start, end, title = chapter["start"], chapter["end"], chapter["title"]
        chapters.append(f"{timestamp(start).split('.')[0]} {title}")
        chapter_vtt.append(f"{timestamp(start)} --> {timestamp(end)}\n{title}\n")
        metadata.extend(["[CHAPTER]", "TIMEBASE=1/1000", f"START={round(start * 1000)}", f"END={round(end * 1000)}", f"title={metadata_escape(title)}"])
    files = {"captions.srt": "\n".join(srt), "captions.vtt": "\n".join(subtitles), "chapters.vtt": "\n".join(chapter_vtt), "chapters.txt": "\n".join(chapters), "chapters.ffmetadata": "\n".join(metadata), "validation.json": json.dumps(report, ensure_ascii=False, indent=2)}
    for name, content in files.items():
        (output / name).write_text(content + "\n", encoding="utf-8")
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
            print(json.dumps({"ok": True, "next": "node build.mjs", "demo": "Synthetic UI, silent"}))
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
