import asyncio
from collections.abc import Awaitable, Callable


async def run_tasks(
    tasks: list[Callable[[], Awaitable[None]]],
    max_concurrent: int,
) -> None:
    """Run async tasks with a concurrency limit.

    When a keyboard interrupt (Ctrl+C) or cancellation is received,
    tasks that have already started are allowed to finish (including
    any cleanup code in finally blocks or context managers), while
    tasks that haven't started yet are cancelled immediately.

    Args:
        tasks: List of zero-argument async callables to execute.
        max_concurrent: Maximum number of tasks running simultaneously.
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    cancel_requested = False

    # Tasks that have acquired the semaphore and are running their payload
    in_flight: set[asyncio.Task] = set()

    async def _worker(task_fn: Callable[[], Awaitable[None]]) -> None:
        nonlocal cancel_requested
        async with semaphore:
            if cancel_requested:
                # Semaphore acquired but a cancellation was requested
                # before this task started its payload — bail out so
                # someone waiting on the semaphore can get in instead
                return
            task = asyncio.current_task()
            in_flight.add(task)
            try:
                await task_fn()
            finally:
                in_flight.discard(task)

    pending = [asyncio.create_task(_worker(t)) for t in tasks]

    try:
        await asyncio.gather(*pending)
    except (KeyboardInterrupt, asyncio.CancelledError):
        cancel_requested = True

        # Cancel tasks that are still waiting for the semaphore
        # (they never entered the `async with semaphore:` body).
        for t in pending:
            if not t.done() and t not in in_flight:
                t.cancel()

        # Let the already-running tasks finish their payload (including
        # cleanup) before we return.
        if in_flight:
            await asyncio.gather(*in_flight, return_exceptions=True)

        # Re-raise so the caller is aware a cancellation occurred
        raise
