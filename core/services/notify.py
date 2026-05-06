"""Optional email ping when a lead is captured from the public site."""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def notify_new_web_lead(lead) -> None:
    to = (getattr(settings, "LEAD_NOTIFY_EMAIL", "") or "").strip()
    if not to:
        return
    subject = f"New lead: {lead.name} ({lead.business.name})"
    lines = [
        f"Business: {lead.business.name}",
        f"Service: {lead.business.service} · {lead.business.city}",
        f"Name: {lead.name}",
        f"Phone: {lead.phone or '—'}",
        f"Email: {lead.email or '—'}",
        "",
        lead.notes or "(no message)",
    ]
    body = "\n".join(lines)
    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [to],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Failed to send lead notification email")
