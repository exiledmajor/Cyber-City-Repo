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
- [x] Structural Lost Cities asset validator integrated into CI: palette character uniqueness and BMP limits, part dimensions/character coverage, building/part/palette links, multibuilding dimensions, city-style selectors, world-style links, and profile worldStyle reachability.
- [x] Compared generated resource shapes against the extracted built-in assets from the exact Lost Cities 1.21-8.4.6 JAR supplied in Reference-2.
- [x] All 15 unique schematic inputs converted with zero converter errors in the latest successful build.

## Generated output (latest successful build)

- 15/15 unique schematic inputs converted; no conversion errors.
- Input formats detected: Sponge v2, Sponge v3, and one Litematica file mislabeled as `.schem`.
- 15 local palettes, 15,976 building parts, 386 building definitions, and 14 multibuilding definitions.
- One standalone single-cell building and 14 multi-cell structure layouts.
- The latest manifest reports 1,162 ignored block entities across the inputs; sign text, inventories, and other block-entity payloads are not preserved.
- The converter manifest records source data versions, dimensions, footprints, filler blocks, ignored block-entity counts, and all block substitutions.
- The ZIP datapack and conversion manifest are published as GitHub Actions artifacts.

## Compatibility and known limitations

- Target: Minecraft Java 1.21.1, NeoForge, Lost Cities 1.21-8.x.
- The converter retains vanilla block states and maps non-vanilla namespaces to approximate vanilla equivalents.
- It also backports several later vanilla block families (for example Pale Oak and later copper trim blocks) to 1.21.1-compatible equivalents.
- Block-entity NBT is counted in the manifest but not restored. Sign text, container contents, and similar payloads may therefore be lost.
- Six-block segmentation is a structural conversion. It does not guarantee a pixel-perfect paste of the source schematic.
- The generated asset graph passes automated structural validation against the extracted Lost Cities 1.21-8.4.6 asset conventions. The validator checks internal references and one-character BMP palette keys; it does not prove every block-state property exists in the Minecraft 1.21.1 registry.
- High-cardinality palettes use Unicode private-use characters within the BMP after the printable character pool is exhausted. The validator rejects supplementary-plane characters because Java's UTF-16 character handling would treat those as two code units.
- Automated structural validation and successful ZIP packaging do not replace a fresh-world runtime test.

## Remaining validation

- [x] Inspect the final conversion manifest and fallback list after the latest build.
- [x] Inspect representative built-in building, part, palette, multibuilding, city-style, and world-style JSON from the exact 1.21-8.4.6 reference extraction.
- [x] Add CI checks for the generated resource graph and BMP-safe palette characters.
- [ ] Validate every generated block ID and block-state property against the Minecraft 1.21.1 vanilla registry.
- [ ] Test in a fresh Minecraft 1.21.1 NeoForge world with the `neon_sprawl` profile.
- [ ] Review in-game building alignment, floor counts, multi-chunk placement, and block-state compatibility.

The datapack is an automated build candidate, not yet declared game-ready.
