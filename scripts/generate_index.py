"""Generate a PEP 503 simple index from this repository's release assets.

The wheels stay in Releases and the index only links out to them. GitHub Pages
has a 1 GB site limit and a soft 100 GB/month bandwidth limit, and one release
of these wheels is already ~235 MB, so serving the files from Pages itself
would not last.

Standard library only, so the workflow needs no install step.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

API = 'https://api.github.com'

# Extensions pip will consider. Anything else in a release (checksums, notes)
# is ignored rather than being offered as a distribution.
DIST_SUFFIXES = ('.whl', '.tar.gz', '.zip')


def api_get(path: str, token: str | None) -> list[dict]:
    """GET a paginated API endpoint and return every item."""
    items: list[dict] = []
    page = 1
    while True:
        url = f'{API}{path}?per_page=100&page={page}'
        headers = {
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
            'User-Agent': 'open3d-wheels-index',
        }
        if token:
            headers['Authorization'] = f'Bearer {token}'
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                batch = json.load(resp)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode('utf-8', 'replace')[:400]
            raise SystemExit(f'GET {url} failed: {exc.code} {exc.reason}\n{body}')
        items.extend(batch)
        if len(batch) < 100:
            return items
        page += 1


def normalize(name: str) -> str:
    """PEP 503 name normalization."""
    return re.sub(r'[-_.]+', '-', name).lower()


def project_of(filename: str) -> str | None:
    """Project name for a distribution filename, or None if unrecognised."""
    if filename.endswith('.whl'):
        # {distribution}-{version}(-{build})?-{python}-{abi}-{platform}.whl
        parts = filename.split('-')
        if len(parts) < 5:
            return None
        return normalize(parts[0])
    for suffix in ('.tar.gz', '.zip'):
        if filename.endswith(suffix):
            stem = filename[: -len(suffix)]
            if '-' not in stem:
                return None
            return normalize(stem.rsplit('-', 1)[0])
    return None


def collect(repo: str, token: str | None) -> dict[str, list[dict]]:
    """Map normalized project name -> its distribution files, newest first."""
    projects: dict[str, list[dict]] = defaultdict(list)
    releases = api_get(f'/repos/{repo}/releases', token)
    for release in releases:
        if release.get('draft'):
            continue
        for asset in release.get('assets', []):
            name = asset['name']
            if not name.endswith(DIST_SUFFIXES):
                continue
            project = project_of(name)
            if project is None:
                print(f'skipping unrecognised asset: {name}', file=sys.stderr)
                continue
            projects[project].append(
                {
                    'name': name,
                    'url': asset['browser_download_url'],
                    # The API reports "sha256:<hex>"; PEP 503 wants the hash in
                    # a URL fragment so pip can verify the download.
                    'digest': (asset.get('digest') or '').removeprefix('sha256:'),
                    'release': release['tag_name'],
                }
            )
    return projects


def write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding='utf-8', newline='\n')
    print(f'wrote {path}')


def page(title: str, body: str) -> str:
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<title>{html.escape(title)}</title>\n'
        '</head>\n<body>\n'
        f'{body}'
        '</body>\n</html>\n'
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, help='owner/name')
    parser.add_argument('--out', required=True, type=Path, help='output directory')
    args = parser.parse_args()

    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    projects = collect(args.repo, token)
    if not projects:
        # An empty index would look like a working install source that simply
        # has no versions, which is a far more confusing failure than this.
        print('::error::no distribution files found in any release', file=sys.stderr)
        return 1

    # /simple/ -- the root listing, one link per project.
    links = '\n'.join(
        f'    <a href="{name}/">{html.escape(name)}</a><br>' for name in sorted(projects)
    )
    write(
        args.out / 'simple' / 'index.html',
        page('Simple index', f'  <h1>Simple index</h1>\n{links}\n'),
    )

    # /simple/<project>/ -- one link per file, with its hash.
    for name, files in sorted(projects.items()):
        files.sort(key=lambda f: f['name'])
        rows = []
        for f in files:
            href = f['url'] + (f'#sha256={f["digest"]}' if f['digest'] else '')
            rows.append(f'    <a href="{html.escape(href)}">{html.escape(f["name"])}</a><br>')
        write(
            args.out / 'simple' / name / 'index.html',
            page(f'Links for {name}', f'  <h1>Links for {name}</h1>\n' + '\n'.join(rows) + '\n'),
        )
        missing = sum(1 for f in files if not f['digest'])
        if missing:
            print(f'::warning::{name}: {missing} file(s) published without a sha256')

    # A landing page, so the site root is not a 404 for anyone who visits it.
    total = sum(len(v) for v in projects.values())
    summary = '\n'.join(
        f'    <li><code>{html.escape(n)}</code> &mdash; {len(v)} file(s)</li>'
        for n, v in sorted(projects.items())
    )
    write(
        args.out / 'index.html',
        page(
            'open3d-wheels',
            '  <h1>open3d-wheels</h1>\n'
            '  <p>A <a href="https://peps.python.org/pep-0503/">PEP 503</a> index of '
            'Linux arm64 wheels, linking to files stored in this repository\'s '
            '<a href="https://github.com/augustelalande/open3d-wheels/releases">releases</a>.</p>\n'
            '  <pre>pip install --extra-index-url https://augustelalande.github.io/open3d-wheels/simple/ open3d</pre>\n'
            f'  <ul>\n{summary}\n  </ul>\n',
        ),
    )

    print(f'indexed {total} file(s) across {len(projects)} project(s)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
