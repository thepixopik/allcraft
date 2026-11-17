(() => {
  const CACHE_NAME = "allcraft-wasm-v1";
  let manifestPromise = null;
  const inflight = new Set();

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

  const warmApp = async (mount) => {
    if (!mount || inflight.has(mount) || !canPrefetch()) return;
    inflight.add(mount);

    try {
      const manifest = await getManifest();
      const entry = manifest[mount];
      if (!entry) return;

      // Warm entry HTML & small JS glue in browser cache
      fetch(mount, { priority: "low" }).catch(() => {});
      for (const jsUrl of entry.js || []) {
        fetch(jsUrl, { priority: "low" }).catch(() => {});
      }

      // If decompressed Wasm is already in CacheStorage, zero Wasm download needed!
      if (entry.cache_key && "caches" in window && typeof DecompressionStream !== "undefined") {
        const cache = await caches.open(CACHE_NAME);
        const existing = await cache.match(entry.cache_key);
        if (existing) return;

        const parts = entry.parts || [];
        if (parts.length > 0) {
          const buffers = await Promise.all(
            parts.map(async (u) => {
              const r = await fetch(u, { priority: "low", cache: "force-cache" });
              if (!r.ok) throw new Error("part fetch failed");
              return new Uint8Array(await r.arrayBuffer());
            })
          );
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

      // Fallback: warm raw files in HTTP cache
      for (const pUrl of entry.parts || []) {
        fetch(pUrl, { priority: "low", cache: "force-cache" }).catch(() => {});
      }
    } catch (_) {
      inflight.delete(mount);
    }
  };

  const normalizeMount = (href) => {
    if (!href) return null;
    try {
      const u = new URL(href, location.origin);
      if (u.origin !== location.origin) return null;
      const m = u.pathname.match(/^\/(photo|vector|film|light|pdf|effect|ani|design|texture|material|sound|word|deck|cad|grid)\/?$/);
      return m ? `/${m[1]}/` : null;
    } catch (_) {
      return null;
    }
  };

  // Hover & touchstart listener for any direct Launch link (/photo/, /vector/, etc.)
  let hoverTimer = null;
  document.addEventListener(
    "pointerover",
    (e) => {
      const a = e.target && e.target.closest ? e.target.closest("a[href]") : null;
      const mount = a ? normalizeMount(a.getAttribute("href")) : null;
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
      const mount = a ? normalizeMount(a.getAttribute("href")) : null;
      if (mount) warmApp(mount);
    },
    { passive: true }
  );

  // On a dedicated Detail Page (/photocraft/, etc.), gently pre-warm that single app during idle time on fast 4G/Wi-Fi
  const pageApp = document.documentElement.getAttribute("data-preload-app");
  if (pageApp) {
    const conn = navigator.connection || {};
    const fastEnough = !conn.effectiveType || conn.effectiveType === "4g";
    if (fastEnough && canPrefetch()) {
      const schedule = window.requestIdleCallback || ((fn) => setTimeout(fn, 1200));
      schedule(() => setTimeout(() => warmApp(pageApp), 900));
    }
  }
})();
