"""Matrix Webhook app."""

import asyncio
import logging

from signal import SIGINT, SIGTERM
from aiohttp import web
from . import conf, handler, utils, encrypted_client

LOGGER = logging.getLogger("matrix_webhook.app")


async def main(event):
    """
    Launch main coroutine.

    matrix client login & start web server
    """
    LOGGER.info(f"Log in {conf.MATRIX_ID=} on {conf.MATRIX_URL=}")
    
    server = web.Server(handler.matrix_webhook)
    runner = web.ServerRunner(server)
    await runner.setup();

    LOGGER.info(f"Binding on {conf.SERVER_ADDRESS=}")
    site = web.TCPSite(runner, *conf.SERVER_ADDRESS)
    await site.start();

    task_a = asyncio.create_task(encrypted_client.run(utils.CLIENT))
    task_b = asyncio.create_task(event.wait())

    await asyncio.gather(
        task_a,
        task_b
    )

    # Cleanup
    await runner.cleanup()
    await utils.CLIENT.close()


def terminate(event, signal):
    """Close handling stuff."""
    event.set()
    asyncio.get_event_loop().remove_signal_handler(signal)


def run():
    """Launch everything."""
    LOGGER.info("Starting...")
    loop = asyncio.get_event_loop()
    event = asyncio.Event()

    for sig in (SIGINT, SIGTERM):
        loop.add_signal_handler(sig, terminate, event, sig)

    loop.run_until_complete(main(event))

    LOGGER.info("Closing...")
    loop.close()
