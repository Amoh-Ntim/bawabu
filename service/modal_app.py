"""Deploys the Bawabu service on Modal. From the repo root:

    uv run modal deploy service/modal_app.py

Two functions:
  * `web`: the HTTP API the CLI calls (/check, /health, /investigations/{id}).
  * `investigate`: the deep check for a suspicious package (diff + sandbox + Muse Spark). /check starts it with
    .spawn() and waits for its verdict; it keeps running if /check gives up waiting, so a retry finds the result.

Secrets (created by hand, never in the repo):
  * `bawabu-supabase`: SUPABASE_URL, SUPABASE_SECRET_KEY (verdict cache, investigations, events).
  * `bawabu-investigator`: META_API_KEY (Muse Spark), LAB_REGISTRY_URL + LAB_REGISTRY_AUTH (the test lab's
    Verdaccio and its HTTP Basic login, so the service can read the private registry).
  * `bawabu-baseten`: BASETEN_API_KEY (Muse Spark Open: the screener and the open-weights investigator).
"""

import os
from pathlib import Path

import modal

SANDBOX_PACKAGE = Path(__file__).resolve().parents[1] / "sandbox" / "bawabu_sandbox"
SPARK_URL = "https://api.meta.ai/v1"
SPARK_MODEL = "muse-spark-1.3"
SPARK_EFFORT = "low"
# Muse Spark Open, Meta's open-weights model, served by Baseten: the screener, and the investigator in open-weights mode.
OPEN_URL = "https://inference.baseten.co/v1"
OPEN_MODEL = "meta-models/muse-spark-open-1026"

image = (
    modal.Image.debian_slim(python_version="3.13")
    .pip_install("fastapi>=0.115", "httpx>=0.27", "packaging>=24", "semantic-version>=2.10", "openai>=1.40")
    .add_local_python_source("bawabu_service")
    # The sandbox runner, with the files it puts into each sandbox (sink.py, dnsshim.c).
    .add_local_dir(SANDBOX_PACKAGE, "/root/bawabu_sandbox", ignore=["__pycache__"])
)
app = modal.App("bawabu", image=image)
secrets = [
    modal.Secret.from_name("bawabu-supabase", required_keys=["SUPABASE_URL", "SUPABASE_SECRET_KEY"]),
    modal.Secret.from_name("bawabu-investigator", required_keys=["META_API_KEY", "LAB_REGISTRY_URL", "LAB_REGISTRY_AUTH"]),
    modal.Secret.from_name("bawabu-baseten", required_keys=["BASETEN_API_KEY"]),
]


@app.function(secrets=secrets, timeout=600)
async def investigate(inv_id: str, payload: dict) -> dict:
    from openai import OpenAI

    from bawabu_sandbox.runner import investigate as sandbox_run
    from bawabu_service import investigations
    from bawabu_service.cache import cache_from_env
    from bawabu_service.net import new_client
    from bawabu_service.verdicts import ENGINE

    def sandbox(name: str, version: str, registry_url: str | None, auth: str | None, env: dict | None, date: str | None) -> dict:
        return sandbox_run(name, version, registry=registry_url, registry_auth=auth, env=env, fake_date=date).report()

    if payload.get("open_weights"):
        spark, model = OpenAI(base_url=OPEN_URL, api_key=os.environ["BASETEN_API_KEY"], timeout=120), OPEN_MODEL
    else:
        spark, model = OpenAI(base_url=SPARK_URL, api_key=os.environ["META_API_KEY"], timeout=120), SPARK_MODEL
    async with new_client() as http:
        return await investigations.run(inv_id, payload, store=investigations.store_from_env(), cache=cache_from_env(),
                                        http=http, spark=spark, model=model, sandbox=sandbox, engine=ENGINE,
                                        effort=SPARK_EFFORT)


@app.function(secrets=secrets, timeout=180, scaledown_window=300)
@modal.concurrent(max_inputs=100)
@modal.asgi_app(label="bawabu")
def web():
    from openai import OpenAI

    from bawabu_service.api import create_app
    from bawabu_service.investigations import Investigations, store_from_env
    from bawabu_service.screener import Screener

    async def spawn(inv_id: str, payload: dict) -> None:
        await investigate.spawn.aio(inv_id, payload)

    screener = Screener(OpenAI(base_url=OPEN_URL, api_key=os.environ["BASETEN_API_KEY"], timeout=30), OPEN_MODEL)
    return create_app(investigations=Investigations(store_from_env(), spawn), screener=screener)
