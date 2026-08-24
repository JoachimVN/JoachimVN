"""Collect the profile numbers used by the README cards.

Shells out to the GitHub CLI (available in Actions and locally) and writes
assets/stats.json. Kept separate from generate.py so the drawing code stays
offline and deterministic.

The language mix is counted per file from each repo's git tree rather than
through the /languages endpoint. That endpoint counts every committed byte,
which here means one 2.6 MB generated file (Music-Popularity-Index's
output/index.html, vendored a second time into Portfolio) accounts for ~95%
of all HTML and drowns out everything hand-written. Counting per file lets
build output be skipped while keeping the HTML and CSS actually authored.
"""
import json
import os
import re
import subprocess
import sys

USER = "JoachimVN"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "stats.json")

EXTENSIONS = {
    ".ts": "TypeScript", ".tsx": "TypeScript",
    ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".java": "Java", ".py": "Python", ".cs": "C#", ".sql": "SQL",
    ".css": "CSS", ".scss": "CSS", ".html": "HTML", ".htm": "HTML",
    ".sh": "Shell", ".ps1": "PowerShell", ".bat": "Batchfile", ".cmd": "Batchfile",
}

# Directory names that hold build output or third-party code, at any depth.
GENERATED_DIRS = {"node_modules", "dist", "build", "out", "output", "target",
                  "coverage", "vendor", ".next", "bin", "obj"}

# Portfolio is a deployment target: everything under projects/ is a built copy of
# another repo in this list, so counting it would count the same work twice.
VENDORED_PREFIXES = {"Portfolio": ("projects/",)}

# Vite and friends emit bundles as name-CONTENTHASH.js; those are build output too.
HASHED_ASSET = re.compile(r"-[A-Za-z0-9_-]{8,}\.(js|mjs|cjs|css)$")

# Anything under this share of the total is folded into a single "Other" slice.
OTHER_THRESHOLD = 0.015


def gh(*args):
    env = dict(os.environ, MSYS_NO_PATHCONV="1")
    out = subprocess.run(("gh",) + args, capture_output=True, text=True,
                         encoding="utf-8", env=env)
    if out.returncode != 0:
        raise RuntimeError(" ".join(args) + " -> " + out.stderr.strip())
    return json.loads(out.stdout)


def search_count(query):
    """Counts include private work, so this needs a token that can see it.

    The Actions GITHUB_TOKEN only sees public repos and undercounts by whatever
    is private. The workflow therefore passes secrets.STATS_TOKEN when it exists.
    never_shrink() below is what stops a weaker token quietly lowering the
    figures on the profile."""
    endpoint = "search/commits" if "type:" not in query else "search/issues"
    return gh("api", "-X", "GET", endpoint, "-f", "q=" + query)["total_count"]


# A token losing sight of every private repo takes about 10% off the commit
# count. Different tokens legitimately differ by a percent or two, because an
# organisation can decline access that the owner's own token has. So catch the
# cliff, not the wobble.
MAX_DROP = 0.05


def no_big_drop(data):
    """Refuse to write figures that fell off a cliff.

    The counts should grow. A large fall means the token stopped seeing
    something rather than that the work disappeared, which is what happened when
    the first scheduled run used GITHUB_TOKEN and 2869 commits became 2598.
    Small falls are normal: a personal token and an org-restricted one disagree
    slightly about private repos, and that is not worth failing over."""
    if not os.path.exists(OUT):
        return
    with open(OUT, encoding="utf-8") as f:
        previous = json.load(f)
    for key in ("commits", "prs", "issues"):
        was, now = previous.get(key, 0), data[key]
        allowed = max(20, was * MAX_DROP)
        if was - now > allowed:
            raise RuntimeError(
                "%s fell from %s to %s, past the %.0f it is allowed to move. That "
                "usually means the token cannot see private repos. Check that the "
                "STATS_TOKEN secret exists and has repo scope. Keeping the "
                "previous figures." % (key, was, now, allowed))


def is_authored(path, repo):
    parts = path.split("/")
    if any(part in GENERATED_DIRS for part in parts[:-1]):
        return False
    if any(path.startswith(prefix) for prefix in VENDORED_PREFIXES.get(repo, ())):
        return False
    name = parts[-1]
    return (".min." not in name and not name.endswith("-lock.json")
            and not HASHED_ASSET.search(name))


def count_languages(repo):
    tree = gh("api", "repos/%s/%s/git/trees/%s?recursive=1"
              % (USER, repo["name"], repo["default_branch"]))
    sizes = {}
    for entry in tree.get("tree", []):
        if entry["type"] != "blob" or not is_authored(entry["path"], repo["name"]):
            continue
        language = EXTENSIONS.get(os.path.splitext(entry["path"])[1].lower())
        if language:
            sizes[language] = sizes.get(language, 0) + entry.get("size", 0)
    return sizes


def main():
    user = gh("api", "users/" + USER)
    repos = [r for r in gh("api", "users/%s/repos?per_page=100" % USER) if not r["fork"]]

    languages = {}
    for repo in repos:
        for name, size in count_languages(repo).items():
            languages[name] = languages.get(name, 0) + size

    total = sum(languages.values()) or 1
    mix, other = {}, 0
    for name, size in sorted(languages.items(), key=lambda kv: -kv[1]):
        if size / total < OTHER_THRESHOLD:
            other += size
        else:
            mix[name] = size
    if other:
        mix["Other"] = other

    data = {
        "commits": search_count("author:" + USER),
        "prs": search_count("author:%s type:pr" % USER),
        "issues": search_count("author:%s type:issue" % USER),
        "repos": len(repos),
        "stars": sum(r["stargazers_count"] for r in repos),
        "followers": user["followers"],
        "languages": mix,
    }

    no_big_drop(data)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print("wrote", OUT)
    for key, value in data.items():
        if key != "languages":
            print("  %-10s %s" % (key, value))
    for name, size in mix.items():
        print("  %-12s %5.1f%%  (%s bytes)" % (name, 100 * size / total, format(size, ",")))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:                     # keep the last good stats.json
        print("stats refresh failed:", exc, file=sys.stderr)
        sys.exit(1)
