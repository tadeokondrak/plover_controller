def get_keys_for_stroke(stroke_str: str) -> tuple[str, ...]:
    keys: list[str] = []
    passed_hyphen = False
    no_hyphen_keys = {"*", "#"}
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
