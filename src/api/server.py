import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from loguru import logger

from src.api.routes import router
from src.api.schemas import build_opportunities_response
from src.api.ws import ConnectionManager
from src.core.app import App
from src.core.models import ValidatedOpportunity


def create_api(app: App) -> FastAPI:
    ws_manager = ConnectionManager()
    update_queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=1)

    async def _enqueue_results(validated: list[ValidatedOpportunity]) -> None:
        ts = app.last_updated_at.isoformat() if app.last_updated_at is not None else None
        payload = build_opportunities_response(validated, updated_at=ts).model_dump()
        if update_queue.full():
            with suppress(asyncio.QueueEmpty):
                update_queue.get_nowait()
                update_queue.task_done()
        with suppress(asyncio.QueueFull):
            update_queue.put_nowait(payload)

    async def _broadcast_loop() -> None:
        while True:
            payload = await update_queue.get()
            try:
                await ws_manager.broadcast(payload)
            finally:
                update_queue.task_done()

    @asynccontextmanager
    async def lifespan(fastapi_app: FastAPI):
        prev_console_output = app._console_output
        prev_on_update = app._on_update
        app._console_output = False
        app._on_update = _enqueue_results
        broadcast_task = asyncio.create_task(_broadcast_loop())
        poll_task = asyncio.create_task(app.run_loop(shutdown_on_exit=False))
        logger.info("API server started, polling loop running in background")
        try:
            yield
        finally:
            poll_task.cancel()
            broadcast_task.cancel()
            try:
                await poll_task
            except asyncio.CancelledError:
                pass
            try:
                await broadcast_task
            except asyncio.CancelledError:
                pass
            app._console_output = prev_console_output
            app._on_update = prev_on_update
            await app.shutdown()

    fastapi_app = FastAPI(
        title="Arbitrage Screener API",
        version="0.3.0",
        lifespan=lifespan,
    )
    fastapi_app.state.screener_app = app
    fastapi_app.state.ws_manager = ws_manager
    fastapi_app.include_router(router)

    @fastapi_app.websocket("/ws/opportunities")
    async def ws_opportunities(ws: WebSocket) -> None:
        await ws_manager.connect(ws)
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            await ws_manager.disconnect(ws)

    return fastapi_app
