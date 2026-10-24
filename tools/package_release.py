"""Create an offline ZIP from tracked working files, including hydrated LFS images."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise SystemExit('Output already exists; choose a new filename')
    entries = subprocess.check_output(['git', '-c', f'safe.directory={ROOT.as_posix()}', 'ls-files', '-z'], cwd=ROOT)
    paths = [ROOT / name.decode('utf-8') for name in entries.split(b'\0') if name]
    for path in paths:
        if not path.is_file() or not path.resolve().is_relative_to(ROOT):
            raise SystemExit(f'Missing or unsafe tracked path: {path.name}')
        with path.open('rb') as stream:
            if stream.read(80).startswith(b'version https://git-lfs.github.com/spec/v1'):
                raise SystemExit('Run git lfs pull before packaging')
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x', allowZip64=True) as archive:
        for path in paths:
            compressed = path.suffix.lower() not in {'.png', '.webp', '.jpg', '.jpeg', '.wav', '.mp3'}
            archive.write(path, 'GOT/' + path.relative_to(ROOT).as_posix(), compress_type=zipfile.ZIP_DEFLATED if compressed else zipfile.ZIP_STORED)
    with output.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    output.with_suffix(output.suffix + '.sha256').write_text(f'{digest}  {output.name}\n', encoding='utf-8')
    print(f'Packaged {len(paths)} files: {output} ({output.stat().st_size:,} bytes)')
    print(f'SHA256 {digest}')


if __name__ == '__main__':
    main()
