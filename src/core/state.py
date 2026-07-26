from datetime import datetime, timezone

from src.core.models import ArbitrageOpportunity


class PollCache:
    """Stores the last fetched VOOI opportunities and their fetch timestamp."""

    def __init__(self) -> None:
        self._opportunities: list[ArbitrageOpportunity] = []
        self._updated_at: datetime | None = None

    def update(self, opportunities: list[ArbitrageOpportunity]) -> None:
        self._opportunities = opportunities
        self._updated_at = datetime.now(timezone.utc)

    def get_opportunities(self) -> list[ArbitrageOpportunity]:
        return list(self._opportunities)

    def is_stale(self, max_age_s: float = 30.0) -> bool:
        if self._updated_at is None:
            return True
        age = (datetime.now(timezone.utc) - self._updated_at).total_seconds()
        return age > max_age_s

    def last_updated(self) -> datetime | None:
        return self._updated_at
