from math import atan2, floor, hypot, sqrt, tau
from typing import Optional


STENO_ORDER = "STKPWHRAO*EUFRPBLGTSDZ#!@$%^&"
NO_HYPHEN_KEYS = set("!@#$%^&*")


def get_keys_for_stroke(stroke_str: str) -> tuple[str, ...]:
    keys = list[str]()
    passed_hyphen = False
    for key in stroke_str:
        if key == "-":
            passed_hyphen = True
            continue
        if key in NO_HYPHEN_KEYS:
            keys.append(key)
        elif passed_hyphen:
            keys.append(f"-{key}")
        else:
            keys.append(f"{key}-")
    return tuple(keys)


def keys_to_stroke(keys: tuple[str, ...]) -> str:
    if not keys:
        return ""

    LEFT_ORDER = "STKPWHRAO"
    RIGHT_ORDER = "EUFRPBLGTSDZ"

    left = []
    right = []
    special = []
    for key in keys:
        if key in NO_HYPHEN_KEYS:
            special.append(key)
        elif key.endswith("-"):
            left.append(key[:-1])
        elif key.startswith("-"):
            right.append(key[1:])

    left.sort(key=lambda c: LEFT_ORDER.index(c) if c in LEFT_ORDER else len(LEFT_ORDER))
    right.sort(key=lambda c: RIGHT_ORDER.index(c) if c in RIGHT_ORDER else len(RIGHT_ORDER))

    result = "".join(left)
    result += "".join(special)
    if right:
        result += "-" + "".join(right)
    elif left:
        result += "-"
    return result


def buttons_to_keys(
    in_keys: set[str],
    unordered_mappings: list[tuple[list[str], tuple[str, ...]]],
) -> set[str]:
    keys = set[str]()
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
