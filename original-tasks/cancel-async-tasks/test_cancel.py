import asyncio
import time
from run import run_tasks

cleanup_log = []

async def make_task(name, duration):
    async def task():
        print(f"  Task {name}: starting (needs {duration}s)")
        try:
            await asyncio.sleep(duration)
        finally:
            cleanup_log.append(name)
            print(f"  Task {name}: cleanup ran!")
    return task

async def main():
    global cleanup_log
    cleanup_log.clear()

    t_tasks = await asyncio.gather(
        make_task("A", 3.0), make_task("B", 3.0),
        make_task("C", 3.0), make_task("D", 0.1),
        make_task("E", 0.1), make_task("F", 0.1),
    )

    print("Cancellation test (max_concurrent=2):")

    runner_task = asyncio.create_task(run_tasks(list(t_tasks), 2))

    # Cancel after 0.5s by cancelling the runner task
    await asyncio.sleep(0.5)
    print("\n  >>> Cancelling runner (simulating Ctrl+C) <<<\n")
    runner_task.cancel()

    # Wait for runner to catch the cancellation and let in-flight tasks finish
    try:
        await asyncio.wait_for(runner_task, timeout=5.0)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("=> Runner raised CancelledError (expected)")
    except BaseException as e:
        print(f"=> Runner raised: {type(e).__name__}: {e}")

    print(f"\nCleanup ran for tasks: {cleanup_log}")
    assert "A" in cleanup_log, "Task A cleanup did NOT run!"
    assert "B" in cleanup_log, "Task B cleanup did NOT run!"
    print("PASS: Cleanup preserved on cancellation")

if __name__ == "__main__":
    asyncio.run(main())
