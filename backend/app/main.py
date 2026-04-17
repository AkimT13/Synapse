"""
Entry point for running the Synapse API.

Starts uvicorn programmatically so we can print the banner *after* the
server has finished its startup phase — it reads more naturally under
the ``Uvicorn running on …`` line than before it. For dev reload use
``uvicorn api.app:app --reload`` directly; this script is the clean
one-shot runner.
"""
from __future__ import annotations

import asyncio

import uvicorn

import os

HOST = os.environ.get("SYNAPSE_HOST", "127.0.0.1")
PORT = int(os.environ.get("SYNAPSE_PORT", "8000"))

BANNER = r"""
     _______     ___   _          _____   _____ ______
    / ____\ \   / / \ | |   /\   |  __ \ / ____|  ____|
   | (___  \ \_/ /|  \| |  /  \  | |__) | (___ | |__
    \___ \  \   / | . ` | / /\ \ |  ___/ \___ \|  __|
    ____) |  | |  | |\  |/ ____ \| |     ____) | |____
   |_____/   |_|  |_| \_/_/    \_\_|    |_____/|______|
"""


def _print_banner() -> None:
    print("\nAkim Tarasov & Aneesh Kumar Present:")
    print(BANNER)
    print("For the Actian VectorAI DB Hackathon!")
    print(f"API listening on http://{HOST}:{PORT}\n")


async def _serve() -> None:
    config = uvicorn.Config(
        "api.app:app",
        host=HOST,
        port=PORT,
        log_level="info",
    )
    server = uvicorn.Server(config)

    serve_task = asyncio.create_task(server.serve())

    # Wait for uvicorn to finish its startup sequence so our banner
    # lands after its own "Uvicorn running on …" log line. A tight
    # poll is fine — startup takes a few hundred ms at most.
    while not server.started and not serve_task.done():
        await asyncio.sleep(0.05)

    if server.started:
        _print_banner()

    await serve_task


def main() -> None:
    try:
        asyncio.run(_serve())
    except KeyboardInterrupt:
        # uvicorn already handles Ctrl-C gracefully; swallow the
        # propagated exception so the banner isn't buried under a
        # stack trace on exit.
        pass


if __name__ == "__main__":
    main()
