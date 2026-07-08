#!/usr/bin/env python3
"""
AIMO Problem 1: Airline Departure Problem

Three airlines depart from Dodola island every 100, 120, and 150 days respectively.
Find the greatest positive integer d such that, regardless of the departure
times (phase offsets) of the various airlines, there will be d consecutive days
without any flight.
"""

import sys

PERIODS = [100, 120, 150]
LCM = 600  # lcm(100, 120, 150)


def max_gap_for_offsets(a, b, c):
    """
    For given phase offsets (a mod 100, b mod 120, c mod 150),
    compute the maximum number of consecutive days with no departures.
    """
    departures = set()

    # Generate all departure days within [0, LCM)
    for k in range(LCM // PERIODS[0] + 2):
        day = a + k * PERIODS[0]
        if 0 <= day < LCM:
            departures.add(day)

    for k in range(LCM // PERIODS[1] + 2):
        day = b + k * PERIODS[1]
        if 0 <= day < LCM:
            departures.add(day)

    for k in range(LCM // PERIODS[2] + 2):
        day = c + k * PERIODS[2]
        if 0 <= day < LCM:
            departures.add(day)

    sorted_days = sorted(departures)

    # Gaps between consecutive departures
    max_gap = 0
    for i in range(len(sorted_days) - 1):
        gap = sorted_days[i + 1] - sorted_days[i] - 1
        if gap > max_gap:
            max_gap = gap

    # Wrap-around gap: from last departure to first departure + LCM
    wrap_gap = (sorted_days[0] + LCM) - sorted_days[-1] - 1
    if wrap_gap > max_gap:
        max_gap = wrap_gap

    return max_gap


def solve():
    """Brute-force over all phase offset combinations to find the
    minimum possible maximum gap (the guaranteed d)."""
    min_of_max_gaps = float('inf')
    worst_offsets = None

    total = PERIODS[0] * PERIODS[1] * PERIODS[2]
    count = 0

    for a in range(PERIODS[0]):
        for b in range(PERIODS[1]):
            for c in range(PERIODS[2]):
                mg = max_gap_for_offsets(a, b, c)
                if mg < min_of_max_gaps:
                    min_of_max_gaps = mg
                    worst_offsets = (a, b, c)
                count += 1

    return min_of_max_gaps, worst_offsets


def main():
    answer, worst = solve()
    print(f"Greatest guaranteed consecutive no-flight days: {answer}")
    print(f"Worst-case offsets (a, b, c): {worst}")

    # Verify: for these worst-case offsets, show the departure pattern
    a, b, c = worst
    print(f"\nVerification for worst-case offsets (a={a}, b={b}, c={c}):")
    mg = max_gap_for_offsets(a, b, c)
    print(f"  Max gap = {mg}")

    # Show departure days in one period for the worst case
    departures = set()
    for k in range(LCM // PERIODS[0] + 2):
        day = a + k * PERIODS[0]
        if 0 <= day < LCM:
            departures.add(day)
    for k in range(LCM // PERIODS[1] + 2):
        day = b + k * PERIODS[1]
        if 0 <= day < LCM:
            departures.add(day)
    for k in range(LCM // PERIODS[2] + 2):
        day = c + k * PERIODS[2]
        if 0 <= day < LCM:
            departures.add(day)
    sorted_days = sorted(departures)
    print(f"  Departure days in [0, {LCM}): {sorted_days}")
    print(f"  Number of departure days: {len(sorted_days)}")

    gaps = []
    for i in range(len(sorted_days) - 1):
        gaps.append(sorted_days[i + 1] - sorted_days[i] - 1)
    wrap_gap = (sorted_days[0] + LCM) - sorted_days[-1] - 1
    gaps.append(wrap_gap)
    print(f"  Gaps: {gaps}")

    # Write final answer to results.txt
    with open("results.txt", "w") as f:
        f.write(str(answer) + "\n")
    print(f"\nAnswer written to results.txt: {answer}")


if __name__ == "__main__":
    main()
