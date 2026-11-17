# The AllCraft Studio Hub (`thepixopik/allcraft`)

Central multi-app assembler & automated Cloudflare Pages publisher for **[the-allcraft.pages.dev](https://the-allcraft.pages.dev)**.

## Architecture

Whenever any app repository (`vectorcraft`, `photocraft`, or future apps) finishes building its WebAssembly artifact, it sends a `repository_dispatch` webhook to this hub repository. `scripts/assemble.py` pulls the latest artifact for every app listed in [`apps.json`](apps.json), merges them with [`site/index.html`](site/index.html) and [`site/_headers`](site/_headers), validates Cloudflare's 25 MiB per-file limit, and deploys the unified site to Cloudflare Pages in ~15 seconds.

## Required Secrets in `thepixopik/allcraft`

Add these 3 secrets under **Settings -> Secrets and variables -> Actions**:

| Secret Name | Value / Permissions |
|---|---|
| `STUDIO_PAT` | GitHub Fine-Grained PAT scoped to `thepixopik` with **Actions: Read and write** & **Contents: Read and write** |
| `CLOUDFLARE_ACCOUNT_ID` | `88f57683348cf1c6f66c6b52553452a2` |
| `CLOUDFLARE_API_TOKEN` | Cloudflare API Token with **Account -> Cloudflare Pages -> Edit** (`All accounts`) + **User -> User Details -> Read** |

*(Also add `STUDIO_PAT` as a secret in `vectorcraft`, `photocraft`, and any future app repo so their build workflows can ping `thepixopik/allcraft` upon completion.)*

## Adding a New App in the Future (30 Seconds)

1. Add a new block in [`apps.json`](apps.json) pointing to your new repo, artifact name, and `mount_path` (e.g. `"video"`).
2. Add a launch card in [`site/index.html`](site/index.html) linking to `./video/`.
3. At the end of the new app's build workflow, add the webhook trigger step:

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
