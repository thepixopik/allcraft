#!/usr/bin/env python3
"""Assemble all Craft web app artifacts from apps.json into a unified dist/ folder for Cloudflare Pages."""

import datetime
import io
import json
import os
import pathlib
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
APPS_CONFIG = ROOT / "apps.json"
SITE_DIR = ROOT / "site"
DIST_DIR = ROOT / "dist"
CF_MAX_FILE_BYTES = 25 * 1024 * 1024  # 25 MiB Cloudflare Pages single-asset limit


class StripCrossOriginAuthRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Strip GitHub Authorization header when redirected to Azure/GitHub Actions blob storage."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req is None:
            return None
        orig_host = urllib.parse.urlparse(req.full_url).hostname
        new_host = urllib.parse.urlparse(newurl).hostname
        if orig_host != new_host:
            new_req.headers.pop("Authorization", None)
            new_req.unredirected_hdrs.pop("Authorization", None)
        return new_req


OPENER = urllib.request.build_opener(StripCrossOriginAuthRedirectHandler)


def gh_get_json(url: str, token: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "allcraft-studio-assembler",
        },
    )
    with OPENER.open(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def gh_download_bytes(url: str, token: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "allcraft-studio-assembler",
        },
    )
    with OPENER.open(req, timeout=180) as resp:
        return resp.read()


def pick_latest_artifact(repo: str, artifact_name: str, branch: str, token: str) -> dict | None:
    encoded_name = urllib.parse.quote(artifact_name)
    url = f"https://api.github.com/repos/{repo}/actions/artifacts?name={encoded_name}&per_page=30"
    data = gh_get_json(url, token)
    artifacts = data.get("artifacts") or []
    valid = [a for a in artifacts if not a.get("expired")]
    if branch:
        branch_matches = [
            a for a in valid if (a.get("workflow_run") or {}).get("head_branch") == branch
        ]
        if branch_matches:
            valid = branch_matches
    if not valid:
        return None
    valid.sort(key=lambda a: a.get("created_at") or "", reverse=True)
    return valid[0]


def main() -> None:
    token = (os.environ.get("STUDIO_PAT") or os.environ.get("GITHUB_TOKEN") or "").strip()
    if not token:
        print("ERROR: STUDIO_PAT secret is missing! Add a GitHub PAT with Actions:Read permission.", file=sys.stderr)
        sys.exit(1)

    config = json.loads(APPS_CONFIG.read_text(encoding="utf-8"))
    apps = config.get("apps") or []

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    shutil.copytree(SITE_DIR, DIST_DIR)

    manifest_entries = []
    for app in apps:
        app_id = app["id"]
        repo = app["repo"]
        artifact_name = app["artifact_name"]
        branch = app.get("branch", "main")
        mount_path = app["mount_path"].strip("/")
        required = app.get("required", True)

        print(f"\n==> Fetching '{artifact_name}' from {repo} (branch: {branch})...")
        try:
            art = pick_latest_artifact(repo, artifact_name, branch, token)
        except urllib.error.HTTPError as exc:
            msg = f"GitHub API HTTP {exc.code} on {repo} — ensure STUDIO_PAT has Actions:Read access to {repo}."
            if required:
                print(f"ERROR: {msg}", file=sys.stderr)
                sys.exit(1)
            print(f"WARN: {msg} (skipping optional app '{app_id}')")
            continue

        if not art:
            msg = f"No non-expired artifact '{artifact_name}' found in {repo}."
            if required:
                print(f"ERROR: {msg} Run the build workflow in {repo} once first.", file=sys.stderr)
                sys.exit(1)
            print(f"WARN: {msg} (skipping optional app '{app_id}')")
            continue

        dl_url = art["archive_download_url"]
        size_mb = (art.get("size_in_bytes") or 0) / (1024 * 1024)
        sha = (art.get("workflow_run") or {}).get("head_sha", "unknown")
        print(f"    Downloading artifact #{art['id']} ({size_mb:.2f} MiB, commit {sha[:7]})...")
        zip_bytes = gh_download_bytes(dl_url, token)

        target_dir = DIST_DIR / mount_path
        target_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            zf.extractall(target_dir)

        print(f"    Extracted to dist/{mount_path}/ ({sum(1 for _ in target_dir.rglob('*') if _.is_file())} files)")
        manifest_entries.append(
            {
                "id": app_id,
                "name": app.get("name", app_id),
                "repo": repo,
                "mount": f"/{mount_path}/",
                "artifact_id": art["id"],
                "commit_sha": sha,
                "artifact_created_at": art.get("created_at"),
            }
        )

    # Validate Cloudflare Pages 25 MiB single-file limit across the entire combined site
    oversized = []
    total_bytes = 0
    file_count = 0
    for f in DIST_DIR.rglob("*"):
        if f.is_file():
            sz = f.stat().st_size
            total_bytes += sz
            file_count += 1
            if sz > CF_MAX_FILE_BYTES:
                oversized.append((str(f.relative_to(DIST_DIR)), sz))

    if oversized:
        for rel, sz in oversized:
            print(f"ERROR: {rel} is {sz / (1024 * 1024):.2f} MiB (exceeds Cloudflare 25 MiB limit!)", file=sys.stderr)
        sys.exit(1)

    build_manifest = {
        "assembled_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_files": file_count,
        "total_size_mb": round(total_bytes / (1024 * 1024), 2),
        "apps": manifest_entries,
    }
    (DIST_DIR / "build-manifest.json").write_text(json.dumps(build_manifest, indent=2), encoding="utf-8")
    print(f"\nSUCCESS: Assembled {len(manifest_entries)} app(s), {file_count} files ({total_bytes / (1024 * 1024):.2f} MiB total) into dist/")


if __name__ == "__main__":
    main()
