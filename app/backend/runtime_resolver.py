"""
Robust runtime directory resolution for WDD PulseX.
Priority: PALMX_RUNTIME_DIR env → /code/runtime (Docker) → walk up to repo root.
"""
import os
from pathlib import Path

def get_runtime_dir() -> Path:
    # 1. Explicit env var
    env_val = os.getenv("PALMX_RUNTIME_DIR")
    if env_val:
        p = Path(env_val)
        if p.is_dir():
            return p

    # 2. Docker convention
    docker_path = Path("/code/runtime")
    if docker_path.is_dir():
        return docker_path

    # 3. Walk up from this file to find repo root containing runtime/
    current = Path(__file__).resolve().parent  # app/backend/
    for _ in range(6):
        candidate = current / "runtime"
        if candidate.is_dir():
            return candidate
        current = current.parent

    # 4. Fallback: CWD-based
    cwd_runtime = Path.cwd() / "runtime"
    cwd_runtime.mkdir(parents=True, exist_ok=True)
    return cwd_runtime


def get_leads_dir() -> Path:
    leads = get_runtime_dir() / "leads"
    leads.mkdir(parents=True, exist_ok=True)
    return leads


def list_sheet_files() -> list[dict]:
    """List all .csv and .xlsx files in the leads directory."""
    leads_dir = get_leads_dir()
    sheets = []
    for f in sorted(leads_dir.iterdir()):
        if f.suffix.lower() in (".csv", ".xlsx") and f.is_file():
            stat = f.stat()
            sheets.append({
                "name": f.name,
                "path": str(f.relative_to(get_runtime_dir())),
                "type": f.suffix.lstrip(".").lower(),
                "modified_at": stat.st_mtime,
                "size_bytes": stat.st_size,
            })
    return sheets
