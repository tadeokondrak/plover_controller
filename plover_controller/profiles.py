import json
from pathlib import Path
from typing import Optional

from plover.oslayer.config import CONFIG_DIR
from plover.resource import resource_exists, resource_filename

PROFILES_FILENAME = "controller_profiles.json"

BUILTIN_PROFILES = {
    "Xbox Elite (Built-in)": "asset:plover_controller:assets/profiles/xbox_elite.txt",
    "Xbox (Built-in)": "asset:plover_controller:assets/profiles/xbox.txt",
    "PlayStation (Built-in)": "asset:plover_controller:assets/profiles/playstation.txt",
    "Generic (Built-in)": "asset:plover_controller:assets/profiles/generic.txt",
}


def get_profiles_path() -> Path:
    return Path(CONFIG_DIR) / PROFILES_FILENAME


def _read_profiles_file() -> dict:
    path = get_profiles_path()
    if not path.exists():
        return {"version": 1, "profiles": {}}
    with open(path, "r") as f:
        return json.load(f)


def _write_profiles_file(data: dict) -> None:
    path = get_profiles_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_builtin_profile(name: str) -> Optional[str]:
    asset_path = BUILTIN_PROFILES.get(name)
    if asset_path is None or not resource_exists(asset_path):
        return None
    with open(resource_filename(asset_path), "r") as f:
        return f.read()


def load_user_profiles() -> dict[str, str]:
    data = _read_profiles_file()
    return {name: p["mapping"] for name, p in data.get("profiles", {}).items()}


def list_profile_names() -> list[str]:
    builtin = sorted(BUILTIN_PROFILES.keys())
    user = sorted(load_user_profiles().keys())
    return builtin + user


def load_profile(name: str) -> Optional[str]:
    if name in BUILTIN_PROFILES:
        return load_builtin_profile(name)
    user_profiles = load_user_profiles()
    return user_profiles.get(name)


def save_profile(name: str, mapping_text: str) -> None:
    data = _read_profiles_file()
    data.setdefault("profiles", {})[name] = {"mapping": mapping_text}
    _write_profiles_file(data)


def delete_profile(name: str) -> bool:
    if name in BUILTIN_PROFILES:
        return False
    data = _read_profiles_file()
    if name in data.get("profiles", {}):
        del data["profiles"][name]
        _write_profiles_file(data)
        return True
    return False


def is_builtin(name: str) -> bool:
    return name in BUILTIN_PROFILES


def export_profile(name: str, path: Path) -> bool:
    mapping = load_profile(name)
    if mapping is None:
        return False
    with open(path, "w") as f:
        f.write(mapping)
    return True


def import_profile(path: Path) -> tuple[str, str]:
    with open(path, "r") as f:
        mapping = f.read()
    name = path.stem
    return name, mapping
