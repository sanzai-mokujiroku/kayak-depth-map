#!/usr/bin/env python3
"""航空写真×水深マップのアイコンを生成（外部ライブラリ不要）。
深い海色の背景に、等深線（同心の帯）＋岸のかけ上がり＋ピンクのマーカー点を描く。"""
import zlib, struct, math

def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def make_pixels(S):
    deep   = (0x0d, 0x1b, 0x33)   # 深場（濃紺）
    shallow= (0x24, 0x50, 0x6e)   # 浅場（明るい海色）
    line_k = (0x63, 0xd6, 0xd0)   # 等深線（カヤック帯の色）
    line_d = (0xcd, 0xd9, 0xf5)   # 深い等深線（淡い）
    pink   = (0xff, 0x5a, 0xa0)   # マーカー
    # 岸（右下）を中心に、そこからの距離で深さが増す設定＝富山湾の急深イメージ
    ox, oy = S * 1.02, S * 1.02
    maxr = math.hypot(S, S) * 0.62
    px = bytearray()
    for y in range(S):
        row = bytearray([0])  # filter type 0
        for x in range(S):
            r = math.hypot(x - ox, y - oy) / maxr  # 0(岸)→1(沖)
            col = lerp(shallow, deep, r)
            # 等深線＝距離の周期的な帯
            phase = (r * 7.0) % 1.0
            band = abs(phase - 0.0)
            if phase < 0.06 or phase > 0.94:
                # 岸寄り(浅い環)はカヤック帯色を濃く、沖は淡く
                lc = lerp(line_k, line_d, r)
                col = lerp(col, lc, 0.85 if r < 0.5 else 0.5)
            row += bytes((col[0], col[1], col[2], 255))
        px += row
    # ピンクのマーカー点（岸寄りの浅場に置く）
    mx, my = S * 0.34, S * 0.40
    rad = S * 0.075
    out = bytearray(px)
    stride = S * 4 + 1
    for y in range(S):
        for x in range(S):
            d = math.hypot(x - mx, y - my)
            if d < rad:
                idx = y * stride + 1 + x * 4
                a = 1.0 if d < rad * 0.72 else (rad - d) / (rad * 0.28)
                base = (out[idx], out[idx+1], out[idx+2])
                c = lerp(base, pink, a)
                out[idx] = c[0]; out[idx+1] = c[1]; out[idx+2] = c[2]
            # 白フチ
            elif rad <= d < rad * 1.12:
                idx = y * stride + 1 + x * 4
                base = (out[idx], out[idx+1], out[idx+2])
                c = lerp(base, (255,255,255), 0.7)
                out[idx] = c[0]; out[idx+1] = c[1]; out[idx+2] = c[2]
    return bytes(out)

def write_png(path, S, raw):
    def chunk(typ, data):
        return struct.pack(">I", len(data)) + typ + data + struct.pack(">I", zlib.crc32(typ + data) & 0xffffffff)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", S, S, 8, 6, 0, 0, 0)  # RGBA
    idat = zlib.compress(raw, 9)
    with open(path, "wb") as f:
        f.write(sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b""))

if __name__ == "__main__":
    for S, name in [(512, "icon-512.png"), (192, "icon-192.png"), (180, "icon-180.png")]:
        write_png(name, S, make_pixels(S))
        print(name, "done")
