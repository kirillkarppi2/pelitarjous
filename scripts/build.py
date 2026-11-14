"""Rakentaa sivuston dist/-kansioon: etusivu, oma sivu jokaiselle pelille, tyylit ja sitemap."""
import csv, html, json, os, shutil
from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")
read = lambda *p: open(os.path.join(ROOT, *p), encoding="utf-8").read()
esc = lambda s: html.escape(str(s), quote=True)
eur = lambda v: f"{v:,.2f}".replace(",", " ").replace(".", ",") + " €"

owner, _, repo = os.environ.get("GITHUB_REPOSITORY", "local/dev").partition("/")
BASE = os.environ.get("SITE_URL") or f"https://{owner}.github.io/{repo}/"
RT = {"Overwhelmingly Positive": "Ylivoimaisen myönteinen", "Very Positive": "Erittäin myönteinen", "Positive": "Myönteinen",
      "Mostly Positive": "Enimmäkseen myönteinen", "Mixed": "Ristiriitainen", "Mostly Negative": "Enimmäkseen kielteinen",
      "Negative": "Kielteinen"}

shutil.rmtree(DIST, ignore_errors=True)
os.makedirs(DIST)
raw = read("data", "deals.json")
D = json.loads(raw)
fi_time = datetime.strptime(D["fetched"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone(ZoneInfo("Europe/Helsinki"))
updated = fi_time.strftime("%-d.%-m.%Y klo %H.%M")

open(os.path.join(DIST, "index.html"), "w", encoding="utf-8").write(read("site", "template.html").replace("__DATA__", raw.replace("</", "<\\/")))
shutil.copy(os.path.join(ROOT, "site", "style.css"), os.path.join(DIST, "style.css"))

hist = defaultdict(list)
hp = os.path.join(ROOT, "data", "history.csv")
if os.path.exists(hp):
    for r in csv.DictReader(open(hp, encoding="utf-8")):
        hist[r["id"]].append(r)

tpl = read("site", "game.html")
urls = [BASE]
for g in D["games"]:
    slug = g.get("slug")
    if not slug:
        continue
    shops = g.get("shops") or [{"shop": g["store"], "price": g["price"], "regular": g["orig"], "cut": g["disc"], "url": g["url"]}]
    rows = "".join(
        f'<tr><td><b>{esc(s["shop"])}</b></td><td class="n">{eur(s["regular"])}</td><td class="n">{"-%d %%" % s["cut"] if s["cut"] else "–"}</td>'
        f'<td class="n{" best" if i == 0 else ""}">{eur(s["price"])}</td><td class="n"><a href="{esc(s["url"])}" rel="noopener">Kauppaan</a></td></tr>'
        for i, s in enumerate(shops))
    h = hist.get(g["id"], [])[-10:][::-1]
    hrows = "".join(f'<tr><td>{esc(r["aika"][:10])}</td><td>{esc(r["kauppa"])}</td><td class="n">{eur(float(r["hinta"]))}</td></tr>' for r in h) \
        or '<tr><td colspan="3">Ei vielä hintamuutoksia.</td></tr>'
    low = g.get("low")
    if low is not None and g["price"] <= low + 0.005:
        verdict, vclass = "Kaikkien aikojen alin hinta. Hyvä hetki ostaa.", "verdict good"
    elif low is not None:
        verdict, vclass = f"Alimmillaan tämä on ollut {eur(low)}.", "verdict"
    else:
        verdict, vclass = "", "verdict"
    pills = []
    if g.get("ratingPct"):
        pills.append(f'<span class="pill{" good" if g["ratingPct"] >= 80 else ""}">{esc(RT.get(g.get("rating"), g.get("rating") or ""))} {g["ratingPct"]} %</span>')
    if g.get("mc"):
        pills.append(f'<span class="pill">Metacritic {g["mc"]}</span>')
    pills.append(f'<span class="pill">{len(shops)} kauppa{"a" if len(shops) != 1 else ""}</span>')
    desc = f'{g["title"]} nyt {eur(g["price"])} ({g["store"]}), alennus {g["disc"]} %. Vertaa hinnat kaupoittain ja katso hintahistoria.'
    page = tpl
    for k, v in {"TITLE": esc(g["title"]), "PRICE": eur(g["price"]), "ORIG": eur(g["orig"]), "DISC": g["disc"], "DESC": esc(desc),
                 "CANONICAL": f"{BASE}peli/{slug}/", "IMG": esc(g.get("img") or ""), "URL": esc(g["url"]), "STORE": esc(g["store"]),
                 "VERDICT": verdict, "VERDICT_CLASS": vclass, "PILLS": "".join(pills), "SHOPS": rows, "HISTORY": hrows,
                 "HISTNOTE": "Hintahistoria kertyy siitä hetkestä, kun aloimme seurata peliä. Uusi rivi syntyy aina, kun halvin hinta muuttuu.",
                 "UPDATED": updated}.items():
        page = page.replace("{{" + k + "}}", str(v))
    d = os.path.join(DIST, "peli", slug)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(page)
    urls.append(f"{BASE}peli/{slug}/")

open(os.path.join(DIST, "sitemap.xml"), "w", encoding="utf-8").write(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "".join(f"  <url><loc>{esc(u)}</loc></url>\n" for u in urls) + "</urlset>\n")
open(os.path.join(DIST, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {BASE}sitemap.xml\n")
print(f"Rakennettu: etusivu + {len(urls) - 1} pelisivua")
