"""Sharp boundary-error radius and finite-population zero-hit audit design."""
import math
from fractions import Fraction


def reversal_radius(d_win, s_win, d_lose, s_lose, cuts_lose):
    """Transitions at the anchor are d_j, switches are s_j, cuts_lose is the number
    of joined edges available for splitting in the loser. Same-side edits only."""
    if not (0 < s_win <= d_win and 0 < s_lose <= d_lose and cuts_lose >= 0):
        raise ValueError("requires positive switch counts and valid capacities")
    gap = s_lose*d_win - s_win*d_lose
    if gap < 0:
        raise ValueError("first group must be the anchor winner")
    used = 0
    pools = [(s_lose, d_win-s_win), (s_win, cuts_lose)]
    for weight, capacity in sorted(pools, reverse=True):
        take = min(capacity, (gap+weight-1)//weight)
        gap -= take*weight
        used += take
        if gap <= 0:
            return used
    raise ValueError("unreachable rank change")


def log_miss(total, errors, draws):
    """Log probability of drawing no errors. Use the shorter product."""
    if not 0 <= errors <= total or not 0 <= draws <= total:
        raise ValueError("invalid finite population")
    if draws > total-errors:
        return -math.inf
    a, b = sorted((errors, draws))
    return math.fsum(math.log1p(-b/(total-i)) for i in range(a))


def audit_size(total, radius, risk=0.05):
    if not (0 < risk < 1 and 1 <= radius <= total):
        raise ValueError("a strict ranking and a positive error radius are required")
    # Exponential search avoids computing a long sum at half the population
    # when the required budget is only a few labels.
    def safe(draws):
        diff = log_miss(total, radius, draws) - math.log(risk)
        if abs(diff) > 1e-11:
            return diff < 0
        # Resolve threshold equality with integers instead of rounding a risk guarantee.
        target = Fraction(str(risk))
        return (math.comb(total-radius, draws)*target.denominator
                <= math.comb(total, draws)*target.numerator)

    hi = 1
    while not safe(hi):
        hi = min(total, 2*hi)
    lo = 0
    while hi-lo > 1:
        mid = (lo+hi)//2
        if safe(mid):
            hi = mid
        else:
            lo = mid
    return hi
