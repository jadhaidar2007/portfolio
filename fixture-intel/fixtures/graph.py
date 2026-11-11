"""Microsoft Graph ingestion (how the production version read the shared inbox).

App-only auth with MSAL client credentials, then page through the mailbox's
inbox since a given time. Not used by the offline demo; needs:

    GRAPH_TENANT_ID, GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET, GRAPH_MAILBOX
and the Mail.Read application permission granted by an admin.
"""
from __future__ import annotations

import datetime as dt
import os
import re

GRAPH = "https://graph.microsoft.com/v1.0"


def _token() -> str:
    import msal

    app = msal.ConfidentialClientApplication(
        os.environ["GRAPH_CLIENT_ID"],
        authority=f"https://login.microsoftonline.com/{os.environ['GRAPH_TENANT_ID']}",
        client_credential=os.environ["GRAPH_CLIENT_SECRET"],
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in result:
        raise RuntimeError(f"Graph auth failed: {result.get('error_description')}")
    return result["access_token"]


def _html_to_text(html: str) -> str:
    text = re.sub(r"<br\s*/?>|</p>|</tr>", "\n", html, flags=re.I)
    text = re.sub(r"</t[dh]>", " | ", text, flags=re.I)
    return re.sub(r"<[^>]+>", "", text)


def fetch_messages(since: dt.datetime) -> list[tuple[str, str, dt.date, str]]:
    """Return (message_id, sender, date, plain_body) for messages received since `since`."""
    import requests

    headers = {"Authorization": f"Bearer {_token()}", "Prefer": 'outlook.body-content-type="text"'}
    url = f"{GRAPH}/users/{os.environ['GRAPH_MAILBOX']}/mailFolders/inbox/messages"
    params = {
        "$filter": f"receivedDateTime ge {since.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "$select": "id,from,receivedDateTime,body",
        "$top": "50",
    }
    out = []
    while url:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        for m in data.get("value", []):
            body = m["body"]["content"]
            if m["body"].get("contentType") == "html":
                body = _html_to_text(body)
            received = dt.datetime.fromisoformat(m["receivedDateTime"].replace("Z", "+00:00"))
            out.append((m["id"], m["from"]["emailAddress"]["address"], received.date(), body))
        url, params = data.get("@odata.nextLink"), None  # nextLink already has the query
    return out
