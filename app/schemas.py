from datetime import date

from pydantic import BaseModel


class PriceData(BaseModel):
    """Response skema untuk data harga saham."""

    ticker: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


class IndicatorResult(BaseModel):
    """Response skema untuk kalkulasi indikator teknikal."""

    ticker: str
    indicator: str
    value: float | None = None
    signal: str | None = None
