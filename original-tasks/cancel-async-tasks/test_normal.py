"""Test normal operation: tasks run with proper concurrency limiting."""
import asyncio
import time
from run import run_tasks

async def make_task(name: str, duration: float):
    async def task():
        print(f"  Task {name}: starting at t={time.monotonic():.1f}")
        await asyncio.sleep(duration)
        print(f"  Task {name}: finished at t={time.monotonic():.1f}")
    return task

async def main():
    tasks = await asyncio.gather(
        make_task("A", 0.5),
        make_task("B", 0.5),
        make_task("C", 0.5),
        make_task("D", 0.5),
    )
    print("Normal run (max_concurrent=2, 4 tasks x 0.5s each):")
    t0 = time.monotonic()
    await run_tasks(list(tasks), max_concurrent=2)
    elapsed = time.monotonic() - t0
    print(f"Completed in {elapsed:.1f}s (expected ~1.0s for 2+2 serial)")
    assert 0.8 < elapsed < 1.5, f"Unexpected duration: {elapsed:.1f}s"
    print("PASS: Normal concurrency test OK")

asyncio.run(main())
