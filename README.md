# The AllCraft Studio Hub (`thepixopik/allcraft`)

Central multi-app WebAssembly assembler, SEO page generator & automated Cloudflare Pages publisher for **[allcraft.app](https://allcraft.app)** (Cloudflare Pages project: `the-allcraft`, with `301` canonical redirects from `the-allcraft.pages.dev`).

## Architecture

Whenever any of the 15 Craft app repositories finishes building its Rust → WebAssembly web artifact, it sends a `repository_dispatch` (`app-updated`) webhook to this hub repository:

1. **`scripts/assemble.py`** fetches the latest non-expired GitHub Actions build artifact for all 15 apps listed in [`apps.json`](apps.json).
2. **Permanent 90-Day Expiry Fallback (`studio-cache` Release):** Whenever a fresh artifact is downloaded, `scripts/assemble.py` incrementally mirrors `<app_id>.zip` + `cache-manifest.json` into the rolling [`studio-cache`](https://github.com/thepixopik/allcraft/releases/tag/studio-cache) GitHub pre-release (which never expires). If any app repository goes >90 days without a rebuild and its Actions artifact expires, `assemble.py` automatically restores that app from `studio-cache` so deployments never break.
3. **Unified Single-Slug SEO + In-Place App Launch:** Every app shares one canonical URL (`/<slug>/`, e.g. `/photocraft/`) for both its SEO detail page and its live WebAssembly editor. Engine assets live under `/runtime/<slug>/` (`X-Robots-Tag: noindex`) and mount full-screen in-place via `site/hover-preload.js`, while legacy short paths (`/photo/`, `/vector/`, etc.) `301` redirect cleanly onto `/<slug>/`.
4. **Wasm Stripper & 1.5 MiB Streaming Chunks:** Strips non-essential custom Wasm sections (`name`, `producers`, `.debug*`, `reloc.*`), recompresses at gzip level 9, slices binaries into **1.5 MiB `.part*` chunks** (staying well within Cloudflare Pages' 25 MiB per-file limit), and injects a **0ms `<head>` eager `DecompressionStream` + `CacheStorage` (`allcraft-wasm-v2`) loader** alongside each app's desktop-style loading splash.
5. **`scripts/generate_pages.py` & `scripts/apps_catalog.py`** generate the 15 SEO detail pages (`/<slug>/`), comparison hubs (`/adobe-alternative/`, `/artcraft-web/`), and `/sitemap.xml`.
6. **`.github/workflows/deploy-studio.yml`** deploys the unified `dist/` bundle to Cloudflare Pages via Wrangler v4.

## Integrated 15 Studio Apps

| App | Canonical Page & Live Editor URL | Internal Runtime Mount | Source Repository |
|---|---|---|---|
| **The AllCraft Photo** | `/photocraft/` | `/runtime/photocraft/` | `thepixopik/photocraft` |
| **The AllCraft Vector** | `/vectorcraft/` | `/runtime/vectorcraft/` | `thepixopik/vectorcraft` |
| **The AllCraft Film** | `/filmcraft/` | `/runtime/filmcraft/` | `thepixopik/filmcraft` |
| **The AllCraft Light** | `/lightcraft/` | `/runtime/lightcraft/` | `thepixopik/lightcraft` |
| **The AllCraft PDF** | `/pdfcraft/` | `/runtime/pdfcraft/` | `thepixopik/pdfcraft` |
| **The AllCraft Effect** | `/effectcraft/` | `/runtime/effectcraft/` | `thepixopik/effectcraft` |
| **The AllCraft Ani** | `/anicraft/` | `/runtime/anicraft/` | `thepixopik/anicraft` |
| **The AllCraft Design** | `/designcraft/` | `/runtime/designcraft/` | `thepixopik/designcraft` |
| **The AllCraft Texture** | `/texturecraft/` | `/runtime/texturecraft/` | `thepixopik/texturecraft` |
| **The AllCraft Material** | `/materialcraft/` | `/runtime/materialcraft/` | `thepixopik/materialcraft` |
| **The AllCraft Sound** | `/soundcraft/` | `/runtime/soundcraft/` | `thepixopik/soundcraft` |
| **The AllCraft Word** | `/wordcraft/` | `/runtime/wordcraft/` | `thepixopik/wordcraft` |
| **The AllCraft Deck** | `/deckcraft/` | `/runtime/deckcraft/` | `thepixopik/deckcraft` |
| **The AllCraft CAD** | `/cadcraft/` | `/runtime/cadcraft/` | `thepixopik/cadcraft` |
| **The AllCraft Grid** | `/gridcraft/` | `/runtime/gridcraft/` | `thepixopik/gridcraft` |

## Required Secrets in `thepixopik/allcraft`

Configure these 3 repository secrets under **Settings → Secrets and variables → Actions**:

| Secret Name | Value / Permissions |
|---|---|
| `STUDIO_PAT` | GitHub Fine-Grained PAT scoped to `thepixopik` with **Actions: Read** (to download app artifacts) & **Contents: Read and write** (for `repository_dispatch` & `studio-cache` release backups) |
| `CLOUDFLARE_ACCOUNT_ID` | `<YOUR_CLOUDFLARE_ACCOUNT_ID>` *(from Cloudflare Dashboard → Workers & Pages → Overview)* |
| `CLOUDFLARE_API_TOKEN` | Cloudflare API Token with **Account → Cloudflare Pages → Edit** + **User → User Details → Read** |

*(Also add `STUDIO_PAT` as an Actions secret in each individual Craft app repository so its web build workflow can send `repository_dispatch` events to `thepixopik/allcraft`.)*

## Adding a New App

1. Add the app entry in [`apps.json`](apps.json) (`id`, `name`, `repo`, `artifact_name`, `branch`, `mount_path: "runtime/<slug>"`, `required`).
2. Add its splash profile in [`scripts/assemble.py`](scripts/assemble.py) (`SPLASH_PROFILES`) and SEO metadata in [`scripts/apps_catalog.py`](scripts/apps_catalog.py).
3. Add a launch card in [`site/index.html`](site/index.html) plus route rules in [`site/hover-preload.js`](site/hover-preload.js), [`site/_headers`](site/_headers), and [`site/_redirects`](site/_redirects).
4. At the end of the new app's web build workflow, trigger the Studio Hub deploy:

```yaml
      - name: Trigger AllCraft Studio Hub Deploy
        if: success()
        run: |
          curl -fsSL -X POST \
            -H "Accept: application/vnd.github+json" \
            -H "Authorization: Bearer ${{ secrets.STUDIO_PAT }}" \
            https://api.github.com/repos/thepixopik/allcraft/dispatches \
            -d '{"event_type":"app-updated","client_payload":{"repo":"${{ github.repository }}"}}'
```
