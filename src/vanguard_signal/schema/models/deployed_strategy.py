from __future__ import annotations

from typing import Any, Dict
import uuid

from sqlalchemy import String, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column

from vanguard_signal.schema.base import Base, TimestampMixin, AuditMixin


class DeployedStrategy(Base, TimestampMixin, AuditMixin):
    """ORM model for deployed strategies.

    This table stores a record for each deployment made through the API.
    """

    __tablename__ = "deployed_strategy"
    __table_args__ = {"comment": "Deployed trading strategies"}

    strategy_id: Mapped[str] = mapped_column(String(256), nullable=False, comment="Strategy identifier")
    name: Mapped[str] = mapped_column(String(256), nullable=False, comment="Deployment name")
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="deployed", comment="Deployment status")
    capital: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, comment="Allocated capital")
    performance: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict, comment="Performance metrics JSON")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "strategy_id": self.strategy_id,
            "name": self.name,
            "status": self.status,
            "capital": float(self.capital),
            "performance": self.performance or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
