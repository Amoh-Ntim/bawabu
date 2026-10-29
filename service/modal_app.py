"""Deploys the Bawabu service on Modal. From the repo root:

    uv run modal deploy service/modal_app.py

Needs the Modal secret `bawabu-supabase` (SUPABASE_URL, SUPABASE_SECRET_KEY) for the verdict cache.
"""

import modal

image = (
    modal.Image.debian_slim(python_version="3.13")
    .pip_install("fastapi>=0.115", "httpx>=0.27")
    .add_local_python_source("bawabu_service")
)
app = modal.App("bawabu", image=image)


@app.function(
    secrets=[modal.Secret.from_name("bawabu-supabase", required_keys=["SUPABASE_URL", "SUPABASE_SECRET_KEY"])],
    timeout=180,
    scaledown_window=300,
)
@modal.concurrent(max_inputs=100)
@modal.asgi_app(label="bawabu")
def web():
    from bawabu_service.api import create_app

    return create_app()
