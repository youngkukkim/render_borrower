from __future__ import annotations

import importlib
import logging
import math
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
import json
from typing import Any, Dict, List, Tuple

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder

logger = logging.getLogger(__name__)


class NTPDParserUnavailable(Exception):
    """Raised when the ntpd extractor modules cannot be imported or configured."""


@lru_cache(maxsize=1)
def _load_ntpd_modules():
    try:
        labels_module = importlib.import_module(settings.NTPD_LABELS_MODULE)
        extractor_module = importlib.import_module(settings.NTPD_EXTRACTOR_MODULE)
    except ModuleNotFoundError as exc:
        logger.exception("Failed to import ntpd modules: %s", exc)
        raise NTPDParserUnavailable(
            "ntpd extractor 모듈을 불러올 수 없습니다. 경로나 패키지 설정을 확인하세요."
        ) from exc
    return labels_module, extractor_module


def _stringify_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    return str(value)


def _clean_for_json(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _clean_for_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_clean_for_json(v) for v in value]
    return value


def _json_safe(value: Any, default: Any) -> Any:
    """
    Convert nested structures into JSON-serializable equivalents.
    실패 시에는 주어진 default(dict/list 등)를 반환한다.
    """
    try:
        cleaned = _clean_for_json(value)
        return json.loads(json.dumps(cleaned, cls=DjangoJSONEncoder, allow_nan=False))
    except (TypeError, ValueError) as exc:
        logger.warning("ntpd parsed payload JSON 직렬화 실패: %s", exc)
        return default


def parse_with_ntpd(xlsx_path: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Parse the borrower Excel using the ntpd extractor.

    Returns:
        - parsed: nested dict keyed by sheet names (원본 구조)
        - records: [{"key_path": [...], "label_path": [...], "value": "..."} ...]
    """
    labels_module, extractor_module = _load_ntpd_modules()
    sheet_specs = getattr(labels_module, "SHEET_SPECS", None)
    if not sheet_specs:
        raise NTPDParserUnavailable("ntpd.labels 모듈에 SHEET_SPECS 정의가 필요합니다.")

    parsed, records = extractor_module.extract_workbook(
        xlsx_path,
        sheet_specs,
        values_only=True,
    )
    parsed = _json_safe(parsed or {}, default={})
    normalized_records: List[Dict[str, Any]] = []
    for key_path, label_path, value in records:
        normalized_records.append(
            {
                "key_path": list(key_path),
                "label_path": list(label_path),
                "value": _stringify_value(value),
            }
        )
    normalized_records = _json_safe(normalized_records, default=[])
    return parsed, normalized_records


def get_ntpd_sheet_specs() -> Dict[str, List[Dict[str, Any]]]:
    labels_module, _ = _load_ntpd_modules()
    return getattr(labels_module, "SHEET_SPECS", {})
