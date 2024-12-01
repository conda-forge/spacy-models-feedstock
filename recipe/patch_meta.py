import sys
import json

from pathlib import Path

UTF8 = {"encoding": "utf-8"}
META_JSON = Path.cwd() / "meta.json"

# keep this synced with ``_update_spacy_recipe.py``
REPLACE_REQS: dict[str, str] = {
    # https://github.com/conda-forge/spacy-models-feedstock/pull/7#issuecomment-2508892104
    # 99% convinced that this protobuf cap is based on some ancient issue that
    # we've either fixed, or which doesn't apply to conda-forge in the first place.
    "protobuf<3.21.0": "protobuf",
}


def main() -> int:
    meta = json.loads(META_JSON.read_text(**UTF8))
    old_reqs = {*meta["requirements"]}
    new_reqs = {REPLACE_REQS.get(r, r) for r in meta["requirements"]}
    if old_reqs == new_reqs:
        print("Dependencies are unchanged:\n", old_reqs)
    else:
        meta["requirements"] = sorted(new_reqs)
        print("Updated dependencies:\n", old_reqs, "\n", new_reqs)
        META_JSON.write_text(json.dumps(meta, indent=2), **UTF8)
    return 0


if __name__ == "__main__":
    sys.exit(main())
