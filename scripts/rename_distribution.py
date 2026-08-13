"""Rename the distribution a wheel declares, without rebuilding it.

Upstream renames CPU-only builds to `open3d-cpu` only on Linux x86_64, because
that is the one platform where the default `open3d` is CUDA-enabled. Our arm64
and Windows builds are equally CPU-only but keep the plain name, which would
make the dependency platform-dependent for no real reason.

The distribution name lives entirely in metadata -- the compiled extension
modules are untouched -- so this rewrites:

  * the wheel filename
  * the `<name>-<version>.dist-info/` directory
  * the `Name:` field in METADATA
  * RECORD, whose paths change and whose METADATA hash no longer matches

The importable package is unaffected: it is `open3d/` either way, so
`import open3d` keeps working.

RECORD is regenerated from the actual bytes rather than patched. As a check
that the hashing matches what the build system produced, every entry that is
not being modified must come out identical to the original RECORD.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import re
import sys
import zipfile
from pathlib import Path


def escape(name: str) -> str:
    """The escaped form used in wheel filenames and dist-info dirs (PEP 427)."""
    return re.sub(r'[^\w\d.]+', '_', name, flags=re.UNICODE)


def record_hash(data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    return 'sha256=' + base64.urlsafe_b64encode(digest).rstrip(b'=').decode('ascii')


def rename(src: Path, new_name: str, out_dir: Path) -> Path:
    with zipfile.ZipFile(src) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]

        dist_infos = {n.split('/')[0] for n in names if n.split('/')[0].endswith('.dist-info')}
        if len(dist_infos) != 1:
            raise SystemExit(f'{src.name}: expected exactly one .dist-info, found {dist_infos}')
        old_di = dist_infos.pop()
        version = old_di[: -len('.dist-info')].rsplit('-', 1)[1]
        new_di = f'{escape(new_name)}-{version}.dist-info'

        old_record = {}
        record_path = f'{old_di}/RECORD'
        if record_path in names:
            text = z.read(record_path).decode('utf-8')
            for row in csv.reader(io.StringIO(text)):
                if row:
                    old_record[row[0]] = (row[1] if len(row) > 1 else '')

        # New filename: swap the leading distribution component.
        out_name = escape(new_name) + src.name[src.name.index('-') :]
        out_path = out_dir / out_name
        out_dir.mkdir(parents=True, exist_ok=True)

        entries: list[tuple[zipfile.ZipInfo, str, bytes]] = []
        for info in infos:
            if info.is_dir():
                continue
            path = info.filename
            data = z.read(path)
            new_path = new_di + path[len(old_di) :] if path.startswith(old_di + '/') else path

            if new_path == f'{new_di}/METADATA':
                before = data
                data = re.sub(
                    rb'(?m)^Name: .*$', f'Name: {new_name}'.encode(), data, count=1
                )
                if data == before:
                    raise SystemExit(f'{src.name}: no Name: field found in METADATA')
            entries.append((info, new_path, data))

        # Verify our hashing agrees with the build system's for untouched files.
        mismatched = []
        for info, new_path, data in entries:
            original = old_record.get(info.filename)
            if original and not info.filename.endswith(('/METADATA', '/RECORD')):
                if record_hash(data) != original:
                    mismatched.append(info.filename)
        if mismatched:
            raise SystemExit(
                f'{src.name}: recomputed hashes differ from RECORD for '
                f'{len(mismatched)} file(s), e.g. {mismatched[:3]}'
            )

        record_lines = []
        for _, new_path, data in entries:
            if new_path == f'{new_di}/RECORD':
                continue
            record_lines.append(f'{new_path},{record_hash(data)},{len(data)}')
        record_lines.append(f'{new_di}/RECORD,,')
        record_data = ('\n'.join(record_lines) + '\n').encode('utf-8')

        with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as out:
            for info, new_path, data in entries:
                if new_path == f'{new_di}/RECORD':
                    data = record_data
                new_info = zipfile.ZipInfo(new_path, date_time=info.date_time)
                new_info.compress_type = info.compress_type
                new_info.external_attr = info.external_attr
                out.writestr(new_info, data)
            if f'{new_di}/RECORD' not in [p for _, p, _ in entries]:
                out.writestr(f'{new_di}/RECORD', record_data)

    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True, help='new distribution name, e.g. open3d-cpu')
    parser.add_argument('--out', required=True, type=Path, help='output directory')
    parser.add_argument('wheels', nargs='+', type=Path)
    args = parser.parse_args()

    for src in args.wheels:
        if not src.name.endswith('.whl'):
            raise SystemExit(f'not a wheel: {src}')
        if src.name.split('-')[0] == escape(args.name):
            print(f'{src.name}: already named {args.name}, copying unchanged')
            args.out.mkdir(parents=True, exist_ok=True)
            (args.out / src.name).write_bytes(src.read_bytes())
            continue
        out = rename(src, args.name, args.out)
        print(f'{src.name}\n  -> {out.name}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
