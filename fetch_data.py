"""
Adim 1 - SteamSpy'dan veri toplama (tekrarlanabilir, kesilirse kaldigi yerden devam eder).

1) "all" endpoint'inden birkac sayfa oyun listesi cekilir (sayfa basi 1000 oyun).
2) Oyunlar populerlige gore siralanir (positive + negative degerlendirme sayisi),
   ilk N oyun secilir.
3) Her oyun icin appdetails cagrilir (etiketler ve oy sayilari burada).

Cikti: data/raw/ klasoru (ham JSON/JSONL + meta.json)

Calistirma:  python fetch_data.py
"""
import argparse
import datetime
import json
import pathlib
import time

import requests

API = "https://steamspy.com/api.php"
RAW = pathlib.Path("data/raw")
HEADERS = {"User-Agent": "BVA-donem-odevi-sosyal-ag-analizi (ogrenci projesi)"}

# SteamSpy hiz sinirlari (steamspy.com/api.php): "all" ~ 60 sn'de 1 istek, digerleri ~ 1 sn'de 1 istek
SLEEP_ALL = 61
SLEEP_DETAIL = 1.1


def get(params, retries=4):
    for i in range(retries):
        try:
            r = requests.get(API, params=params, headers=HEADERS, timeout=60)
            if r.status_code == 200:
                return r.json()
            print(f"  HTTP {r.status_code}, tekrar deneniyor...")
        except (requests.RequestException, ValueError) as e:
            print(f"  hata: {e}, tekrar deneniyor...")
        time.sleep(5 * (i + 1))
    return None


def fetch_pages(n_pages):
    games = {}
    for p in range(n_pages):
        f = RAW / f"all_page_{p}.json"
        if f.exists():
            data = json.loads(f.read_text(encoding="utf-8"))
            print(f"Sayfa {p}: onbellekten okundu ({len(data)} oyun)")
        else:
            print(f"Sayfa {p} indiriliyor...")
            data = get({"request": "all", "page": p})
            if not data:
                print(f"Sayfa {p} alinamadi, atlaniyor.")
                continue
            f.write_text(json.dumps(data), encoding="utf-8")
            print(f"  {len(data)} oyun alindi; hiz siniri icin {SLEEP_ALL} sn bekleniyor")
            time.sleep(SLEEP_ALL)
        games.update(data)
    return games


def popularity(g):
    # Populerlik olcusu: toplam degerlendirme sayisi (owners alani aralik oldugu icin kaba)
    return int(g.get("positive", 0)) + int(g.get("negative", 0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=3, help="indirilecek 'all' sayfasi (1000 oyun/sayfa)")
    ap.add_argument("--top", type=int, default=2000, help="secilecek en populer oyun sayisi")
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)

    games = fetch_pages(args.pages)
    ranked = sorted(games.values(), key=popularity, reverse=True)[: args.top]
    print("\nKontrol icin ilk 10 oyun (taninan oyunlar mi?):")
    for g in ranked[:10]:
        print(f"  {g.get('name')}  ({popularity(g):,} degerlendirme)")

    (RAW / "top_games.json").write_text(json.dumps(ranked), encoding="utf-8")

    out = RAW / "appdetails.jsonl"
    done = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["appid"])
    todo = [g for g in ranked if g["appid"] not in done]
    print(f"\nappdetails: {len(done)} tamam, {len(todo)} kaldi "
          f"(~{len(todo) * SLEEP_DETAIL / 60:.0f} dk)")

    with out.open("a", encoding="utf-8") as fh:
        for i, g in enumerate(todo, 1):
            d = get({"request": "appdetails", "appid": g["appid"]})
            if d and d.get("appid"):
                fh.write(json.dumps(d, ensure_ascii=False) + "\n")
                fh.flush()
            else:
                print(f"  {g['appid']} ({g.get('name')}) alinamadi")
            if i % 50 == 0:
                print(f"  {i}/{len(todo)}")
            time.sleep(SLEEP_DETAIL)

    meta = {
        "kaynak": "SteamSpy API (https://steamspy.com/api.php)",
        "toplama_tarihi": datetime.date.today().isoformat(),
        "sayfa_sayisi": args.pages,
        "secilen_oyun_sayisi": args.top,
        "populerlik_olcusu": "positive + negative degerlendirme sayisi",
    }
    (RAW / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nBitti. Siradaki adim: python build_network.py")


if __name__ == "__main__":
    main()
