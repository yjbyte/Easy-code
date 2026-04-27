"""
Agent Team - 多 Agent 协作模块

基于内存任务队列的 Agent 协作系统
"""
import asyncio
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(int, Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class Task:
    """任务"""
    task_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout: int = 300  # 超时时间（秒）
    max_retries: int = 3
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkerConfig:
    """Worker 配置"""
    worker_id: str
    name: str
    handler: Callable[[Task], Any]
    max_concurrent_tasks: int = 1
    auto_start: bool = True


class AgentTeam:
    """
    Agent Team - 多 Agent 协作

    使用内存队列实现，多个 Worker 从队列中取任务处理
    """

    def __init__(self):
        self._task_queue: asyncio.Queue[Task] = asyncio.Queue()
        self._workers: Dict[str, WorkerConfig] = {}
        self._tasks: Dict[str, Task] = {}
        self._worker_tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        self._lock = asyncio.Lock()

    def register_worker(self, config: WorkerConfig) -> None:
        """
        注册 Worker

        Args:
            config: Worker 配置
        """
        self._workers[config.worker_id] = config

    def unregister_worker(self, worker_id: str) -> bool:
        """
        注销 Worker

        Args:
            worker_id: Worker ID

        Returns:
            是否成功
        """
        if worker_id in self._workers:
            del self._workers[worker_id]
            return True
        return False

    async def submit_task(
        self,
        name: str,
        input_data: Dict[str, Any],
        description: str = "",
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: int = 300,
        metadata: Dict[str, Any] = None
    ) -> Task:
        """
        提交任务

        Args:
            name: 任务名称
            input_data: 输入数据
            description: 任务描述
            priority: 任务优先级
            timeout: 超时时间
            metadata: 元数据

        Returns:
            Task: 创建的任务
        """
        task = Task(
            name=name,
            description=description,
            input_data=input_data,
            priority=priority,
            timeout=timeout,
            metadata=metadata or {}
        )

        await self._task_queue.put(task)
        self._tasks[task.task_id] = task

        return task

    async def get_task_result(self, task_id: str, timeout: float = 30.0) -> Task:
        """
        获取任务结果（等待任务完成）

        Args:
            task_id: 任务 ID
            timeout: 等待超时时间

        Returns:
            Task: 完成的任务
        """
        start = asyncio.get_event_loop().time()

        while True:
            task = self._tasks.get(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")

            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return task

            if asyncio.get_event_loop().time() - start > timeout:
                raise TimeoutError(f"Wait for task {task_id} timeout")

            await asyncio.sleep(0.1)

    async def start(self) -> None:
        """启动 Agent Team"""
        async with self._lock:
            if self._running:
                return

            self._running = True

            # 启动所有 Worker
            for worker_id, config in self._workers.items():
                if config.auto_start:
                    worker_task = asyncio.create_task(
                        self._worker_loop(config)
                    )
                    self._worker_tasks[worker_id] = worker_task

    async def stop(self) -> None:
        """停止 Agent Team"""
        async with self._lock:
            if not self._running:
                return

            self._running = False

            # 取消所有 Worker 任务
            for worker_task in self._worker_tasks.values():
                worker_task.cancel()

            # 等待所有 Worker 完成
            await asyncio.gather(*self._worker_tasks.values(), return_exceptions=True)

            self._worker_tasks.clear()

    async def _worker_loop(self, config: WorkerConfig) -> None:
        """Worker 循环"""
        while self._running:
            try:
                # 从队列获取任务
                task = await asyncio.wait_for(
                    self._task_queue.get(),
                    timeout=1.0
                )

                # 处理任务
                await self._process_task(task, config)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Worker {config.worker_id} error: {e}")

    async def _process_task(self, task: Task, config: WorkerConfig) -> None:
        """处理单个任务"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()

        try:
            # 执行任务
            result = await asyncio.wait_for(
                config.handler(task),
                timeout=task.timeout
            )

            task.result = result
            task.status = TaskStatus.COMPLETED

        except asyncio.TimeoutError:
            task.status = TaskStatus.FAILED
            task.error = f"Task timeout after {task.timeout}s"

            # 重试逻辑
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                await self._task_queue.put(task)

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)

            # 重试逻辑
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                await self._task_queue.put(task)

        finally:
            task.completed_at = datetime.now()

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        task = self._tasks.get(task_id)
        return task.status if task else None

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None
    ) -> List[Task]:
        """列出任务"""
        tasks = list(self._tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]

        return tasks

    def get_worker_status(self) -> Dict[str, Dict[str, Any]]:
        """获取 Worker 状态"""
        status = {}

        for worker_id, config in self._workers.items():
            status[worker_id] = {
                "name": config.name,
                "max_concurrent_tasks": config.max_concurrent_tasks,
                "is_running": worker_id in self._worker_tasks
            }

        return status


# 全局实例
_global_team: Optional[AgentTeam] = None


def get_agent_team() -> AgentTeam:
    """获取全局 Agent Team"""
    global _global_team
    if _global_team is None:
        _global_team = AgentTeam()
    return _global_team
