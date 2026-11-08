from fastapi import APIRouter

from app.api.v1.endpoints import (
    ai,
    executions,
    health,
    llm_configs,
    pages,
    projects,
    requirements,
    scripts,
    tasks,
    test_cases,
    workflows,
)

router = APIRouter()
router.include_router(health.router)
router.include_router(projects.router)
router.include_router(pages.router)
router.include_router(llm_configs.router)
router.include_router(requirements.router)
router.include_router(workflows.router)
router.include_router(test_cases.router)
router.include_router(ai.router)
router.include_router(scripts.router)
router.include_router(executions.router)
router.include_router(tasks.router)
