# -*- coding: utf-8 -*-
import os
import sys
import urllib.request
import urllib.error
import json
from datetime import datetime

# ══════════════ CONFIG ══════════════
# Normal mode:  python upload_artifacts.py <local_folder> <api_token>
# Retry mode:   python upload_artifacts.py retry <api_token> <failed_log.json>

art_base   = "https://artifactory.fis.dev/artifactory"
art_repo   = "myaccess-maven-release-local"
art_dest   = "8.4-testing"
valid_exts = (".jar", ".class")

if len(sys.argv) < 3:
    print("Normal mode: python upload_artifacts.py <local_folder> <api_token>")
    print("Retry mode:  python upload_artifacts.py retry <api_token> <failed_log.json>")
    sys.exit(1)

mode      = sys.argv[1]
api_token = sys.argv[2]
headers   = {"X-JFrog-Art-Api": api_token}

# ══════════════ COUNTERS ══════════════
uploaded  = 0
skipped   = 0
exists    = 0
failed    = 0
failures  = []

# ══════════════ CHECK IF FILE EXISTS IN ARTIFACTORY ══════════════
def file_exists_in_artifactory(art_path):
    """
    Does a HEAD request to Artifactory - much faster than downloading.
    Returns True if file is already there, False if not.
    """
    url = f"{art_base}/{art_repo}/{art_path}"
    try:
        req = urllib.request.Request(url, headers=headers, method="HEAD")
        with urllib.request.urlopen(req) as response:
            return response.getcode() == 200
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False   # file not there, need to upload
        raise              # any other HTTP error, bubble it up
    except Exception:
        return False

# ══════════════ UPLOAD ══════════════
def upload_file(local_path, art_path, skip_if_exists=True):
    global uploaded, failed, exists

    # Check if already exists before uploading
    if skip_if_exists:
        print(f"  Checking:  {art_path}")
        if file_exists_in_artifactory(art_path):
            print(f"  Already exists, skipping.")
            exists += 1
            return

    url = f"{art_base}/{art_repo}/{art_path}"
    print(f"\n  Uploading: {local_path}")
    print(f"  To:        {url}")

    try:
        with open(local_path, "rb") as f:
            data = f.read()

        req = urllib.request.Request(url, data=data, headers=headers, method="PUT")
        with urllib.request.urlopen(req) as response:
            print(f"  Status:    {response.getcode()} OK")
            uploaded += 1

    except urllib.error.HTTPError as e:
        reason = f"HTTP {e.code} - {e.reason}"
        print(f"  ERROR:     {reason}")
        failures.append({
            "local_path": local_path,
            "art_path":   art_path,
            "error":      reason
        })
        failed += 1

    except Exception as e:
        reason = str(e)
        print(f"  ERROR:     {reason}")
        failures.append({
            "local_path": local_path,
            "art_path":   art_path,
            "error":      reason
        })
        failed += 1

# ══════════════ NORMAL MODE - walk local folder ══════════════
def process_folder(local_folder, relative_path=""):
    global skipped

    for entry in os.scandir(local_folder):
        entry_relative = os.path.join(relative_path, entry.name).replace("\\", "/")

        if entry.is_dir():
            print(f"\nEntering folder: {entry.path}")
            process_folder(entry.path, entry_relative)

        elif entry.is_file():
            if entry.name.endswith(valid_exts):
                art_path = f"{art_dest}/{entry_relative}"
                upload_file(entry.path, art_path, skip_if_exists=True)
            else:
                print(f"  Skipping:  {entry.name} (not a .jar or .class)")
                skipped += 1

# ══════════════ SAVE FAILURE LOG ══════════════
def save_failure_log():
    if not failures:
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file  = f"failed_uploads_{timestamp}.json"

    with open(log_file, "w") as f:
        json.dump(failures, f, indent=2)

    print(f"\n  Failure log saved to: {log_file}")
    return log_file

# ══════════════ RUN ══════════════
if mode == "retry":
    # RETRY MODE - read failures from a previous log file
    # In retry mode we always attempt the upload regardless, since these already failed
    if len(sys.argv) < 4:
        print("Retry mode requires a log file: python upload_artifacts.py retry <api_token> <failed_log.json>")
        sys.exit(1)

    log_file = sys.argv[3]
    print(f"Retry mode - reading failures from: {log_file}")
    print("=" * 60)

    with open(log_file) as f:
        failed_files = json.load(f)

    print(f"Found {len(failed_files)} failed files to retry...")

    for item in failed_files:
        # skip_if_exists=False on retry so we always force the upload
        upload_file(item["local_path"], item["art_path"], skip_if_exists=False)

else:
    # NORMAL MODE - walk the local folder
    local_root = mode   # first arg is the folder path in normal mode
    print(f"Starting upload from: {local_root}")
    print(f"Destination:          {art_base}/{art_repo}/{art_dest}/")
    print(f"File types:           {valid_exts}")
    print(f"Mode:                 Skipping files that already exist in Artifactory")
    print("=" * 60)
    process_folder(local_root)

# ══════════════ SUMMARY ══════════════
print("\n" + "=" * 60)
print(f"Done!")
print(f"  Uploaded:       {uploaded}")
print(f"  Already exists: {exists}  (skipped)")
print(f"  Skipped:        {skipped}  (wrong file type)")
print(f"  Failed:         {failed}")

if failures:
    log = save_failure_log()
    print(f"\nTo retry failed files run:")
    print(f"  python upload_artifacts.py retry \"your-api-token\" \"{log}\"")
else:
    print("\nNo failures!")
```

The key addition is the `file_exists_in_artifactory()` function — instead of downloading the file to check, it does a **HEAD request** which just asks "does this exist?" without transferring any data. So it's super fast, basically zero overhead per file.

The summary at the end now breaks down all four categories so you know exactly what happened:
```
Done!
  Uploaded:       22
  Already exists: 817  (skipped)
  Skipped:        24793  (wrong file type)
  Failed:         0
