#!/usr/bin/env python3
"""Convert Sponge .schem v2/v3 files into Lost Cities building/part assets.

Scope: vanilla Minecraft block states only. Non-minecraft namespace blocks are
mapped to documented vanilla approximations in manifest.json. Block-entity NBT
is reported but not imported in this first pass.
"""
from __future__ import annotations
import argparse, gzip, hashlib, json, math, re, sys
from pathlib import Path

try:
    import nbtlib
except ImportError:
    print("Missing dependency: install nbtlib==1.12.1", file=sys.stderr)
    raise

NS = "neoncity"
REG = "lostcities"
CHARS = list("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!#$%&()*+,-./:;<=>?@[]^_{|}~")
AIR_NAMES = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}
FALLBACKS = [
    ("glass", "minecraft:cyan_stained_glass"),
    ("neon|light|lamp", "minecraft:sea_lantern"),
    ("metal|steel|iron", "minecraft:iron_block"),
    ("wood|plank", "minecraft:dark_oak_planks"),
    ("water", "minecraft:water"),
    ("lava", "minecraft:lava"),
    ("concrete", "minecraft:gray_concrete"),
    ("stone|brick|rock", "minecraft:polished_deepslate"),
]

def unpack(v):
    return v.unpack() if hasattr(v, "unpack") else v

def root_compound(nbt):
    root = nbt
    if hasattr(root, "keys") and "Schematic" in root and hasattr(root["Schematic"], "keys"):
        root = root["Schematic"]
    return root

def read_nbt(path):
    # nbtlib detects gzip from the file header when loading a path.
    return root_compound(nbtlib.load(str(path)))

def varints(data):
    out, value, shift = [], 0, 0
    for raw in data:
        b = int(raw) & 255
        value |= (b & 127) << shift
        if b & 128:
            shift += 7
            if shift > 35:
                raise ValueError("Invalid oversized varint in BlockData")
        else:
            out.append(value)
            value, shift = 0, 0
    if shift:
        raise ValueError("Truncated varint stream in BlockData")
    return out

def vanilla_state(state):
    state = str(state)
    if ":" not in state:
        state = "minecraft:" + state
    if state.startswith("minecraft:"):
        return "minecraft:structure_void" if state.split("[",1)[0] in AIR_NAMES else state
    low = state.lower()
    for pattern, replacement in FALLBACKS:
        if re.search(pattern, low):
            return replacement
    return "minecraft:polished_deepslate"

def slugify(name):
    s = re.sub(r"[^a-z0-9_]+", "_", Path(name).stem.lower()).strip("_")
    return (s[:48] or "imported_structure")

def load_schematic(path):
    nbt = read_nbt(path)
    w, h, l = (int(nbt[k]) for k in ("Width", "Height", "Length"))
    if min(w,h,l) < 1 or max(w,h,l) > 2048:
        raise ValueError(f"Unreasonable dimensions {w}x{h}x{l}")
    pal = nbt["Palette"]
    palette = {str(k): int(v) for k,v in pal.items()}
    raw = nbt["BlockData"]
    indices = varints(raw)
    expected = w*h*l
    if len(indices) != expected:
        raise ValueError(f"BlockData has {len(indices)} entries; expected {expected}")
    states = [None] * (max(palette.values(), default=-1)+1)
    for state, idx in palette.items():
        states[idx] = vanilla_state(state)
    blocks = [states[i] if i < len(states) and states[i] is not None else "minecraft:air" for i in indices]
    # Sponge linear order: x fastest, then z, then y.
    def get(x,y,z):
        return blocks[x + z*w + y*w*l]
    return w,h,l,get,int(nbt["Version"]) if "Version" in nbt else 2, len(nbt["BlockEntities"]) if "BlockEntities" in nbt else 0

def char_map(states):
    chars = {}
    available = iter(CHARS)
    next_private = 0xE000
    for state in sorted(set(states)):
        try:
            ch = next(available)
        except StopIteration:
            if next_private > 0xF8FF:
                raise ValueError("Palette exceeds supported private-use character range")
            ch = chr(next_private)
            next_private += 1
        chars[state] = ch
    chars["minecraft:air"] = " "
    return chars

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def convert_one(path, out, manifest):
    w,h,l,get,version,block_entities = load_schematic(path)
    slug = slugify(path.name)
    nx, nz = math.ceil(w/16), math.ceil(l/16)
    floors = max(1, math.ceil(h/6))
    all_states = {get(x,y,z) for y in range(h) for z in range(l) for x in range(w)}
    all_states.add("minecraft:air")
    cmap = char_map(all_states)
    palette_id = f"{NS}:{slug}_palette"
    palette_entries = [{"char": ch, "block": state} for state,ch in sorted(cmap.items(), key=lambda kv: kv[1])]
    write_json(out/"data"/NS/REG/"palettes"/f"{slug}_palette.json", {"palette": palette_entries})
    building_ids = []
    for cx in range(nx):
        for cz in range(nz):
            bid = f"{NS}:{slug}_c{cx}_{cz}"
            building_ids.append(bid)
            part_ids = []
            for fy in range(floors):
                pid = f"{slug}_c{cx}_{cz}_f{fy}"
                part_ids.append(f"{NS}:{pid}")
                slices = []
                for sy in range(fy*6, fy*6+6):
                    rows = []
                    for z in range(16):
                        row = []
                        for x in range(16):
                            gx, gz = cx*16+x, cz*16+z
                            if gx >= w or gz >= l or sy >= h:
                                state = "minecraft:air"
                            else:
                                state = get(gx,sy,gz)
                            row.append(cmap[state])
                        rows.append("".join(row))
                    slices.append(rows)
                write_json(out/"data"/NS/REG/"parts"/f"{pid}.json", {
                    "xsize":16, "zsize":16, "slices":slices,
                    "refpalette":palette_id
                })
            normal = max(1, floors-1)
            part_refs = []
            if floors == 1:
                part_refs.append({"part":part_ids[0], "ground":True})
                part_refs.append({"part":part_ids[0], "top":True})
            else:
                for fy in range(floors-1):
                    entry = {"part":part_ids[fy]}
                    if fy == 0: entry["ground"] = True
                    else: entry["floor"] = fy
                    part_refs.append(entry)
                part_refs.append({"part":part_ids[-1], "top":True})
            write_json(out/"data"/NS/REG/"buildings"/f"{slug}_c{cx}_{cz}.json", {
                "filler":"#", "rubble":"#", "refpalette":palette_id,
                "minfloors":normal, "maxfloors":normal,
                "mincellars":0, "maxcellars":0, "overrideFloors":True,
                "parts":part_refs
            })
    multi_id = None
    if nx*nz > 1:
        multi_id = f"{NS}:{slug}_multi"
        grid = [[f"{NS}:{slug}_c{cx}_{cz}" for cz in range(nz)] for cx in range(nx)]
        write_json(out/"data"/NS/REG/"multibuildings"/f"{slug}_multi.json", {
            "dimx":nx, "dimz":nz, "buildings":grid
        })
    manifest.append({
        "file":path.name, "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
        "sponge_version":version, "width":w, "height":h, "length":l,
        "chunk_footprint":[nx,nz], "six_block_segments":floors,
        "palette_states":len(cmap), "block_entities_ignored":block_entities,
        "vanilla_only":True, "buildings":building_ids, "multibuilding":multi_id
    })

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input", default="schematics/source")
    ap.add_argument("--output", default="build/neon_sprawl")
    args=ap.parse_args()
    src, out = Path(args.input), Path(args.output)
    if out.exists():
        import shutil; shutil.rmtree(out)
    manifest=[]
    errors=[]
    for path in sorted(src.glob("*.schem")):
        try: convert_one(path,out,manifest)
        except Exception as e: errors.append({"file":path.name,"error":str(e)})
    # Baseline vanilla palette/style and reachable city/world styles.
    write_json(out/"data"/NS/REG/"palettes"/"neon_palette.json", {"palette":[
        {"char":"#","block":"minecraft:polished_deepslate"},
        {"char":"G","block":"minecraft:cyan_stained_glass"},
        {"char":"M","block":"minecraft:magenta_stained_glass"},
        {"char":"A","block":"minecraft:ochre_froglight"},
        {"char":"L","block":"minecraft:sea_lantern"},
        {"char":"B","block":"minecraft:black_concrete"},
        {"char":"C","block":"minecraft:oxidized_cut_copper"},
        {"char":" ","block":"minecraft:air"}
    ]})
    write_json(out/"data"/NS/REG/"styles"/"neon_style.json", {"randompalettes":[
        [{"factor":1.0,"palette":"lostcities:common"}],
        [{"factor":1.0,"palette":f"{NS}:neon_palette"}]
    ]})
    selectors, multis = [], []
    for item in manifest:
        if item["multibuilding"]:
            multis.append({"factor":2.0,"value":item["multibuilding"]})
        else:
            for bid in item["buildings"]:
                selectors.append({"factor":1.5,"value":bid})
    city = {
        "inherit":"lostcities:citystyle_standard",
        "style":f"{NS}:neon_style",
        "selectors":{"buildings":selectors,"multibuildings":multis}
    }
    write_json(out/"data"/NS/REG/"citystyles"/"neon_city.json",city)
    write_json(out/"data"/NS/REG/"worldstyles"/"neon_sprawl.json",{
        "outsidestyle":"lostcities:citystyle_standard",
        "citystyles":[{"factor":1.0,"citystyle":f"{NS}:neon_city"}],
        "multisettings":{"areasize":10,"minimum":1,"maximum":3,"attempts":50}
    })
    write_json(out/"manifest.json",{"converted":manifest,"errors":errors})
    if errors:
        print(json.dumps(errors,indent=2),file=sys.stderr)
    print(f"Converted {len(manifest)} / {len(list(src.glob('*.schem')))} schematics; {len(errors)} errors")
    if not manifest: raise SystemExit(2)

if __name__=="__main__": main()
