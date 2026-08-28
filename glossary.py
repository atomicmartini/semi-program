"""개념 사전을 읽고, 기사 글 속의 용어에 링크를 건다.

설명은 data/glossary.md 에서만 온다. 모델이 만들지 않는다 (CLAUDE.md).
출처와 확인일이 없는 항목은 싣지 않는다.
"""

import html
import re
from pathlib import Path

HERE = Path(__file__).parent
GLOSSARY_FILE = HERE / "data" / "glossary.md"

CONCEPTS_PAGE = "concepts.html"

# | 용어 | 영문 | 별칭 | 분류 | 설명 | 출처 | 확인일 |
_COLUMNS = ("term", "english", "aliases", "category", "definition", "source", "checked")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
# 출처 칸 끝의 꼬리표. 표 안에서는 백틱으로 감싸 링크의 대괄호와 구분한다.
_TAG = re.compile(r"`\[([^\]]+)\]`")
_LATIN = re.compile(r"^[a-z0-9 .,'&-]+$")


def parse_source(cell: str) -> tuple[str, str, str]:
    """출처 칸에서 (이름, 주소, 꼬리표) 를 읽는다.

    꼬리표는 `[공식]` 또는 `[2차]` — 표준화 기구·제조사 공식 페이지에서 온 설명인지,
    업체 해설 글이나 칼럼에서 온 설명인지를 화면에서 가르기 위한 것이다.
    데이터에만 두고 화면에 안 내보내면 둘을 가른 의미가 없다 (data/glossary.md).
    """
    link = _LINK.search(cell)
    if not link:
        return "", "", ""
    tag = _TAG.search(cell)
    return link.group(1), link.group(2), tag.group(1) if tag else ""


def _bounded(alias: str) -> str:
    """용어를 찾을 정규식 조각.

    **영문 용어는 낱말 경계를 요구한다** — `ASIC` 이 `basic`, `SoC` 가 `association`,
    `SiP` 가 `gossip` 안에서 잡힌다. companies.py 가 같은 버그를 이미 겪었다
    (`intel` 이 `intelligent` 안에서 잡혀 23건 중 7건이 거짓이었다).
    한국어는 조사가 붙으므로(`패키징을`) 낱말 경계를 쓰면 못 찾는다. 그대로 둔다.
    """
    escaped = re.escape(alias)
    if _LATIN.match(alias.lower()):
        return rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"
    return escaped


def _slug(text: str) -> str:
    """앵커로 쓸 id. 영문 이름을 쓰므로 한글이 주소에 안 들어간다."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def read_terms() -> list[dict]:
    """등재된 개념을 읽는다. 출처나 확인일이 비면 건너뛴다."""
    terms: list[dict] = []
    in_table = False

    for line in GLOSSARY_FILE.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("## "):
            in_table = s.startswith("## 등재된")
            continue
        if not in_table or not s.startswith("|"):
            continue

        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < len(_COLUMNS) or cells[0] in ("용어", "---"):
            continue

        row = dict(zip(_COLUMNS, cells))

        # 출처와 확인일이 없으면 싣지 않는다 (CLAUDE.md).
        source_label, source_url, source_tag = parse_source(row["source"])
        if not source_url or not row["checked"] or row["checked"] == "—":
            continue

        aliases = [a.strip() for a in row["aliases"].split(",") if a.strip()]
        terms.append(
            {
                "term": row["term"],
                "english": row["english"],
                "category": row["category"],
                "definition": row["definition"],
                "source_label": source_label,
                "source_url": source_url,
                "source_tag": source_tag,
                "checked": row["checked"],
                "id": _slug(row["english"] or row["term"]),
                # 긴 것부터 찾아야 '패키징' 이 '고급 패키징' 을 잘라먹지 않는다
                "patterns": sorted({row["term"], row["english"], *aliases}, key=len, reverse=True),
            }
        )
    return terms


def link_terms(text: str, terms: list[dict], page_prefix: str = "") -> str:
    """이미 HTML escape 된 글에서 용어를 찾아 링크로 감싼다.

    한 용어당 처음 나온 한 번만 건다. 같은 단어가 열 번 나오면 화면이 어지럽다.
    """
    if not terms:
        return text

    lookup: dict[str, dict] = {}
    for t in terms:
        for p in t["patterns"]:
            lookup.setdefault(p.lower(), t)

    pattern = re.compile(
        "|".join(_bounded(p) for p in sorted(lookup, key=len, reverse=True)),
        re.IGNORECASE,
    )
    used: set[str] = set()

    def swap(m: re.Match) -> str:
        t = lookup.get(m.group(0).lower())
        if not t or t["id"] in used:
            return m.group(0)
        used.add(t["id"])
        return f'<a class="term" href="{page_prefix}{CONCEPTS_PAGE}#{t["id"]}">{m.group(0)}</a>'

    return pattern.sub(swap, text)


ENTRY = """<div class="entry" id="{id}">
  <div class="ehead"><h2>{term}</h2> <span class="en">{english}</span>
    <span class="cat">{category}</span></div>
  <p class="def">{definition}</p>
  <div class="meta">출처 <a href="{source_url}">{source_label}</a>{tag} · 확인일 {checked}</div>
</div>
"""

TAG = ' <span class="stag">{tag}</span>'


def render_entries(terms: list[dict]) -> str:
    return "".join(
        ENTRY.format(
            id=t["id"],
            term=html.escape(t["term"]),
            english=html.escape(t["english"]),
            category=html.escape(t["category"]),
            definition=html.escape(t["definition"]),
            source_url=html.escape(t["source_url"], quote=True),
            source_label=html.escape(t["source_label"]),
            # 꼬리표가 없는 항목은 빈 자리로 둔다 — 빈 대괄호를 찍지 않는다
            tag=TAG.format(tag=html.escape(t["source_tag"])) if t.get("source_tag") else "",
            checked=html.escape(t["checked"]),
        )
        for t in terms
    )
