from collections.abc import Sequence 
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from notifications.common.schemas import NotificationChannel
from notifications.notifications_api.schemas.template import (
    TemplateCreate,
    TemplateUpdate,
)
from notifications.db.models import Template


class TemplateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Template]:
        stmt = (
            select(Template)
            .order_by(Template.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def find_by_id(self, template_id: UUID) -> Template | None:
        """Get a template by ID or return None."""
        stmt = select(Template).where(Template.id == template_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_code_locale_channel(
        self,
        template_code: str,
        locale: str,
        channel: NotificationChannel,
    ) -> Template | None:
        """Get a template by unique key or return None."""
        stmt = select(Template).where(
            Template.template_code == template_code,
            Template.locale == locale,
            Template.channel == channel.value,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: TemplateCreate) -> Template:
        tpl = Template(
            id=uuid4(),
            template_code=data.template_code,
            locale=data.locale,
            channel=data.channel.value,
            subject=data.subject,
            body=data.body,
        )
        self._session.add(tpl)
        await self._session.commit()
        await self._session.refresh(tpl)
        return tpl

    async def update(
        self,
        template: Template,
        data: TemplateUpdate,
    ) -> Template:
        if data.subject is not None:
            template.subject = data.subject
        if data.body is not None:
            template.body = data.body

        await self._session.commit()
        await self._session.refresh(template)
        return template