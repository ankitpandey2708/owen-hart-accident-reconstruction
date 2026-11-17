"""Blender scene builder for the accident reconstruction.
Usage: blender -b -P blender_scene.py -- <s3|s5> <out_dir> [start end]
         [--res 540|720|1080|1440|2160] [--samples N] [--fast-lights] [--draft] [--test]
Defaults reproduce the published render: 1080p, 16 samples, full lighting, EEVEE.
Units: metres. Ring centred at origin. Mat surface z=1.2.
"""
import bpy, bmesh, math, sys, random, argparse
from mathutils import Vector, Euler

RES = {540: (960, 540), 720: (1280, 720), 1080: (1920, 1080), 1440: (2560, 1440), 2160: (3840, 2160)}
ap = argparse.ArgumentParser(prog="blender_scene.py")
ap.add_argument("mode", choices=["s3", "s5"])
ap.add_argument("out")
ap.add_argument("start", nargs="?", type=int)
ap.add_argument("end", nargs="?", type=int)
ap.add_argument("--res", type=int, choices=sorted(RES), default=1080, help="output height (16:9)")
ap.add_argument("--samples", type=int, default=16, help="EEVEE anti-aliasing samples (1-64)")
ap.add_argument("--fast-lights", action="store_true", help="hard shadows, drop two fill lights")
ap.add_argument("--draft", action="store_true", help="Workbench engine: fast flat preview")
ap.add_argument("--test", action="store_true", help="debug print; implies --res 540 unless --res given")
args = ap.parse_args(sys.argv[sys.argv.index("--") + 1:])
if args.test and "--res" not in sys.argv:
    args.res = 540
if not 1 <= args.samples <= 64:
    ap.error("--samples must be 1-64")
MODE, OUT, TEST = args.mode, args.out, args.test
nums = [args.start, args.end] if args.start is not None and args.end is not None else []

FPS = 30
G = 9.81
MAT_Z = 1.2
ROPE_Z = [MAT_Z + 0.45, MAT_Z + 0.85, MAT_Z + 1.30]
TOP_ROPE = ROPE_Z[2]
HALF = 3.05                       # 20 ft ring
IMPACT = Vector((HALF - 0.45, HALF, TOP_ROPE))   # ~1-1.5 ft from turnbuckle
DROP = 23.0                       # chest -> top rope (~76 ft); rafters ~78-80 ft above ring
CHEST_TOP = TOP_ROPE + DROP
RAFTER_Z = CHEST_TOP + 1.0
TF = math.sqrt(2 * DROP / G)      # ~2.17 s

# ---------------------------------------------------------------- reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
if args.draft:
    scn.render.engine = 'BLENDER_WORKBENCH'
    scn.display.shading.light = 'STUDIO'
    scn.display.shading.color_type = 'MATERIAL'
    scn.display.render_aa = '8'
else:
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scn.render.engine = eng
            break
        except TypeError:
            pass
    try:
        scn.eevee.taa_render_samples = args.samples
    except Exception:
        pass
scn.render.resolution_x, scn.render.resolution_y = RES[args.res]
scn.render.fps = FPS
scn.render.image_settings.file_format = 'PNG'
scn.view_settings.view_transform = 'AgX' if 'AgX' in [i.identifier for i in scn.view_settings.bl_rna.properties['view_transform'].enum_items] else 'Filmic'

world = bpy.data.worlds.new("W"); scn.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.012, 0.014, 0.022, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0

# ---------------------------------------------------------------- helpers
def mat(name, color, emit=0.0, rough=0.5, metal=0.0, emit_color=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    m.diffuse_color = (*color, 1)   # used by --draft (Workbench)
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*(emit_color or color), 1)
        b.inputs["Emission Strength"].default_value = emit
    return m

def assign(o, m):
    o.data.materials.clear(); o.data.materials.append(m); return o

def box(name, loc, size, m, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.name = name; o.scale = size
    assign(o, m)
    if parent: o.parent = parent
    return o

def cyl(name, a, b, r, m, verts=16):
    a, b = Vector(a), Vector(b)
    d = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d.length, location=(a + b) / 2)
    o = bpy.context.object; o.name = name
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    assign(o, m)
    return o

def sphere(name, loc, r, m):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=24, ring_count=12)
    o = bpy.context.object; o.name = name; assign(o, m)
    bpy.ops.object.shade_smooth()
    return o

def look_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = d.to_track_quat('-Z', 'Y')

def text(body, loc, size, m, rot=(math.radians(90), 0, 0)):
    bpy.ops.object.text_add(location=loc, rotation=rot)
    t = bpy.context.object; t.data.body = body; t.data.size = size
    t.data.align_x = 'CENTER'; t.data.extrude = 0.01
    assign(t, m); return t

# ---------------------------------------------------------------- materials
M_FLOOR = mat("floor", (0.03, 0.03, 0.035), rough=0.8)
M_CANVAS = mat("canvas", (0.75, 0.75, 0.78), rough=0.9)
M_APRON = mat("apron", (0.02, 0.02, 0.02), rough=0.7)
M_POST = mat("post", (0.6, 0.6, 0.62), metal=1.0, rough=0.3)
M_PAD = mat("pad", (0.05, 0.12, 0.5), rough=0.6)
M_ROPE = mat("rope", (0.75, 0.05, 0.05), rough=0.5)
M_STEEL = mat("steel", (0.25, 0.26, 0.28), metal=1.0, rough=0.45)
M_CABLE = mat("cable", (0.8, 0.8, 0.8), metal=1.0, rough=0.2, emit=0.6, emit_color=(0.9, 0.9, 1.0))
M_DUMMY = mat("dummy", (0.95, 0.72, 0.05), rough=0.45)
M_DUMMY2 = mat("dummy2", (0.03, 0.03, 0.03), rough=0.5)
M_HARNESS = mat("harness", (0.02, 0.02, 0.05), rough=0.6)
M_SHACKLE = mat("shackle", (0.85, 0.85, 0.9), metal=1.0, rough=0.15, emit=1.5, emit_color=(1.0, 0.6, 0.1))
M_RED = mat("redglow", (1, 0.05, 0.02), emit=8.0)
M_LABEL = mat("label", (1, 1, 1), emit=4.0)
M_ACCENT = mat("accent", (1, 0.75, 0.1), emit=5.0)

# crowd material: noise-driven colour variation
M_CROWD = bpy.data.materials.new("crowd"); M_CROWD.use_nodes = True; M_CROWD.diffuse_color = (0.2, 0.15, 0.13, 1)
nt = M_CROWD.node_tree; bsdf = nt.nodes["Principled BSDF"]
tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise")
nz.inputs["Scale"].default_value = 3.0
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].color = (0.02, 0.02, 0.03, 1)
ramp.color_ramp.elements[1].color = (0.25, 0.18, 0.15, 1)
nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

# ---------------------------------------------------------------- arena
bpy.ops.mesh.primitive_plane_add(size=120, location=(0, 0, 0)); assign(bpy.context.object, M_FLOOR)
box("ring_top", (0, 0, MAT_Z - 0.05), (2 * HALF + 0.4, 2 * HALF + 0.4, 0.1), M_CANVAS)
box("ring_apron", (0, 0, (MAT_Z - 0.1) / 2), (2 * HALF + 0.4, 2 * HALF + 0.4, MAT_Z - 0.1), M_APRON)
for sx in (-1, 1):
    for sy in (-1, 1):
        cyl("post", (sx * HALF, sy * HALF, 0), (sx * HALF, sy * HALF, TOP_ROPE + 0.2), 0.06, M_POST)
        for z in ROPE_Z:
            box("pad", (sx * (HALF - 0.08), sy * (HALF - 0.08), z), (0.2, 0.2, 0.28), M_PAD)

def rope_mesh(name, y, z, deflect=False):
    """Rope along x at (y,z). Optional shape key 'hit' = point load at IMPACT.x."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    segs, sides, r = 80, 10, 0.022
    rings = []
    for i in range(segs + 1):
        x = -HALF + 2 * HALF * i / segs
        ring = [bm.verts.new((x, y + r * math.cos(2 * math.pi * k / sides), z + r * math.sin(2 * math.pi * k / sides))) for k in range(sides)]
        rings.append(ring)
    for i in range(segs):
        for k in range(sides):
            bm.faces.new((rings[i][k], rings[i][(k + 1) % sides], rings[i + 1][(k + 1) % sides], rings[i + 1][k]))
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); scn.collection.objects.link(o); assign(o, M_ROPE)
    for p in me.polygons: p.use_smooth = True
    if deflect:
        o.shape_key_add(name="Basis"); sk = o.shape_key_add(name="hit")
        ix, d = IMPACT.x, 0.22
        for v in sk.data:
            x = v.co.x
            f = (x + HALF) / (ix + HALF) if x <= ix else (HALF - x) / (HALF - ix)
            v.co.z -= d * max(0.0, f)
            v.co.y -= 0.05 * max(0.0, f)
    return o

for z in ROPE_Z:
    for side in range(4):
        defl = (side == 0 and z == TOP_ROPE)
        o = rope_mesh("rope", HALF, z, deflect=defl)
        o.rotation_euler.z = side * math.pi / 2
        if defl: HIT_ROPE = o

# steps / barricade
for a in range(0, 360, 90):
    box("barricade", (math.cos(math.radians(a)) * 9, math.sin(math.radians(a)) * 9, 0.5),
        (0.2 if a % 180 == 0 else 18, 18 if a % 180 == 0 else 0.2, 1.0), M_STEEL)

# crowd bowl: one mesh, many boxes
me = bpy.data.meshes.new("crowd"); bm = bmesh.new()
random.seed(7)
for tier in range(14):
    rad = 16 + tier * 2.2; z = 0.6 + tier * 1.35
    n = int(2 * math.pi * rad / 0.7)
    for i in range(n):
        if random.random() < 0.12: continue
        ang = 2 * math.pi * i / n
        if abs(math.sin(ang * 2)) < 0.03: continue    # aisles
        c = Vector((math.cos(ang) * rad, math.sin(ang) * rad, z + random.uniform(0, 0.15)))
        res = bmesh.ops.create_cube(bm, size=1.0)
        for v in res["verts"]:
            v.co = Vector((v.co.x * 0.45, v.co.y * 0.45, v.co.z * 0.9)) + c
        # seat step under
    for i in range(0, 1):
        pass
bm.to_mesh(me); bm.free()
crowd = bpy.data.objects.new("crowd", me); scn.collection.objects.link(crowd); crowd.data.materials.append(M_CROWD)
me = bpy.data.meshes.new("bowl"); bm = bmesh.new()
SEG = 128
for tier in range(14):
    r0 = 16 + tier * 2.2 - 1.1; r1 = r0 + 2.2; z = 0.15 + tier * 1.35; zb = z - 1.35
    ring = []
    for i in range(SEG):
        a = 2 * math.pi * i / SEG; c, s = math.cos(a), math.sin(a)
        ring.append((bm.verts.new((c * r0, s * r0, max(zb, 0))), bm.verts.new((c * r0, s * r0, z)), bm.verts.new((c * r1, s * r1, z))))
    for i in range(SEG):
        a, b = ring[i], ring[(i + 1) % SEG]
        bm.faces.new((a[0], b[0], b[1], a[1]))   # riser
        bm.faces.new((a[1], b[1], b[2], a[2]))   # tread
bm.to_mesh(me); bm.free()
bowl = bpy.data.objects.new("bowl", me); scn.collection.objects.link(bowl); bowl.data.materials.append(M_APRON)
del SEG

# roof + rafters
bpy.ops.mesh.primitive_plane_add(size=110, location=(0, 0, RAFTER_Z + 5)); assign(bpy.context.object, M_APRON)
for i in range(-6, 7):
    box("rafter_x", (0, i * 5.0, RAFTER_Z + 0.3), (90, 0.25, 0.6), M_STEEL)
    box("rafter_y", (i * 5.0, 0, RAFTER_Z + 0.9), (0.25, 90, 0.6), M_STEEL)
# catwalk over ring corner
box("catwalk", (IMPACT.x, IMPACT.y, RAFTER_Z + 0.02), (1.0, 14, 0.06), M_STEEL)
for s in (-1, 1):
    box("catwalk_rail", (IMPACT.x + s * 0.5, IMPACT.y, RAFTER_Z + 0.55), (0.04, 14, 0.04), M_STEEL)
# lighting truss over ring

# lights
def light(kind, loc, energy, color=(1, 1, 1), size=1.0, target=(0, 0, MAT_Z), spot=None):
    ld = bpy.data.lights.new("L", kind); ld.energy = energy; ld.color = color
    if kind == 'AREA': ld.size = size
    if kind == 'SPOT' and spot: ld.spot_size = spot; ld.spot_blend = 0.4
    o = bpy.data.objects.new("L", ld); scn.collection.objects.link(o)
    if args.fast_lights:   # hard shadows
        if kind == 'AREA': ld.size = min(ld.size, 1.0)
        elif hasattr(ld, "shadow_soft_size"): ld.shadow_soft_size = 0.0
        if hasattr(ld, "use_shadow_jitter"): ld.use_shadow_jitter = False
    o.location = loc; look_at(o, target); return o

light('AREA', (0, 0, 9.5), 7000, (1, 0.97, 0.9), size=8)
light('SPOT', (-12, -12, 14), 40000, (0.6, 0.7, 1.0), spot=math.radians(30))
if not args.fast_lights: light('SPOT', (12, 12, 14), 25000, (1.0, 0.8, 0.6), spot=math.radians(30))
light('SPOT', (IMPACT.x, IMPACT.y - 6, RAFTER_Z - 1), 8000, (1, 1, 1), target=(IMPACT.x, IMPACT.y, CHEST_TOP), spot=math.radians(25))
if not args.fast_lights: light('AREA', (0, 0, RAFTER_Z - 2), 1500, (0.5, 0.6, 1.0), size=30, target=(0, 0, 0))

# ---------------------------------------------------------------- dummy (crash-test style)
body = bpy.data.objects.new("body", None); scn.collection.objects.link(body)
body.rotation_mode = 'XYZ'
def part(o):
    o.parent = body; return o
part(box("torso", (0, 0, 0), (0.42, 0.25, 0.62), M_DUMMY))
part(box("pelvis", (0, 0, -0.42), (0.38, 0.24, 0.2), M_DUMMY2))
part(sphere("head", (0, 0, 0.5), 0.13, M_DUMMY))
part(cyl("neck", (0, 0, 0.3), (0, 0, 0.4), 0.05, M_DUMMY2))
for s in (-1, 1):
    part(cyl("thigh", (s * 0.11, 0, -0.5), (s * 0.12, -0.02, -0.92), 0.085, M_DUMMY))
    part(cyl("shin", (s * 0.12, -0.02, -0.95), (s * 0.12, 0.0, -1.35), 0.07, M_DUMMY))
    part(sphere("knee", (s * 0.12, -0.02, -0.935), 0.08, M_DUMMY2))
    part(cyl("upperarm", (s * 0.26, 0, 0.26), (s * 0.34, -0.05, -0.05), 0.06, M_DUMMY))
    part(cyl("forearm", (s * 0.34, -0.05, -0.08), (s * 0.36, -0.12, -0.35), 0.05, M_DUMMY))
    part(sphere("shoulder", (s * 0.25, 0, 0.27), 0.07, M_DUMMY2))
# target marks (crash-test style quadrant discs on chest)
for s in (-1, 1):
    o = part(cyl("mark", (s * 0.1, -0.126, 0.12), (s * 0.1, -0.13, 0.12), 0.05, M_DUMMY2))
# harness vest
part(box("vest", (0, 0, 0.1), (0.45, 0.28, 0.14), M_HARNESS))
for s in (-1, 1):
    part(box("strap", (s * 0.12, 0, 0.2), (0.06, 0.28, 0.4), M_HARNESS))
part(box("backplate", (0, 0.14, 0.25), (0.14, 0.03, 0.14), M_HARNESS))
ATTACH_LOCAL = Vector((0, 0.17, 0.33))

# shackle (world-space, stays on cable after release)
shackle = bpy.data.objects.new("shackle", None); scn.collection.objects.link(shackle)
bpy.ops.mesh.primitive_torus_add(major_radius=0.05, minor_radius=0.012, location=(0, 0, 0.04))
o = bpy.context.object; assign(o, M_SHACKLE); o.parent = shackle; o.rotation_euler.x = math.pi / 2
gate_piv = bpy.data.objects.new("gate_pivot", None); scn.collection.objects.link(gate_piv)
gate_piv.parent = shackle; gate_piv.location = (0.04, 0, -0.01)
g = box("gate", (-0.04, 0, -0.03), (0.09, 0.02, 0.02), M_SHACKLE); g.parent = gate_piv
hook = cyl("hook", (0, 0, -0.01), (0, 0, -0.06), 0.012, M_SHACKLE); hook.parent = shackle
hook.location = (0, 0, -0.035)

HANG_POS = Vector((IMPACT.x, IMPACT.y + 0.05, CHEST_TOP))
ATTACH_WORLD = HANG_POS + ATTACH_LOCAL
shackle.location = ATTACH_WORLD

cable = cyl("cable", (ATTACH_WORLD.x, ATTACH_WORLD.y, ATTACH_WORLD.z + 0.08),
            (ATTACH_WORLD.x, ATTACH_WORLD.y, RAFTER_Z + 0.3), 0.008, M_CABLE)

# ---------------------------------------------------------------- body kinematics (function of sim time tau)
def smooth(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

THETA_IMPACT = math.radians(84)
def body_state(tau):
    """returns (loc Vector, pitch rad, rope_hit 0..1, gate_angle, shackle_z_offset)"""
    gate = math.radians(75) * smooth(tau / 0.08) if tau > 0 else 0.0
    sh_dz = 0.12 * math.sin(min(max(tau, 0), 0.6) / 0.6 * math.pi) * math.exp(-max(tau, 0) * 2) if tau > 0 else 0.0
    if tau <= 0:
        sway = 0.03 * math.sin(tau * 2.2)
        return HANG_POS.copy(), sway, 0.0, gate, sh_dz
    if tau <= TF:
        z = CHEST_TOP - 0.5 * G * tau * tau
        th = THETA_IMPACT * smooth(tau / TF) ** 1.3
        # chest offset: rotating about chest; nudge so chest centre meets rope from above
        loc = Vector((HANG_POS.x, HANG_POS.y - 0.05 * smooth(tau / TF), z + 0.14 * smooth(tau / TF)))
        return loc, th, 0.0, gate, sh_dz
    t2 = tau - TF
    end_loc = Vector((IMPACT.x, HALF - 1.45, MAT_Z + 0.15))
    hit_loc = Vector((IMPACT.x, HALF - 0.05, TOP_ROPE + 0.14))
    if t2 <= 0.12:   # compression onto rope
        k = t2 / 0.12
        rope = math.sin(k * math.pi / 2)
        loc = hit_loc + Vector((0, 0, -0.22 * rope))
        return loc, THETA_IMPACT + math.radians(4) * k, rope, gate, sh_dz
    t3 = t2 - 0.12
    # rebound + roll over rope into ring
    rope = max(0.0, math.cos(t3 * 9) * math.exp(-t3 * 4)) if t3 < 1.5 else 0.0
    k = smooth(t3 / 0.9)
    start = hit_loc + Vector((0, 0, -0.22))
    mid = Vector((IMPACT.x, HALF - 0.7, TOP_ROPE + 0.05))
    # quadratic bezier start -> mid -> end
    loc = (1 - k) ** 2 * start + 2 * (1 - k) * k * mid + k * k * end_loc
    th = THETA_IMPACT + math.radians(4) + math.radians(2) * k
    if t3 > 0.9:   # small settle bounce on mat
        b = t3 - 0.9
        loc.z += 0.06 * abs(math.sin(b * 10)) * math.exp(-b * 6)
    return loc, th, rope, gate, sh_dz

def apply_tau(tau, frame):
    loc, th, rope, gate, sh_dz = body_state(tau)
    body.location = loc; body.rotation_euler = (th, 0, 0)
    body.keyframe_insert("location", frame=frame); body.keyframe_insert("rotation_euler", frame=frame)
    kb = HIT_ROPE.data.shape_keys.key_blocks["hit"]; kb.value = rope
    kb.keyframe_insert("value", frame=frame)
    gate_piv.rotation_euler = (0, -gate, 0); gate_piv.keyframe_insert("rotation_euler", frame=frame)
    shackle.location = ATTACH_WORLD + Vector((0, 0, sh_dz)); shackle.keyframe_insert("location", frame=frame)
    return loc

# ---------------------------------------------------------------- cameras
def camera(name, loc, target, lens=35):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.clip_end = 400
    c = bpy.data.objects.new(name, cd); scn.collection.objects.link(c)
    c.location = loc; look_at(c, target); return c

def key_cam(c, frame, loc, target):
    c.location = loc; look_at(c, target)
    c.keyframe_insert("location", frame=frame); c.keyframe_insert("rotation_quaternion", frame=frame)

def hide_key(o, frame, hidden):
    for ch in [o] + list(o.children_recursive):
        ch.hide_render = hidden; ch.keyframe_insert("hide_render", frame=frame)

# ================================================================ MODES
if MODE == "s3":
    N = 540
    scn.frame_start, scn.frame_end = 0, N - 1
    for f in range(N): apply_tau(-3 + f / FPS * 0.3, f) if f % 3 == 0 else None
    cam = camera("cam", (0, -14, 2.5), (0, 0, 2), lens=24); scn.camera = cam
    # height dimension line beside the fall path
    dx = IMPACT.x + 1.6
    cyl("dim", (dx, IMPACT.y, TOP_ROPE), (dx, IMPACT.y, CHEST_TOP), 0.03, M_ACCENT)
    for i in range(0, 9):
        z = TOP_ROPE + i * 10 * 0.3048
        if z <= CHEST_TOP:
            cyl("tick", (dx - 0.25, IMPACT.y, z), (dx + 0.25, IMPACT.y, z), 0.02, M_ACCENT)
            t = text(f"{i*10} ft", (dx + 0.9, IMPACT.y, z - 0.15), 0.45, M_LABEL)
    lbl = text("~78 ft  (24 m)", (dx + 4.5, IMPACT.y, (TOP_ROPE + CHEST_TOP) / 2), 1.3, M_ACCENT)
    for o in [lbl]:
        c = o.constraints.new('TRACK_TO'); c.target = cam; c.track_axis = 'TRACK_Z'; c.up_axis = 'UP_Y'
    # camera path: low wide -> orbit & crane up -> near rafters looking down
    for f in range(0, N, 3):
        k = smooth(f / (N - 1))
        ang = math.radians(-90 + 70 * k)
        rad = 14 - 3 * k
        z = 2.5 + 24 * k ** 1.2
        tgt = Vector((0, 0, 2)).lerp(Vector((IMPACT.x, IMPACT.y, 12)), smooth(f / (N * 0.6)))
        if f > N * 0.6:
            tgt = Vector((IMPACT.x, IMPACT.y, 12)).lerp(Vector((IMPACT.x, IMPACT.y, 2)), smooth((f - N * 0.6) / (N * 0.4)))
        key_cam(cam, f, (IMPACT.x * k + math.cos(ang) * rad, IMPACT.y * k + math.sin(ang) * rad, z), tgt)

elif MODE == "s5":
    # segments: (f0, f1, tau0, tau1)
    SEG = [(0, 60, -2.0, 0.0), (60, 66, 0.0, 0.2), (66, 200, 0.2, 4.67), (200, 225, 4.67, 4.67),
           (225, 485, -0.3, 2.0), (485, 725, 2.0, 3.4), (725, 860, 3.4, 4.2), (860, 1005, 4.2, 4.2)]
    N = 1005
    scn.frame_start, scn.frame_end = 0, N - 1
    def tau_at(f):
        for f0, f1, a, b in SEG:
            if f0 <= f < f1:
                return a + (b - a) * (f - f0) / max(1, f1 - f0)
        return SEG[-1][3]
    locs = {}
    for f in range(N):
        locs[f] = apply_tau(tau_at(f), f)

    camA = camera("camA", (HANG_POS.x + 2.2, HANG_POS.y - 2.6, CHEST_TOP + 0.6), HANG_POS + Vector((0, 0, 0.2)), lens=40)
    camB = camera("camB", (IMPACT.x - 7, IMPACT.y - 9, 2.0), (IMPACT.x, IMPACT.y, 10.5), lens=14)
    camC = camera("camC", (0, 0, 0), (0, 0, 0), lens=30)
    camD = camera("camD", (IMPACT.x + 3.2, IMPACT.y - 3.6, TOP_ROPE + 0.6), (IMPACT.x - 0.2, IMPACT.y - 0.3, TOP_ROPE - 0.2), lens=32)
    camE = camera("camE", (IMPACT.x - 4.5, IMPACT.y - 5.5, TOP_ROPE + 4.0), (IMPACT.x - 0.3, IMPACT.y - 0.4, TOP_ROPE - 0.4), lens=30)
    # slow push on camA
    key_cam(camA, 0, camA.location.copy(), HANG_POS + Vector((0, 0, 0.2)))
    key_cam(camA, 66, camA.location + Vector((-0.6, 0.7, 0)), HANG_POS + Vector((0, 0, -0.3)))
    # camC tracks the body during replay
    for f in range(225, 485):
        p = locs[f]
        zc = max(p.z, TOP_ROPE + 0.8)
        key_cam(camC, f, (p.x + 6.0, p.y - 4.5, zc + 0.6), (p.x, p.y, max(p.z, TOP_ROPE)))
    # camD gentle drift
    key_cam(camD, 485, camD.location.copy(), (IMPACT.x - 0.2, IMPACT.y - 0.3, TOP_ROPE - 0.2))
    key_cam(camD, 725, camD.location + Vector((-0.6, 0.3, 0.2)), (IMPACT.x - 0.4, IMPACT.y - 0.6, TOP_ROPE - 0.4))
    key_cam(camE, 725, camE.location.copy(), (IMPACT.x - 0.3, IMPACT.y - 0.4, TOP_ROPE - 0.4))
    key_cam(camE, 1004, camE.location + Vector((1.2, -0.4, 0.8)), (IMPACT.x - 0.3, IMPACT.y - 0.5, TOP_ROPE - 0.5))
    for fr, c in [(0, camA), (66, camB), (225, camC), (485, camD), (725, camE)]:
        m = scn.timeline_markers.new(c.name, frame=fr); m.camera = c
    scn.camera = camA

    # trajectory trail (replay onwards): thin red line from release point to current body
    trail = cyl("trail", (0, 0, 0), (0, 0, 1), 0.025, M_RED)
    trail.rotation_mode = 'XYZ'; trail.rotation_euler = (0, 0, 0)
    hide_key(trail, 0, True); hide_key(trail, 225, False)
    for f in range(225, N):
        top = CHEST_TOP; bot = min(top, max(locs[f].z + 0.3, TOP_ROPE + 0.3))
        trail.location = (HANG_POS.x + 0.35, HANG_POS.y, (top + bot) / 2)
        trail.scale = (1, 1, max(0.001, top - bot))
        trail.keyframe_insert("location", frame=f); trail.keyframe_insert("scale", frame=f)

    # impact marker
    bpy.ops.mesh.primitive_torus_add(major_radius=0.35, minor_radius=0.025, location=IMPACT)
    ring = bpy.context.object; assign(ring, M_RED)
    hide_key(ring, 0, True); hide_key(ring, 725, False)
    for f in range(725, N, 2):
        s = 1 + 0.25 * math.sin((f - 725) / FPS * 2 * math.pi * 0.8)
        ring.scale = (s, s, s); ring.keyframe_insert("scale", frame=f)
    arrow = cyl("arrow", (IMPACT.x, IMPACT.y, IMPACT.z + 2.2), (IMPACT.x, IMPACT.y, IMPACT.z + 0.45), 0.02, M_RED)
    hide_key(arrow, 0, True); hide_key(arrow, 725, False)
    bpy.ops.mesh.primitive_cone_add(radius1=0.09, depth=0.25, location=(IMPACT.x, IMPACT.y, IMPACT.z + 0.4), rotation=(math.pi, 0, 0))
    tip = bpy.context.object; assign(tip, M_RED); hide_key(tip, 0, True); hide_key(tip, 725, False)

# ---------------------------------------------------------------- render
if nums:
    scn.frame_start, scn.frame_end = int(nums[0]), int(nums[1])
scn.render.filepath = OUT.rstrip("/\\") + "/"
if TEST:
    scn.frame_set(scn.frame_start)
    cam = scn.camera
    print("DBG ENGINE", scn.render.engine, "CAM", cam.name, tuple(round(v, 2) for v in cam.matrix_world.translation),
          "FWD", tuple(round(v, 2) for v in (cam.matrix_world.to_3x3() @ Vector((0, 0, -1)))),
          "BODY", tuple(round(v, 2) for v in body.matrix_world.translation))
bpy.ops.wm.save_as_mainfile(filepath=OUT.rstrip("/\\") + f"_{MODE}.blend")
bpy.ops.render.render(animation=True)
