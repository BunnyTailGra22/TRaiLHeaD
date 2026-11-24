"""Stamp 240 DPI (pHYs) into PNG files: python3 png_dpi.py a.png [b.png ...]"""
import sys, struct, zlib
for f in sys.argv[1:]:
    b = open(f, "rb").read(); ppm = round(240 / 0.0254); data = struct.pack(">IIB", ppm, ppm, 1)
    chunk = struct.pack(">I", 9) + b"pHYs" + data + struct.pack(">I", zlib.crc32(b"pHYs" + data) & 0xffffffff)
    out = bytearray(b[:8]); i = 8
    while i < len(b):
        n = struct.unpack(">I", b[i:i+4])[0]; t = b[i+4:i+8]
        if t != b"pHYs": out += b[i:i+12+n]
        if t == b"IHDR": out += chunk
        i += 12 + n
    open(f, "wb").write(out); print(f.rsplit("/",1)[1], *struct.unpack(">II", b[16:24]), len(out))
