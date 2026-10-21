/*
 * Dependency-free WebGL2 viewer for the Diagnose Invisibility 3D preview.
 *
 * Draws the diagnosed elements (colored by visibility status) together with
 * the view's clipping context: section box and crop wireframes, and
 * translucent view range / cut planes. Scene coordinates are Revit feet
 * relative to scene.origin, Z up.
 *
 * Exposes window.pyRevitInvisibilityViewer (class). Rendering is on demand:
 * nothing draws unless the camera, a layer, a status or the size changes.
 */
(function () {
  "use strict";

  const COLORS = {
    visible: [0.62, 0.70, 0.78, 1.0],
    visibleEdge: [0.29, 0.36, 0.42, 1.0],
    hidden: [0.90, 0.28, 0.30, 1.0],
    hiddenEdge: [0.55, 0.10, 0.14, 1.0],
    highlight: [0.96, 0.65, 0.14, 1.0],
    highlightEdge: [0.55, 0.33, 0.0, 1.0],
    background: [0.972, 0.976, 0.98, 1.0],
    overlay: {
      section_box: [0.18, 0.50, 0.93],
      crop: [0.56, 0.27, 0.68],
      top: [0.88, 0.47, 0.0],
      cut: [0.78, 0.15, 0.31],
      bottom: [0.38, 0.52, 0.0],
      depth: [0.18, 0.50, 0.93],
      far: [0.56, 0.27, 0.68],
    },
  };
  const PLANE_ALPHA = 0.10;
  const FOV = (40 * Math.PI) / 180;
  const MAX_PITCH = (89.5 * Math.PI) / 180;

  const v3 = {
    sub: (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]],
    add: (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]],
    scale: (a, s) => [a[0] * s, a[1] * s, a[2] * s],
    dot: (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2],
    cross: (a, b) => [
      a[1] * b[2] - a[2] * b[1],
      a[2] * b[0] - a[0] * b[2],
      a[0] * b[1] - a[1] * b[0],
    ],
    len: (a) => Math.hypot(a[0], a[1], a[2]),
    norm: (a) => {
      const l = Math.hypot(a[0], a[1], a[2]) || 1;
      return [a[0] / l, a[1] / l, a[2] / l];
    },
  };

  const m4 = {
    perspective(fovy, aspect, near, far) {
      const f = 1 / Math.tan(fovy / 2);
      const nf = 1 / (near - far);
      return [f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) * nf, -1, 0, 0, 2 * far * near * nf, 0];
    },
    ortho(halfW, halfH, near, far) {
      const nf = 1 / (near - far);
      return [1 / halfW, 0, 0, 0, 0, 1 / halfH, 0, 0, 0, 0, 2 * nf, 0, 0, 0, (far + near) * nf, 1];
    },
    lookAt(eye, target, up) {
      const z = v3.norm(v3.sub(eye, target));
      const x = v3.norm(v3.cross(up, z));
      const y = v3.cross(z, x);
      return [
        x[0], y[0], z[0], 0,
        x[1], y[1], z[1], 0,
        x[2], y[2], z[2], 0,
        -v3.dot(x, eye), -v3.dot(y, eye), -v3.dot(z, eye), 1,
      ];
    },
    mul(a, b) {
      const out = new Array(16);
      for (let c = 0; c < 4; c++) {
        for (let r = 0; r < 4; r++) {
          let s = 0;
          for (let k = 0; k < 4; k++) s += a[k * 4 + r] * b[c * 4 + k];
          out[c * 4 + r] = s;
        }
      }
      return out;
    },
    invert(m) {
      const inv = new Array(16);
      inv[0] = m[5] * m[10] * m[15] - m[5] * m[11] * m[14] - m[9] * m[6] * m[15] + m[9] * m[7] * m[14] + m[13] * m[6] * m[11] - m[13] * m[7] * m[10];
      inv[4] = -m[4] * m[10] * m[15] + m[4] * m[11] * m[14] + m[8] * m[6] * m[15] - m[8] * m[7] * m[14] - m[12] * m[6] * m[11] + m[12] * m[7] * m[10];
      inv[8] = m[4] * m[9] * m[15] - m[4] * m[11] * m[13] - m[8] * m[5] * m[15] + m[8] * m[7] * m[13] + m[12] * m[5] * m[11] - m[12] * m[7] * m[9];
      inv[12] = -m[4] * m[9] * m[14] + m[4] * m[10] * m[13] + m[8] * m[5] * m[14] - m[8] * m[6] * m[13] - m[12] * m[5] * m[10] + m[12] * m[6] * m[9];
      inv[1] = -m[1] * m[10] * m[15] + m[1] * m[11] * m[14] + m[9] * m[2] * m[15] - m[9] * m[3] * m[14] - m[13] * m[2] * m[11] + m[13] * m[3] * m[10];
      inv[5] = m[0] * m[10] * m[15] - m[0] * m[11] * m[14] - m[8] * m[2] * m[15] + m[8] * m[3] * m[14] + m[12] * m[2] * m[11] - m[12] * m[3] * m[10];
      inv[9] = -m[0] * m[9] * m[15] + m[0] * m[11] * m[13] + m[8] * m[1] * m[15] - m[8] * m[3] * m[13] - m[12] * m[1] * m[11] + m[12] * m[3] * m[9];
      inv[13] = m[0] * m[9] * m[14] - m[0] * m[10] * m[13] - m[8] * m[1] * m[14] + m[8] * m[2] * m[13] + m[12] * m[1] * m[10] - m[12] * m[2] * m[9];
      inv[2] = m[1] * m[6] * m[15] - m[1] * m[7] * m[14] - m[5] * m[2] * m[15] + m[5] * m[3] * m[14] + m[13] * m[2] * m[7] - m[13] * m[3] * m[6];
      inv[6] = -m[0] * m[6] * m[15] + m[0] * m[7] * m[14] + m[4] * m[2] * m[15] - m[4] * m[3] * m[14] - m[12] * m[2] * m[7] + m[12] * m[3] * m[6];
      inv[10] = m[0] * m[5] * m[15] - m[0] * m[7] * m[13] - m[4] * m[1] * m[15] + m[4] * m[3] * m[13] + m[12] * m[1] * m[7] - m[12] * m[3] * m[5];
      inv[14] = -m[0] * m[5] * m[14] + m[0] * m[6] * m[13] + m[4] * m[1] * m[14] - m[4] * m[2] * m[13] - m[12] * m[1] * m[6] + m[12] * m[2] * m[5];
      inv[3] = -m[1] * m[6] * m[11] + m[1] * m[7] * m[10] + m[5] * m[2] * m[11] - m[5] * m[3] * m[10] - m[9] * m[2] * m[7] + m[9] * m[3] * m[6];
      inv[7] = m[0] * m[6] * m[11] - m[0] * m[7] * m[10] - m[4] * m[2] * m[11] + m[4] * m[3] * m[10] + m[8] * m[2] * m[7] - m[8] * m[3] * m[6];
      inv[11] = -m[0] * m[5] * m[11] + m[0] * m[7] * m[9] + m[4] * m[1] * m[11] - m[4] * m[3] * m[9] - m[8] * m[1] * m[7] + m[8] * m[3] * m[5];
      inv[15] = m[0] * m[5] * m[10] - m[0] * m[6] * m[9] - m[4] * m[1] * m[10] + m[4] * m[2] * m[9] + m[8] * m[1] * m[6] - m[8] * m[2] * m[5];
      const det = m[0] * inv[0] + m[1] * inv[4] + m[2] * inv[8] + m[3] * inv[12];
      if (!det) return null;
      return inv.map((v) => v / det);
    },
    transform(m, p) {
      const x = p[0], y = p[1], z = p[2];
      const w = m[3] * x + m[7] * y + m[11] * z + m[15];
      return [
        (m[0] * x + m[4] * y + m[8] * z + m[12]) / w,
        (m[1] * x + m[5] * y + m[9] * z + m[13]) / w,
        (m[2] * x + m[6] * y + m[10] * z + m[14]) / w,
        w,
      ];
    },
  };

  const MESH_VS = `#version 300 es
in vec3 aPos;
in vec3 aNormal;
uniform mat4 uViewProj;
out vec3 vNormal;
void main() {
  vNormal = aNormal;
  gl_Position = uViewProj * vec4(aPos, 1.0);
}`;
  const MESH_FS = `#version 300 es
precision highp float;
in vec3 vNormal;
uniform vec4 uColor;
uniform vec3 uLight;
out vec4 outColor;
void main() {
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

  function compile(gl, vsSource, fsSource) {
    const program = gl.createProgram();
    for (const [type, source] of [[gl.VERTEX_SHADER, vsSource], [gl.FRAGMENT_SHADER, fsSource]]) {
      const shader = gl.createShader(type);
      gl.shaderSource(shader, source);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
        throw new Error(gl.getShaderInfoLog(shader));
      }
      gl.attachShader(program, shader);
    }
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      throw new Error(gl.getProgramInfoLog(program));
    }
    const uniforms = {};
    const count = gl.getProgramParameter(program, gl.ACTIVE_UNIFORMS);
    for (let i = 0; i < count; i++) {
      const name = gl.getActiveUniform(program, i).name;
      uniforms[name] = gl.getUniformLocation(program, name);
    }
    return { program, uniforms, aPos: gl.getAttribLocation(program, "aPos"), aNormal: gl.getAttribLocation(program, "aNormal") };
  }

  function expandTriangles(positions, indices) {
    const triCount = indices.length / 3;
    const pos = new Float32Array(triCount * 9);
    const nrm = new Float32Array(triCount * 9);
    for (let t = 0; t < triCount; t++) {
      const ia = indices[t * 3] * 3, ib = indices[t * 3 + 1] * 3, ic = indices[t * 3 + 2] * 3;
      const a = [positions[ia], positions[ia + 1], positions[ia + 2]];
      const b = [positions[ib], positions[ib + 1], positions[ib + 2]];
      const c = [positions[ic], positions[ic + 1], positions[ic + 2]];
      const n = v3.norm(v3.cross(v3.sub(b, a), v3.sub(c, a)));
      pos.set(a, t * 9);
      pos.set(b, t * 9 + 3);
      pos.set(c, t * 9 + 6);
      for (let k = 0; k < 3; k++) nrm.set(n, t * 9 + k * 3);
    }
    return { pos, nrm };
  }

  function boundsOf(values, into) {
    for (let i = 0; i < values.length; i += 3) {
      for (let k = 0; k < 3; k++) {
        if (values[i + k] < into.min[k]) into.min[k] = values[i + k];
        if (values[i + k] > into.max[k]) into.max[k] = values[i + k];
      }
    }
    return into;
  }

  function emptyBounds() {
    return { min: [Infinity, Infinity, Infinity], max: [-Infinity, -Infinity, -Infinity] };
  }

  function rayTriangle(origin, dir, a, b, c) {
    const e1 = v3.sub(b, a), e2 = v3.sub(c, a);
    const p = v3.cross(dir, e2);
    const det = v3.dot(e1, p);
    if (Math.abs(det) < 1e-12) return null;
    const inv = 1 / det;
    const s = v3.sub(origin, a);
    const u = v3.dot(s, p) * inv;
    if (u < 0 || u > 1) return null;
    const q = v3.cross(s, e1);
    const v = v3.dot(dir, q) * inv;
    if (v < 0 || u + v > 1) return null;
    const t = v3.dot(e2, q) * inv;
    return t > 0 ? t : null;
  }

  function rayBox(origin, dir, box) {
    let tmin = -Infinity, tmax = Infinity;
    for (let k = 0; k < 3; k++) {
      if (Math.abs(dir[k]) < 1e-12) {
        if (origin[k] < box.min[k] || origin[k] > box.max[k]) return false;
        continue;
      }
      let t1 = (box.min[k] - origin[k]) / dir[k];
      let t2 = (box.max[k] - origin[k]) / dir[k];
      if (t1 > t2) [t1, t2] = [t2, t1];
      tmin = Math.max(tmin, t1);
      tmax = Math.min(tmax, t2);
      if (tmin > tmax) return false;
    }
    return tmax >= 0;
  }

  class Viewer {
    /**
     * @param {HTMLElement} host - container; the viewer fills it.
     * @param {object} scene - scene from invisibility_scene.build_scene.
     * @param {object} options - {strings, onPick(id), onHover(id)}.
     */
    constructor(host, scene, options) {
      this.host = host;
      this.scene = scene;
      this.options = options || {};
      this.strings = this.options.strings || {};
      this.layers = { visible: true, hidden: true, clip: true, planes: true };
      this.highlightId = null;
      this.hoverId = null;
      this.pendingFrame = 0;

      this.canvas = document.createElement("canvas");
      this.canvas.className = "dvi3d-canvas";
      this.labelLayer = document.createElement("div");
      this.labelLayer.className = "dvi3d-labels";
      this.tooltip = document.createElement("div");
      this.tooltip.className = "dvi3d-tooltip";
      host.append(this.canvas, this.labelLayer, this.tooltip);

      const gl = this.canvas.getContext("webgl2", { antialias: true, alpha: false });
      if (!gl) throw new Error("WebGL2 is not available");
      this.gl = gl;
      this.meshProgram = compile(gl, MESH_VS, MESH_FS);
      this.flatProgram = compile(gl, FLAT_VS, FLAT_FS);

      this._buildMeshes();
      this._buildOverlays();
      this._bindEvents();
      this.setCameraPreset(scene.camera && scene.camera.eye ? "view" : "iso");

      this.resizeObserver = new ResizeObserver(() => this._resize());
      this.resizeObserver.observe(host);
      this._resize();
    }

    _buffer(data) {
      const gl = this.gl;
      const buffer = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
      gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
      return buffer;
    }

    _vao(program, positionBuffer, normalBuffer) {
      const gl = this.gl;
      const vao = gl.createVertexArray();
      gl.bindVertexArray(vao);
      gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
      gl.enableVertexAttribArray(program.aPos);
      gl.vertexAttribPointer(program.aPos, 3, gl.FLOAT, false, 0, 0);
      if (normalBuffer && program.aNormal >= 0) {
        gl.bindBuffer(gl.ARRAY_BUFFER, normalBuffer);
        gl.enableVertexAttribArray(program.aNormal);
        gl.vertexAttribPointer(program.aNormal, 3, gl.FLOAT, false, 0, 0);
      }
      gl.bindVertexArray(null);
      return vao;
    }

    _buildMeshes() {
      this.meshes = [];
      this.bounds = emptyBounds();
      for (const mesh of this.scene.meshes || []) {
        const entry = {
          id: mesh.id,
          label: mesh.label,
          visible: mesh.visible,
          approx: mesh.approx,
          bounds: emptyBounds(),
          triCount: 0,
          edgeCount: 0,
        };
        if (mesh.indices && mesh.indices.length) {
          const { pos, nrm } = expandTriangles(mesh.positions, mesh.indices);
          entry.triangles = pos;
          entry.triCount = pos.length / 9;
          entry.triVao = this._vao(this.meshProgram, this._buffer(pos), this._buffer(nrm));
          boundsOf(pos, entry.bounds);
        }
        if (mesh.edges && mesh.edges.length) {
          const edges = new Float32Array(mesh.edges);
          entry.edgeCount = edges.length / 3;
          entry.edgeVao = this._vao(this.flatProgram, this._buffer(edges));
          boundsOf(edges, entry.bounds);
        }
        if (entry.bounds.min[0] === Infinity) continue;
        boundsOf([...entry.bounds.min, ...entry.bounds.max], this.bounds);
        this.meshes.push(entry);
      }
      if (this.bounds.min[0] === Infinity) {
        this.bounds = { min: [-1, -1, -1], max: [1, 1, 1] };
      }
    }

    _buildOverlays() {
      this.boxes = [];
      this.planes = [];
      this.overallBounds = boundsOf([...this.bounds.min, ...this.bounds.max], emptyBounds());
      for (const box of this.scene.boxes || []) {
        const lines = new Float32Array(box.lines);
        boundsOf(lines, this.overallBounds);
        this.boxes.push({
          kind: box.kind,
          label: box.label,
          count: lines.length / 3,
          vao: this._vao(this.flatProgram, this._buffer(lines)),
          anchor: [lines[0], lines[1], lines[2]],
          color: COLORS.overlay[box.kind] || [0.3, 0.3, 0.3],
        });
      }
      for (const plane of this.scene.planes || []) {
        const c = plane.corners;
        const fill = new Float32Array([
          c[0], c[1], c[2], c[3], c[4], c[5], c[6], c[7], c[8],
          c[0], c[1], c[2], c[6], c[7], c[8], c[9], c[10], c[11],
        ]);
        const outline = new Float32Array([
          c[0], c[1], c[2], c[3], c[4], c[5],
          c[3], c[4], c[5], c[6], c[7], c[8],
          c[6], c[7], c[8], c[9], c[10], c[11],
          c[9], c[10], c[11], c[0], c[1], c[2],
        ]);
        boundsOf(outline, this.overallBounds);
        this.planes.push({
          kind: plane.kind,
          label: plane.label,
          fillVao: this._vao(this.flatProgram, this._buffer(fill)),
          lineVao: this._vao(this.flatProgram, this._buffer(outline)),
          anchor: [c[9], c[10], c[11]],
          color: COLORS.overlay[plane.kind] || [0.4, 0.4, 0.4],
        });
      }
      const ob = this.overallBounds;
      this.overallRadius = Math.max(v3.len(v3.sub(ob.max, ob.min)) / 2, 1);
    }

    _bindEvents() {
      const canvas = this.canvas;
      let drag = null;
      canvas.addEventListener("contextmenu", (e) => e.preventDefault());
      canvas.addEventListener("pointerdown", (e) => {
        canvas.setPointerCapture(e.pointerId);
        drag = {
          x: e.clientX,
          y: e.clientY,
          moved: false,
          pan: e.button === 1 || e.button === 2 || e.shiftKey,
        };
      });
      canvas.addEventListener("pointermove", (e) => {
        if (!drag) {
          this._hover(e);
          return;
        }
        const dx = e.clientX - drag.x;
        const dy = e.clientY - drag.y;
        if (Math.abs(dx) + Math.abs(dy) > 2) drag.moved = true;
        drag.x = e.clientX;
        drag.y = e.clientY;
        if (drag.pan) this._pan(dx, dy);
        else this._orbit(dx, dy);
      });
      canvas.addEventListener("pointerup", (e) => {
        canvas.releasePointerCapture(e.pointerId);
        const clicked = drag && !drag.moved && e.button === 0;
        drag = null;
        if (clicked) {
          const id = this.pick(e);
          this.highlight(id);
          if (id !== null && this.options.onPick) this.options.onPick(id);
        }
      });
      canvas.addEventListener("pointerleave", () => {
        this.tooltip.style.display = "none";
        if (this.hoverId !== null) {
          this.hoverId = null;
          this.requestRender();
        }
      });
      canvas.addEventListener(
        "wheel",
        (e) => {
          e.preventDefault();
          this.camera.dist = Math.max(this.camera.dist * Math.exp(e.deltaY * 0.0015), this.radius * 0.02);
          this.requestRender();
        },
        { passive: false }
      );
      canvas.addEventListener("dblclick", (e) => {
        const id = this.pick(e);
        if (id !== null) this.focus(id);
        else this.frame(this.bounds);
      });
    }

    get radius() {
      return Math.max(v3.len(v3.sub(this.bounds.max, this.bounds.min)) / 2, 1);
    }

    _center(bounds) {
      return v3.scale(v3.add(bounds.min, bounds.max), 0.5);
    }

    _eye() {
      const c = this.camera;
      const dir = [
        Math.cos(c.pitch) * Math.cos(c.yaw),
        Math.cos(c.pitch) * Math.sin(c.yaw),
        Math.sin(c.pitch),
      ];
      return v3.add(c.target, v3.scale(dir, c.dist));
    }

    _orbit(dx, dy) {
      this.camera.yaw -= dx * 0.008;
      this.camera.pitch = Math.min(MAX_PITCH, Math.max(-MAX_PITCH, this.camera.pitch + dy * 0.008));
      this.requestRender();
    }

    _pan(dx, dy) {
      const eye = this._eye();
      const forward = v3.norm(v3.sub(this.camera.target, eye));
      const right = v3.norm(v3.cross(forward, [0, 0, 1]));
      const up = v3.cross(right, forward);
      const perPixel = (2 * this.camera.dist * Math.tan(FOV / 2)) / Math.max(this.canvas.clientHeight, 1);
      const shift = v3.add(v3.scale(right, -dx * perPixel), v3.scale(up, dy * perPixel));
      this.camera.target = v3.add(this.camera.target, shift);
      this.requestRender();
    }

    /** Fit the camera to bounds, keeping the current direction. */
    frame(bounds) {
      const radius = Math.max(v3.len(v3.sub(bounds.max, bounds.min)) / 2, 0.5);
      this.camera.target = this._center(bounds);
      this.camera.dist = (radius / Math.sin(FOV / 2)) * 1.1;
      this.requestRender();
    }

    /** Camera presets: "view" (as Revit shows the view), "top", "iso". */
    setCameraPreset(name) {
      const cam = this.scene.camera || {};
      let yaw = (-45 * Math.PI) / 180;
      let pitch = (35 * Math.PI) / 180;
      let ortho = false;
      if (name === "top") {
        yaw = -Math.PI / 2;
        pitch = MAX_PITCH;
        ortho = true;
      } else if (name === "view" && cam.forward) {
        const back = v3.scale(v3.norm(cam.forward), -1);
        pitch = Math.asin(Math.max(-1, Math.min(1, back[2])));
        if (Math.abs(back[2]) > 0.999 && cam.up) {
          yaw = Math.atan2(-cam.up[1], -cam.up[0]);
        } else {
          yaw = Math.atan2(back[1], back[0]);
        }
        pitch = Math.min(MAX_PITCH, Math.max(-MAX_PITCH, pitch));
        ortho = !cam.perspective;
      }
      this.camera = { target: this._center(this.bounds), dist: 1, yaw, pitch, ortho };
      this.frame(this.bounds);
    }

    /** Return a copy of the camera state, for restoring after a rebuild. */
    getCamera() {
      return { ...this.camera, target: [...this.camera.target] };
    }

    setCamera(camera) {
      this.camera = { ...camera, target: [...camera.target] };
      this.requestRender();
    }

    setLayer(name, on) {
      this.layers[name] = on;
      this.requestRender();
    }

    setStatus(id, visible) {
      for (const mesh of this.meshes) if (mesh.id === id) mesh.visible = visible;
      this.requestRender();
    }

    highlight(id) {
      this.highlightId = id;
      this.requestRender();
    }

    focus(id) {
      const mesh = this.meshes.find((m) => m.id === id);
      if (!mesh) return;
      this.highlight(id);
      this.frame(mesh.bounds);
    }

    destroy() {
      this.resizeObserver.disconnect();
      const lose = this.gl.getExtension("WEBGL_lose_context");
      if (lose) lose.loseContext();
      this.host.replaceChildren();
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
      const width = Math.max(1, Math.round(this.host.clientWidth * dpr));
      const height = Math.max(1, Math.round(this.host.clientHeight * dpr));
      if (this.canvas.width !== width || this.canvas.height !== height) {
        this.canvas.width = width;
        this.canvas.height = height;
      }
      this.requestRender();
    }

    _matrices() {
      const eye = this._eye();
      const aspect = this.canvas.width / Math.max(this.canvas.height, 1);
      const view = m4.lookAt(eye, this.camera.target, [0, 0, 1]);
      const reach = this.camera.dist + this.overallRadius * 4;
      let proj;
      if (this.camera.ortho) {
        const halfH = this.camera.dist * Math.tan(FOV / 2);
        proj = m4.ortho(halfH * aspect, halfH, -reach, reach);
      } else {
        proj = m4.perspective(FOV, aspect, Math.max(this.camera.dist * 0.01, 0.01), reach);
      }
      return { eye, viewProj: m4.mul(proj, view) };
    }

    _meshColors(mesh) {
      if (mesh.id === this.highlightId || mesh.id === this.hoverId) {
        return [COLORS.highlight, COLORS.highlightEdge];
      }
      return mesh.visible ? [COLORS.visible, COLORS.visibleEdge] : [COLORS.hidden, COLORS.hiddenEdge];
    }

    _isShown(mesh) {
      return mesh.visible ? this.layers.visible : this.layers.hidden;
    }

    _render() {
      const gl = this.gl;
      const { eye, viewProj } = this._matrices();
      this.viewProj = viewProj;
      gl.viewport(0, 0, this.canvas.width, this.canvas.height);
      gl.clearColor(...COLORS.background);
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
      gl.enable(gl.POLYGON_OFFSET_FILL);
      gl.polygonOffset(1, 1);
      for (const mesh of this.meshes) {
        if (!mesh.triVao || !this._isShown(mesh)) continue;
        const [color] = this._meshColors(mesh);
        gl.uniform4fv(mp.uniforms.uColor, color);
        gl.bindVertexArray(mesh.triVao);
        gl.drawArrays(gl.TRIANGLES, 0, mesh.triCount * 3);
      }
      gl.disable(gl.POLYGON_OFFSET_FILL);

      const fp = this.flatProgram;
      gl.useProgram(fp.program);
      gl.uniformMatrix4fv(fp.uniforms.uViewProj, false, viewProj);
      for (const mesh of this.meshes) {
        if (!mesh.edgeVao || !this._isShown(mesh)) continue;
        const [, edge] = this._meshColors(mesh);
        gl.uniform4fv(fp.uniforms.uColor, mesh.triVao ? edge : this._meshColors(mesh)[0]);
        gl.bindVertexArray(mesh.edgeVao);
        gl.drawArrays(gl.LINES, 0, mesh.edgeCount);
      }
      if (this.layers.clip) {
        for (const box of this.boxes) {
          gl.uniform4fv(fp.uniforms.uColor, [...box.color, 1]);
          gl.bindVertexArray(box.vao);
          gl.drawArrays(gl.LINES, 0, box.count);
        }
      }
      if (this.layers.planes && this.planes.length) {
        for (const plane of this.planes) {
          gl.uniform4fv(fp.uniforms.uColor, [...plane.color, 0.9]);
          gl.bindVertexArray(plane.lineVao);
          gl.drawArrays(gl.LINES, 0, 8);
        }
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
        gl.depthMask(false);
        for (const plane of this.planes) {
          gl.uniform4fv(fp.uniforms.uColor, [...plane.color, PLANE_ALPHA]);
          gl.bindVertexArray(plane.fillVao);
          gl.drawArrays(gl.TRIANGLES, 0, 6);
        }
        gl.depthMask(true);
        gl.disable(gl.BLEND);
      }
      gl.bindVertexArray(null);
      this._renderLabels();
    }

    _renderLabels() {
      const items = [];
      if (this.layers.planes) items.push(...this.planes);
      if (this.layers.clip) items.push(...this.boxes);
      const width = this.canvas.clientWidth;
      const height = this.canvas.clientHeight;
      const placed = [];
      for (const item of items) {
        const p = m4.transform(this.viewProj, item.anchor);
        if (p[3] <= 0 || Math.abs(p[0]) > 1.2 || Math.abs(p[1]) > 1.2) continue;
        placed.push({ item, x: ((p[0] + 1) / 2) * width, y: ((1 - p[1]) / 2) * height });
      }
      placed.sort((a, b) => a.y - b.y);
      const lineHeight = 18;
      for (let i = 0; i < placed.length; i++) {
        for (let j = 0; j < i; j++) {
          const other = placed[j];
          if (Math.abs(other.x - placed[i].x) < 160 && placed[i].y - other.y < lineHeight) {
            placed[i].y = other.y + lineHeight;
          }
        }
      }
      const nodes = placed.map(({ item, x, y }) => {
        const node = document.createElement("span");
        node.className = "dvi3d-label";
        node.textContent = item.label;
        node.style.left = x + "px";
        node.style.top = y + "px";
        node.style.borderColor = `rgb(${item.color.map((c) => Math.round(c * 255)).join(",")})`;
        return node;
      });
      this.labelLayer.replaceChildren(...nodes);
    }

    _ray(event) {
      const rect = this.canvas.getBoundingClientRect();
      const x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      const y = 1 - ((event.clientY - rect.top) / rect.height) * 2;
      const inverse = m4.invert(this._matrices().viewProj);
      if (!inverse) return null;
      const near = m4.transform(inverse, [x, y, -1]);
      const far = m4.transform(inverse, [x, y, 1]);
      const origin = near.slice(0, 3);
      return { origin, dir: v3.norm(v3.sub(far.slice(0, 3), origin)) };
    }

    /** Return the id of the nearest shown element under the pointer, or null. */
    pick(event) {
      const ray = this._ray(event);
      if (!ray) return null;
      let best = null;
      let bestT = Infinity;
      for (const mesh of this.meshes) {
        if (!mesh.triangles || !this._isShown(mesh)) continue;
        if (!rayBox(ray.origin, ray.dir, mesh.bounds)) continue;
        const tri = mesh.triangles;
        for (let i = 0; i < tri.length; i += 9) {
          const t = rayTriangle(
            ray.origin,
            ray.dir,
            [tri[i], tri[i + 1], tri[i + 2]],
            [tri[i + 3], tri[i + 4], tri[i + 5]],
            [tri[i + 6], tri[i + 7], tri[i + 8]]
          );
          if (t !== null && t < bestT) {
            bestT = t;
            best = mesh.id;
          }
        }
      }
      return best;
    }

    _hover(event) {
      if (this._hoverScheduled) {
        this._lastHoverEvent = event;
        return;
      }
      this._hoverScheduled = true;
      this._lastHoverEvent = event;
      requestAnimationFrame(() => {
        this._hoverScheduled = false;
        const e = this._lastHoverEvent;
        const id = this.pick(e);
        if (id !== this.hoverId) {
          this.hoverId = id;
          this.requestRender();
          if (this.options.onHover) this.options.onHover(id);
        }
        const mesh = this.meshes.find((m) => m.id === id);
        if (!mesh) {
          this.tooltip.style.display = "none";
          return;
        }
        const rect = this.host.getBoundingClientRect();
        const status = mesh.visible ? this.strings.visible : this.strings.hidden;
        this.tooltip.textContent = `${mesh.label} — ${status}${mesh.approx ? ` (${this.strings.approx})` : ""}`;
        this.tooltip.style.display = "block";
        this.tooltip.style.left = e.clientX - rect.left + 12 + "px";
        this.tooltip.style.top = e.clientY - rect.top + 12 + "px";
      });
    }
  }

  window.pyRevitInvisibilityViewer = Viewer;
})();
