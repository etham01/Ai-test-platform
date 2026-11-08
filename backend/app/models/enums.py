from __future__ import annotations

from enum import StrEnum


class ProjectStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class TaskType(StrEnum):
    SCAN = "scan"
    EXPLORE = "explore"
    WORKFLOW_ANALYSIS = "workflow_analysis"
    CASE_GENERATION = "case_generation"
    SCRIPT_GENERATION = "script_generation"
    EXECUTION = "execution"
    FAILURE_ANALYSIS = "failure_analysis"
    DEBUG = "debug"


class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
