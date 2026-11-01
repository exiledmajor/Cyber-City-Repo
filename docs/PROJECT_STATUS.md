# Project status and migration plan

## Repository roles

- Destination: `exiledmajor/Cyber-City-Repo`
- Schematic source: `exiledmajor/Reference`, `Schems1/schemmys/`
- Previous working repository: `burtondole-ship-it/Lost-Cities-Future`

## Confirmed source inventory

The source directory contains 16 files with a `.schem` extension. Two filenames, `mega-cyber-thing.schem` and `mega-cyber-thing (1).schem`, are the same Git blob, leaving 15 unique structures. The folder also contains one legacy `.schematic` and one Bedrock `.mcstructure`; those are intentionally excluded from this Java schematic pipeline.

One `.schem` file, `futuristic-house.schem`, is actually Litematica region-based NBT. The converter detects and reads it despite the misleading extension.

## Implemented

- [x] Destination repository and integration branch created.
- [x] Automated sync copies unique `.schem` inputs into `schematics/source/`.
- [x] Sponge v2 and v3 decoding.
- [x] Litematica region decoding for the mislabeled file.
- [x] Conversion into 16×16 Lost Cities parts, building definitions, and multibuilding footprints.
- [x] Per-schematic vanilla palettes and solid-block filler selection.
- [x] Six-block floor segmentation and floor/top part constraints.
- [x] Neon Sprawl city style and world style using the built-in standard palette/style for compatibility with inherited Lost Cities streets and buildings.
- [x] Minecraft 1.21.1 profile source at `config/lostcities/profiles/neon_sprawl.json`.
- [x] Automated JSON validation and ZIP artifact publishing.
- [x] All 15 unique schematic inputs converted in the initial successful full conversion run.

## Compatibility and known limitations

- Target: Minecraft Java 1.21.1, NeoForge, Lost Cities 1.21-8.x.
- The converter retains vanilla block states and maps non-vanilla namespaces to approximate vanilla equivalents.
- It also backports several later vanilla block families (for example Pale Oak and later copper trim blocks) to 1.21.1-compatible equivalents.
- Block-entity NBT is counted in the manifest but not restored. Sign text, container contents, and similar payloads may therefore be lost.
- Six-block segmentation is a structural conversion. It does not guarantee a pixel-perfect paste of the source schematic.
- Generated assets have passed automated JSON parsing. This does not replace validation against the exact installed Lost Cities 1.21.1 JAR or an in-game world-generation test.

## Remaining validation

- [ ] Inspect the final conversion manifest and fallback list after the latest build.
- [ ] Validate all generated registry references against the exact Lost Cities 1.21.1 NeoForge JAR.
- [ ] Test in a fresh Minecraft 1.21.1 world with the `neon_sprawl` profile.
- [ ] Review in-game building alignment, floor counts, multi-chunk placement, and block-state compatibility.

The datapack is an automated build candidate, not yet declared game-ready.
