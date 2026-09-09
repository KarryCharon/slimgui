# Contributor rules

- Every SlimGUI change that affects the published package must increment the
  version in `pyproject.toml` to the next regular release version. Consumers
  discover the newest wheel by the rolling package version.
- Keep platform-specific build changes in the build configuration. The
  Windows MSVC Release configuration uses `/O2 /DNDEBUG` with nanobind's
  `NOMINSIZE`; non-MSVC builds retain `-Os -DNDEBUG`. Do not add Windows-only
  compiler flags to shared source or runtime code.
- When changing the package version or native build configuration, run the
  wheel build workflow and verify the resulting wheel metadata and ABI tags.
