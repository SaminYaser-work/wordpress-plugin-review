#!/usr/bin/env python3
"""Capture a non-destructive WordPress debug-log baseline and per-phase delta.

Only state/evidence JSON files are written. Log contents stay out of stdout.
Successful capture (exit 0) is not a plugin-quality or logging-health verdict.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat


def digest_prefix(handle, size):
    digest = hashlib.sha256()
    handle.seek(0)
    remaining = size
    while remaining:
        chunk = handle.read(min(remaining, 65536))
        if not chunk:
            raise ValueError('Log changed during capture; retry after requests finish')
        digest.update(chunk)
        remaining -= len(chunk)
    return digest.hexdigest()


def inspect_log(path, baseline=None, limit=1_000_000):
    try:
        info = path.stat()
    except FileNotFoundError:
        status = 'removed' if baseline and baseline['exists'] else 'missing'
        return dict(exists=False, size=0, identity=None, sha256=None,
                    status=status, boundary_preserved=status == 'missing',
                    captured_bytes=0, remaining_bytes=0, truncated=False, text='')
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('Log path must be a regular file')
    with path.open('rb') as handle:
        info = os.fstat(handle.fileno())
        identity = [info.st_dev, info.st_ino]
        size = info.st_size
        if baseline is None:
            return dict(exists=True, size=size, identity=identity,
                        sha256=digest_prefix(handle, size))
        start = 0
        preserved = True
        if not baseline['exists']:
            status = 'created'
        elif (identity != baseline['identity'] or size < baseline['size'] or
              digest_prefix(handle, baseline['size']) != baseline['sha256']):
            status = 'replaced_or_rewritten'
            preserved = False
        else:
            start = baseline['size']
            status = 'appended' if size > start else 'unchanged'
        handle.seek(start)
        data = handle.read(min(size - start, limit))
        if len(data) != min(size - start, limit):
            raise ValueError('Log changed during capture; retry after requests finish')
        remaining = size - start - len(data)
        return dict(status=status, boundary_preserved=preserved,
                    captured_bytes=len(data), remaining_bytes=remaining,
                    truncated=remaining > 0, text=data.decode('utf-8', errors='replace'))


def load_state(path, log):
    state = json.loads(path.read_text(encoding='utf-8'))
    if (not isinstance(state, dict) or state.get('version') != 1 or
            state.get('path') != str(log) or
            type(state.get('exists')) is not bool or
            type(state.get('size')) is not int or state['size'] < 0):
        raise ValueError('Invalid baseline or baseline belongs to another log')
    if state['exists']:
        identity = state.get('identity')
        digest = state.get('sha256')
        if (not isinstance(identity, list) or len(identity) != 2 or
                any(type(value) is not int for value in identity) or
                not isinstance(digest, str) or len(digest) != 64 or
                any(value not in '0123456789abcdef' for value in digest)):
            raise ValueError('Invalid baseline file identity or digest')
    elif state['size'] != 0:
        raise ValueError('Invalid baseline size for missing log')
    return state


def write_json(path, data):
    # Evidence can contain credentials or customer data; keep artifacts private.
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w',
                   encoding='utf-8') as handle:
        os.fchmod(handle.fileno(), 0o600)
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('baseline', 'delta'))
    parser.add_argument('log', type=Path)
    parser.add_argument('--state', required=True, type=Path)
    parser.add_argument('--out', type=Path, help='Required evidence JSON output for delta')
    parser.add_argument('--max-bytes', type=int, default=1_000_000,
                        help='Maximum bytes captured by delta (default: 1000000)')
    args = parser.parse_args()
    if args.action == 'delta' and args.out is None:
        parser.error('delta requires --out')
    if args.max_bytes < 1:
        parser.error('--max-bytes must be positive')
    try:
        log = args.log.resolve()
        artifacts = [args.state.resolve()]
        if args.out is not None:
            artifacts.append(args.out.resolve())
        paths = [log] + artifacts
        for index, left in enumerate(paths):
            for right in paths[index + 1:]:
                if left == right or (left.exists() and right.exists() and left.samefile(right)):
                    raise ValueError('Log, state and output paths must be distinct')
        timestamp = datetime.now(timezone.utc).isoformat()
        if args.action == 'baseline':
            state = dict(version=1, path=str(log), captured_at=timestamp,
                         **inspect_log(log))
            write_json(args.state, state)
            print(f'Baseline saved; exists={state["exists"]}; bytes={state["size"]}')
        else:
            state = load_state(args.state, log)
            report = dict(version=1, path=str(log), captured_at=timestamp,
                          baseline_at=state.get('captured_at'),
                          **inspect_log(log, state, args.max_bytes))
            write_json(args.out, report)
            print(f'Delta saved; status={report["status"]}; '
                  f'bytes={report["captured_bytes"]}; truncated={report["truncated"]}')
    except (OSError, ValueError) as error:
        parser.exit(2, f'Capture failed: {error}\n')


if __name__ == '__main__':
    main()
