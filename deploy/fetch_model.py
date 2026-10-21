"""Put the embedding model in models/ as plain files, so the container needs no internet and no HF cache.

python deploy/fetch_model.py
"""
from pathlib import Path

from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parent.parent
path = snapshot_download("BAAI/bge-small-en-v1.5", local_dir=ROOT / "models" / "bge-small-en-v1.5",
                         allow_patterns=["*.json", "*.txt", "model.safetensors", "1_Pooling/*"])
print("model files in", Path(path).relative_to(ROOT))
for f in sorted(Path(path).rglob("*")):
    if f.is_file() and ".cache" not in f.parts:
        print(f"  {f.relative_to(path)}  {f.stat().st_size:,} bytes")
