"""Optional, local-only camera inference for KoalaByte Blue Ultra.

This module performs a single operator-triggered frame capture and generic object
detection. It does not perform face recognition, person re-identification, plate
OCR, continuous tracking, RF scans, or correlation with Wi-Fi/BLE survey records.
Model weights must already exist locally; no model is downloaded automatically.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG_ROOT = ROOT / "logs" / "ultra_vision"
DEFAULT_MODEL = os.getenv("KOALABYTE_VISION_MODEL", "").strip()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def dependency_status() -> dict[str, Any]:
    status: dict[str, Any] = {"opencv": False, "ultralytics": False, "model_path": DEFAULT_MODEL or None}
    try:
        import cv2  # type: ignore
        status["opencv"] = True
        status["opencv_version"] = getattr(cv2, "__version__", "unknown")
    except Exception as exc:
        status["opencv_error"] = str(exc)
    try:
        import ultralytics  # type: ignore
        status["ultralytics"] = True
        status["ultralytics_version"] = getattr(ultralytics, "__version__", "unknown")
    except Exception as exc:
        status["ultralytics_error"] = str(exc)
    if DEFAULT_MODEL:
        status["model_exists"] = Path(DEFAULT_MODEL).expanduser().is_file()
    else:
        status["model_exists"] = False
    status["status"] = "ULTRA_VISION_READY" if status["opencv"] and status["ultralytics"] and status["model_exists"] else "ULTRA_VISION_OPTIONAL_DEPENDENCIES_MISSING"
    return status


def _load_model(model_path: str):
    path = Path(model_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(
            f"Model must be an existing local file; no downloads are attempted: {path}"
        )
    try:
        from ultralytics import YOLO  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "Optional vision dependencies are missing. See requirements-vision.txt."
        ) from exc
    return YOLO(str(path))


def capture_and_detect(
    *,
    camera_index: int = 0,
    model_path: str,
    confidence: float = 0.45,
    width: int = 1280,
    height: int = 720,
    save_frame: bool = False,
    record: bool = False,
    site_label: str = "",
    log_root: Path = DEFAULT_LOG_ROOT,
) -> dict[str, Any]:
    if not 0.05 <= confidence <= 0.99:
        raise ValueError("confidence must be between 0.05 and 0.99")
    if not 320 <= width <= 3840 or not 240 <= height <= 2160:
        raise ValueError("frame dimensions are outside the supported safe range")

    try:
        import cv2  # type: ignore
    except Exception as exc:
        raise RuntimeError("OpenCV is not installed; see requirements-vision.txt.") from exc

    model = _load_model(model_path)
    capture = cv2.VideoCapture(int(camera_index))
    try:
        if not capture.isOpened():
            raise RuntimeError(f"Camera index {camera_index} could not be opened.")
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, int(width))
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, int(height))
        ok, frame = capture.read()
        if not ok or frame is None:
            raise RuntimeError("Camera opened but did not return a frame.")
    finally:
        capture.release()

    # Explicitly use CPU inference for predictable memory use. The Pi 5 profile
    # can later add an opt-in accelerator backend after hardware benchmarking.
    predictions = model.predict(source=frame, conf=confidence, device="cpu", verbose=False)
    detections: list[dict[str, Any]] = []
    for prediction in predictions:
        names = getattr(prediction, "names", {})
        boxes = getattr(prediction, "boxes", None)
        if boxes is None:
            continue
        for box in boxes:
            cls_id = int(box.cls[0].item())
            label = str(names.get(cls_id, cls_id)) if isinstance(names, dict) else str(cls_id)
            # Keep detections categorical. Never expose identities, faces, or
            # plate text; this module contains no face/plate recognition code.
            if label.lower() in {"face", "license plate", "licence plate"}:
                continue
            xyxy = [int(value) for value in box.xyxy[0].tolist()]
            detections.append({
                "label": label,
                "confidence": round(float(box.conf[0].item()), 4),
                "bbox_xyxy": xyxy,
            })

    now = datetime.now(timezone.utc)
    event: dict[str, Any] = {
        "status": "ULTRA_VISION_CAPTURE_COMPLETE",
        "observed_at_utc": now.replace(microsecond=0).isoformat(),
        "camera_index": int(camera_index),
        "frame_width": int(frame.shape[1]),
        "frame_height": int(frame.shape[0]),
        "inference_device": "cpu",
        "model_file": str(Path(model_path).expanduser().resolve()),
        "confidence_threshold": confidence,
        "site_label": site_label.strip(),
        "detections": detections,
        "privacy_scope": "single operator-triggered frame; no identity recognition or RF correlation",
    }

    if save_frame or record:
        log_root.mkdir(parents=True, exist_ok=True)
    if save_frame:
        captures = log_root / "captures"
        captures.mkdir(parents=True, exist_ok=True)
        frame_path = captures / f"frame_{now.strftime('%Y%m%dT%H%M%SZ')}.jpg"
        if not cv2.imwrite(str(frame_path), frame):
            raise RuntimeError(f"Could not write local frame to {frame_path}")
        event["frame_path"] = str(frame_path)
    if record:
        event_path = log_root / "detections.jsonl"
        with event_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
        event["event_log_path"] = str(event_path)
    return event


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Optional local-only KoalaByte Blue Ultra camera")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Check optional camera and inference dependencies")
    capture = sub.add_parser("capture", help="Capture one frame and run local object detection")
    capture.add_argument("--camera-index", type=int, default=0)
    capture.add_argument("--model", default=DEFAULT_MODEL, help="Path to an already-downloaded local model file")
    capture.add_argument("--confidence", type=float, default=0.45)
    capture.add_argument("--width", type=int, default=1280)
    capture.add_argument("--height", type=int, default=720)
    capture.add_argument("--site-label", default="", help="Optional operator-entered site label; no GPS is collected")
    capture.add_argument("--save-frame", action="store_true", help="Explicitly save the captured image locally")
    capture.add_argument("--record", action="store_true", help="Append detection metadata to local JSONL")
    args = parser.parse_args(argv)

    try:
        if args.command == "status":
            payload = dependency_status()
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0 if payload["status"] == "ULTRA_VISION_READY" else 2
        if not args.model:
            raise ValueError("Set KOALABYTE_VISION_MODEL or pass --model with an existing local model file.")
        payload = capture_and_detect(
            camera_index=args.camera_index,
            model_path=args.model,
            confidence=args.confidence,
            width=args.width,
            height=args.height,
            save_frame=args.save_frame,
            record=args.record,
            site_label=args.site_label,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "ULTRA_VISION_ERROR", "error": str(exc)}, indent=2), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
