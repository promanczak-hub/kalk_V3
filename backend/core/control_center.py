"""Adapter dla pionowej (EAV) tabeli control_center.

Tabela control_center w bazie ma teraz uklad key/value (pionowy):
    key    | value (jsonb) | category | updated_at
    -------+---------------+----------+-----------
    default_wibor | 3.76   | finanse  | ...
    bank_spread   | 2.20   | finanse  | ...
    ...

Kalkulatory i ControlCenterSettings (core/models.py) oczekuja jednak
"plaskiego" dict-a w stylu wide-row (kolumna per parametr). Ten modul
zapewnia backward-compatibility: czyta wszystkie wiersze i sklada je
w slownik o ksztalcie starej tabeli, plus pomocniki do zapisu.

Drop-in replacement dla:
    response = supabase.table("control_center").select("*").eq("id", 1).execute()
    data = response.data[0]
->
    from core.control_center import fetch_control_center_row
    data = fetch_control_center_row()
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Mapping, Optional

from supabase import Client

from core.database import supabase as _default_client
from core.models import ControlCenterSettings

log = logging.getLogger(__name__)

LEGACY_ID = 1  # singleton id z dawnej wide-row tabeli; niektorzy callerzy ja czytaja


def _client(client: Optional[Client]) -> Client:
    return client if client is not None else _default_client


def fetch_control_center_row(
    client: Optional[Client] = None,
    keys: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """Zwraca slownik {key: value, ..., 'id': 1, 'updated_at': ISO} - ksztalt starej wide-row.

    Args:
        client: opcjonalny klient supabase (np. get_fresh_client()); domyslnie singleton.
        keys: jesli podane, pobiera tylko te klucze (zamiast wszystkich rzedow).
    """
    sb = _client(client)
    query = sb.table("control_center").select("key,value,updated_at")
    if keys is not None:
        keys_list = list(keys)
        if not keys_list:
            return {"id": LEGACY_ID, "updated_at": _now_iso()}
        query = query.in_("key", keys_list)
    res = query.execute()
    rows = res.data or []
    out: Dict[str, Any] = {"id": LEGACY_ID}
    max_ts: Optional[str] = None
    for r in rows:
        out[r["key"]] = r["value"]
        ts = r.get("updated_at")
        if ts and (max_ts is None or ts > max_ts):
            max_ts = ts
    out["updated_at"] = max_ts or _now_iso()
    return out


def fetch_control_center_settings(
    client: Optional[Client] = None,
) -> ControlCenterSettings:
    """Czyta cala tabele i sklada w Pydantic ControlCenterSettings."""
    row = fetch_control_center_row(client=client)
    row.setdefault("last_settings_update", row.get("updated_at", ""))
    return ControlCenterSettings(**row)


def fetch_control_center_value(
    key: str,
    client: Optional[Client] = None,
    default: Any = None,
) -> Any:
    """Selektywny read pojedynczego klucza (taniej niz pelny scan)."""
    sb = _client(client)
    res = (
        sb.table("control_center")
        .select("value")
        .eq("key", key)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        return default
    return rows[0]["value"]


def update_control_center_fields(
    payload: Mapping[str, Any],
    client: Optional[Client] = None,
) -> int:
    """Upsert wielu key/value rows. Zwraca liczbe zaktualizowanych wierszy.

    payload to slownik o ksztalcie starej wide-row (np. {"default_wibor": 3.81, ...}).
    Klucze 'id' i 'updated_at' sa ignorowane (sa pochodne / zarzadzane przez trigger).
    """
    sb = _client(client)
    rows = []
    for k, v in payload.items():
        if k in ("id", "updated_at"):
            continue
        rows.append({"key": k, "value": v})
    if not rows:
        return 0
    res = sb.table("control_center").upsert(rows, on_conflict="key").execute()
    return len(res.data or [])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
