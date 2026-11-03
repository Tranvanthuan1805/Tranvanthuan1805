"""Generate pixel-style GitHub stat cards (SVG) from the GitHub GraphQL API."""
import json, os, sys, urllib.request, datetime

USER = os.environ.get("GH_USER", "Tranvanthuan1805")
TOKEN = os.environ["GITHUB_TOKEN"]
OUT = sys.argv[1] if len(sys.argv) > 1 else "dist"
os.makedirs(OUT, exist_ok=True)

QUERY = """
query($login:String!){user(login:$login){
  followers{totalCount}
  pullRequests{totalCount}
  issues{totalCount}
  repositories(ownerAffiliations:OWNER,isFork:false,first:100,orderBy:{field:PUSHED_AT,direction:DESC}){
    totalCount
    nodes{stargazerCount languages(first:6,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}}}
  }
  contributionsCollection{
    totalCommitContributions
    contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}
  }
}}"""
req = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
    headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "profile-stats"},
)
data = json.load(urllib.request.urlopen(req, timeout=30))
if "errors" in data:
    sys.exit(json.dumps(data["errors"]))
u = data["data"]["user"]
repos = u["repositories"]["nodes"]
stars = sum(r["stargazerCount"] for r in repos)
cc = u["contributionsCollection"]
days = [d for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
total = cc["contributionCalendar"]["totalContributions"]

# streaks
today = datetime.date.today().isoformat()
counts = [(d["date"], d["contributionCount"]) for d in days if d["date"] <= today]
longest = cur = 0
for _, c in counts:
    cur = cur + 1 if c > 0 else 0
    longest = max(longest, cur)
current = 0
for i, (dt, c) in enumerate(reversed(counts)):
    if c > 0:
        current += 1
    elif i == 0:
        continue
    else:
        break

# languages
langs = {}
for r in repos:
    for e in r["languages"]["edges"]:
        n = e["node"]
        langs.setdefault(n["name"], [0, n["color"] or "#64748b"])[0] += e["size"]
top = sorted(langs.items(), key=lambda kv: -kv[1][0])[:6]
lsum = sum(v[0] for _, v in top) or 1

NAVY = "#0f172a"
F = "Courier New,Courier,monospace"
def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
def svg(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'shape-rendering="crispEdges"><title>{esc(title)}</title><g font-family="{F}" font-weight="700">{body}</g></svg>')
def panel(x, y, w, h):
    return (f'<rect x="{x+8}" y="{y+8}" width="{w}" height="{h}" fill="{NAVY}"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#fff" stroke="{NAVY}" stroke-width="4"/>'
            f'<rect x="{x+4}" y="{y+4}" width="{w-8}" height="6" fill="#e0f2fe"/>')

# stats card
rows = [("TOTAL STARS", stars), ("COMMITS (YEAR)", cc["totalCommitContributions"]), ("PULL REQUESTS", u["pullRequests"]["totalCount"]),
        ("ISSUES", u["issues"]["totalCount"]), ("REPOSITORIES", u["repositories"]["totalCount"]), ("FOLLOWERS", u["followers"]["totalCount"])]
b = panel(12, 12, 576, 270) + f'<text x="36" y="50" font-size="16" letter-spacing="3" fill="#4338ca">PLAYER STATS · {esc(USER)}</text>'
for i, (k, v) in enumerate(rows):
    y = 90 + i * 30
    b += (f'<rect x="36" y="{y-12}" width="12" height="12" fill="#fbbf24" stroke="#b45309" stroke-width="2"/>'
          f'<text x="62" y="{y}" font-size="15" fill="#475569">{k}</text><text x="560" y="{y}" text-anchor="end" font-size="17" fill="{NAVY}">{v:,}</text>')
open(f"{OUT}/stats-card.svg", "w", encoding="utf-8").write(svg(604, 296, b, "GitHub stats"))

# languages card
b = panel(12, 12, 576, 270) + '<text x="36" y="50" font-size="16" letter-spacing="3" fill="#4338ca">TOP LANGUAGES</text>'
for i, (n, (sz, col)) in enumerate(top):
    y = 74 + i * 32
    pct = sz / lsum
    b += (f'<text x="36" y="{y+16}" font-size="14" fill="{NAVY}">{esc(n)}</text>'
          f'<rect x="170" y="{y}" width="320" height="20" fill="#e2e8f0" stroke="{NAVY}" stroke-width="3"/>'
          f'<rect x="173" y="{y+3}" width="{int(314*pct)}" height="14" fill="{esc(col)}"/>'
          f'<text x="560" y="{y+16}" text-anchor="end" font-size="14" fill="{NAVY}">{pct*100:.0f}%</text>')
open(f"{OUT}/langs-card.svg", "w", encoding="utf-8").write(svg(604, 296, b, "Top languages"))

# streak card
cells = [("TOTAL CONTRIBUTIONS", total, "#bae6fd"), ("CURRENT STREAK", current, "#fde68a"), ("LONGEST STREAK", longest, "#bbf7d0")]
b = ""
for i, (k, v, c) in enumerate(cells):
    x = 12 + i * 400
    b += panel(x, 12, 376, 130) + f'<rect x="{x+4}" y="{12+10}" width="368" height="0" fill="none"/>'
    b += (f'<text x="{x+188}" y="{12+70}" text-anchor="middle" font-size="44" fill="{NAVY}">{v:,}</text>'
          f'<text x="{x+188}" y="{12+108}" text-anchor="middle" font-size="14" letter-spacing="2" fill="#4338ca">{k}</text>')
open(f"{OUT}/streak-card.svg", "w", encoding="utf-8").write(svg(1200, 162, b, "Contribution streak"))

# activity: last 26 weeks, weekly totals
weeks = cc["contributionCalendar"]["weeks"][-26:]
wt = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in weeks]
mx = max(wt + [1])
b = panel(12, 12, 1176, 210) + '<text x="36" y="50" font-size="16" letter-spacing="3" fill="#4338ca">ACTIVITY · LAST 26 WEEKS</text>'
bw = 1100 / max(len(wt), 1)
for i, v in enumerate(wt):
    h = int(110 * v / mx)
    x = 44 + i * bw
    b += f'<rect x="{x:.0f}" y="{190-h}" width="{bw-8:.0f}" height="{max(h,4)}" fill="{"#38bdf8" if i % 2 == 0 else "#818cf8"}" stroke="{NAVY}" stroke-width="2"/>'
open(f"{OUT}/activity-card.svg", "w", encoding="utf-8").write(svg(1200, 242, b, "Weekly contribution activity"))
print("ok", stars, total, current, longest)
