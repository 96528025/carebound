from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ScalekitResult:
    enabled: bool
    mode: str
    connection_name: str
    identifier: str
    connected_account_id: str | None = None
    status: str | None = None
    authorization_link: str | None = None
    tool_name: str | None = None
    tool_output_preview: str | None = None
    error: str | None = None


def configured() -> bool:
    return all(os.getenv(key) for key in ["SCALEKIT_ENV_URL", "SCALEKIT_CLIENT_ID", "SCALEKIT_CLIENT_SECRET"])


def connection_name(default: str = "gmail") -> str:
    return os.getenv("GMAIL_CONNECTION_NAME") or os.getenv("SCALEKIT_CONNECTION_NAME") or default


def calendar_connection_name(default: str = "googlecalendar") -> str:
    return os.getenv("GOOGLE_CALENDAR_CONNECTION_NAME") or os.getenv("CALENDAR_CONNECTION_NAME") or default


def _client():
    import scalekit.client

    return scalekit.client.ScalekitClient(
        client_id=os.getenv("SCALEKIT_CLIENT_ID"),
        client_secret=os.getenv("SCALEKIT_CLIENT_SECRET"),
        env_url=os.getenv("SCALEKIT_ENV_URL"),
    )


def get_or_create_connected_account(identifier: str, name: str | None = None) -> ScalekitResult:
    name = name or connection_name()
    if not configured():
        return ScalekitResult(
            enabled=False,
            mode="demo",
            connection_name=name,
            identifier=identifier,
            status="not_configured",
            error="Missing Scalekit env vars; using demo identity mode.",
        )

    try:
        client = _client()
        actions = client.actions
        response = actions.get_or_create_connected_account(
            connection_name=name,
            identifier=identifier,
        )
        connected_account = response.connected_account
        status = str(getattr(connected_account, "status", "UNKNOWN"))
        account_id = str(getattr(connected_account, "id", ""))
        authorization_link = None
        if "ACTIVE" not in status.upper():
            link_response = actions.get_authorization_link(
                connection_name=name,
                identifier=identifier,
            )
            authorization_link = getattr(link_response, "link", None)
        return ScalekitResult(
            enabled=True,
            mode="live",
            connection_name=name,
            identifier=identifier,
            connected_account_id=account_id,
            status=status,
            authorization_link=authorization_link,
        )
    except Exception as exc:
        return ScalekitResult(
            enabled=True,
            mode="live_error",
            connection_name=name,
            identifier=identifier,
            status="error",
            error=str(exc),
        )


def create_calendar_event(
    identifier: str,
    summary: str,
    start: str | None,
    end: str | None,
    location: str | None = None,
    description: str | None = None,
    timezone: str = "America/Los_Angeles",
) -> ScalekitResult:
    """Create a Google Calendar event as this user via Scalekit AgentKit.

    In demo mode (no Scalekit env vars) it returns a preview instead of
    actually creating the event, so the flow can be shown without credentials.
    """
    name = calendar_connection_name()
    if not configured():
        return ScalekitResult(
            enabled=False,
            mode="demo",
            connection_name=name,
            identifier=identifier,
            status="preview",
            tool_name="googlecalendar_create_event",
            tool_output_preview=f"[demo] would create: {summary} @ {location or 'n/a'} ({start} - {end})",
            error="Missing Scalekit env vars; calendar event previewed in demo mode.",
        )

    # Make sure this identity has an active Google Calendar connection first.
    account = get_or_create_connected_account(identifier, name)
    if account.authorization_link or account.status == "error":
        return account

    try:
        client = _client()
        tool_input = {
            "summary": summary,
            "start": {"dateTime": start, "timeZone": timezone},
            "end": {"dateTime": end, "timeZone": timezone},
        }
        if location:
            tool_input["location"] = location
        if description:
            tool_input["description"] = description
        result = client.actions.execute_tool(
            tool_name="googlecalendar_create_event",
            identifier=identifier,
            tool_input=tool_input,
        )
        return ScalekitResult(
            enabled=True,
            mode="live",
            connection_name=name,
            identifier=identifier,
            connected_account_id=account.connected_account_id,
            status="event_created",
            tool_name="googlecalendar_create_event",
            tool_output_preview=str(result)[:500],
        )
    except Exception as exc:
        return ScalekitResult(
            enabled=True,
            mode="live_error",
            connection_name=name,
            identifier=identifier,
            connected_account_id=account.connected_account_id,
            status="tool_error",
            tool_name="googlecalendar_create_event",
            error=str(exc),
        )


def fetch_recent_care_emails(identifier: str, query: str = "appointment OR care OR doctor", max_results: int = 5) -> ScalekitResult:
    name = connection_name()
    account = get_or_create_connected_account(identifier, name)
    if not account.enabled or account.status == "error" or account.authorization_link:
        return account

    try:
        client = _client()
        result = client.actions.execute_tool(
            tool_name="gmail_fetch_mails",
            identifier=identifier,
            tool_input={"query": query, "max_results": max_results},
        )
        return ScalekitResult(
            enabled=True,
            mode="live",
            connection_name=name,
            identifier=identifier,
            connected_account_id=account.connected_account_id,
            status="tool_executed",
            tool_name="gmail_fetch_mails",
            tool_output_preview=str(result)[:500],
        )
    except Exception as exc:
        return ScalekitResult(
            enabled=True,
            mode="live_error",
            connection_name=name,
            identifier=identifier,
            connected_account_id=account.connected_account_id,
            status="tool_error",
            tool_name="gmail_fetch_mails",
            error=str(exc),
        )
