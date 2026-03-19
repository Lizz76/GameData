from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
JSON_PATH = BASE_DIR / "games_data.json"
HTML_PATH = BASE_DIR / "GameInfo.html"
TEMPLATE_PATH = BASE_DIR / "game_template.html"
DISPLAY_FIELDS = [
    "游戏名",
    "标准题材",
    "运行环境",
    "开发商",
    "官网",
    "核心玩法",
    "美术风格",
    "亮点",
    "不足",
    "发行日期",
    "截图",
]
CATEGORY_RULES = [
    ("三国", ["三国"]),
    ("历史/中世纪", ["中世纪", "王国", "城堡", "战国", "历史", "帝国", "文明", "骑士", "封建"]),
    ("科幻", ["科幻", "星际", "太空", "银河", "宇宙", "赛博", "机甲", "异星"]),
    ("末日生存", ["末日", "丧尸", "废土", "冰河", "荒原", "生存"]),
    ("奇幻/魔幻", ["魔幻", "奇幻", "龙", "地下城", "神话", "维京", "海盗"]),
    ("现代战争", ["现代", "军事", "战争", "二战", "黑帮", "都市"]),
    ("经营模拟", ["经营", "模拟经营", "建造", "商业", "农场", "工厂", "城市"]),
    ("策略/4X", ["4x", "外交", "扩张", "星图", "文明发展"]),
    ("放置/休闲", ["放置", "挂机", "轻度", "休闲"]),
]


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    return str(value).strip()


def game_id(name: str) -> str:
    return "game-" + hashlib.sha1(name.encode("utf-8")).hexdigest()[:10]


def classify_category(record: dict[str, str]) -> str:
    blob = " ".join(
        normalize_text(record.get(field, ""))
        for field in ("题材", "游戏名", "核心玩法", "美术风格", "亮点", "不足")
    ).lower()
    for category, keywords in CATEGORY_RULES:
        if any(keyword.lower() in blob for keyword in keywords):
            return category
    return "其他"


def load_records(json_path: Path) -> list[dict[str, str]]:
    raw = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("games_data.json 必须是数组")
    records: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        record: dict[str, str] = {}
        for key, value in item.items():
            field = normalize_text(key)
            if field == "游戏发行日期":
                field = "发行日期"
            if field:
                record[field] = normalize_text(value)
        for field in DISPLAY_FIELDS:
            record.setdefault(field, "")
        record["标准题材"] = classify_category(record)
        record["游戏ID"] = game_id(record.get("游戏名", "未命名游戏"))
        records.append(record)
    return records


def is_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def render_value(field: str, value: str) -> str:
    text = value or "暂无"
    safe = escape(text)
    if field == "官网" and value and is_url(value):
        url = escape(value, quote=True)
        return (
            f'<a class="link-pill" href="{url}" target="_blank" '
            f'rel="noopener noreferrer">{safe}<span>↗</span></a>'
        )
    if field == "截图" and value and is_url(value):
        url = escape(value, quote=True)
        return (
            f'<a class="shot-pill" href="{url}" target="_blank" '
            f'rel="noopener noreferrer">查看截图<span>↗</span></a>'
        )
    return safe


def build_card(record: dict[str, str]) -> str:
    gid = escape(record["游戏ID"], quote=True)
    name = escape(record.get("游戏名", "未命名游戏"))
    category = escape(record.get("标准题材", "其他"))
    return f"""
<article class="game-card" data-game-id="{gid}" data-category="{escape(record.get('标准题材', ''), quote=True)}" data-release-date="{escape(record.get('发行日期', ''), quote=True)}">
  <div class="card-head">
    <div class="card-title-wrap">
      <div class="card-topline"><span class="played-flag">✓ 已玩</span></div>
      <h2><span>{name}</span><span class="title-check">✓</span></h2>
      <div class="card-subline">
        <span class="meta-pill">{escape(record.get('开发商', '暂无'))}</span>
        <span class="meta-pill">{escape(record.get('运行环境', '暂无'))}</span>
        <span class="meta-pill">{escape(record.get('发行日期', '暂无'))}</span>
      </div>
    </div>
    <div class="card-badges"><span class="badge badge-primary">{category}</span><span class="badge">{escape(record.get('美术风格', '暂无'))}</span></div>
  </div>
  <div class="card-actions"><button class="mini-action" type="button" onclick="addCardToPlaylist('{gid}')">加入游玩清单</button></div>
  <div class="field-grid">
    <div class="field field-wide"><div class="field-label">官网</div><div class="field-value">{render_value('官网', record.get('官网', ''))}</div></div>
    <div class="field field-wide"><div class="field-label">核心玩法</div><div class="field-value">{render_value('核心玩法', record.get('核心玩法', ''))}</div></div>
    <div class="field field-highlight"><div class="field-label">亮点</div><div class="field-value">{render_value('亮点', record.get('亮点', ''))}</div></div>
    <div class="field field-warning"><div class="field-label">不足</div><div class="field-value">{render_value('不足', record.get('不足', ''))}</div></div>
    <div class="field field-compact"><div class="field-label">截图</div><div class="field-value">{render_value('截图', record.get('截图', ''))}</div></div>
  </div>
</article>"""


def build_chips(records: list[dict[str, str]]) -> str:
    categories = sorted({record["标准题材"] for record in records if record.get("标准题材")})
    chips = ['<button class="chip is-active" type="button" onclick="filterByCategory(\'\', this)">全部</button>']
    for category in categories:
        safe = escape(category)
        chips.append(
            f'<button class="chip" type="button" data-category="{safe}" '
            f'onclick="filterByCategory(this.dataset.category, this)">{safe}</button>'
        )
    return "\n".join(chips)


def build_game_index(records: list[dict[str, str]]) -> str:
    payload = [
        {
            "id": record["游戏ID"],
            "name": record["游戏名"],
            "category": record["标准题材"],
            "developer": record["开发商"],
            "releaseDate": record["发行日期"],
        }
        for record in records
    ]
    return json.dumps(payload, ensure_ascii=False)


def build_html(json_path: Path, html_path: Path) -> tuple[int, int, str]:
    records = load_records(json_path)
    if not records:
        raise ValueError("games_data.json 里没有可生成的数据")
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    category_count = len({record["标准题材"] for record in records if record.get("标准题材")})
    updated_at = datetime.fromtimestamp(json_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    html = (
        template.replace("__CARDS__", "\n".join(build_card(record) for record in records))
        .replace("__CHIPS__", build_chips(records))
        .replace("__GAME_INDEX__", build_game_index(records))
        .replace("__GAME_COUNT__", str(len(records)))
        .replace("__CATEGORY_COUNT__", str(category_count))
        .replace("__UPDATED_AT__", updated_at)
    )
    html_path.write_text(html, encoding="utf-8")
    return len(records), category_count, updated_at


def sync_once() -> None:
    games, categories, _ = build_html(JSON_PATH, HTML_PATH)
    print(f"已同步 {games} 条记录，{categories} 个题材大类 -> {HTML_PATH}")


def watch_json(interval: float = 1.0) -> None:
    last_stamp = JSON_PATH.stat().st_mtime_ns
    sync_once()
    print("正在监听 games_data.json，修改后会自动同步，按 Ctrl+C 退出。")
    while True:
        try:
            current_stamp = JSON_PATH.stat().st_mtime_ns
        except FileNotFoundError:
            time.sleep(interval)
            continue
        if current_stamp != last_stamp:
            try:
                sync_once()
                last_stamp = current_stamp
            except Exception as exc:
                print(f"同步失败：{exc}")
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="从 games_data.json 生成 GameInfo.html")
    parser.add_argument("--watch", action="store_true", help="持续监听 JSON 文件并自动同步 HTML")
    parser.add_argument("--interval", type=float, default=1.0, help="监听间隔，单位秒")
    args = parser.parse_args()
    if not JSON_PATH.exists():
        raise FileNotFoundError(f"找不到 JSON 文件：{JSON_PATH}")
    if args.watch:
        watch_json(args.interval)
    else:
        sync_once()


if __name__ == "__main__":
    main()
