"""Writes the Homebrew cask (Casks/cockpit.rb) and the Scoop manifest (bucket/cockpit.json) for a release.

Usage: write-manifests.py --version 0.1.0 --repo Owner/repo --dmg-sha256 <hex> --zip-sha256 <hex>
       [--min-macos 11.0] [--base-url URL]
The release workflow runs it; --base-url exists so the manifests can be tested against local files.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESCRIPTION = "Personal cockpit for tasks, goals, learning, trips and money"

MACOS_NAMES = {11: "big_sur", 12: "monterey", 13: "ventura", 14: "sonoma", 15: "sequoia", 26: "tahoe"}

CASK = '''cask "cockpit" do
  version "{version}"
  sha256 "{dmg_sha}"

  url "{mac_url}"
  name "Cockpit"
  desc "{description}"
  homepage "{homepage}"

  depends_on arch: :arm64
  depends_on macos: :{macos}

  app "Cockpit.app"

  # Cockpit is not signed with an Apple Developer ID, so macOS would refuse to open a quarantined
  # copy. Homebrew has verified the download against the sha256 above; this clears the flag.
  postflight_steps do
    run "/usr/bin/xattr", args: ["-dr", "com.apple.quarantine", "{{{{appdir}}}}/Cockpit.app"]
  end

  caveats "Your data is kept in ~/Library/Application Support/Cockpit. Uninstalling does not delete it."
end
'''


def sha(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise argparse.ArgumentTypeError("expected a lowercase 64-character sha256")
    return value


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--version", required=True)
    p.add_argument("--repo", required=True, help="GitHub owner/name")
    p.add_argument("--dmg-sha256", required=True, type=sha)
    p.add_argument("--zip-sha256", required=True, type=sha)
    p.add_argument("--min-macos", default="12.0", help="oldest macOS the .dmg runs on, e.g. 11.0")
    p.add_argument("--base-url", help="where the release files are (default: the GitHub release for this version)")
    a = p.parse_args()
    if not re.fullmatch(r"\d+\.\d+\.\d+", a.version):
        p.error("version must look like 1.2.3")

    macos = MACOS_NAMES.get(int(a.min_macos.split(".")[0]))
    if macos is None:
        p.error(f"no Homebrew name known for macOS {a.min_macos}: add it to MACOS_NAMES")

    homepage = f"https://github.com/{a.repo}"
    releases = f"{homepage}/releases/download"
    base = a.base_url.rstrip("/") if a.base_url else f"{releases}/v{a.version}"
    mac_file = "Cockpit-{v}-mac-arm64.dmg"
    win_file = "Cockpit-{v}-windows-x64.zip"

    # In the cask the version is interpolated by Ruby, so `brew bump` style edits stay one-line.
    mac_url = (f"{base}/" if a.base_url else f"{releases}/v#{{version}}/") + mac_file.format(v="#{version}")
    cask = ROOT / "Casks" / "cockpit.rb"
    cask.parent.mkdir(exist_ok=True)
    cask.write_text(CASK.format(version=a.version, dmg_sha=a.dmg_sha256, mac_url=mac_url,
                                description=DESCRIPTION, homepage=homepage, macos=macos), encoding="utf-8")

    manifest = {
        "version": a.version,
        "description": DESCRIPTION,
        "homepage": homepage,
        "license": "MIT",
        "architecture": {"64bit": {
            "url": f"{base}/{win_file.format(v=a.version)}",
            "hash": a.zip_sha256,
            "extract_dir": "Cockpit",
        }},
        "shortcuts": [["Cockpit.exe", "Cockpit"]],
        "notes": "Your data is kept in %APPDATA%\\Cockpit. Uninstalling does not delete it.",
        "checkver": "github",
        "autoupdate": {"architecture": {"64bit": {"url": f"{releases}/v$version/{win_file.format(v='$version')}"}}},
    }
    bucket = ROOT / "bucket" / "cockpit.json"
    bucket.parent.mkdir(exist_ok=True)
    bucket.write_text(json.dumps(manifest, indent=4) + "\n", encoding="utf-8")
    print(f"wrote {cask.relative_to(ROOT)} and {bucket.relative_to(ROOT)} for {a.version}")


if __name__ == "__main__":
    main()
