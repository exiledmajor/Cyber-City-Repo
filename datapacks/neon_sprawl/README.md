# Neon Sprawl datapack

This is the Minecraft 1.21.1 datapack destination for the Cyber City Lost Cities expansion.

## Build

The repository workflow reads unique Sponge `.schem` files from `schematics/source/`, converts them into Lost Cities parts/buildings/multibuildings, validates generated JSON, and publishes a ZIP artifact.

- Workflow: [Build Neon Sprawl datapack](../../actions/workflows/build-datapack.yml)
- Build output: GitHub Actions artifact named `neon-sprawl-datapack`
- Conversion report: artifact `neon-sprawl-conversion-manifest` and `SCHEMATIC_MANIFEST.json`

To run locally:

```bash
python -m pip install -r tools/requirements.txt
python tools/convert_schematics.py --input schematics/source --output build/generated
```

The generated registry assets are written beneath `build/generated/data/neoncity/lostcities/`.

## Install

1. Put the generated `neon_sprawl_datapack.zip` in the world's `datapacks/` folder (or extract it there).
2. Copy `config/lostcities/profiles/neon_sprawl.json` into the Minecraft instance's `config/lostcities/profiles/` folder.
3. Create a new world and select the **neon_sprawl** Lost Cities profile. Existing chunks are not regenerated when datapack assets change.

## Compatibility and conversion limits

- Target: Minecraft Java 1.21.1, NeoForge, Lost Cities 1.21-8.x.
- The converter reads Sponge schematic v2 and v3 layouts when their dimensions and block containers match the specification.
- Only vanilla block states are retained. Non-vanilla namespaces are replaced with approximate vanilla blocks and reported in the manifest.
- Block-entity NBT (sign text, container contents, etc.) is currently counted and reported, not restored.
- A schematic spanning multiple chunks is emitted as a Lost Cities multibuilding.
- Six-block segmentation is used to fit the Lost Cities floor model. This is a structural conversion, not a perfect in-game paste.
- Unsupported or malformed files are recorded in the manifest and skipped; they do not prevent supported schematics from building.

The generated assets have passed automated JSON validation when the build succeeds. They still require a fresh-world test with the exact installed Lost Cities 1.21.1 NeoForge build before being treated as fully game-verified.
