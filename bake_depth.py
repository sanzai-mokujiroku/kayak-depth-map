#!/usr/bin/env python3
# 富山湾ぶんの水深(GEBCO 2020, opentopodata)を事前に取得してJSONに焼き込む。
# ブラウザから直接GEBCOを呼ぶとCORSで弾かれるため、Mac側で1回だけ取っておく方式。
import json, time, urllib.request, sys

# 富山湾を覆う範囲。出艇地点そのものは埋め込まない（範囲は湾全体）。
LAT_MIN, LAT_MAX = 36.68, 37.06
LNG_MIN, LNG_MAX = 137.00, 137.66
LAT_STEP = 0.005   # 約555m
LNG_STEP = 0.006   # 約535m（GEBCO実解像度450m相当に合わせた粗さ）

n_lat = int(round((LAT_MAX - LAT_MIN) / LAT_STEP)) + 1
n_lng = int(round((LNG_MAX - LNG_MIN) / LNG_STEP)) + 1
print(f"grid {n_lat} x {n_lng} = {n_lat*n_lng} points", flush=True)

# 全点を行優先で並べる（北→南 / 西→東）
pts = []
for i in range(n_lat):
    lat = LAT_MAX - i * LAT_STEP      # 上から下（北→南）
    for j in range(n_lng):
        lng = LNG_MIN + j * LNG_STEP
        pts.append((lat, lng))

depths = [None] * len(pts)  # 陸(標高>=0)や取得失敗は null
BATCH = 100
API = "https://api.opentopodata.org/v1/gebco2020?locations="

k = 0
total_calls = (len(pts) + BATCH - 1) // BATCH
call = 0
while k < len(pts):
    batch = pts[k:k+BATCH]
    locs = "|".join(f"{la:.5f},{ln:.5f}" for la, ln in batch)
    url = API + urllib.parse.quote(locs)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                data = json.load(r)
            break
        except Exception as e:
            print(f"  retry {attempt+1}: {e}", flush=True)
            time.sleep(3)
    else:
        print("FAILED batch, leaving null", flush=True)
        data = {"results": [{"elevation": None} for _ in batch]}
    for m, res in enumerate(data.get("results", [])):
        el = res.get("elevation")
        # 海のみ残す（標高が負＝海面下）。陸や欠測は null のまま。
        if el is not None and el < 0:
            depths[k+m] = round(-el, 1)   # 正の水深[m]に変換
    k += BATCH
    call += 1
    print(f"  {call}/{total_calls} calls done", flush=True)
    time.sleep(1.2)   # 公開APIへの礼儀（1req/sec制限）

sea = sum(1 for d in depths if d is not None)
out = {
    "source": "GEBCO 2020 via opentopodata.org",
    "note": "海面下のみ。陸・欠測はnull。粗い格子(約450-550m)＝おおまかな文脈用。",
    "latMax": LAT_MAX, "lngMin": LNG_MIN,
    "latStep": LAT_STEP, "lngStep": LNG_STEP,
    "nLat": n_lat, "nLng": n_lng,
    "depths": depths,
}
with open("/Users/taniiyuuto/Desktop/クロウド/kayak-depth-map/depth-toyama.json", "w") as f:
    json.dump(out, f, separators=(",", ":"))
print(f"DONE: sea points {sea}/{len(pts)} written", flush=True)
