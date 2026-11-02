# Cyber City — Lost Cities / Neon Sprawl

Cyber City is a Minecraft 1.21.1 NeoForge project focused on a cyberpunk conversion of McJty's The Lost Cities, using vanilla Minecraft blocks wherever possible.

## Repository layout

- `schematics/source/` — imported Sponge `.schem` structures synchronized from [Reference/Schems1/schemmys](https://github.com/exiledmajor/Reference/tree/main/Schems1/schemmys).
- `datapacks/neon_sprawl/` — Lost Cities datapack assets (in development).
- `config/lostcities/profiles/` — Lost Cities profile JSON files.
- `tools/` — schematic inspection and conversion utilities.
- `.github/workflows/` — automation for syncing source schematics.

## Target

- Minecraft Java 1.21.1
- NeoForge
- McJty Lost Cities 1.21-8.x
- Vanilla block palette; no custom blocks required for the core city generation.

## Status

The repository is being consolidated. The schematic sync workflow is the first integration step. The Lost Cities datapack conversion must be validated against the exact 1.21.1 asset schema before it is described as game-ready. See [PROJECT_STATUS.md](docs/PROJECT_STATUS.md).
