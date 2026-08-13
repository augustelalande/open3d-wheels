# open3d-wheels

CPU-only [Open3D](https://github.com/isl-org/Open3D) wheels for the platforms and
Python versions upstream does not publish, served from a PEP 503 index on GitHub
Pages.

| Platform | CPython | Why it is here |
|---|---|---|
| `manylinux_2_35_aarch64` | 3.10–3.14 | upstream publishes no arm64 wheels at all |
| `manylinux_2_35_x86_64` | 3.13–3.14 | PyPI's `open3d-cpu` stops at 3.12 |
| `win_amd64` | 3.13–3.14 | PyPI's `open3d` stops at 3.12 |

## Usage

Everything here is one distribution, **`open3d-cpu`**, so a single requirement
works on every platform. With uv:

```toml
[[tool.uv.index]]
name = "open3d-wheels"
url = "https://augustelalande.github.io/open3d-wheels/simple/"
```

With pip:

```bash
pip install --extra-index-url https://augustelalande.github.io/open3d-wheels/simple/ open3d-cpu
```

The importable package is `open3d` regardless — only the distribution name
differs, so `import open3d` is unchanged.

Every link in the index carries a `sha256` fragment, so downloads are verified.
Wheels can also be installed directly from
[Releases](https://github.com/augustelalande/open3d-wheels/releases/latest) by URL.

## Naming

Upstream renames CPU-only builds to `open3d-cpu` on Linux x86_64 only, because
that is the one platform where the default `open3d` is CUDA-enabled. Its arm64
and Windows builds keep the plain `open3d` name despite being equally CPU-only,
which would make the dependency differ by platform for no real reason.

So the arm64 and Windows wheels are relabelled to `open3d-cpu` to match, by
[`scripts/rename_distribution.py`](scripts/rename_distribution.py). That is a
metadata change only — the `.dist-info` directory, the `Name:` field and
`RECORD`. The compiled modules are byte-identical to what the build produced.

Relabelling happens at publish time, not during the build, so the build
workflows stay a faithful reproduction of upstream and the one deviation lives
in a single place.

## Requirements

- On Linux, **glibc ≥ 2.35**, as the `manylinux_2_35_*` tags declare. JetPack 6
  / Ubuntu 22.04 qualifies; JetPack 5 / Ubuntu 20.04 (glibc 2.31) does not.
- **CPU only, no CUDA.** Upstream says the same of its own arm64 builds: CUDA on
  Jetson needs a manual build against JetPack's CUDA, which cannot be done on a
  generic runner.

## Built from `main`, not a release

v0.19.0 (January 2025) is still the newest Open3D release and its build script
stops at `openblas-arm64-py312`, so no released version can produce a 3.13 or
3.14 wheel. These are built from a pinned commit on `main` — the same source
upstream's own development wheel index uses.

That commit still reports version `0.19.0`, because upstream bumps the number
only at release time. **These are not the 0.19.0 release**; each release records
the exact commit.

Every wheel in a batch comes from one commit. Mixing a release tag for the older
Pythons with `main` for the newer ones would publish two different Open3D
versions under a single distribution name, which resolvers handle badly.

## Build environment

**Linux** uses upstream's `docker/docker_build.sh openblas-{arm64,amd64}-py3XX`
unmodified. Building a **release tag** would need one fix — `Dockerfile.openblas`
fetches `Miniconda3-latest`, and current Miniconda refuses to create an
environment from Anaconda's default channels until their Terms of Service are
accepted, so the workflow inserts `ENV CONDA_PLUGINS_AUTO_ACCEPT_TOS=yes` ahead
of that step. It does not fire for `main`, which uses pyenv instead of conda.

**Windows** has no `docker_build.sh` equivalent. Upstream splits the C++ core
from the pybind module across two jobs so the core compiles once for many
Pythons; at two Pythons that costs more than it saves, so each job builds the
whole tree. The Azure Kinect and RealSense SDKs, WebRTC and the Jupyter
extension are disabled — they carry the heaviest and least reliable dependencies
and are not why these wheels exist. `BUILD_GUI` is on, so
`open3d.visualization` works. These wheels are therefore slightly leaner than
PyPI's official Windows ones, for two Pythons PyPI does not ship at all.

## Workflows

- `build.yml` — Linux, takes an Open3D ref, a set of Pythons and a set of
  architectures.
- `build-windows.yml` — Windows, takes a ref and a set of Pythons.
- `pages.yml` — regenerates the index from release assets; runs automatically
  when a release changes.

The index links to release assets rather than hosting them: Pages allows a 1 GB
site and a soft 100 GB/month of bandwidth, and one release of these wheels is
already ~400 MB.

## Not official

Unaffiliated with Intel or the Open3D maintainers. Open3D is MIT licensed; these
are builds of its unmodified source.
