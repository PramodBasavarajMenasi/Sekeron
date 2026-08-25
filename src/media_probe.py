from __future__ import annotations

import wave
from pathlib import Path

from .schemas import Evidence


def probe_image(path: Path, image_index: int, category: str) -> Evidence:
    metadata = {}
    try:
        from PIL import Image, ImageStat

        with Image.open(path) as image:
            width, height = image.size
            orientation = orientation_label(width, height)
            thumb = image.convert("L").resize((32, 32))
            brightness = ImageStat.Stat(thumb).mean[0]
            lighting = brightness_label(brightness)
            if category == "video_editors":
                claim = f"supporting image asset probe: still image, {width}x{height}px; not treated as editing proof"
            else:
                claim = (
                    f"image content probe: {orientation} still image, "
                    f"{width}x{height}px, {lighting} average luminance"
                )
            metadata = {
                "width": width,
                "height": height,
                "orientation": orientation,
                "average_luminance": round(brightness, 2),
                "lighting_bucket": lighting,
            }
    except Exception as exc:
        claim = f"image sample: content probe unavailable ({type(exc).__name__}); sampled for human review"
        metadata = {"error": type(exc).__name__}
    return Evidence(
        str(path),
        "media_probe",
        claim,
        image_index=image_index,
        confidence="low",
        layer="metadata",
        metadata=metadata,
    )


def probe_audio(path: Path) -> list[Evidence]:
    metadata = audio_metadata(path)
    duration = metadata.get("duration_seconds")
    stamps = sample_timestamps(duration)
    details = f"duration {duration:.1f}s" if duration else "duration unavailable"
    return [
        Evidence(
            str(path),
            "media_probe",
            f"audio content probe: sampled track/performance format, {details}",
            timestamp=stamp,
            confidence="low",
            layer="sampling",
            metadata={**metadata, "sample_position": stamp},
        )
        for stamp in stamps
    ]


def probe_video(path: Path, category: str) -> list[Evidence]:
    try:
        import cv2

        capture = cv2.VideoCapture(str(path))
        if not capture.isOpened():
            raise ValueError("OpenCV could not open video")
        fps = capture.get(cv2.CAP_PROP_FPS) or 0
        frames = capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        duration = frames / fps if fps else None
        orientation = orientation_label(width, height)
        stamps = sample_timestamps(duration)
        result = []
        for stamp in stamps:
            frame_index = timestamp_to_frame(stamp, fps, frames)
            portfolio_format = video_portfolio_format(category)
            claim = (
                f"video content probe: {orientation} {portfolio_format}, "
                f"{width}x{height}px, {fps:.2f}fps, duration {duration:.1f}s, frame_index {frame_index}"
                if duration
                else f"video content probe: {orientation} {portfolio_format}, {width}x{height}px, duration unavailable"
            )
            result.append(
                Evidence(
                    str(path),
                    "media_probe",
                    claim,
                    timestamp=stamp,
                    confidence="low",
                    layer="sampling",
                    metadata={
                        "width": width,
                        "height": height,
                        "orientation": orientation,
                        "fps": round(fps, 3) if fps else None,
                        "frame_count": int(frames) if frames else None,
                        "duration_seconds": round(duration, 3) if duration else None,
                        "frame_index": frame_index,
                        "sample_position": stamp,
                    },
                )
            )
        capture.release()
        return result
    except Exception as exc:
        return [
            Evidence(
                str(path),
                "media_probe",
                f"video sample: content probe unavailable ({type(exc).__name__}); sampled for human review",
                timestamp=stamp,
                confidence="low",
                layer="sampling",
                metadata={"error": type(exc).__name__, "sample_position": stamp},
            )
            for stamp in ("00:00", "middle", "end")
        ]


def audio_metadata(path: Path) -> dict:
    metadata = {}
    try:
        from mutagen import File

        media = File(path)
        if media and media.info and getattr(media.info, "length", None):
            metadata["duration_seconds"] = round(float(media.info.length), 3)
            if getattr(media.info, "bitrate", None):
                metadata["bitrate"] = int(media.info.bitrate)
            if getattr(media.info, "sample_rate", None):
                metadata["sample_rate"] = int(media.info.sample_rate)
            if getattr(media.info, "channels", None):
                metadata["channels"] = int(media.info.channels)
            return metadata
    except Exception:
        pass

    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as wav:
                metadata["duration_seconds"] = round(wav.getnframes() / float(wav.getframerate()), 3)
                metadata["sample_rate"] = int(wav.getframerate())
                metadata["channels"] = int(wav.getnchannels())
                return metadata
        except Exception:
            return {"error": "audio metadata unavailable"}
    return metadata


def sample_timestamps(duration: float | None) -> list[str]:
    if not duration or duration <= 0:
        return ["00:00", "middle", "end"]
    return [format_seconds(0), format_seconds(duration / 2), format_seconds(max(duration - 1, 0))]


def timestamp_to_frame(stamp: str, fps: float, frames: float) -> int:
    if not fps or not frames:
        return 0
    if stamp == "middle":
        return int(frames // 2)
    if stamp == "end":
        return int(max(frames - 1, 0))
    minutes, seconds = stamp.split(":")
    return int((int(minutes) * 60 + int(seconds)) * fps)


def format_seconds(seconds: float) -> str:
    total = int(seconds)
    return f"{total // 60:02d}:{total % 60:02d}"


def orientation_label(width: int, height: int) -> str:
    if width <= 0 or height <= 0:
        return "unknown orientation"
    if height > width:
        return "vertical"
    if width > height:
        return "horizontal"
    return "square"


def brightness_label(value: float) -> str:
    if value < 75:
        return "low-light"
    if value > 180:
        return "bright"
    return "balanced-light"


def video_portfolio_format(category: str) -> str:
    if category == "musicians":
        return "performance portfolio format"
    if category == "video_editors":
        return "video-edit portfolio format"
    return "video portfolio format"
