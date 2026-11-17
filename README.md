# The AllCraft Studio Hub (`thepixopik/allcraft`)

Central multi-app WebAssembly assembler, SEO page generator & automated Cloudflare Pages publisher for **[allcraft.app](https://allcraft.app)** (Cloudflare Pages project: `the-allcraft`, with `301` canonical redirects from `the-allcraft.pages.dev`).

## Architecture

Whenever any of the 15 Craft app repositories finishes building its Rust → WebAssembly web artifact, it sends a `repository_dispatch` (`app-updated`) webhook to this hub repository:

1. **`scripts/assemble.py`** fetches the latest non-expired GitHub Actions build artifact for all 15 apps listed in [`apps.json`](apps.json).
2. **Wasm Stripper & 1.5 MiB Streaming Chunks:** Strips non-essential custom Wasm sections (`name`, `producers`, `.debug*`, `reloc.*`), recompresses at gzip level 9, slices binaries into **1.5 MiB `.part*` chunks** (staying well within Cloudflare Pages' 25 MiB per-file limit), and injects a **0ms `<head>` eager `DecompressionStream` + `CacheStorage` (`allcraft-wasm-v2`) loader** alongside each app's desktop-style loading splash.
3. **`scripts/generate_pages.py` & `scripts/apps_catalog.py`** generate the 15 SEO detail pages (`/<slug>/`), comparison hubs (`/adobe-alternative/`, `/artcraft-web/`), and `/sitemap.xml`.
4. **`site/`** contributes the main launcher (`site/index.html`), smart card hover preloader (`site/hover-preload.js`), security/caching/COOP+COEP headers (`site/_headers`), canonical & alias redirects (`site/_redirects`), `robots.txt`, and `404.html`.
5. **`.github/workflows/deploy-studio.yml`** deploys the unified `dist/` bundle to Cloudflare Pages via Wrangler v4.

## Integrated 15 Studio Apps

| App | Live Web Route | Detail Page | Source Repository |
|---|---|---|---|
| **The AllCraft Photo** | `/photo/` | `/photocraft/` | `thepixopik/photocraft` |
| **The AllCraft Vector** | `/vector/` | `/vectorcraft/` | `thepixopik/vectorcraft` |
| **The AllCraft Film** | `/film/` | `/filmcraft/` | `thepixopik/filmcraft` |
| **The AllCraft Light** | `/light/` | `/lightcraft/` | `thepixopik/lightcraft` |
| **The AllCraft PDF** | `/pdf/` | `/pdfcraft/` | `thepixopik/pdfcraft` |
| **The AllCraft Effect** | `/effect/` | `/effectcraft/` | `thepixopik/effectcraft` |
| **The AllCraft Ani** | `/ani/` | `/anicraft/` | `thepixopik/anicraft` |
| **The AllCraft Design** | `/design/` | `/designcraft/` | `thepixopik/designcraft` |
| **The AllCraft Texture** | `/texture/` | `/texturecraft/` | `thepixopik/texturecraft` |
| **The AllCraft Material** | `/material/` | `/materialcraft/` | `thepixopik/materialcraft` |
| **The AllCraft Sound** | `/sound/` | `/soundcraft/` | `thepixopik/soundcraft` |
| **The AllCraft Word** | `/word/` | `/wordcraft/` | `thepixopik/wordcraft` |
| **The AllCraft Deck** | `/deck/` | `/deckcraft/` | `thepixopik/deckcraft` |
| **The AllCraft CAD** | `/cad/` | `/cadcraft/` | `thepixopik/cadcraft` |
| **The AllCraft Grid** | `/grid/` | `/gridcraft/` | `thepixopik/gridcraft` |

## Required Secrets in `thepixopik/allcraft`

Configure these 3 repository secrets under **Settings → Secrets and variables → Actions**:

| Secret Name | Value / Permissions |
|---|---|
| `STUDIO_PAT` | GitHub Fine-Grained PAT scoped to `thepixopik` with **Actions: Read** (to download app artifacts) & **Contents: Read and write** |
| `CLOUDFLARE_ACCOUNT_ID` | `<YOUR_CLOUDFLARE_ACCOUNT_ID>` *(from Cloudflare Dashboard → Workers & Pages → Overview)* |
| `CLOUDFLARE_API_TOKEN` | Cloudflare API Token with **Account → Cloudflare Pages → Edit** + **User → User Details → Read** |

*(Also add `STUDIO_PAT` as an Actions secret in each individual Craft app repository so its web build workflow can send `repository_dispatch` events to `thepixopik/allcraft`.)*

## Adding a New App

1. Add the app entry in [`apps.json`](apps.json) (`id`, `name`, `repo`, `artifact_name`, `branch`, `mount_path`, `required`).
2. Add its splash profile in [`scripts/assemble.py`](scripts/assemble.py) (`SPLASH_PROFILES`) and SEO metadata in [`scripts/apps_catalog.py`](scripts/apps_catalog.py).
3. Add a launch card in [`site/index.html`](site/index.html) plus route rules in [`site/_headers`](site/_headers) and [`site/_redirects`](site/_redirects).
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
