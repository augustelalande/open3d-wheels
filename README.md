# open3d-wheels

Linux arm64 wheels for [Open3D](https://github.com/isl-org/Open3D), Python
3.10–3.14, built with upstream's own build script.

## Why

Open3D publishes wheels for Python 3.10–3.14 on Linux x86_64, Windows x86_64 and
macOS universal2, including on its
[development wheel index](https://www.open3d.org/docs/latest/getting_started.html).
Linux **arm64** is the gap — there are no wheels for it on either index, so
`pip install open3d` on a Jetson or other arm64 Linux board finds nothing.

These are the stock `docker/docker_build.sh openblas-arm64-pyXXX` targets, run on
GitHub's arm64 runners. No patches to Open3D itself — see
[Build environment](#build-environment) for the one line the workflow does change.

## Built from `main`, not a release

v0.19.0 (January 2025) is still the newest Open3D release, and it predates
Python 3.13 support: its build script stops at `openblas-arm64-py312`. There is
no released version that can produce a 3.13 or 3.14 wheel, so these are built
from a pinned commit on `main` — the same source upstream's own development
wheel index is built from.

Every wheel in a given batch comes from one commit. Mixing a release tag for the
older Pythons with `main` for the newer ones would publish two different Open3D
versions under a single distribution name, which resolvers handle badly.

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

## Build environment

Building a **release tag** needs one fix. Upstream pins the Open3D source but
not its toolchain: `Dockerfile.openblas` fetches `Miniconda3-latest`, and
current Miniconda refuses to create an environment from Anaconda's default
channels until their Terms of Service are accepted. That makes those builds fail
at `conda create`, on every architecture. The workflow inserts one line —

```dockerfile
ENV CONDA_PLUGINS_AUTO_ACCEPT_TOS=yes
```

— ahead of that step. It accepts the channel ToS non-interactively and changes
nothing else about the build.

Building from **`main`** needs no fix: upstream replaced Miniconda with pyenv
after v0.19.0, and the workflow skips the patch when there is no conda to patch.

## Provenance

Each release records the exact upstream commit it was built from. The build is
`docker/docker_build.sh` from that commit, on `ubuntu-24.04-arm`, with only the
Dockerfile line above added where it applies.
