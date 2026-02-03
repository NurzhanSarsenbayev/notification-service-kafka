from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import asyncpg


@dataclass
class Template:
    template_code: str
    locale: str
    channel: str
    subject: str
    body: str


class TemplateRepository:
    """Access to the templates table."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_template(
        self,
        template_code: str,
        locale: str,
        channel: str,
    ) -> Optional[Template]:
        query = """
            SELECT template_code, locale, channel, subject, body
            FROM templates
            WHERE template_code = $1
              AND locale        = $2
              AND channel       = $3
            LIMIT 1;
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, template_code, locale, channel)

        if row is None:
            return None

        return Template(
            template_code=row["template_code"],
            locale=row["locale"],
            channel=row["channel"],
            subject=row["subject"],
            body=row["body"],
        )
