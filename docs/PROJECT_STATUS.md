# Project status and migration plan

## Repository roles

- Destination: `exiledmajor/Cyber-City-Repo`
- Schematic source: `exiledmajor/Reference`, `Schems1/schemmys/`
- Previous working repository: `burtondole-ship-it/Lost-Cities-Future`

## Confirmed source inventory (2026-11-01)

The Reference directory currently contains 16 files ending in `.schem`. Two filenames, `mega-cyber-thing.schem` and `mega-cyber-thing (1).schem`, resolve to the same Git blob and are an exact duplicate. The sync workflow deduplicates by content hash. The folder also contains one legacy `.schematic` and one Bedrock `.mcstructure`; these are deliberately not included in the Sponge `.schem` pipeline.

## Planned project structure

1. Preserve original `.schem` inputs under `schematics/source/`.
2. Inspect dimensions, palette entries, block entities, and data version for each schematic.
3. Convert supported structures into Lost Cities building parts and multibuilding definitions.
4. Integrate the generated assets into the Neon Sprawl city style and world style.
5. Validate JSON and registry references against the installed Lost Cities 1.21.1 JAR.
6. Test generation in a clean NeoForge 1.21.1 instance.

## Compatibility boundary

A Sponge `.schem` file is not itself a Lost Cities building definition. It must be decoded and segmented into Lost Cities parts, with correct palette/state mapping, floor definitions, footprint handling, and multibuilding metadata. Importing files into Git does not mean they are active in world generation.

## Current status

- [x] Destination repository verified and writable through the connected GitHub account.
- [x] Schematic source directory inspected.
- [x] Integration branch created.
- [x] Automated source sync workflow added.
- [ ] Run the workflow and confirm source files land in this repository.
- [ ] Restore/port earlier Neon Sprawl datapack assets.
- [ ] Validate converter against actual `.schem` payloads and Lost Cities 1.21.1 schemas.
- [ ] Perform in-game generation test.

No datapack is marked game-ready until those validation steps pass.
