from __future__ import annotations

import logging

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.api.deps import get_pair_scanner
from app.domain.market.symbols import SUPPORTED_SYMBOLS, list_symbols
from app.domain.scanner.pair_scanner import PairScanner
from app.schemas.scanner import ScanResultOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scanner", tags=["scanner"])

MAX_SYMBOLS_PER_SCAN = 25


class ScanRequest(BaseModel):
    symbols: list[str] | None = Field(
        default=None, description="Symbols to scan; defaults to all supported symbols."
    )
    min_quality_score: int = Field(default=0, ge=0, le=100)

    @field_validator("symbols")
    @classmethod
    def _validate_symbols(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        if len(value) > MAX_SYMBOLS_PER_SCAN:
            raise ValueError(f"Cannot scan more than {MAX_SYMBOLS_PER_SCAN} symbols at once.")
        normalized = [s.strip().upper() for s in value]
        unknown = [s for s in normalized if s not in SUPPORTED_SYMBOLS]
        if unknown:
            raise ValueError(f"Unsupported symbols: {', '.join(unknown)}")
        return normalized


@router.post("/run", response_model=ScanResultOut)
def run_scan(
    request: ScanRequest = Body(default_factory=ScanRequest),
    scanner: PairScanner = Depends(get_pair_scanner),
) -> ScanResultOut:
    symbols = request.symbols or [s.name for s in list_symbols()]
    try:
        result = scanner.scan(symbols)
    except Exception:
        logger.exception("Scan failed for symbols=%s", symbols)
        raise HTTPException(status_code=502, detail="The market scan could not be completed.") from None

    if request.min_quality_score:
        result = ScanResultOut.from_domain(result)
        result.candidates = [c for c in result.candidates if c.quality_score >= request.min_quality_score]
        return result

    return ScanResultOut.from_domain(result)
