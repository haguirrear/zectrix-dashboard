from datetime import date, timedelta

from zectrix_collector.sources.github import current_streak, parse_public_calendar, quartile_levels, week_grid


def days_from(start: str, counts: list[int]):
    d0 = date.fromisoformat(start)
    return [((d0 + timedelta(i)).isoformat(), c, 1 if c else 0) for i, c in enumerate(counts)]


def test_quartile_levels():
    assert quartile_levels([0, 0]) == [0, 0]
    levels = quartile_levels([0, 1, 2, 3, 4, 5, 6, 7, 8])
    assert levels[0] == 0
    assert levels[-1] == 4
    assert levels == sorted(levels)


def test_week_grid_is_monday_first():
    # 2026-11-04 is a Wednesday: the first column is partial and bottom-aligned (Mon, Tue empty)
    days = days_from("2026-11-04", [1] * 12)  # Wed 4th .. Sun 15th
    weeks, grid = week_grid(days, 18)
    assert len(grid) == 2
    assert grid[0] == [-1, -1, 1, 1, 1, 1, 1]
    assert grid[1] == [1] * 7
    assert date.fromisoformat(weeks[1][0][0]).weekday() == 0


def test_week_grid_keeps_last_weeks_and_pads_current_week():
    days = days_from("2026-01-05", [0] * (7 * 30 + 3))  # Monday start, current week has 3 days
    weeks, grid = week_grid(days, 18)
    assert len(grid) == 18
    assert grid[-1] == [0, 0, 0, -1, -1, -1, -1]


def test_streak_ignores_an_empty_today():
    assert current_streak(days_from("2026-11-01", [0, 1, 1, 1, 0])) == 3
    assert current_streak(days_from("2026-11-01", [0, 1, 1, 1, 2])) == 4
    assert current_streak(days_from("2026-11-01", [1, 0, 0])) == 0


def test_parse_public_calendar():
    html = """
    <td data-date="2026-11-15" id="c1" data-level="2" class="x"></td>
    <td data-date="2026-11-16" id="c2" data-level="0"></td>
    <tool-tip for="c1">5 contributions on November 15th.</tool-tip>
    <tool-tip for="c2">No contributions on November 16th.</tool-tip>
    <h2>1,234 contributions in the last year</h2>
    """
    days, total = parse_public_calendar(html)
    assert days == [("2026-11-15", 5, 2), ("2026-11-16", 0, 0)]
    assert total == 1234
