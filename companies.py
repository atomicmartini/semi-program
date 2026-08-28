"""기업 사전을 읽고, 분류별로 묶고, 회사 카드를 그린다.

회사 이름·별칭·분류·설명은 data/companies.md 에서만 온다. 모델이 만들지 않는다 (CLAUDE.md).
설명은 공식 사이트에서 옮기고 출처와 확인일을 함께 적는다 — 개념 사전과 같은 규칙이다.

**개념 사전과 다른 점 하나** — 출처가 없어도 회사를 목록에서 빼지 않는다.
설명만 비운다. 여기서는 목록 자체가 값이라, 회사를 감추면 분류표가 망가진다
(docs/slices/07-기업-탭.md).

read_company_map 과 companies_mentioned 는 link.py 에 있던 것을 옮겨 왔다.
회사 로직은 회사 파일에 둔다.
"""

import html
import re
from pathlib import Path

HERE = Path(__file__).parent
COMPANIES_FILE = HERE / "data" / "companies.md"

# 밸류체인 순서. 뉴스 카테고리(keywords.md)와 다른 체계다 — 뉴스는 '무엇에 관한 기사인가',
# 기업은 '밸류체인 어디에 있는 회사인가' 다. 임의로 늘리지 않는다 (CLAUDE.md).
CATEGORY_ORDER = (
    "메모리",
    "팹리스",
    "파운드리",
    "종합(IDM)",
    "OSAT·후공정",
    "장비",
    "소재·부품",
    "EDA·IP",
)

# | 정식명 | 별칭 | 분류 | 영문 | 국가 | 설명 | 출처 | 확인일 |
_COLUMNS = ("name", "aliases", "categories", "english", "country", "description", "source", "checked")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def slug(text: str) -> str:
    """주소로 쓸 이름. 영문을 쓰므로 한글이 주소에 안 들어간다 (glossary.py 와 같은 방식)."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _rows(markdown: str):
    """`## 정식명` 표의 칸들을 하나씩 내놓는다."""
    in_table = False
    for line in markdown.splitlines():
        s = line.strip()
        if s.startswith("## "):
            in_table = s.startswith("## 정식명")
            continue
        if not in_table or not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 2 or cells[0] in ("정식명", "---"):
            continue
        yield cells


def parse_companies(markdown: str) -> list[dict]:
    """표를 읽어 회사 목록을 만든다. 출처가 없으면 설명을 비운다."""
    out: list[dict] = []
    for cells in _rows(markdown):
        row = dict(zip(_COLUMNS, cells + [""] * (len(_COLUMNS) - len(cells))))

        link = _LINK.search(row["source"])
        has_source = bool(link) and bool(row["checked"]) and row["checked"] != "—"

        english = row["english"] or row["name"]
        out.append(
            {
                "name": row["name"],
                "aliases": [a.strip().lower() for a in row["aliases"].split(",") if a.strip()],
                "categories": [c.strip() for c in row["categories"].split(",") if c.strip()],
                "english": english,
                "country": row["country"],
                # 출처 없는 설명은 싣지 않는다 (CLAUDE.md). 회사는 그대로 남는다.
                "description": row["description"] if has_source else "",
                "source_label": link.group(1) if link else "",
                "source_url": link.group(2) if link else "",
                "checked": row["checked"] if has_source else "",
                "slug": slug(english),
            }
        )
    return out


def read_companies() -> list[dict]:
    return parse_companies(COMPANIES_FILE.read_text(encoding="utf-8"))


def by_category(rows: list[dict]) -> dict[str, list[dict]]:
    """분류별로 묶는다. 한 회사가 여러 칸에 나올 수 있다.

    빈 칸도 남긴다 — 무엇이 비었는지가 정보다 (카테고리 칩과 같은 판단).
    """
    grouped: dict[str, list[dict]] = {name: [] for name in CATEGORY_ORDER}
    for c in rows:
        for name in c["categories"]:
            grouped.setdefault(name, []).append(c)
    return grouped


# --- 기사에서 회사 찾기 (link.py 에서 옮겨 옴) -------------------------------


def read_company_map() -> dict[str, str]:
    """별칭·정식명을 소문자로 낮춰 정식명에 매핑한다. 사전에 없는 이름은 다루지 않는다."""
    mapping: dict[str, str] = {}
    for c in read_companies():
        mapping[c["name"].lower()] = c["name"]
        for alias in c["aliases"]:
            mapping[alias] = c["name"]
    return mapping


def companies_mentioned(text: str, company_map: dict[str, str]) -> set[str]:
    """글에 등장하는 정식명 집합. 긴 별칭부터 찾아야 짧은 이름이 긴 이름을 잘라먹지 않는다."""
    haystack = text.lower()
    found: set[str] = set()
    for alias in sorted(company_map, key=len, reverse=True):
        if alias in haystack:
            found.add(company_map[alias])
    return found


# --- 화면 -------------------------------------------------------------------

CHIP = """<a class="co" href="{prefix}company/{slug}.html">{name}<span class="n">{count}</span></a>"""

GROUP = """<div class="cgroup">
  <h2>{category}<span class="n">{total}</span></h2>
  <div class="colist">{chips}</div>
</div>
"""

EMPTY_GROUP = """<div class="cgroup">
  <h2>{category}<span class="n">0</span></h2>
  <p class="none">아직 등재된 회사가 없습니다.</p>
</div>
"""


def render_groups(grouped: dict[str, list[dict]], counts: dict[str, int], prefix: str = "") -> str:
    """분류별 회사 목록."""
    out = []
    for category, members in grouped.items():
        if not members:
            out.append(EMPTY_GROUP.format(category=html.escape(category)))
            continue
        chips = "".join(
            CHIP.format(
                prefix=prefix,
                slug=html.escape(c["slug"], quote=True),
                name=html.escape(c["name"]),
                count=counts.get(c["name"], 0),
            )
            for c in sorted(members, key=lambda c: -counts.get(c["name"], 0))
        )
        out.append(
            GROUP.format(category=html.escape(category), total=len(members), chips=chips)
        )
    return "".join(out)


PROFILE = """<div class="profile">
  <div class="ehead"><h2>{name}</h2> <span class="en">{english}</span>
    <span class="cat">{country}</span></div>
  <div class="ctags">{tags}</div>
  {description}
</div>
"""

DESC = """<p class="def">{text}</p>
<div class="meta">출처 <a href="{url}">{label}</a> · 확인일 {checked}</div>
"""

NO_DESC = '<p class="none">설명은 아직 출처를 확인하지 못했습니다.</p>'


def render_profile(company: dict) -> str:
    """회사 한 곳의 소개."""
    if company["description"]:
        description = DESC.format(
            text=html.escape(company["description"]),
            url=html.escape(company["source_url"], quote=True),
            label=html.escape(company["source_label"]),
            checked=html.escape(company["checked"]),
        )
    else:
        description = NO_DESC

    tags = "".join(
        f'<span class="ctag">{html.escape(c)}</span>' for c in company["categories"]
    )
    return PROFILE.format(
        name=html.escape(company["name"]),
        english=html.escape(company["english"]),
        country=html.escape(company["country"]),
        tags=tags,
        description=description,
    )
