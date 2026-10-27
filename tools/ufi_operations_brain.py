#!/usr/bin/env python3
"""Additive UFI operations policy: Africa/Lagos clock, blacklist, market rules and unit ledger.

This module is deliberately fail-closed. It does not place bets, infer missing data,
or claim that historical patterns are profitable. Supply a durable SQLite path for
local use; production workers must mount persistent storage or provide a durable DB.
"""
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

WAT = ZoneInfo("Africa/Lagos")
DEFAULT_DB = os.getenv("UFI_OPERATIONS_DB", "ufi_operations.sqlite3")


def nigeria_now() -> datetime:
    """Return an aware current timestamp in Nigeria (Africa/Lagos)."""
    return datetime.now(WAT)


def operating_phase(now: datetime | None = None, cutoff: time = time(21, 0)) -> str:
    """At/after 21:00 WAT use next-day preparation; before it use qualification."""
    local = (now or nigeria_now()).astimezone(WAT)
    return "nightly_preparation" if local.timetz().replace(tzinfo=None) >= cutoff else "qualification"


def normalize_team(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", " ", str(name).casefold()).strip()


@dataclass(frozen=True)
class Decision:
    status: str
    reasons: tuple[str, ...]
    phase: str


class OperationsStore:
    """Persistent blacklist, rulebook, decisions and three independent bankroll ledgers."""
    def __init__(self, path: str | Path = DEFAULT_DB):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=15)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS blacklist (
          team_key TEXT NOT NULL, team_name TEXT NOT NULL, scope TEXT NOT NULL DEFAULT 'all',
          competition TEXT NOT NULL DEFAULT '', reason TEXT NOT NULL, evidence_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL, expires_at TEXT, active INTEGER NOT NULL DEFAULT 1,
          PRIMARY KEY(team_key, scope, competition)
        );
        CREATE TABLE IF NOT EXISTS market_rules (
          rule_id TEXT PRIMARY KEY, market TEXT NOT NULL, competition TEXT NOT NULL DEFAULT '',
          prompt_version TEXT NOT NULL, rule_json TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'experimental',
          evidence_json TEXT NOT NULL DEFAULT '{}', updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS decisions (
          decision_id TEXT PRIMARY KEY, fixture_id TEXT NOT NULL, home TEXT NOT NULL, away TEXT NOT NULL,
          market TEXT NOT NULL, status TEXT NOT NULL, reasons_json TEXT NOT NULL, phase TEXT NOT NULL,
          evaluated_at TEXT NOT NULL, data_fresh INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS units (
          unit_id INTEGER PRIMARY KEY CHECK(unit_id BETWEEN 1 AND 3),
          bankroll REAL NOT NULL CHECK(bankroll >= 0), normal_stake REAL NOT NULL CHECK(normal_stake >= 0),
          absorber_min REAL NOT NULL CHECK(absorber_min >= 0), absorber_max REAL NOT NULL CHECK(absorber_max >= absorber_min),
          remaining_lives INTEGER NOT NULL DEFAULT 4 CHECK(remaining_lives BETWEEN 0 AND 4),
          daily_failure_date TEXT NOT NULL DEFAULT '', daily_failure_used INTEGER NOT NULL DEFAULT 0,
          mode TEXT NOT NULL DEFAULT 'normal', status TEXT NOT NULL DEFAULT 'active',
          daily_pnl REAL NOT NULL DEFAULT 0, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ledger (
          id INTEGER PRIMARY KEY AUTOINCREMENT, unit_id INTEGER NOT NULL REFERENCES units(unit_id),
          event_key TEXT NOT NULL UNIQUE, event_type TEXT NOT NULL, amount REAL NOT NULL,
          bankroll_after REAL NOT NULL, details_json TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS phase_runs (
          local_date TEXT NOT NULL, phase TEXT NOT NULL, status TEXT NOT NULL,
          details_json TEXT NOT NULL DEFAULT '{}', started_at TEXT NOT NULL, finished_at TEXT,
          PRIMARY KEY(local_date, phase)
        );
        """)
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def blacklist_team(self, name: str, reason: str, scope: str = "all",
                       competition: str = "", evidence: dict[str, Any] | None = None,
                       expires_at: str | None = None) -> None:
        key = normalize_team(name)
        if not key or not reason.strip():
            raise ValueError("team name and reason are required")
        self.db.execute("""INSERT INTO blacklist(team_key,team_name,scope,competition,reason,evidence_json,created_at,expires_at,active)
          VALUES(?,?,?,?,?,?,?,?,1) ON CONFLICT(team_key,scope,competition) DO UPDATE SET
          team_name=excluded.team_name,reason=excluded.reason,evidence_json=excluded.evidence_json,
          created_at=excluded.created_at,expires_at=excluded.expires_at,active=1""",
          (key, name.strip(), scope.strip() or "all", competition.strip(),
           reason.strip(), json.dumps(evidence or {}, sort_keys=True), nigeria_now().isoformat(), expires_at))
        self.db.commit()

    def unblacklist_team(self, name: str, scope: str = "all", competition: str = "") -> None:
        self.db.execute("UPDATE blacklist SET active=0 WHERE team_key=? AND scope=? AND competition=?",
                        (normalize_team(name), scope, competition))
        self.db.commit()

    def blacklist_reasons(self, team: str, market: str, competition: str = "",
                          now: datetime | None = None) -> list[str]:
        current = (now or nigeria_now()).astimezone(WAT)
        key = normalize_team(team)
        rows = self.db.execute("SELECT * FROM blacklist WHERE active=1 AND team_key=?", (key,)).fetchall()
        reasons = []
        for row in rows:
            if row["scope"] not in ("all", "*", market):
                continue
            if row["competition"] and normalize_team(row["competition"]) != normalize_team(competition):
                continue
            expiry = row["expires_at"]
            if expiry:
                try:
                    exp = datetime.fromisoformat(expiry)
                    if exp.tzinfo is None:
                        exp = exp.replace(tzinfo=WAT)
                    if exp.astimezone(WAT) <= current:
                        continue
                except ValueError:
                    # Malformed expiry is fail-closed: continue blocking.
                    pass
            reasons.append(f"{row['team_name']} blacklisted ({row['scope']}): {row['reason']}")
        return reasons

    def save_rule(self, rule_id: str, market: str, prompt_version: str,
                  rule: dict[str, Any], competition: str = "", status: str = "experimental",
                  evidence: dict[str, Any] | None = None) -> None:
        if status not in {"experimental", "validated", "suspended", "rejected"}:
            raise ValueError("invalid rule status")
        self.db.execute("""INSERT INTO market_rules VALUES(?,?,?,?,?,?,?,?)
          ON CONFLICT(rule_id) DO UPDATE SET market=excluded.market,competition=excluded.competition,
          prompt_version=excluded.prompt_version,rule_json=excluded.rule_json,status=excluded.status,
          evidence_json=excluded.evidence_json,updated_at=excluded.updated_at""",
          (rule_id, market, competition, prompt_version, json.dumps(rule, sort_keys=True),
           status, json.dumps(evidence or {}, sort_keys=True), nigeria_now().isoformat()))
        self.db.commit()

    def qualify(self, fixture: dict[str, Any], market: str, *, prompt_pass: bool | None,
                rule_id: str | None, required_data_present: bool, data_age_seconds: float | None,
                max_data_age_seconds: float = 120, odds: float | None = None,
                odds_range: tuple[float, float] | None = None, phase_time: datetime | None = None) -> Decision:
        """Evaluate hard gates. prompt_pass=None means prompt has not been implemented/configured."""
        reasons: list[str] = []
        home, away = str(fixture.get("home", "")), str(fixture.get("away", ""))
        competition = str(fixture.get("competition", ""))
        phase = operating_phase(phase_time)
        if not fixture.get("id") or not home.strip() or not away.strip():
            reasons.append("fixture identity incomplete")
        reasons += self.blacklist_reasons(home, market, competition, phase_time)
        reasons += self.blacklist_reasons(away, market, competition, phase_time)
        if prompt_pass is not True:
            reasons.append("filtering prompt did not explicitly pass; prompt not configured or criteria failed")
        rule = self.db.execute("SELECT status FROM market_rules WHERE rule_id=?", (rule_id,)).fetchone() if rule_id else None
        if not rule or rule["status"] != "validated":
            reasons.append("no validated research rule is attached")
        if not required_data_present:
            reasons.append("required source data unavailable")
        if data_age_seconds is None or data_age_seconds < 0 or data_age_seconds > max_data_age_seconds:
            reasons.append("source data is missing, future-dated, or stale")
        if odds_range is not None and (odds is None or not (odds_range[0] <= odds <= odds_range[1])):
            reasons.append("odds are missing or outside the configured range")
        return Decision("REJECTED" if reasons else "QUALIFIED_FOR_REVIEW", tuple(reasons), phase)

    def record_decision(self, decision_id: str, fixture: dict[str, Any], market: str,
                        decision: Decision, data_fresh: bool) -> None:
        self.db.execute("""INSERT OR REPLACE INTO decisions VALUES(?,?,?,?,?,?,?,?,?,?)""",
          (decision_id, str(fixture.get("id", "")), str(fixture.get("home", "")),
           str(fixture.get("away", "")), market, decision.status, json.dumps(decision.reasons),
           decision.phase, nigeria_now().isoformat(), int(data_fresh)))
        self.db.commit()

    def configure_unit(self, unit_id: int, bankroll: float, normal_stake: float,
                       absorber_min: float = 50, absorber_max: float = 75) -> None:
        if unit_id not in (1, 2, 3) or min(bankroll, normal_stake, absorber_min, absorber_max) < 0 or absorber_max < absorber_min:
            raise ValueError("invalid unit configuration")
        now = nigeria_now().isoformat()
        self.db.execute("""INSERT INTO units(unit_id,bankroll,normal_stake,absorber_min,absorber_max,
          remaining_lives,daily_failure_date,daily_failure_used,mode,status,daily_pnl,updated_at)
          VALUES(?,?,?,?,?,4,'',0,'normal','active',0,?)
          ON CONFLICT(unit_id) DO UPDATE SET bankroll=excluded.bankroll,normal_stake=excluded.normal_stake,
          absorber_min=excluded.absorber_min,absorber_max=excluded.absorber_max,updated_at=excluded.updated_at""",
          (unit_id, bankroll, normal_stake, absorber_min, absorber_max, now))
        self.db.commit()

    def unit_event(self, unit_id: int, event_key: str, event_type: str, amount: float = 0,
                   *, qualifying_failure: bool = False, cycle_success: bool = False,
                   details: dict[str, Any] | None = None, when: datetime | None = None) -> dict[str, Any]:
        """Record settlement/state transitions exactly once; amount is signed bankroll delta."""
        now = (when or nigeria_now()).astimezone(WAT)
        date = now.date().isoformat()
        if not event_key or not event_type:
            raise ValueError("event_key and event_type required")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            existing = self.db.execute("SELECT * FROM ledger WHERE event_key=?", (event_key,)).fetchone()
            if existing:
                row = self.db.execute("SELECT * FROM units WHERE unit_id=?", (unit_id,)).fetchone()
                self.db.commit()
                return dict(row) if row else {}
            row = self.db.execute("SELECT * FROM units WHERE unit_id=?", (unit_id,)).fetchone()
            if not row:
                raise ValueError("unit must be configured first")
            # A unit with a qualifying failure is paused for the rest of the local day.
            status = row["status"]
            failure_date = row["daily_failure_date"]
            failure_used = bool(row["daily_failure_used"]) if failure_date == date else False
            pnl = float(row["daily_pnl"]) if failure_date == date else 0.0
            mode = row["mode"]
            lives = int(row["remaining_lives"])
            if status == "paused_today" and failure_date != date:
                status = "active"
            if event_type == "set_mode":
                mode = str((details or {}).get("mode", "normal"))
                if mode not in {"normal", "absorber_boost"}:
                    raise ValueError("mode must be normal or absorber_boost")
            bankroll = max(0.0, float(row["bankroll"]) + float(amount))
            pnl += float(amount)
            if qualifying_failure and not failure_used:
                failure_used, failure_date, status = True, date, "paused_today"
                lives = max(0, lives - 1)
            if cycle_success:
                lives = 4
                mode = "normal"
            stamp = now.isoformat()
            self.db.execute("""UPDATE units SET bankroll=?,remaining_lives=?,daily_failure_date=?,
              daily_failure_used=?,mode=?,status=?,daily_pnl=?,updated_at=? WHERE unit_id=?""",
              (bankroll, lives, failure_date if failure_used else date, int(failure_used), mode, status, pnl, stamp, unit_id))
            self.db.execute("INSERT INTO ledger(unit_id,event_key,event_type,amount,bankroll_after,details_json,created_at) VALUES(?,?,?,?,?,?,?)",
              (unit_id, event_key, event_type, float(amount), bankroll, json.dumps(details or {}, sort_keys=True), stamp))
            self.db.commit()
            result = self.db.execute("SELECT * FROM units WHERE unit_id=?", (unit_id,)).fetchone()
            return dict(result)
        except Exception:
            self.db.rollback()
            raise

    def start_phase(self, phase: str, local_date: str | None = None) -> None:
        if phase not in {"qualification", "nightly_preparation"}:
            raise ValueError("invalid phase")
        day = local_date or nigeria_now().date().isoformat()
        now = nigeria_now().isoformat()
        self.db.execute("""INSERT INTO phase_runs(local_date,phase,status,details_json,started_at)
          VALUES(?,?,'running','{}',?) ON CONFLICT(local_date,phase) DO UPDATE SET
          status='running',started_at=excluded.started_at,finished_at=NULL""", (day, phase, now))
        self.db.commit()

    def finish_phase(self, phase: str, status: str, details: dict[str, Any] | None = None,
                     local_date: str | None = None) -> None:
        if status not in {"complete", "partial", "failed"}:
            raise ValueError("invalid phase status")
        day = local_date or nigeria_now().date().isoformat()
        self.db.execute("UPDATE phase_runs SET status=?,details_json=?,finished_at=? WHERE local_date=? AND phase=?",
          (status, json.dumps(details or {}, sort_keys=True), nigeria_now().isoformat(), day, phase))
        self.db.commit()
