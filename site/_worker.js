/**
 * Cloudflare Pages Advanced Mode Edge Worker for AllCraft Studio (https://allcraft.app)
 *
 * Eliminates Google duplicate-content indexing by enforcing a 1-hop 301 canonical
 * redirect from:
 *   - https://the-allcraft.pages.dev/* (and *.the-allcraft.pages.dev preview URLs)
 *   - https://www.allcraft.app/* (and any www.* alias)
 *   - http://* -> https://allcraft.app/*
 *
 * Also handles legacy /apps/*, short launch slugs (/photo, /vector, ...), and
 * *-alternative SEO aliases in 1 hop before falling through to env.ASSETS.fetch().
 */

const CANONICAL_HOST = "allcraft.app";
const CANONICAL_ORIGIN = "https://allcraft.app";

const SHORT_LAUNCH_MAP = {
  photo: "photocraft",
  vector: "vectorcraft",
  film: "filmcraft",
  light: "lightcraft",
  pdf: "pdfcraft",
  effect: "effectcraft",
  ani: "anicraft",
  design: "designcraft",
  texture: "texturecraft",
  material: "materialcraft",
  sound: "soundcraft",
  word: "wordcraft",
  deck: "deckcraft",
  cad: "cadcraft",
  grid: "gridcraft",
};

const SEO_ALIAS_MAP = {
  "photoshop-alternative": "photocraft",
  "illustrator-alternative": "vectorcraft",
  "premiere-alternative": "filmcraft",
  "lightroom-alternative": "lightcraft",
  "acrobat-alternative": "pdfcraft",
  "after-effects-alternative": "effectcraft",
  "animate-alternative": "anicraft",
  "indesign-alternative": "designcraft",
  "substance-painter-alternative": "texturecraft",
  "substance-designer-alternative": "materialcraft",
  "audition-alternative": "soundcraft",
  "word-alternative": "wordcraft",
  "powerpoint-alternative": "deckcraft",
  "autocad-alternative": "cadcraft",
  "excel-alternative": "gridcraft",
};

function resolvePathRedirect(pathname, incomingSearchParams) {
  const trimmed =
    pathname.length > 1 && pathname.endsWith("/")
      ? pathname.slice(0, -1)
      : pathname;

  if (trimmed === "/apps") {
    const qs = incomingSearchParams.toString();
    return `${qs ? "/?" + qs : "/"}#lineup`;
  }

  if (trimmed.startsWith("/apps/")) {
    const rest = trimmed.slice("/apps/".length);
    if (rest && !rest.includes("/")) {
      const qs = incomingSearchParams.toString();
      return `/${rest}/${qs ? "?" + qs : ""}`;
    }
  }

  if (trimmed.startsWith("/") && !trimmed.slice(1).includes("/")) {
    const key = trimmed.slice(1).toLowerCase();

    if (Object.prototype.hasOwnProperty.call(SHORT_LAUNCH_MAP, key)) {
      const slug = SHORT_LAUNCH_MAP[key];
      const merged = new URLSearchParams(incomingSearchParams);
      if (!merged.has("launch")) {
        merged.set("launch", "1");
      }
      return `/${slug}/?${merged.toString()}`;
    }

    if (Object.prototype.hasOwnProperty.call(SEO_ALIAS_MAP, key)) {
      const slug = SEO_ALIAS_MAP[key];
      const qs = incomingSearchParams.toString();
      return `/${slug}/${qs ? "?" + qs : ""}`;
    }
  }

  return null;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const host = url.hostname.toLowerCase();
    const isLocalDev = host === "localhost" || host === "127.0.0.1";
    const isNonCanonicalHost =
      !isLocalDev && (host !== CANONICAL_HOST || url.protocol !== "https:");

    const mappedTarget = resolvePathRedirect(url.pathname, url.searchParams);

    if (isNonCanonicalHost) {
      const targetSuffix = mappedTarget ?? `${url.pathname}${url.search}`;
      return new Response(null, {
        status: 301,
        headers: {
          Location: `${CANONICAL_ORIGIN}${targetSuffix}`,
          "Cache-Control": "public, max-age=86400",
          "X-Robots-Tag": "noindex",
        },
      });
    }

    if (mappedTarget !== null) {
      const origin = isLocalDev ? url.origin : CANONICAL_ORIGIN;
      return new Response(null, {
        status: 301,
        headers: {
          Location: `${origin}${mappedTarget}`,
          "Cache-Control": "public, max-age=86400",
        },
      });
    }

    return env.ASSETS.fetch(request);
  },
};
