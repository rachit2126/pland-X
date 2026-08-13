from typing import Optional
from datetime import datetime, date
from .models import ProgressMetric


def _parse_iso_date(dt_str: Optional[str]) -> Optional[date]:
    if not dt_str:
        return None
    try:
        parts = [int(p) for p in dt_str.split("T")[0].split("-")]
        return date(parts[0], parts[1], parts[2])
    except Exception:
        return None


def calculate_progress_metric(
    start_date: Optional[str],
    finish_date: Optional[str],
    actual_percent: float,
    is_milestone: bool = False,
    as_of_date: Optional[date] = None
) -> ProgressMetric:
    """
    Calculates planned progress percentage vs actual progress percentage as of reference date,
    returns variance, delay flag, and estimated delay in days.
    """
    s_dt = _parse_iso_date(start_date)
    f_dt = _parse_iso_date(finish_date)

    if as_of_date is None:
        # Default reference date for calculations
        as_of_date = date.today()

    planned = 0.0

    if s_dt and f_dt:
        if as_of_date < s_dt:
            planned = 0.0
        elif as_of_date >= f_dt:
            planned = 100.0
        else:
            total_days = (f_dt - s_dt).days or 1
            elapsed_days = (as_of_date - s_dt).days
            planned = min(100.0, max(0.0, (elapsed_days / total_days) * 100.0))
    else:
        # If dates missing, assume planned = actual
        planned = actual_percent

    variance = round(actual_percent - planned, 2)
    is_delayed = variance < -5.0  # Flag delayed if more than 5% behind planned baseline

    delay_days = 0.0
    if is_delayed and s_dt and f_dt:
        total_days = (f_dt - s_dt).days or 1
        delay_days = round((abs(variance) / 100.0) * total_days, 1)

    return ProgressMetric(
        plannedPercent=round(planned, 2),
        actualPercent=round(actual_percent, 2),
        variance=variance,
        isDelayed=is_delayed,
        delayDays=delay_days,
    )
