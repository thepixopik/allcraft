(() => {
  const CACHE_NAME = "allcraft-wasm-v2";
  const OVERLAY_ID = "ac-studio-overlay";
  const STYLE_ID = "ac-pre-splash-style";
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

  const APP_THEMES = {
    photocraft:    { code: "Ph", title: "The AllCraft Photo",    tagline: "Non-Destructive Imaging, RAW & Layer Compositing",    accent: "#31A8FF", soft: "rgba(49, 168, 255, 0.24)",  bg: "#081E36", stage: "Initializing WebGPU & 32-Bit Color Engine…" },
    vectorcraft:   { code: "Vc", title: "The AllCraft Vector",   tagline: "Precision Vector Illustration & Typography Studio",   accent: "#E8573F", soft: "rgba(232, 87, 63, 0.22)",   bg: "#2B1410", stage: "Initializing WebGPU Vector Engine…" },
    filmcraft:     { code: "Fm", title: "The AllCraft Film",     tagline: "Multi-Track Non-Linear Video, Color & Audio Suite",   accent: "#A855F7", soft: "rgba(168, 85, 247, 0.24)",  bg: "#211036", stage: "Initializing Hardware WebCodecs & GPU Scopes…" },
    lightcraft:    { code: "Lc", title: "The AllCraft Light",    tagline: "RAW Photo Catalog, Culling & Color Darkroom",         accent: "#22D3EE", soft: "rgba(34, 211, 238, 0.24)",  bg: "#06232B", stage: "Initializing Linear RAW & HDR Color Pipeline…" },
    pdfcraft:      { code: "Pd", title: "The AllCraft PDF",      tagline: "Document Editing, On-Device OCR, Forms & Signing",    accent: "#10B981", soft: "rgba(16, 185, 129, 0.24)",  bg: "#08291E", stage: "Initializing Vector Page Renderer & Font Engine…" },
    effectcraft:   { code: "Ef", title: "The AllCraft Effect",   tagline: "Motion Graphics, 3D VFX Compositing & Roto Studio",   accent: "#F472B6", soft: "rgba(244, 114, 182, 0.24)", bg: "#2D0C20", stage: "Initializing 32-Bit Float GPU Compositor…" },
    anicraft:      { code: "An", title: "The AllCraft Ani",      tagline: "2D Vector Animation, Tweens, Bones & Onion Skin",     accent: "#C084FC", soft: "rgba(192, 132, 252, 0.24)", bg: "#210E36", stage: "Initializing 2D Vector Stage & Brush Engine…" },
    designcraft:   { code: "Ds", title: "The AllCraft Design",   tagline: "Desktop Publishing, Master Layouts & Prepress Studio", accent: "#F59E0B", soft: "rgba(245, 158, 11, 0.24)",  bg: "#2E1C06", stage: "Initializing Multi-Page Layout & Grid Engine…" },
    texturecraft:  { code: "Tx", title: "The AllCraft Texture",  tagline: "3D PBR Viewport Painting, Smart Masks & Mesh Bakers", accent: "#FB7185", soft: "rgba(251, 113, 133, 0.24)", bg: "#2E0B14", stage: "Initializing WebGPU 3D PBR & UV Viewport…" },
    materialcraft: { code: "Mt", title: "The AllCraft Material", tagline: "Node-Based Procedural PBR Materials & 3D Preview",    accent: "#E879F9", soft: "rgba(232, 121, 249, 0.24)", bg: "#2B0B30", stage: "Initializing Procedural Graph & Tile Engine…" },
    soundcraft:    { code: "Sd", title: "The AllCraft Sound",    tagline: "Multi-Track Audio DAW, MIDI, Score & Mastering",      accent: "#2DD4BF", soft: "rgba(45, 212, 191, 0.24)",  bg: "#062825", stage: "Initializing Low-Latency WebAudio & DSP Engine…" },
    wordcraft:     { code: "Wd", title: "The AllCraft Word",     tagline: "Print-Layout Word Processor, Equations & Citations",  accent: "#818CF8", soft: "rgba(129, 140, 248, 0.24)", bg: "#15173B", stage: "Initializing Print-Layout Page & Font Shaper…" },
    deckcraft:     { code: "Dk", title: "The AllCraft Deck",     tagline: "Presentations, Slide Masters, Animations & Live Show", accent: "#FB923C", soft: "rgba(251, 146, 60, 0.24)",  bg: "#2E1305", stage: "Initializing GPU Slide & Transition Renderer…" },
    cadcraft:      { code: "Cd", title: "The AllCraft CAD",      tagline: "2D/3D Technical Drafting, DWG/DXF & Parametric CAD",  accent: "#F87171", soft: "rgba(248, 113, 113, 0.24)", bg: "#2D0C0C", stage: "Initializing Precision 2D/3D CAD Viewport…" },
    gridcraft:     { code: "Gd", title: "The AllCraft Grid",     tagline: "Spreadsheets, 400+ Formulas, PivotTables & Analytics", accent: "#4ADE80", soft: "rgba(74, 222, 128, 0.24)",  bg: "#082914", stage: "Initializing Vectorized Calculation Engine…" },
  };

  const LEGACY_SHORTS = new Set([
    "photo", "vector", "film", "light", "pdf", "effect", "ani", "design",
    "texture", "material", "sound", "word", "deck", "cad", "grid",
  ]);

  const slugToManifestKey = (slug) => (slug ? `/runtime/${slug}/` : null);
  const slugToRuntimeUrl = (slug) => (slug ? `/runtime/${slug}` : null);

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

  const resolveMount = (href) => slugToManifestKey(resolveSlug(href));

  const ensurePreSplashStyles = () => {
    if (document.getElementById(STYLE_ID)) return;
    const st = document.createElement("style");
    st.id = STYLE_ID;
    st.textContent = `
      #${OVERLAY_ID} {
        position: fixed; inset: 0; width: 100vw; height: 100dvh; z-index: 2147483647;
        background: radial-gradient(circle at 50% 35%, #23252b 0%, #141519 100%);
        margin: 0; padding: 0; border: 0; overflow: hidden;
      }
      #${OVERLAY_ID}.ac-animate-in {
        animation: acOverlayFadeIn 0.18s cubic-bezier(0.16, 1, 0.3, 1) forwards;
      }
      @keyframes acOverlayFadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
      }
      .ac-pre-stage {
        position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
        padding: 20px; pointer-events: none; user-select: none; z-index: 1;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        transition: opacity 0.22s ease;
      }
      .ac-pre-card {
        position: relative; width: min(650px, 100%); min-height: 360px;
        display: grid; grid-template-columns: 1.28fr 0.92fr;
        background: #1c1d22; border-radius: 18px; overflow: hidden;
        border: 1px solid rgba(255,255,255,0.10);
        box-shadow: 0 32px 90px rgba(0,0,0,0.72), 0 0 0 1px rgba(0,0,0,0.5);
        animation: acCardPopIn 0.22s cubic-bezier(0.16, 1, 0.3, 1);
      }
      @keyframes acCardPopIn {
        from { opacity: 0.4; transform: scale(0.975) translateY(6px); }
        to { opacity: 1; transform: scale(1) translateY(0); }
      }
      .ac-pre-left {
        padding: 32px 30px 28px; display: flex; flex-direction: column; justify-content: space-between; text-align: left;
      }
      .ac-pre-brand { display: flex; align-items: center; gap: 14px; margin-bottom: 18px; }
      .ac-pre-mono {
        width: 54px; height: 54px; border-radius: 13px;
        display: flex; align-items: center; justify-content: center;
        font-size: 24px; font-weight: 800; letter-spacing: -0.03em;
      }
      .ac-pre-suite { font-size: 10.5px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #8b92a5; margin-bottom: 3px; }
      .ac-pre-title { margin: 0; font-size: 23px; font-weight: 800; letter-spacing: -0.02em; color: #f8fafc; line-height: 1.15; }
      .ac-pre-tag { margin: 0 0 18px; font-size: 13.5px; line-height: 1.5; color: #9ca3af; }
      .ac-pre-pills { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 24px; }
      .ac-pre-pill {
        font-size: 11px; font-weight: 600; padding: 4px 9px; border-radius: 6px;
        background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.07); color: #cbd5e1;
      }
      .ac-pre-row { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; margin-bottom: 9px; }
      .ac-pre-stxt { font-size: 12.5px; font-weight: 500; color: #d1d5db; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .ac-pre-pct { font-size: 12px; font-weight: 700; font-variant-numeric: tabular-nums; flex-shrink: 0; }
      .ac-pre-track { position: relative; width: 100%; height: 4px; background: rgba(255,255,255,0.08); border-radius: 999px; overflow: hidden; }
      .ac-pre-shimmer {
        position: absolute; top: 0; bottom: 0; left: -35%; width: 38%; border-radius: 999px;
        animation: acBarSlide 1.05s cubic-bezier(0.4, 0, 0.2, 1) infinite;
      }
      @keyframes acBarSlide {
        0% { left: -35%; width: 28%; }
        50% { width: 46%; }
        100% { left: 102%; width: 28%; }
      }
      .ac-pre-foot { margin-top: 14px; font-size: 10.5px; color: #64748b; letter-spacing: 0.02em; }
      .ac-pre-right {
        position: relative; background: #121318; border-left: 1px solid rgba(255,255,255,0.06);
        display: flex; align-items: center; justify-content: center; overflow: hidden;
      }
      .ac-pre-orb {
        width: 148px; height: 148px; border-radius: 50%; filter: blur(36px); opacity: 0.42;
        animation: acOrbPulse 1.8s ease-in-out infinite alternate;
      }
      @keyframes acOrbPulse {
        from { transform: scale(0.88); opacity: 0.34; }
        to { transform: scale(1.08); opacity: 0.52; }
      }
      @media (max-width: 600px) {
        .ac-pre-card { grid-template-columns: 1fr; min-height: auto; }
        .ac-pre-right { display: none; }
      }
    `;
    document.head.appendChild(st);
  };

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

  const launchInPlace = (slug, pushHistory, animateEntry = true) => {
    const runtimeUrl = slugToRuntimeUrl(slug);
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
      ensurePreSplashStyles();
      savedHtmlOverflow = document.documentElement.style.overflow || "";
      savedBodyOverflow = (document.body && document.body.style.overflow) || "";
      document.documentElement.style.overflow = "hidden";
      document.body.style.overflow = "hidden";

      const t = APP_THEMES[slug] || APP_THEMES.photocraft;
      const wrap = document.createElement("div");
      wrap.id = OVERLAY_ID;
      if (animateEntry) wrap.className = "ac-animate-in";

      const preStage = document.createElement("div");
      preStage.className = "ac-pre-stage";
      preStage.innerHTML = `
        <div class="ac-pre-card">
          <div class="ac-pre-left">
            <div>
              <div class="ac-pre-brand">
                <div class="ac-pre-mono" style="background:${t.bg};border:2px solid ${t.accent};color:${t.accent};box-shadow:0 8px 24px ${t.soft}">${t.code}</div>
                <div>
                  <div class="ac-pre-suite">The AllCraft Studio &bull; 2026</div>
                  <h1 class="ac-pre-title">${t.title}</h1>
                </div>
              </div>
              <p class="ac-pre-tag">${t.tagline}</p>
              <div class="ac-pre-pills">
                <span class="ac-pre-pill">HTTP/3 Parallel Stream</span>
                <span class="ac-pre-pill">Instant Local Cache</span>
                <span class="ac-pre-pill">Rust + Wasm</span>
              </div>
            </div>
            <div>
              <div class="ac-pre-row">
                <span class="ac-pre-stxt">${t.stage}</span>
                <span class="ac-pre-pct" style="color:${t.accent}">Starting…</span>
              </div>
              <div class="ac-pre-track">
                <div class="ac-pre-shimmer" style="background:${t.accent};box-shadow:0 0 12px ${t.accent}"></div>
              </div>
              <div class="ac-pre-foot">&copy; 2026 The AllCraft Studio &middot; Zero Cloud Uploads</div>
            </div>
          </div>
          <div class="ac-pre-right">
            <div class="ac-pre-orb" style="background:${t.accent}"></div>
          </div>
        </div>
      `;

      const frame = document.createElement("iframe");
      frame.src = runtimeUrl;
      frame.title = slug;
      frame.setAttribute("data-slug", slug);
      frame.setAttribute(
        "allow",
        "cross-origin-isolated; clipboard-read; clipboard-write; fullscreen; microphone; camera; midi; autoplay"
      );
      frame.setAttribute("allowfullscreen", "true");
      frame.style.cssText =
        "position:absolute;inset:0;width:100%;height:100%;border:0;display:block;background:transparent;z-index:2;opacity:0;pointer-events:none;transition:opacity 0.22s cubic-bezier(0.16,1,0.3,1);";

      let revealed = false;
      const revealRuntime = () => {
        if (revealed) return;
        revealed = true;
        frame.style.opacity = "1";
        frame.style.pointerEvents = "auto";
        setTimeout(() => {
          preStage.style.opacity = "0";
          setTimeout(() => preStage.remove(), 240);
        }, 180);
        try {
          frame.focus();
          if (frame.contentWindow) frame.contentWindow.focus();
        } catch (_) {}
      };

      const onMsg = (ev) => {
        if (ev.origin === location.origin && ev.data && ev.data.type === "ac-runtime-splash-ready") {
          window.removeEventListener("message", onMsg);
          revealRuntime();
        }
      };
      window.addEventListener("message", onMsg);
      frame.addEventListener("load", () => {
        window.removeEventListener("message", onMsg);
        revealRuntime();
      });

      wrap.appendChild(preStage);
      wrap.appendChild(frame);
      document.body.appendChild(wrap);
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
    launchInPlace(initialSlug, false, false);
  }

  window.addEventListener("popstate", (e) => {
    if (e.state && e.state.acStudioLaunch) {
      launchInPlace(e.state.acStudioLaunch, false, true);
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

    launchInPlace(targetSlug, curSlug !== targetSlug, true);
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

      const cleanRuntimeUrl = mount.replace(/\/+$/, "");
      fetch(cleanRuntimeUrl, { priority: "low" }).catch(() => {});
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
