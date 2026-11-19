/*
 * Shared WebGL2 helpers for the pyRevit scene previews (Diagnose Invisibility,
 * Section Box Navigator): vector and matrix math, shader compilation, packed
 * array decoding, ray tests and the orbit camera.
 *
 * Exposes window.pyRevitScene3D. Scene coordinates are Revit feet relative to
 * scene.origin, Z up. Camera functions work on a plain state object
 * {target, dist, yaw, pitch, ortho} so a viewer can keep and copy its camera.
 */
(function () {
  "use strict";

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

  function decodeArray(value, Type) {
    if (typeof value !== "string") return Type.from(value || []);
    const binary = atob(value);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return new Type(bytes.buffer);
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

  function cameraEye(camera) {
    const dir = [
      Math.cos(camera.pitch) * Math.cos(camera.yaw),
      Math.cos(camera.pitch) * Math.sin(camera.yaw),
      Math.sin(camera.pitch),
    ];
    return v3.add(camera.target, v3.scale(dir, camera.dist));
  }

  function cameraOrbit(camera, dx, dy) {
    camera.yaw -= dx * 0.008;
    camera.pitch = Math.min(MAX_PITCH, Math.max(-MAX_PITCH, camera.pitch + dy * 0.008));
  }

  function cameraPan(camera, dx, dy, canvasHeight) {
    const eye = cameraEye(camera);
    const forward = v3.norm(v3.sub(camera.target, eye));
    const right = v3.norm(v3.cross(forward, [0, 0, 1]));
    const up = v3.cross(right, forward);
    const perPixel = (2 * camera.dist * Math.tan(FOV / 2)) / Math.max(canvasHeight, 1);
    const shift = v3.add(v3.scale(right, -dx * perPixel), v3.scale(up, dy * perPixel));
    camera.target = v3.add(camera.target, shift);
  }

  function cameraZoom(camera, deltaY, minDist) {
    camera.dist = Math.max(camera.dist * Math.exp(deltaY * 0.0015), minDist);
  }

  /** Return {eye, viewProj} for a canvas of the given aspect; reach adds to the clip depth. */
  function cameraMatrices(camera, aspect, reach) {
    const eye = cameraEye(camera);
    const view = m4.lookAt(eye, camera.target, [0, 0, 1]);
    const depth = camera.dist + reach;
    let proj;
    if (camera.ortho) {
      const halfH = camera.dist * Math.tan(FOV / 2);
      proj = m4.ortho(halfH * aspect, halfH, -depth, depth);
    } else {
      proj = m4.perspective(FOV, aspect, Math.max(camera.dist * 0.01, 0.01), depth);
    }
    return { eye, view, proj, viewProj: m4.mul(proj, view) };
  }

  /** Camera that frames bounds, keeping the direction of the given camera. */
  function cameraFrame(camera, bounds) {
    const radius = Math.max(v3.len(v3.sub(bounds.max, bounds.min)) / 2, 0.5);
    camera.target = v3.scale(v3.add(bounds.min, bounds.max), 0.5);
    camera.dist = (radius / Math.sin(FOV / 2)) * 1.1;
  }

  /** Camera presets: "view" (as Revit shows the view), "top", "iso". */
  function cameraPreset(name, sceneCamera, bounds) {
    const cam = sceneCamera || {};
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
    const camera = { target: v3.scale(v3.add(bounds.min, bounds.max), 0.5), dist: 1, yaw, pitch, ortho };
    cameraFrame(camera, bounds);
    return camera;
  }

  window.pyRevitScene3D = {
    FOV,
    MAX_PITCH,
    v3,
    m4,
    compile,
    decodeArray,
    boundsOf,
    emptyBounds,
    rayTriangle,
    rayBox,
    cameraEye,
    cameraOrbit,
    cameraPan,
    cameraZoom,
    cameraMatrices,
    cameraFrame,
    cameraPreset,
  };
})();
