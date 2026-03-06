# -*- coding: utf-8 -*-
import os
import sys
import urllib.request
import urllib.error

# ══════════════ CONFIG ══════════════
# Usage: python upload_artifacts.py <local_folder> <api_token>
# Example: python upload_artifacts.py "C:\myproject" "your-api-token-here"

art_base    = "https://artifactory.fis.dev/artifactory"
art_repo    = "myaccess-maven-release-local"
art_dest    = "8.4-testing"   # root destination folder in Artifactory
valid_exts  = (".jar", ".class")

if len(sys.argv) < 3:
    print("Usage: python upload_artifacts.py <local_folder> <api_token>")
    sys.exit(1)

local_root  = sys.argv[1]   # e.g. C:\myproject\workspace
api_token   = sys.argv[2]

headers = {
    "X-JFrog-Art-Api": api_token   # API token auth - won't lock your account!
}

# ══════════════ COUNTERS ══════════════
uploaded = 0
skipped  = 0
failed   = 0

# ══════════════ UPLOAD ══════════════
def upload_file(local_path, art_path):
    global uploaded, failed

    url = f"{art_base}/{art_repo}/{art_path}"

    print(f"\n  Uploading: {local_path}")
    print(f"  To:        {url}")

    try:
        with open(local_path, "rb") as f:
            data = f.read()

        req = urllib.request.Request(url, data=data, headers=headers, method="PUT")
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            print(f"  Status:    {status} OK")
            uploaded += 1

    except urllib.error.HTTPError as e:
        print(f"  ERROR:     HTTP {e.code} - {e.reason}")
        failed += 1
    except Exception as e:
        print(f"  ERROR:     {str(e)}")
        failed += 1

def process_folder(local_folder, relative_path=""):
    global skipped

    for entry in os.scandir(local_folder):
        # Build the relative path from the root (this mirrors folder structure)
        entry_relative = os.path.join(relative_path, entry.name).replace("\\", "/")

        if entry.is_dir():
            print(f"\nEntering folder: {entry.path}")
            process_folder(entry.path, entry_relative)

        elif entry.is_file():
            if entry.name.endswith(valid_exts):
                # e.g. Tomcat/lib/somejar.jar becomes 8.4-testing/Tomcat/lib/somejar.jar
                art_path = f"{art_dest}/{entry_relative}"
                upload_file(entry.path, art_path)
            else:
                print(f"  Skipping:  {entry.name} (not a .jar or .class)")
                skipped += 1

# ══════════════ RUN ══════════════
print(f"Starting upload from: {local_root}")
print(f"Destination:          {art_base}/{art_repo}/{art_dest}/")
print(f"File types:           {valid_exts}")
print("=" * 60)

process_folder(local_root)

print("\n" + "=" * 60)
print(f"Done! Uploaded: {uploaded} | Skipped: {skipped} | Failed: {failed}")
