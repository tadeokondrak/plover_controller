import re
from dataclasses import dataclass
from .util import get_keys_for_stroke, keys_to_stroke


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
class Alias:
    renamed: str
    actual: str


@dataclass
class Mappings:
    sticks: dict[str, Stick]
    hats: dict[str, Alias]
    buttons: dict[str, Alias]
    triggers: dict[str, Alias]
    unordered_mappings: list[tuple[list[str], tuple[str, ...]]]
    ordered_mappings: dict[tuple[str, ...], tuple[str, ...]]

    @classmethod
    def empty(cls) -> "Mappings":
        return Mappings(
            sticks={},
            hats={},
            buttons={},
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
            elif match := re.match(r"([a-z0-9,]+) ->\s*$", line):
                lhs = match[1].split(",")
                result.unordered_mappings.append((lhs, ()))
            elif match := re.match(r"(\w+)\(([a-z,]+)\) -> ([A-Z-*#]+)", line):
                result.ordered_mappings[
                    tuple(f"{match[1]}{pos}" for pos in match[2].split(","))
                ] = get_keys_for_stroke(match[3])
            elif match := re.match(r"button (\d+) is ([a-z0-9]+)", line):
                alias = Alias(
                    renamed=match[2],
                    actual=f"b{match[1]}",
                )
                result.buttons[alias.actual] = alias
            elif match := re.match(r"hat (\d+) is ([a-z0-9]+)", line):
                alias = Alias(
                    renamed=match[2],
                    actual=f"h{match[1]}",
                )
                result.hats[alias.actual] = alias
            elif match := re.match(r"trigger on axis (\d+) is ([a-z0-9]+)", line):
                alias = Alias(
                    renamed=match[2],
                    actual=f"a{match[1]}",
                )
                result.triggers[alias.actual] = alias
            else:
                print(f"don't know how to parse '{line}', skipping")
        return result

    def serialize(self) -> str:
        lines: list[str] = []

        for stick in self.sticks.values():
            segs = ",".join(stick.segments)
            x = stick.x_axis[1:]
            y = stick.y_axis[1:]
            offset = int(stick.offset) if stick.offset == int(stick.offset) else stick.offset
            lines.append(
                f"{stick.name} stick has segments ({segs}) on axes {x} and {y} offset by {offset} degrees"
            )

        if self.sticks and (self.triggers or self.hats or self.buttons):
            lines.append("")

        for alias in self.triggers.values():
            lines.append(f"trigger on axis {alias.actual[1:]} is {alias.renamed}")

        if self.triggers and (self.hats or self.buttons):
            lines.append("")

        for alias in self.hats.values():
            lines.append(f"hat {alias.actual[1:]} is {alias.renamed}")

        if self.hats and self.buttons:
            lines.append("")

        for alias in self.buttons.values():
            lines.append(f"button {alias.actual[1:]} is {alias.renamed}")

        if self.buttons and self.unordered_mappings:
            lines.append("")

        for lhs, rhs in self.unordered_mappings:
            stroke = keys_to_stroke(rhs)
            if stroke:
                lines.append(f"{','.join(lhs)} -> {stroke}")
            else:
                lines.append(f"{','.join(lhs)} ->")

        if self.unordered_mappings and self.ordered_mappings:
            lines.append("")

        for key_tuple, rhs in self.ordered_mappings.items():
            if not key_tuple:
                continue
            first = key_tuple[0]
            stick_name = ""
            for s in self.sticks.values():
                for seg in s.segments:
                    prefix = s.name
                    if first.startswith(prefix):
                        stick_name = prefix
                        break
                if stick_name:
                    break
            if not stick_name:
                stick_name = re.match(r"[a-z]+", first)
                stick_name = stick_name.group(0) if stick_name else first
            segments = ",".join(k[len(stick_name):] for k in key_tuple)
            lines.append(f"{stick_name}({segments}) -> {keys_to_stroke(rhs)}")

        lines.append("")
        return "\n".join(lines)
