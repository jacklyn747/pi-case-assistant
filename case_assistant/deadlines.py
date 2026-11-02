"""Deterministic Texas filing-deadline helper.

Dates come from plain date math, never from the language model, so the same
inputs always give the same answer. This is a paralegal aid, not legal advice:
every result must be checked against the official statutes and the facts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta


@dataclass
class DeadlineResult:
    label: str
    due: date
    basis: str
    notes: list[str] = field(default_factory=list)


def _add_years(start: date, years: int) -> date:
    try:
        return start.replace(year=start.year + years)
    except ValueError:  # Feb 29 in a non-leap year
        return start.replace(year=start.year + years, day=28)


def _add_months(start: date, months: int) -> date:
    month = start.month - 1 + months
    year, month = start.year + month // 12, month % 12 + 1
    day = start.day
    while True:
        try:
            return date(year, month, day)
        except ValueError:
            day -= 1


def _roll_weekend(d: date) -> tuple[date, bool]:
    rolled = d
    while rolled.weekday() >= 5:
        rolled += timedelta(days=1)
    return rolled, rolled != d


def personal_injury_deadlines(
    incident: date,
    client_birthdate: date | None = None,
    government_defendant: bool = False,
) -> list[DeadlineResult]:
    results: list[DeadlineResult] = []

    accrual = incident
    notes: list[str] = []
    if client_birthdate is not None:
        eighteenth = _add_years(client_birthdate, 18)
        if eighteenth > incident:
            accrual = eighteenth
            notes.append(
                "Client was a minor on the incident date, so the two years are counted "
                "from the 18th birthday (Tex. Civ. Prac. & Rem. Code § 16.001)."
            )

    due, rolled = _roll_weekend(_add_years(accrual, 2))
    if rolled:
        notes.append("Fell on a weekend, so it moves to the next weekday (§ 16.072).")
    notes.append("Check for legal holidays, which also extend the deadline (§ 16.072).")
    results.append(
        DeadlineResult(
            label="Suit filing deadline (general personal injury)",
            due=due,
            basis="Tex. Civ. Prac. & Rem. Code § 16.003: two years from when the claim accrues.",
            notes=notes,
        )
    )

    if government_defendant:
        notice, rolled = _roll_weekend(_add_months(incident, 6))
        gov_notes = ["City charters can require notice sooner. Check the charter."]
        if rolled:
            gov_notes.insert(0, "Fell on a weekend, so it was moved to the next weekday.")
        results.append(
            DeadlineResult(
                label="Written notice to the governmental unit",
                due=notice,
                basis="Tex. Civ. Prac. & Rem. Code § 101.101(a): notice within six months of the incident.",
                notes=gov_notes,
            )
        )

    return results
