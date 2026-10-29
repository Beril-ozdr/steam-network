"""
Adim 2 (pandas'siz surum) - Ham veriden aglari kurma ve temel istatistikleri hesaplama.

Uretilen aglar:
  1) Iki parcali (bipartite) oyun <-> etiket agi   (kenar agirligi = etiket oy sayisi)
  2) Etiket-etiket projeksiyonu   (agirlik = birlikte gectigi oyun sayisi; ayrica Jaccard)
  3) Oyun-oyun projeksiyonu       (agirlik = etiket oy vektorlerinin kosinus benzerligi)

Cikti: data/processed/ (CSV kenar listeleri, GraphML dosyalari, stats.csv)

Calistirma:  python build_network_v2.py
"""
import argparse
import csv
import itertools
import json
import pathlib
from collections import Counter

import networkx as nx
import numpy as np

RAW = pathlib.Path("data/raw")
OUT = pathlib.Path("data/processed")


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def load_games():
    rows = []
    for line in (RAW / "appdetails.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        tags = d.get("tags") or {}
        if isinstance(tags, list):  # etiketsiz oyunlarda bos liste donebilir
            tags = {}
        rows.append({
            "appid": d["appid"],
            "name": d.get("name", ""),
            "positive": d.get("positive", 0),
            "negative": d.get("negative", 0),
            "owners": d.get("owners", ""),
            "tags": {k: int(v) for k, v in tags.items() if int(v) > 0},
        })
    return rows


def keep_top_k(tags, k):
    return dict(sorted(tags.items(), key=lambda kv: kv[1], reverse=True)[:k])


def graph_stats(name, G, bipartite_nodes=None):
    n, m = G.number_of_nodes(), G.number_of_edges()
    comps = list(nx.connected_components(G))
    largest = max((len(c) for c in comps), default=0)
    if bipartite_nodes is not None:
        density = nx.bipartite.density(G, bipartite_nodes)
        clustering = ""
    else:
        density = nx.density(G)
        clustering = round(nx.average_clustering(G), 4)
    return [
        name, n, m, round(density, 5), len(comps), largest,
        sum(1 for _, d in G.degree() if d == 0), clustering,
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-k-tags", type=int, default=15,
                    help="her oyun icin en cok oy alan k etiket tutulur")
    ap.add_argument("--min-tag-games", type=int, default=5,
                    help="en az bu kadar oyunda gecmeyen etiketler atilir")
    ap.add_argument("--game-sim", type=float, default=0.5,
                    help="oyun-oyun agi icin kosinus benzerlik esigi")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    games = load_games()
    for g in games:
        g["tags"] = keep_top_k(g["tags"], args.top_k_tags)
    games = [g for g in games if g["tags"]]

    tag_game_count = Counter(t for g in games for t in g["tags"])
    keep_tags = {t for t, c in tag_game_count.items() if c >= args.min_tag_games}
    for g in games:
        g["tags"] = {t: v for t, v in g["tags"].items() if t in keep_tags}
    games = [g for g in games if g["tags"]]
    tag_game_count = Counter(t for g in games for t in g["tags"])
    print(f"{len(games)} oyun, {len(tag_game_count)} etiket")

    # ---- 1) Bipartite ag ----
    write_csv(
        OUT / "edges_game_tag.csv",
        ["appid", "oyun", "etiket", "oy"],
        [[g["appid"], g["name"], t, v] for g in games for t, v in g["tags"].items()],
    )

    B = nx.Graph()
    game_nodes = [f"g{g['appid']}" for g in games]
    for g in games:
        B.add_node(f"g{g['appid']}", label=g["name"], tur="oyun",
                   degerlendirme=int(g["positive"] + g["negative"]))
    for t, c in tag_game_count.items():
        B.add_node(f"t:{t}", label=t, tur="etiket", oyun_sayisi=c)
    for g in games:
        for t, v in g["tags"].items():
            B.add_edge(f"g{g['appid']}", f"t:{t}", weight=v)
    nx.write_graphml(B, OUT / "bipartite_game_tag.graphml")

    # ---- 2) Etiket-etiket projeksiyonu ----
    cooc = Counter()
    for g in games:
        for a, b in itertools.combinations(sorted(g["tags"]), 2):
            cooc[(a, b)] += 1
    tt_rows = []
    for (a, b), c in cooc.items():
        union = tag_game_count[a] + tag_game_count[b] - c
        tt_rows.append([a, b, c, round(c / union, 5)])
    tt_rows.sort(key=lambda r: r[2], reverse=True)
    write_csv(OUT / "edges_tag_tag.csv",
              ["etiket_a", "etiket_b", "ortak_oyun", "jaccard"], tt_rows)

    T = nx.Graph()
    for t, c in tag_game_count.items():
        T.add_node(t, oyun_sayisi=c)
    for a, b, c, j in tt_rows:
        T.add_edge(a, b, weight=c, jaccard=j)
    nx.write_graphml(T, OUT / "tag_projection.graphml")

    # ---- 3) Oyun-oyun projeksiyonu (kosinus benzerligi) ----
    tags_list = sorted(tag_game_count)
    idx = {t: i for i, t in enumerate(tags_list)}
    M = np.zeros((len(games), len(tags_list)))
    for i, g in enumerate(games):
        for t, v in g["tags"].items():
            M[i, idx[t]] = v
    M /= np.linalg.norm(M, axis=1, keepdims=True)
    S = M @ M.T
    np.fill_diagonal(S, 0)
    ii, jj = np.where(np.triu(S >= args.game_sim, k=1))
    gg_rows = [
        [games[i]["appid"], games[j]["appid"], games[i]["name"], games[j]["name"],
         round(float(S[i, j]), 4)]
        for i, j in zip(ii, jj)
    ]
    write_csv(OUT / "edges_game_game.csv",
              ["appid_a", "appid_b", "oyun_a", "oyun_b", "benzerlik"], gg_rows)

    G = nx.Graph()
    for g in games:
        G.add_node(f"g{g['appid']}", label=g["name"])
    for a, b, _, _, s in gg_rows:
        G.add_edge(f"g{a}", f"g{b}", weight=s)
    nx.write_graphml(G, OUT / "game_projection.graphml")

    # ---- Temel istatistikler (ara kontrol tablosu) ----
    header = ["ag", "dugum", "kenar", "yogunluk", "bilesen_sayisi",
              "en_buyuk_bilesen", "izole_dugum", "ort_kumelenme"]
    stats = [
        graph_stats("oyun-etiket (bipartite)", B, set(game_nodes)),
        graph_stats("etiket-etiket", T),
        graph_stats(f"oyun-oyun (benzerlik>={args.game_sim})", G),
    ]
    write_csv(OUT / "stats.csv", header, stats)

    print()
    for row in stats:
        print(" | ".join(f"{h}: {v}" for h, v in zip(header, row)))
    print(f"\nDosyalar: {OUT}/")


if __name__ == "__main__":
    main()
