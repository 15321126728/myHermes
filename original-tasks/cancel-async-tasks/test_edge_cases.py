"""Edge case tests for run_tasks."""
import asyncio
from run import run_tasks

async def make_task(name, duration=0.05):
    async def task():
        await asyncio.sleep(duration)
    return task

async def test_empty():
    print("Test 1: Empty task list")
    await run_tasks([], max_concurrent=5)
    print("  PASS")

async def test_all_at_once():
    print("Test 2: max_concurrent > len(tasks)")
    tasks = await asyncio.gather(*[make_task(chr(65+i)) for i in range(3)])
    await run_tasks(list(tasks), max_concurrent=10)
    print("  PASS")

async def test_sequential():
    print("Test 3: max_concurrent=1 (sequential)")
    order = []
    async def tracked(name):
        async def task():
            order.append(f"start_{name}")
            await asyncio.sleep(0.05)
            order.append(f"end_{name}")
        return task
    tasks = await asyncio.gather(tracked("A"), tracked("B"), tracked("C"))
    await run_tasks(list(tasks), max_concurrent=1)
    assert order == ["start_A", "end_A", "start_B", "end_B", "start_C", "end_C"], f"Bad order: {order}"
    print("  PASS")

async def test_single_task():
    print("Test 4: Single task")
    ran = False
    async def task():
        nonlocal ran
        ran = True
    await run_tasks([task], max_concurrent=5)
    assert ran
    print("  PASS")

async def test_concurrent_limit():
    print("Test 5: Concurrency doesn't exceed limit")
    max_seen = 0
    active = 0
    lock = asyncio.Lock()
    async def concurrency_task():
        nonlocal max_seen, active
        async with lock:
            active += 1
            max_seen = max(max_seen, active)
        await asyncio.sleep(0.1)
        async with lock:
            active -= 1
    tasks = [concurrency_task for _ in range(20)]
    await run_tasks(tasks, max_concurrent=4)
    assert max_seen <= 4, f"Max concurrency was {max_seen}, expected <= 4"
    print(f"  Max concurrent seen: {max_seen} <= 4. PASS")

async def main():
    await test_empty()
    await test_all_at_once()
    await test_sequential()
    await test_single_task()
    await test_concurrent_limit()
    print("\nAll edge case tests PASSED!")

if __name__ == "__main__":
    asyncio.run(main())
