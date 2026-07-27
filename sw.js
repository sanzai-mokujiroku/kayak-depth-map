// 富山湾 航空写真×水深マップ サービスワーカー。
// アプリの外枠＋水深データ＋Leafletをキャッシュし、電波の弱い海上でも起動できるようにする。
// さらに一度見た航空写真タイル（国土地理院）もキャッシュ＝見た海域は圏外でも表示できる。
// アプリを更新したら CACHE の番号を上げること（古いキャッシュを破棄するため）。
const CACHE = "depth-map-v2";       // アプリ本体（v2: 根メモ機能を追加）
const TILECACHE = "depth-tiles-v1"; // 航空写真タイル（見たぶんだけ貯まる）
const TILE_LIMIT = 1200;            // タイルの貯め過ぎ防止（古いものから捨てる）

const ASSETS = [
  "./", "./index.html", "./manifest.webmanifest", "./depth-toyama.json",
  "./vendor/leaflet/leaflet.js", "./vendor/leaflet/leaflet.css",
  "./vendor/leaflet/images/marker-icon.png",
  "./vendor/leaflet/images/marker-icon-2x.png",
  "./vendor/leaflet/images/marker-shadow.png",
  "./vendor/leaflet/images/layers.png",
  "./vendor/leaflet/images/layers-2x.png",
  "./icon-192.png", "./icon-512.png", "./icon-180.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE && k !== TILECACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  const url = new URL(e.request.url);

  // 航空写真タイル（国土地理院）＝キャッシュ優先、無ければ取得して貯める（海上のオフライン用）
  if (url.hostname === "cyberjapandata.gsi.go.jp") {
    e.respondWith(
      caches.open(TILECACHE).then((c) =>
        c.match(e.request).then((hit) =>
          hit || fetch(e.request).then((res) => {
            if (res && res.status === 200) { c.put(e.request, res.clone()); trimTiles(c); }
            return res;
          }).catch(() => hit)
        )
      )
    );
    return;
  }

  // 他オリジンは素通し
  if (url.origin !== location.origin) return;

  const isShell = e.request.mode === "navigate"
    || url.pathname.endsWith("/")
    || url.pathname.endsWith("/index.html");

  if (isShell) {
    // ネットワーク優先（オンラインなら最新、圏外はキャッシュへ）
    e.respondWith(
      fetch(e.request)
        .then((res) => {
          if (res && res.status === 200 && res.type === "basic") {
            const cp = res.clone(); caches.open(CACHE).then((c) => c.put(e.request, cp));
          }
          return res;
        })
        .catch(() => caches.match(e.request).then((c) => c || caches.match("./index.html")))
    );
    return;
  }
  // 同一オリジンの静的ファイル（Leaflet・水深JSON・アイコン等）はキャッシュ優先
  e.respondWith(caches.match(e.request).then((cached) => cached || fetch(e.request)));
});

// タイルキャッシュが増えすぎたら古いものから間引く
function trimTiles(cache) {
  cache.keys().then((keys) => {
    if (keys.length > TILE_LIMIT) {
      for (let i = 0; i < keys.length - TILE_LIMIT; i++) cache.delete(keys[i]);
    }
  });
}
