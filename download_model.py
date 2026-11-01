"""Download intfloat/multilingual-e5-small once for 100% local, offline execution.

After running this script, the model is permanently saved in the local 'models/'
directory. The application will never send any requests to Hugging Face again.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Suppress warnings on Windows
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

ROOT_DIR = Path(__file__).resolve().parent
TARGET_DIR = ROOT_DIR / "models" / "multilingual-e5-small"
TARGET_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 65)
print("  OFFLINE MODEL DOWNLOADER (intfloat/multilingual-e5-small)")
print("=" * 65)
print(f"Local storage destination: {TARGET_DIR}\n")
print("Downloading files (supports automatic resume)...")

try:
    from huggingface_hub import snapshot_download

    snapshot_download(
        repo_id="intfloat/multilingual-e5-small",
        local_dir=str(TARGET_DIR),
        resume_download=True,
    )
    print("\n" + "=" * 65)
    print("SUCCESS: Model is fully saved to local storage!")
    print(f"Path: {TARGET_DIR}")
    print("From now on, the app runs 100% offline without any HuggingFace requests.")
    print("=" * 65)
except Exception as e:
    print(f"\nDownload error: {e}", file=sys.stderr)
    sys.exit(1)
