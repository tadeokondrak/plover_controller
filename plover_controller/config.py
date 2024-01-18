import re
from dataclasses import dataclass
from .util import get_keys_for_stroke


@dataclass
class Stick:
    name: str
    x_axis: str
    y_axis: str
    offset: float
    segments: list[str]


@dataclass
class Trigger:
    name: str
    axis: str


@dataclass
class ButtonOrHat:
    name: str
    button: str


@dataclass
class Mappings:
    sticks: dict[str, Stick]
    buttons_and_hats: dict[str, ButtonOrHat]
    triggers: dict[str, Trigger]
    unordered_mappings: list[tuple[list[str], tuple[str, ...]]]
    ordered_mappings: dict[tuple[str, ...], tuple[str, ...]]

    @classmethod
    def empty(cls) -> "Mappings":
        return Mappings(
            sticks={},
            buttons_and_hats={},
            triggers={},
            ordered_mappings={},
            unordered_mappings=[],
        )

    @classmethod
    def parse(cls, text: str) -> "Mappings":
        result = Mappings.empty()
        for line in text.splitlines():
            if not line or line.startswith("//"):
                continue
            if match := re.match(
                r"(\w+) stick has segments \(([a-z,]+)\) on axes (\d+) and (\d+) offset by ([0-9-.]+) degrees",
                line,
            ):
                stick = Stick(
                    name=match[1],
                    x_axis=f"a{match[3]}",
                    y_axis=f"a{match[4]}",
                    offset=float(match[5]),
                    segments=match[2].split(","),
                )
                result.sticks[stick.name] = stick
            elif match := re.match(r"([a-z0-9,]+) -> ([A-Z-*#]+)", line):
                lhs = match[1].split(",")
                rhs = get_keys_for_stroke(match[2])
                result.unordered_mappings.append((lhs, rhs))
            elif match := re.match(r"(\w+)\(([a-z,]+)\) -> ([A-Z-*#]+)", line):
                result.ordered_mappings[
                    tuple(f"{match[1]}{pos}" for pos in match[2].split(","))
                ] = get_keys_for_stroke(match[3])
            elif match := re.match(r"button (\d+) is ([a-z0-9]+)", line):
                button = ButtonOrHat(
                    name=match[2],
                    button=f"b{match[1]}",
                )
                result.buttons_and_hats[button.button] = button
            elif match := re.match(r"hat (\d+) is ([a-z0-9]+)", line):
                button = ButtonOrHat(
                    name=match[2],
                    button=f"h{match[1]}",
                )
                result.buttons_and_hats[button.button] = button
            elif match := re.match(r"trigger on axis (\d+) is ([a-z0-9]+)", line):
                trigger = Trigger(
                    name=match[2],
                    axis=f"a{match[1]}",
                )
                result.triggers[trigger.axis] = trigger
            else:
                print(f"don't know how to parse '{line}', skipping")
        return result
