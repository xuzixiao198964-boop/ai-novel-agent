# -*- coding: utf-8 -*-
"""Agent 基类：进度输出、日志输出、异常处理"""
from abc import ABC, abstractmethod
from typing import Optional, Any
from app.core.state import (
    set_agent_progress,
    append_agent_log,
    AgentStatus,
)


class BaseAgent(ABC):
    """所有 Agent 的基类，统一进度与日志上报"""

    name: str = "BaseAgent"

    def __init__(self, task_id: str):
        self.task_id = task_id

    def _set_progress(self, status: str, progress_percent: float = 0, message: str = "", **extra: Any) -> None:
        set_agent_progress(self.task_id, self.name, status, progress_percent, message, extra or None)

    def _log(self, level: str, message: str, detail: Optional[dict] = None) -> None:
        append_agent_log(self.task_id, self.name, level, message, detail)

    def _set_running(self, progress_percent: float = 0, message: str = "", **extra: Any) -> None:
        self._set_progress(AgentStatus.RUNNING.value, progress_percent, message, **extra)

    def _set_completed(self, message: str = "完成", **extra: Any) -> None:
        self._set_progress(AgentStatus.COMPLETED.value, 100.0, message, **extra)

    def _set_failed(self, message: str, detail: Optional[dict] = None) -> None:
        self._set_progress(AgentStatus.FAILED.value, 0, message)
        self._log("error", message, detail)

    @abstractmethod
    def run(self) -> None:
        """执行 Agent 主流程。内部应调用 _set_* 与 _log 上报进度与日志。"""
        pass
