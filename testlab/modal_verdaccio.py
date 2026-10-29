"""The Bawabu test-lab registry: Verdaccio on Modal, password-locked, proxying the real npm.

Deploy from the repo root:
    uv run modal deploy testlab/modal_verdaccio.py

Needs the Modal secret `bawabu-verdaccio` (VERDACCIO_HTPASSWD). Published packages persist in the
`bawabu-verdaccio-data` volume. The registry is at https://amohntim123--bawabu-verdaccio.modal.run
and requires HTTP Basic auth (the VERDACCIO_* credentials in .env).
"""

import subprocess
import time
import urllib.request

import modal

VERDACCIO_VERSION = "6.10.5"  # needs Node >= 22
PORT = 4873

image = (
    modal.Image.from_registry("node:22-bookworm-slim", add_python="3.13")
    .run_commands(f"npm install -g verdaccio@{VERDACCIO_VERSION}")
    .add_local_file(__file__.replace("modal_verdaccio.py", "verdaccio/config.yaml"), "/app/config.yaml")
)
app = modal.App("bawabu-verdaccio", image=image)
data = modal.Volume.from_name("bawabu-verdaccio-data", create_if_missing=True)


@app.function(
    volumes={"/data": data},
    secrets=[modal.Secret.from_name("bawabu-verdaccio", required_keys=["VERDACCIO_HTPASSWD"])],
    timeout=3600,
    scaledown_window=300,
    min_containers=0,
)
@modal.concurrent(max_inputs=50)
@modal.web_server(PORT, startup_timeout=120)
def registry():
    import os

    os.makedirs("/data/storage", exist_ok=True)
    # Seed the single login from the secret (only if absent, so a later rotation is deliberate).
    if not os.path.exists("/data/htpasswd"):
        with open("/data/htpasswd", "w") as f:
            f.write(os.environ["VERDACCIO_HTPASSWD"].strip() + "\n")

    subprocess.Popen(["verdaccio", "--config", "/app/config.yaml", "--listen", f"0.0.0.0:{PORT}"])

    # Hold the function open until Verdaccio answers, so Modal doesn't route traffic too early.
    for _ in range(120):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/-/ping", timeout=2)
            return
        except Exception:
            time.sleep(1)
