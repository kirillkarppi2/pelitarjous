"""Hakee pelitarjoukset Suomen hinnoilla (Steam + Epicin ilmaispelit) ja tallentaa ne data/-kansioon.

Tulos:
  data/deals.json    tämänhetkinen tilanne, josta sivu rakennetaan
  data/history.csv   hintahistoria: uusi rivi aina kun pelin hinta muuttuu
"""
import csv, json, os, sys, time, urllib.error, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
os.makedirs(DATA, exist_ok=True)
REPO = os.environ.get("GITHUB_REPOSITORY", "local/dev")
UA = f"Pelitarjous/0.1 (+https://github.com/{REPO})"


def get(url):
    for _ in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(15)
                continue
            raise
    raise RuntimeError("rate limited: " + url)


def steam_img(appid):
    return f"https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{appid}/header.jpg"


def fetch_steam():
    # 1) Ehdokkaat CheapSharkista (storeID 1 = Steam), useampi järjestys jotta valikoima on monipuolinen
    cands = {}
    for params in [{"sortBy": "Deal Rating", "pageSize": 60}, {"sortBy": "Reviews", "pageSize": 60, "onSale": 1},
                   {"sortBy": "Metacritic", "pageSize": 40, "onSale": 1}, {"sortBy": "Recent", "pageSize": 40, "onSale": 1}]:
        q = {"storeID": 1, **params}
        for d in get("https://www.cheapshark.com/api/1.0/deals?" + urllib.parse.urlencode(q)):
            if d.get("steamAppID"):
                cands.setdefault(d["steamAppID"], d)
        time.sleep(1)

    # 2) Oikeat Suomen hinnat Steamista
    games, ids = [], list(cands)
    for i in range(0, len(ids), 40):
        chunk = ids[i:i + 40]
        r = get("https://store.steampowered.com/api/appdetails?" + urllib.parse.urlencode(
            {"appids": ",".join(chunk), "cc": "fi", "filters": "price_overview"}))
        for aid in chunk:
            data = (r.get(aid) or {}).get("data")
            po = data.get("price_overview") if isinstance(data, dict) else None
            if not po or po.get("currency") != "EUR" or po.get("discount_percent", 0) <= 0:
                continue
            c = cands[aid]
            games.append({"id": aid, "title": c["title"], "price": po["final"] / 100, "orig": po["initial"] / 100,
                          "disc": po["discount_percent"], "mc": int(c.get("metacriticScore") or 0),
                          "rating": c.get("steamRatingText"), "ratingPct": int(c.get("steamRatingPercent") or 0),
                          "ratingCount": int(c.get("steamRatingCount") or 0), "store": "Steam",
                          "url": f"https://store.steampowered.com/app/{aid}/", "img": steam_img(aid)})
        time.sleep(1.5)

    # 3) Steamin etusivun tarjoukset
    fc = get("https://store.steampowered.com/api/featuredcategories?cc=fi&l=finnish")
    seen = {g["id"] for g in games}
    for it in fc["specials"]["items"] + fc["top_sellers"]["items"]:
        aid = str(it["id"])
        if aid in seen or not it.get("discounted") or it.get("currency") != "EUR":
            continue
        games.append({"id": aid, "title": it["name"], "price": it["final_price"] / 100,
                      "orig": it["original_price"] / 100, "disc": it["discount_percent"], "mc": 0, "rating": None,
                      "ratingPct": 0, "ratingCount": 0, "store": "Steam",
                      "url": f"https://store.steampowered.com/app/{aid}/", "img": it.get("header_image") or steam_img(aid)})
        seen.add(aid)
    return games


def fetch_epic_free():
    ep = get("https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=fi&country=FI&allowCountries=FI")
    free = []
    for e in ep["data"]["Catalog"]["searchStore"]["elements"]:
        p = e.get("promotions") or {}
        is_free = lambda o: o["discountSetting"]["discountPercentage"] == 0
        now = [o for x in p.get("promotionalOffers", []) for o in x["promotionalOffers"] if is_free(o)]
        up = [o for x in p.get("upcomingPromotionalOffers", []) for o in x["promotionalOffers"] if is_free(o)]
        if not (now or up):
            continue
        o = (now or up)[0]
        imgs = {k["type"]: k["url"] for k in e.get("keyImages", [])}
        img = imgs.get("OfferImageWide") or imgs.get("DieselStoreFrontWide") or imgs.get("Thumbnail") or next(iter(imgs.values()), None)
        slug = e.get("productSlug") or ((e.get("catalogNs") or {}).get("mappings") or [{}])[0].get("pageSlug") or ""
        free.append({"title": e["title"], "orig": e["price"]["totalPrice"]["originalPrice"] / 100,
                     "start": o["startDate"], "end": o["endDate"], "now": bool(now), "img": img,
                     "url": f"https://store.epicgames.com/fi/p/{slug}" if slug else "https://store.epicgames.com/fi/free-games"})
    return free


def main():
    path = os.path.join(DATA, "deals.json")
    prev = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {"games": [], "free": []}
    errors = []
    try:
        games = fetch_steam()
        print("Steam-tarjouksia:", len(games))
    except Exception as e:
        errors.append(f"Steam: {e}"); games = prev["games"]
    try:
        free = fetch_epic_free()
        print("Epicin ilmaispelejä:", len(free))
    except Exception as e:
        errors.append(f"Epic: {e}"); free = prev["free"]

    # Hintahistoria: kirjataan rivi vain kun hinta on uusi tai muuttunut
    old = {(g["store"], g["id"]): g["price"] for g in prev["games"]}
    hist = os.path.join(DATA, "history.csv")
    new_file = not os.path.exists(hist)
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(hist, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["aika", "kauppa", "id", "nimi", "hinta", "normaalihinta", "alennus"])
        for g in games:
            if old.get((g["store"], g["id"])) != g["price"]:
                w.writerow([ts, g["store"], g["id"], g["title"], g["price"], g["orig"], g["disc"]])

    json.dump({"fetched": ts, "games": games, "free": free}, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if errors:
        print("VIRHEET:", *errors, sep="\n  ")
        sys.exit(1 if len(errors) == 2 else 0)


if __name__ == "__main__":
    main()
