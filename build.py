#!/usr/bin/env python3
"""Génère le site statique « Menus de la maison » à partir de data/.

data/recettes/<slug>.json : une recette (nom, type, portions, notes, source, ingredients[{q,u,n,r}], etapes[])
data/menus/<AAAA-Sxx>.json : un menu de semaine
    {"titre": "Semaine 45", "du": "2026-11-02", "au": "2026-11-08",
     "repas": [{"jour": "Lundi soir", "recette": "lasagnes", "note": "restes mardi"}],
     "extras": ["tarama"]}
Usage : python3 build.py  → écrit le site dans ./docs (servi par GitHub Pages)
"""
import json, html, os, re, shutil, glob
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "docs"
TYPES = {"veau": "Bœuf, veau & agneau", "porc": "Porc & charcuterie", "volaille": "Volaille",
         "poisson": "Poisson", "vege": "Végétarien", "apero": "Apéro", "dessert": "Dessert"}
EXTRA = {"apero", "dessert"}
AISLES = ["Fruits & légumes", "Boucherie & poisson", "Frais & charcuterie", "Crèmerie & œufs", "Épicerie", "Cave"]
JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
e = html.escape


def fmt(x):
    if x is None:
        return ""
    r = round(x * 100) / 100
    return (str(int(r)) if r == int(r) else str(r)).replace(".", ",")


def qty(i):
    q, u = i.get("q"), (i.get("u") or "")
    if q is None:
        return ""
    if u == "g" and q >= 1000:
        q, u = q / 1000, "kg"
    if u == "cl" and q >= 100:
        q, u = q / 100, "l"
    return (fmt(q) + " " + u).strip()


def line(i):
    q = qty(i)
    return f"{q} {i['n']}".strip() if q else i["n"][:1].upper() + i["n"][1:]


def meals(r):
    return 0 if r.get("type") in EXTRA else max(1, round((r.get("portions") or 6) / 3))


def duree(m):
    if not m:
        return ""
    h, mn = divmod(int(m), 60)
    return f"{h} h {mn:02d}" if h and mn else (f"{h} h" if h else f"{mn} min")


def infos(r):
    """« 1 h 10 · ~25 € » ; vide si rien n'est estimé."""
    out = []
    t = (r.get("prep") or 0) + (r.get("cuisson") or 0)
    if t:
        out.append("⏱ " + duree(t))
    if r.get("cout"):
        out.append(f"~{r['cout']} €")
    return " · ".join(out)


PROFILS = {"equilibre": "Équilibré", "gourmand": "Gourmand"}
GEO = {"oui": "Georges : oui", "adapter": "Georges : à adapter", "non": "Georges : non"}


def chips(r):
    out = ""
    if r.get("profil") in PROFILS:
        out += f'<span class="pill p-{r["profil"]}">{PROFILS[r["profil"]]}</span>'
    if r.get("georges") in GEO:
        out += f'<span class="pill g-{r["georges"]}">{GEO[r["georges"]]}</span>'
    return out


def week_totals(menu, rs):
    slugs = []
    for s in [m.get("recette") for m in menu.get("repas", [])] + menu.get("extras", []):
        if s in rs and s not in slugs:
            slugs.append(s)
    cout = sum(rs[s].get("cout") or 0 for s in slugs)
    actif = sum(rs[s].get("prep") or 0 for s in slugs)
    total = sum((rs[s].get("prep") or 0) + (rs[s].get("cuisson") or 0) for s in slugs)
    return cout, actif, total


def load():
    rs = {}
    for f in sorted(glob.glob(str(ROOT / "data/recettes/*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        d["slug"] = Path(f).stem
        rs[d["slug"]] = d
    ms = {}
    for f in sorted(glob.glob(str(ROOT / "data/menus/*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        d["slug"] = Path(f).stem
        ms[d["slug"]] = d
    return rs, ms


ICON_HOME = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3.5" y="5" width="17" height="15" rx="2"/><path d="M3.5 9.5h17M8 3v4M16 3v4"/></svg>'
ICON_REC = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 4.5h11a2 2 0 0 1 2 2V20H7a2 2 0 0 1-2-2z"/><path d="M5 18a2 2 0 0 1 2-2h11M9 8.5h5M9 11.5h5"/></svg>'
ICON_CART = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 6h2l2 10h10l2-7H7.2"/><circle cx="9.5" cy="19.5" r="1.2"/><circle cx="16.5" cy="19.5" r="1.2"/></svg>'


def page(title, eyebrow, body, depth=0, current="", jsonld=None, h1=None):
    p = "../" * depth
    nav = "".join(
        f'<a href="{p}{href}"{" aria-current=\"page\"" if key == current else ""}>{ico}{lbl}</a>'
        for key, href, ico, lbl in [("menus", "index.html", ICON_HOME, "Menus"),
                                    ("listes", "listes.html", ICON_CART, "Courses"),
                                    ("recettes", "recettes.html", ICON_REC, "Recettes")])
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>' if jsonld else ""
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(title)}</title>
<meta name="theme-color" content="#2f6b5a">
<meta name="robots" content="noindex,nofollow">
<link rel="manifest" href="{p}manifest.webmanifest">
<link rel="icon" href="{p}icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{p}apple-touch-icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Menus">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&family=Atkinson+Hyperlegible:wght@400;700&display=swap">
<link rel="stylesheet" href="{p}style.css">
{ld}
</head><body>
<div class="wrap">
<header class="top"><div class="eyebrow">{e(eyebrow)}</div><h1>{e(h1 or title)}</h1></header>
{body}
</div>
<nav class="tabs" aria-label="Sections"><div class="in">{nav}</div></nav>
<script>
document.querySelectorAll('[data-bring]').forEach(function(a){{
  var u=new URL(a.getAttribute('data-bring'),location.href).href;
  a.href='https://api.getbring.com/rest/bringrecipes/deeplink?url='+encodeURIComponent(u)+'&source=web&baseQuantity='+a.dataset.base+'&requestedQuantity='+a.dataset.base;
}});
</script>
</body></html>
"""


def bring_btn(target, base, label="Ajouter à Bring", cls="btn"):
    return f'<a class="{cls} bring" data-bring="{e(target)}" data-base="{base}" href="#" rel="noopener">{BRING_SVG}{e(label)}</a>'


BRING_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>'


def tag(r):
    t = r.get("type", "vege")
    return f'<span class="tag"><span class="dot t-{t}"></span>{e(TYPES.get(t, ""))}</span>'


def recipe_page(r):
    ings = r.get("ingredients") or []
    steps = r.get("etapes") or []
    port = r.get("portions") or 4
    jl = {"@context": "https://schema.org", "@type": "Recipe", "name": r["nom"],
          "recipeYield": f"{port} portions", "recipeIngredient": [line(i) for i in ings],
          "recipeInstructions": [{"@type": "HowToStep", "text": s} for s in steps],
          "recipeCategory": TYPES.get(r.get("type"), "")}
    meta = f'{tag(r)} <span class="tag">pour {port}{" · " + str(meals(r)) + " repas" if meals(r) else ""}</span>'
    if infos(r):
        pp = f' (≈{fmt(r["cout"] / port)} €/part)' if r.get("cout") else ""
        det = f' — préparation {duree(r["prep"])}, cuisson {duree(r["cuisson"])}' if r.get("cuisson") else ""
        meta += chips(r)
        meta += f'<span class="tag">{e(infos(r))}{e(pp)}</span><span class="hint">{e(det.lstrip(" —").capitalize() if det else "")}</span>'
    body = [f'<p class="meta">{meta}</p>']
    if r.get("notes"):
        body.append(f'<p class="lead">{e(r["notes"])}</p>')
    if r.get("georges_note"):
        body.append(f'<p class="note-geo"><strong>Pour Georges :</strong> {e(r["georges_note"])}</p>')
    if ings:
        body.append('<div class="actions">' + bring_btn(f'{r["slug"]}.html', port) + '</div>')
        body.append('<section class="panel"><h2>Ingrédients</h2><ul class="ing">' + "".join(
            f'<li><span class="qq">{e(qty(i))}</span><span>{e(i["n"])}</span></li>' for i in ings) + '</ul></section>')
    else:
        body.append('<p class="empty">Ingrédients pas encore renseignés.</p>')
    if steps:
        body.append('<section class="panel"><h2>Étapes</h2><ol class="steps">' + "".join(f"<li>{e(s)}</li>" for s in steps) + "</ol></section>")
    if r.get("source"):
        s = r["source"]
        src = f'<a href="{e(s)}">{e(re.sub(r"^https?://(www\\.)?", "", s).split("/")[0])}</a>' if s.startswith("http") else e(s)
        body.append(f'<p class="hint">Source : {src}</p>')
    return page(r["nom"], "Recette", "\n".join(body), depth=1, current="recettes", jsonld=jl)


def recipes_index(rs):
    groups = []
    for t, lbl in TYPES.items():
        items = sorted([r for r in rs.values() if r.get("type") == t], key=lambda r: r["nom"].lower())
        if not items:
            continue
        rows = "".join(
            f'<li class="row" data-q="{e((r["nom"] + " " + " ".join(i["n"] for i in r.get("ingredients") or [])).lower())}">'
            f'<a class="main" href="recettes/{r["slug"]}.html"><span class="name">{e(r["nom"])}'
            f'{"" if r.get("ingredients") else " <span class=badge>à compléter</span>"}</span>'
            f'<span class="sub">pour {r.get("portions") or 4}{" · " + e(infos(r)) if infos(r) else ""}</span><span class="chips">{chips(r)}</span></a><span class="chev">›</span></li>'
            for r in items)
        groups.append(f'<section class="grp"><h2><span class="dot t-{t}"></span>{e(lbl)} <small>{len(items)}</small></h2><ul class="list">{rows}</ul></section>')
    body = ('<input type="search" id="q" placeholder="Chercher une recette ou un ingrédient" aria-label="Chercher">'
            + "".join(groups)
            + """<script>
var q=document.getElementById('q');q.addEventListener('input',function(){var v=q.value.toLowerCase().trim();
document.querySelectorAll('.row').forEach(function(li){li.hidden=v&&li.dataset.q.indexOf(v)<0});
document.querySelectorAll('.grp').forEach(function(g){g.hidden=!g.querySelector('.row:not([hidden])')});});
</script>""")
    return page("Mes recettes", f"Carnet · {len(rs)} recettes", body, current="recettes")


def shopping(menu, rs):
    agg = {}
    slugs = [m["recette"] for m in menu.get("repas", []) if m.get("recette")] + menu.get("extras", [])
    seen = []
    for s in slugs:
        if s in seen or s not in rs:
            continue
        seen.append(s)
        r = rs[s]
        for i in r.get("ingredients") or []:
            q, u = i.get("q"), (i.get("u") or "").lower()
            if q is not None and u == "kg":
                q, u = q * 1000, "g"
            if q is not None and u == "l":
                q, u = q * 100, "cl"
            key = re.sub(r"s\b", "", i["n"].lower()) + "|" + u
            cur = agg.setdefault(key, {"n": i["n"], "u": u, "q": None, "r": i.get("r") or "Épicerie", "from": []})
            if q is not None:
                cur["q"] = (cur["q"] or 0) + q
            if r["nom"] not in cur["from"]:
                cur["from"].append(r["nom"])
    return list(agg.values()), seen


def list_page(menu, rs):
    items, used = shopping(menu, rs)
    by = {}
    for it in items:
        by.setdefault(it["r"], []).append(it)
    lines = []
    sec = []
    for a in AISLES:
        its = sorted(by.get(a, []), key=lambda x: x["n"].lower())
        if not its:
            continue
        lines += [line(i) for i in its]
        sec.append(f'<section class="aisle"><h2>{e(a)} <small>{len(its)}</small></h2><ul class="list">' + "".join(
            f'<li class="item"><span class="lbl">{e(i["n"])}<span class="from">{e(", ".join(i["from"]))}</span></span><span class="q">{e(qty(i))}</span></li>'
            for i in its) + "</ul></section>")
    jl = {"@context": "https://schema.org", "@type": "Recipe", "name": f'Courses · {menu.get("titre", menu["slug"])}',
          "recipeYield": "1", "recipeIngredient": lines}
    cout, _, _ = week_totals(menu, rs)
    body = (f'<p class="lead">{len(lines)} articles pour {len(used)} plats, environ {cout} €. Le bouton ouvre Bring : décoche ce que tu as déjà avant de valider.</p>'
            f'<div class="actions">{bring_btn(menu["slug"] + ".html", 1, "Tout envoyer dans Bring")}</div>'
            + "".join(sec)
            + f'<p class="hint"><a href="../menus/{menu["slug"]}.html">← Voir le menu</a></p>')
    return page(f'Courses {menu.get("titre", "")}', "Liste de courses", body, depth=1, current="listes", jsonld=jl,
                h1=menu.get("titre", menu["slug"]))


def menu_block(menu, rs, depth):
    p = "../" * depth
    rows = []
    for m in menu.get("repas", []):
        r = rs.get(m.get("recette"))
        name = f'<a href="{p}recettes/{r["slug"]}.html">{e(r["nom"])}</a>' if r else e(m.get("libelle", m.get("recette", "")))
        sub = " · ".join(x for x in [m.get("note", ""), infos(r) if r and not m.get("note") else ""] if x)
        note = f'<span class="sub">{e(sub)}</span>' if sub else ""
        dot = f'<span class="dot t-{r.get("type")}"></span>' if r else '<span class="dot"></span>'
        geo = f'<span class="chips">{chips(r)}</span>' if r else ""
        rows.append(f'<li class="mrow"><span class="day">{e(m.get("jour", ""))}</span><span class="main">{dot}<span>{name}{note}{geo}</span></span></li>')
    ex = [rs[s] for s in menu.get("extras", []) if s in rs]
    extra = ("<p class=\"hint\">En plus : " + ", ".join(f'<a href="{p}recettes/{r["slug"]}.html">{e(r["nom"])}</a>' for r in ex) + "</p>") if ex else ""
    cout, actif, total = week_totals(menu, rs)
    plats = [rs[m["recette"]] for m in menu.get("repas", []) if m.get("recette") in rs]
    nb_e = sum(1 for r in plats if r.get("profil") == "equilibre")
    nb_g = sum(1 for r in plats if r.get("profil") == "gourmand")
    adapt = sorted({r["nom"] for r in plats if r.get("georges") in ("adapter", "non")})
    tot = (f'<p class="budget"><strong>Budget estimé : ~{cout} €</strong> · temps en cuisine ≈ {duree(actif)} (+ cuissons)'
           f'<br>{nb_e} repas équilibrés, {nb_g} gourmands'
           + (f'<br>À adapter pour Georges : {e(", ".join(adapt))}' if adapt else "<br>Tout convient à Georges")
           + '</p>') if cout else ""
    return f'{tot}<ul class="list menu">{"".join(rows)}</ul>{extra}'


def menu_page(menu, rs):
    body = (f'<p class="lead">{e(menu.get("intro", ""))}</p>' if menu.get("intro") else "") + menu_block(menu, rs, 1) + \
        f'<div class="actions">{bring_btn("../listes/" + menu["slug"] + ".html", 1, "Liste de courses dans Bring")}<a class="btn ghost" href="../listes/{menu["slug"]}.html">Voir la liste</a></div>'
    return page(menu.get("titre", menu["slug"]), "Menu", body, depth=1, current="menus")


def home(ms, rs):
    if not ms:
        body = ('<div class="panel empty-state"><h2>Pas encore de menu</h2>'
                '<p>Demande à Claude les menus de la semaine : ils apparaîtront ici avec la liste de courses à envoyer dans Bring.</p>'
                '<a class="btn" href="recettes.html">Parcourir les recettes</a></div>')
        return page("Menus de la maison", "Cette semaine", body, current="menus")
    order = sorted(ms.values(), key=lambda m: m["slug"], reverse=True)
    cur = order[0]
    body = (f'<section><h2 class="sec">{e(cur.get("titre", cur["slug"]))}</h2>' + menu_block(cur, rs, 0)
            + f'<div class="actions">{bring_btn("listes/" + cur["slug"] + ".html", 1, "Liste de courses dans Bring")}'
            f'<a class="btn ghost" href="listes/{cur["slug"]}.html">Voir la liste</a></div></section>')
    if len(order) > 1:
        body += '<section><h2 class="sec">Semaines précédentes</h2><ul class="list">' + "".join(
            f'<li class="row"><a class="main" href="menus/{m["slug"]}.html"><span class="name">{e(m.get("titre", m["slug"]))}</span></a><span class="chev">›</span></li>'
            for m in order[1:]) + "</ul></section>"
    return page("Menus de la maison", "Cette semaine", body, current="menus", h1="Menus de la maison")


def lists_index(ms):
    order = sorted(ms.values(), key=lambda m: m["slug"], reverse=True)
    body = ('<ul class="list">' + "".join(
        f'<li class="row"><a class="main" href="listes/{m["slug"]}.html"><span class="name">{e(m.get("titre", m["slug"]))}</span></a><span class="chev">›</span></li>'
        for m in order) + "</ul>") if order else '<p class="empty">Aucune liste pour l\'instant.</p>'
    return page("Listes de courses", "Courses", body, current="listes")


def icons():
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#2f6b5a"/>'
           '<path d="M18 30h28a14 14 0 0 1-28 0z" fill="#f2f5f1"/><path d="M26 22c0-4 4-4 4-8M34 22c0-4 4-4 4-8" stroke="#e2b04a" stroke-width="3" stroke-linecap="round" fill="none"/></svg>')
    (OUT / "icon.svg").write_text(svg, encoding="utf-8")
    try:
        from PIL import Image, ImageDraw
        for size, name in [(180, "apple-touch-icon.png"), (192, "icon-192.png"), (512, "icon-512.png")]:
            s = size / 64
            im = Image.new("RGB", (size, size), "#2f6b5a")
            d = ImageDraw.Draw(im)
            d.pieslice([18 * s, 16 * s, 46 * s, 44 * s], 0, 180, fill="#f2f5f1")
            d.rectangle([18 * s, 29 * s, 46 * s, 31 * s], fill="#f2f5f1")
            for x in (26, 34):
                d.line([(x * s, 22 * s), (x * s + 2 * s, 17 * s), (x * s + 4 * s, 13 * s)], fill="#e2b04a", width=max(2, int(3 * s)))
            im.save(OUT / name)
    except ImportError:
        pass
    (OUT / "manifest.webmanifest").write_text(json.dumps({
        "name": "Menus de la maison", "short_name": "Menus", "start_url": "./index.html", "scope": "./",
        "display": "standalone", "background_color": "#f2f5f1", "theme_color": "#2f6b5a", "lang": "fr",
        "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"},
                  {"src": "icon.svg", "sizes": "any", "type": "image/svg+xml"}]}, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    rs, ms = load()
    if OUT.exists():
        shutil.rmtree(OUT)
    for d in ("recettes", "listes", "menus"):
        (OUT / d).mkdir(parents=True)
    shutil.copy(ROOT / "style.css", OUT / "style.css")
    (OUT / ".nojekyll").write_text("")
    icons()
    for r in rs.values():
        (OUT / "recettes" / f'{r["slug"]}.html').write_text(recipe_page(r), encoding="utf-8")
    for m in ms.values():
        (OUT / "listes" / f'{m["slug"]}.html').write_text(list_page(m, rs), encoding="utf-8")
        (OUT / "menus" / f'{m["slug"]}.html').write_text(menu_page(m, rs), encoding="utf-8")
    (OUT / "recettes.html").write_text(recipes_index(rs), encoding="utf-8")
    (OUT / "listes.html").write_text(lists_index(ms), encoding="utf-8")
    (OUT / "index.html").write_text(home(ms, rs), encoding="utf-8")
    print(f"{len(rs)} recettes, {len(ms)} menus → {OUT}")


if __name__ == "__main__":
    main()
