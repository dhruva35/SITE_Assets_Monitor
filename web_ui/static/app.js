/**
 * SITE Assets Monitor — HITL Web UI  •  app.js
 * Handles: video frame display, bbox drawing/proposals, enrollment, gallery, WS streaming
 */

"use strict";

// ============================================================
// State
// ============================================================
const S = {
  frameIdx:       0,
  totalFrames:    0,
  fps:            10,
  width:          640,
  height:         360,
  playing:        false,
  speed:          1.0,
  proposals:      [],       // [{x1,y1,x2,y2,tag}, ...]
  selectedPropIdx: -1,       // index into proposals
  activeBbox:     null,     // {x1,y1,x2,y2} — currently active box (manual or proposal)
  drawingBbox:    null,     // while mouse is dragging
  showProposals:  true,
  lastEnrolledId: null,
  videoLoaded:    false,
  ws:             null,
  frameLoadInProgress: false,
};

// ============================================================
// DOM refs
// ============================================================
const D = {
  canvas:          document.getElementById("video-canvas"),
  bboxSvg:         document.getElementById("bbox-svg"),
  cropCanvas:      document.getElementById("crop-canvas"),
  cropPlaceholder: document.getElementById("crop-placeholder"),
  noPH:            document.getElementById("no-video-placeholder"),
  scrubber:        document.getElementById("scrubber"),
  frameCur:        document.getElementById("frame-current"),
  frameTotal:      document.getElementById("frame-total"),
  timeCur:         document.getElementById("time-current"),
  timeDuration:    document.getElementById("time-duration"),
  btnPlay:         document.getElementById("btn-play"),
  btnPrev5:        document.getElementById("btn-prev5"),
  btnNext5:        document.getElementById("btn-next5"),
  btnPrev30:       document.getElementById("btn-prev30"),
  btnNext30:       document.getElementById("btn-next30"),
  speedSelect:     document.getElementById("speed-select"),
  modeBadge:       document.getElementById("mode-badge"),
  candCount:       document.getElementById("cand-count"),
  toggleProposals: document.getElementById("toggle-proposals"),
  bboxCoords:      document.getElementById("bbox-coords"),
  bboxInfo:        document.getElementById("bbox-info"),
  proposalList:    document.getElementById("proposal-list"),
  qaGrid:          document.getElementById("qa-grid"),
  galleryGrid:     document.getElementById("gallery-grid"),
  galleryTotal:    document.getElementById("gallery-total"),
  newIdInput:      document.getElementById("new-id-input"),
  btnEnrollNew:    document.getElementById("btn-enroll-new"),
  btnExport:       document.getElementById("btn-export"),
  btnExportBottom: document.getElementById("btn-export-bottom"),
  btnLoadVideo:    document.getElementById("btn-load-video"),
  exportInfo:      document.getElementById("export-info"),
  toast:           document.getElementById("toast"),
  modalVideo:      document.getElementById("modal-video"),
  modalVideoPath:  document.getElementById("modal-video-path"),
  btnModalCancel:  document.getElementById("btn-modal-cancel"),
  btnModalLoad:    document.getElementById("btn-modal-load"),
  hdrVideoName:    document.getElementById("hdr-video-name"),
  hdrGalleryCount: document.getElementById("hdr-gallery-count"),
  hdrSessionCount: document.getElementById("hdr-session-count"),
  qStatus:         document.getElementById("q-status"),
  qBlurBar:        document.getElementById("q-blur-bar"),
  qBlurVal:        document.getElementById("q-blur-val"),
  qBriBar:         document.getElementById("q-bri-bar"),
  qBriVal:         document.getElementById("q-bri-val"),
};

// ============================================================
// Toast
// ============================================================
let toastTimer = null;
function showToast(msg, type = "info", duration = 3500) {
  D.toast.textContent = msg;
  D.toast.className = `toast ${type}`;
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { D.toast.classList.add("hidden"); }, duration);
}

// ============================================================
// API helpers
// ============================================================
async function api(method, path, body = null) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(path, opts);
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error(err.detail || r.statusText);
  }
  return r.json();
}

// ============================================================
// Init — load video info on page load
// ============================================================
(async function init() {
  try {
    const info = await api("GET", "/api/video/info");
    if (info.loaded) {
      applyVideoInfo(info);
      await loadFrame(0);
      await fetchGallery();
    }
  } catch (e) {
    console.warn("Init:", e);
  }
  bindEvents();
})();

function applyVideoInfo(info) {
  S.videoLoaded  = true;
  S.totalFrames  = info.total_frames;
  S.fps          = info.fps;
  S.width        = info.width;
  S.height       = info.height;
  S.frameIdx     = 0;

  D.scrubber.max = info.total_frames - 1;
  D.frameTotal.textContent = `/ ${info.total_frames}`;
  D.timeDuration.textContent = `/ ${info.duration_s.toFixed(1)}s`;
  D.hdrVideoName.textContent = info.name;
  D.hdrVideoName.classList.remove("hdr-pill-dim");
  D.noPH.style.display = "none";

  // Resize canvas to match aspect ratio
  D.canvas.style.aspectRatio = `${info.width} / ${info.height}`;

  showToast(`Video loaded: ${info.name}  (${info.total_frames} frames @ ${info.fps.toFixed(1)} fps)`, "info");
}

// ============================================================
// Frame loading
// ============================================================
async function loadFrame(idx, withProposals = null) {
  if (!S.videoLoaded || S.frameLoadInProgress) return;
  S.frameLoadInProgress = true;

  idx = Math.max(0, Math.min(idx, S.totalFrames - 1));
  S.frameIdx = idx;

  const show = withProposals !== null ? withProposals : false;
  const url  = `/api/frame/${idx}?draw_proposals=false&t=${Date.now()}`;

  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const ctx = D.canvas.getContext("2d");
      D.canvas.width  = img.naturalWidth  || S.width;
      D.canvas.height = img.naturalHeight || S.height;
      ctx.drawImage(img, 0, 0);
      updateScrubber();
      S.frameLoadInProgress = false;
      resolve();
    };
    img.onerror = () => { S.frameLoadInProgress = false; resolve(); };
    img.src = url;
  });
}

function updateScrubber() {
  D.scrubber.value          = S.frameIdx;
  D.frameCur.textContent    = S.frameIdx;
  const sec = S.frameIdx / S.fps;
  D.timeCur.textContent     = sec.toFixed(1) + "s";
}

// ============================================================
// Proposals
// ============================================================
async function fetchProposals(frameIdx) {
  if (!S.videoLoaded) return;
  try {
    const data = await api("GET", `/api/proposals/${frameIdx}`);
    S.proposals = data.proposals || [];
    S.selectedPropIdx = S.proposals.length > 0 ? 0 : -1;
    renderProposals();
    updateActiveBbox();
    renderProposalList();
    D.candCount.textContent = `${S.proposals.length} candidate${S.proposals.length !== 1 ? "s" : ""}`;
  } catch (e) {
    console.warn("Proposals:", e);
    S.proposals = [];
    renderProposals();
  }
}

function renderProposals() {
  // Clear existing proposal/manual rects except drawing rect
  D.bboxSvg.querySelectorAll(".bbox-proposal, .bbox-manual").forEach(el => el.remove());

  if (!S.showProposals) return;

  const cw = D.canvas.offsetWidth;
  const ch = D.canvas.offsetHeight;
  const sw = D.canvas.width  || S.width;
  const sh = D.canvas.height || S.height;
  const sx = cw / sw;
  const sy = ch / sh;

  S.proposals.forEach((p, i) => {
    const rect = makeSvgRect(
      p.x1 * sx, p.y1 * sy,
      (p.x2 - p.x1) * sx, (p.y2 - p.y1) * sy,
      "bbox-proposal" + (i === S.selectedPropIdx ? " selected" : ""),
    );
    rect.dataset.idx = i;
    rect.addEventListener("click", () => selectProposal(i));

    // Label
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", p.x1 * sx + 4);
    text.setAttribute("y", Math.max(14, p.y1 * sy - 4));
    text.setAttribute("fill", i === S.selectedPropIdx ? "#FFD700" : "#888");
    text.setAttribute("font-size", "11");
    text.setAttribute("font-family", "monospace");
    text.textContent = `[${i+1}] ${p.tag}`;
    text.style.pointerEvents = "none";

    D.bboxSvg.appendChild(rect);
    D.bboxSvg.appendChild(text);
  });

  // Manual bbox
  if (S.activeBbox && S.selectedPropIdx === -1) {
    const b = S.activeBbox;
    const rect = makeSvgRect(
      b.x1 * sx, b.y1 * sy,
      (b.x2 - b.x1) * sx, (b.y2 - b.y1) * sy,
      "bbox-manual",
    );
    D.bboxSvg.appendChild(rect);
  }
}

function makeSvgRect(x, y, w, h, cls) {
  const r = document.createElementNS("http://www.w3.org/2000/svg", "rect");
  r.setAttribute("x", x); r.setAttribute("y", y);
  r.setAttribute("width", w); r.setAttribute("height", h);
  r.setAttribute("class", cls);
  return r;
}

function selectProposal(idx) {
  S.selectedPropIdx = idx;
  S.activeBbox = idx >= 0 && idx < S.proposals.length
    ? { x1: S.proposals[idx].x1, y1: S.proposals[idx].y1,
        x2: S.proposals[idx].x2, y2: S.proposals[idx].y2 }
    : null;
  renderProposals();
  updateActiveBbox();
  renderProposalList();
  updateCropPreview();
}

function updateActiveBbox() {
  if (S.activeBbox) {
    const b = S.activeBbox;
    D.bboxCoords.textContent = `x1:${b.x1} y1:${b.y1} x2:${b.x2} y2:${b.y2}  (${b.x2-b.x1}×${b.y2-b.y1}px)`;
    D.bboxCoords.classList.remove("muted");
  } else {
    D.bboxCoords.textContent = "—";
    D.bboxCoords.classList.add("muted");
  }
}

function renderProposalList() {
  D.proposalList.innerHTML = "";
  if (S.proposals.length === 0) {
    D.proposalList.innerHTML = '<li class="proposal-empty">No proposals — navigate to a frame with assets</li>';
    return;
  }
  S.proposals.forEach((p, i) => {
    const li = document.createElement("li");
    li.className = "proposal-item" + (i === S.selectedPropIdx ? " selected" : "");
    li.innerHTML = `<span class="proposal-idx">${i+1}</span>
      <span>${p.tag}</span>
      <span class="muted" style="margin-left:auto;font-size:10px">${p.x2-p.x1}×${p.y2-p.y1}px</span>`;
    li.addEventListener("click", () => selectProposal(i));
    D.proposalList.appendChild(li);
  });
}

// ============================================================
// Crop preview in center column
// ============================================================
async function updateCropPreview() {
  const cropCanvas = document.getElementById("crop-canvas");
  const cropCtx = cropCanvas.getContext("2d");

  if (!S.activeBbox || !S.videoLoaded) {
    cropCanvas.width  = 220;
    cropCanvas.height = 160;
    cropCtx.clearRect(0, 0, 220, 160);
    D.cropPlaceholder.style.display = "block";
    resetQualityUI();
    return;
  }

  D.cropPlaceholder.style.display = "none";

  // Crop from main canvas
  const mainCtx = D.canvas.getContext("2d");
  const { x1, y1, x2, y2 } = S.activeBbox;
  const cw = x2 - x1, ch = y2 - y1;
  if (cw <= 0 || ch <= 0) return;

  // Scale to fit 220×160
  const scale  = Math.min(220 / cw, 160 / ch);
  const dw     = Math.round(cw * scale);
  const dh     = Math.round(ch * scale);
  const sx     = (D.canvas.width / (D.canvas.offsetWidth || 1));
  const sy     = (D.canvas.height / (D.canvas.offsetHeight || 1));

  cropCanvas.width  = dw;
  cropCanvas.height = dh;

  const imgData = mainCtx.getImageData(
    Math.round(x1 * sx), Math.round(y1 * sy),
    Math.round(cw * sx), Math.round(ch * sy)
  );

  // Draw scaled onto temp canvas then copy
  const tmpCanvas = document.createElement("canvas");
  tmpCanvas.width  = Math.round(cw * sx);
  tmpCanvas.height = Math.round(ch * sy);
  tmpCanvas.getContext("2d").putImageData(imgData, 0, 0);

  cropCtx.clearRect(0, 0, dw, dh);
  cropCtx.drawImage(tmpCanvas, 0, 0, dw, dh);

  // Quality check via API
  try {
    const qinfo = await api("POST", "/api/quality", {
      frame_idx: S.frameIdx,
      bbox: [x1, y1, x2, y2],
    });
    updateQualityUI(qinfo);
  } catch (_) {}
}

function resetQualityUI() {
  D.qStatus.textContent = "—";
  D.qStatus.className   = "q-badge q-unknown";
  D.qBlurBar.style.width = "0%";
  D.qBlurVal.textContent = "—";
  D.qBriBar.style.width  = "0%";
  D.qBriVal.textContent  = "—";
}

function updateQualityUI(q) {
  const qual = q.quality || "UNUSABLE";
  D.qStatus.textContent = qual;
  if (qual === "GOOD")     D.qStatus.className = "q-badge q-ok";
  else if (qual === "OK")  D.qStatus.className = "q-badge q-warn";
  else                     D.qStatus.className = "q-badge q-bad";

  const blur = Math.min(100, (q.blur_score || 0) / 10 * 100);
  D.qBlurBar.style.width = blur + "%";
  D.qBlurVal.textContent = (q.blur_score || 0).toFixed(0);

  const bri = Math.min(100, ((q.brightness || 0) / 255) * 100);
  D.qBriBar.style.width  = bri + "%";
  D.qBriVal.textContent  = (q.brightness || 0).toFixed(0);
}

// ============================================================
// Enroll
// ============================================================
async function doEnroll(assetId) {
  if (!assetId || !assetId.trim()) { showToast("Enter an asset ID first", "error"); return; }
  if (!S.activeBbox)               { showToast("Select or draw a bounding box first", "error"); return; }
  if (!S.videoLoaded)              { showToast("Load a video first", "error"); return; }

  const id  = assetId.trim().toUpperCase();
  const { x1, y1, x2, y2 } = S.activeBbox;

  try {
    const result = await api("POST", "/api/enroll", {
      frame_idx: S.frameIdx,
      bbox: [x1, y1, x2, y2],
      asset_id: id,
    });
    showToast(result.message, "success", 4000);
    S.lastEnrolledId = id;

    // Update session counter in header
    const sess = await api("GET", "/api/session");
    D.hdrSessionCount.textContent = `Session: ${sess.session_enrollments} enrollments`;

    // Clear input, refresh gallery and pills
    D.newIdInput.value = "";
    await fetchGallery();

    // Highlight the pill
    document.querySelectorAll(".qa-pill").forEach(p => {
      p.classList.toggle("last-used", p.dataset.id === id);
    });

  } catch (e) {
    showToast(`Enroll failed: ${e.message}`, "error");
  }
}

// ============================================================
// Gallery
// ============================================================
async function fetchGallery() {
  try {
    const data = await api("GET", "/api/gallery");
    renderGallery(data.assets);
    renderQAGrid(data.assets);
    D.galleryTotal.textContent = `${data.total} assets`;
    D.hdrGalleryCount.textContent = `Gallery: ${data.total} assets`;
  } catch (e) {
    console.warn("Gallery fetch:", e);
  }
}

function renderGallery(assets) {
  D.galleryGrid.innerHTML = "";
  if (!assets || assets.length === 0) {
    D.galleryGrid.innerHTML = '<div class="muted small" style="padding:8px">No assets enrolled yet</div>';
    return;
  }
  assets.forEach(a => {
    const card = document.createElement("div");
    card.className = "gallery-card";
    card.title = `${a.asset_id} — ${a.view_count} view(s)`;

    const thumb = document.createElement("img");
    thumb.className = "gallery-thumb";
    if (a.thumbnail) {
      thumb.src = `data:image/jpeg;base64,${a.thumbnail}`;
    } else {
      thumb.src = `/api/gallery/thumbnail/${a.asset_id}?t=${Date.now()}`;
    }
    thumb.onerror = () => { thumb.style.background = "#333"; thumb.alt = "?"; };

    const idLabel   = document.createElement("div");
    idLabel.className = "gallery-id";
    idLabel.textContent = a.asset_id;

    const viewLabel = document.createElement("div");
    viewLabel.className = "gallery-views";
    viewLabel.textContent = `${a.view_count} view${a.view_count !== 1 ? "s" : ""}`;

    card.appendChild(thumb);
    card.appendChild(idLabel);
    card.appendChild(viewLabel);

    // Click to auto-fill the new ID input
    card.addEventListener("click", () => {
      D.newIdInput.value = a.asset_id;
      showToast(`Selected ${a.asset_id} — click Enroll to add another view`, "info", 2500);
    });

    D.galleryGrid.appendChild(card);
  });
}

function renderQAGrid(assets) {
  D.qaGrid.innerHTML = "";
  if (!assets || assets.length === 0) {
    D.qaGrid.innerHTML = '<div class="muted small" style="padding:4px">Enroll assets to see quick-assign buttons</div>';
    return;
  }
  assets.forEach(a => {
    const pill = document.createElement("button");
    pill.className  = "qa-pill" + (a.asset_id === S.lastEnrolledId ? " last-used" : "");
    pill.textContent = a.asset_id;
    pill.dataset.id  = a.asset_id;
    pill.title       = `Quick-assign: ${a.asset_id}`;
    pill.addEventListener("click", () => doEnroll(a.asset_id));
    D.qaGrid.appendChild(pill);
  });
}

// ============================================================
// Playback — WebSocket streaming
// ============================================================
function connectWS() {
  if (S.ws && S.ws.readyState === WebSocket.OPEN) return;
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  S.ws = new WebSocket(`${protocol}://${location.host}/ws/stream`);

  S.ws.onopen = () => console.log("[WS] Connected");

  S.ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.event === "frame") {
      const img = new Image();
      img.onload = () => {
        const ctx = D.canvas.getContext("2d");
        D.canvas.width  = img.naturalWidth  || S.width;
        D.canvas.height = img.naturalHeight || S.height;
        ctx.drawImage(img, 0, 0);
        S.frameIdx = msg.frame_idx;
        updateScrubber();
        if (S.showProposals) {
          fetchProposals(S.frameIdx);  // async, don't await here
        }
      };
      img.src = "data:image/jpeg;base64," + msg.jpeg_b64;
    } else if (msg.event === "end") {
      setPlaying(false);
      showToast("End of video reached", "info");
    }
  };

  S.ws.onclose = () => {
    console.log("[WS] Disconnected");
    if (S.playing) setPlaying(false);
  };

  S.ws.onerror = (e) => console.warn("[WS] Error", e);
}

function wsSend(msg) {
  if (!S.ws || S.ws.readyState !== WebSocket.OPEN) connectWS();
  // Retry after open
  if (S.ws.readyState !== WebSocket.OPEN) {
    S.ws.addEventListener("open", () => S.ws.send(JSON.stringify(msg)), { once: true });
  } else {
    S.ws.send(JSON.stringify(msg));
  }
}

function setPlaying(val) {
  S.playing = val;
  D.btnPlay.textContent = val ? "⏸" : "▶";
  D.btnPlay.classList.toggle("playing", val);
  D.modeBadge.textContent = val ? "PLAYING" : "PAUSED";
  D.modeBadge.className = val ? "badge badge-playing" : "badge badge-paused";
}

function togglePlay() {
  if (!S.videoLoaded) { showToast("Load a video first", "error"); return; }
  connectWS();
  if (S.playing) {
    setPlaying(false);
    wsSend({ action: "pause" });
  } else {
    setPlaying(true);
    wsSend({ action: "play", frame_idx: S.frameIdx, speed: S.speed });
  }
}

// ============================================================
// Seek (manual, non-streaming)
// ============================================================
async function seekTo(idx) {
  if (!S.videoLoaded) return;
  if (S.playing) {
    setPlaying(false);
    wsSend({ action: "pause" });
  }
  await loadFrame(idx);
  await fetchProposals(idx);
  S.activeBbox = null;
  S.selectedPropIdx = S.proposals.length > 0 ? 0 : -1;
  updateActiveBbox();
  renderProposals();
  renderProposalList();
  updateCropPreview();
}

// ============================================================
// Mouse: bbox drawing on SVG
// ============================================================
let _dragStart = null;

D.bboxSvg.addEventListener("mousedown", (e) => {
  if (!S.videoLoaded) return;
  if (S.playing) return;    // only draw when paused
  if (e.button !== 0) return;

  const r   = D.bboxSvg.getBoundingClientRect();
  const x   = e.clientX - r.left;
  const y   = e.clientY - r.top;
  _dragStart = { x, y };
  e.preventDefault();
});

document.addEventListener("mousemove", (e) => {
  if (!_dragStart) return;
  const r  = D.bboxSvg.getBoundingClientRect();
  const cx = e.clientX - r.left;
  const cy = e.clientY - r.top;

  // Update / create drawing rect
  let drawRect = D.bboxSvg.querySelector(".bbox-drawing");
  if (!drawRect) {
    drawRect = makeSvgRect(0, 0, 0, 0, "bbox-drawing");
    D.bboxSvg.appendChild(drawRect);
  }
  const x1 = Math.min(_dragStart.x, cx);
  const y1 = Math.min(_dragStart.y, cy);
  const x2 = Math.max(_dragStart.x, cx);
  const y2 = Math.max(_dragStart.y, cy);
  drawRect.setAttribute("x", x1); drawRect.setAttribute("y", y1);
  drawRect.setAttribute("width", x2 - x1); drawRect.setAttribute("height", y2 - y1);
});

document.addEventListener("mouseup", (e) => {
  if (!_dragStart) return;
  const r  = D.bboxSvg.getBoundingClientRect();
  const cx = e.clientX - r.left;
  const cy = e.clientY - r.top;

  D.bboxSvg.querySelector(".bbox-drawing")?.remove();

  const svgW = D.bboxSvg.clientWidth;
  const svgH = D.bboxSvg.clientHeight;
  const imgW = D.canvas.width  || S.width;
  const imgH = D.canvas.height || S.height;

  const sx = imgW / svgW;
  const sy = imgH / svgH;

  const ix1 = Math.round(Math.min(_dragStart.x, cx) * sx);
  const iy1 = Math.round(Math.min(_dragStart.y, cy) * sy);
  const ix2 = Math.round(Math.max(_dragStart.x, cx) * sx);
  const iy2 = Math.round(Math.max(_dragStart.y, cy) * sy);

  _dragStart = null;

  if ((ix2 - ix1) < 20 || (iy2 - iy1) < 20) {
    showToast("Box too small — drag a larger area", "error", 2000);
    return;
  }

  // Set as manual bbox
  S.activeBbox      = { x1: ix1, y1: iy1, x2: ix2, y2: iy2 };
  S.selectedPropIdx = -1;
  renderProposals();
  updateActiveBbox();
  renderProposalList();
  updateCropPreview();
  showToast("Manual box drawn — now assign an ID on the right", "info", 2500);
});

// Right-click = reset
D.bboxSvg.addEventListener("contextmenu", (e) => {
  e.preventDefault();
  S.activeBbox      = null;
  S.selectedPropIdx = S.proposals.length > 0 ? 0 : -1;
  renderProposals();
  updateActiveBbox();
  renderProposalList();
  updateCropPreview();
  showToast("Reset to auto-proposals", "info", 1500);
});

// ============================================================
// Keyboard shortcuts
// ============================================================
document.addEventListener("keydown", (e) => {
  // Ignore if typing in input
  if (e.target.tagName === "INPUT") return;

  switch (e.code) {
    case "Space":        e.preventDefault(); togglePlay();         break;
    case "ArrowRight":   e.preventDefault(); seekTo(S.frameIdx + 5); break;
    case "ArrowLeft":    e.preventDefault(); seekTo(S.frameIdx - 5); break;
    case "KeyD":         seekTo(S.frameIdx + 30);                  break;
    case "KeyA":         seekTo(S.frameIdx - 30);                  break;
    case "KeyR":
      S.activeBbox      = null;
      S.selectedPropIdx = S.proposals.length > 0 ? 0 : -1;
      renderProposals(); updateActiveBbox(); renderProposalList();
      updateCropPreview();
      showToast("Reset to auto-proposals", "info", 1500);
      break;
    case "Tab":
      e.preventDefault();
      if (S.proposals.length > 0) {
        const next = (S.selectedPropIdx + 1) % S.proposals.length;
        selectProposal(next);
        showToast(`Candidate ${next+1}/${S.proposals.length}: ${S.proposals[next].tag}`, "info", 1500);
      }
      break;
  }
});

// ============================================================
// Control bindings
// ============================================================
function bindEvents() {
  D.btnPlay.addEventListener("click",   togglePlay);
  D.btnPrev5.addEventListener("click",  () => seekTo(S.frameIdx - 5));
  D.btnNext5.addEventListener("click",  () => seekTo(S.frameIdx + 5));
  D.btnPrev30.addEventListener("click", () => seekTo(S.frameIdx - 30));
  D.btnNext30.addEventListener("click", () => seekTo(S.frameIdx + 30));

  D.speedSelect.addEventListener("change", () => {
    S.speed = parseFloat(D.speedSelect.value);
    if (S.playing) wsSend({ action: "play", frame_idx: S.frameIdx, speed: S.speed });
  });

  D.scrubber.addEventListener("input", () => {
    const idx = parseInt(D.scrubber.value, 10);
    D.frameCur.textContent = idx;
    D.timeCur.textContent  = (idx / S.fps).toFixed(1) + "s";
  });
  D.scrubber.addEventListener("change", () => {
    seekTo(parseInt(D.scrubber.value, 10));
  });

  D.toggleProposals.addEventListener("change", () => {
    S.showProposals = D.toggleProposals.checked;
    renderProposals();
  });

  // Enroll new ID
  D.btnEnrollNew.addEventListener("click", () => doEnroll(D.newIdInput.value));
  D.newIdInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") doEnroll(D.newIdInput.value);
  });

  // Export
  const handleExport = async () => {
    showToast("Exporting training dataset…", "info");
    try {
      const r = await api("POST", "/api/export");
      showToast(r.message, "success", 5000);
      D.exportInfo.textContent = `${r.zip_path.split("\\").pop()} (${r.size_mb} MB)`;
    } catch (e) {
      showToast(`Export failed: ${e.message}`, "error");
    }
  };
  D.btnExport.addEventListener("click", handleExport);
  D.btnExportBottom.addEventListener("click", handleExport);

  // Load video modal
  D.btnLoadVideo.addEventListener("click", () => D.modalVideo.classList.remove("hidden"));
  D.btnModalCancel.addEventListener("click", () => D.modalVideo.classList.add("hidden"));
  D.btnModalLoad.addEventListener("click", async () => {
    const path = D.modalVideoPath.value.trim();
    if (!path) return;
    try {
      const r = await api("POST", "/api/video/load", { path });
      showToast(r.message, "success");
      D.modalVideo.classList.add("hidden");
      const info = await api("GET", "/api/video/info");
      applyVideoInfo(info);
      await loadFrame(0);
      await fetchProposals(0);
      await fetchGallery();
    } catch (e) {
      showToast(`Failed: ${e.message}`, "error");
    }
  });
  D.modalVideoPath.addEventListener("keydown", (e) => {
    if (e.key === "Enter") D.btnModalLoad.click();
  });
  D.modalVideo.addEventListener("click", (e) => {
    if (e.target === D.modalVideo) D.modalVideo.classList.add("hidden");
  });
}
