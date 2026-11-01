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
BLOCK_FALLBACKS = {}
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
    # nbtlib exposes the named root tag as an empty-string child in some
    # versions; Sponge v3 then wraps its payload in a Schematic compound.
    changed = True
    while changed and hasattr(root, "keys"):
        changed = False
        if "" in root and hasattr(root[""], "keys"):
            root = root[""]
            changed = True
        elif "Schematic" in root and hasattr(root["Schematic"], "keys"):
            root = root["Schematic"]
            changed = True
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
        base, sep, props = state.partition("[")
        if base in AIR_NAMES:
            return "minecraft:structure_void"
        original = state
        drop_properties = False
        # Backport newer vanilla content to blocks available in MC 1.21.1.
        if base.startswith("minecraft:pale_oak_"):
            base = base.replace("minecraft:pale_oak_", "minecraft:dark_oak_", 1)
        elif base in {"minecraft:pale_moss_block", "minecraft:pale_moss_carpet"}:
            base = "minecraft:moss_block" if base.endswith("_block") else "minecraft:moss_carpet"
            drop_properties = True
        elif base.startswith("minecraft:resin_"):
            base = "minecraft:orange_concrete"
            drop_properties = True
        elif base == "minecraft:creaking_heart":
            base = "minecraft:dark_oak_log"
            props = ",".join(p for p in props.rstrip("]").split(",") if p.startswith("axis="))
            drop_properties = not props
        elif base in {"minecraft:open_eyeblossom", "minecraft:closed_eyeblossom"}:
            base = "minecraft:flowering_azalea"
            drop_properties = True
        elif base == "minecraft:grass":
            base = "minecraft:short_grass"
            drop_properties = True
        elif base.endswith("_shelf"):
            base = "minecraft:bookshelf"
            drop_properties = True
        elif base == "minecraft:exposed_lightning_rod":
            base = "minecraft:lightning_rod"
        elif base.endswith("_copper_bars"):
            base = "minecraft:iron_bars"
        elif base.endswith("_copper_chain"):
            base = "minecraft:chain"
        elif base.endswith("_copper_trapdoor"):
            base = "minecraft:iron_trapdoor"
        elif base.endswith("_copper_door"):
            base = "minecraft:iron_door"
        elif base.endswith("_chiseled_copper"):
            base = base.replace("_chiseled_copper", "_cut_copper")
            drop_properties = True
        elif base.endswith("_cut_copper_stairs") or base.endswith("_cut_copper_slab"):
            base = base.rsplit("_",1)[0]
            drop_properties = True
        result = base + (sep + props if sep and not drop_properties else "")
        if result != original:
            BLOCK_FALLBACKS[original] = result
        return result
    low = state.lower()
    for pattern, replacement in FALLBACKS:
        if re.search(pattern, low):
            return replacement
    return "minecraft:polished_deepslate"

def slugify(name):
    s = re.sub(r"[^a-z0-9_]+", "_", Path(name).stem.lower()).strip("_")
    return (s[:48] or "imported_structure")

def decode_litematic(nbt):
    regions = nbt["Regions"]
    parsed = []
    for region_name, region in regions.items():
        pos, size = region["Position"], region["Size"]
        px, py, pz = (int(pos[k]) for k in ("x","y","z"))
        sx, sy, sz = (int(size[k]) for k in ("x","y","z"))
        dx, dy, dz = abs(sx), abs(sy), abs(sz)
        if min(dx,dy,dz) < 1:
            continue
        palette = []
        for entry in region["BlockStatePalette"]:
            name = str(entry["Name"])
            props = entry["Properties"] if "Properties" in entry else {}
            if props:
                state = name + "[" + ",".join(f"{k}={props[k]}" for k in sorted(props.keys())) + "]"
            else:
                state = name
            palette.append(vanilla_state(state))
        longs = [int(v) & ((1 << 64)-1) for v in region["BlockStates"]]
        bits = max(2, (len(palette)-1).bit_length())
        mask = (1 << bits)-1
        volume = dx*dy*dz
        values = []
        for index in range(volume):
            bit_index = index*bits
            li, offset = divmod(bit_index,64)
            value = longs[li] >> offset
            if offset+bits > 64:
                value |= longs[li+1] << (64-offset)
            palette_index = value & mask
            values.append(palette[palette_index] if palette_index < len(palette) else "minecraft:air")
        # Negative Litematica sizes indicate a mirrored axis.
        minx, maxx = (px, px+sx-1) if sx > 0 else (px+sx+1, px)
        miny, maxy = (py, py+sy-1) if sy > 0 else (py+sy+1, py)
        minz, maxz = (pz, pz+sz-1) if sz > 0 else (pz+sz+1, pz)
        parsed.append((px,py,pz,sx,sy,sz,dx,dy,dz,values,
                       minx,maxx,miny,maxy,minz,maxz,
                       len(region["TileEntities"]) if "TileEntities" in region else 0))
    if not parsed:
        raise ValueError("Litematica file has no non-empty regions")
    minx=min(r[10] for r in parsed); maxx=max(r[11] for r in parsed)
    miny=min(r[12] for r in parsed); maxy=max(r[13] for r in parsed)
    minz=min(r[14] for r in parsed); maxz=max(r[15] for r in parsed)
    w,h,l=maxx-minx+1,maxy-miny+1,maxz-minz+1
    if max(w,h,l)>2048:
        raise ValueError(f"Unreasonable Litematica bounds {w}x{h}x{l}")
    blocks=["minecraft:air"]*(w*h*l)
    block_entities=0
    for r in parsed:
        px,py,pz,sx,sy,sz,dx,dy,dz,values,*rest=r
        rx0,rx1,ry0,ry1,rz0,rz1,be=r[10:]
        block_entities += be
        for y in range(dy):
            gy=(py+y if sy>0 else py-y)-miny
            for z in range(dz):
                gz=(pz+z if sz>0 else pz-z)-minz
                for x in range(dx):
                    gx=(px+x if sx>0 else px-x)-minx
                    source=x+z*dx+y*dx*dz
                    blocks[gx+gz*w+gy*w*l]=values[source]
    def get(x,y,z):
        return blocks[x+z*w+y*w*l]
    return w,h,l,get,int(nbt["Version"]),block_entities,"litematica",int(nbt["MinecraftDataVersion"])

def load_schematic(path):
    nbt = read_nbt(path)
    missing = [k for k in ("Width", "Height", "Length") if k not in nbt]
    if missing:
        if "Regions" in nbt and "Metadata" in nbt:
            return decode_litematic(nbt)
        raise ValueError(f"Missing dimensions {missing}; NBT keys={list(nbt.keys())}")
    w, h, l = (int(nbt[k]) for k in ("Width", "Height", "Length"))
    if min(w,h,l) < 1 or max(w,h,l) > 2048:
        raise ValueError(f"Unreasonable dimensions {w}x{h}x{l}")
    # Sponge v2 stores Palette/BlockData at schematic root. v3 nests
    # Palette/Data/BlockEntities under Schematic.Blocks.
    container = nbt["Blocks"] if "Blocks" in nbt else nbt
    palette_tag = container["Palette"] if "Palette" in container else nbt["Palette"]
    data_tag = container["Data"] if "Data" in container else (nbt["BlockData"] if "BlockData" in nbt else container["BlockData"])
    palette = {str(k): int(v) for k,v in palette_tag.items()}
    indices = varints(data_tag)
    expected = w*h*l
    if len(indices) != expected:
        raise ValueError(f"Block data has {len(indices)} entries; expected {expected}")
    states = [None] * (max(palette.values(), default=-1)+1)
    for state, idx in palette.items():
        states[idx] = vanilla_state(state)
    blocks = [states[i] if i < len(states) and states[i] is not None else "minecraft:air" for i in indices]
    # Sponge linear order: x fastest, then z, then y.
    def get(x,y,z):
        return blocks[x + z*w + y*w*l]
    be = container["BlockEntities"] if "BlockEntities" in container else (nbt["BlockEntities"] if "BlockEntities" in nbt else [])
    return w,h,l,get,int(nbt["Version"]) if "Version" in nbt else 2, len(be), ("sponge_v3" if "Blocks" in nbt else "sponge_v2"), int(nbt["DataVersion"]) if "DataVersion" in nbt else 0

def choose_filler(cmap):
    preferred = [
        "minecraft:polished_deepslate", "minecraft:deepslate_bricks",
        "minecraft:stone_bricks", "minecraft:black_concrete",
        "minecraft:gray_concrete", "minecraft:iron_block",
        "minecraft:polished_blackstone", "minecraft:bricks",
        "minecraft:stone", "minecraft:deepslate", "minecraft:andesite"
    ]
    for state in preferred:
        if state in cmap:
            return state
    excluded = ("_slab", "_stairs", "_fence", "_wall", "_pane", "_glass",
                "_trapdoor", "_door", "_button", "_pressure_plate", "_sign",
                "_banner", "_torch", "_rod", "_chain", "_rail", "_carpet",
                "_leaves", "_sapling", "_flower", "_plant", "_pot", "_head",
                "_skull", "_bed", "_chest", "_barrel", "_shulker_box",
                "_grindstone", "_lever", "_ladder", "_scaffolding", "_vine",
                "_lichen", "_coral", "_bamboo", "_water", "_lava", "_air")
    for state in sorted(cmap):
        base = state.split("[",1)[0]
        if base not in AIR_NAMES and base != "minecraft:structure_void" and not base.endswith(excluded):
            return state
    return "minecraft:polished_deepslate"

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
    BLOCK_FALLBACKS.clear()
    w,h,l,get,version,block_entities,source_format,data_version = load_schematic(path)
    slug = slugify(path.name)
    nx, nz = math.ceil(w/16), math.ceil(l/16)
    floors = max(1, math.ceil(h/6))
    all_states = {get(x,y,z) for y in range(h) for z in range(l) for x in range(w)}
    all_states.add("minecraft:air")
    cmap = char_map(all_states)
    filler_state = choose_filler(cmap)
    filler_char = cmap[filler_state]
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
                "filler":filler_char, "rubble":filler_char, "refpalette":palette_id,
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
        "source_format":source_format, "source_version":version, "minecraft_data_version":data_version, "filler_block":filler_state, "width":w, "height":h, "length":l,
        "chunk_footprint":[nx,nz], "six_block_segments":floors,
        "palette_states":len(cmap), "block_fallbacks":dict(BLOCK_FALLBACKS), "block_entities_ignored":block_entities,
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
    # Use the built-in standard palette style. Each imported building and part
    # references its own local palette, so stock Lost Cities palette characters
    # remain untouched for inherited streets, parks, and buildings.
    selectors, multis = [], []
    for item in manifest:
        if item["multibuilding"]:
            multis.append({"factor":2.0,"value":item["multibuilding"]})
        else:
            for bid in item["buildings"]:
                selectors.append({"factor":1.5,"value":bid})
    city = {
        "inherit":"lostcities:citystyle_standard",
        "style":"standard",
        "selectors":{"buildings":selectors,"multibuildings":multis}
    }
    write_json(out/"data"/NS/REG/"citystyles"/"neon_city.json",city)
    write_json(out/"data"/NS/REG/"worldstyles"/"neon_sprawl.json",{
        "outsidestyle":"outside",
        "citystyles":[{"factor":1.0,"citystyle":f"{NS}:neon_city"}],
        "multisettings":{"areasize":10,"minimum":1,"maximum":3,"attempts":50}
    })
    write_json(out/"manifest.json",{"converted":manifest,"errors":errors})
    if errors:
        print(json.dumps(errors,indent=2),file=sys.stderr)
    print(f"Converted {len(manifest)} / {len(list(src.glob('*.schem')))} schematics; {len(errors)} errors")
    if not manifest: raise SystemExit(2)

if __name__=="__main__": main()
