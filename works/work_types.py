import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from core.config import settings


@dataclass(frozen=True)
class WorkTypeConfig:
    type_id: str
    name: str
    questions: dict[str, str | None]


def config_path() -> Path:
    return Path(settings.WORK_TYPES_PATH)


def parse_work_types(data: dict[str, Any]) -> dict[str, WorkTypeConfig]:
    result: dict[str, WorkTypeConfig] = {}
    for type_id, entry in data.items():
        result[type_id] = WorkTypeConfig(
            type_id=type_id,
            name=entry.get("name", ""),
            questions=entry.get("questions", {}),
        )
    return result


@lru_cache
def load_work_types() -> dict[str, WorkTypeConfig]:
    path = config_path()
    if not path.is_file():
        raise RuntimeError(f"Файл типов работ не найден: {path}")

    with path.open(encoding="utf-8") as file:
        data = json.load(file)

    return parse_work_types(data)


def reload_work_types() -> dict[str, WorkTypeConfig]:
    load_work_types.cache_clear()
    return load_work_types()


def list_work_types() -> list[WorkTypeConfig]:
    return list(load_work_types().values())


def get_work_type(type_id: str) -> WorkTypeConfig:
    work_type = load_work_types().get(type_id)
    if work_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неизвестный тип работы: {type_id}",
        )
    return work_type


def has_test_part(questions: dict[str, str | None]) -> bool:
    return any(v for v in questions.values())


def questions_to_json(questions: dict[str, str | None]) -> str:
    return json.dumps(questions, ensure_ascii=False)


def questions_from_json(raw: str) -> dict[str, str | None]:
    return json.loads(raw)
