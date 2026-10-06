#!/usr/bin/env python3
"""Build a Pages artifact containing only the interface and licensed assets."""
import argparse
from pathlib import Path
import shutil

SOURCE = Path(__file__).resolve().parent
ASSETS = ('index.html', 'app.js', 'hosting.js', 'pdf-export.js', 'styles.css', 'scene.svg')


def build(destination):
    destination = Path(destination).resolve()
    if SOURCE.is_relative_to(destination) or destination.is_relative_to(SOURCE):
        raise ValueError('Build outside the source directory.')
    marker = destination / '.pdf-analyzer-pages'
    if destination.exists() and any(destination.iterdir()):
        if not marker.is_file():
            raise ValueError('Choose an empty folder or an existing PDF Analyzer Pages build.')
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    marker.write_text('Generated interface assets only.\n')
    for name in ASSETS:
        shutil.copyfile(SOURCE / name, destination / name)
    shutil.copytree(SOURCE / 'vendor', destination / 'vendor')
    index = destination / 'index.html'
    html = index.read_text()
    if html.count('<html lang="en">') != 1:
        raise ValueError('Pages hosting marker could not be added.')
    index.write_text(html.replace('<html lang="en">', '<html lang="en" data-hosting="pages">'))
    (destination / '.nojekyll').touch()
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=SOURCE.parent / '.pages-build')
    args = parser.parse_args()
    print('Built Pages interface:', build(args.output))
