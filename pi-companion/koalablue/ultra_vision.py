"""Optional local or explicitly opted-in Ollama Cloud camera inference for KoalaByte Blue Ultra Pi 5.

This module performs one operator-triggered frame capture and generic object
classification. GPS enrichment is opt-in and goes through the existing protected
GNSS gate; it never opens the Heltec serial port itself. User-supplied event and
observation references are contextual links only, not proof that an RF emitter is
physically at the photographed point.

No face recognition, person re-identification, plate OCR, continuous tracking,
RF scans, or model downloads are performed.
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
CAMERA_LIKE_LABELS = {
    "camera", "security camera", "surveillance camera", "traffic camera",
    "webcam", "cctv camera", "dome camera", "bullet camera",
}
LOCATION_MAX_AGE_SECONDS = 120


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def _location_context(enabled: bool) -> dict[str, Any]:
    """Return a recent valid fix only when geotagging was explicitly enabled."""
    if not enabled:
        return {"status": "not_requested", "latitude": None, "longitude": None}
    try:
        # current_fix enforces the existing protected-actions location gate and
        # uses the brokered GNSS owner rather than opening a serial port here.
        from .gnss_location import current_fix, valid_lat_lon
        fix = current_fix(authorized=True, prompt=False)
    except Exception:
        fix = None
        valid_lat_lon = lambda lat, lon: False  # type: ignore[assignment]
    if fix is None:
        return {"status": "unknown", "latitude": None, "longitude": None, "reason": "no authorized recent GNSS fix"}
    latitude = getattr(fix, "latitude", None)
    longitude = getattr(fix, "longitude", None)
    if not valid_lat_lon(latitude, longitude):
        return {"status": "unknown", "latitude": None, "longitude": None, "reason": "invalid GNSS coordinates"}
    captured_at = str(getattr(fix, "captured_at_utc", "") or "")
    try:
        stamp = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - stamp.astimezone(timezone.utc)).total_seconds()
    except (ValueError, TypeError):
        return {"status": "unknown", "latitude": None, "longitude": None, "reason": "GNSS fix timestamp missing or invalid"}
    if age < -5 or age > LOCATION_MAX_AGE_SECONDS:
        return {"status": "unknown", "latitude": None, "longitude": None, "reason": "GNSS fix is stale"}
    return {
        "status": "fix",
        "latitude": float(latitude),
        "longitude": float(longitude),
        "altitude_meters": getattr(fix, "altitude_meters", None),
        "accuracy_meters": getattr(fix, "accuracy_meters", None),
        "source": str(getattr(fix, "source", "authorized_gnss")),
        "captured_at_utc": captured_at,
        "age_seconds": round(max(0.0, age), 1),
    }


def _is_camera_like(label: str) -> bool:
    normalized = " ".join(label.casefold().replace("_", " ").replace("-", " ").split())
    return normalized in CAMERA_LIKE_LABELS or (
        "camera" in normalized and any(token in normalized for token in ("security", "surveillance", "traffic", "cctv", "dome", "bullet", "license"))
    )


def _camera_backend_name() -> str:
    """Resolve the capture backend without changing MCU or display services.

    auto prefers the CSI/Picamera2 stack when installed; otherwise it uses
    OpenCV UVC. An explicitly selected backend never silently switches.
    """
    requested = os.getenv("KOALABYTE_VISION_CAMERA_BACKEND", "auto").strip().lower()
    if requested not in {"auto", "picamera2", "uvc"}:
        raise ValueError("KOALABYTE_VISION_CAMERA_BACKEND must be auto, picamera2, or uvc")
    if requested != "auto":
        return requested
    try:
        import picamera2  # type: ignore  # noqa: F401
        return "picamera2"
    except Exception:
        return "uvc"


def _capture_frame(*, camera_index: int = 0, width: int = 1280, height: int = 720):
    """Capture exactly one frame and return (OpenCV BGR frame, backend label).

    Camera capture is scoped to this call. No preview loop or background
    capture is started, and the camera object is always released/stopped.
    """
    backend = _camera_backend_name()
    if backend == "picamera2":
        try:
            import numpy as np
            from picamera2 import Picamera2  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "Picamera2 backend selected but Picamera2/NumPy is unavailable. "
                "Install python3-picamera2 and use the system Python, or select uvc."
            ) from exc
        camera = None
        try:
            camera = Picamera2(camera_num=int(camera_index))
            config = camera.create_still_configuration(
                main={"size": (int(width), int(height)), "format": "BGR888"}
            )
            camera.configure(config)
            camera.start()
            # Sensor startup can take a moment; capture_array returns one frame.
            frame = camera.capture_array("main")
            if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
                raise RuntimeError("Picamera2 opened but did not return a frame.")
            return frame, "picamera2"
        except Exception as exc:
            if isinstance(exc, RuntimeError) and "did not return a frame" in str(exc):
                raise
            raise RuntimeError(f"Picamera2 camera {camera_index} capture failed: {exc}") from exc
        finally:
            if camera is not None:
                try:
                    camera.stop()
                except Exception:
                    pass
                try:
                    camera.close()
                except Exception:
                    pass

    try:
        import cv2  # type: ignore
    except Exception as exc:
        raise RuntimeError("OpenCV is not installed; see requirements-vision.txt.") from exc
    capture = cv2.VideoCapture(int(camera_index))
    try:
        if not capture.isOpened():
            raise RuntimeError(f"UVC camera index {camera_index} could not be opened.")
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, int(width))
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, int(height))
        ok, frame = capture.read()
        if not ok or frame is None:
            raise RuntimeError("UVC camera opened but did not return a frame.")
        return frame, "uvc"
    finally:
        capture.release()


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
    geotag: bool = False,
    session_id: str = "",
    event_id: str = "",
    observation_ref: str = "",
    camera_spotting: bool = False,
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
    frame, camera_backend = _capture_frame(
        camera_index=camera_index, width=width, height=height
    )

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
            if label.casefold() in {"face", "license plate", "licence plate"}:
                continue
            detections.append({
                "label": label,
                "confidence": round(float(box.conf[0].item()), 4),
                "bbox_xyxy": [int(value) for value in box.xyxy[0].tolist()],
                "camera_like_candidate": bool(camera_spotting and _is_camera_like(label)),
                "verification": "unverified model suggestion" if camera_spotting and _is_camera_like(label) else None,
            })

    now = datetime.now(timezone.utc)
    timestamp = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    effective_event_id = event_id.strip() or f"vision-{now.strftime('%Y%m%dT%H%M%SZ')}"
    location = _location_context(geotag)
    event: dict[str, Any] = {
        "status": "ULTRA_VISION_CAPTURE_COMPLETE",
        "event_id": effective_event_id,
        "session_id": session_id.strip() or None,
        "observed_at_utc": timestamp,
        "camera_index": int(camera_index),
        "camera_backend": camera_backend,
        "frame_width": int(frame.shape[1]),
        "frame_height": int(frame.shape[0]),
        "inference_device": "cpu",
        "model_file": str(Path(model_path).expanduser().resolve()),
        "confidence_threshold": confidence,
        "site_label": site_label.strip(),
        "location": location,
        "observation_reference": observation_ref.strip() or None,
        "observation_link_semantics": (
            "operator-supplied contextual reference only; does not prove an observed Wi-Fi/BLE device is located at this photo or GNSS point"
            if observation_ref.strip() else None
        ),
        "detections": detections,
        "camera_like_candidates": [item for item in detections if item["camera_like_candidate"]],
        "privacy_scope": "single operator-triggered frame; local CPU inference; no identity recognition, RF scan, or automatic device correlation",
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



def observe_camera_with_companion(
    question: str,
    *,
    camera_index: int = 0,
    host: str | None = None,
    model: str | None = None,
    width: int = 1280,
    height: int = 720,
) -> dict[str, Any]:
    """Capture one requested frame and ask a local Ollama vision model about it."""
    import base64
    from urllib.parse import urlparse

    import httpx

    ai_mode = os.getenv("KILLERKOALA_AI_MODE", "local").strip().lower()
    if ai_mode == "online":
        online_vision_enabled = os.getenv("KILLERKOALA_ONLINE_VISION_ENABLED", "false").strip().lower()
        if online_vision_enabled not in {"1", "true", "yes", "on"}:
            raise RuntimeError(
                "Online camera upload is disabled. Set KILLERKOALA_ONLINE_VISION_ENABLED=true "
                "only if you consent to sending each explicitly requested still frame to Ollama Cloud."
            )
        vision_model = (model or os.getenv("KILLERKOALA_ONLINE_VISION_MODEL", "") or os.getenv("KILLERKOALA_VISION_MODEL", "")).strip()
        ollama_host = "https://ollama.com"
        api_key = os.getenv("OLLAMA_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("Online camera vision needs OLLAMA_API_KEY in the private environment file.")
        headers = {"Authorization": f"Bearer {api_key}"}
    elif ai_mode == "local":
        vision_model = (model or os.getenv("KILLERKOALA_VISION_MODEL", "")).strip()
        ollama_host = (host or os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")).strip().rstrip("/")
        headers = {}
    else:
        raise RuntimeError("KILLERKOALA_AI_MODE must be 'local' or 'online'.")
    parsed_host = urlparse(ollama_host)
    if ai_mode == "local":
        local_hosts = {"localhost", "127.0.0.1", "::1"}
        if parsed_host.scheme != "http" or parsed_host.hostname not in local_hosts:
            raise RuntimeError("Local camera vision requires a loopback Ollama endpoint.")
        if vision_model.lower().endswith(":cloud"):
            raise RuntimeError("Local camera vision requires a downloaded Ollama model.")
    elif ollama_host != "https://ollama.com":
        raise RuntimeError("Online camera vision supports only https://ollama.com.")
    if not vision_model:
        raise RuntimeError(
            "KillerKoala vision is not configured. Set KILLERKOALA_VISION_MODEL "
            "to an installed Ollama vision model before asking me to look through the camera."
        )
    try:
        import cv2  # type: ignore
    except Exception as exc:
        raise RuntimeError("Camera vision dependencies are missing; install requirements-vision.txt.") from exc

    frame, camera_backend = _capture_frame(
        camera_index=camera_index, width=width, height=height
    )
    encoded_ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
    if not encoded_ok:
        raise RuntimeError("The camera frame could not be encoded for vision.")
    image_b64 = base64.b64encode(encoded.tobytes()).decode("ascii")
    frame_shape = {"width": int(frame.shape[1]), "height": int(frame.shape[0])}

    prompt = (
        "You are KillerKoala's visual perception module. Describe only visible, image-grounded details "
        "and answer the user's request: " + " ".join(str(question).split())[:600]
        + "\nBe clear about uncertainty and low image quality. Do not identify a person, infer a person's identity, "
        "track anyone, read license plates, or claim a device make/model/owner/function unless the image supports "
        "the category. For camera-like objects, say it is a possible camera and needs human verification. "
        "Do not infer Wi-Fi/Bluetooth device locations from this image. Keep the answer concise and suitable for speech."
    )
    try:
        with httpx.Client(timeout=float(os.getenv("KILLERKOALA_VISION_TIMEOUT_SECONDS", "90"))) as client:
            response = client.post(
                f"{ollama_host}/api/generate",
                headers=headers,
                json={
                    "model": vision_model,
                    "prompt": prompt,
                    "images": [image_b64],
                    "stream": False,
                    "options": {"num_predict": 160, "temperature": 0.2},
                },
            )
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        raise RuntimeError(f"Ollama vision request failed ({vision_model}, mode={ai_mode}): {exc}") from exc

    answer = " ".join(str(data.get("response", "")).split()).strip()
    if not answer:
        raise RuntimeError("The local vision model returned no description.")
    return {
        "status": "KILLERKOALA_VISION_RESPONSE_READY",
        "answer": answer[:1800],
        "model": vision_model,
        "camera_index": int(camera_index),
        "camera_backend": camera_backend,
        "frame": frame_shape,
        "captured_at_utc": _utc_now(),
        "saved_to_disk": False,
        "transport": "local_ollama",
        "continuous_stream": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Optional local-only KoalaByte Blue Ultra Pi 5 camera")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Check optional camera and inference dependencies")
    capture = sub.add_parser("capture", help="Capture one frame and run local object detection")
    capture.add_argument("--camera-index", type=int, default=0)
    capture.add_argument("--model", default=DEFAULT_MODEL, help="Path to an already-downloaded local model file")
    capture.add_argument("--confidence", type=float, default=0.45)
    capture.add_argument("--width", type=int, default=1280)
    capture.add_argument("--height", type=int, default=720)
    capture.add_argument("--site-label", default="", help="Optional operator-entered site label")
    capture.add_argument("--save-frame", action="store_true", help="Explicitly save the captured image locally")
    capture.add_argument("--record", action="store_true", help="Explicitly append event/detection metadata to local JSONL")
    capture.add_argument("--geotag", action="store_true", help="Attach a valid GNSS fix no older than 120 seconds; uses the protected location gate")
    capture.add_argument("--session-id", default="", help="Optional Kruisin/session identifier supplied by the operator")
    capture.add_argument("--event-id", default="", help="Optional event identifier supplied by the operator")
    capture.add_argument("--observation-ref", default="", help="Optional operator-supplied survey row/event reference; no radio identifiers are imported")
    capture.add_argument("--camera-spotting", action="store_true", help="Flag generic camera-like model detections for manual verification")
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
            geotag=args.geotag,
            session_id=args.session_id,
            event_id=args.event_id,
            observation_ref=args.observation_ref,
            camera_spotting=args.camera_spotting,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "ULTRA_VISION_ERROR", "error": str(exc)}, indent=2), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
