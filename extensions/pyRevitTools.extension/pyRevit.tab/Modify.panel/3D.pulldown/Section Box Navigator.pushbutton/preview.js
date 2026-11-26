/*
 * Interactive 3D preview of a section or crop box, and of a plan's view range,
 * for the Section Box Navigator.
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
  const ELEVATION_PITCH = (6 * Math.PI) / 180;
  const GRID_ALONG_VIEW = (20 * Math.PI) / 180;
  const GRID_SPAN_PAD = 0.08;
  const SIDE_MIN_PX = 160;
  const SIDE_MAX_PX = 1200;
  const SIDE_MAX_FRACTION = 0.7;
  const LABEL_PIN_PX = 12;
  const LABEL_DOT_PX = 9;
  const LABEL_CHAR_PX = 6.5;
  const LABEL_PAD_PX = 14;
  const BOX_ONLY_ALPHA = 0.35;
  const AXIS_NAMES = ["x", "y", "z"];
  const RANGE_ORDER = { floor: ["top", "cut", "bottom", "depth"], ceiling: ["depth", "top", "cut"] };
  const RANGE_STRINGS = { top: "PreviewRangeTop", cut: "PreviewRangeCut", bottom: "PreviewRangeBottom", depth: "PreviewRangeDepth" };
  const RANGE_COLORS = { top: [0.0, 0.66, 0.2], cut: [0.86, 0.12, 0.12], bottom: [0.16, 0.36, 0.92], depth: [0.95, 0.5, 0.0] };
  const RANGE_HANDLE_AT = { top: 0.2, cut: 0.4, bottom: 0.6, depth: 0.8 };
  const RANGE_COINCIDENT_FT = 1e-5;
  const RANGE_TOP_PITCH = (80 * Math.PI) / 180;
  const RANGE_CHIP_PX = 18;
  const RANGE_HANDLE_GAP_PX = 12;
  const RANGE_DEFAULT_STEP_FT = 1 / 24;
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

  /** The chord of a grid, {mid, dir} in plan, or null for a grid without length. */
  function gridChord(grid) {
    if (!grid.segs.length) return null;
    const first = grid.segs[0], last = grid.segs[grid.segs.length - 1];
    const dx = last[2] - first[0], dy = last[3] - first[1];
    const len = Math.hypot(dx, dy);
    if (len < 1e-9) return null;
    return { mid: [(first[0] + last[2]) / 2, (first[1] + last[3]) / 2], dir: [dx / len, dy / len] };
  }

  /** Indexes of the grids running along the horizontal viewing direction of a camera with this yaw, within maxAngle. */
  function gridsAlongView(grids, yaw, maxAngle) {
    const limit = Math.cos(maxAngle);
    const indexes = [];
    grids.forEach((grid, index) => {
      const chord = gridChord(grid);
      if (chord && Math.abs(chord.dir[0] * Math.cos(yaw) + chord.dir[1] * Math.sin(yaw)) >= limit) indexes.push(index);
    });
    return indexes;
  }

  /** Whether a camera looks level enough that levels collapse to lines and grids to vertical lines. */
  function isElevationCamera(camera) {
    return Math.abs(camera.pitch) < ELEVATION_PITCH;
  }

  /** Where a label of a line running from left to right on screen sits so it stays inside the viewport; null when none of the line shows. */
  function pinToViewport(left, right, minX) {
    if (right[0] < minX) return null;
    if (left[0] >= minX) return { x: left[0], y: left[1] };
    const span = right[0] - left[0];
    const t = span > 1e-6 ? (minX - left[0]) / span : 0;
    return { x: minX, y: left[1] + t * (right[1] - left[1]) };
  }

  /**
   * The groups to list for a search term, as [key, group] entries per source, by name.
   *
   * A term matches a category name or a link title; a link title keeps all of
   * that link's categories. An empty term lists everything.
   */
  function filterGroups(groups, term) {
    const needle = term.trim().toLowerCase();
    const bySource = new Map();
    for (const [key, group] of groups) {
      const hit = !needle || group.name.toLowerCase().includes(needle) || (group.link && group.link.toLowerCase().includes(needle));
      if (!hit) continue;
      if (!bySource.has(group.source)) bySource.set(group.source, []);
      bySource.get(group.source).push([key, group]);
    }
    for (const entries of bySource.values()) entries.sort((a, b) => a[1].name.localeCompare(b[1].name));
    return bySource;
  }

  /** Whether any segment of a grid passes through the plan footprint of a box. */
  function crossesFootprint(grid, box) {
    return grid.segs.some((seg) => {
      const a = worldToLocal(box, [seg[0], seg[1], box.origin[2]]);
      const b = worldToLocal(box, [seg[2], seg[3], box.origin[2]]);
      let enter = 0, leave = 1;
      for (let k = 0; k < 2; k++) {
        const d = b[k] - a[k];
        if (Math.abs(d) < 1e-9) {
          if (a[k] < box.min[k] || a[k] > box.max[k]) return false;
          continue;
        }
        const t0 = (box.min[k] - a[k]) / d, t1 = (box.max[k] - a[k]) / d;
        enter = Math.max(enter, Math.min(t0, t1));
        leave = Math.min(leave, Math.max(t0, t1));
      }
      return enter <= leave;
    });
  }

  /** Indexes of the grids to show around a box: those crossing it, plus the next one each side face would snap to when dragged outward. */
  function relevantGrids(grids, box) {
    const crossing = new Set();
    grids.forEach((grid, index) => {
      if (crossesFootprint(grid, box)) crossing.add(index);
    });
    const shown = new Set(crossing);
    for (let axis = 0; axis < 2; axis++) {
      for (let side = 0; side < 2; side++) {
        const p = faceCenter(box, axis, side), n = faceNormal(box, axis, side);
        let best = null;
        grids.forEach((grid, index) => {
          if (crossing.has(index)) return;
          for (const c of snapCandidates(p, n, { grids: [grid] })) {
            if (c.t > 0 && (best === null || c.t < best.t)) best = { t: c.t, index };
          }
        });
        if (best) shown.add(best.index);
      }
    }
    return shown;
  }

  /**
   * The heights that change when one view range plane is dragged to z, given the planes as the drag started.
   *
   * A plane stops at its neighbours in the plan's order, except that a bottom plane dragged below a view
   * depth it coincided with takes the view depth along. Returns {id: z} for each plane that moves.
   * sectionbox_viewrange_rules.py holds the same order.
   */
  function dragRangePlane(planes, id, z, ceiling) {
    const heights = {};
    for (const plane of planes) heights[plane.id] = plane.z;
    const order = (ceiling ? RANGE_ORDER.ceiling : RANGE_ORDER.floor).filter((name) => name in heights);
    const index = order.indexOf(id);
    if (index < 0) return {};
    const higher = order[index - 1], lower = order[index + 1];
    const carries = !ceiling && id === "bottom" && lower === "depth" && Math.abs(heights.bottom - heights.depth) <= RANGE_COINCIDENT_FT;
    let next = z;
    if (higher !== undefined) next = Math.min(next, heights[higher]);
    if (lower !== undefined && !carries) next = Math.max(next, heights[lower]);
    const moved = { [id]: next };
    if (carries && next < heights.depth) moved.depth = next;
    return moved;
  }

  /** The planes with the heights in moved applied, their project elevations shifted by the same amounts. */
  function withHeights(planes, moved) {
    return planes.map((plane) =>
      plane.id in moved ? Object.assign({}, plane, { z: moved[plane.id], elevation: plane.elevation + moved[plane.id] - plane.z }) : plane
    );
  }

  /** The height whose offset from levelZ is the multiple of step nearest to that of z. */
  function roundToStep(z, levelZ, step) {
    return levelZ + Math.round((z - levelZ) / step) * step;
  }

  /** A typed offset as a number, accepting a decimal comma; null when it is not one. */
  function parseOffset(text) {
    const cleaned = String(text).trim().replace(",", ".");
    const value = Number(cleaned);
    return cleaned && isFinite(value) ? value : null;
  }

  const SETTING_KEYS = ["model", "levels", "allLevels", "grids", "allGrids", "names", "scope", "viewRange", "cut", "ghost", "live", "snap", "sideWidth"];

  /** The persisted display and box settings in a stored object, with unknown or malformed entries dropped. */
  function sanitizeSettings(stored) {
    const clean = {};
    if (!stored || typeof stored !== "object") return clean;
    for (const key of SETTING_KEYS) {
      const value = stored[key];
      if (key === "cut") {
        if (["ghost", "hide", "off"].includes(value)) clean.cut = value;
      } else if (key === "ghost") {
        if (typeof value === "number" && isFinite(value)) clean.ghost = Math.min(0.6, Math.max(0.02, value));
      } else if (key === "sideWidth") {
        if (typeof value === "number" && isFinite(value)) clean.sideWidth = Math.min(SIDE_MAX_PX, Math.max(SIDE_MIN_PX, value));
      } else if (typeof value === "boolean") {
        clean[key] = value;
      }
    }
    return clean;
  }

  /** A group's key: the element source and the group name, so a link's walls stay apart from the host's. */
  function groupKey(source, name) {
    return source + "|" + name;
  }

  const api = {
    cloneBox, localToWorld, worldToLocal, boxCorners, boxCenter, faceNormal, faceCenter, parseFace,
    closestOnAxis, snapCandidates, bestSnap, scopePlanes, snapYaw, moveFace, yawOf, setYaw,
    fitToWorldBounds, insideBox, distanceToSegment2d, triangleHit,
    gridChord, gridsAlongView, isElevationCamera, pinToViewport, groupKey, filterGroups, sanitizeSettings,
    relevantGrids, dragRangePlane, withHeights, roundToStep, parseOffset,
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
    level: [0.88, 0.47, 0.0],
    grid: [0.38, 0.52, 0.0],
    scope: [0.56, 0.27, 0.68],
    snap: [0.953, 0.612, 0.071],
  };
  const THEME_COLORS = {
    light: { box: [0.173, 0.243, 0.314], background: [0.957, 0.965, 0.973] },
    dark: { box: [0.498, 0.651, 0.8], background: [0.106, 0.141, 0.18] },
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

  function groupColor(name, link) {
    if (link) return hslToRgb(30, 0.45, 0.5 + (hashHue(name) % 5) * 0.04);
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
      this.northAngle = payload.northAngle || 0;
      this.guides = { levels: [], grids: [], scopeBoxes: [] };
      this.batches = [];
      this.elements = new Map();
      this.groups = new Map();
      this.modelBounds = null;
      this.progress = [0, 0];
      this.loading = true;
      this.flags = {
        model: true, levels: true, grids: true, names: true, scope: true, viewRange: true,
        cut: "ghost", ghost: 0.12, live: false, snap: true, allLevels: false, allGrids: false, sideWidth: null,
      };
      this.rememberedVisibility = new Map();
      this.failure = null;
      Object.assign(this.flags, sanitizeSettings(payload.settings));
      this.categoryTerm = "";
      this.collapsed = new Set();
      this.mode = null;
      this.hover = null;
      this.drag = null;
      this.pending = 0;
      this.editRevision = 0;
      this.snapHighlight = null;
      this.pendingFrame = 0;
      this.requests = new Map();
      this.rangeRequests = new Set();
      this._build();
      this._bindBridge();
      this.setCameraPreset(this.view.camera ? "view" : "iso");
      this._buildViewCube();
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
      if (action === "apply_view_range") this.rangeRequests.add(requestId);
      return new Promise((resolve) => {
        this.requests.set(requestId, resolve);
        if (window.chrome && window.chrome.webview) {
          const stamped = Object.assign({}, payload, { generation: this.view.generation });
          window.chrome.webview.postMessage({ channel: this.channel, action, payload: stamped, requestId });
        } else {
          resolve({ ok: false });
        }
      });
    }

    _notify(action, payload) {
      if (window.chrome && window.chrome.webview) {
        window.chrome.webview.postMessage({ channel: this.channel, action, payload });
      }
    }

    _saveSettings() {
      const settings = {};
      for (const key of SETTING_KEYS) settings[key] = this.flags[key];
      this._notify("save_settings", { settings });
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
      if (this.viewCube) this.viewCube.dispose();
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
      else if (event === "error") this._onStreamError(payload.message);
    }

    _onStreamError(message) {
      this.loading = false;
      for (const group of this.groups.values()) group.requested = false;
      this._renderCategories();
      this._updateProgress();
      this.setStatus(message, "error");
    }

    onResult(payload) {
      const forRange = this.rangeRequests.delete(payload.requestId);
      const resolve = this.requests.get(payload.requestId);
      if (resolve) {
        this.requests.delete(payload.requestId);
        this.pending = Math.max(0, this.pending - 1);
        resolve(payload);
      }
      if (payload.ok) {
        this.failure = null;
        this.setStatus(this.t("PreviewApplied"), "ok");
      } else {
        this.failure = format(this.t(forRange ? "PreviewRangeFailed" : "PreviewFailed"), payload.message || "");
        this.setStatus(this.failure, "error");
      }
    }

    onSources(payload) {
      if (payload.dropAll) this.dropModel();
      if (payload.done) {
        this.loading = false;
        this._setDropped(payload.dropped || []);
        const key = payload.truncated ? "PreviewTruncated" : "PreviewLoaded";
        this.setStatus(format(this.t(key), this.elements.size, payload.truncated), "info");
        this._updateProgress();
      }
      if (payload.loading) {
        this.loading = true;
        this._updateProgress();
      }
      if (payload.dropLinks) this.dropLinks();
    }

    _newGroup(source, name, link, hidden) {
      const key = groupKey(source, name);
      return {
        name, source, link: link || null, color: groupColor(name, link),
        visible: this.rememberedVisibility.has(key) ? this.rememberedVisibility.get(key) : !hidden,
        count: 0, boxes: 0, dropped: 0, requested: false,
      };
    }

    /** Forgets every streamed element, keeping which categories the user hid, before the model is streamed again. */
    dropModel() {
      for (const [key, group] of this.groups) this.rememberedVisibility.set(key, group.visible);
      this._deleteBatches(this.batches);
      this.batches = [];
      this.elements.clear();
      this.groups.clear();
      this.modelBounds = null;
      this.progress = [0, 0];
      this._clearHover();
      this._renderCategories();
    }

    _deleteBatches(batches) {
      if (!this.gl) return;
      for (const batch of batches) {
        if (batch.vao) this.gl.deleteVertexArray(batch.vao);
        for (const buffer of batch.buffers || []) this.gl.deleteBuffer(buffer);
      }
    }

    _setDropped(dropped) {
      for (const [key, group] of [...this.groups]) {
        group.dropped = 0;
        group.requested = false;
        if (!group.count) this.groups.delete(key);
      }
      for (const entry of dropped) {
        const key = groupKey(entry.source, entry.group);
        let group = this.groups.get(key);
        if (!group) {
          group = this._newGroup(entry.source, entry.group, entry.link, entry.hidden);
          this.groups.set(key, group);
        }
        group.dropped = entry.count;
      }
      this._renderCategories();
    }

    requestGroup(key) {
      const group = this.groups.get(key);
      if (!group || group.requested) return;
      group.requested = true;
      this.commitRequest("load_group", { source: group.source, group: group.name });
      this._renderCategories();
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
      this.splitter = el("div", "sbp-splitter");
      this.main.append(this.stage, this.splitter, this.side);
      this._bindSplitter();
      this._applySideWidth();
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
      this.applyTheme(this.view.theme);

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

    /** Follows the host's theme, or the browser's color scheme when the host sends none. */
    applyTheme(theme) {
      const preferred = !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
      this.dark = theme ? theme === "dark" : preferred;
      document.documentElement.dataset.theme = this.dark ? "dark" : "light";
    }

    _sideLimit() {
      return Math.max(SIDE_MIN_PX, this.main.clientWidth * SIDE_MAX_FRACTION);
    }

    setSideWidth(pixels) {
      this.flags.sideWidth = Math.round(Math.min(this._sideLimit(), Math.max(SIDE_MIN_PX, pixels)));
      this._applySideWidth();
    }

    _applySideWidth() {
      if (!this.flags.sideWidth) return;
      this.side.style.width = Math.min(this.flags.sideWidth, this._sideLimit()) + "px";
    }

    _bindSplitter() {
      const splitter = this.splitter;
      let dragging = false;
      splitter.addEventListener("pointerdown", (e) => {
        dragging = true;
        capture(splitter, e.pointerId, true);
        e.preventDefault();
      });
      splitter.addEventListener("pointermove", (e) => {
        if (!dragging) return;
        this.setSideWidth(this.main.getBoundingClientRect().right - e.clientX);
      });
      splitter.addEventListener("pointerup", (e) => {
        if (!dragging) return;
        dragging = false;
        capture(splitter, e.pointerId, false);
        this._saveSettings();
      });
      splitter.addEventListener("dblclick", () => {
        this.flags.sideWidth = null;
        this.side.style.width = "";
        this._saveSettings();
      });
    }

    _toggle(parent, label, key, onChange) {
      const wrap = el("label", "sbp-toggle");
      const input = el("input");
      input.type = "checkbox";
      input.checked = !!this.flags[key];
      input.addEventListener("change", () => {
        this.flags[key] = input.checked;
        if (onChange) onChange();
        this._saveSettings();
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
      const content = el("div", "sbp-bar-content");
      content.append(...children);
      bar.append(el("span", "sbp-bar-caption", caption), content);
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
      this._toggle(showGroup, this.t("PreviewAllGrids"), "allGrids");
      this._toggle(showGroup, this.t("PreviewNames"), "names");
      this._toggle(showGroup, this.t("PreviewScopeBoxes"), "scope");
      this.rangeToggle = this._toggle(showGroup, this.t("PreviewViewRange"), "viewRange", () => this.refreshChrome());
      const cutGroup = el("div", "sbp-group");
      cutGroup.append(el("span", "sbp-caption", this.t("PreviewCut")));
      this.cutSelect = el("select", "sbp-select");
      for (const [value, key] of [["ghost", "PreviewCutGhost"], ["hide", "PreviewCutHide"], ["off", "PreviewCutOff"]]) {
        const o = el("option", "", this.t(key));
        o.value = value;
        this.cutSelect.append(o);
      }
      this.cutSelect.value = this.flags.cut;
      this.cutSelect.addEventListener("change", () => {
        this.flags.cut = this.cutSelect.value;
        this._saveSettings();
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
      this.ghostRange.addEventListener("change", () => this._saveSettings());
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
      this._buildCategoryHead();
      this.refreshSide();
    }

    _buildCategoryHead() {
      const head = el("div", "sbp-panel-head");
      head.append(el("span", "", this.t("PreviewCategories")));
      const all = el("a", "sbp-link", this.t("PreviewAll"));
      const none = el("a", "sbp-link", this.t("PreviewNone"));
      all.addEventListener("click", () => this._setAllGroups(true));
      none.addEventListener("click", () => this._setAllGroups(false));
      head.append(all, none);
      this.categorySearch = el("input", "sbp-input sbp-search");
      this.categorySearch.type = "search";
      this.categorySearch.placeholder = this.t("PreviewSearch");
      this.categorySearch.addEventListener("input", () => {
        this.categoryTerm = this.categorySearch.value;
        this._renderCategories();
      });
      this.categoryList = el("div", "sbp-category-list");
      this.categoryBox.append(head, this.categorySearch, this.categoryList);
    }

    refreshSide() {
      this._renderCategories();
      this._renderScopeBoxes();
      this._renderBookmarks();
    }

    _renderCategories() {
      const list = this.categoryList;
      list.replaceChildren();
      const searching = this.categoryTerm.trim() !== "";
      const bySource = filterGroups(this.groups, this.categoryTerm);
      for (const [source, entries] of [...bySource].sort((a, b) => a[0] - b[0])) {
        if (source !== 0) list.append(this._linkHeader(source, entries, searching));
        if (source !== 0 && !searching && this.collapsed.has(source)) continue;
        for (const [key, group] of entries) list.append(this._groupRow(key, group));
      }
    }

    _linkHeader(source, entries, searching) {
      const head = el("div", "sbp-chip sbp-link-head");
      const collapsed = !searching && this.collapsed.has(source);
      const chevron = el("span", "sbp-chevron", collapsed ? "▸" : "▾");
      chevron.addEventListener("click", () => {
        if (searching) return;
        if (this.collapsed.has(source)) this.collapsed.delete(source);
        else this.collapsed.add(source);
        this._renderCategories();
      });
      const label = el("label", "sbp-link-label");
      const input = el("input");
      input.type = "checkbox";
      const visible = entries.filter(([, group]) => group.visible).length;
      input.checked = visible === entries.length;
      input.indeterminate = visible > 0 && visible < entries.length;
      input.addEventListener("change", () => {
        for (const [, group] of entries) group.visible = input.checked;
        this._renderCategories();
        this.requestRender();
      });
      label.append(input, el("span", "sbp-link-title", "Link: " + entries[0][1].link), el("span", "sbp-count", `(${entries.length})`));
      head.append(chevron, label);
      return head;
    }

    _groupRow(key, group) {
      const row = el("label", "sbp-chip" + (group.source !== 0 ? " sbp-indent" : ""));
      const input = el("input");
      input.type = "checkbox";
      input.checked = group.visible;
      input.addEventListener("change", () => {
        group.visible = input.checked;
        if (group.source !== 0) this._renderCategories();
        this.requestRender();
      });
      const swatch = el("i", "sbp-swatch");
      swatch.style.background = `rgb(${group.color.map((c) => Math.round(c * 255)).join(",")})`;
      row.append(input, swatch, el("span", "", `${group.name} (${group.count})`));
      if (group.boxes) row.append(el("span", "sbp-note", format(this.t("PreviewBoxes"), group.boxes)));
      if (group.dropped) {
        row.append(el("span", "sbp-note", format(this.t("PreviewNotLoaded"), group.dropped)));
        const load = el("a", "sbp-link", this.t("PreviewLoadGroup"));
        load.classList.toggle("sbp-disabled", group.requested);
        load.addEventListener("click", (e) => {
          e.preventDefault();
          this.requestGroup(key);
        });
        row.append(load);
      }
      return row;
    }

    _setAllGroups(on) {
      for (const entries of filterGroups(this.groups, this.categoryTerm).values()) {
        for (const [, group] of entries) group.visible = on;
      }
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
      this.rangeHandles = {};
      for (const id of Object.keys(RANGE_STRINGS)) this.rangeHandles[id] = this._buildRangeHandle(id);
      this.snapLabel = el("div", "sbp-snap-label");
      this.handleLayer.append(this.snapLabel);
    }

    _buildRangeHandle(id) {
      const handle = el("div", "sbp-plane-handle");
      handle.dataset.plane = id;
      handle.addEventListener("pointerdown", (e) => this._startRangeDrag(e, id));
      const chip = el("button", "sbp-plane-chip");
      chip.type = "button";
      chip.dataset.plane = id;
      chip.addEventListener("click", () => this._typeRangeOffset(id));
      const color = `rgb(${RANGE_COLORS[id].map((c) => Math.round(c * 255)).join(",")})`;
      handle.style.background = color;
      chip.style.borderColor = color;
      handle.style.display = "none";
      chip.style.display = "none";
      this.handleLayer.append(handle, chip);
      return { handle, chip };
    }

    /** The view range planes on screen: none while the toggle is off or the view has no view range. */
    _rangePlanes() {
      const range = this.view.viewRange;
      return this.flags.viewRange && range && this.view.box ? range.planes : [];
    }

    _rangeEditable() {
      return this._rangePlanes().length > 0 && !this.view.viewRange.template;
    }

    /** Why some of the view range cannot be seen or edited, or null. */
    _rangeNotice() {
      const range = this.view.viewRange;
      if (!this.flags.viewRange || !range) return null;
      if (range.template) return format(this.t("PreviewRangeTemplate"), range.template);
      if (!range.relative || !range.relative.length) return null;
      return format(this.t("PreviewRangeRelative"), range.relative.map((id) => this.t(RANGE_STRINGS[id])).join(", "));
    }

    _rangeHandlePoint(plane) {
      const box = this.view.box;
      const at = RANGE_HANDLE_AT[plane.id];
      const p = localToWorld(box, [
        box.min[0] + at * (box.max[0] - box.min[0]),
        box.min[1] + at * (box.max[1] - box.min[1]),
        box.min[2],
      ]);
      return [p[0], p[1], plane.z];
    }

    _rangeCorners(z) {
      const box = this.view.box;
      return [[box.min[0], box.min[1]], [box.max[0], box.min[1]], [box.max[0], box.max[1]], [box.min[0], box.max[1]]].map(([x, y]) => {
        const p = localToWorld(box, [x, y, box.min[2]]);
        return [p[0], p[1], z];
      });
    }

    _rangeLabel(plane, dragged) {
      const offset = plane.z - plane.levelZ;
      const sign = offset < 0 ? "−" : "+";
      const text = `${this.t(RANGE_STRINGS[plane.id])}: ${plane.level} ${sign} ${this.fmt(Math.abs(offset))}`;
      return dragged ? `${text} (${this.fmt(plane.elevation)})` : text;
    }

    _setRangePlanes(planes) {
      this.view.viewRange = Object.assign({}, this.view.viewRange, { planes });
    }

    _commitRange(changes) {
      this.pending += 1;
      this.editRevision += 1;
      this._post("apply_view_range", { planes: changes, revision: this.editRevision });
      this.requestRender();
    }

    /** The current heights of every plane the drag has moved at some point, so a plane carried and then released is restored. */
    _draggedHeights(drag) {
      const changes = {};
      for (const plane of this.view.viewRange.planes) {
        if (drag.touched.has(plane.id)) changes[plane.id] = plane.z;
      }
      return changes;
    }

    _startRangeDrag(e, id) {
      if (this.drag || !this._rangeEditable()) return;
      e.preventDefault();
      e.stopPropagation();
      const target = e.currentTarget;
      capture(target, e.pointerId, true);
      const planes0 = this.view.viewRange.planes.map((plane) => Object.assign({}, plane));
      const p0 = this._rangeHandlePoint(planes0.find((plane) => plane.id === id));
      const ray = this._ray(e);
      const t0 = ray ? closestOnAxis(p0, [0, 0, 1], ray.origin, ray.dir) : null;
      this.drag = { kind: "range", plane: id, planes0, p0, t0: t0 || 0, touched: new Set(), lastSend: 0 };
      const move = (ev) => this._moveRangeDrag(ev);
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

    _moveRangeDrag(e) {
      const d = this.drag;
      if (!d || d.kind !== "range") return;
      const ray = this._ray(e);
      if (!ray) return;
      const t = closestOnAxis(d.p0, [0, 0, 1], ray.origin, ray.dir);
      if (t === null) return;
      const start = d.planes0.find((plane) => plane.id === d.plane);
      let z = start.z + t - d.t0;
      let snap = null;
      if (this.flags.snap && !e.altKey) {
        const candidates = snapCandidates(d.p0, [0, 0, 1], { levels: this.guides.levels });
        const res = bestSnap(z - d.p0[2], candidates, this._toleranceFt(d.p0, SNAP_PIXELS));
        if (res.snap) {
          z = d.p0[2] + res.t;
          snap = res.snap;
        }
      }
      if (!snap) z = roundToStep(z, start.levelZ, this.units.dragStep || RANGE_DEFAULT_STEP_FT);
      const moved = dragRangePlane(d.planes0, d.plane, z, this.view.viewRange.ceiling);
      for (const id of Object.keys(moved)) {
        if (Math.abs(moved[id] - d.planes0.find((plane) => plane.id === id).z) > RANGE_COINCIDENT_FT) d.touched.add(id);
      }
      this._setRangePlanes(withHeights(d.planes0, moved));
      this._setSnapHighlight(snap && Math.abs(moved[d.plane] - z) <= RANGE_COINCIDENT_FT ? snap : null, d);
      this.requestRender();
      this._liveCommit();
    }

    _typeRangeOffset(id) {
      if (this.drag || !this._rangeEditable()) return;
      const planes = this.view.viewRange.planes;
      const plane = planes.find((item) => item.id === id);
      if (!plane) return;
      const unit = this.units.symbol || (Math.abs(this.units.factor - 12) < 0.001 ? "in" : "ft");
      const prompt = format(this.t("PreviewRangeOffsetPrompt"), this.t(RANGE_STRINGS[id]), plane.level, unit);
      const answer = window.prompt(prompt, ((plane.z - plane.levelZ) * this.units.factor).toFixed(this.units.decimals));
      if (answer === null) return;
      const offset = parseOffset(answer);
      if (offset === null) {
        this.setStatus(this.t("PreviewRangeNotANumber"), "error");
        return;
      }
      const z = plane.levelZ + offset / this.units.factor;
      const changes = { [id]: z };
      const moved = dragRangePlane(planes, id, z, this.view.viewRange.ceiling);
      if (id !== "depth" && moved.depth !== undefined) changes.depth = moved.depth;
      this._setRangePlanes(withHeights(planes, changes));
      this._commitRange(changes);
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

    /** Why the crop, the view range or both cannot be edited, or null. */
    _warnings() {
      const blockers = { scope_box: "PreviewBlockedScopeBox", crop_shape: "PreviewBlockedCropShape" };
      const crop = this.view.blocker ? this.t(blockers[this.view.blocker]) : null;
      return [crop, this._rangeNotice()].filter(Boolean).join(" ") || null;
    }

    _resetStatus() {
      if (this.glMissing) this.setStatus("WebGL2 is not available", "error");
      else if (!this.view.box) this.setStatus(this.t("PreviewNoBox"), "warn");
      else if (this._warnings()) this.setStatus(this._warnings(), "warn");
      else if (!this.loading) this.setStatus(this.t(this._rangeEditable() ? "PreviewRangeHelp" : "PreviewHelp"), "info");
    }

    refreshChrome() {
      const box = this.view.box;
      const editable = new Set(this.view.editable || []);
      for (const face of Object.keys(this.handles)) {
        this.handles[face].style.display = box && editable.has(face) ? "" : "none";
      }
      this.rotateHandle.style.display = box && this.view.kind === "3d" ? "" : "none";
      this.alignBtn.style.display = this.view.kind === "3d" ? "" : "none";
      this.rangeToggle.parentNode.style.display = this.view.viewRange ? "" : "none";
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
      if (!resetCamera && typeof payload.revision === "number" && payload.revision < this.editRevision) return;
      this.view = payload;
      this.drag = null;
      if (payload.theme) this.applyTheme(payload.theme);
      this._buildGuideBuffers();
      this.refreshChrome();
      if (this.failure && !resetCamera) this.setStatus(this.failure, "error");
      this.failure = null;
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
      this._deleteBatches(this.batches.filter((b) => b.source !== 0));
      this.batches = this.batches.filter((b) => b.source === 0);
      for (const [key, element] of [...this.elements]) if (element.source !== 0) this.elements.delete(key);
      for (const [key, group] of [...this.groups]) if (group.source !== 0) this.groups.delete(key);
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
        const gkey = groupKey(mesh.source, mesh.group);
        const boxOnly = !!mesh.approx;
        this.elements.set(key, { id: mesh.id, source: mesh.source, group: gkey, bounds, approx: boxOnly });
        this._extendModelBounds(bounds);
        const batchKey = gkey + "|" + (boxOnly ? 1 : 0);
        if (!byGroup.has(batchKey)) byGroup.set(batchKey, { group: gkey, source: mesh.source, approx: boxOnly, parts: [], triangles: 0 });
        const entry = byGroup.get(batchKey);
        entry.parts.push({ positions, indices, key });
        entry.triangles += indices.length / 3;
        let group = this.groups.get(gkey);
        if (!group) {
          group = this._newGroup(mesh.source, mesh.group, mesh.link, mesh.hidden);
          this.groups.set(gkey, group);
        }
        group.count += 1;
        if (boxOnly) group.boxes += 1;
      }
      for (const entry of byGroup.values()) this._addBatch(entry.group, entry);
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
      const buffers = this.gl ? [this._buffer(pos), this._buffer(nrm)] : [];
      const vao = this.gl ? this._vao(this.meshProgram, buffers[0], buffers[1]) : null;
      const batch = { group: name, source: entry.source, approx: entry.approx, vao, buffers, count: entry.triangles * 3, pos };
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
      this.gridChords = this.guides.grids.map(gridChord);
      this.guideZ = { lo: ext.min[2], hi: ext.max[2] };
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
      if (d.kind === "range") {
        this._setRangePlanes(d.planes0);
        if (d.sent) this._commitRange(this._draggedHeights(d));
      } else {
        this.view.box = d.box0;
        if (d.sent) this._commitBox(d.box0);
      }
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
          label: this._elementLabel(element),
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

    _elementLabel(element) {
      const group = this.groups.get(element.group);
      const name = group ? group.name : element.group;
      const prefix = group && group.link ? group.link + " · " : "";
      return `${prefix}${name} · ${element.id}` + (element.approx ? " · " + this.t("PreviewBoxOnly") : "");
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

    _elevation() {
      return isElevationCamera(this.camera);
    }

    _gridSpan() {
      const base = this.guideZ || { lo: 0, hi: 0 };
      const pad = Math.max(GRID_SPAN_PAD * (base.hi - base.lo), 1);
      return { lo: base.lo - pad, hi: base.hi + pad };
    }

    /** All grids with the toggle on, without a box or while picking one to align to; else the ones around the box. */
    _visibleGridIndexes() {
      const grids = this.guides.grids;
      const all = grids.map((_, i) => i);
      if (this.flags.allGrids || !this.view.box || this.mode === "grid") return all;
      const shown = relevantGrids(grids, this.view.box);
      const snap = this.snapHighlight;
      if (snap && snap.kind === "grid") {
        grids.forEach((grid, i) => {
          if (grid.name === snap.name) shown.add(i);
        });
      }
      return all.filter((i) => shown.has(i));
    }

    _elevationGridLines() {
      const grids = this.guides.grids;
      const span = this._gridSpan();
      const visible = new Set(this._visibleGridIndexes());
      return gridsAlongView(grids, this.camera.yaw, GRID_ALONG_VIEW)
        .filter((index) => visible.has(index))
        .map((index) => ({ index, mid: this.gridChords[index].mid, lo: span.lo, hi: span.hi }));
    }

    _guideSegments() {
      const grids = this.guides.grids;
      if (this._elevation()) {
        return this._elevationGridLines().map((line) => {
          const segs = grids[line.index].segs;
          const first = segs[0], last = segs[segs.length - 1];
          return {
            grid: grids[line.index],
            seg: [first[0], first[1], last[2], last[3]],
            a: [line.mid[0], line.mid[1], line.lo],
            b: [line.mid[0], line.mid[1], line.hi],
          };
        });
      }
      const out = [];
      for (const index of this._visibleGridIndexes()) {
        const grid = grids[index];
        for (const s of grid.segs) out.push({ grid, seg: s, a: [s[0], s[1], this.gridZ], b: [s[2], s[3], this.gridZ] });
      }
      return out;
    }

    _gridAt(e) {
      if (this.view.kind !== "3d") return null;
      const rect = this.canvas.getBoundingClientRect();
      const px = e.clientX - rect.left, py = e.clientY - rect.top;
      const vp = this._matrices().viewProj;
      let best = null, bestD = 14;
      for (const item of this._guideSegments()) {
        const a = this._project(vp, item.a);
        const b = this._project(vp, item.b);
        if (!a || !b) continue;
        const d = distanceToSegment2d(px, py, a.x, a.y, b.x, b.y);
        if (d < bestD) {
          bestD = d;
          best = { grid: item.grid, seg: item.seg };
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
      if (d.kind === "range" && !d.touched.size) return;
      d.lastSend = now;
      d.sent = true;
      if (d.kind === "range") this._commitRange(this._draggedHeights(d));
      else this._commitBox(this.view.box, true);
    }

    _endDrag() {
      const d = this.drag;
      this.drag = null;
      this.snapHighlight = null;
      this.snapLabel.style.display = "none";
      if (d && d.kind === "range") {
        if (d.touched.size) this._commitRange(this._draggedHeights(d));
      } else if (d) {
        this._commitBox(this.view.box);
      }
      this._buildGuideBuffers();
      this.requestRender();
    }

    _commitBox(box, keepDrag) {
      this.view.box = box;
      this.pending += 1;
      this.editRevision += 1;
      this._post("apply_box", { box, revision: this.editRevision });
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
      this._applySideWidth();
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

    _drawBatches(gl, program, alphaFor, approx) {
      for (const batch of this.batches) {
        if (approx !== undefined && batch.approx !== approx) continue;
        const group = this.groups.get(batch.group);
        if (!group || !group.visible) continue;
        gl.uniform4fv(program.uniforms.uColor, [...group.color, alphaFor]);
        gl.bindVertexArray(batch.vao);
        gl.drawArrays(gl.TRIANGLES, 0, batch.count);
      }
    }

    _buildViewCube() {
      if (!S3.createViewCube) return;
      this.viewCube = S3.createViewCube({
        parent: this.stage,
        className: "sbp-viewcube",
        getCamera: () => this.camera,
        onChange: () => this.requestRender(),
        labels: {
          top: this.t("PreviewTop"), bottom: this.t("PreviewCubeBottom"), front: this.t("PreviewFront"),
          back: this.t("PreviewCubeBack"), left: this.t("PreviewCubeLeft"), right: this.t("PreviewCubeRight"),
        },
        compass: this.t("PreviewCompass").split(","),
        northAngle: this.northAngle,
      });
    }

    _render() {
      const { eye, viewProj } = this._matrices();
      this.viewProj = viewProj;
      if (this.viewCube) this.viewCube.update();
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
      const bg = this._themeColors().background;
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
        this._drawBatches(gl, mp, 1, false);
        gl.disable(gl.POLYGON_OFFSET_FILL);
        this._drawHoverElement(gl, mp);
        this._drawBoxOnlyElements(gl, mp, cutting ? 1 : 0);
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

    _themeColors() {
      return this.dark ? THEME_COLORS.dark : THEME_COLORS.light;
    }

    _drawBoxOnlyElements(gl, mp, mode) {
      if (!this.batches.some((batch) => batch.approx)) return;
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
      gl.depthMask(false);
      this._boxUniforms(gl, mp, mode);
      this._drawBatches(gl, mp, BOX_ONLY_ALPHA, true);
      gl.depthMask(true);
      gl.disable(gl.BLEND);
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
      for (const item of this._guideSegments()) {
        if (item.grid !== hover.grid) continue;
        const a = this._project(viewProj, item.a);
        const b = this._project(viewProj, item.b);
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
        if (this._elevation()) this._drawElevationGrids(gl, fp);
        else this._drawPlanGrids(gl, fp);
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
      this._drawViewRange(gl, fp);
      if (this.hover) this._drawWireBox(gl, fp, this.hover.box, COLORS.snap, 1);
      gl.enable(gl.DEPTH_TEST);
    }

    _drawViewRange(gl, fp) {
      const planes = this._rangePlanes();
      if (!planes.length) return;
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
      for (const plane of planes) {
        const color = RANGE_COLORS[plane.id];
        const q = this._rangeCorners(plane.z);
        const active = this.drag && this.drag.plane === plane.id;
        this._drawDynamic(gl, fp, new Float32Array([...q[0], ...q[1], ...q[2], ...q[0], ...q[2], ...q[3]]), gl.TRIANGLES, [...color, active ? 0.2 : 0.05]);
        this._drawDynamic(gl, fp, new Float32Array([...q[0], ...q[1], ...q[1], ...q[2], ...q[2], ...q[3], ...q[3], ...q[0]]), gl.LINES, [...color, 0.95]);
      }
      gl.disable(gl.BLEND);
    }

    _drawPlanGrids(gl, fp) {
      const grids = this.guides.grids;
      gl.uniform4fv(fp.uniforms.uColor, [...COLORS.grid, 0.9]);
      gl.bindVertexArray(this.gridVao);
      for (const index of this._visibleGridIndexes()) {
        const range = this.gridRanges[index];
        gl.drawArrays(gl.LINES, range.first, range.count);
      }
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

    _drawElevationGrids(gl, fp) {
      const lines = this._elevationGridLines();
      if (!lines.length) return;
      const verticals = (subset) => {
        const data = new Float32Array(subset.length * 6);
        subset.forEach((line, i) => data.set([line.mid[0], line.mid[1], line.lo, line.mid[0], line.mid[1], line.hi], i * 6));
        return data;
      };
      this._drawDynamic(gl, fp, verticals(lines), gl.LINES, [...COLORS.grid, 0.9]);
      const snap = this.snapHighlight;
      if (snap && snap.kind === "grid") {
        const shown = lines.filter((line) => this.guides.grids[line.index].name === snap.name);
        if (shown.length) this._drawDynamic(gl, fp, verticals(shown), gl.LINES, [...COLORS.snap, 1]);
      }
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
      const boxColor = this._themeColors().box;
      this._drawDynamic(gl, fp, new Float32Array(all), gl.TRIANGLES, [...boxColor, 0.05]);
      gl.disable(gl.BLEND);
      this._drawWireBox(gl, fp, box, boxColor, 1);
      void editable;
    }

    _pinnedLevelPoint(viewProj, z, labelWidth) {
      const r = this.guideRect;
      const corners = [[r.x0, r.y0], [r.x1, r.y0], [r.x1, r.y1], [r.x0, r.y1]]
        .map((c) => this._project(viewProj, [c[0], c[1], z]))
        .filter(Boolean)
        .sort((a, b) => a.x - b.x);
      if (!corners.length) return null;
      const left = corners[0], right = corners[corners.length - 1];
      return pinToViewport([left.x, left.y], [right.x, right.y], labelWidth + LABEL_PIN_PX + LABEL_DOT_PX);
    }

    _pinnedGridPoint(viewProj, line) {
      const top = this._project(viewProj, [line.mid[0], line.mid[1], line.hi]);
      const bottom = this._project(viewProj, [line.mid[0], line.mid[1], line.lo]);
      if (!top || !bottom) return null;
      if (top.y >= LABEL_PIN_PX) return top;
      return bottom.y >= LABEL_PIN_PX ? { x: top.x, y: LABEL_PIN_PX } : null;
    }

    _renderLabels(viewProj) {
      const candidates = [];
      const width = this.canvas.clientWidth, height = this.canvas.clientHeight;
      const add = (text, p, className, end) => {
        if (!p || p.x < -20 || p.x > width + 20 || p.y < -20 || p.y > height + 20) return;
        candidates.push({ text, x: p.x, y: p.y, className, end: !!end });
      };
      const place = (text, point, className) => add(text, this._project(viewProj, point), className);
      if (this.flags.names && this.guideRect) {
        const r = this.guideRect;
        const elevationView = this._elevation();
        const lookingDown = Math.abs(this.camera.pitch) > (70 * Math.PI) / 180;
        if (this.flags.levels && !lookingDown) {
          const levels = this.guides.levels;
          for (const i of this._visibleLevelIndexes()) {
            const level = levels[i];
            const elevation = level.elevation === undefined ? level.z : level.elevation;
            const text = `${level.name} (${this.fmt(elevation)})`;
            if (elevationView) add(text, this._pinnedLevelPoint(viewProj, level.z, text.length * LABEL_CHAR_PX + LABEL_PAD_PX), "sbp-label-level", true);
            else place(text, [r.x0, r.y0, level.z], "sbp-label-level");
          }
        }
        if (this.flags.grids && elevationView) {
          for (const line of this._elevationGridLines()) {
            add(this.guides.grids[line.index].name, this._pinnedGridPoint(viewProj, line), "sbp-label-grid");
          }
        } else if (this.flags.grids) {
          for (const index of this._visibleGridIndexes()) {
            const grid = this.guides.grids[index];
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
        const w = item.text.length * LABEL_CHAR_PX + LABEL_PAD_PX;
        const left = item.end ? item.x - w - LABEL_DOT_PX : item.x;
        const clash = kept.some((o) => left < o.left + o.w && o.left < left + w && Math.abs(item.y - o.y) < 15);
        if (!clash) kept.push({ ...item, w, left });
      }
      this.labelLayer.replaceChildren(
        ...kept.map((item) => {
          const node = el("span", "sbp-label " + item.className + (item.end ? " sbp-label-end" : ""), item.text);
          node.style.left = item.x + "px";
          node.style.top = item.y + "px";
          return node;
        })
      );
    }

    _placeRangeHandles(viewProj) {
      const planes = this._rangePlanes();
      const topDown = Math.abs(this.camera.pitch) > RANGE_TOP_PITCH;
      const editable = this._rangeEditable();
      const placed = [], handles = [];
      for (const [id, parts] of Object.entries(this.rangeHandles)) {
        const plane = planes.find((item) => item.id === id);
        const p = plane && !topDown ? this._project(viewProj, this._rangeHandlePoint(plane)) : null;
        parts.handle.style.display = p && editable ? "" : "none";
        parts.chip.style.display = p ? "" : "none";
        if (!p) continue;
        const dragged = !!(this.drag && this.drag.plane === id);
        parts.handle.style.left = p.x + "px";
        parts.handle.style.top = p.y + "px";
        parts.handle.classList.toggle("sbp-active", dragged);
        parts.chip.textContent = this._rangeLabel(plane, dragged);
        parts.chip.title = this.fmt(plane.elevation);
        parts.chip.disabled = !editable;
        const w = parts.chip.offsetWidth || parts.chip.textContent.length * LABEL_CHAR_PX + LABEL_PAD_PX;
        const fits = p.x + RANGE_HANDLE_GAP_PX + w <= this.canvas.clientWidth;
        placed.push({ parts, x: fits ? p.x + RANGE_HANDLE_GAP_PX : Math.max(0, p.x - RANGE_HANDLE_GAP_PX - w), y: p.y, w });
        if (editable) handles.push({ x: p.x - RANGE_HANDLE_GAP_PX + 2, y: p.y, w: 2 * RANGE_HANDLE_GAP_PX - 4 });
      }
      const kept = handles;
      for (const item of placed.sort((a, b) => a.y - b.y)) {
        let clash = true;
        while (clash) {
          const other = kept.find((o) => item.x < o.x + o.w && o.x < item.x + item.w && Math.abs(item.y - o.y) < RANGE_CHIP_PX);
          clash = !!other;
          if (other) item.y = other.y + RANGE_CHIP_PX + 1;
        }
        kept.push(item);
        item.parts.chip.style.left = item.x + "px";
        item.parts.chip.style.top = item.y + "px";
      }
    }

    _placeHandles(viewProj) {
      this._placeRangeHandles(viewProj);
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
        const dragged = this.drag.kind === "range" && this._rangePlanes().find((item) => item.id === this.drag.plane);
        const ref = dragged ? this._rangeHandlePoint(dragged) : this.drag.face ? faceCenter(box, this.drag.axis, this.drag.side) : boxCenter(box);
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
