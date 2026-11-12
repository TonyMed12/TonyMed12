#!/usr/bin/env python3
"""Genera las tarjetas SVG animadas del perfil en ../assets.

  python scripts/build.py            # usa la API publica de GitHub (sin token) y guarda cache
  python scripts/build.py --offline  # usa assets/data-cache.json
"""
import base64, datetime as dt, html, json, math, random, re, sys, textwrap, urllib.request
from pathlib import Path

USER = "TonyMed12"
NAME = "José Antonio Medina Ayala"
EMAIL, SITE, LINKEDIN = "tonymed2022@gmail.com", "tonymed.dev", "tony-medinaa"
BIO = ("Hi, I'm Tony. I'm a 9th-semester systems engineering student from Morelia who likes making things work, and helping "
       "the people around me do the same. Away from the keyboard you'll find me on a soccer field or a pádel "
       "court, planning the next trip, or practicing my English.")
CEDULA = "15938245"  # numero de cedula (cadena); vacio -> solo se destaca el titulo
CED = "Cédula profesional técnica" + (f" · No. {CEDULA}" if CEDULA else "")
PHOTO = True  # False -> iniciales en lugar de la foto de GitHub
OUT = Path(__file__).resolve().parent.parent / "assets"
OUT.mkdir(exist_ok=True)
CACHE = OUT / "data-cache.json"
SANS = "'Segoe UI','Helvetica Neue',Arial,sans-serif"
SERIF = "Georgia,'Times New Roman',serif"
e = html.escape

T = {  # paleta "escarcha": azul noche + dorado navideno
    "dark": dict(bg0="#0a1020", bg1="#14213d", tile="#ffffff", tileo=".055", edge="#ffffff", edgeo=".11", fg="#f4f6fb",
                 dim="#a3afc6", faint="#6b7894", gold="#f5c26b", ice="#7ab8f0", ok="#4ade80", snow="#ffffff",
                 pine="#0b1a2e", pine2="#12314a", hill="#e6f0ff", hill2="#b9cdea",
                 heat=["#18243d", "#2b4a7a", "#3f77b5", "#7ab8f0", "#eaf5ff"]),
    "light": dict(bg0="#f5f8fd", bg1="#e3ecf9", tile="#ffffff", tileo=".85", edge="#9fb3d1", edgeo=".55", fg="#0f172a",
                  dim="#475569", faint="#8493ab", gold="#b7791f", ice="#2b6cb0", ok="#15803d", snow="#9fb3d1",
                  pine="#1d4a66", pine2="#2b6a8c", hill="#ffffff", hill2="#cfdcf0",
                  heat=["#e3eaf5", "#bcd3f0", "#7fb0e6", "#3f84cf", "#1e4f8f"]),
}
LANGC = {"TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Java": "#d08a3a", "Python": "#4b8bbe",
         "CSS": "#a78bfa", "HTML": "#f0643c", "PLpgSQL": "#5b8db8", "PHP": "#8892bf"}
LIGHTS = ["#ef4444", "#facc15", "#38bdf8", "#34d399", "#f472b6"]


# ------------------------------------------------------------------ datos
def get(url, raw=False):
    req = urllib.request.Request(url, headers={"User-Agent": "profile-cards", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        b = r.read()
    return b if raw else json.loads(b)


def fetch():
    u = get(f"https://api.github.com/users/{USER}")
    repos = [r for r in get(f"https://api.github.com/users/{USER}/repos?per_page=100") if not r["fork"]]
    langs, proj = {}, {}
    for r in repos:
        for k, v in get(r["languages_url"]).items():
            langs[k] = langs.get(k, 0) + v
        try:
            c = get(f"https://api.github.com/repos/{USER}/{r['name']}/contributors?per_page=30")
            if isinstance(c, list):
                me = next((x["contributions"] for x in c if x["login"] == USER), 0)
                proj[r["name"]] = dict(commits=me, team=len([x for x in c if "[bot]" not in x["login"]]),
                                       rank=1 + sum(x["contributions"] > me for x in c), pushed=r["pushed_at"][:10])
        except Exception:
            pass
    page = get(f"https://github.com/users/{USER}/contributions", raw=True).decode("utf-8")
    cells = re.findall(r'data-date="([\d-]+)"[^>]*data-level="(\d)"', page)
    tips = re.findall(r"<tool-tip[^>]*>([^<]+)</tool-tip>", page)
    cal = sorted((d, int(re.match(r"(\d+)", t).group(1)) if t[0].isdigit() else 0, int(l))
                 for (d, l), t in zip(cells, tips))
    commits = get(f"https://api.github.com/search/commits?q=author:{USER}")["total_count"]
    prs = get(f"https://api.github.com/search/issues?q=author:{USER}+type:pr")["total_count"]
    avatar = get(u["avatar_url"] + "&s=420", raw=True) if PHOTO else b""
    return dict(user=dict(repos=u["public_repos"], followers=u["followers"]), langs=langs, proj=proj, cal=cal,
                commits=commits, prs=prs, avatar=base64.b64encode(avatar).decode())


def load():
    if "--offline" not in sys.argv:
        try:
            d = fetch(); CACHE.write_text(json.dumps(d), encoding="utf-8"); return d
        except Exception as ex:
            print("sin red/API, uso cache:", ex)
    return json.loads(CACHE.read_text(encoding="utf-8"))


def streaks(cal):
    days = [c for _, c, _ in cal]
    best = run = 0
    for c in days:
        run = run + 1 if c else 0
        best = max(best, run)
    cur = 0
    for c in reversed(days if days[-1] else days[:-1]):  # hoy sin actividad no rompe la racha
        if not c: break
        cur += 1
    return cur, best


# ------------------------------------------------------------------ piezas SVG
CSS = f"""<style>
text{{font-family:{SANS}}}.sf{{font-family:{SERIF}}}
.up{{opacity:0;animation:up .7s ease-out forwards}}
@keyframes up{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:none}}}}
.fd{{opacity:0;animation:fd 1.2s ease-out .1s forwards}}
@keyframes fd{{to{{opacity:1}}}}
.tw{{animation:tw 3s ease-in-out infinite}}
@keyframes tw{{0%,100%{{opacity:.25}}50%{{opacity:1}}}}
.sn{{animation:fall linear infinite}}
@keyframes fall{{from{{transform:translate(0,-10px)}}50%{{transform:translate(14px,calc(var(--h)/2))}}to{{transform:translate(0,var(--h))}}}}
.spin{{transform-origin:var(--o);animation:spin 50s linear infinite}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
.bar{{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:gy .9s cubic-bezier(.2,.8,.2,1) forwards}}
@keyframes gy{{to{{transform:scaleY(1)}}}}
.draw{{stroke-dasharray:1400;stroke-dashoffset:1400;animation:dr 2s ease-out .3s forwards}}
@keyframes dr{{to{{stroke-dashoffset:0}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important;opacity:1!important;transform:none!important;stroke-dashoffset:0!important}}}}
</style>"""


def svg(w, h, th, label, body, extra=""):
    c = T[th]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
            f'aria-label="{e(label)}"><title>{e(label)}</title>{CSS.replace("</style>", extra + "</style>")}'
            f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{c["bg0"]}"/>'
            f'<stop offset="1" stop-color="{c["bg1"]}"/></linearGradient></defs>'
            f'<rect width="{w}" height="{h}" rx="18" fill="url(#bg)"/>{body}</svg>')


def tx(x, y, s, size=13, fill="#fff", anchor="start", weight=400, serif=False, delay=None, ls=None, cls=""):
    a = f' class="{("sf " if serif else "") + cls}"'.replace('class=" "', "").replace('class=""', "")
    a += f' letter-spacing="{ls}"' if ls else ""
    a += f' style="animation-delay:{delay:.2f}s"' if delay is not None else ""
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}"{a}>{e(str(s))}</text>'


def tile(x, y, w, h, th, r=14):
    c = T[th]
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{c["tile"]}" fill-opacity="{c["tileo"]}" '
            f'stroke="{c["edge"]}" stroke-opacity="{c["edgeo"]}"/>')


def chip(x, y, s, th, size=11, color=None, h=24, bold=False, dot=None):
    c = T[th]
    w = len(s) * size * .56 + 22 + (14 if dot else 0)
    o = (f'<rect x="{x:.0f}" y="{y}" width="{w:.0f}" height="{h}" rx="{h / 2}" fill="{c["tile"]}" fill-opacity="{c["tileo"]}" '
         f'stroke="{color or c["edge"]}" stroke-opacity="{1 if color else c["edgeo"]}"/>')
    if dot:
        o += f'<circle cx="{x + 13:.0f}" cy="{y + h / 2}" r="3.5" fill="{dot}"/>'
    return o + tx(f"{x + 11 + (14 if dot else 0):.0f}", y + h / 2 + size * .36, s, size, color or c["fg"], weight=600 if bold else 400), w


def snow(th, w, h, n, seed):
    r = random.Random(seed)
    return "".join(f'<circle class="sn" cx="{r.uniform(8, w - 8):.0f}" cy="0" r="{r.choice([1, 1.5, 2.2, 3]):.1f}" '
                   f'fill="{T[th]["snow"]}" opacity="{r.uniform(.35, .9):.2f}" '
                   f'style="--h:{h}px;animation-duration:{r.uniform(8, 15):.1f}s;animation-delay:-{r.uniform(0, 15):.1f}s"/>'
                   for _ in range(n))


def pine(x, y, s, th, seed):
    """Pino silueteado con nieve y luces; (x, y) = base del tronco."""
    c, r = T[th], random.Random(seed)
    p = ""
    for i, (hw, top, bot) in enumerate([(46, -84, -40), (36, -118, -72), (26, -146, -104)]):
        col = c["pine2"] if i % 2 else c["pine"]
        p += (f'<polygon points="{-hw * s + x:.1f},{y + bot * s:.1f} {x:.1f},{y + top * s:.1f} {hw * s + x:.1f},{y + bot * s:.1f}" fill="{col}"/>'
              f'<path d="M{x - hw * s * .55:.1f} {y + (top + (bot - top) * .45) * s:.1f} L{x:.1f} {y + top * s:.1f} L{x + hw * s * .55:.1f} {y + (top + (bot - top) * .45) * s:.1f} Q{x:.1f} {y + (top + (bot - top) * .62) * s:.1f} {x - hw * s * .55:.1f} {y + (top + (bot - top) * .45) * s:.1f}Z" fill="#fff" opacity=".9"/>')
        for _ in range(4):
            t = r.uniform(.25, .9)
            bx = x + r.uniform(-1, 1) * hw * s * t * .8
            p += f'<circle class="tw" cx="{bx:.1f}" cy="{y + (top + (bot - top) * t) * s:.1f}" r="2.6" fill="{LIGHTS[r.randrange(5)]}" style="animation-delay:-{r.uniform(0, 3):.1f}s"/>'
    return p + f'<rect x="{x - 5 * s:.1f}" y="{y - 40 * s:.1f}" width="{10 * s:.1f}" height="{40 * s:.1f}" fill="#5b3a21"/>' \
        f'<text class="tw" x="{x}" y="{y - 142 * s:.1f}" font-size="{16 * s:.0f}" fill="#fde68a" text-anchor="middle">★</text>'


# ------------------------------------------------------------------ hero
def hero(th, d):
    c, w = T[th], 985
    wrap = textwrap.wrap(BIO, 66)
    h = 504 + 22 * max(0, len(wrap) - 3)
    b = snow(th, w, h, 55, 2)
    for i, x in enumerate(range(24, w - 10, 30)):  # guirnalda
        b += f'<circle class="tw" cx="{x}" cy="{12 + 6 * math.sin(x / 36):.1f}" r="3.6" fill="{LIGHTS[i % 5]}" style="animation-delay:-{(i * .7) % 3:.1f}s"/>'
    # foto con aro dorado y nieve encima
    cx, cy, rad = 168, 178, 100
    b += (f'<clipPath id="ph"><circle cx="{cx}" cy="{cy}" r="{rad}"/></clipPath>'
          f'<circle class="spin" style="--o:{cx}px {cy}px" cx="{cx}" cy="{cy}" r="{rad + 20}" fill="none" stroke="{c["gold"]}" stroke-opacity=".5" stroke-dasharray="2 9" stroke-linecap="round"/>'
          f'<circle cx="{cx}" cy="{cy}" r="{rad + 7}" fill="none" stroke="{c["gold"]}" stroke-width="3"/>')
    if PHOTO and d.get("avatar"):
        b += (f'<image class="fd" href="data:image/jpeg;base64,{d["avatar"]}" x="{cx - rad}" y="{cy - rad}" width="{2 * rad}" height="{2 * rad}" '
              f'preserveAspectRatio="xMidYMid slice" clip-path="url(#ph)"/>')
    else:
        b += f'<circle cx="{cx}" cy="{cy}" r="{rad}" fill="{c["tile"]}" fill-opacity=".1"/>' + tx(cx, cy + 22, "JM", 64, c["gold"], "middle", 700, True)
    r2 = random.Random(5)
    for a in range(-158, -21, 9):  # nieve acumulada sobre el aro
        ar = math.radians(a)
        b += f'<circle cx="{cx + (rad + 7) * math.cos(ar):.1f}" cy="{cy + (rad + 7) * math.sin(ar):.1f}" r="{r2.uniform(5, 9):.1f}" fill="#fff"/>'
    b += tx(cx, cy + rad + 44, "Morelia, México", 12, c["dim"], "middle", ls=1)
    # texto
    x0 = 330
    b += (tx(x0, 66, "SOFTWARE DEVELOPMENT  ·  SYSTEMS ENGINEERING", 11, c["gold"], weight=700, ls=3, cls="up", delay=.1) +
          tx(x0, 112, "José Antonio", 44, c["fg"], weight=700, serif=True, cls="up", delay=.25) +
          tx(x0, 158, "Medina Ayala", 44, c["fg"], weight=700, serif=True, cls="up", delay=.4))
    y = 196
    for i, ln in enumerate(wrap):
        b += tx(x0, y, ln, 15, c["dim"], cls="up", delay=.7 + i * .15)
        y += 22
    y += 8
    x, row = x0, y
    for s, kw in [("Open to internships & junior roles", dict(dot=c["ok"], bold=True)), ("Available now · will relocate to any city below", dict(color=c["gold"], bold=True)), (CED, dict(color=c["ok"], bold=True)),
                  ("Morelia · Acámbaro · Querétaro · Remote", {})]:
        if x + len(s) * 11.5 * .56 + 36 > 962: x, row = x0, row + 32
        o, wd = chip(x, row, s, th, 11.5, **kw); b += o; x += wd + 10
    y = row + 40
    items = [("EMAIL", EMAIL), ("PORTFOLIO", SITE), ("LINKEDIN", LINKEDIN), ("GITHUB", USER)]
    x = x0
    for i, (k, v) in enumerate(items):
        wd = 22 + len(k) * 7.4 + 10 + len(v) * 6.9
        if x + wd > 790: x, y = x0, y + 34
        b += (f'<rect x="{x:.0f}" y="{y}" width="{wd:.0f}" height="26" rx="13" fill="{c["gold"]}" fill-opacity=".10" stroke="{c["gold"]}" stroke-opacity=".55"/>' +
              tx(f"{x + 12:.0f}", y + 17, k, 8.5, c["gold"], weight=700, ls=1.4) + tx(f"{x + 22 + len(k) * 7.4:.0f}", y + 17.5, v, 12, c["fg"], weight=600))
        x += wd + 10
    # paisaje nevado
    gy = h - 92
    b += (f'<path d="M0 {gy + 38} Q160 {gy - 6} 330 {gy + 30} T690 {gy + 22} T985 {gy + 10} V{h} H0Z" fill="{c["hill2"]}" opacity=".55"/>'
          f'<path d="M0 {gy + 58} Q220 {gy + 14} 470 {gy + 52} T985 {gy + 40} V{h} H0Z" fill="{c["hill"]}" opacity=".95"/>')
    for px, py, s in [(820, gy + 70, .78), (884, gy + 78, 1.0), (948, gy + 68, .66), (44, gy + 74, .7), (96, gy + 84, .9)]:
        b += pine(px, py, s, th, int(px))
    return svg(w, h, th, f"{NAME} — software development and systems engineering", b)


# ------------------------------------------------------------------ sobre mi (bento)
TOOLBOX = [
    ("Languages", ["Java", "Python", "TypeScript", "JavaScript", "C#", "PHP", "SQL", "HTML", "CSS"]),
    ("Frontend", ["Next.js", "React", "Tailwind CSS"]),
    ("Backend & data", ["Node.js", "Supabase", "PostgreSQL", "Django"]),
    ("Cloud & DevOps", ["Docker", "Docker Compose", "AWS (Basics)", "Git"]),
    ("Data & AI", ["NumPy", "Pandas", "scikit-learn", "Matplotlib", "Jupyter"]),
    ("APIs & security", ["Postman", "OAuth", "CWE"]),
    ("Design & planning", ["Figma", "Notion", "Obsidian", "Trello", "Jira"]),
    ("Ways of working", ["Scrum", "Kanban", "Agile", "User Stories", "UML", "Clean Architecture", "Design patterns"]),
]


def toolbox(th, y0):
    """Etiquetas por grupo en 4 columnas; devuelve (svg, alto)."""
    c, out, y = T[th], "", y0
    for r in range(0, len(TOOLBOX), 4):
        rh = 0
        for i, (g, items) in enumerate(TOOLBOX[r:r + 4]):
            gx = x = 44 + i * 224
            yy = y + 12
            out += tx(gx, y, g, 10.5, c["dim"], weight=600)
            for t in items:
                wd = len(t) * 6.4 + 20
                if x + wd > gx + 208: x, yy = gx, yy + 30
                out += (f'<rect x="{x:.0f}" y="{yy}" width="{wd:.0f}" height="24" rx="12" fill="none" stroke="{c["ice"]}" stroke-opacity=".6"/>' +
                        tx(f"{x + 10:.0f}", yy + 16, t, 11, c["fg"]))
                x += wd + 6
            rh = max(rh, yy + 24 - y)
        y += rh + 22
    return out, y - y0


def about(th, d):
    c, w = T[th], 985
    tb, tbh = toolbox(th, 266)
    h = 284 + tbh
    b = snow(th, w, h, 14, 9)

    def head(x, y, s): return tx(x, y, s, 9.5, c["gold"], weight=700, ls=2.2)

    # educacion
    b += tile(24, 24, 300, 168, th) + head(44, 52, "EDUCATION")
    for i, (t1, t2) in enumerate([("Ingeniería en Sistemas Computacionales", "Instituto Tecnológico de Morelia · 9th semester"),
                                  ("Programming Technician", CED)]):
        yy = 84 + i * 50
        b += f'<circle cx="52" cy="{yy - 4}" r="4" fill="{c["gold"]}"/>' + (f'<line x1="52" x2="52" y1="{yy + 2}" y2="{yy + 38}" stroke="{c["gold"]}" stroke-opacity=".35"/>' if i == 0 else "")
        b += tx(66, yy, t1, 11.2, c["fg"], weight=600, serif=True) + tx(66, yy + 18, t2, 11, c["dim"])
    # idiomas
    b += tile(340, 24, 300, 168, th) + head(360, 52, "LANGUAGES")
    b += tx(360, 88, "Spanish", 14, c["fg"], weight=600, serif=True) + tx(620, 88, "Native", 11, c["dim"], "end")
    b += tx(360, 124, "English", 14, c["fg"], weight=600, serif=True) + tx(620, 124, "B2 · Upper-intermediate", 11, c["gold"], "end", 700)
    for i, lv in enumerate(["A1", "A2", "B1", "B2", "C1", "C2"]):
        on = i <= 3
        b += (f'<rect x="{360 + i * 43.3:.0f}" y="138" width="38" height="8" rx="4" fill="{c["gold"] if on else c["tile"]}" fill-opacity="{1 if on else c["tileo"]}"/>' +
              tx(f"{360 + i * 43.3 + 19:.0f}", 162, lv, 9, c["gold"] if on else c["faint"], "middle", 700 if on else 400))
    # ahora
    b += tile(656, 24, 305, 168, th) + head(676, 52, "RIGHT NOW")
    for i, (t1, t2) in enumerate([("GCI World 2026", "Data science & AI · in progress"), ("Backend foundations", "Django · REST APIs · algorithms")]):
        yy = 84 + i * 50
        b += f'<circle cx="684" cy="{yy - 4}" r="4" fill="{c["ok"]}" class="tw"/>' + tx(698, yy, t1, 13.5, c["fg"], weight=600, serif=True) + tx(698, yy + 18, t2, 11, c["dim"])
    b += tile(24, 208, 937, 52 + tbh, th) + head(44, 236, "TOOLBOX") + tb
    return svg(w, h, th, "About me: education, languages, current focus and toolbox", b)


# ------------------------------------------------------------------ proyectos
PROJECTS = [
    dict(repo="ProjeXus", title="ProjeXus", kind="TEAM PROJECT · 2025", role="Scrum Master",
         desc="Project-competition management platform for ICTI Michoacán, with QR-verified certificates.",
         third=("Stack", "TS + Java"), tags=["TypeScript", "Java", "Supabase"], link="github.com/TonyMed12/ProjeXus"),
    dict(repo="Adopciones-CAAM", title="Adopciones CAAM", kind="CLIENT PROJECT · 2026", role="Team lead · requirements",
         desc="Animal adoption registration, tracking and veterinary scheduling for the Centro de Atención Animal de Morelia.",
         third=("Live", "Vercel"), tags=["Next.js", "TypeScript", "Docker"], link="caamorelia.vercel.app"),
    dict(repo="Alvare-Ditana", title="Alvare Ditana", kind="CLIENT PROJECT · ACÁMBARO", role="Web development",
         desc="Website for a café in Acámbaro, Guanajuato: menu, shop, directions and reviews, written in Spanish.",
         third=("Stack", "Next.js 16"), tags=["React 19", "TypeScript", "Motion"], link="Acámbaro, Guanajuato", team="—"),
    dict(repo="Aquamarine-Resort", title="Aquamarine Resort", kind="WEB PROJECT · 2025", role="Web development",
         desc="Website for a resort, built with HTML and deployed on Vercel.",
         third=("Live", "Vercel"), tags=["HTML", "Vercel"], link="aquamarine-resort.vercel.app", team="—"),
    dict(repo="gestor-cfdi", title="Gestor CFDI", kind="SCHOOL PROJECT · 2026", role="Developer",
         desc="Web app for accounting firms: reads and validates CFDI invoices and suggests classifications; the accountant approves.",
         third=("Stack", "Next.js 16"), tags=["React 19", "Supabase", "Tailwind"], link="github.com/TonyMed12/gestor-cfdi"),
]


def slug(p):
    return re.sub(r"[^a-z0-9]+", "-", p["repo"].lower()).strip("-")


def project(th, p, d, idx):
    c, w, h = T[th], 480, 292
    s = d["proj"].get(p["repo"], {})
    cm, team = s.get("commits", 0), p.get("team", s.get("team", 1))
    b = tile(0.5, 0.5, w - 1, h - 1, th, 18)
    b += f'<rect x="0.5" y="22" width="4" height="64" rx="2" fill="{c["gold"]}"/>'
    b += (tx(28, 42, f"{idx:02d}", 12, c["gold"], weight=700, serif=True, ls=1) + tx(w - 26, 42, p["kind"], 9.5, c["faint"], "end", 600, ls=1.6) +
          tx(28, 80, p["title"], 25, c["fg"], weight=700, serif=True))
    y = 106
    for ln in textwrap.wrap(p["desc"], 62)[:2]:
        b += tx(28, y, ln, 12.5, c["dim"]); y += 19
    o, _ = chip(28, 150, p["role"], th, 11, c["gold"], bold=True); b += o
    b += f'<line x1="28" x2="{w - 28}" y1="196" y2="196" stroke="{c["edge"]}" stroke-opacity="{c["edgeo"]}"/>'
    mets = [(str(cm or "—"), "COMMITS"), (str(team), "PEOPLE"), (p["third"][1], p["third"][0].upper())]
    for i, (num, lab) in enumerate(mets):
        mx = 28 + i * 140
        b += tx(mx, 230, num, 22 if i < 2 else 15, c["fg"] if i < 2 else c["ice"], weight=700, serif=True) + tx(mx, 247, lab, 9, c["faint"], weight=600, ls=1.6)
    x = 28
    for t in p["tags"]:
        wd = len(t) * 6.2 + 18
        b += tx(f"{x:.0f}", 276, "# " + t, 10, c["ice"], weight=600); x += wd + 12
    b += tx(w - 26, 276, p["link"] + " ↗", 10, c["faint"], "end")
    return svg(w, h, th, f"{p['title']} — {p['kind']}", f'<g opacity="1">{b}</g>' + snow(th, w, h, 6, sum(map(ord, p["repo"]))))


# ------------------------------------------------------------------ actividad
def smooth(pts):
    path = f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, len(pts) - 1)]
        path += (f" C{p1[0] + (p2[0] - p0[0]) / 6:.1f} {p1[1] + (p2[1] - p0[1]) / 6:.1f}, "
                 f"{p2[0] - (p3[0] - p1[0]) / 6:.1f} {p2[1] - (p3[1] - p1[1]) / 6:.1f}, {p2[0]:.1f} {p2[1]:.1f}")
    return path


def activity(th, d):
    c, w, h = T[th], 985, 620
    cal = d["cal"]
    cur, best = streaks(cal)
    total = sum(x[1] for x in cal)
    active = sum(1 for x in cal if x[1])
    b = snow(th, w, h, 14, 21)
    b += (tx(40, 52, "YEAR IN REVIEW", 10, c["gold"], weight=700, ls=3) + tx(40, 100, f"{total} contributions", 42, c["fg"], weight=700, serif=True) +
          tx(40, 128, f"in the last 12 months  ·  {active} active days  ·  longest streak {best} days  ·  current {cur}", 12.5, c["dim"]))
    for i, (num, lab) in enumerate([(d["user"]["repos"], "REPOSITORIES"), (d["commits"], "COMMITS"), (d["prs"], "PULL REQUESTS"), (active, "ACTIVE DAYS")]):
        x = 24 + i * 239.3
        b += tile(x, 148, 218, 70, th) + tx(x + 20, 190, num, 30, c["fg"], weight=700, serif=True) + tx(x + 20, 206 - 2, "", 1, c["dim"]) + tx(x + 198, 192, lab, 9, c["faint"], "end", 600, ls=1.5)
    # area mensual
    months = {}
    for dte, n, _ in cal:
        months[dte[:7]] = months.get(dte[:7], 0) + n
    ms = sorted(months.items())[-12:]
    mx = max(v for _, v in ms) or 1
    b += tile(24, 234, 560, 190, th) + tx(44, 262, "MONTHLY ACTIVITY", 9.5, c["gold"], weight=700, ls=2.2)
    pts = [(60 + i * (480 / 11), 394 - 100 * v / mx) for i, (_, v) in enumerate(ms)]
    line = smooth(pts)
    b += (f'<defs><linearGradient id="ar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{c["ice"]}" stop-opacity=".55"/><stop offset="1" stop-color="{c["ice"]}" stop-opacity="0"/></linearGradient></defs>'
          f'<path d="{line} L{pts[-1][0]:.1f} 394 L{pts[0][0]:.1f} 394Z" fill="url(#ar)" class="fd"/>'
          f'<path class="draw" d="{line}" fill="none" stroke="{c["ice"]}" stroke-width="2.4" stroke-linecap="round"/>')
    for (px, py), (m, v) in zip(pts, ms):
        b += (f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.4" fill="{c["bg0"]}" stroke="{c["gold"]}" stroke-width="2"/>' +
              tx(f"{px:.1f}", f"{py - 10:.1f}", v, 9.5, c["dim"], "middle", 600) + tx(f"{px:.1f}", 412, dt.date.fromisoformat(m + "-01").strftime("%b"), 9.5, c["faint"], "middle"))
    # donut lenguajes
    b += tile(600, 234, 361, 190, th) + tx(620, 262, "LANGUAGES BY CODE", 9.5, c["gold"], weight=700, ls=2.2)
    langs = sorted(d["langs"].items(), key=lambda k: -k[1])[:6]
    tot = sum(v for _, v in langs) or 1
    C, off = 2 * math.pi * 52, 0
    for k, v in langs:
        ln = C * v / tot
        b += (f'<circle cx="690" cy="342" r="52" fill="none" stroke="{LANGC.get(k, "#64748b")}" stroke-width="16" stroke-dasharray="{max(ln - 2, 1):.1f} {C - max(ln - 2, 1):.1f}" '
              f'stroke-dashoffset="{-off:.1f}" transform="rotate(-90 690 342)"/>')
        off += ln
    b += tx(690, 340, len(d["langs"]), 22, c["fg"], "middle", 700, True) + tx(690, 356, "languages", 9.5, c["dim"], "middle")
    for i, (k, v) in enumerate(langs):
        yy = 290 + i * 22
        b += f'<circle cx="775" cy="{yy - 4}" r="4.5" fill="{LANGC.get(k, "#64748b")}"/>' + tx(787, yy, k, 11.5, c["fg"]) + tx(940, yy, f"{100 * v / tot:.0f}%", 11, c["dim"], "end", 600)
    # calendario nevado
    b += tile(24, 440, 937, 158, th) + tx(44, 466, "CONTRIBUTION CALENDAR", 9.5, c["gold"], weight=700, ls=2.2)
    first = dt.date.fromisoformat(cal[0][0])
    base = first - dt.timedelta(days=(first.weekday() + 1) % 7)
    for dte, n, lv in cal:
        dd = dt.date.fromisoformat(dte)
        col, row = (dd - base).days // 7, (dd.weekday() + 1) % 7
        b += f'<rect x="{44 + col * 17}" y="{478 + row * 14}" width="12" height="11" rx="3" fill="{c["heat"][lv]}"><title>{n} on {dte}</title></rect>'
    b += tx(805, 466, "Less", 9.5, c["faint"], "end") + "".join(f'<rect x="{814 + i * 16}" y="457" width="12" height="11" rx="3" fill="{c["heat"][i]}"/>' for i in range(5)) + tx(902, 466, "More", 9.5, c["faint"])
    return svg(w, h, th, "GitHub activity: contributions, languages and calendar", b)


# ------------------------------------------------------------------ main
if __name__ == "__main__":
    d = load()
    for f in OUT.glob("*.svg"): f.unlink()
    for th in T:
        (OUT / f"hero-{th}.svg").write_text(hero(th, d), encoding="utf-8")
        (OUT / f"about-{th}.svg").write_text(about(th, d), encoding="utf-8")
        (OUT / f"activity-{th}.svg").write_text(activity(th, d), encoding="utf-8")
        for i, p in enumerate(PROJECTS, 1):
            (OUT / f"project-{slug(p)}-{th}.svg").write_text(project(th, p, d, i), encoding="utf-8")
    print("ok:", len(list(OUT.glob("*.svg"))), "svg en", OUT)
