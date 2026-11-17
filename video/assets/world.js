/* The 3D world: one continuous take, a pure function of timeline time t.
   Times come from window.HF_TIMING (assets/timing.js, written by build.py from the voice).
   Units: metres, Y up. Ring centred at origin; the fall happens at the +Z side. */
(function () {
  const T = window.HF_TIMING;
  const W = 1920, H = 1080;
  const G = 9.81, MAT_Y = 1.2, ROPES = [1.65, 2.05, 2.5], TOP = 2.5, HALF = 3.05;
  const DROP = 23.0, TF = Math.sqrt((2 * DROP) / G);          // chest -> top rope, ~2.17 s
  const IMPACT = [HALF - 0.45, TOP, HALF];
  const HANG = [IMPACT[0], TOP + DROP, HALF + 0.05];           // chest while hanging
  const RAFTER_Y = HANG[1] + 1.1;
  const FIX = [IMPACT[0] - 2.6, HANG[1], HALF + 0.05];         // corrected rig hangs here
  const FT = 0.3048;

  const sc = Object.fromEntries(T.scenes.map((s) => [s.id, s]));
  const word = (scene, text, k = 0) => {
    const ws = T.words.filter((w) => w.scene === scene && w.text.toLowerCase().replace(/[^\w:']/g, "").startsWith(text));
    return ws.length ? ws[Math.min(k, ws.length - 1)].start : sc[scene].voice_start;
  };
  const sEnd = (id) => sc[id].start + sc[id].duration;
  const T_OPEN = word("release", "opened");
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const smooth = (x) => { x = clamp(x); return x * x * (3 - 2 * x); };
  const inOut = (x) => { x = clamp(x); return x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2; };   // power2.inOut
  const expoOut = (x) => (x >= 1 ? 1 : 1 - Math.pow(2, -10 * clamp(x)));

  let THREE, renderer, scene, cam, ready = false;
  const R = {};   // refs

  // ---------------------------------------------------------------- build
  async function build() {
    THREE = await import(new URL("assets/lib/three.module.min.js", document.baseURI).href);
    const canvas = document.getElementById("world-canvas");
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(1); renderer.setSize(W, H, false);
    renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x07080a);
    scene.fog = new THREE.Fog(0x07080a, 40, 95);
    cam = new THREE.PerspectiveCamera(32, W / H, 0.01, 300);

    // environment for metal reflections (a small room of soft strips)
    const env = new THREE.Scene();
    const room = new THREE.Mesh(new THREE.BoxGeometry(10, 10, 10), new THREE.MeshBasicMaterial({ color: 0x15161a, side: THREE.BackSide }));
    env.add(room);
    for (const [x, y, z, w, h, c] of [[0, 4.9, 0, 6, 1.2, 0xfff2df], [-4.9, 1, 0, 0.1, 3, 0x9db4ff], [4.9, 2, 1, 0.1, 2.5, 0xffe0b8], [0, 1, -4.9, 4, 0.6, 0xffffff]]) {
      const m = new THREE.Mesh(new THREE.BoxGeometry(Math.max(w, 0.1), h, x === 0 && y !== 1 ? 0.1 : 0.1), new THREE.MeshBasicMaterial({ color: c }));
      m.position.set(x, y, z); if (y === 4.9) m.rotation.x = Math.PI / 2; env.add(m);
    }
    const pm = new THREE.PMREMGenerator(renderer);
    scene.environment = pm.fromScene(env, 0.04).texture;
    scene.environmentIntensity = 0.85;

    const mat = (c, o = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.6, metalness: 0, ...o });
    const M = {
      floor: mat(0x0b0c0f, { roughness: 0.9 }), canvas: mat(0xcfd0d4, { roughness: 0.95 }), apron: mat(0x050506, { roughness: 0.8 }),
      post: mat(0x9aa0a8, { metalness: 0.9, roughness: 0.35 }), pad: mat(0x1d3a9e, { roughness: 0.6 }), rope: mat(0xb3201a, { roughness: 0.55 }),
      steel: mat(0x2a2d33, { metalness: 0.8, roughness: 0.5 }), cable: mat(0xc9ced6, { metalness: 1, roughness: 0.35 }),
      ss: mat(0xe6e9ee, { metalness: 1, roughness: 0.22 }), dummy: mat(0xf2b80d, { roughness: 0.45 }), joint: mat(0x141416, { roughness: 0.5 }),
      web: mat(0x101114, { roughness: 0.85 }), red: mat(0xe0301e, { roughness: 0.5, emissive: 0x400000 }),
      amber: new THREE.MeshBasicMaterial({ color: 0xf2a93b }), green: mat(0x3fbf7f, { metalness: 0.6, roughness: 0.35 }),
      ghost: new THREE.MeshBasicMaterial({ color: 0xf2f0ea, transparent: true, opacity: 0.55, depthWrite: false }),
      stand: mat(0x15130f, { roughness: 0.95 }), metal: mat(0x9aa0a8, { metalness: 0.9, roughness: 0.35 }),
      forged: mat(0xc9ced6, { metalness: 0.55, roughness: 0.3 }),   // satin stainless: reads in a dark rafter space
    };
    R.M = M;
    const add = (g, m, p, parent = scene, shadow = true) => {
      const o = new THREE.Mesh(g, m); o.position.set(...p); o.castShadow = shadow; o.receiveShadow = true; parent.add(o); return o;
    };
    const box = (s, m, p, parent) => add(new THREE.BoxGeometry(...s), m, p, parent);
    const cyl = (a, b, r, m, parent = scene, seg = 16) => {
      const A = new THREE.Vector3(...a), B = new THREE.Vector3(...b), d = B.clone().sub(A);
      const o = add(new THREE.CylinderGeometry(r, r, d.length(), seg), m, [0, 0, 0], parent);
      o.position.copy(A.clone().add(B).multiplyScalar(0.5));
      o.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.normalize()); return o;
    };
    R.cyl = cyl;

    // lights
    scene.add(new THREE.HemisphereLight(0x8090b0, 0x0a0806, 0.25));
    const key = new THREE.SpotLight(0xffd7a8, 900, 60, THREE.MathUtils.degToRad(24), 0.5, 1.6);
    key.position.set(0, 26, 0); key.target.position.set(0, MAT_Y, 0); key.castShadow = true;
    key.shadow.mapSize.set(2048, 2048); key.shadow.bias = -0.0004; scene.add(key, key.target);
    const rim = new THREE.DirectionalLight(0x9db4ff, 0.6); rim.position.set(-10, 18, -14); scene.add(rim);
    const topKey = new THREE.SpotLight(0xffe6c8, 150, 16, THREE.MathUtils.degToRad(32), 0.6, 1.5);
    topKey.position.set(HANG[0] + 2.6, RAFTER_Y + 0.5, HANG[2] + 3.2); topKey.target.position.set(HANG[0], HANG[1], HANG[2]); scene.add(topKey, topKey.target);
    const fixKey = new THREE.SpotLight(0xffe6c8, 140, 16, THREE.MathUtils.degToRad(32), 0.6, 1.5);
    fixKey.position.set(FIX[0] + 2.2, RAFTER_Y + 0.5, FIX[2] + 3.2);
    const highRim = new THREE.SpotLight(0x9db4ff, 120, 14, THREE.MathUtils.degToRad(40), 0.7, 1.5);
    highRim.position.set(HANG[0] - 3, RAFTER_Y + 1, HANG[2] - 3); highRim.target.position.set((HANG[0] + FIX[0]) / 2, HANG[1], HANG[2]); scene.add(highRim, highRim.target); fixKey.target.position.set(...FIX); scene.add(fixKey, fixKey.target);

    // arena floor, ring
    add(new THREE.PlaneGeometry(200, 200), M.floor, [0, 0, 0]).rotation.x = -Math.PI / 2;
    box([2 * HALF + 0.4, MAT_Y - 0.1, 2 * HALF + 0.4], M.apron, [0, (MAT_Y - 0.1) / 2, 0]);
    box([2 * HALF + 0.4, 0.1, 2 * HALF + 0.4], M.canvas, [0, MAT_Y - 0.05, 0]);
    for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
      cyl([sx * HALF, 0, sz * HALF], [sx * HALF, TOP + 0.2, sz * HALF], 0.06, M.post);
      for (const y of ROPES) box([0.2, 0.28, 0.2], M.pad, [sx * (HALF - 0.08), y, sz * (HALF - 0.08)]);
    }
    // ropes: the +Z top rope deforms at impact
    for (const y of ROPES) for (let side = 0; side < 4; side++) {
      const g = new THREE.CylinderGeometry(0.022, 0.022, 2 * HALF, 10, 80); g.rotateZ(Math.PI / 2);
      const o = add(g, M.rope, [0, y, 0]);
      const a = (side * Math.PI) / 2;
      o.position.set(Math.sin(a) * HALF, y, Math.cos(a) * HALF); o.rotation.y = a;
      if (side === 0 && y === TOP) { R.hitRope = o; R.hitRopeBase = g.attributes.position.array.slice(); }
    }
    // barricade
    for (const [x, z, w, d] of [[0, 9, 18, 0.2], [0, -9, 18, 0.2], [9, 0, 0.2, 18], [-9, 0, 0.2, 18]]) box([w, 1, d], M.steel, [x, 0.5, z]);

    // seating bowl + crowd (seeded)
    let seed = 7; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    for (let tier = 0; tier < 14; tier++) {
      const r0 = 16 + tier * 2.2 - 1.1, y = 0.15 + tier * 1.35;
      const tread = add(new THREE.RingGeometry(r0, r0 + 2.2, 128), M.stand, [0, y, 0], scene, false); tread.rotation.x = -Math.PI / 2;
      add(new THREE.CylinderGeometry(r0, r0, 1.35, 128, 1, true), M.stand, [0, y - 0.675, 0], scene, false).material.side = THREE.DoubleSide;
    }
    const people = [];
    for (let tier = 0; tier < 14; tier++) {
      const rad = 16 + tier * 2.2, n = Math.floor((2 * Math.PI * rad) / 0.7);
      for (let i = 0; i < n; i++) { const a = (2 * Math.PI * i) / n; if (rnd() < 0.12 || Math.abs(Math.sin(a * 2)) < 0.03) continue; people.push([Math.cos(a) * rad, 0.6 + tier * 1.35 + rnd() * 0.15, Math.sin(a) * rad, rnd()]); }
    }
    const crowd = new THREE.InstancedMesh(new THREE.BoxGeometry(0.45, 0.9, 0.45), new THREE.MeshStandardMaterial({ roughness: 0.9 }), people.length);
    const m4 = new THREE.Matrix4(), col = new THREE.Color();
    people.forEach((p, i) => { m4.makeTranslation(p[0], p[1], p[2]); crowd.setMatrixAt(i, m4); col.setRGB(0.05 + p[3] * 0.2, 0.04 + p[3] * 0.14, 0.035 + p[3] * 0.11); crowd.setColorAt(i, col); });
    scene.add(crowd);

    // rafters: steel Warren trusses (chords + diagonals), one instanced mesh
    const parts = [];   // [cx, cy, cz, len, thick, axis('x'|'z'), tilt]
    const truss = (axis, off, y0, h) => {
      for (const y of [y0, y0 + h]) parts.push([axis === "x" ? 0 : off, y, axis === "x" ? off : 0, 90, 0.09, axis, 0]);
      for (let k = -45; k < 45; k += 1.2) {
        const c = k + 0.6, tilt = Math.atan2(h, 1.2) * ((Math.round((k + 45) / 1.2) % 2) ? 1 : -1);
        parts.push([axis === "x" ? c : off, y0 + h / 2, axis === "x" ? off : c, Math.hypot(h, 1.2), 0.045, axis, tilt]);
      }
    };
    for (let i = -6; i <= 6; i++) { truss("x", i * 5, RAFTER_Y + 0.6, 0.7); truss("z", i * 5, RAFTER_Y + 1.35, 0.7); }
    const trussMesh = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), M.steel, parts.length);
    const q = new THREE.Quaternion(), e = new THREE.Euler(), sv = new THREE.Vector3(), pv = new THREE.Vector3();
    parts.forEach(([x, y, z, len, th, axis, tilt], i) => {
      if (axis === "x") { e.set(0, 0, tilt); sv.set(len, th, th); } else { e.set(-tilt, 0, 0); sv.set(th, th, len); }
      q.setFromEuler(e); pv.set(x, y, z); m4.compose(pv, q, sv); trussMesh.setMatrixAt(i, m4);
    });
    scene.add(trussMesh);
    // catwalk: grating, toe boards, posts, two rails
    const CW = HANG[0] - 1.3;
    const grate = mat(0x23262b, { metalness: 0.7, roughness: 0.6 });
    box([1.0, 0.03, 16], grate, [CW, RAFTER_Y, HANG[2]]);
    for (let z = -7.8; z <= 7.8; z += 0.2) box([0.98, 0.012, 0.012], M.steel, [CW, RAFTER_Y + 0.02, HANG[2] + z]);
    for (const s of [-1, 1]) {
      box([0.02, 0.12, 16], M.steel, [CW + s * 0.5, RAFTER_Y + 0.07, HANG[2]]);
      for (const y of [0.55, 1.05]) box([0.04, 0.04, 16], M.steel, [CW + s * 0.5, RAFTER_Y + y, HANG[2]]);
      for (let z = -7.5; z <= 7.5; z += 1.5) box([0.04, 1.05, 0.04], M.steel, [CW + s * 0.5, RAFTER_Y + 0.53, HANG[2] + z]);
    }
    // I-beam the cable hangs from
    const BX = HANG[0] - 0.6;
    for (const y of [0.16, 0.34]) box([3.0, 0.02, 0.16], M.steel, [BX, RAFTER_Y + y, HANG[2] + 0.165]);
    box([3.0, 0.18, 0.015], M.steel, [BX, RAFTER_Y + 0.25, HANG[2] + 0.165]);

    // mannequin builder (front faces -Z, origin at chest)
    function dummy(materialSet) {
      const g = new THREE.Group(); scene.add(g);
      const D = materialSet.dummy, J = materialSet.joint;
      box([0.42, 0.62, 0.25], D, [0, 0, 0], g); box([0.38, 0.2, 0.24], J, [0, -0.42, 0], g);
      add(new THREE.SphereGeometry(0.13, 32, 16), D, [0, 0.5, 0], g); add(new THREE.CylinderGeometry(0.05, 0.05, 0.12), J, [0, 0.35, 0], g);
      const cap = (r, len) => new THREE.CapsuleGeometry(r, len, 6, 16);
      for (const s of [-1, 1]) {
        add(cap(0.082, 0.3), D, [s * 0.11, -0.73, -0.01], g);
        add(new THREE.SphereGeometry(0.075, 16, 12), J, [s * 0.12, -0.96, -0.02], g);
        add(cap(0.064, 0.28), D, [s * 0.12, -1.17, 0], g);
        const ua = add(cap(0.056, 0.22), D, [s * 0.3, 0.1, -0.02], g); ua.rotation.z = s * 0.2;
        const fa = add(cap(0.046, 0.2), D, [s * 0.35, -0.2, -0.08], g); fa.rotation.set(0.3, 0, s * 0.12);
        add(new THREE.SphereGeometry(0.07, 16, 12), J, [s * 0.25, 0.27, 0], g);
        add(new THREE.CircleGeometry(0.045, 24), J, [s * 0.1, 0.12, -0.126], g).rotation.y = Math.PI;
      }
      // full-body harness: chest band, shoulder straps over the top, leg loops, buckles, back plate
      const W_ = materialSet.web, MET = materialSet.metal;
      box([0.44, 0.07, 0.27], W_, [0, 0.12, 0], g);
      for (const s of [-1, 1]) {
        const c = new THREE.CatmullRomCurve3([[s * 0.11, 0.12, -0.13], [s * 0.11, 0.29, -0.115], [s * 0.115, 0.335, 0], [s * 0.11, 0.29, 0.13], [s * 0.11, 0.12, 0.13]].map((p) => new THREE.Vector3(...p)));
        const st = add(new THREE.TubeGeometry(c, 24, 0.011, 6), W_, [0, 0, 0], g); st.scale.set(1.6, 1, 1);
        const loop = add(new THREE.TorusGeometry(0.096, 0.011, 8, 32), W_, [s * 0.11, -0.56, -0.01], g); loop.rotation.x = Math.PI / 2;
        const lc = new THREE.CatmullRomCurve3([[s * 0.13, 0.09, -0.13], [s * 0.15, -0.22, -0.13], [s * 0.13, -0.5, -0.1]].map((p) => new THREE.Vector3(...p)));
        add(new THREE.TubeGeometry(lc, 16, 0.009, 6), W_, [0, 0, 0], g);
        box([0.05, 0.035, 0.014], MET, [s * 0.11, -0.56, -0.112], g);
      }
      box([0.06, 0.04, 0.014], MET, [0, 0.12, -0.142], g);                 // chest buckle
      box([0.14, 0.16, 0.02], W_, [0, 0.25, 0.135], g);                   // back plate
      box([0.03, 0.04, 0.012], MET, [0, 0.305, 0.15], g);                 // D-ring tab
      return g;
    }
    R.body = dummy(M);
    // harness D-ring: threads through the shackle jaw (plane normal = world Z)
    add(new THREE.TorusGeometry(0.013, 0.0028, 12, 32), M.ss, [0, 0.33, 0.165], R.body);

    // swivel snap shackle, modelled in its own XY plane (extruded along Z), turned so its profile faces +X.
    // Parts: swivel bail, barrel, forged body, fixed jaw, hinged gate, spring plunger, pull lanyard + ring.
    const sh = new THREE.Group(); scene.add(sh); R.shackle = sh;
    const forged = { depth: 0.008, bevelEnabled: true, bevelThickness: 0.0012, bevelSize: 0.0012, bevelSegments: 3, curveSegments: 32 };
    const extrude = (shape, o = forged) => { const g = new THREE.ExtrudeGeometry(shape, o); g.translate(0, 0, -o.depth / 2); return g; };
    const C = [0, -0.012], RO = 0.019, RI = 0.011, deg = Math.PI / 180;
    const arc = (a0, a1) => { const s = new THREE.Shape(); s.absarc(C[0], C[1], RO, a0 * deg, a1 * deg, false); s.absarc(C[0], C[1], RI, a1 * deg, a0 * deg, true); s.closePath(); return s; };
    const body = new THREE.Shape();   // rounded forged body
    const bx = 0.013, by0 = -0.006, by1 = 0.03, rr = 0.004;
    body.moveTo(-bx + rr, by0); body.lineTo(bx - rr, by0); body.quadraticCurveTo(bx, by0, bx, by0 + rr); body.lineTo(bx, by1 - rr);
    body.quadraticCurveTo(bx, by1, bx - rr, by1); body.lineTo(-bx + rr, by1); body.quadraticCurveTo(-bx, by1, -bx, by1 - rr);
    body.lineTo(-bx, by0 + rr); body.quadraticCurveTo(-bx, by0, -bx + rr, by0);
    add(extrude(body, { ...forged, depth: 0.011 }), M.forged, [0, 0, 0], sh);
    add(extrude(arc(150, 290)), M.forged, [0, 0, 0], sh);                                       // fixed jaw
    const piv = [C[0] + 0.015 * Math.cos(25 * deg), C[1] + 0.015 * Math.sin(25 * deg)];
    const gp = new THREE.Group(); gp.position.set(piv[0], piv[1], 0); sh.add(gp); R.gate = gp;  // hinged gate
    const gateGeo = extrude(arc(292, 385)); gateGeo.translate(-piv[0], -piv[1], 0); add(gateGeo, M.forged, [0, 0, 0], gp);
    add(new THREE.CylinderGeometry(0.0022, 0.0022, 0.013, 12), M.post, [0, 0, 0], gp).rotation.x = Math.PI / 2;   // hinge pin
    add(new THREE.CylinderGeometry(0.0078, 0.0078, 0.012, 32), M.ss, [0, 0.036, 0], sh);                         // swivel barrel
    add(new THREE.TorusGeometry(0.0078, 0.0012, 8, 32), M.ss, [0, 0.031, 0], sh).rotation.x = Math.PI / 2;
    add(new THREE.CylinderGeometry(0.004, 0.004, 0.012, 16), M.ss, [0, 0.047, 0], sh);
    add(new THREE.TorusGeometry(0.011, 0.003, 14, 40), M.ss, [0, 0.063, 0], sh);                                  // bail
    const pl = new THREE.Group(); sh.add(pl); R.plunger = pl;                                                      // spring plunger
    add(new THREE.CylinderGeometry(0.0024, 0.0024, 0.03, 12), M.ss, [0.0162, 0.016, 0], pl);
    add(new THREE.TorusGeometry(0.0038, 0.0011, 8, 20), M.ss, [0.0162, 0.034, 0], pl);
    const lan = new THREE.Group(); lan.position.set(0.0162, 0.034, 0); pl.add(lan); R.lanyard = lan;
    const lc = new THREE.CatmullRomCurve3([[0, 0, 0], [0.01, -0.004, 0.001], [0.016, -0.03, 0], [0.014, -0.07, 0.002], [0.016, -0.106, 0]].map((p) => new THREE.Vector3(...p)));
    add(new THREE.TubeGeometry(lc, 48, 0.0017, 8), M.red, [0, 0, 0], lan);
    add(new THREE.TorusGeometry(0.0068, 0.0018, 10, 28), M.red, [0.016, -0.113, 0], lan);                          // pull ring
    sh.rotation.set(0, -Math.PI / 2, 0);
    R.shBase = new THREE.Vector3(HANG[0], HANG[1] + 0.33 + 0.036, HANG[2] + 0.165);
    sh.position.copy(R.shBase);
    R.cable = cyl([R.shBase.x, R.shBase.y + 0.073, R.shBase.z], [R.shBase.x, RAFTER_Y + 0.16, R.shBase.z], 0.0035, M.cable);

    // ruler: 0-78 ft beside the drop
    R.ruler = new THREE.Group(); scene.add(R.ruler);
    const rx = HANG[0] + 1.6;
    cyl([rx, MAT_Y, HALF], [rx, MAT_Y + 78 * FT, HALF], 0.03, M.amber, R.ruler);
    for (let f = 0; f <= 78; f += 10) cyl([rx - 0.3, MAT_Y + f * FT, HALF], [rx + 0.3, MAT_Y + f * FT, HALF], 0.02, M.amber, R.ruler);
    cyl([rx - 0.4, MAT_Y + 78 * FT, HALF], [rx + 0.4, MAT_Y + 78 * FT, HALF], 0.03, M.amber, R.ruler);
    R.ruler.traverse((o) => (o.castShadow = false));

    // plan: dashed path + ghost mannequin
    const PLAN_Y = MAT_Y + 2.2;
    R.planY = PLAN_Y;
    const pts = [new THREE.Vector3(HANG[0], HANG[1], HANG[2]), new THREE.Vector3(HANG[0], PLAN_Y, HANG[2])];
    R.path = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineDashedMaterial({ color: 0xf2f0ea, dashSize: 0.5, gapSize: 0.35, transparent: true, opacity: 0 }));
    R.path.computeLineDistances(); scene.add(R.path);
    R.mark = box([1.6, 0.04, 0.04], M.amber, [HANG[0], PLAN_Y, HANG[2]]); R.mark.castShadow = false;
    R.ghost = dummy({ dummy: M.ghost, joint: M.ghost, web: M.ghost, metal: M.ghost }); R.ghost.traverse((o) => (o.castShadow = false));

    // corrected rig: two independent lines, locking carabiners, no quick release
    R.fix = dummy(M);
    R.fix.position.set(...FIX);
    R.fixRig = new THREE.Group(); scene.add(R.fixRig);
    for (const s of [-1, 1]) {
      const p = [FIX[0] + s * 0.12, FIX[1] + 0.36, FIX[2] + 0.17];
      const cb = add(new THREE.TorusGeometry(0.03, 0.006, 12, 32), M.green, [p[0], p[1] + 0.03, p[2]], R.fixRig); cb.scale.set(0.65, 1.15, 1);
      add(new THREE.CylinderGeometry(0.009, 0.009, 0.022, 12), M.green, [p[0] + 0.018, p[1] + 0.03, p[2]], R.fixRig);
      cyl([p[0], p[1] + 0.065, p[2]], [p[0] + s * 0.25, RAFTER_Y + 0.25, p[2]], 0.004, M.cable, R.fixRig);
    }
    R.fixAnch = { cbL: new THREE.Vector3(FIX[0] - 0.12, FIX[1] + 0.39, FIX[2] + 0.17), lineR: new THREE.Vector3(FIX[0] + 0.19, FIX[1] + 0.85, FIX[2] + 0.17), mid: new THREE.Vector3(FIX[0], FIX[1] + 0.36, FIX[2] + 0.2) };

    // post: linear HDR targets, an additive accumulation quad and the grade pass
    R.rtS = new THREE.WebGLRenderTarget(W, H, { type: THREE.HalfFloatType, samples: 4 });
    R.rtA = new THREE.WebGLRenderTarget(W, H, { type: THREE.HalfFloatType });
    R.quadCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    const vs = "varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }";
    R.accMat = new THREE.ShaderMaterial({
      uniforms: { tex: { value: null }, w: { value: 1 } }, vertexShader: vs,
      fragmentShader: "uniform sampler2D tex; uniform float w; varying vec2 vUv; void main(){ gl_FragColor = vec4(texture2D(tex, vUv).rgb * w, 1.0); }",
      blending: THREE.AdditiveBlending, depthTest: false, depthWrite: false, toneMapped: false,
    });
    R.accScene = new THREE.Scene(); R.accScene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), R.accMat));
    R.gradeMat = new THREE.ShaderMaterial({
      uniforms: { tex: { value: R.rtA.texture }, frame: { value: 0 } }, vertexShader: vs, depthTest: false, depthWrite: false, toneMapped: true,
      fragmentShader: `
        uniform sampler2D tex; uniform float frame; varying vec2 vUv;
        float hash(vec2 p){ p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
        void main(){
          vec3 c = toneMapping(texture2D(tex, vUv).rgb);
          float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
          c *= mix(vec3(0.95, 0.99, 1.06), vec3(1.05, 1.0, 0.93), smoothstep(0.08, 0.7, l));   // cool shadows, warm highlights
          c = mix(vec3(l), c, 0.9);                                                               // saturation 0.9
          c = clamp(c, 0.0, 1.0);
          c = mix(c, c * c * (3.0 - 2.0 * c), 0.2);                                               // gentle S-curve
          vec2 d = vUv - 0.5; d.x *= 1.7778;
          c *= 1.0 - 0.26 * smoothstep(0.35, 1.05, length(d));                                    // vignette
          vec4 o = linearToOutputTexel(vec4(c, 1.0));
          o.rgb += (hash(vUv * vec2(1920.0, 1080.0) + frame * 17.13) - 0.5) * 0.028;              // grain ~3%, seeded by frame
          gl_FragColor = o;
        }`,
    });
    R.gradeScene = new THREE.Scene(); R.gradeScene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), R.gradeMat));

    await (renderer.compileAsync ? renderer.compileAsync(scene, cam) : Promise.resolve());
    ready = true;
  }

  // ---------------------------------------------------------------- body kinematics (tau = s since release)
  const THETA = (84 * Math.PI) / 180;
  function bodyState(tau) {
    if (tau <= 0) return { p: HANG.slice(), th: 0.02 * Math.sin(tau * 2.2), rope: 0 };
    if (tau <= TF) {
      const k = smooth(tau / TF);
      return { p: [HANG[0], HANG[1] - 0.5 * G * tau * tau + 0.14 * k, HANG[2] - 0.05 * k], th: THETA * Math.pow(k, 1.3), rope: 0 };
    }
    const t2 = tau - TF, hit = [IMPACT[0], TOP + 0.14, HALF - 0.05];
    if (t2 <= 0.12) { const r = Math.sin(((t2 / 0.12) * Math.PI) / 2); return { p: [hit[0], hit[1] - 0.22 * r, hit[2]], th: THETA + 0.07 * (t2 / 0.12), rope: r }; }
    const t3 = t2 - 0.12, k = smooth(t3 / 0.9);
    const rope = t3 < 1.5 ? Math.max(0, Math.cos(t3 * 9) * Math.exp(-t3 * 4)) : 0;
    const a = [hit[0], hit[1] - 0.22, hit[2]], m = [IMPACT[0], TOP + 0.05, HALF - 0.7], e = [IMPACT[0], MAT_Y + 0.15, HALF - 1.45];
    const p = [0, 1, 2].map((i) => (1 - k) ** 2 * a[i] + 2 * (1 - k) * k * m[i] + k * k * e[i]);
    if (t3 > 0.9) { const b = t3 - 0.9; p[1] += 0.06 * Math.abs(Math.sin(b * 10)) * Math.exp(-b * 6); }
    return { p, th: THETA + 0.07 + 0.035 * k, rope };
  }

  // ---------------------------------------------------------------- camera: one continuous take
  const S = R.shBase ? null : null;
  function keys() {
    const sb = [HANG[0], HANG[1] + 0.38, HANG[2] + 0.165];     // shackle world pos (approx)
    const ch = HANG;
    const off = (p, d) => [p[0] + d[0], p[1] + d[1], p[2] + d[2]];
    const fb = [FIX[0], FIX[1] + 0.4, FIX[2] + 0.17];
    return [
      // [time, position, target, fov]
      [0.0, off(sb, [0.26, -0.02, 0.04]), off(sb, [0, 0.0, 0.01]), 30],
      [sc.hook.voice_start + 4.6, off(sb, [0.27, -0.03, 0.1]), off(sb, [0, 0.0, 0.01]), 30],
      [word("who", "one"), off(sb, [0.55, 0.05, 0.75]), off(sb, [0, -0.15, 0]), 30],
      [word("who", "holding"), off(ch, [1.9, 1.1, 2.6]), off(ch, [0, -0.2, 0]), 34],
      [word("who", "ring"), [HANG[0] + 15, 23, HANG[2] + 19], [0.5, 12, 0.6], 40],
      [sEnd("who"), [HANG[0] + 15.5, 22, HANG[2] + 19.5], [0.5, 12, 0.6], 40],
      [word("plan", "lower"), [HANG[0] + 9, 7.5, HANG[2] + 13], [HANG[0] - 0.5, 6.5, HANG[2] - 0.5], 40],
      [sEnd("plan") - 0.3, [HANG[0] + 8, 6.0, HANG[2] + 12], [HANG[0] - 0.5, 4.5, HANG[2] - 0.5], 40],
      [sc.release.start + 0.8, off(sb, [0.27, -0.02, 0.07]), off(sb, [0, -0.01, 0.01]), 32],
      [T_OPEN + 0.12, off(sb, [0.26, -0.02, 0.06]), off(sb, [0, -0.01, 0.01]), 32],
      // during the fall the target tracks the body (see render); position rises to the catwalk edge
      [T_OPEN + 0.55, off(sb, [0.25, 0.3, 0.45]), null, 46],
      [T_OPEN + TF + 1.6, off(sb, [0.25, 0.32, 0.45]), null, 46],
      [sc.after.start, [IMPACT[0] - 7, 16, IMPACT[2] + 9], [IMPACT[0] - 0.5, MAT_Y, IMPACT[2] - 0.6], 34],
      [sEnd("after"), [IMPACT[0] - 5.5, 19, IMPACT[2] + 6.5], [IMPACT[0] - 0.5, MAT_Y, IMPACT[2] - 0.6], 34],
      [sc.fix.start + 0.3, off(sb, [0.5, 0.05, 0.75]), off(sb, [-0.1, -0.05, 0]), 30],
      [word("fix", "rated"), off(fb, [1.0, 0.1, 1.55]), off(fb, [0, -0.05, 0]), 32],
      [sEnd("fix"), off(fb, [1.2, 0.25, 1.75]), off(fb, [0, 0.0, 0]), 32],
      [sc.end.start + 1.0, off(fb, [3.5, 1.2, 6.0]), off(fb, [0, -0.6, 0]), 34],
      [T.total, [FIX[0] + 9, 23, FIX[2] + 16], [0.5, 15, 0.5], 38],
    ];
  }
  let KEYS = null;
  function camAt(t, bodyP) {
    KEYS = KEYS || keys();
    let i = 0;
    while (i < KEYS.length - 2 && t >= KEYS[i + 1][0]) i++;
    const a = KEYS[i], b = KEYS[i + 1];
    const k = inOut((t - a[0]) / Math.max(1e-3, b[0] - a[0]));
    const pos = a[1].map((v, j) => v + (b[1][j] - v) * k);
    const ta = a[2] || bodyP, tb = b[2] || bodyP;
    const tgt = ta.map((v, j) => v + (tb[j] - v) * k);
    return { pos, tgt, fov: a[3] + (b[3] - a[3]) * k };
  }

  // ---------------------------------------------------------------- labels anchored to objects
  const L = [];
  function label(id, anchor, tin, tout) { L.push({ el: document.getElementById(id), anchor, tin, tout }); }
  function setupLabels() {
    const V = (x, y, z) => new THREE.Vector3(x, y, z);
    const sbV = () => R.shackle.position.clone();
    label("lb-arena", () => V(0, MAT_Y + 0.3, -HALF - 0.5), word("who", "1999"), sEnd("who"));
    label("lb-height", () => V(HANG[0] + 2.2, MAT_Y + 39 * FT, HALF), word("who", "above"), sEnd("who") + 0.3);
    label("lb-plan", () => V(HANG[0] + 1.2, R.planY, HANG[2]), word("plan", "release"), sEnd("plan") - 0.2);
    label("lb-lanyard", () => sbV().add(V(0, -0.079, 0.032)), sc.release.start + 0.9, T_OPEN - 0.05);
    label("lb-rated", () => R.fixAnch.cbL, word("fix", "rated"), sEnd("fix"));
    label("lb-two", () => R.fixAnch.lineR, word("fix", "two"), sEnd("fix"));
    label("lb-noqr", () => R.fixAnch.mid.clone().add(V(0, -0.22, 0.05)), word("fix", "quick"), sEnd("fix"));
  }

  // ---------------------------------------------------------------- render(t): pure function of t
  function update(t, withLabels) {
    const tau = t - T_OPEN;
    // shackle gate: open at start, snaps shut at 0.3 s; snaps open at T_OPEN
    let gate = t < 0.3 ? 1.0 : t < 0.4 ? 1.0 * (1 - (t - 0.3) / 0.1) : 0;
    if (tau > 0) gate = 1.05 * clamp(tau / 0.1);
    R.gate.rotation.z = gate;
    // lanyard tug before the release (adjusting the cape/harness theory), pulled taut at T_OPEN
    const tug = clamp((t - (T_OPEN - 0.6)) / 0.5) * (tau < 0.6 ? 1 : Math.max(0, 1 - (tau - 0.6) * 2));
    R.lanyard.rotation.z = 0.25 * tug; R.plunger.position.y = 0.006 * tug;
    // shackle recoil after release
    const rec = tau > 0 ? 0.04 * Math.sin(Math.min(tau, 0.6) / 0.6 * Math.PI) * Math.exp(-tau * 2) : 0;
    R.shackle.position.copy(R.shBase).add(new THREE.Vector3(0, rec, 0));
    R.shackle.rotation.set(tau > 0 ? 0.25 * Math.sin(tau * 5) * Math.exp(-tau * 1.2) : 0, -Math.PI / 2, 0);

    // body
    const bs = bodyState(tau);
    R.body.position.set(...bs.p); R.body.rotation.set(-bs.th, 0, 0);
    R.body.visible = t < sc.after.start;
    // top rope deflection: point load ~0.45 m from the post
    const pos = R.hitRope.geometry.attributes.position, base = R.hitRopeBase, d = 0.2 * bs.rope;
    const ixLocal = IMPACT[0];
    for (let i = 0; i < pos.count; i++) {
      const x = base[i * 3];
      const f = x <= ixLocal ? (x + HALF) / (ixLocal + HALF) : (HALF - x) / (HALF - ixLocal);
      pos.array[i * 3 + 1] = base[i * 3 + 1] - d * Math.max(0, f);
      pos.array[i * 3 + 2] = base[i * 3 + 2] + 0.05 * bs.rope * Math.max(0, f) * -1;
    }
    pos.needsUpdate = true;

    // plan: path and ghost descent + pratfall
    const pIn = smooth((t - word("plan", "lower")) / 0.6) * (1 - smooth((t - (sEnd("plan") - 0.6)) / 0.5));
    R.path.material.opacity = 0.7 * pIn; R.path.visible = pIn > 0.01;
    R.mark.visible = t > word("plan", "release") - 0.1 && t < sEnd("plan") - 0.1;
    const gd = inOut((t - word("plan", "lower")) / Math.max(0.5, word("plan", "release") - word("plan", "lower")));
    const gy = HANG[1] + (R.planY - HANG[1]) * gd;
    const pf = clamp((t - word("plan", "comedy")) / 0.45);       // the planned flat-on-the-face drop
    R.ghost.visible = pIn > 0.01;
    R.ghost.position.set(HANG[0], gy - (R.planY - (MAT_Y + 0.15)) * pf * pf, HANG[2] - 0.9 * pf);
    R.ghost.rotation.set(-Math.PI / 2 * smooth(pf * 1.2), 0, 0);

    // ruler
    R.ruler.visible = t > word("who", "above") - 0.1 && t < sEnd("who") + 0.3;
    R.fix.visible = R.fixRig.visible = t > sc.fix.start - 1.0;

    // camera
    const c = camAt(t, [bs.p[0], bs.p[1] - 0.2, bs.p[2]]);
    cam.position.set(...c.pos); cam.lookAt(...c.tgt); cam.fov = c.fov; cam.updateProjectionMatrix(); cam.updateMatrixWorld();

    if (!withLabels) return;
    // labels
    for (const l of L) {
      const a = clamp((t - l.tin) / 0.18) * clamp((l.tout - t) / 0.12);
      if (a <= 0) { l.el.style.opacity = 0; continue; }
      const p = l.anchor().project(cam);
      const x = ((p.x + 1) / 2) * W, y = ((1 - p.y) / 2) * H;
      l.el.style.opacity = a * (p.z < 1 ? 1 : 0);
      l.el.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px)`;
      l.el.style.filter = `blur(${(8 * (1 - expoOut((t - l.tin) / 0.18))).toFixed(2)}px)`;
    }
  }

  // ---------------------------------------------------------------- frame: sub-frame motion blur + grade
  // MB_SAMPLES renders spread over a 180-degree shutter (half a frame), averaged in linear HDR,
  // then one grade pass: ACES tone map, split-tone, saturation, contrast, vignette, frame-seeded grain.
  const FPS = 30, MB_SAMPLES = 8, SHUTTER = 0.5;
  function render(t) {
    renderer.setRenderTarget(R.rtA); renderer.setClearColor(0x000000, 1); renderer.clear();
    for (let i = 0; i < MB_SAMPLES; i++) {
      const ti = Math.max(0, t + (SHUTTER / FPS) * (i / (MB_SAMPLES - 1) - 0.5));
      update(ti, false);
      renderer.autoClear = true; renderer.setRenderTarget(R.rtS); renderer.render(scene, cam);
      renderer.autoClear = false; renderer.setRenderTarget(R.rtA);
      R.accMat.uniforms.tex.value = R.rtS.texture; R.accMat.uniforms.w.value = 1 / MB_SAMPLES;
      renderer.render(R.accScene, R.quadCam);
    }
    update(t, true);                       // labels and final state at the frame's own time
    renderer.autoClear = true; renderer.setRenderTarget(null);
    R.gradeMat.uniforms.frame.value = Math.round(t * FPS);
    renderer.render(R.gradeScene, R.quadCam);
  }

  window.__hf = window.__hf || {};
  window.__hf.buildReady = window.__hf.buildReady || {};
  const built = build().then(() => { setupLabels(); render(0); });
  window.__hf.buildReady["world"] = built;
  let queue = built;
  window.addEventListener("hf-seek", (e) => {
    const t = e.detail.time;
    queue = queue.then(() => render(t));
    if (e.detail.waitUntil) e.detail.waitUntil(queue);
  });
})();
