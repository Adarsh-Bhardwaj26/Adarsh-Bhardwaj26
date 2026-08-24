"""
Fetches public LeetCode stats via LeetCode's own GraphQL API and renders
a themed SVG card, committed to the repo by a GitHub Action (no third-party
live rendering server involved).
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error

USERNAME = os.environ.get("LEETCODE_USERNAME", "Adarsh-Bhardwaj26")
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "leetcode-stats.svg")

GRAPHQL_URL = "https://leetcode.com/graphql"

QUERY = """
query getUserProfile($username: String!) {
  allQuestionsCount {
    difficulty
    count
  }
  matchedUser(username: $username) {
    username
    profile {
      ranking
      reputation
    }
    submitStatsGlobal {
      acSubmissionNum {
        difficulty
        count
      }
    }
  }
}
"""


def fetch_stats(username: str) -> dict:
    payload = json.dumps({
        "query": QUERY,
        "variables": {"username": username},
    }).encode("utf-8")

    req = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Referer": f"https://leetcode.com/{username}/",
            "User-Agent": "Mozilla/5.0 (GitHub Actions LeetCode Stats Bot)",
        },
        method="POST",
    )
    last_err = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            break
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            last_err = e
            time.sleep(2 ** attempt)  # 1s, 2s, 4s, 8s
    else:
        raise RuntimeError(f"LeetCode API unreachable after retries: {last_err}")

    if body.get("errors"):
        raise RuntimeError(f"LeetCode API error: {body['errors']}")

    data = body.get("data")
    if not data or not data.get("matchedUser"):
        raise RuntimeError(f"No user found for '{username}'")

    return data


def parse_counts(data: dict) -> dict:
    totals = {d["difficulty"]: d["count"] for d in data["allQuestionsCount"]}
    solved = {
        d["difficulty"]: d["count"]
        for d in data["matchedUser"]["submitStatsGlobal"]["acSubmissionNum"]
    }
    profile = data["matchedUser"]["profile"]

    return {
        "easy_solved": solved.get("Easy", 0),
        "easy_total": totals.get("Easy", 0),
        "medium_solved": solved.get("Medium", 0),
        "medium_total": totals.get("Medium", 0),
        "hard_solved": solved.get("Hard", 0),
        "hard_total": totals.get("Hard", 0),
        "total_solved": solved.get("All", 0),
        "total_questions": totals.get("All", 0),
        "ranking": profile.get("ranking", 0),
    }


def bar(x, y, width, pct, color):
    filled = max(0, min(width, round(width * pct / 100))) if pct else 0
    return f"""
    <rect x="{x}" y="{y}" width="{width}" height="8" rx="4" fill="#2a2b3d"/>
    <rect x="{x}" y="{y}" width="{filled}" height="8" rx="4" fill="{color}"/>
    """


def render_svg(stats: dict, username: str) -> str:
    total_pct = (stats["total_solved"] / stats["total_questions"] * 100) if stats["total_questions"] else 0
    easy_pct = (stats["easy_solved"] / stats["easy_total"] * 100) if stats["easy_total"] else 0
    med_pct = (stats["medium_solved"] / stats["medium_total"] * 100) if stats["medium_total"] else 0
    hard_pct = (stats["hard_solved"] / stats["hard_total"] * 100) if stats["hard_total"] else 0

    bar_x = 190
    bar_w = 270

    svg = f"""<svg width="495" height="195" viewBox="0 0 495 195" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{username}'s LeetCode Stats">
  <defs>
    <linearGradient id="ring" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00F7FF"/>
      <stop offset="100%" stop-color="#6A00FF"/>
    </linearGradient>
  </defs>

  <rect x="0.5" y="0.5" width="494" height="194" rx="14" fill="#1a1b27" stroke="#2a2b3d"/>

  <text x="25" y="35" font-family="Segoe UI, Verdana, sans-serif" font-size="18" font-weight="600" fill="#ffffff">
    {username}'s LeetCode Stats
  </text>
  <line x1="25" y1="45" x2="470" y2="45" stroke="#2a2b3d" stroke-width="1"/>

  <!-- Ring: overall solved percentage -->
  <g transform="translate(85,105)">
    <circle r="52" fill="none" stroke="#2a2b3d" stroke-width="10"/>
    <circle r="52" fill="none" stroke="url(#ring)" stroke-width="10"
      stroke-dasharray="{round(2*3.14159*52*total_pct/100)} 999"
      stroke-linecap="round" transform="rotate(-90)"/>
    <text x="0" y="-2" text-anchor="middle" font-family="Segoe UI, Verdana, sans-serif" font-size="24" font-weight="700" fill="#ffffff">{stats['total_solved']}</text>
    <text x="0" y="18" text-anchor="middle" font-family="Segoe UI, Verdana, sans-serif" font-size="11" fill="#9a9ab0">/ {stats['total_questions']} Solved</text>
  </g>

  <!-- Difficulty bars -->
  <text x="{bar_x}" y="72" font-family="Segoe UI, Verdana, sans-serif" font-size="12" fill="#00e396">Easy</text>
  <text x="{bar_x+bar_w-40}" y="72" font-family="Segoe UI, Verdana, sans-serif" font-size="12" fill="#9a9ab0" text-anchor="end">{stats['easy_solved']}/{stats['easy_total']}</text>
  {bar(bar_x, 78, bar_w, easy_pct, "#00e396")}

  <text x="{bar_x}" y="108" font-family="Segoe UI, Verdana, sans-serif" font-size="12" fill="#ffb020">Medium</text>
  <text x="{bar_x+bar_w-40}" y="108" font-family="Segoe UI, Verdana, sans-serif" font-size="12" fill="#9a9ab0" text-anchor="end">{stats['medium_solved']}/{stats['medium_total']}</text>
  {bar(bar_x, 114, bar_w, med_pct, "#ffb020")}

  <text x="{bar_x}" y="144" font-family="Segoe UI, Verdana, sans-serif" font-size="12" fill="#ff4d4f">Hard</text>
  <text x="{bar_x+bar_w-40}" y="144" font-family="Segoe UI, Verdana, sans-serif" font-size="12" fill="#9a9ab0" text-anchor="end">{stats['hard_solved']}/{stats['hard_total']}</text>
  {bar(bar_x, 150, bar_w, hard_pct, "#ff4d4f")}

  <text x="{bar_x}" y="178" font-family="Segoe UI, Verdana, sans-serif" font-size="11" fill="#9a9ab0">Global Rank: #{stats['ranking']:,}</text>
</svg>"""
    return svg


def main():
    try:
        data = fetch_stats(USERNAME)
        stats = parse_counts(data)
        svg = render_svg(stats, USERNAME)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"Wrote {OUTPUT_PATH} for user {USERNAME}: {stats}")
    except Exception as e:
        print(f"Failed to generate LeetCode SVG: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
