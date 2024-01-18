from math import atan2, floor, hypot, sqrt, tau
from typing import Optional


def get_keys_for_stroke(stroke_str: str) -> tuple[str, ...]:
    keys: list[str] = []
    passed_hyphen = False
    no_hyphen_keys = set("!@#$%^&*")
    for key in stroke_str:
        if key == "-":
            passed_hyphen = True
            continue
        if key in no_hyphen_keys:
            keys.append(key)
        elif passed_hyphen:
            keys.append(f"-{key}")
        else:
            keys.append(f"{key}-")
    return tuple(keys)


def buttons_to_keys(
    in_keys: set[str],
    unordered_mappings: list[tuple[list[str], tuple[str, ...]]],
) -> set[str]:
    keys: set[str] = set()
    for chord, result in unordered_mappings:
        if all(map(lambda x: x in in_keys, chord)):
            for key in chord:
                in_keys.remove(key)
            keys.update(result)
    return keys


def stick_segment(
    stick_dead_zone: float,
    offset: float,
    segment_count: int,
    lr: float,
    ud: float,
) -> Optional[int]:
    if hypot(lr, ud) < stick_dead_zone * sqrt(2):
        return None
    offset = offset / 360 * tau
    angle = atan2(ud, lr) - offset
    while angle < 0:
        angle += tau
    while angle > tau:
        angle -= tau
    segment = floor(angle / tau * segment_count)
    return segment % segment_count
