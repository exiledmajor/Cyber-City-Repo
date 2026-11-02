#!/usr/bin/env python3
"""Structural validator for the generated Neon Sprawl Lost Cities datapack.

This checks the resource graph and the documented JSON shape against the
extracted Lost Cities 1.21.1 reference assets. It deliberately does not claim
to validate Minecraft's complete 1.21.1 block registry or replace an in-game
world-generation test.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

ROOT = Path("datapacks/neon_sprawl")
DATA = ROOT / "data"
PROFILE = Path("config/lostcities/profiles/neon_sprawl.json")
REG = "lostcities"
errors: list[str] = []
counts = {"json": 0, "palettes": 0, "parts": 0, "buildings": 0, "multibuildings": 0}

def fail(where: str, message: str) -> None:
    errors.append(f"{where}: {message}")

def read_json(path: Path):
    global counts
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        counts["json"] += 1
        return obj
    except Exception as exc:
        fail(str(path), f"invalid JSON: {exc}")
        return None

def resource_path(kind: str, ref: str) -> Path | None:
    if not isinstance(ref, str) or not ref:
        return None
    namespace, sep, name = ref.partition(":")
    if not sep:
        namespace, name = "neoncity", ref
    if not re.fullmatch(r"[a-z0-9_.-]+", namespace):
        return None
    if not re.fullmatch(r"[a-z0-9_./-]+", name) or name.startswith("/") or ".." in name.split("/"):
        return None
    return DATA / namespace / REG / kind / (name + ".json")

def load_index(kind: str) -> dict[str, tuple[Path, dict]]:
    folder = DATA / "neoncity" / REG / kind
    index = {}
    for path in sorted(folder.glob("*.json")):
        obj = read_json(path)
        if isinstance(obj, dict):
            index[f"neoncity:{path.stem}"] = (path, obj)
    return index

def check_palette(path: Path, obj: dict) -> set[str]:
    entries = obj.get("palette")
    if not isinstance(entries, list) or not entries:
        fail(str(path), "palette must be a non-empty array")
        return set()
    chars = []
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            fail(str(path), f"palette[{i}] must be an object")
            continue
        ch = entry.get("char")
        if not isinstance(ch, str) or len(ch) != 1:
            fail(str(path), f"palette[{i}].char must be exactly one Unicode character")
            continue
        chars.append(ch)
        block = entry.get("block")
        if not isinstance(block, str) or not re.fullmatch(r"[a-z0-9_.-]+:[a-z0-9_./-]+(?:\[[a-z0-9_.,= -]+\])?", block):
            fail(str(path), f"palette[{i}] has invalid block-state syntax: {block!r}")
        elif not block.startswith("minecraft:"):
            fail(str(path), f"non-vanilla block is not allowed: {block}")
    if len(chars) != len(set(chars)):
        fail(str(path), "palette contains duplicate character keys")
    return set(chars)

def main() -> int:
    if not ROOT.exists():
        print(f"Missing datapack directory: {ROOT}", file=sys.stderr)
        return 2

    palettes = {}
    for path in sorted((DATA / "neoncity" / REG / "palettes").glob("*.json")):
        obj = read_json(path)
        if isinstance(obj, dict):
            palettes[f"neoncity:{path.stem}"] = (path, check_palette(path, obj))
            counts["palettes"] += 1

    parts = {}
    for path in sorted((DATA / "neoncity" / REG / "parts").glob("*.json")):
        obj = read_json(path)
        if not isinstance(obj, dict):
            continue
        counts["parts"] += 1
        xsize, zsize, slices = obj.get("xsize"), obj.get("zsize"), obj.get("slices")
        if not isinstance(xsize, int) or not isinstance(zsize, int) or xsize < 1 or zsize < 1:
            fail(str(path), "xsize and zsize must be positive integers")
            continue
        if not isinstance(slices, list) or not slices:
            fail(str(path), "slices must be a non-empty array")
            continue
        pref = obj.get("refpalette")
        ppath = resource_path("palettes", pref) if pref else None
        if ppath is None:
            fail(str(path), f"missing or invalid refpalette: {pref!r}")
            valid_chars = set()
        else:
            key = pref if ":" in pref else f"neoncity:{pref}"
            valid_chars = palettes.get(key, (None, set()))[1]
            if key not in palettes:
                fail(str(path), f"palette does not exist: {key}")
        for si, layer in enumerate(slices):
            if not isinstance(layer, list) or len(layer) != zsize:
                fail(str(path), f"slices[{si}] must contain exactly {zsize} rows")
                continue
            for zi, row in enumerate(layer):
                if not isinstance(row, str) or len(row) != xsize:
                    fail(str(path), f"slices[{si}][{zi}] must be a string of {xsize} characters")
                    continue
                unknown = set(row) - valid_chars
                if unknown:
                    fail(str(path), f"slices[{si}][{zi}] uses undefined palette characters: {''.join(sorted(unknown))!r}")
        parts[f"neoncity:{path.stem}"] = obj

    buildings = {}
    for path in sorted((DATA / "neoncity" / REG / "buildings").glob("*.json")):
        obj = read_json(path)
        if not isinstance(obj, dict):
            continue
        counts["buildings"] += 1
        bid = f"neoncity:{path.stem}"
        buildings[bid] = obj
        pref = obj.get("refpalette")
        pkey = pref if isinstance(pref, str) and ":" in pref else f"neoncity:{pref}" if isinstance(pref, str) else ""
        if pkey not in palettes:
            fail(str(path), f"refpalette does not exist: {pref!r}")
            filler_chars = set()
        else:
            filler_chars = palettes[pkey][1]
        for field in ("filler", "rubble"):
            ch = obj.get(field)
            if not isinstance(ch, str) or len(ch) != 1 or ch not in filler_chars:
                fail(str(path), f"{field} must be one character defined by {pkey}")
        refs = obj.get("parts")
        if not isinstance(refs, list) or not refs:
            fail(str(path), "parts must be a non-empty array")
            continue
        for i, entry in enumerate(refs):
            if not isinstance(entry, dict) or not isinstance(entry.get("part"), str):
                fail(str(path), f"parts[{i}] must contain a part resource id")
                continue
            ref = entry["part"]
            key = ref if ":" in ref else f"neoncity:{ref}"
            if key not in parts:
                fail(str(path), f"part resource does not exist: {key}")
            elif parts[key].get("refpalette") not in (pref, pkey):
                fail(str(path), f"part {key} uses a different palette than its building")

    multis = {}
    for path in sorted((DATA / "neoncity" / REG / "multibuildings").glob("*.json")):
        obj = read_json(path)
        if not isinstance(obj, dict):
            continue
        counts["multibuildings"] += 1
        mid = f"neoncity:{path.stem}"
        multis[mid] = obj
        dx, dz, grid = obj.get("dimx"), obj.get("dimz"), obj.get("buildings")
        if not isinstance(dx, int) or not isinstance(dz, int) or dx < 1 or dz < 1:
            fail(str(path), "dimx and dimz must be positive integers")
            continue
        if not isinstance(grid, list) or len(grid) != dx:
            fail(str(path), f"buildings must have dimx={dx} columns")
            continue
        for x, column in enumerate(grid):
            if not isinstance(column, list) or len(column) != dz:
                fail(str(path), f"buildings[{x}] must have dimz={dz} entries")
                continue
            for z, ref in enumerate(column):
                key = ref if isinstance(ref, str) and ":" in ref else f"neoncity:{ref}" if isinstance(ref, str) else ""
                if key not in buildings:
                    fail(str(path), f"buildings[{x}][{z}] references missing building {ref!r}")

    citystyles = {}
    for path in sorted((DATA / "neoncity" / REG / "citystyles").glob("*.json")):
        obj = read_json(path)
        if not isinstance(obj, dict):
            continue
        citystyles[f"neoncity:{path.stem}"] = obj
        selectors = obj.get("selectors", {})
        if not isinstance(selectors, dict):
            fail(str(path), "selectors must be an object")
            continue
        for kind, index in (("buildings", buildings), ("multibuildings", multis)):
            entries = selectors.get(kind, [])
            if not isinstance(entries, list):
                fail(str(path), f"selectors.{kind} must be an array")
                continue
            for i, entry in enumerate(entries):
                ref = entry.get("value") if isinstance(entry, dict) else None
                key = ref if isinstance(ref, str) and ":" in ref else f"neoncity:{ref}" if isinstance(ref, str) else ""
                if key not in index:
                    fail(str(path), f"selectors.{kind}[{i}] references missing resource {ref!r}")

    worldstyles = {}
    for path in sorted((DATA / "neoncity" / REG / "worldstyles").glob("*.json")):
        obj = read_json(path)
        if not isinstance(obj, dict):
            continue
        worldstyles[f"neoncity:{path.stem}"] = obj
        styles = obj.get("citystyles")
        if not isinstance(styles, list) or not styles:
            fail(str(path), "citystyles must be a non-empty array")
            continue
        for i, entry in enumerate(styles):
            ref = entry.get("citystyle") if isinstance(entry, dict) else None
            key = ref if isinstance(ref, str) and ":" in ref else f"neoncity:{ref}" if isinstance(ref, str) else ""
            if key not in citystyles:
                fail(str(path), f"citystyles[{i}] references missing city style {ref!r}")

    profile = read_json(PROFILE)
    if isinstance(profile, dict):
        profile_worldstyle = profile.get("lostcity", {}).get("worldStyle")
        key = profile_worldstyle if isinstance(profile_worldstyle, str) and ":" in profile_worldstyle else f"neoncity:{profile_worldstyle}"
        if key not in worldstyles:
            fail(str(PROFILE), f"lostcity.worldStyle does not resolve: {profile_worldstyle!r}")

    mcmeta = read_json(ROOT / "pack.mcmeta")
    if isinstance(mcmeta, dict) and not isinstance(mcmeta.get("pack", {}).get("pack_format"), int):
        fail(str(ROOT / "pack.mcmeta"), "pack.pack_format must be an integer")

    print("Neon Sprawl structural validation:")
    for key, value in counts.items():
        print(f"  {key}: {value}")
    if errors:
        print(f"FAILED: {len(errors)} validation error(s)", file=sys.stderr)
        for error in errors[:100]:
            print(f"  - {error}", file=sys.stderr)
        if len(errors) > 100:
            print(f"  ... and {len(errors)-100} more", file=sys.stderr)
        return 1
    print("PASS: JSON syntax, palette keys, part dimensions, resource references, multibuilding grids, style links, and profile worldStyle.")
    print("NOTE: Minecraft block registry validity and actual world generation still require runtime testing.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
