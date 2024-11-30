"""(re-)generate the spacy-models recipe"""
import jinja2
from subprocess import check_call
from pathlib import Path
import json
import fnmatch
import re

DEV_URL = "https://github.com/explosion/spacy-models"
VERSION = "3.8.0"
HEAD = "3d026eec88c53128ed71e10b399d0084361a11a3"
BUILD_NUMBER = "0"

# see https://github.com/conda-forge/spacy-models-feedstock/issues/2
SKIP_PATTERNS: list[str] = [
    # needs pymorphy3 https://github.com/conda-forge/staged-recipes/issues/21931
    "ru_core_*",
    "uk_core_*",
]

SKIP_PIP_CHECK: dict[str, dict[str, str]] = {
    # Example (keep this for the future)
    #
    # "fr": {
    #     "dep_news_trf": "transformers 4.19.4 has requirement tokenizers!=0.11.3,<0.13,>=0.11.1, but you have tokenizers 0.13.2."
    # }
}

EXTRA_SUBREQS: dict[str, list[str]] = {
    # Example (keep this for the future)
    #
    ## TODO: remove after
    ##       https://github.com/conda-forge/spacy-pkuseg-feedstock/pull/11
    ## "spacy-pkuseg": ["cython"]
}

EXTRA_PKG_REQS: dict[tuple[str, str], list[str]] = {
    # TODO: investigate
    # ImportError: tokenizers>=0.11.1,!=0.11.3,<0.13 is required for a normal functioning of this module, but found tokenizers==0.13.2.
    ("fr", "dep_news_trf"): ["tokenizers >=0.11.1,!=0.11.3,<0.13"]
}

# keep this synced with ``patch_meta.py``
REPLACE_REQS: dict[str, str] = {
    # https://github.com/conda-forge/spacy-models-feedstock/pull/7#issuecomment-2508892104
    # 99% convinced that this protobuf cap is based on some ancient issue that
    # we've either fixed, or which doesn't apply to conda-forge in the first place.
    "protobuf<3.21.0": "protobuf",
}

HERE = Path(__file__).parent
REPO = HERE.parent / "_spacy_models_repo"
TMPL = HERE.glob("*.j2")


def reqtify(raw):
    """split requirements on operators"""
    if "=" in raw:
        return " ".join(re.findall(r"(.*?)([><=!~\^].*)", raw)[0])
    return raw


def ensure_repo():
    """ensure that the repo is up-to-date"""
    if not REPO.exists():
        check_call(["git", "clone", DEV_URL, str(REPO)])
        check_call(["git", "fetch"], cwd=str(REPO))
        check_call(["git", "checkout", HEAD], cwd=str(REPO))


def update_recipe():
    all_metas = {
        p: json.load(p.open())
        for p in sorted((REPO / "meta").glob(f"*-{VERSION}.json"))
        if not any([fnmatch.fnmatch(p.name, pattern) for pattern in SKIP_PATTERNS])
    }

    lang_metas = {}

    for path, meta in all_metas.items():
        lang_metas.setdefault(meta["lang"], {})[path] = meta
        for pattern, extra_reqs in EXTRA_SUBREQS.items():
            for req in meta["requirements"]:
                if pattern in req:
                    print(
                        f"""- {path.name}:{req} needs extra: {", ".join(extra_reqs)}"""
                    )
                    meta["requirements"] += extra_reqs

        meta["requirements"] += EXTRA_PKG_REQS.get((meta["lang"], meta["name"]), [])
        meta["requirements"] = [REPLACE_REQS.get(r, r) for r in meta["requirements"]]
        meta["requirements"] = sorted(set(meta["requirements"]))

    context = dict(
        lang_metas=lang_metas,
        reqtify=reqtify,
        version=VERSION,
        dev_url=DEV_URL,
        build_number=BUILD_NUMBER,
        skip_pip_check=SKIP_PIP_CHECK,
    )

    for tmpl_path in TMPL:
        dest_path = tmpl_path.parent / tmpl_path.name.replace(".j2", "")
        template = jinja2.Template(
            tmpl_path.read_text(encoding="utf-8").strip(),
            # use alternate template delimiters to avoid conflicts
            block_start_string="<%",
            block_end_string="%>",
            variable_start_string="<<",
            variable_end_string=">>",
        )

        dest_path.write_text(
            template.render(**context).strip() + "\n", encoding="utf-8"
        )


def lint_recipe():
    check_call(["conda-smithy", "recipe-lint", str(HERE)])


if __name__ == "__main__":
    ensure_repo()
    update_recipe()
    lint_recipe()
