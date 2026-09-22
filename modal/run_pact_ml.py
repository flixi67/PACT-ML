"""Modal runner for the PACT-ML model stage (module 06 rework).

Builds a pinned image from requirements.txt, bundles the repo (add_local_dir,
copy=False -> mounted at container startup, so local edits are picked up), and
runs module scripts on an L4 GPU. Output artifacts are written to a persistent
Modal Volume (`pact-ml-artifacts`) mounted at /artifacts, because the repo mount
does not sync back to local.

Usage:
  modal run modal/run_pact_ml.py --cmd "python modules/07_location_masking.py ..."
  modal run modal/run_pact_ml.py --cmd "python modules/06_roberta_model.py ..."

After a run, fetch artifacts to the local repo with:
  modal volume get pact-ml-artifacts <volume path> <local dest>
"""
from __future__ import annotations

import os

from modal import App, Image, Volume, is_local

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_LOCAL = os.path.dirname(HERE)  # repo root on this machine
REPO = "/root/pact-ml"

app = App("pact-ml-model-stage")
vol = Volume.from_name("pact-ml-artifacts", create_if_missing=True)

def _read_reqs() -> list[str]:
    candidates = [
        os.path.join(ROOT_LOCAL, "requirements.txt"),   # local build
        "/root/pact-ml/requirements.txt",                # in-container (repo mount)
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "requirements.txt"),
    ]
    for p in candidates:
        try:
            with open(p) as f:
                return [l.strip() for l in f
                        if l.strip() and not l.strip().startswith("#")]
        except FileNotFoundError:
            continue
    raise FileNotFoundError("requirements.txt not found")


REQS = _read_reqs()

IGNORE = [".git", "__pycache__", ".venv", ".venv_test", "wandb", "logs",
          "PACT-ML Report_files", "PACT-ML-Report_files", ".ipynb_checkpoints",
          "modal/__pycache__"]

image = (
    Image.debian_slim()
    .apt_install("git")
    .pip_install(*REQS)
    .add_local_dir(ROOT_LOCAL if is_local() else REPO,
                   remote_path=REPO, copy=False, ignore=IGNORE)
)


@app.function(image=image, gpu="L4", timeout=7200, volumes={"/artifacts": vol})
def run(cmd: str) -> str:
    import subprocess

    env = dict(os.environ)
    env["PYTHONPATH"] = f"{REPO}/modules"
    env["HF_HOME"] = "/root/hf"
    env["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
    proc = subprocess.run(f"cd {REPO} && {cmd}", shell=True,
                          capture_output=True, text=True, env=env, cwd=REPO)
    print("=== STDOUT (tail) ===")
    print((proc.stdout or "")[-20000:])
    if proc.returncode != 0:
        print("=== STDERR (tail) ===")
        print((proc.stderr or "")[-20000:])
    print(f"=== exit code: {proc.returncode} ===")
    return str(proc.returncode)


@app.local_entrypoint()
def main(cmd: str):
    run.remote(cmd)
