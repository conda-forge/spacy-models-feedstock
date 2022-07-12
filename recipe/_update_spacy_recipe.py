"""(re-)generate the spacy-models recipe"""
import jinja2
from subprocess import check_call
from pathlib import Path
import json
import fnmatch
import re

DEV_URL = "https://github.com/explosion/spacy-models"
VERSION = "3.4.0"
HEAD = "125c74d3ba00db1ac85c690112c210e0f13a6911"
BUILD_NUMBER = "0"

SKIP_PATTERNS = [
    # needs sudachipy
    "ja_core*"
]
EXTRA_REQS = {
    # TODO: remove after https://github.com/conda-forge/spacy-pkuseg-feedstock/pull/11
    # "spacy-pkuseg": ["cython"]
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
        for pattern, extra_reqs in EXTRA_REQS.items():
            if any(pattern in req for req in meta["requirements"]):
                print(f"""- {path.name} needs extra: {", ".join(extra_reqs)}""")
                meta["requirements"] += extra_reqs
        meta["requirements"] = sorted(set(meta["requirements"]))

    context = dict(
        lang_metas=lang_metas,
        reqtify=reqtify,
        version=VERSION,
        dev_url=DEV_URL,
        build_number=BUILD_NUMBER,
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
