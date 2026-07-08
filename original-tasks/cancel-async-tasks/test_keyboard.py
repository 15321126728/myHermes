"""Test with KeyboardInterrupt directly (simulated via a signal-like approach)."""
import asyncio
from run import run_tasks

cleanup_log = []

async def make_task(name, duration):
    async def task():
        print(f"  Task {name}: starting")
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
        make_task("X", 5.0), make_task("Y", 5.0),
        make_task("Z", 5.0),
    )

    async def normal_run():
        await run_tasks(list(t_tasks), 2)

    runner = asyncio.create_task(normal_run())
    await asyncio.sleep(0.3)

    # Raise KeyboardInterrupt inside the event loop
    print("\n  >>> Raising KeyboardInterrupt <<<\n")
    runner.cancel(msg="Simulated Ctrl+C via cancel")

    try:
        await runner
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("=> Runner raised exception (expected)")

    print(f"\nCleanup log: {cleanup_log}")
    assert "X" in cleanup_log, "Task X cleanup did NOT run!"
    assert "Y" in cleanup_log, "Task Y cleanup did NOT run!"
    print("PASS: KeyboardInterrupt-style test OK")

if __name__ == "__main__":
    asyncio.run(main())
