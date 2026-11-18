(() => {
  const CACHE_NAME = "allcraft-wasm-v2";
  const OVERLAY_ID = "ac-studio-overlay";
  const ISOLATED_SLUGS = new Set(["pdfcraft", "effectcraft"]);
  let manifestPromise = null;
  const inflight = new Set();

  if ("caches" in window) {
    caches.delete("allcraft-wasm-v1").catch(() => {});
  }

  const SHORT_TO_SLUG = {
    photo: "photocraft", photocraft: "photocraft",
    vector: "vectorcraft", vectorcraft: "vectorcraft",
    film: "filmcraft", filmcraft: "filmcraft",
    light: "lightcraft", lightcraft: "lightcraft",
    pdf: "pdfcraft", pdfcraft: "pdfcraft",
    effect: "effectcraft", effectcraft: "effectcraft",
    ani: "anicraft", anicraft: "anicraft",
    design: "designcraft", designcraft: "designcraft",
    texture: "texturecraft", texturecraft: "texturecraft",
    material: "materialcraft", materialcraft: "materialcraft",
    sound: "soundcraft", soundcraft: "soundcraft",
    word: "wordcraft", wordcraft: "wordcraft",
    deck: "deckcraft", deckcraft: "deckcraft",
    cad: "cadcraft", cadcraft: "cadcraft",
    grid: "gridcraft", gridcraft: "gridcraft",
  };

  const LEGACY_SHORTS = new Set([
    "photo", "vector", "film", "light", "pdf", "effect", "ani", "design",
    "texture", "material", "sound", "word", "deck", "cad", "grid",
  ]);

  const slugToRuntime = (slug) => (slug ? `/runtime/${slug}/` : null);

  const getCurrentSlug = () => {
    const seg = location.pathname.replace(/^\/+|\/+$/g, "");
    return SHORT_TO_SLUG[seg] && !LEGACY_SHORTS.has(seg) ? SHORT_TO_SLUG[seg] : null;
  };

  const resolveSlug = (raw) => {
    if (!raw) return null;
    try {
      const cleaned = String(raw).trim();
      if (SHORT_TO_SLUG[cleaned]) return SHORT_TO_SLUG[cleaned];
      const u = new URL(cleaned, location.origin);
      if (u.origin !== location.origin) return null;
      const seg = u.pathname.replace(/^\/+|\/+$/g, "");
      if (seg.startsWith("runtime/")) {
        const sub = seg.slice("runtime/".length).split("/")[0];
        return SHORT_TO_SLUG[sub] || null;
      }
      return SHORT_TO_SLUG[seg] || null;
    } catch (_) {
      return null;
    }
  };

  const resolveMount = (href) => slugToRuntime(resolveSlug(href));

  let savedHtmlOverflow = "";
  let savedBodyOverflow = "";

  const closeInPlace = () => {
    document.documentElement.removeAttribute("data-autolaunch");
    const existing = document.getElementById(OVERLAY_ID);
    if (!existing) return;
    existing.remove();
    document.documentElement.style.overflow = savedHtmlOverflow;
    if (document.body) document.body.style.overflow = savedBodyOverflow;
  };

  const launchInPlace = (slug, pushHistory) => {
    const runtimeUrl = slugToRuntime(slug);
    if (!runtimeUrl) return;
    const cleanPath = `/${slug}/`;

    if (pushHistory) {
      history.pushState({ acStudioLaunch: slug }, "", cleanPath);
    } else {
      history.replaceState({ acStudioLaunch: slug }, "", cleanPath);
    }

    const existing = document.getElementById(OVERLAY_ID);
    if (existing) {
      const existingFrame = existing.querySelector("iframe");
      if (existingFrame && existingFrame.getAttribute("data-slug") === slug) return;
      existing.remove();
    }

    const mountOverlay = () => {
      if (document.getElementById(OVERLAY_ID)) return;
      savedHtmlOverflow = document.documentElement.style.overflow || "";
      savedBodyOverflow = (document.body && document.body.style.overflow) || "";
      document.documentElement.style.overflow = "hidden";
      document.body.style.overflow = "hidden";

      const wrap = document.createElement("div");
      wrap.id = OVERLAY_ID;
      wrap.style.cssText =
        "position:fixed;inset:0;width:100vw;height:100dvh;z-index:2147483647;background:#141519;margin:0;padding:0;border:0;overflow:hidden;";

      const frame = document.createElement("iframe");
      frame.src = runtimeUrl;
      frame.title = slug;
      frame.setAttribute("data-slug", slug);
      frame.setAttribute(
        "allow",
        "cross-origin-isolated; clipboard-read; clipboard-write; fullscreen; microphone; camera; midi; autoplay"
      );
      frame.setAttribute("allowfullscreen", "true");
      frame.style.cssText = "width:100%;height:100%;border:0;display:block;background:#141519;";
      frame.addEventListener("load", () => {
        try {
          frame.focus();
          if (frame.contentWindow) frame.contentWindow.focus();
        } catch (_) {}
      });

      wrap.appendChild(frame);
      document.body.appendChild(wrap);
      try {
        frame.focus();
      } catch (_) {}
    };

    if (document.body) {
      mountOverlay();
    } else {
      document.addEventListener("DOMContentLoaded", mountOverlay, { once: true });
    }
  };

  // Detect auto-launch arrival (/photocraft?launch=1 or #launch) immediately
  const initialSlug = getCurrentSlug();
  const wantsAutoLaunch =
    location.hash === "#launch" || new URLSearchParams(location.search).get("launch") === "1";

  if (initialSlug && wantsAutoLaunch) {
    launchInPlace(initialSlug, false);
  }

  window.addEventListener("popstate", (e) => {
    if (e.state && e.state.acStudioLaunch) {
      launchInPlace(e.state.acStudioLaunch, false);
    } else {
      closeInPlace();
    }
  });

  document.addEventListener("click", (e) => {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    const a = e.target && e.target.closest ? e.target.closest("a[href]") : null;
    if (!a || a.target === "_blank") return;

    const rawHref = a.getAttribute("href");
    if (!rawHref) return;
    let u;
    try {
      u = new URL(rawHref, location.origin);
    } catch (_) {
      return;
    }
    if (u.origin !== location.origin) return;

    const pathSeg = u.pathname.replace(/^\/+|\/+$/g, "");
    const targetSlug = a.getAttribute("data-launch-app") || SHORT_TO_SLUG[pathSeg];
    if (!targetSlug) return;

    const isLaunchLink =
      a.hasAttribute("data-launch-app") ||
      u.hash === "#launch" ||
      u.searchParams.get("launch") === "1" ||
      LEGACY_SHORTS.has(pathSeg);

    if (!isLaunchLink) return;

    e.preventDefault();
    const curSlug = getCurrentSlug();

    // PDF & Effect need COOP/COEP headers from their own /<slug> page for SharedArrayBuffer
    if (ISOLATED_SLUGS.has(targetSlug) && !window.crossOriginIsolated && curSlug !== targetSlug) {
      location.href = `/${targetSlug}?launch=1`;
      return;
    }

    launchInPlace(targetSlug, curSlug !== targetSlug);
  });

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

  let hoverTimer = null;
  document.addEventListener(
    "pointerover",
    (e) => {
      const a = e.target && e.target.closest ? e.target.closest("a[href]") : null;
      const mount = a ? resolveMount(a.getAttribute("data-launch-app") || a.getAttribute("href")) : null;
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
      const mount = a ? resolveMount(a.getAttribute("data-launch-app") || a.getAttribute("href")) : null;
      if (mount) warmApp(mount);
    },
    { passive: true }
  );

  const pageApp = resolveMount(document.documentElement.getAttribute("data-preload-app") || initialSlug);
  if (pageApp && canPrefetch() && !wantsAutoLaunch) {
    setTimeout(() => warmApp(pageApp), 300);
  }
})();
