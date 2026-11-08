from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import DbSession, ProjectDep
from app.core.logging import get_request_id
from app.schemas.common import ApiResponse
from app.schemas.llm_config import (
    LLMConfigRead,
    LLMConfigUpdate,
    LLMTestRequest,
    LLMTestResult,
)
from app.services.llm_config_service import LLMConfigService

router = APIRouter(prefix="/projects/{project_id}/llm-config", tags=["llm"])


@router.get("", response_model=ApiResponse[LLMConfigRead], summary="读取 LLM 配置")
def get_llm_config(project: ProjectDep, db: DbSession) -> ApiResponse[LLMConfigRead]:
    return ApiResponse(
        data=LLMConfigService.read(db, project.id),
        request_id=get_request_id(),
    )


@router.put("", response_model=ApiResponse[LLMConfigRead], summary="保存 LLM 配置")
def update_llm_config(
    payload: LLMConfigUpdate,
    project: ProjectDep,
    db: DbSession,
) -> ApiResponse[LLMConfigRead]:
    LLMConfigService.upsert(db, project.id, payload)
    return ApiResponse(
        data=LLMConfigService.read(db, project.id),
        request_id=get_request_id(),
    )


@router.post(
    "/test",
    response_model=ApiResponse[LLMTestResult],
    summary="测试 LLM 连接",
)
def test_llm_config(
    project: ProjectDep,
    db: DbSession,
    payload: LLMTestRequest | None = None,
) -> ApiResponse[LLMTestResult]:
    result = LLMConfigService.test(db, project.id, payload)
    return ApiResponse(
        data=LLMTestResult.model_validate(result),
        request_id=get_request_id(),
    )
