
from math import floor, ceil
from typing import Dict, List

def k_factor(subscribers: int) -> int:
    return floor(subscribers / 250) + 1

def boosts_for_level(subscribers: int, level: int) -> int:
    k = k_factor(subscribers)
    if level <= 8:
        return ceil(k * level / 2)
    if level == 9:
        return 7 * k
    return k * level  # level >= 10

def full_table(subscribers: int, levels: List[int] = list(range(1, 11))) -> Dict[int, int]:
    return {lvl: boosts_for_level(subscribers, lvl) for lvl in levels}
