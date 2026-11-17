(() => {
  const CACHE_NAME = "allcraft-wasm-v2";
  let manifestPromise = null;
  const inflight = new Set();

  if ("caches" in window) {
    caches.delete("allcraft-wasm-v1").catch(() => {});
  }

  const SLUG_TO_MOUNT = {
    photo: "/photo/", photocraft: "/photo/",
    vector: "/vector/", vectorcraft: "/vector/",
    film: "/film/", filmcraft: "/film/",
    light: "/light/", lightcraft: "/light/",
    pdf: "/pdf/", pdfcraft: "/pdf/",
    effect: "/effect/", effectcraft: "/effect/",
    ani: "/ani/", anicraft: "/ani/",
    design: "/design/", designcraft: "/design/",
    texture: "/texture/", texturecraft: "/texture/",
    material: "/material/", materialcraft: "/material/",
    sound: "/sound/", soundcraft: "/sound/",
    word: "/word/", wordcraft: "/word/",
    deck: "/deck/", deckcraft: "/deck/",
    cad: "/cad/", cadcraft: "/cad/",
    grid: "/grid/", gridcraft: "/grid/",
  };

  const canPrefetch = () => {
    const conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    if (conn) {
      if (conn.saveData) return false;
      const et = String(conn.effectiveType || "").toLowerCase();
      if (et === "slow-2g" || et === "2g") return false;
    }
    return true;
  };

  const getManifest = () => {
    if (!manifestPromise) {
      manifestPromise = fetch("/prefetch-manifest.json", { priority: "low" })
        .then((r) => (r.ok ? r.json() : {}))
        .catch(() => ({}));
    }
    return manifestPromise;
  };

  const fetchWindowedBuffers = async (urls, concurrency = 3) => {
    const out = new Array(urls.length);
    let cursor = 0;
    const worker = async () => {
      while (cursor < urls.length) {
        const idx = cursor++;
        const r = await fetch(urls[idx], { priority: "low", cache: "force-cache" });
        if (!r.ok) throw new Error("part fetch failed");
        out[idx] = new Uint8Array(await r.arrayBuffer());
      }
    };
    await Promise.all(Array.from({ length: Math.min(concurrency, urls.length) }, worker));
    return out;
  };

  const warmApp = async (mount) => {
    if (!mount || inflight.has(mount) || !canPrefetch()) return;
    inflight.add(mount);

    try {
      const manifest = await getManifest();
      const entry = manifest[mount];
      if (!entry) return;

      fetch(mount, { priority: "low" }).catch(() => {});
      for (const jsUrl of entry.js || []) {
        fetch(jsUrl, { priority: "low" }).catch(() => {});
      }

      if (entry.cache_key && "caches" in window && typeof DecompressionStream !== "undefined") {
        const cache = await caches.open(CACHE_NAME);
        if (await cache.match(entry.cache_key)) return;

        const parts = entry.parts || [];
        if (parts.length > 0) {
          const buffers = await fetchWindowedBuffers(parts, 3);
          const stream = new ReadableStream({
            start(ctrl) {
              for (const b of buffers) ctrl.enqueue(b);
              ctrl.close();
            },
          });
          const decompResp = new Response(stream.pipeThrough(new DecompressionStream("gzip")));
          const wasmBlob = await decompResp.blob();
          await cache.put(
            entry.cache_key,
            new Response(wasmBlob, {
              status: 200,
              headers: {
                "Content-Type": "application/wasm",
                "Cross-Origin-Resource-Policy": "same-origin",
              },
            })
          );
          return;
        }
      }

      for (const pUrl of (entry.parts || []).slice(0, 3)) {
        fetch(pUrl, { priority: "low", cache: "force-cache" }).catch(() => {});
      }
    } catch (_) {
      inflight.delete(mount);
    }
  };

  const resolveMount = (href) => {
    if (!href) return null;
    try {
      const u = new URL(href, location.origin);
      if (u.origin !== location.origin) return null;
      const seg = u.pathname.replace(/^\/+|\/+$/g, "");
      return SLUG_TO_MOUNT[seg] || null;
    } catch (_) {
      return null;
    }
  };

  let hoverTimer = null;
  document.addEventListener(
    "pointerover",
    (e) => {
      const a = e.target && e.target.closest ? e.target.closest("a[href]") : null;
      const mount = a ? resolveMount(a.getAttribute("href")) : null;
      if (!mount) return;
      clearTimeout(hoverTimer);
      hoverTimer = setTimeout(() => warmApp(mount), 90);
    },
    { passive: true }
  );

  document.addEventListener(
    "touchstart",
    (e) => {
      const a = e.target && e.target.closest ? e.target.closest("a[href]") : null;
      const mount = a ? resolveMount(a.getAttribute("href")) : null;
      if (mount) warmApp(mount);
    },
    { passive: true }
  );

  const pageApp = document.documentElement.getAttribute("data-preload-app");
  if (pageApp && canPrefetch()) {
    setTimeout(() => warmApp(pageApp), 300);
  }
})();
