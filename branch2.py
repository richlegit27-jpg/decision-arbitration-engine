import asyncio

async def branch1_task1():
    print("Branch1: Task1 started")
    await asyncio.sleep(1)
    print("Branch1: Task1 completed")

async def branch1_task2():
    print("Branch1: Task2 started")
    await asyncio.sleep(2)
    print("Branch1: Task2 completed")

async def branch2_task1():
    print("Branch2: Task1 started")
    await asyncio.sleep(1)
    print("Branch2: Task1 completed")

async def branch2_task2():
    print("Branch2: Task2 started, waiting for Task1 completion")
    await branch2_task1()
    print("Branch2: Task2 continuing after Task1 completion")
    await asyncio.sleep(1)
    print("Branch2: Task2 completed")

async def branch2_task3():
    print("Branch2: Task3 started, depends on Task2")
    await branch2_task2()
    print("Branch2: Task3 continuing after Task2 completion")
    await asyncio.sleep(1)
    print("Branch2: Task3 completed")

async def branch2():
    await branch2_task3()

async def branch1():
    await branch1_task1()
    await branch1_task2()

async def main():
    await asyncio.gather(
        branch1(),
        branch2()
    )

if __name__ == "__main__":
    asyncio.run(main())
