# open3d-wheels

Linux arm64 wheels for [Open3D](https://github.com/isl-org/Open3D), built from
upstream's own release tags with upstream's own build script.

## Why

Open3D publishes wheels for Python 3.10–3.14 on Linux x86_64, Windows x86_64 and
macOS universal2, including on its
[development wheel index](https://www.open3d.org/docs/latest/getting_started.html).
Linux **arm64** is the gap — there are no wheels for it on either index, so
`pip install open3d` on a Jetson or other arm64 Linux board finds nothing.

These are the stock `docker/docker_build.sh openblas-arm64-pyXXX` targets, run on
GitHub's arm64 runners. No source patches.

## What these are not

- **Not CUDA builds.** Upstream's arm64 wheels are CPU-only too: "Open3D
  installed via `pip install open3d` will not contain CUDA support on ARM64
  platforms." CUDA on Jetson needs a manual build against JetPack's CUDA, which
  cannot be done on a generic arm64 runner.
- **Not official.** Unaffiliated with Intel or the Open3D maintainers. Open3D is
  MIT licensed; these are unmodified builds of their source.

## Status

Spike. Nothing published yet — the build workflow is manual and uploads a
throwaway artifact while the arm64 build is being proven out.

## Usage

Once wheels are published they will be served from a PEP 503 index on GitHub
Pages:

```toml
[[tool.uv.index]]
name = "open3d-wheels"
url = "https://augustelalande.github.io/open3d-wheels/simple/"
```

The distribution keeps its upstream name, `open3d`, so nothing else changes.

## Provenance

Each release records the upstream tag it was built from. The build is
`docker/docker_build.sh` from that tag, unmodified, on `ubuntu-24.04-arm`.
