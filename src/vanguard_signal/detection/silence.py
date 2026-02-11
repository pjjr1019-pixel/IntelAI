"""Alert silence/snooze service — temporarily suppress alert notifications."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.schema.database import get_async_session
from vanguard_signal.schema.models.alert import AlertSilence

logger = logging.getLogger(__name__)


class AlertSilenceService:
    """
    Manages alert silencing rules to temporarily suppress notifications.
    Supports individual alert silencing, entity pattern matching, and global silencing.
    """

    async def silence_alert(
        self,
        alert_id: str | None = None,
        entity_pattern: str | None = None,
        duration_minutes: int | None = None,
        reason: str | None = None,
        silenced_by: str = "system",
        silence_type: str = "alert",
        session: AsyncSession | None = None,
    ) -> str:
        """
        Create a new silence rule.

        Args:
            alert_id: Specific alert ID to silence
            entity_pattern: Regex pattern for entity-based silencing
            duration_minutes: How long to silence (None = indefinite)
            reason: Reason for silencing
            silenced_by: User/system that created the silence
            silence_type: 'alert', 'entity', or 'global'
            session: Optional session to use

        Returns:
            ID of the created silence rule
        """
        if session is None:
            async with get_async_session() as session:
                return await self._create_silence(
                    alert_id, entity_pattern, duration_minutes, reason,
                    silenced_by, silence_type, session
                )
        else:
            return await self._create_silence(
                alert_id, entity_pattern, duration_minutes, reason,
                silenced_by, silence_type, session
            )

    async def _create_silence(
        self,
        alert_id: str | None,
        entity_pattern: str | None,
        duration_minutes: int | None,
        reason: str | None,
        silenced_by: str,
        silence_type: str,
        session: AsyncSession,
    ) -> str:
        """Internal method to create silence rule."""
        expires_at = None
        if duration_minutes:
            expires_at = datetime.utcnow() + timedelta(minutes=duration_minutes)

        silence = AlertSilence(
            alert_id=alert_id,
            entity_pattern=entity_pattern,
            silenced_by=silenced_by,
            reason=reason,
            silence_type=silence_type,
            duration_minutes=duration_minutes,
            expires_at=expires_at,
            is_active=True,
        )

        session.add(silence)
        await session.flush()

        logger.info(
            f"Alert silence created: type={silence_type}, alert_id={alert_id}, "
            f"pattern={entity_pattern}, duration={duration_minutes}min, by={silenced_by}"
        )

        return str(silence.id)

    async def unsilence(
        self,
        silence_id: str,
        session: AsyncSession | None = None,
    ) -> bool:
        """
        Deactivate a silence rule.

        Returns:
            True if silence was found and deactivated, False otherwise
        """
        if session is None:
            async with get_async_session() as session:
                return await self._unsilence(silence_id, session)
        else:
            return await self._unsilence(silence_id, session)

    async def _unsilence(self, silence_id: str, session: AsyncSession) -> bool:
        """Internal method to deactivate silence rule."""
        stmt = select(AlertSilence).where(AlertSilence.id == silence_id)
        result = await session.execute(stmt)
        silence = result.scalar_one_or_none()

        if silence and silence.is_active:
            silence.is_active = False
            await session.flush()
            logger.info(f"Alert silence deactivated: {silence_id}")
            return True

        return False

    async def is_alert_silenced(
        self,
        alert_id: str | None = None,
        entity: str | None = None,
        session: AsyncSession | None = None,
    ) -> tuple[bool, str | None]:
        """
        Check if an alert should be silenced.

        Args:
            alert_id: Specific alert ID to check
            entity: Entity name to check against patterns

        Returns:
            (is_silenced, reason) tuple
        """
        if session is None:
            async with get_async_session() as session:
                return await self._check_silenced(alert_id, entity, session)
        else:
            return await self._check_silenced(alert_id, entity, session)

    async def _check_silenced(
        self,
        alert_id: str | None,
        entity: str | None,
        session: AsyncSession,
    ) -> tuple[bool, str | None]:
        """Internal method to check if alert is silenced."""
        now = datetime.utcnow()

        # Clean up expired silences
        await self._cleanup_expired_silences(session)

        # Check for active silences
        conditions = [AlertSilence.is_active == True]

        # Specific alert silence
        if alert_id:
            conditions.append(
                or_(
                    AlertSilence.alert_id == alert_id,
                    AlertSilence.silence_type == "global"
                )
            )

        # Entity pattern matching
        if entity:
            # Check for global silences or pattern matches
            pattern_conditions = [AlertSilence.silence_type == "global"]
            if alert_id:
                pattern_conditions.append(AlertSilence.alert_id == alert_id)

            # Add pattern matching conditions
            entity_silences = select(AlertSilence).where(
                and_(
                    AlertSilence.is_active == True,
                    AlertSilence.silence_type == "entity",
                    AlertSilence.entity_pattern.isnot(None)
                )
            )
            entity_result = await session.execute(entity_silences)
            for silence in entity_result.scalars():
                if silence.entity_pattern and re.search(silence.entity_pattern, entity, re.IGNORECASE):
                    return True, f"Entity pattern match: {silence.entity_pattern}"

            conditions.append(or_(*pattern_conditions))

        stmt = select(AlertSilence).where(and_(*conditions))
        result = await session.execute(stmt)
        silence = result.scalar_one_or_none()

        if silence:
            reason = silence.reason or f"Silenced by {silence.silenced_by} ({silence.silence_type})"
            return True, reason

        return False, None

    async def _cleanup_expired_silences(self, session: AsyncSession) -> None:
        """Deactivate expired silence rules."""
        now = datetime.utcnow()

        stmt = select(AlertSilence).where(
            and_(
                AlertSilence.is_active == True,
                AlertSilence.expires_at.isnot(None),
                AlertSilence.expires_at <= now
            )
        )

        result = await session.execute(stmt)
        expired_silences = result.scalars().all()

        for silence in expired_silences:
            silence.is_active = False
            logger.info(f"Alert silence expired: {silence.id}")

        if expired_silences:
            await session.flush()

    async def list_active_silences(self, session: AsyncSession | None = None) -> list[dict[str, Any]]:
        """Get all active silence rules."""
        if session is None:
            async with get_async_session() as session:
                return await self._list_active_silences(session)
        else:
            return await self._list_active_silences(session)

    async def _list_active_silences(self, session: AsyncSession) -> list[dict[str, Any]]:
        """Internal method to list active silences."""
        # Clean up expired first
        await self._cleanup_expired_silences(session)

        stmt = select(AlertSilence).where(AlertSilence.is_active == True).order_by(AlertSilence.created_at.desc())
        result = await session.execute(stmt)
        silences = result.scalars().all()

        return [
            {
                "id": str(s.id),
                "alert_id": str(s.alert_id) if s.alert_id else None,
                "entity_pattern": s.entity_pattern,
                "silenced_by": s.silenced_by,
                "reason": s.reason,
                "silence_type": s.silence_type,
                "duration_minutes": s.duration_minutes,
                "expires_at": s.expires_at.isoformat() if s.expires_at else None,
                "created_at": s.created_at.isoformat(),
            }
            for s in silences
        ]


# Global service instance
_silence_service: AlertSilenceService | None = None


def get_silence_service() -> AlertSilenceService:
    """Get the global alert silence service instance."""
    global _silence_service
    if _silence_service is None:
        _silence_service = AlertSilenceService()
    return _silence_service