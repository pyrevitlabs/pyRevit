/*
 * Interactive 3D preview of a section or crop box for the Section Box Navigator.
 *
 * Needs lib/scene3d/gl.js (window.pyRevitScene3D) loaded first. Exposes
 * window.pyRevitSectionBoxPreview {mount, api}. The pure box and snapping math
 * lives in `api` so a headless test can exercise it without WebGL.
 *
 * Scene coordinates are Revit feet relative to the session origin, Z up. A box
 * is {origin, bx, by, bz, min, max}: a rigid transform plus local extents.
 * Faces are named by axis and side: x0 is the min-X face, x1 the max-X face.
 */
(function () {
  "use strict";

  const S3 = window.pyRevitScene3D;
  const { v3, m4, compile, decodeArray, FOV } = S3;

  const MIN_SIZE_FT = 0.05;
  const PARALLEL_SIN = Math.sin((2 * Math.PI) / 180);
  const SNAP_PIXELS = 12;
  const YAW_SNAP_RAD = (3 * Math.PI) / 180;
  const LIVE_INTERVAL_MS = 250;
  const CLIP_EPSILON_FT = 0.01;
  const AXIS_NAMES = ["x", "y", "z"];
  const BOX_EDGES = [
    [0, 1], [1, 3], [3, 2], [2, 0], [4, 5], [5, 7], [7, 6], [6, 4], [0, 4], [1, 5], [2, 6], [3, 7],
  ];
  const BOX_FACES = {
    x0: [0, 2, 6, 4], x1: [1, 3, 7, 5],
    y0: [0, 1, 5, 4], y1: [2, 3, 7, 6],
    z0: [0, 1, 3, 2], z1: [4, 5, 7, 6],
  };

  function cloneBox(box) {
    return {
      origin: box.origin.slice(), bx: box.bx.slice(), by: box.by.slice(), bz: box.bz.slice(),
      min: box.min.slice(), max: box.max.slice(),
    };
  }

  function basisOf(box) {
    return [box.bx, box.by, box.bz];
  }

  function localToWorld(box, p) {
    const w = v3.add(box.origin, v3.scale(box.bx, p[0]));
    return v3.add(v3.add(w, v3.scale(box.by, p[1])), v3.scale(box.bz, p[2]));
  }

  function worldToLocal(box, w) {
    const d = v3.sub(w, box.origin);
    return [v3.dot(d, box.bx), v3.dot(d, box.by), v3.dot(d, box.bz)];
  }

  function boxCorners(box) {
    const corners = [];
    for (let k = 0; k < 8; k++) {
      corners.push(localToWorld(box, [
        k & 1 ? box.max[0] : box.min[0],
        k & 2 ? box.max[1] : box.min[1],
        k & 4 ? box.max[2] : box.min[2],
      ]));
    }
    return corners;
  }

  function boxCenter(box) {
    return localToWorld(box, v3.scale(v3.add(box.min, box.max), 0.5));
  }

  function faceNormal(box, axis, side) {
    const b = basisOf(box)[axis];
    return side ? b.slice() : v3.scale(b, -1);
  }

  function faceCenter(box, axis, side) {
    const c = v3.scale(v3.add(box.min, box.max), 0.5);
    c[axis] = side ? box.max[axis] : box.min[axis];
    return localToWorld(box, c);
  }

  function parseFace(face) {
    return { axis: AXIS_NAMES.indexOf(face[0]), side: Number(face[1]) };
  }

  /** Parameter t of the point on the axis line p + t*d nearest to the ray o + s*r; null when parallel. */
  function closestOnAxis(p, d, o, r) {
    const w = v3.sub(p, o);
    const b = v3.dot(d, r);
    const denom = 1 - b * b;
    if (denom < 1e-9) return null;
    return (b * v3.dot(r, w) - v3.dot(d, w)) / denom;
  }

  /** Candidate face positions, as distances t along the unit normal n from the face point p. */
  function snapCandidates(p, n, targets) {
    const out = [];
    if (Math.abs(n[2]) > 0.9) {
      for (const level of targets.levels || []) {
        out.push({ t: (level.z - p[2]) / n[2], kind: "level", name: level.name });
      }
    } else if (Math.abs(n[2]) < 0.1) {
      const nl = Math.hypot(n[0], n[1]);
      const nx = n[0] / nl, ny = n[1] / nl;
      for (const grid of targets.grids || []) {
        for (const seg of grid.segs) {
          const dx = seg[2] - seg[0], dy = seg[3] - seg[1];
          const len = Math.hypot(dx, dy);
          if (len < 1e-9) continue;
          const ux = dx / len, uy = dy / len;
          const rx = seg[0] - p[0], ry = seg[1] - p[1];
          if (Math.abs(ux * nx + uy * ny) < PARALLEL_SIN) {
            out.push({ t: nx * rx + ny * ry, kind: "grid", name: grid.name });
            continue;
          }
          const det = ux * ny - nx * uy;
          if (Math.abs(det) < 1e-9) continue;
          const s = (nx * ry - ny * rx) / det;
          if (s < -0.01 || s > len + 0.01) continue;
          out.push({ t: (ux * ry - uy * rx) / det, kind: "grid", name: grid.name });
        }
      }
    }
    for (const plane of targets.planes || []) {
      const dn = v3.dot(plane.n, n);
      if (Math.abs(dn) < Math.cos((2 * Math.PI) / 180)) continue;
      out.push({ t: (plane.d - v3.dot(plane.n, p)) / dn, kind: "scope", name: plane.name });
    }
    return out;
  }

  /** The nearest candidate within tol of t, as {t, snap}; snap is null when none is close. */
  function bestSnap(t, candidates, tol) {
    let best = null;
    for (const c of candidates) {
      const gap = Math.abs(c.t - t);
      if (gap <= tol && (best === null || gap < best.gap)) best = { gap, c };
    }
    return best ? { t: best.c.t, snap: best.c } : { t, snap: null };
  }

  /** Planes (n, d with n.x = d) of the six faces of each scope box, for snapping. */
  function scopePlanes(scopeBoxes) {
    const planes = [];
    for (const scope of scopeBoxes || []) {
      for (let axis = 0; axis < 3; axis++) {
        for (let side = 0; side < 2; side++) {
          const n = faceNormal(scope.box, axis, side);
          planes.push({ name: scope.name, n, d: v3.dot(n, faceCenter(scope.box, axis, side)) });
        }
      }
    }
    return planes;
  }

  function wrapAngle(a) {
    while (a > Math.PI) a -= 2 * Math.PI;
    while (a < -Math.PI) a += 2 * Math.PI;
    return a;
  }

  /** Snap a yaw to the direction of any grid segment or its perpendicular. */
  function snapYaw(yaw, grids, tol) {
    let best = null;
    for (const grid of grids || []) {
      for (const seg of grid.segs) {
        const base = Math.atan2(seg[3] - seg[1], seg[2] - seg[0]);
        for (let k = 0; k < 4; k++) {
          const target = base + (k * Math.PI) / 2;
          const gap = Math.abs(wrapAngle(target - yaw));
          if (gap <= tol && (best === null || gap < best.gap)) {
            best = { gap, yaw: yaw + wrapAngle(target - yaw), name: grid.name };
          }
        }
      }
    }
    return best ? { yaw: best.yaw, snap: { kind: "grid", name: best.name } } : { yaw, snap: null };
  }

  /** The box with its face moved t along the face normal, or null when it would collapse. */
  function moveFace(box, axis, side, t) {
    const next = cloneBox(box);
    if (side) next.max[axis] = box.max[axis] + t;
    else next.min[axis] = box.min[axis] - t;
    return next.max[axis] - next.min[axis] < MIN_SIZE_FT ? null : next;
  }

  function yawOf(box) {
    return Math.atan2(box.bx[1], box.bx[0]);
  }

  /** The box rotated about the vertical axis through its center to the given yaw. */
  function setYaw(box, yaw) {
    const next = cloneBox(box);
    const center = boxCenter(box);
    next.bx = [Math.cos(yaw), Math.sin(yaw), 0];
    next.by = [-Math.sin(yaw), Math.cos(yaw), 0];
    next.bz = [0, 0, 1];
    const local = v3.scale(v3.add(box.min, box.max), 0.5);
    next.origin = v3.sub(center, localToWorld({ origin: [0, 0, 0], bx: next.bx, by: next.by, bz: next.bz }, local));
    return next;
  }

  /** The box's local extents enlarged to contain a world-space axis-aligned box. */
  function fitToWorldBounds(box, min, max, pad) {
    const next = cloneBox(box);
    const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
    for (let k = 0; k < 8; k++) {
      const local = worldToLocal(box, [k & 1 ? max[0] : min[0], k & 2 ? max[1] : min[1], k & 4 ? max[2] : min[2]]);
      for (let a = 0; a < 3; a++) {
        lo[a] = Math.min(lo[a], local[a]);
        hi[a] = Math.max(hi[a], local[a]);
      }
    }
    next.min = lo.map((v) => v - pad);
    next.max = hi.map((v) => v + pad);
    return next;
  }

  function insideBox(box, world, eps) {
    const l = worldToLocal(box, world);
    return l.every((v, i) => v >= box.min[i] - eps && v <= box.max[i] + eps);
  }

  function triangleHit(o, d, p, i) {
    const e1x = p[i + 3] - p[i], e1y = p[i + 4] - p[i + 1], e1z = p[i + 5] - p[i + 2];
    const e2x = p[i + 6] - p[i], e2y = p[i + 7] - p[i + 1], e2z = p[i + 8] - p[i + 2];
    const px = d[1] * e2z - d[2] * e2y, py = d[2] * e2x - d[0] * e2z, pz = d[0] * e2y - d[1] * e2x;
    const det = e1x * px + e1y * py + e1z * pz;
    if (Math.abs(det) < 1e-12) return null;
    const inv = 1 / det;
    const sx = o[0] - p[i], sy = o[1] - p[i + 1], sz = o[2] - p[i + 2];
    const u = (sx * px + sy * py + sz * pz) * inv;
    if (u < 0 || u > 1) return null;
    const qx = sy * e1z - sz * e1y, qy = sz * e1x - sx * e1z, qz = sx * e1y - sy * e1x;
    const v = (d[0] * qx + d[1] * qy + d[2] * qz) * inv;
    if (v < 0 || u + v > 1) return null;
    const t = (e2x * qx + e2y * qy + e2z * qz) * inv;
    return t > 0 ? t : null;
  }

  function distanceToSegment2d(px, py, ax, ay, bx, by) {
    const dx = bx - ax, dy = by - ay;
    const len2 = dx * dx + dy * dy;
    const t = len2 ? Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / len2)) : 0;
    return Math.hypot(px - (ax + t * dx), py - (ay + t * dy));
  }

  const api = {
    cloneBox, localToWorld, worldToLocal, boxCorners, boxCenter, faceNormal, faceCenter, parseFace,
    closestOnAxis, snapCandidates, bestSnap, scopePlanes, snapYaw, moveFace, yawOf, setYaw,
    fitToWorldBounds, insideBox, distanceToSegment2d, triangleHit,
  };

  const MESH_VS = `#version 300 es
in vec3 aPos;
in vec3 aNormal;
uniform mat4 uViewProj;
out vec3 vNormal;
out vec3 vPos;
void main() {
  vNormal = aNormal;
  vPos = aPos;
  gl_Position = uViewProj * vec4(aPos, 1.0);
}`;
  const MESH_FS = `#version 300 es
precision highp float;
in vec3 vNormal;
in vec3 vPos;
uniform vec4 uColor;
uniform vec3 uLight;
uniform mat4 uBoxInv;
uniform vec3 uMin;
uniform vec3 uMax;
uniform int uMode;
out vec4 outColor;
void main() {
  if (uMode != 0) {
    vec3 l = (uBoxInv * vec4(vPos, 1.0)).xyz;
    bool inside = all(greaterThanEqual(l, uMin)) && all(lessThanEqual(l, uMax));
    if (uMode == 1 && !inside) discard;
    if (uMode == 2 && inside) discard;
  }
  float d = abs(dot(normalize(vNormal), uLight));
  outColor = vec4(uColor.rgb * (0.48 + 0.52 * d), uColor.a);
}`;
  const FLAT_VS = `#version 300 es
in vec3 aPos;
uniform mat4 uViewProj;
void main() { gl_Position = uViewProj * vec4(aPos, 1.0); }`;
  const FLAT_FS = `#version 300 es
precision highp float;
uniform vec4 uColor;
out vec4 outColor;
void main() { outColor = uColor; }`;

  const COLORS = {
    boxLine: [0.18, 0.50, 0.93],
    boxFace: [0.18, 0.50, 0.93],
    level: [0.88, 0.47, 0.0],
    grid: [0.38, 0.52, 0.0],
    scope: [0.56, 0.27, 0.68],
    snap: [0.96, 0.65, 0.14],
  };

  function hashHue(text) {
    let h = 0;
    for (let i = 0; i < text.length; i++) h = (h * 31 + text.charCodeAt(i)) >>> 0;
    return h % 360;
  }

  function hslToRgb(h, s, l) {
    const c = (1 - Math.abs(2 * l - 1)) * s;
    const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
    const m = l - c / 2;
    const [r, g, b] = h < 60 ? [c, x, 0] : h < 120 ? [x, c, 0] : h < 180 ? [0, c, x] : h < 240 ? [0, x, c] : h < 300 ? [x, 0, c] : [c, 0, x];
    return [r + m, g + m, b + m];
  }

  function groupColor(name) {
    if (name.startsWith("Link: ")) return hslToRgb(30, 0.45, 0.6);
    return hslToRgb(hashHue(name), 0.28, 0.64);
  }

  function boxInverse(box) {
    const b = [box.bx, box.by, box.bz];
    const out = new Array(16).fill(0);
    for (let r = 0; r < 3; r++) {
      for (let c = 0; c < 3; c++) out[c * 4 + r] = b[r][c];
      out[12 + r] = -v3.dot(b[r], box.origin);
    }
    out[15] = 1;
    return out;
  }

  function capture(node, pointerId, on) {
    try {
      if (on) node.setPointerCapture(pointerId);
      else node.releasePointerCapture(pointerId);
    } catch (error) {
      void error;
    }
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function format(template, ...values) {
    return values.reduce((text, v, i) => text.replace("{" + i + "}", v), template);
  }

  class Preview {
    constructor(root, payload) {
      this.root = root;
      this.channel = payload.channel;
      this.strings = payload.strings;
      this.units = payload.units;
      this.document = payload.document;
      this.view = payload.view;
      this.guides = { levels: [], grids: [], scopeBoxes: [] };
      this.batches = [];
      this.elements = new Map();
      this.groups = new Map();
      this.modelBounds = null;
      this.progress = [0, 0];
      this.loading = true;
      this.flags = {
        model: true, levels: true, grids: true, names: true, scope: true,
        cut: "ghost", ghost: 0.12, live: false, snap: true, allLevels: false,
      };
      this.mode = null;
      this.hover = null;
      this.drag = null;
      this.pending = 0;
      this.snapHighlight = null;
      this.pendingFrame = 0;
      this.requests = new Map();
      this._build();
      this._bindBridge();
      this.setCameraPreset(this.view.camera ? "view" : "iso");
      this._post("ready", {});
    }

    t(key) {
      return this.strings[key] || key;
    }

    fmt(feet) {
      const value = feet * this.units.factor;
      const text = value.toFixed(this.units.decimals);
      return this.units.symbol ? text + " " + this.units.symbol : text;
    }

    _post(action, payload) {
      const requestId = Math.random().toString(36).slice(2);
      return new Promise((resolve) => {
        this.requests.set(requestId, resolve);
        if (window.chrome && window.chrome.webview) {
          window.chrome.webview.postMessage({ channel: this.channel, action, payload, requestId });
        } else {
          resolve({ ok: false });
        }
      });
    }

    _bindBridge() {
      if (!(window.chrome && window.chrome.webview)) return;
      this._onMessage = (e) => {
        const m = e.data;
        if (!m || m.channel !== this.channel) return;
        this._onEvent(m.event, m.payload);
      };
      window.chrome.webview.addEventListener("message", this._onMessage);
    }

    dispose() {
      this.disposed = true;
      if (this.resizeObserver) this.resizeObserver.disconnect();
      if (this.pendingFrame) cancelAnimationFrame(this.pendingFrame);
      if (this._onKeyDown) window.removeEventListener("keydown", this._onKeyDown);
      if (this._onMessage && window.chrome.webview.removeEventListener) {
        window.chrome.webview.removeEventListener("message", this._onMessage);
      }
      const lose = this.gl && this.gl.getExtension("WEBGL_lose_context");
      if (lose) lose.loseContext();
      this.root.replaceChildren();
    }

    _onEvent(event, payload) {
      if (this.disposed) return;
      if (event === "reset") mount(this.root.id, payload);
      else if (event === "scene") this.addChunk(payload);
      else if (event === "guides") this.setGuides(payload);
      else if (event === "view" || event === "box") this.setView(payload, event === "view");
      else if (event === "sources") this.onSources(payload);
      else if (event === "result") this.onResult(payload);
      else if (event === "error" && payload.requestId) this.onResult({ requestId: payload.requestId, ok: false, message: payload.message });
      else if (event === "error") this.setStatus(payload.message, "error");
    }

    onResult(payload) {
      const resolve = this.requests.get(payload.requestId);
      if (resolve) {
        this.requests.delete(payload.requestId);
        this.pending = Math.max(0, this.pending - 1);
        resolve(payload);
      }
      if (payload.ok) this.setStatus(this.t("PreviewApplied"), "ok");
      else this.setStatus(format(this.t("PreviewFailed"), payload.message || ""), "error");
    }

    onSources(payload) {
      if (payload.done) {
        this.loading = false;
        this.setStatus(format(this.t("PreviewLoaded"), this.elements.size), "info");
        this._updateProgress();
      }
      if (payload.loading) {
        this.loading = true;
        this._updateProgress();
      }
      if (payload.dropLinks) this.dropLinks();
    }

    _build() {
      const root = this.root;
      root.className = "sbp-root";
      this.toolbar = el("div", "sbp-toolbar");
      this.main = el("div", "sbp-main");
      this.stage = el("div", "sbp-stage");
      this.canvas = el("canvas", "sbp-canvas");
      this.labelLayer = el("div", "sbp-labels");
      this.handleLayer = el("div", "sbp-handles");
      this.overlay = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      this.overlay.setAttribute("class", "sbp-overlay");
      this.hoverChip = el("div", "sbp-hover-chip");
      this.stage.append(this.canvas, this.overlay, this.labelLayer, this.handleLayer, this.hoverChip);
      this.side = el("div", "sbp-side");
      this.main.append(this.stage, this.side);
      this.statusBar = el("div", "sbp-status");
      this.statusText = el("span", "sbp-status-text");
      this.progressText = el("span", "sbp-progress");
      this.sizeText = el("span", "sbp-size");
      this.statusBar.append(this.statusText, this.sizeText, this.progressText);
      root.append(this.toolbar, this.main, this.statusBar);

      const gl = this.canvas.getContext("webgl2", { antialias: true, alpha: false });
      this.glMissing = !gl;
      if (gl) {
        this.gl = gl;
        this.meshProgram = compile(gl, MESH_VS, MESH_FS);
        this.flatProgram = compile(gl, FLAT_VS, FLAT_FS);
        this.dynamic = { lines: gl.createBuffer(), fill: gl.createBuffer() };
      }
      this.dark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;

      this._buildToolbar();
      this._buildSide();
      this._buildHandles();
      this._bindCanvas();
      this._bindKeys();
      this.resizeObserver = new ResizeObserver(() => this._resize());
      this.resizeObserver.observe(this.stage);
      this._resize();
      this.refreshChrome();
    }

    _toggle(parent, label, key, onChange) {
      const wrap = el("label", "sbp-toggle");
      const input = el("input");
      input.type = "checkbox";
      input.checked = !!this.flags[key];
      input.addEventListener("change", () => {
        this.flags[key] = input.checked;
        if (onChange) onChange();
        this.requestRender();
      });
      wrap.append(input, el("span", "", label));
      parent.append(wrap);
      return input;
    }

    _button(parent, label, onClick, title, className) {
      const b = el("button", "sbp-btn" + (className ? " " + className : ""), label);
      b.type = "button";
      if (title) b.title = title;
      b.addEventListener("click", onClick);
      parent.append(b);
      return b;
    }

    _bar(caption, ...children) {
      const bar = el("div", "sbp-bar");
      bar.append(el("span", "sbp-bar-caption", caption), ...children);
      this.toolbar.append(bar);
    }

    _segmented(items) {
      const segment = el("div", "sbp-seg");
      for (const [label, handler] of items) this._button(segment, label, handler);
      return segment;
    }

    _buildToolbar() {
      const showGroup = el("div", "sbp-group");
      this._toggle(showGroup, this.t("PreviewModel"), "model");
      this._toggle(showGroup, this.t("PreviewLevels"), "levels");
      this._toggle(showGroup, this.t("PreviewAllLevels"), "allLevels");
      this._toggle(showGroup, this.t("PreviewGrids"), "grids");
      this._toggle(showGroup, this.t("PreviewNames"), "names");
      this._toggle(showGroup, this.t("PreviewScopeBoxes"), "scope");
      const cutGroup = el("div", "sbp-group");
      cutGroup.append(el("span", "sbp-caption", this.t("PreviewCut")));
      this.cutSelect = el("select", "sbp-select");
      for (const [value, key] of [["ghost", "PreviewCutGhost"], ["hide", "PreviewCutHide"], ["off", "PreviewCutOff"]]) {
        const o = el("option", "", this.t(key));
        o.value = value;
        this.cutSelect.append(o);
      }
      this.cutSelect.addEventListener("change", () => {
        this.flags.cut = this.cutSelect.value;
        this.requestRender();
      });
      this.ghostRange = el("input", "sbp-range");
      this.ghostRange.type = "range";
      this.ghostRange.min = "2";
      this.ghostRange.max = "60";
      this.ghostRange.value = String(Math.round(this.flags.ghost * 100));
      this.ghostRange.title = this.t("PreviewGhostStrength");
      this.ghostRange.addEventListener("input", () => {
        this.flags.ghost = Number(this.ghostRange.value) / 100;
        this.requestRender();
      });
      cutGroup.append(this.cutSelect, this.ghostRange);
      this._bar(this.t("PreviewGroupShow"), showGroup, cutGroup);

      const cameraBar = this._segmented([
        [this.t("PreviewView"), () => this.setCameraPreset("view")],
        [this.t("PreviewTop"), () => this.setCameraPreset("top")],
        [this.t("PreviewFront"), () => this.setCameraPreset("front")],
        [this.t("PreviewSide"), () => this.setCameraPreset("side")],
        [this.t("PreviewIso"), () => this.setCameraPreset("iso")],
        [this.t("PreviewFitBox"), () => this.frameBox()],
        [this.t("PreviewFitModel"), () => this.frameModel()],
      ]);
      this._bar(this.t("PreviewGroupView"), cameraBar);

      const editGroup = el("div", "sbp-group");
      this._toggle(editGroup, this.t("PreviewSnap"), "snap");
      this._toggle(editGroup, this.t("PreviewLive"), "live");
      this.pickElementBtn = this._button(editGroup, this.t("PreviewPickElement"), () => this.setMode(this.mode === "element" ? null : "element"), "", "sbp-action");
      this.alignBtn = this._button(editGroup, this.t("PreviewAlignGrid"), () => this.setMode(this.mode === "grid" ? null : "grid"), "", "sbp-action");
      this._button(editGroup, this.t("PreviewFitVisible"), () => this.commitRequest("fit_visible", { padding: 1.0 }), "", "sbp-action");
      this._bar(this.t("PreviewGroupBox"), editGroup);
    }

    _buildSide() {
      this.categoryBox = el("div", "sbp-panel");
      this.scopeList = el("div", "sbp-panel");
      this.bookmarkList = el("div", "sbp-panel");
      this.side.append(this.categoryBox, this.scopeList, this.bookmarkList);
      this.refreshSide();
    }

    refreshSide() {
      this._renderCategories();
      this._renderScopeBoxes();
      this._renderBookmarks();
    }

    _renderCategories() {
      const box = this.categoryBox;
      box.replaceChildren();
      const head = el("div", "sbp-panel-head");
      head.append(el("span", "", this.t("PreviewCategories")));
      const all = el("a", "sbp-link", this.t("PreviewAll"));
      const none = el("a", "sbp-link", this.t("PreviewNone"));
      all.addEventListener("click", () => this._setAllGroups(true));
      none.addEventListener("click", () => this._setAllGroups(false));
      head.append(all, none);
      box.append(head);
      const names = [...this.groups.keys()].sort((a, b) => a.localeCompare(b));
      for (const name of names) {
        const group = this.groups.get(name);
        const row = el("label", "sbp-chip");
        const input = el("input");
        input.type = "checkbox";
        input.checked = group.visible;
        input.addEventListener("change", () => {
          group.visible = input.checked;
          this.requestRender();
        });
        const swatch = el("i", "sbp-swatch");
        swatch.style.background = `rgb(${group.color.map((c) => Math.round(c * 255)).join(",")})`;
        row.append(input, swatch, el("span", "", `${name} (${group.count})`));
        box.append(row);
      }
    }

    _setAllGroups(on) {
      for (const group of this.groups.values()) group.visible = on;
      this._renderCategories();
      this.requestRender();
    }

    _renderScopeBoxes() {
      const box = this.scopeList;
      box.replaceChildren();
      if (!this.guides.scopeBoxes.length) return;
      box.append(el("div", "sbp-panel-head", this.t("PreviewScopeBoxes")));
      for (const scope of this.guides.scopeBoxes) {
        const row = el("div", "sbp-row");
        row.append(el("span", "sbp-grow", scope.name));
        this._button(row, this.t("PreviewUseScopeBox"), () => this.commitRequest("use_scope_box", { id: scope.id }));
        box.append(row);
      }
    }

    _renderBookmarks() {
      const box = this.bookmarkList;
      box.replaceChildren();
      box.append(el("div", "sbp-panel-head", this.t("PreviewBookmarks")));
      const form = el("div", "sbp-row");
      const input = el("input", "sbp-input");
      input.type = "text";
      input.placeholder = this.t("PreviewBookmarkName");
      const save = this._button(form, this.t("PreviewBookmarkSave"), () => {
        if (!this.view.box) return;
        const name = input.value.trim() || this.t("PreviewBookmarkName");
        input.value = "";
        this.commitRequest("bookmark_save", { name, box: this.view.box });
      });
      save.disabled = !this.view.box;
      form.prepend(input);
      box.append(form);
      for (const bookmark of this.view.bookmarks || []) {
        const row = el("div", "sbp-row");
        const name = el("a", "sbp-link sbp-grow", bookmark.name);
        name.title = this.t("PreviewBookmarkApply");
        name.addEventListener("click", () => this.commitRequest("bookmark_apply", { id: bookmark.id }));
        row.append(name);
        this._button(row, "✎", () => {
          const next = window.prompt(this.t("PreviewBookmarkRename"), bookmark.name);
          if (next && next.trim()) this.commitRequest("bookmark_rename", { id: bookmark.id, name: next.trim() });
        }, this.t("PreviewBookmarkRename"));
        this._button(row, "✕", () => this.commitRequest("bookmark_delete", { id: bookmark.id }), this.t("PreviewBookmarkDelete"));
        box.append(row);
      }
    }

    _buildHandles() {
      this.handles = {};
      for (const face of Object.keys(BOX_FACES)) {
        const h = el("div", "sbp-handle sbp-handle-" + face[0]);
        h.dataset.face = face;
        h.addEventListener("pointerdown", (e) => this._startFaceDrag(e, face));
        this.handleLayer.append(h);
        this.handles[face] = h;
      }
      this.rotateHandle = el("div", "sbp-handle sbp-handle-rotate", "⟳");
      this.rotateHandle.addEventListener("pointerdown", (e) => this._startRotateDrag(e));
      this.handleLayer.append(this.rotateHandle);
      this.snapLabel = el("div", "sbp-snap-label");
      this.handleLayer.append(this.snapLabel);
    }

    setMode(mode) {
      this.mode = mode;
      this._clearHover();
      this.pickElementBtn.classList.toggle("sbp-on", mode === "element");
      this.alignBtn.classList.toggle("sbp-on", mode === "grid");
      this.canvas.style.cursor = mode ? "crosshair" : "";
      if (mode === "element") this.setStatus(this.t("PreviewHintElement"), "info");
      else if (mode === "grid") this.setStatus(this.t("PreviewHintGrid"), "info");
      else this._resetStatus();
    }

    _clearHover() {
      this.hover = null;
      if (this.hoverChip) this.hoverChip.style.display = "none";
      if (this.overlay) this.overlay.replaceChildren();
      this.requestRender();
    }

    setStatus(text, kind) {
      this.statusText.textContent = text || "";
      this.statusText.className = "sbp-status-text sbp-" + (kind || "info");
    }

    _resetStatus() {
      if (this.glMissing) this.setStatus("WebGL2 is not available", "error");
      else if (!this.view.box) this.setStatus(this.t("PreviewNoBox"), "warn");
      else if (this.view.blocker === "scope_box") this.setStatus(this.t("PreviewBlockedScopeBox"), "warn");
      else if (this.view.blocker === "crop_shape") this.setStatus(this.t("PreviewBlockedCropShape"), "warn");
      else if (!this.loading) this.setStatus(this.t("PreviewHelp"), "info");
    }

    refreshChrome() {
      const box = this.view.box;
      const editable = new Set(this.view.editable || []);
      for (const face of Object.keys(this.handles)) {
        this.handles[face].style.display = box && editable.has(face) ? "" : "none";
      }
      this.rotateHandle.style.display = box && this.view.kind === "3d" ? "" : "none";
      this.alignBtn.style.display = this.view.kind === "3d" ? "" : "none";
      this._resetStatus();
      this._updateSize();
      this._renderBookmarks();
    }

    _updateSize() {
      const box = this.view.box;
      if (!box) {
        this.sizeText.textContent = "";
        return;
      }
      const dims = [0, 1, 2].map((a) => this.fmt(box.max[a] - box.min[a]));
      this.sizeText.textContent = this.t("PreviewSize") + " " + dims.join(" × ");
    }

    _updateProgress() {
      const [done, total] = this.progress;
      this.progressText.textContent = this.loading && total ? format(this.t("PreviewLoading"), done, total) : "";
    }

    setView(payload, resetCamera) {
      if (this.drag && !resetCamera) return;
      this.view = payload;
      this.drag = null;
      this._buildGuideBuffers();
      this.refreshChrome();
      if (resetCamera) this.setCameraPreset(payload.camera ? "view" : "iso");
      this.requestRender();
    }

    setGuides(payload) {
      this.guides = payload;
      this._buildGuideBuffers();
      this._renderScopeBoxes();
      this.requestRender();
    }

    dropLinks() {
      this.batches = this.batches.filter((b) => b.source === 0);
      for (const [key, element] of [...this.elements]) if (element.source !== 0) this.elements.delete(key);
      for (const [name, group] of [...this.groups]) if (name.startsWith("Link: ")) this.groups.delete(name);
      this._renderCategories();
      this.requestRender();
    }

    _buffer(data, usage) {
      const gl = this.gl;
      const buffer = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
      gl.bufferData(gl.ARRAY_BUFFER, data, usage || gl.STATIC_DRAW);
      return buffer;
    }

    _vao(program, positions, normals) {
      const gl = this.gl;
      const vao = gl.createVertexArray();
      gl.bindVertexArray(vao);
      gl.bindBuffer(gl.ARRAY_BUFFER, positions);
      const aPos = gl.getAttribLocation(program.program, "aPos");
      gl.enableVertexAttribArray(aPos);
      gl.vertexAttribPointer(aPos, 3, gl.FLOAT, false, 0, 0);
      if (normals) {
        const aNormal = gl.getAttribLocation(program.program, "aNormal");
        gl.bindBuffer(gl.ARRAY_BUFFER, normals);
        gl.enableVertexAttribArray(aNormal);
        gl.vertexAttribPointer(aNormal, 3, gl.FLOAT, false, 0, 0);
      }
      gl.bindVertexArray(null);
      return vao;
    }

    addChunk(payload) {
      this.progress = payload.progress || this.progress;
      const byGroup = new Map();
      for (const mesh of payload.meshes) {
        const positions = decodeArray(mesh.positions, Float32Array);
        const indices = decodeArray(mesh.indices, Uint32Array);
        if (!indices.length) continue;
        const key = mesh.source + ":" + mesh.id;
        const bounds = { min: [Infinity, Infinity, Infinity], max: [-Infinity, -Infinity, -Infinity] };
        for (let i = 0; i < positions.length; i += 3) {
          for (let k = 0; k < 3; k++) {
            if (positions[i + k] < bounds.min[k]) bounds.min[k] = positions[i + k];
            if (positions[i + k] > bounds.max[k]) bounds.max[k] = positions[i + k];
          }
        }
        this.elements.set(key, { id: mesh.id, source: mesh.source, group: mesh.group, bounds, approx: mesh.approx });
        this._extendModelBounds(bounds);
        if (!byGroup.has(mesh.group)) byGroup.set(mesh.group, { source: mesh.source, parts: [], triangles: 0 });
        const entry = byGroup.get(mesh.group);
        entry.parts.push({ positions, indices, key });
        entry.triangles += indices.length / 3;
        let group = this.groups.get(mesh.group);
        if (!group) {
          group = { color: groupColor(mesh.group), visible: !mesh.hidden, count: 0 };
          this.groups.set(mesh.group, group);
        }
        group.count += 1;
      }
      for (const [name, entry] of byGroup) this._addBatch(name, entry);
      if (!this.view.box) this._buildGuideBuffers();
      this._renderCategories();
      this._updateProgress();
      this.requestRender();
    }

    _extendModelBounds(bounds) {
      if (!this.modelBounds) {
        this.modelBounds = { min: bounds.min.slice(), max: bounds.max.slice() };
        this._pendingFrame = true;
        return;
      }
      for (let k = 0; k < 3; k++) {
        this.modelBounds.min[k] = Math.min(this.modelBounds.min[k], bounds.min[k]);
        this.modelBounds.max[k] = Math.max(this.modelBounds.max[k], bounds.max[k]);
      }
    }

    _addBatch(name, entry) {
      const pos = new Float32Array(entry.triangles * 9);
      const nrm = new Float32Array(entry.triangles * 9);
      let offset = 0;
      const ranges = [];
      for (const part of entry.parts) {
        const rangeStart = offset;
        const p = part.positions, idx = part.indices;
        for (let t = 0; t < idx.length; t += 3) {
          const ia = idx[t] * 3, ib = idx[t + 1] * 3, ic = idx[t + 2] * 3;
          const ax = p[ia], ay = p[ia + 1], az = p[ia + 2];
          const ux = p[ib] - ax, uy = p[ib + 1] - ay, uz = p[ib + 2] - az;
          const vx = p[ic] - ax, vy = p[ic + 1] - ay, vz = p[ic + 2] - az;
          let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
          const l = Math.hypot(nx, ny, nz) || 1;
          nx /= l; ny /= l; nz /= l;
          pos[offset] = ax; pos[offset + 1] = ay; pos[offset + 2] = az;
          pos[offset + 3] = p[ib]; pos[offset + 4] = p[ib + 1]; pos[offset + 5] = p[ib + 2];
          pos[offset + 6] = p[ic]; pos[offset + 7] = p[ic + 1]; pos[offset + 8] = p[ic + 2];
          for (let k = 0; k < 3; k++) {
            nrm[offset + k * 3] = nx; nrm[offset + k * 3 + 1] = ny; nrm[offset + k * 3 + 2] = nz;
          }
          offset += 9;
        }
        ranges.push({ key: part.key, start: rangeStart, end: offset });
      }
      const vao = this.gl ? this._vao(this.meshProgram, this._buffer(pos), this._buffer(nrm)) : null;
      const batch = { group: name, source: entry.source, vao, count: entry.triangles * 3, pos };
      this.batches.push(batch);
      for (const range of ranges) {
        const element = this.elements.get(range.key);
        if (element) Object.assign(element, { batch, start: range.start, end: range.end });
      }
      if (this.gl) this.gl.bindVertexArray(null);
    }

    _guideExtent() {
      const bounds = { min: [Infinity, Infinity, Infinity], max: [-Infinity, -Infinity, -Infinity] };
      const merge = (p) => {
        for (let k = 0; k < 3; k++) {
          bounds.min[k] = Math.min(bounds.min[k], p[k]);
          bounds.max[k] = Math.max(bounds.max[k], p[k]);
        }
      };
      if (this.view.box) {
        boxCorners(this.view.box).forEach(merge);
      } else if (this.modelBounds) {
        merge(this.modelBounds.min);
        merge(this.modelBounds.max);
      }
      if (bounds.min[0] === Infinity) return { min: [-50, -50, -10], max: [50, 50, 50] };
      return bounds;
    }

    _buildGuideBuffers() {
      const ext = this._guideExtent();
      const pad = Math.max(8, 0.15 * Math.max(ext.max[0] - ext.min[0], ext.max[1] - ext.min[1]));
      const x0 = ext.min[0] - pad, x1 = ext.max[0] + pad, y0 = ext.min[1] - pad, y1 = ext.max[1] + pad;
      this.guideRect = { x0, x1, y0, y1 };
      this.gridZ = ext.min[2];
      if (!this.gl) return;
      const gl = this.gl;
      const fill = [], lines = [];
      for (const level of this.guides.levels) {
        const z = level.z;
        fill.push(x0, y0, z, x1, y0, z, x1, y1, z, x0, y0, z, x1, y1, z, x0, y1, z);
        lines.push(x0, y0, z, x1, y0, z, x1, y0, z, x1, y1, z, x1, y1, z, x0, y1, z, x0, y1, z, x0, y0, z);
      }
      const gridLines = [];
      this.gridRanges = [];
      const zBase = ext.min[2];
      for (const grid of this.guides.grids) {
        const start = gridLines.length / 3;
        for (const s of grid.segs) gridLines.push(s[0], s[1], zBase, s[2], s[3], zBase);
        this.gridRanges.push({ first: start, count: gridLines.length / 3 - start });
      }
      this.levelFillVao = this._vao(this.flatProgram, this._buffer(new Float32Array(fill)));
      this.levelLineVao = this._vao(this.flatProgram, this._buffer(new Float32Array(lines)));
      this.gridVao = this._vao(this.flatProgram, this._buffer(new Float32Array(gridLines)));
      gl.bindVertexArray(null);
    }

    _bindKeys() {
      this._onKeyDown = (e) => {
        if (e.key === "Escape") {
          if (this.drag) this._cancelDrag();
          else this.setMode(null);
        }
      };
      window.addEventListener("keydown", this._onKeyDown);
    }

    _cancelDrag() {
      const d = this.drag;
      if (!d) return;
      if (d.detach) d.detach();
      this.drag = null;
      this.view.box = d.box0;
      if (d.sent) this._commitBox(d.box0);
      this.snapHighlight = null;
      this.snapLabel.style.display = "none";
      this._updateSize();
      this.requestRender();
    }

    _bindCanvas() {
      const canvas = this.canvas;
      let nav = null;
      canvas.addEventListener("contextmenu", (e) => e.preventDefault());
      canvas.addEventListener("pointerdown", (e) => {
        capture(canvas, e.pointerId, true);
        nav = { x: e.clientX, y: e.clientY, moved: false, pan: e.button === 1 || e.button === 2 || e.shiftKey };
      });
      canvas.addEventListener("pointermove", (e) => {
        if (!nav) {
          if (this.mode) this._scheduleHover(e);
          return;
        }
        const dx = e.clientX - nav.x, dy = e.clientY - nav.y;
        if (Math.abs(dx) + Math.abs(dy) > 2) nav.moved = true;
        nav.x = e.clientX;
        nav.y = e.clientY;
        if (nav.pan) S3.cameraPan(this.camera, dx, dy, canvas.clientHeight);
        else S3.cameraOrbit(this.camera, dx, dy);
        this.requestRender();
      });
      canvas.addEventListener("pointerup", (e) => {
        capture(canvas, e.pointerId, false);
        const click = nav && !nav.moved && e.button === 0;
        nav = null;
        if (click) this._onCanvasClick(e);
      });
      canvas.addEventListener("wheel", (e) => {
        e.preventDefault();
        S3.cameraZoom(this.camera, e.deltaY, this._radius() * 0.02);
        this.requestRender();
      }, { passive: false });
      canvas.addEventListener("pointerleave", () => {
        if (this.mode) this._clearHover();
      });
      canvas.addEventListener("dblclick", () => this.frameBox());
    }

    _radius() {
      const ext = this.modelBounds || this._guideExtent();
      return Math.max(v3.len(v3.sub(ext.max, ext.min)) / 2, 1);
    }

    _onCanvasClick(e) {
      if (!this.mode) return;
      const hover = this._hoverAt(e);
      if (!hover) return;
      this.setMode(null);
      this._commitBox(hover.box);
    }

    _scheduleHover(e) {
      this._hoverEvent = e;
      if (this._hoverQueued) return;
      this._hoverQueued = true;
      requestAnimationFrame(() => {
        this._hoverQueued = false;
        if (!this.mode) return;
        const event = this._hoverEvent;
        this.hover = this._hoverAt(event);
        this._placeChip(event);
        this.requestRender();
      });
    }

    _placeChip(e) {
      const chip = this.hoverChip;
      if (!this.hover) {
        chip.style.display = "none";
        return;
      }
      const rect = this.stage.getBoundingClientRect();
      chip.textContent = this.hover.label;
      chip.style.display = "block";
      chip.style.left = e.clientX - rect.left + 14 + "px";
      chip.style.top = e.clientY - rect.top + 14 + "px";
    }

    _hoverAt(e) {
      if (!this.view.box || this.view.blocker) return null;
      if (this.mode === "element") {
        const ray = this._ray(e);
        const element = ray && this._elementAt(ray);
        if (!element) return null;
        return {
          kind: "element",
          element,
          label: `${element.group} · ${element.id}`,
          box: fitToWorldBounds(this.view.box, element.bounds.min, element.bounds.max, 1.0),
        };
      }
      const found = this._gridAt(e);
      if (!found) return null;
      const yaw = Math.atan2(found.seg[3] - found.seg[1], found.seg[2] - found.seg[0]);
      const quarter = Math.round(wrapAngle(yawOf(this.view.box) - yaw) / (Math.PI / 2));
      return {
        kind: "grid",
        grid: found.grid,
        label: `${this.t("PreviewAlignGrid")}: ${found.grid.name}`,
        box: setYaw(this.view.box, yaw + quarter * (Math.PI / 2)),
      };
    }

    _elementAt(ray) {
      let best = null, bestT = Infinity;
      for (const element of this.elements.values()) {
        if (!element.batch) continue;
        const group = this.groups.get(element.group);
        if (group && !group.visible) continue;
        if (!S3.rayBox(ray.origin, ray.dir, element.bounds)) continue;
        const pos = element.batch.pos;
        for (let i = element.start; i < element.end; i += 9) {
          const t = triangleHit(ray.origin, ray.dir, pos, i);
          if (t !== null && t < bestT) {
            bestT = t;
            best = element;
          }
        }
      }
      return best;
    }

    _gridAt(e) {
      if (this.view.kind !== "3d") return null;
      const rect = this.canvas.getBoundingClientRect();
      const px = e.clientX - rect.left, py = e.clientY - rect.top;
      const vp = this._matrices().viewProj;
      let best = null, bestD = 14;
      for (const grid of this.guides.grids) {
        for (const s of grid.segs) {
          const a = this._project(vp, [s[0], s[1], this.gridZ]);
          const b = this._project(vp, [s[2], s[3], this.gridZ]);
          if (!a || !b) continue;
          const d = distanceToSegment2d(px, py, a.x, a.y, b.x, b.y);
          if (d < bestD) {
            bestD = d;
            best = { grid, seg: s };
          }
        }
      }
      return best;
    }

    _ray(e) {
      const rect = this.canvas.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const y = 1 - ((e.clientY - rect.top) / rect.height) * 2;
      const inverse = m4.invert(this._matrices().viewProj);
      if (!inverse) return null;
      const near = m4.transform(inverse, [x, y, -1]).slice(0, 3);
      const far = m4.transform(inverse, [x, y, 1]).slice(0, 3);
      return { origin: near, dir: v3.norm(v3.sub(far, near)) };
    }

    _project(viewProj, p) {
      const q = m4.transform(viewProj, p);
      if (q[3] <= 0) return null;
      return {
        x: ((q[0] + 1) / 2) * this.canvas.clientWidth,
        y: ((1 - q[1]) / 2) * this.canvas.clientHeight,
      };
    }

    _toleranceFt(point, pixels) {
      const cam = this.camera;
      const eye = S3.cameraEye(cam);
      const depth = cam.ortho ? cam.dist : v3.len(v3.sub(eye, point));
      return (pixels * 2 * depth * Math.tan(FOV / 2)) / Math.max(this.canvas.clientHeight, 1);
    }

    _targets() {
      return { levels: this.guides.levels, grids: this.guides.grids, planes: scopePlanes(this.flags.scope ? this.guides.scopeBoxes : []) };
    }

    _startFaceDrag(e, face) {
      if (!this.view.box || this.drag) return;
      e.preventDefault();
      e.stopPropagation();
      const target = e.currentTarget;
      capture(target, e.pointerId, true);
      const { axis, side } = parseFace(face);
      const box0 = cloneBox(this.view.box);
      this.drag = {
        kind: "face", face, axis, side, box0,
        p0: faceCenter(box0, axis, side), n: faceNormal(box0, axis, side), t: 0, lastSend: 0,
      };
      const move = (ev) => this._moveFaceDrag(ev);
      const detach = () => {
        target.removeEventListener("pointermove", move);
        target.removeEventListener("pointerup", up);
        capture(target, e.pointerId, false);
      };
      const up = () => {
        detach();
        this._endDrag();
      };
      this.drag.detach = detach;
      target.addEventListener("pointermove", move);
      target.addEventListener("pointerup", up);
    }

    _moveFaceDrag(e) {
      const d = this.drag;
      if (!d || d.kind !== "face") return;
      const ray = this._ray(e);
      if (!ray) return;
      let t = closestOnAxis(d.p0, d.n, ray.origin, ray.dir);
      if (t === null) return;
      let snap = null;
      if (this.flags.snap && !e.altKey) {
        const res = bestSnap(t, snapCandidates(d.p0, d.n, this._targets()), this._toleranceFt(d.p0, SNAP_PIXELS));
        t = res.t;
        snap = res.snap;
      }
      const next = moveFace(d.box0, d.axis, d.side, t);
      if (!next) return;
      d.t = t;
      this.view.box = next;
      this._setSnapHighlight(snap, d);
      this._updateSize();
      this.requestRender();
      this._liveCommit();
    }

    _setSnapHighlight(snap, d) {
      this.snapHighlight = snap;
      if (!snap) {
        this.snapLabel.style.display = "none";
        return;
      }
      this.snapLabel.textContent = format(this.t("PreviewSnappedTo"), snap.name);
      this.snapLabel.style.display = "";
      d.label = snap;
    }

    _startRotateDrag(e) {
      if (!this.view.box || this.drag || this.view.kind !== "3d") return;
      e.preventDefault();
      e.stopPropagation();
      const target = e.currentTarget;
      capture(target, e.pointerId, true);
      const box0 = cloneBox(this.view.box);
      const center = boxCenter(box0);
      const angleAt = (ev) => {
        const ray = this._ray(ev);
        if (!ray || Math.abs(ray.dir[2]) < 1e-6) return null;
        const t = (center[2] - ray.origin[2]) / ray.dir[2];
        return Math.atan2(ray.origin[1] + t * ray.dir[1] - center[1], ray.origin[0] + t * ray.dir[0] - center[0]);
      };
      this.drag = { kind: "rotate", box0, a0: angleAt(e), yaw0: yawOf(box0), lastSend: 0 };
      const move = (ev) => {
        const d = this.drag;
        if (!d || d.kind !== "rotate") return;
        const a = angleAt(ev);
        if (a === null || d.a0 === null) return;
        let yaw = d.yaw0 + wrapAngle(a - d.a0);
        let snap = null;
        if (this.flags.snap && !ev.altKey) {
          const res = snapYaw(yaw, this.guides.grids, YAW_SNAP_RAD);
          yaw = res.yaw;
          snap = res.snap;
        }
        this.view.box = setYaw(d.box0, yaw);
        this._setSnapHighlight(snap, d);
        this.requestRender();
        this._liveCommit();
      };
      const detach = () => {
        target.removeEventListener("pointermove", move);
        target.removeEventListener("pointerup", up);
        capture(target, e.pointerId, false);
      };
      const up = () => {
        detach();
        this._endDrag();
      };
      this.drag.detach = detach;
      target.addEventListener("pointermove", move);
      target.addEventListener("pointerup", up);
    }

    _liveCommit() {
      const d = this.drag;
      if (!this.flags.live || !d || this.pending) return;
      const now = performance.now();
      if (now - d.lastSend < LIVE_INTERVAL_MS) return;
      d.lastSend = now;
      d.sent = true;
      this._commitBox(this.view.box, true);
    }

    _endDrag() {
      const d = this.drag;
      this.drag = null;
      this.snapHighlight = null;
      this.snapLabel.style.display = "none";
      if (d) this._commitBox(this.view.box);
      this._buildGuideBuffers();
      this.requestRender();
    }

    _commitBox(box, keepDrag) {
      this.view.box = box;
      this.pending += 1;
      this._post("apply_box", { box });
      this._updateSize();
      this.requestRender();
    }

    commitRequest(action, payload) {
      this.pending += 1;
      this._post(action, payload);
    }

    frameBounds(bounds) {
      S3.cameraFrame(this.camera, bounds);
      this.requestRender();
    }

    frameBox() {
      if (this.view.box) {
        const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
        for (const c of boxCorners(this.view.box)) for (let k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], c[k]); hi[k] = Math.max(hi[k], c[k]); }
        this.frameBounds({ min: lo, max: hi });
      } else {
        this.frameModel();
      }
    }

    frameModel() {
      this.frameBounds(this.modelBounds || this._guideExtent());
    }

    setCameraPreset(name) {
      const bounds = this.view.box ? this._boxBounds() : this.modelBounds || this._guideExtent();
      if (name === "front" || name === "side") {
        this.camera = this._elevationCamera(name, bounds);
      } else {
        this.camera = S3.cameraPreset(name, this.view.camera, bounds);
      }
      this.requestRender();
    }

    _elevationCamera(name, bounds) {
      const box = this.view.box;
      const axis = name === "front" ? (box ? box.by : [0, 1, 0]) : box ? box.bx : [1, 0, 0];
      const sign = name === "front" ? -1 : 1;
      const camera = {
        target: [0, 0, 0],
        dist: 1,
        yaw: Math.atan2(sign * axis[1], sign * axis[0]),
        pitch: 0,
        ortho: true,
      };
      S3.cameraFrame(camera, bounds);
      return camera;
    }

    _boxBounds() {
      const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
      for (const c of boxCorners(this.view.box)) for (let k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], c[k]); hi[k] = Math.max(hi[k], c[k]); }
      return { min: lo, max: hi };
    }

    requestRender() {
      if (this.pendingFrame) return;
      this.pendingFrame = requestAnimationFrame(() => {
        this.pendingFrame = 0;
        this._render();
      });
    }

    _resize() {
      const dpr = window.devicePixelRatio || 1;
      const w = Math.max(1, Math.round(this.stage.clientWidth * dpr));
      const h = Math.max(1, Math.round(this.stage.clientHeight * dpr));
      if (this.canvas.width !== w || this.canvas.height !== h) {
        this.canvas.width = w;
        this.canvas.height = h;
      }
      this.requestRender();
    }

    _matrices() {
      const aspect = this.canvas.width / Math.max(this.canvas.height, 1);
      return S3.cameraMatrices(this.camera, aspect, this._radius() * 4);
    }

    _boxUniforms(gl, program, mode) {
      const box = this.view.box;
      gl.uniform1i(program.uniforms.uMode, box ? mode : 0);
      if (!box) return;
      gl.uniformMatrix4fv(program.uniforms.uBoxInv, false, boxInverse(box));
      gl.uniform3fv(program.uniforms.uMin, box.min.map((v) => v - CLIP_EPSILON_FT));
      gl.uniform3fv(program.uniforms.uMax, box.max.map((v) => v + CLIP_EPSILON_FT));
    }

    _drawBatches(gl, program, alphaFor) {
      for (const batch of this.batches) {
        const group = this.groups.get(batch.group);
        if (!group || !group.visible) continue;
        gl.uniform4fv(program.uniforms.uColor, [...group.color, alphaFor]);
        gl.bindVertexArray(batch.vao);
        gl.drawArrays(gl.TRIANGLES, 0, batch.count);
      }
    }

    _render() {
      const { eye, viewProj } = this._matrices();
      this.viewProj = viewProj;
      if (this.gl) this._drawScene(eye, viewProj);
      this._renderHover(viewProj);
      this._renderLabels(viewProj);
      this._placeHandles(viewProj);
      if (this._pendingFrame && this.modelBounds && !this.view.box) {
        this._pendingFrame = false;
        this.frameModel();
      }
    }

    _drawScene(eye, viewProj) {
      const gl = this.gl;
      gl.viewport(0, 0, this.canvas.width, this.canvas.height);
      const bg = this.dark ? [0.11, 0.12, 0.14] : [0.972, 0.976, 0.98];
      gl.clearColor(bg[0], bg[1], bg[2], 1);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      gl.enable(gl.DEPTH_TEST);
      gl.disable(gl.CULL_FACE);
      gl.disable(gl.BLEND);
      gl.depthMask(true);

      const light = v3.norm(v3.add(v3.sub(eye, this.camera.target), [0, 0, this.camera.dist * 0.6]));
      const mp = this.meshProgram;
      gl.useProgram(mp.program);
      gl.uniformMatrix4fv(mp.uniforms.uViewProj, false, viewProj);
      gl.uniform3fv(mp.uniforms.uLight, light);
      const cutting = this.flags.cut !== "off" && this.view.box;
      if (this.flags.model) {
        gl.enable(gl.POLYGON_OFFSET_FILL);
        gl.polygonOffset(1, 1);
        this._boxUniforms(gl, mp, cutting ? 1 : 0);
        this._drawBatches(gl, mp, 1);
        gl.disable(gl.POLYGON_OFFSET_FILL);
        this._drawHoverElement(gl, mp);
        if (cutting && this.flags.cut === "ghost") {
          gl.enable(gl.BLEND);
          gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
          gl.depthMask(false);
          this._boxUniforms(gl, mp, 2);
          this._drawBatches(gl, mp, this.flags.ghost);
          gl.depthMask(true);
          gl.disable(gl.BLEND);
        }
      }
      this._renderGuides(gl, viewProj);
      gl.bindVertexArray(null);
    }

    _drawHoverElement(gl, mp) {
      const hover = this.hover;
      if (!hover || hover.kind !== "element" || !hover.element.batch) return;
      const { batch, start, end } = hover.element;
      gl.enable(gl.POLYGON_OFFSET_FILL);
      gl.polygonOffset(-2, -2);
      gl.depthFunc(gl.LEQUAL);
      this._boxUniforms(gl, mp, 0);
      gl.uniform4fv(mp.uniforms.uColor, [...COLORS.snap, 1]);
      gl.bindVertexArray(batch.vao);
      gl.drawArrays(gl.TRIANGLES, start / 3, (end - start) / 3);
      gl.depthFunc(gl.LESS);
      gl.disable(gl.POLYGON_OFFSET_FILL);
    }

    _renderHover(viewProj) {
      const svg = this.overlay;
      svg.replaceChildren();
      const hover = this.hover;
      if (!hover || hover.kind !== "grid") return;
      for (const s of hover.grid.segs) {
        const a = this._project(viewProj, [s[0], s[1], this.gridZ]);
        const b = this._project(viewProj, [s[2], s[3], this.gridZ]);
        if (!a || !b) continue;
        const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
        line.setAttribute("x1", a.x);
        line.setAttribute("y1", a.y);
        line.setAttribute("x2", b.x);
        line.setAttribute("y2", b.y);
        line.setAttribute("class", "sbp-hover-line");
        svg.append(line);
      }
    }

    _visibleLevelIndexes() {
      const levels = this.guides.levels;
      const all = levels.map((_, i) => i);
      if (this.flags.allLevels || !this.view.box) return all;
      const zs = boxCorners(this.view.box).map((c) => c[2]);
      const low = Math.min(...zs), high = Math.max(...zs);
      let below = -1, above = -1;
      const shown = [];
      for (const i of all) {
        const z = levels[i].z;
        if (z >= low - 1e-6 && z <= high + 1e-6) shown.push(i);
        else if (z < low && (below < 0 || z > levels[below].z)) below = i;
        else if (z > high && (above < 0 || z < levels[above].z)) above = i;
      }
      if (below >= 0) shown.push(below);
      if (above >= 0) shown.push(above);
      const snap = this.snapHighlight;
      if (snap && snap.kind === "level") {
        const index = levels.findIndex((l) => l.name === snap.name);
        if (index >= 0 && !shown.includes(index)) shown.push(index);
      }
      return shown;
    }

    _renderGuides(gl, viewProj) {
      const fp = this.flatProgram;
      gl.useProgram(fp.program);
      gl.uniformMatrix4fv(fp.uniforms.uViewProj, false, viewProj);
      const levels = this.guides.levels, grids = this.guides.grids;
      if (this.flags.grids && grids.length) {
        gl.uniform4fv(fp.uniforms.uColor, [...COLORS.grid, 0.9]);
        gl.bindVertexArray(this.gridVao);
        gl.drawArrays(gl.LINES, 0, this.gridRanges.length ? this.gridRanges[this.gridRanges.length - 1].first + this.gridRanges[this.gridRanges.length - 1].count : 0);
        const snap = this.snapHighlight;
        if (snap && snap.kind === "grid") {
          const index = grids.findIndex((g) => g.name === snap.name);
          if (index >= 0) {
            const r = this.gridRanges[index];
            gl.uniform4fv(fp.uniforms.uColor, [...COLORS.snap, 1]);
            gl.drawArrays(gl.LINES, r.first, r.count);
          }
        }
      }
      if (this.flags.levels && levels.length) {
        gl.uniform4fv(fp.uniforms.uColor, [...COLORS.level, 0.55]);
        gl.bindVertexArray(this.levelLineVao);
        for (const i of this._visibleLevelIndexes()) gl.drawArrays(gl.LINES, i * 8, 8);
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
        gl.depthMask(false);
        const snap = this.snapHighlight;
        gl.bindVertexArray(this.levelFillVao);
        if (snap && snap.kind === "level") {
          const index = levels.findIndex((l) => l.name === snap.name);
          if (index >= 0) {
            gl.uniform4fv(fp.uniforms.uColor, [...COLORS.snap, 0.35]);
            gl.drawArrays(gl.TRIANGLES, index * 6, 6);
          }
        }
        gl.depthMask(true);
        gl.disable(gl.BLEND);
      }
      gl.disable(gl.DEPTH_TEST);
      if (this.flags.scope) {
        for (const scope of this.guides.scopeBoxes) this._drawWireBox(gl, fp, scope.box, COLORS.scope, 0.9);
      }
      if (this.view.box) this._drawBoxOverlay(gl, fp);
      if (this.hover) this._drawWireBox(gl, fp, this.hover.box, COLORS.snap, 1);
      gl.enable(gl.DEPTH_TEST);
    }

    _drawWireBox(gl, fp, box, color, alpha) {
      const corners = boxCorners(box);
      const data = new Float32Array(BOX_EDGES.length * 6);
      BOX_EDGES.forEach(([a, b], i) => {
        data.set(corners[a], i * 6);
        data.set(corners[b], i * 6 + 3);
      });
      this._drawDynamic(gl, fp, data, gl.LINES, [...color, alpha]);
    }

    _drawDynamic(gl, fp, data, mode, color) {
      gl.bindVertexArray(null);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.dynamic.lines);
      gl.bufferData(gl.ARRAY_BUFFER, data, gl.DYNAMIC_DRAW);
      const aPos = gl.getAttribLocation(fp.program, "aPos");
      gl.enableVertexAttribArray(aPos);
      gl.vertexAttribPointer(aPos, 3, gl.FLOAT, false, 0, 0);
      gl.uniform4fv(fp.uniforms.uColor, color);
      gl.drawArrays(mode, 0, data.length / 3);
    }

    _drawBoxOverlay(gl, fp) {
      const box = this.view.box;
      const corners = boxCorners(box);
      const editable = new Set(this.view.editable || []);
      const tris = [];
      for (const [face, idx] of Object.entries(BOX_FACES)) {
        const active = this.drag && this.drag.face === face;
        if (!active && !this.flags.cut) continue;
        const quad = idx.map((i) => corners[i]);
        if (active) tris.push(...quad[0], ...quad[1], ...quad[2], ...quad[0], ...quad[2], ...quad[3]);
      }
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
      if (tris.length) this._drawDynamic(gl, fp, new Float32Array(tris), gl.TRIANGLES, [...COLORS.snap, 0.25]);
      const all = [];
      for (const idx of Object.values(BOX_FACES)) {
        const q = idx.map((i) => corners[i]);
        all.push(...q[0], ...q[1], ...q[2], ...q[0], ...q[2], ...q[3]);
      }
      this._drawDynamic(gl, fp, new Float32Array(all), gl.TRIANGLES, [...COLORS.boxFace, 0.05]);
      gl.disable(gl.BLEND);
      this._drawWireBox(gl, fp, box, COLORS.boxLine, 1);
      void editable;
    }

    _renderLabels(viewProj) {
      const candidates = [];
      const width = this.canvas.clientWidth, height = this.canvas.clientHeight;
      const place = (text, point, className) => {
        const p = this._project(viewProj, point);
        if (!p || p.x < -20 || p.x > width + 20 || p.y < -20 || p.y > height + 20) return;
        candidates.push({ text, x: p.x, y: p.y, className });
      };
      if (this.flags.names && this.guideRect) {
        const r = this.guideRect;
        const lookingDown = Math.abs(this.camera.pitch) > (70 * Math.PI) / 180;
        if (this.flags.levels && !lookingDown) {
          const levels = this.guides.levels;
          for (const i of this._visibleLevelIndexes()) {
            const level = levels[i];
            const elevation = level.elevation === undefined ? level.z : level.elevation;
            place(`${level.name} (${this.fmt(elevation)})`, [r.x0, r.y0, level.z], "sbp-label-level");
          }
        }
        if (this.flags.grids) {
          for (const grid of this.guides.grids) {
            if (!grid.segs.length) continue;
            const first = grid.segs[0], last = grid.segs[grid.segs.length - 1];
            const a = this._project(viewProj, [first[0], first[1], this.gridZ]);
            const b = this._project(viewProj, [last[2], last[3], this.gridZ]);
            if (!a || !b) continue;
            const steep = Math.abs(a.y - b.y) >= Math.abs(a.x - b.x);
            const useFirst = steep ? a.y <= b.y : a.x <= b.x;
            const end = useFirst ? [first[0], first[1]] : [last[2], last[3]];
            place(grid.name, [end[0], end[1], this.gridZ], "sbp-label-grid");
          }
        }
        if (this.flags.scope) for (const scope of this.guides.scopeBoxes) place(scope.name, boxCenter(scope.box), "sbp-label-scope");
      }
      const kept = [];
      for (const item of candidates) {
        const w = item.text.length * 6.5 + 14;
        const clash = kept.some((o) => item.x < o.x + o.w && o.x < item.x + w && Math.abs(item.y - o.y) < 15);
        if (!clash) kept.push({ ...item, w });
      }
      this.labelLayer.replaceChildren(
        ...kept.map((item) => {
          const node = el("span", "sbp-label " + item.className, item.text);
          node.style.left = item.x + "px";
          node.style.top = item.y + "px";
          return node;
        })
      );
    }

    _placeHandles(viewProj) {
      const box = this.view.box;
      if (!box) return;
      const editable = new Set(this.view.editable || []);
      for (const face of Object.keys(this.handles)) {
        if (!editable.has(face)) continue;
        const { axis, side } = parseFace(face);
        const p = this._project(viewProj, faceCenter(box, axis, side));
        const h = this.handles[face];
        if (!p) {
          h.style.display = "none";
          continue;
        }
        h.style.display = "";
        h.style.left = p.x + "px";
        h.style.top = p.y + "px";
        h.classList.toggle("sbp-active", !!(this.drag && this.drag.face === face));
      }
      if (this.view.kind === "3d") {
        const top = faceCenter(box, 2, 1);
        const lift = Math.max(2, 0.12 * v3.len(v3.sub(box.max, box.min)));
        const p = this._project(viewProj, [top[0], top[1], top[2] + lift]);
        this.rotateHandle.style.display = p ? "" : "none";
        if (p) {
          this.rotateHandle.style.left = p.x + "px";
          this.rotateHandle.style.top = p.y + "px";
        }
      }
      if (this.drag && this.snapLabel.style.display !== "none") {
        const ref = this.drag.face ? faceCenter(box, this.drag.axis, this.drag.side) : boxCenter(box);
        const p = this._project(viewProj, ref);
        if (p) {
          this.snapLabel.style.left = p.x + 14 + "px";
          this.snapLabel.style.top = p.y - 22 + "px";
        }
      }
    }
  }

  function mount(rootId, payload) {
    const api = window.pyRevitSectionBoxPreview;
    if (api.instance) api.instance.dispose();
    api.instance = new Preview(document.getElementById(rootId), payload);
  }

  window.pyRevitSectionBoxPreview = { mount, api, Preview };
})();
