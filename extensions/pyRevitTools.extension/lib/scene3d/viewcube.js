/*
 * Opt-in view cube for the pyRevit scene previews, modelled on Revit's ViewCube:
 * a labelled cube that mirrors the orbit camera, with a compass ring around it.
 *
 * Needs gl.js (window.pyRevitScene3D) loaded first and adds
 * window.pyRevitScene3D.createViewCube and window.pyRevitScene3D.viewCube. A
 * page that never loads this file never shows a cube; gl.js does not depend on it.
 *
 * The cube lives in world axes: TOP is +Z, FRONT faces -Y and RIGHT faces +X.
 * The compass ring is turned by options.northAngle, the angle in radians from
 * the +Y axis clockwise (seen from above) to true north, so N points to +Y for
 * a project without a rotated true north. Clicking a face, an edge or a corner moves the
 * camera to look from that direction, clicking a compass letter turns the
 * camera to that heading at its current pitch, and dragging the cube orbits.
 * The cube is drawn as inline SVG, so it needs no extra GL context, and takes
 * its colors from the CSS custom properties --scene3d-cube-face, -edge, -hover,
 * -line, -text, -ring, -compass and -compass-halo, with light defaults.
 */
(function () {
  "use strict";

  const S3 = window.pyRevitScene3D;
  const { v3 } = S3;

  const SVG_NS = "http://www.w3.org/2000/svg";
  const EYE_DISTANCE = 12.5;
  const EDGE_BAND = 0.62;
  const RING_RADIUS = 1.95;
  const RING_Z = -1.05;
  const RING_SEGMENTS = 72;
  const HALF_EXTENT = 2.45;
  const DRAG_PIXELS = 3;
  const COMPASS_HIT_PIXELS = 9;
  const FACES = {
    top: { n: [0, 0, 1], u: [1, 0, 0], v: [0, 1, 0], shade: 1 },
    bottom: { n: [0, 0, -1], u: [1, 0, 0], v: [0, -1, 0], shade: 0.78 },
    front: { n: [0, -1, 0], u: [1, 0, 0], v: [0, 0, 1], shade: 0.94 },
    back: { n: [0, 1, 0], u: [-1, 0, 0], v: [0, 0, 1], shade: 0.84 },
    right: { n: [1, 0, 0], u: [0, 1, 0], v: [0, 0, 1], shade: 0.88 },
    left: { n: [-1, 0, 0], u: [0, -1, 0], v: [0, 0, 1], shade: 0.8 },
  };
  const FACE_NAMES = Object.keys(FACES);
  const BANDS = [[-1, -EDGE_BAND], [-EDGE_BAND, EDGE_BAND], [EDGE_BAND, 1]];
  const DEFAULT_LABELS = { top: "Top", bottom: "Bottom", front: "Front", back: "Back", left: "Left", right: "Right" };
  const DEFAULT_COMPASS = ["N", "E", "S", "W"];

  function viewBasis(camera) {
    const { back, right, up } = S3.cameraBasis(camera);
    return { d: back, right, up };
  }

  function projector(basis, size) {
    const scale = size / 2 / HALF_EXTENT;
    const center = size / 2;
    return (p) => {
      const depth = v3.dot(p, basis.d);
      const s = 1 / (1 - depth / EYE_DISTANCE);
      return [center + scale * v3.dot(p, basis.right) * s, center - scale * v3.dot(p, basis.up) * s, depth];
    };
  }

  function faceFacesViewer(basis, face) {
    return EYE_DISTANCE * v3.dot(FACES[face].n, basis.d) - 1 > 0;
  }

  function onFace(face, a, b) {
    const f = FACES[face];
    return v3.add(f.n, v3.add(v3.scale(f.u, a), v3.scale(f.v, b)));
  }

  /** Direction from the cube center toward the viewer for a face cell: the face (0, 0), an edge or a corner. */
  function cellDirection(face, iu, iv) {
    const f = FACES[face];
    return v3.norm(v3.add(f.n, v3.add(v3.scale(f.u, iu), v3.scale(f.v, iv))));
  }

  function cellsOf(project, face) {
    const cells = [];
    for (let iu = -1; iu <= 1; iu++) {
      for (let iv = -1; iv <= 1; iv++) {
        const [u0, u1] = BANDS[iu + 1];
        const [v0, v1] = BANDS[iv + 1];
        cells.push({
          face,
          iu,
          iv,
          dir: cellDirection(face, iu, iv),
          points: [onFace(face, u0, v0), onFace(face, u1, v0), onFace(face, u1, v1), onFace(face, u0, v1)].map(project),
        });
      }
    }
    return cells;
  }

  function insideQuad(points, x, y) {
    let sign = 0;
    for (let i = 0; i < points.length; i++) {
      const a = points[i], b = points[(i + 1) % points.length];
      const cross = (b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0]);
      if (cross === 0) continue;
      if (sign === 0) sign = Math.sign(cross);
      else if (Math.sign(cross) !== sign) return false;
    }
    return true;
  }

  /** The compass letters as {key, dir}, with N at the bearing northAngle clockwise from +Y. */
  function compassEntries(northAngle) {
    const s = Math.sin(northAngle || 0), c = Math.cos(northAngle || 0);
    return [
      { key: "n", dir: [s, c, 0] },
      { key: "e", dir: [c, -s, 0] },
      { key: "s", dir: [-s, -c, 0] },
      { key: "w", dir: [-c, s, 0] },
    ];
  }

  function compassPoint(entry) {
    return [entry.dir[0] * RING_RADIUS, entry.dir[1] * RING_RADIUS, RING_Z];
  }

  /**
   * What a pointer at (x, y) of a cube of the given pixel size points at.
   * A compass letter is drawn above the cube, so the nearest letter in reach wins over a face.
   *
   * Returns {kind: "cell", face, iu, iv, dir}, {kind: "compass", key, dir} or null.
   * northAngle turns the compass as in createViewCube.
   */
  function hitTest(camera, size, x, y, northAngle) {
    const basis = viewBasis(camera);
    const project = projector(basis, size);
    let nearest = null, nearestGap = COMPASS_HIT_PIXELS;
    for (const entry of compassEntries(northAngle)) {
      const p = project(compassPoint(entry));
      const gap = Math.hypot(p[0] - x, p[1] - y);
      if (gap <= nearestGap) {
        nearest = entry;
        nearestGap = gap;
      }
    }
    if (nearest) return { kind: "compass", key: nearest.key, dir: nearest.dir };
    const visible = FACE_NAMES.filter((face) => faceFacesViewer(basis, face));
    visible.sort((a, b) => v3.dot(FACES[b].n, basis.d) - v3.dot(FACES[a].n, basis.d));
    for (const face of visible) {
      const cell = cellsOf(project, face).find((c) => insideQuad(c.points, x, y));
      if (cell) return { kind: "cell", face, iu: cell.iu, iv: cell.iv, dir: cell.dir };
    }
    return null;
  }

  /** The pixel position of each compass letter, {n, e, s, w}, as drawn for this camera. */
  function compassScreenPoints(camera, size, northAngle) {
    const project = projector(viewBasis(camera), size);
    const points = {};
    for (const entry of compassEntries(northAngle)) {
      const p = project(compassPoint(entry));
      points[entry.key] = [p[0], p[1]];
    }
    return points;
  }

  /** The camera angles {yaw, pitch} that look from a hit's direction; a compass hit keeps the current pitch. */
  function cameraFor(hit, camera) {
    const [x, y, z] = hit.dir;
    const horizontal = Math.hypot(x, y);
    const yaw = horizontal < 1e-6 ? camera.yaw : Math.atan2(y, x);
    if (hit.kind === "compass") return { yaw, pitch: camera.pitch };
    const pitch = horizontal < 1e-6 ? (Math.sign(z) * Math.PI) / 2 : Math.atan2(z, horizontal);
    return { yaw, pitch };
  }

  function svg(tag, attributes) {
    const node = document.createElementNS(SVG_NS, tag);
    for (const [name, value] of Object.entries(attributes || {})) node.setAttribute(name, value);
    return node;
  }

  function polygon(points, fill, extra) {
    return svg("polygon", Object.assign({ points: points.map((p) => p[0].toFixed(2) + "," + p[1].toFixed(2)).join(" "), fill }, extra));
  }

  function labelFontSize(text) {
    return Math.min(0.5, 2.8 / Math.max(text.length, 1));
  }

  /**
   * Create a view cube and append it to options.parent.
   *
   * options: {parent, getCamera, onChange, labels, compass, northAngle, size, className, onPick}.
   * getCamera returns the live camera state {yaw, pitch, ...} of the viewer.
   * By default a click or drag edits that camera and calls onChange; onPick
   * (hit, {yaw, pitch}) replaces the click edit, for viewers that animate.
   * labels names the six faces and compass lists the letters N, E, S, W.
   *
   * Returns {element, update, hit, dispose}; call update() after the camera moved.
   */
  function createViewCube(options) {
    const size = options.size || 120;
    const labels = Object.assign({}, DEFAULT_LABELS, options.labels);
    const compass = options.compass || DEFAULT_COMPASS;
    const north = options.northAngle || 0;
    const root = svg("svg", { width: size, height: size, viewBox: "0 0 " + size + " " + size, class: "scene3d-viewcube" });
    if (options.className) root.setAttribute("class", "scene3d-viewcube " + options.className);
    root.style.touchAction = "none";
    root.style.userSelect = "none";
    root.style.cursor = "pointer";
    root.style.overflow = "visible";
    const state = { hover: null, gesture: null, disposed: false, signature: null };

    function paintRing(project, layer) {
      const points = [];
      for (let i = 0; i < RING_SEGMENTS; i++) {
        const a = (i / RING_SEGMENTS) * 2 * Math.PI;
        points.push(project([Math.cos(a) * RING_RADIUS, Math.sin(a) * RING_RADIUS, RING_Z]));
      }
      layer.append(polygon(points, "none", { stroke: "var(--scene3d-cube-ring, rgba(150,160,172,0.55))", "stroke-width": size * 0.085 }));
    }

    function paintCompass(project, layer) {
      compassEntries(north).forEach((entry, index) => {
        const p = project(compassPoint(entry));
        const letter = svg("text", {
          x: p[0],
          y: p[1],
          "text-anchor": "middle",
          "dominant-baseline": "central",
          "font-size": size * 0.095,
          "font-weight": 700,
          "font-family": "Segoe UI, sans-serif",
          fill: "var(--scene3d-cube-compass, #3f4852)",
          stroke: "var(--scene3d-cube-compass-halo, #ffffff)",
          "stroke-width": size * 0.03,
          "paint-order": "stroke",
          "pointer-events": "none",
        });
        const hover = state.hover;
        if (hover && hover.kind === "compass" && hover.key === entry.key) letter.setAttribute("fill", "var(--scene3d-cube-hover, #2f7fed)");
        letter.textContent = compass[index] || DEFAULT_COMPASS[index];
        layer.append(letter);
      });
    }

    function paintFace(project, face, layer) {
      const group = svg("g", { opacity: FACES[face].shade });
      const hover = state.hover;
      for (const cell of cellsOf(project, face)) {
        const centered = cell.iu === 0 && cell.iv === 0;
        const hovered = hover && hover.kind === "cell" && hover.face === face && hover.iu === cell.iu && hover.iv === cell.iv;
        const fill = hovered ? "var(--scene3d-cube-hover, #2f7fed)" : centered ? "var(--scene3d-cube-face, #dde2e8)" : "var(--scene3d-cube-edge, #c0c8d1)";
        group.append(polygon(cell.points, fill, { stroke: "var(--scene3d-cube-line, #9aa4af)", "stroke-width": 0.8, "stroke-linejoin": "round" }));
      }
      const text = String(labels[face]).toUpperCase();
      const c = project(FACES[face].n);
      const u = project(onFace(face, 1, 0)), v = project(onFace(face, 0, 1));
      const fontSize = labelFontSize(text);
      const ux = u[0] - c[0], uy = u[1] - c[1], vx = v[0] - c[0], vy = v[1] - c[1];
      const label = svg("text", {
        transform: "matrix(" + [ux, uy, -vx, -vy, c[0], c[1]].map((n) => n.toFixed(4)).join(" ") + ")",
        "text-anchor": "middle",
        "dominant-baseline": "central",
        "font-size": fontSize,
        "font-weight": 700,
        "font-family": "Segoe UI, sans-serif",
        fill: "var(--scene3d-cube-text, #4b5662)",
        "pointer-events": "none",
      });
      label.textContent = text;
      group.append(label);
      layer.append(group);
    }

    function update() {
      if (state.disposed) return;
      const camera = options.getCamera();
      const hover = state.hover;
      const signature = [camera.yaw.toFixed(4), camera.pitch.toFixed(4), hover ? [hover.kind, hover.face, hover.iu, hover.iv, hover.key].join(":") : ""].join("|");
      if (signature === state.signature) return;
      state.signature = signature;
      const basis = viewBasis(camera);
      const project = projector(basis, size);
      const layer = svg("g");
      const below = camera.pitch < 0;
      if (!below) paintRing(project, layer);
      const visible = FACE_NAMES.filter((face) => faceFacesViewer(basis, face));
      visible.sort((a, b) => v3.dot(FACES[a].n, basis.d) - v3.dot(FACES[b].n, basis.d));
      for (const face of visible) paintFace(project, face, layer);
      if (below) paintRing(project, layer);
      paintCompass(project, layer);
      root.replaceChildren(layer);
    }

    function localPoint(event) {
      const rect = root.getBoundingClientRect();
      const scale = rect.width ? size / rect.width : 1;
      return [(event.clientX - rect.left) * scale, (event.clientY - rect.top) * scale];
    }

    function pick(hit) {
      const camera = options.getCamera();
      const target = cameraFor(hit, camera);
      if (options.onPick) options.onPick(hit, target);
      else Object.assign(camera, target);
      if (options.onChange) options.onChange();
      update();
    }

    function setHover(hit) {
      const same = (a, b) => (!a && !b) || (a && b && a.kind === b.kind && a.face === b.face && a.iu === b.iu && a.iv === b.iv && a.key === b.key);
      if (same(hit, state.hover)) return;
      state.hover = hit;
      update();
    }

    const onDown = (event) => {
      event.stopPropagation();
      if (state.gesture) return;
      try {
        root.setPointerCapture(event.pointerId);
      } catch (error) {
        void error;
      }
      state.gesture = { pointerId: event.pointerId, x: event.clientX, y: event.clientY, moved: false };
    };
    const onMove = (event) => {
      const gesture = state.gesture;
      if (gesture && event.pointerId !== gesture.pointerId) return;
      if (!gesture) {
        const [x, y] = localPoint(event);
        setHover(hitTest(options.getCamera(), size, x, y, north));
        return;
      }
      const dx = event.clientX - gesture.x, dy = event.clientY - gesture.y;
      if (!gesture.moved && Math.abs(dx) + Math.abs(dy) <= DRAG_PIXELS) return;
      gesture.moved = true;
      gesture.x = event.clientX;
      gesture.y = event.clientY;
      S3.cameraOrbit(options.getCamera(), dx, dy);
      if (options.onChange) options.onChange();
      update();
    };
    const onCancel = (event) => {
      if (state.gesture && event.pointerId === state.gesture.pointerId) state.gesture = null;
    };
    const onUp = (event) => {
      const gesture = state.gesture;
      if (gesture && event.pointerId !== gesture.pointerId) return;
      state.gesture = null;
      try {
        root.releasePointerCapture(event.pointerId);
      } catch (error) {
        void error;
      }
      if (!gesture || gesture.moved) return;
      const [x, y] = localPoint(event);
      const hit = hitTest(options.getCamera(), size, x, y, north);
      if (hit) pick(hit);
    };
    const onLeave = () => setHover(null);
    root.addEventListener("pointerdown", onDown);
    root.addEventListener("pointermove", onMove);
    root.addEventListener("pointerup", onUp);
    root.addEventListener("pointercancel", onCancel);
    root.addEventListener("lostpointercapture", onCancel);
    root.addEventListener("pointerleave", onLeave);
    options.parent.append(root);
    update();

    return {
      element: root,
      update,
      hit: (x, y) => hitTest(options.getCamera(), size, x, y, north),
      dispose() {
        state.disposed = true;
        root.remove();
      },
    };
  }

  S3.viewCube = { FACES, cellDirection, compassEntries, compassScreenPoints, hitTest, cameraFor, viewBasis };
  S3.createViewCube = createViewCube;
})();
