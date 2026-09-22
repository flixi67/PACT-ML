"""Phase 1 exit test: prove the Modal umbilical — remote GPU visible from Hermie.

Run:  modal run modal/hello_gpu.py
"""
import subprocess

import modal

app = modal.App("pact-ml-hello-gpu")

image = modal.Image.debian_slim().pip_install("torch", "transformers")


@app.function(gpu="L4", image=image, timeout=300)
def hello_gpu() -> dict:
    import torch

    smi = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
    return {
        "cuda_available": torch.cuda.is_available(),
        "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "nvidia_smi_head": smi.stdout[:400],
    }


if __name__ == "__main__":
    with app.run():
        result = hello_gpu.remote()
        print(result)
