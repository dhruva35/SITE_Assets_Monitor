"""
SITE Assets Monitor — Web HITL Enrollment Server
Phase 1: Browser-based Human-in-the-Loop Asset Registration

Run:
    python -m uvicorn web_ui.server:app --reload --port 8000 --app-dir .
    # Then open http://localhost:8000

Accepts:
    --video / env var HITL_VIDEO_PATH  (set before launching uvicorn)
"""

import os
import sys
import json
import base64
import zipfile
import argparse
import threading
from io import BytesIO
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Project root
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.image_quality import ImageQualityChecker
from src.reid_engine import ReIDEngine
from src.reference_store import ReferenceStore

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REF_IMAGES_DIR  = PROJECT_ROOT / "data" / "reference_images"
YOLO_IMAGES_DIR = PROJECT_ROOT / "data" / "datasets" / "containers" / "images"
YOLO_LABELS_DIR = PROJECT_ROOT / "data" / "datasets" / "containers" / "labels"
LOG_FILE        = PROJECT_ROOT / "data" / "enrollment_log.json"

for _d in [REF_IMAGES_DIR, YOLO_IMAGES_DIR, YOLO_LABELS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Lazy-load from hitl_enrollment.py (reuse ContainerProposer without cv window)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from hitl_enrollment import ContainerProposer  # noqa: E402

# ---------------------------------------------------------------------------
# App state (shared, protected by a lock for frame access)
# ---------------------------------------------------------------------------
class AppState:
    def __init__(self):
        self.lock           = threading.Lock()
        self.cap            = None
        self.video_path     = None
        self.total_frames   = 0
        self.fps            = 10.0
        self.width          = 0
        self.height         = 0
        self.frame_cache    = {}   # frame_idx -> JPEG bytes
        self.proposals_cache= {}   # frame_idx -> list[dict]

        self.quality_checker  = ImageQualityChecker()
        self.reid_engine      = ReIDEngine("config/reid_config.yaml")
        self.reference_store  = ReferenceStore("config/reid_config.yaml")
        self.proposer         = ContainerProposer()

        self.session_enrolled = []  # records for this session

    def load_video(self, path: str):
        with self.lock:
            if self.cap:
                self.cap.release()
            self.cap = cv2.VideoCapture(path)
            if not self.cap.isOpened():
                raise RuntimeError(f"Cannot open video: {path}")
            self.video_path   = Path(path)
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps          = self.cap.get(cv2.CAP_PROP_FPS) or 10.0
            self.width        = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height       = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.frame_cache.clear()
            self.proposals_cache.clear()
            print(f"[WebUI] Video loaded: {self.video_path.name}  "
                  f"{self.width}x{self.height} @ {self.fps:.1f}fps  "
                  f"({self.total_frames} frames)")

    def read_frame(self, frame_idx: int) -> Optional[np.ndarray]:
        """Read a frame by index (thread-safe)."""
        with self.lock:
            if self.cap is None:
                return None
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = self.cap.read()
            return frame if ret else None

    def frame_to_jpeg(self, frame: np.ndarray, quality: int = 80) -> bytes:
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return buf.tobytes()

    def get_proposals(self, frame_idx: int) -> list:
        if frame_idx in self.proposals_cache:
            return self.proposals_cache[frame_idx]
        frame = self.read_frame(frame_idx)
        if frame is None:
            return []
        raw = self.proposer.propose(frame)  # list[(x1,y1,x2,y2,tag)]
        result = [{"x1": int(c[0]), "y1": int(c[1]), "x2": int(c[2]), "y2": int(c[3]),
                   "tag": c[4]} for c in raw]
        self.proposals_cache[frame_idx] = result
        return result


STATE = AppState()

# ---------------------------------------------------------------------------
# Determine video path
# ---------------------------------------------------------------------------
_default_video = Path(r"C:\Users\GANGARI DHRUVAVEER\Downloads\Phase1.mp4")
_video_env = os.environ.get("HITL_VIDEO_PATH", "")

if _video_env and Path(_video_env).exists():
    STATE.load_video(_video_env)
    print(f"[WebUI] Auto-loaded video from env: {_video_env}")
elif _default_video.exists():
    STATE.load_video(str(_default_video))
    print(f"[WebUI] Auto-loaded default video: {_default_video}")
else:
    print("[WebUI] No video loaded yet — POST /api/video/load to set one")

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="SITE Assets Monitor — HITL Web UI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
_STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Root — serve the HTML app
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = _STATIC_DIR / "index.html"
    return html_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Video info
# ---------------------------------------------------------------------------
@app.get("/api/video/info")
async def video_info():
    if STATE.cap is None:
        return {"loaded": False}
    return {
        "loaded"      : True,
        "name"        : STATE.video_path.name if STATE.video_path else "unknown",
        "total_frames": STATE.total_frames,
        "fps"         : STATE.fps,
        "width"       : STATE.width,
        "height"      : STATE.height,
        "duration_s"  : round(STATE.total_frames / max(1, STATE.fps), 2),
    }


class LoadVideoRequest(BaseModel):
    path: str

@app.post("/api/video/load")
async def load_video(req: LoadVideoRequest):
    raw_path = req.path.strip().strip('"').strip("'")
    target_path = Path(raw_path)

    # If relative, check common locations
    if not target_path.exists():
        candidates = [
            PROJECT_ROOT / target_path,
            Path.home() / "Downloads" / target_path,
            Path.home() / "Downloads" / target_path.name,
        ]
        for c in candidates:
            if c.exists():
                target_path = c
                break

    if not target_path.exists():
        raise HTTPException(400, f"File not found: {raw_path}")
    try:
        STATE.load_video(str(target_path))
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "message": f"Loaded {target_path.name}"}


# ---------------------------------------------------------------------------
# Frame endpoint — returns JPEG frame (optionally with proposals drawn)
# ---------------------------------------------------------------------------
@app.get("/api/frame/{frame_idx}")
async def get_frame(frame_idx: int, draw_proposals: bool = False):
    frame = STATE.read_frame(frame_idx)
    if frame is None:
        raise HTTPException(404, f"Frame {frame_idx} not available")

    if draw_proposals:
        proposals = STATE.get_proposals(frame_idx)
        for p in proposals:
            cv2.rectangle(frame, (p["x1"], p["y1"]), (p["x2"], p["y2"]),
                          (0, 215, 255), 2)   # BGR gold
            cv2.putText(frame, p["tag"], (p["x1"], max(18, p["y1"] - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 215, 255), 2, cv2.LINE_AA)

    jpeg = STATE.frame_to_jpeg(frame)
    return StreamingResponse(BytesIO(jpeg), media_type="image/jpeg")


# ---------------------------------------------------------------------------
# Proposals endpoint
# ---------------------------------------------------------------------------
@app.get("/api/proposals/{frame_idx}")
async def get_proposals(frame_idx: int):
    if STATE.cap is None:
        raise HTTPException(400, "No video loaded")
    proposals = STATE.get_proposals(frame_idx)
    return {"frame_idx": frame_idx, "proposals": proposals}


# ---------------------------------------------------------------------------
# Enroll endpoint
# ---------------------------------------------------------------------------
class EnrollRequest(BaseModel):
    frame_idx: int
    bbox: List[int]      # [x1, y1, x2, y2]
    asset_id: str
    class_name: str = "container"

@app.post("/api/enroll")
async def enroll(req: EnrollRequest):
    if STATE.cap is None:
        raise HTTPException(400, "No video loaded")

    frame = STATE.read_frame(req.frame_idx)
    if frame is None:
        raise HTTPException(404, f"Frame {req.frame_idx} not available")

    x1, y1, x2, y2 = req.bbox
    h, w = frame.shape[:2]
    x1 = max(0, min(x1, w)); x2 = max(0, min(x2, w))
    y1 = max(0, min(y1, h)); y2 = max(0, min(y2, h))

    if (x2 - x1) < 20 or (y2 - y1) < 20:
        raise HTTPException(400, "Bounding box too small (min 20x20 px)")

    crop = frame[y1:y2, x1:x2].copy()
    asset_id = req.asset_id.strip().upper()

    # Quality check
    quality_info = STATE.quality_checker.check(crop)

    # Extract embedding
    embedding = STATE.reid_engine.extract_embedding(crop)
    if embedding is None:
        raise HTTPException(500, f"Failed to extract embedding for '{asset_id}'")

    # Add to reference store
    success = STATE.reference_store.add_reference(
        asset_id=asset_id,
        class_name=req.class_name,
        embedding=embedding,
        auto_save=True,
    )
    if not success:
        raise HTTPException(500, f"ReferenceStore rejected '{asset_id}'")

    # Save reference image
    asset_dir = REF_IMAGES_DIR / asset_id
    asset_dir.mkdir(parents=True, exist_ok=True)
    ref_idx      = len(list(asset_dir.glob("*.jpg"))) + 1
    ref_img_path = asset_dir / f"ref_{ref_idx:03d}.jpg"
    cv2.imwrite(str(ref_img_path), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])

    # Save YOLO sample
    sample_name     = f"frame_{req.frame_idx:06d}"
    frame_save_path = YOLO_IMAGES_DIR / f"{sample_name}.jpg"
    cv2.imwrite(str(frame_save_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

    bx_c = ((x1 + x2) / 2.0) / w
    by_c = ((y1 + y2) / 2.0) / h
    bw   = (x2 - x1) / w
    bh   = (y2 - y1) / h
    label_path = YOLO_LABELS_DIR / f"{sample_name}.txt"
    with open(label_path, "a") as lf:
        lf.write(f"0 {bx_c:.6f} {by_c:.6f} {bw:.6f} {bh:.6f}\n")

    # Audit log
    record = {
        "asset_id"     : asset_id,
        "class_name"   : req.class_name,
        "timestamp"    : datetime.now(timezone.utc).isoformat(),
        "frame_idx"    : req.frame_idx,
        "timestamp_sec": round(req.frame_idx / max(1, STATE.fps), 2),
        "bbox_xyxy"    : [int(x1), int(y1), int(x2), int(y2)],
        "embedding_dim": int(len(embedding)),
        "ref_image"    : str(ref_img_path.relative_to(PROJECT_ROOT)),
        "quality"      : quality_info.get("quality", "UNKNOWN"),
        "source"       : "web_ui",
    }
    STATE.session_enrolled.append(record)
    _append_to_log(record)

    view_num = ref_idx
    gallery  = STATE.reference_store.list_assets()

    return {
        "ok"          : True,
        "asset_id"    : asset_id,
        "view_num"    : view_num,
        "total_assets": len(gallery),
        "quality"     : quality_info.get("quality", "UNKNOWN"),
        "blur_score"  : round(quality_info.get("blur_score", 0), 1),
        "message"     : f"✓ '{asset_id}' enrolled (view #{view_num}, gallery: {len(gallery)} assets)",
    }


def _append_to_log(record: dict):
    existing = []
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, "r") as f:
                existing = json.load(f)
        except Exception:
            existing = []
    existing.append(record)
    with open(LOG_FILE, "w") as f:
        json.dump(existing, f, indent=2)


# ---------------------------------------------------------------------------
# Gallery endpoints
# ---------------------------------------------------------------------------
@app.get("/api/gallery")
async def gallery():
    assets_raw = STATE.reference_store.list_assets()
    result = []
    for entry in assets_raw:
        aid = entry["asset_id"] if isinstance(entry, dict) else str(entry)
        asset_dir = REF_IMAGES_DIR / aid
        crops = sorted(asset_dir.glob("*.jpg")) if asset_dir.exists() else []
        view_count = len(crops)

        # Latest thumbnail as base64
        thumb_b64 = None
        if crops:
            img = cv2.imread(str(crops[-1]))
            if img is not None:
                h, w = img.shape[:2]
                scale = 80 / max(h, w)
                thumb = cv2.resize(img, (max(1, int(w * scale)), max(1, int(h * scale))))
                _, buf = cv2.imencode(".jpg", thumb, [cv2.IMWRITE_JPEG_QUALITY, 70])
                thumb_b64 = base64.b64encode(buf.tobytes()).decode()

        result.append({
            "asset_id"   : aid,
            "view_count" : view_count,
            "thumbnail"  : thumb_b64,
        })

    result.sort(key=lambda x: x["asset_id"])
    return {"assets": result, "total": len(result)}


@app.get("/api/gallery/thumbnail/{asset_id}")
async def gallery_thumbnail(asset_id: str):
    asset_dir = REF_IMAGES_DIR / asset_id.upper()
    if not asset_dir.exists():
        raise HTTPException(404, f"No images for {asset_id}")
    crops = sorted(asset_dir.glob("*.jpg"))
    if not crops:
        raise HTTPException(404, f"No images for {asset_id}")
    return FileResponse(str(crops[-1]), media_type="image/jpeg")


# ---------------------------------------------------------------------------
# Quality check (crop from bbox)
# ---------------------------------------------------------------------------
class QualityRequest(BaseModel):
    frame_idx: int
    bbox: List[int]  # [x1, y1, x2, y2]

@app.post("/api/quality")
async def check_quality(req: QualityRequest):
    frame = STATE.read_frame(req.frame_idx)
    if frame is None:
        raise HTTPException(404, f"Frame {req.frame_idx} not found")
    x1, y1, x2, y2 = req.bbox
    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        raise HTTPException(400, "Empty crop")
    info = STATE.quality_checker.check(crop)
    return info


# ---------------------------------------------------------------------------
# Export training zip
# ---------------------------------------------------------------------------
@app.post("/api/export")
async def export_training():
    ds_dir = PROJECT_ROOT / "data" / "datasets" / "containers"
    if not ds_dir.exists():
        raise HTTPException(400, "No YOLO dataset directory found")

    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = PROJECT_ROOT / "data" / f"training_export_{ts}.zip"

    n_imgs = len(list((ds_dir / "images").glob("*.jpg")))
    n_lbl  = len(list((ds_dir / "labels").glob("*.txt")))

    info = {
        "created"       : datetime.now(timezone.utc).isoformat(),
        "video_source"  : STATE.video_path.name if STATE.video_path else "unknown",
        "num_images"    : n_imgs,
        "num_labels"    : n_lbl,
        "classes"       : ["container"],
        "format"        : "YOLOv8",
        "enrolled_ids"  : [
            (e["asset_id"] if isinstance(e, dict) else str(e))
            for e in STATE.reference_store.list_assets()
        ],
    }
    info_path = ds_dir / "dataset_info.json"
    with open(info_path, "w") as f:
        json.dump(info, f, indent=2)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fpath in ds_dir.rglob("*"):
            if fpath.is_file():
                zf.write(fpath, fpath.relative_to(PROJECT_ROOT / "data"))

    size_mb = zip_path.stat().st_size / 1024 / 1024
    return {
        "ok"      : True,
        "zip_path": str(zip_path),
        "size_mb" : round(size_mb, 2),
        "n_images": n_imgs,
        "n_labels": n_lbl,
        "message" : f"✓ Training zip exported: {zip_path.name} ({size_mb:.1f} MB)",
    }


# ---------------------------------------------------------------------------
# Session summary
# ---------------------------------------------------------------------------
@app.get("/api/session")
async def session_summary():
    all_assets = STATE.reference_store.list_assets()
    return {
        "total_enrolled_assets" : len(all_assets),
        "session_enrollments"   : len(STATE.session_enrolled),
        "session_records"       : STATE.session_enrolled,
        "video"                 : STATE.video_path.name if STATE.video_path else None,
    }


# ---------------------------------------------------------------------------
# WebSocket — stream frames as MJPEG for play mode
# ---------------------------------------------------------------------------
@app.websocket("/ws/stream")
async def websocket_stream(ws: WebSocket):
    import asyncio
    await ws.accept()
    try:
        # Client sends JSON: {"action": "play"|"pause"|"seek", "frame_idx": N, "speed": 1.0}
        frame_idx = 0
        playing   = False
        speed     = 1.0

        while True:
            # Non-blocking check for incoming message
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=0.01)
                msg  = json.loads(data)
                action = msg.get("action", "")
                if action == "play":
                    playing   = True
                    speed     = float(msg.get("speed", 1.0))
                    frame_idx = int(msg.get("frame_idx", frame_idx))
                elif action == "pause":
                    playing = False
                elif action == "seek":
                    frame_idx = int(msg.get("frame_idx", frame_idx))
                    playing   = False
            except asyncio.TimeoutError:
                pass
            except Exception:
                break

            if playing and STATE.cap is not None:
                frame = STATE.read_frame(frame_idx)
                if frame is None:
                    playing = False
                    await ws.send_text(json.dumps({"event": "end"}))
                    continue

                jpeg = STATE.frame_to_jpeg(frame, quality=65)
                b64  = base64.b64encode(jpeg).decode()
                await ws.send_text(json.dumps({
                    "event"      : "frame",
                    "frame_idx"  : frame_idx,
                    "total"      : STATE.total_frames,
                    "jpeg_b64"   : b64,
                }))
                frame_idx = min(frame_idx + 1, STATE.total_frames - 1)
                delay = max(0.016, (1.0 / max(0.1, STATE.fps)) / speed)
                await asyncio.sleep(delay)
            else:
                await asyncio.sleep(0.05)

    except WebSocketDisconnect:
        pass


# ---------------------------------------------------------------------------
# Dev entry point (for direct python run)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument("--video",  "-v", default="", help="Path to video file")
    parser.add_argument("--port",   "-p", type=int, default=8000)
    parser.add_argument("--reload",       action="store_true")
    args = parser.parse_args()

    if args.video and Path(args.video).exists():
        STATE.load_video(args.video)

    uvicorn.run("web_ui.server:app", host="0.0.0.0", port=args.port,
                reload=args.reload, app_dir=str(PROJECT_ROOT))

