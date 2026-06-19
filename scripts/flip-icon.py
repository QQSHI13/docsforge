#!/usr/bin/env python3
"""Horizontally flip an SVG icon so it resembles a 'D' shape.
Reads an SVG, wraps paths in <g transform="translate(W,0) scale(-1,1)">,
writes the flipped SVG in-place.
"""

import re, sys

def flip_svg(svg: str) -> str:
    m = re.search(r'viewBox="0\s+0\s+(\d+)\s+\d+"', svg)
    if not m:
        raise ValueError("viewBox width not found (expects viewBox='0 0 W H')")
    w = int(m.group(1))

    start = svg.index('>') + 1
    end = svg.rindex('<')
    if svg[end:].strip() == '':
        end = len(svg)

    prefix = svg[:start]
    inner = svg[start:end].strip()
    suffix = svg[end:]

    flip = f'\n  <g transform="translate({w},0) scale(-1,1)">\n    {inner}\n  </g>\n'
    return prefix + flip + suffix

def main():
    for path in sys.argv[1:]:
        with open(path) as f:
            original = f.read()
        flipped = flip_svg(original)
        with open(path, 'w') as f:
            f.write(flipped)
        print(f"Flipped: {path}")

if __name__ == '__main__':
    main()
