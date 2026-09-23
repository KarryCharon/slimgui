# Contributor rules

- Every SlimGUI change that affects the published package must increment the
  version in `pyproject.toml` to the next regular release version. Consumers
  discover the newest wheel by the rolling package version.
- Keep platform-specific build changes in the build configuration. Release
  builds use `/O2 /DNDEBUG` on MSVC and `-O2 -DNDEBUG` elsewhere, and always
  pass nanobind's `NOMINSIZE` so it does not append `-Os`/`/Os`. Do not add
  platform-only compiler flags to shared source or runtime code.
- When changing the package version or native build configuration, run the
  wheel build workflow and verify the resulting wheel metadata and ABI tags.
