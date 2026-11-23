#!/usr/bin/env python3
"""Genera las tarjetas SVG animadas del perfil en ../assets.

  python scripts/build.py            # con PROFILE_TOKEN usa GraphQL (actividad privada agregada); sin token, API publica
  python scripts/build.py --offline  # solo usa assets/data-cache.json y assets/projects-cache.json
Los proyectos se editan en scripts/projects.json. Nada de repos privados se escribe en SVG, cache o README
(salvo "public_ok": true en el proyecto).
"""
import base64, datetime as dt, html, json, math, os, random, re, sys, textwrap, urllib.error, urllib.parse, urllib.request
from pathlib import Path

USER = "TonyMed12"
NAME = "José Antonio Medina Ayala"
EMAIL, SITE, LINKEDIN = "tonymed2022@gmail.com", "tonymed.dev", "tony-medinaa"
ABOUT = [("WHO I AM", "Computer Systems Engineering", "9th-semester student, Morelia"), ("WHAT I LIKE", "Learning something", "new every week"),
         ("OFF THE KEYBOARD", "Soccer, pádel, travel", "and practicing English")]
CEDULA = "15938245"  # numero de cedula (cadena); vacio -> solo se destaca el titulo
CED = "Technical License (Cédula)" + (f" · No. {CEDULA}" if CEDULA else "")
PHOTO = False  # False -> iniciales en lugar de la foto de GitHub
OUT = Path(__file__).resolve().parent.parent / "assets"
OUT.mkdir(exist_ok=True)
CACHE = OUT / "data-cache.json"
PCACHE = OUT / "projects-cache.json"
HERE = Path(__file__).resolve().parent
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
API = "https://api.github.com"
TOKEN = os.environ.get("PROFILE_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
TODAY = dt.date.today()
LEVEL = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


class _Redirect(urllib.request.HTTPRedirectHandler):
    """Si una redireccion sale de api.github.com, el token no la acompana."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        n = super().redirect_request(req, fp, code, msg, headers, newurl)
        if n and not newurl.startswith(API + "/"):
            n.headers.pop("Authorization", None)
            n.unredirected_hdrs.pop("Authorization", None)
        return n


_OPEN = urllib.request.build_opener(_Redirect).open


def get(url, raw=False, data=None):
    h = {"User-Agent": "profile-cards", "Accept": "application/vnd.github+json"}
    if TOKEN and url.startswith(API + "/"):  # el token solo viaja a api.github.com y nunca se imprime
        h["Authorization"] = f"bearer {TOKEN}"
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None, headers=h)
    with _OPEN(req, timeout=30) as r:
        b = r.read()
    return b if raw else json.loads(b)


def why(ex):
    """Descripcion corta y segura (sin URLs ni cabeceras) de un error."""
    return f"HTTP {ex.code}" if isinstance(ex, urllib.error.HTTPError) else type(ex).__name__


def graphql(query, **variables):
    res = get(API + "/graphql", data={"query": query, "variables": variables})
    if res.get("errors"):
        raise RuntimeError("; ".join(x.get("message", "") for x in res["errors"])[:160])
    return res["data"]


# Los repos privados solo se consultan para sumar bytes de lenguaje: nunca se pide su nombre ni su URL.
Q_USER = """query($l:String!){ user(login:$l){ id createdAt followers{totalCount}
  repositoriesContributedTo(first:1, contributionTypes:[COMMIT,PULL_REQUEST,REPOSITORY]){totalCount}
  repositories(first:1, ownerAffiliations:OWNER, privacy:PUBLIC){totalCount} } }"""
Q_LANGS = """query($l:String!, $after:String){ user(login:$l){
  repositories(first:100, after:$after, isFork:false, ownerAffiliations:[OWNER,COLLABORATOR,ORGANIZATION_MEMBER]){
    pageInfo{hasNextPage endCursor} nodes{ languages(first:10, orderBy:{field:SIZE, direction:DESC}){ edges{ size node{name} } } } } } }"""
Q_YEAR = """query($l:String!, $from:DateTime!, $to:DateTime!){ user(login:$l){
  contributionsCollection(from:$from, to:$to){ totalCommitContributions totalPullRequestContributions restrictedContributionsCount
    contributionCalendar{ weeks{ contributionDays{ date contributionCount contributionLevel } } } } } }"""


def fetch_graphql():
    u = graphql(Q_USER, l=USER)["user"]
    days, commits, prs = {}, 0, 0
    for y in range(int(u["createdAt"][:4]), TODAY.year + 1):
        col = graphql(Q_YEAR, l=USER, **{"from": f"{y}-01-01T00:00:00Z", "to": f"{y}-12-31T23:59:59Z"})["user"]["contributionsCollection"]
        commits += col["totalCommitContributions"]
        prs += col["totalPullRequestContributions"]
        for wk in col["contributionCalendar"]["weeks"]:
            for dy in wk["contributionDays"]:
                days[dy["date"]] = (dy["contributionCount"], LEVEL.get(dy["contributionLevel"], 0))
    last = graphql(Q_YEAR, l=USER, **{"from": f"{TODAY - dt.timedelta(days=364)}T00:00:00Z", "to": f"{TODAY}T23:59:59Z"})["user"]["contributionsCollection"]
    langs, after = {}, None
    while True:
        r = graphql(Q_LANGS, l=USER, after=after)["user"]["repositories"]
        for n in r["nodes"]:
            for e_ in n["languages"]["edges"]:
                langs[e_["node"]["name"]] = langs.get(e_["node"]["name"], 0) + e_["size"]
        if not r["pageInfo"]["hasNextPage"]: break
        after = r["pageInfo"]["endCursor"]
    since = (TODAY - dt.timedelta(days=371)).isoformat()
    cal = [(d_, *days[d_]) for d_ in sorted(days) if since < d_ <= TODAY.isoformat()]
    return dict(user=dict(repos=u["repositories"]["totalCount"], followers=u["followers"]["totalCount"]), langs=langs, cal=cal,
                commits=commits, prs=prs, contributed=u["repositoriesContributedTo"]["totalCount"],
                private_1y=last["restrictedContributionsCount"], since=int(u["createdAt"][:4]))


def fetch_public():
    """Respaldo sin token: solo repos publicos y el calendario publico (scraping)."""
    u = get(f"{API}/users/{USER}")
    langs = {}
    for r in get(f"{API}/users/{USER}/repos?per_page=100"):
        if r["fork"]: continue
        for k, v in get(r["languages_url"]).items():
            langs[k] = langs.get(k, 0) + v
    page = get(f"https://github.com/users/{USER}/contributions", raw=True).decode("utf-8")
    cells = re.findall(r'data-date="([\d-]+)"[^>]*data-level="(\d)"', page)
    tips = re.findall(r"<tool-tip[^>]*>([^<]+)</tool-tip>", page)
    cal = sorted((d_, int(re.match(r"(\d+)", t).group(1)) if t[0].isdigit() else 0, int(l)) for (d_, l), t in zip(cells, tips))
    commits = get(f"{API}/search/commits?q=author:{USER}")["total_count"]
    prs = get(f"{API}/search/issues?q=author:{USER}+type:pr")["total_count"]
    return dict(user=dict(repos=u["public_repos"], followers=u["followers"]), langs=langs, cal=cal, commits=commits, prs=prs)


def load():
    if "--offline" not in sys.argv:
        for name, fn in (("graphql", fetch_graphql), ("public", fetch_public)):
            if name == "graphql" and not TOKEN: continue
            try:
                d = fn(); d["mode"] = name
                CACHE.write_text(json.dumps(d), encoding="utf-8"); print("datos:", name); return d
            except Exception as ex:
                print(f"aviso: fallo el modo {name} ({why(ex)}); sigo con el siguiente o con la cache", file=sys.stderr)
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
.dsh{{animation:dsh 6s linear infinite}}
@keyframes dsh{{to{{stroke-dashoffset:-110}}}}
.tm{{opacity:0;animation:tmin .7s cubic-bezier(.2,.8,.2,1) forwards}}
@keyframes nudge{{50%{{transform:translateX(5px)}}}}
.nudge{{animation:nudge 1.6s ease-in-out infinite}}
@keyframes tmin{{from{{opacity:0;transform:translateY(4px)}}to{{opacity:1;transform:none}}}}
.dot{{opacity:0;animation:tmin .7s cubic-bezier(.2,.8,.2,1) forwards,dotp 2.6s ease-in-out infinite}}
@keyframes dotp{{0%,100%{{fill:#93c5fd}}50%{{fill:#f5c26b}}}}
.flt{{animation:flt 5s ease-in-out infinite}}
@keyframes flt{{50%{{transform:translateY(-6px)}}}}
.sway{{animation:sway 4s ease-in-out infinite}}
@keyframes sway{{50%{{transform:rotate(5deg)}}}}
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
    h = 520
    b = snow(th, w, h, 55, 2)
    for i, x in enumerate(range(24, w - 10, 30)):  # guirnalda
        b += f'<circle class="tw" cx="{x}" cy="{12 + 6 * math.sin(x / 36):.1f}" r="3.6" fill="{LIGHTS[i % 5]}" style="animation-delay:-{(i * .7) % 3:.1f}s"/>'
    cx, cy, rad = 168, 178, 100
    r2 = random.Random(5)
    if PHOTO and d.get("avatar"):  # foto con aro dorado y nieve encima
        b += (f'<clipPath id="ph"><circle cx="{cx}" cy="{cy}" r="{rad}"/></clipPath>'
              f'<circle class="spin" style="--o:{cx}px {cy}px" cx="{cx}" cy="{cy}" r="{rad + 20}" fill="none" stroke="{c["gold"]}" stroke-opacity=".5" stroke-dasharray="2 9" stroke-linecap="round"/>'
              f'<circle cx="{cx}" cy="{cy}" r="{rad + 7}" fill="none" stroke="{c["gold"]}" stroke-width="3"/>'
              f'<image class="fd" href="data:image/jpeg;base64,{d["avatar"]}" x="{cx - rad}" y="{cy - rad}" width="{2 * rad}" height="{2 * rad}" preserveAspectRatio="xMidYMid slice" clip-path="url(#ph)"/>')
        for a in range(-158, -21, 9):
            ar = math.radians(a)
            b += f'<circle cx="{cx + (rad + 7) * math.cos(ar):.1f}" cy="{cy + (rad + 7) * math.sin(ar):.1f}" r="{r2.uniform(5, 9):.1f}" fill="#fff"/>'
    else:  # monograma "tm." = favicon de tonymed.dev, animado y con gorro navideno (GitHub ya muestra la foto aparte)
        sx, sy, sz = cx - rad, cy - rad, 2 * rad
        b += (f'<ellipse cx="{cx}" cy="{sy + sz + 22}" rx="84" ry="8" fill="{c["ice"]}" opacity=".18"/><g class="flt">'
              f'<svg x="{sx}" y="{sy}" width="{sz}" height="{sz}" viewBox="0 0 64 64" overflow="visible"><rect x=".4" y=".4" width="63.2" height="63.2" rx="14" fill="#101c36" stroke="#93c5fd" stroke-opacity=".45" stroke-width=".8"/>'
              f'<g font-family="Arial,Helvetica,sans-serif" font-size="30" font-weight="700" style="font-family:Arial,Helvetica,sans-serif">'
              f'<text class="tm" x="10" y="43" fill="#93c5fd" style="animation-delay:.3s">t</text>'
              f'<text class="tm" x="17" y="43" fill="#93c5fd" style="animation-delay:.7s">m</text>'
              f'<text class="dot" x="40.7" y="43" fill="#93c5fd" style="animation-delay:1.1s,2.2s">.</text></g></svg>'
              f'<g transform="translate({sx + 40} {sy + 6}) rotate(-12)"><g class="sway">'  # gorro de Santa sobre la esquina
              f'<path d="M-34 -4 Q-24 -74 22 -66 Q12 -42 34 -4Z" fill="#dc2626"/>'
              f'<rect x="-42" y="-10" width="84" height="20" rx="10" fill="#fff"/><circle cx="23" cy="-66" r="10" fill="#fff"/></g></g></g>')
    b += tx(cx, cy + rad + 50, "Morelia, México", 12, c["dim"], "middle", ls=1)
    # texto
    x0 = 330
    b += (tx(x0, 66, "COMPUTER SYSTEMS ENGINEERING STUDENT  ·  SOFTWARE DEVELOPMENT", 11, c["gold"], weight=700, ls=3, cls="up", delay=.1) +
          tx(x0, 112, "José Antonio", 44, c["fg"], weight=700, serif=True, cls="up", delay=.25) +
          tx(x0, 158, "Medina Ayala", 44, c["fg"], weight=700, serif=True, cls="up", delay=.4))
    b += tx(x0, 194, "Hi, I'm Tony.", 20, c["gold"], weight=700, serif=True, cls="up", delay=.6)
    for i, (lab, l1, l2) in enumerate(ABOUT):
        bx, dl = x0 + sum((236, 186, 186)[:i]) + 12 * i, .8 + i * .15
        b += (tile(bx, 208, (236, 186, 186)[i], 72, th, 12) + tx(bx + 14, 228, lab, 8.5, c["gold"], weight=700, ls=1.6, cls="up", delay=dl) +
              tx(bx + 14, 249, l1, 12, c["fg"], weight=600, cls="up", delay=dl) + tx(bx + 14, 266, l2, 12, c["dim"], cls="up", delay=dl))
    x, row = x0, 302
    for s, kw in [("Open to internships & junior roles", dict(dot=c["ok"], bold=True)), (CED, dict(color=c["ok"], bold=True)),
                  ("Available now · will relocate to Morelia, Acámbaro or Querétaro · hybrid or remote", dict(color=c["gold"], bold=True))]:
        if x + len(s) * 11.5 * .56 + 36 > 962: x, row = x0, row + 32
        o, wd = chip(x, row, s, th, 11.5, **kw); b += o; x += wd + 10
    y = row + 40
    items = [("GITHUB", USER), ("EMAIL", EMAIL), ("LINKEDIN", LINKEDIN)]
    t1 = "Get to know me better"
    cw_ = 14 + len(t1) * 7.1 + 30 + len(SITE) * 6.9 + 12
    b += (f'<rect x="{x0}" y="{y}" width="{cw_:.0f}" height="26" rx="13" fill="{c["gold"]}" fill-opacity=".2" stroke="{c["gold"]}" stroke-width="1.6"/>' +
          tx(x0 + 14, y + 17.5, t1, 12, c["fg"], weight=700) + tx(f"{x0 + 14 + len(t1) * 7.1 + 6:.0f}", y + 18, "→", 13, c["gold"], weight=700, cls="nudge") +
          tx(f"{x0 + 14 + len(t1) * 7.1 + 28:.0f}", y + 17.5, SITE, 12, c["gold"], weight=700))
    x = x0 + cw_ + 10
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
    y = 80
    edu = [("Computer Systems Engineering", ["Instituto Tecnológico de Morelia · 9th semester", "Specialization in Software", "Development Technologies"]),
           ("Programming Technician", [CED])]
    for i, (t1, subs) in enumerate(edu):
        nxt = y + 17 + 14 * (len(subs) - 1) + 24
        b += f'<circle cx="52" cy="{y - 4}" r="4" fill="{c["gold"]}"/>' + (f'<line x1="52" x2="52" y1="{y + 2}" y2="{nxt - 10}" stroke="{c["gold"]}" stroke-opacity=".35"/>' if i == 0 else "")
        b += tx(66, y, t1, 11.2, c["fg"], weight=600, serif=True)
        for k, t2 in enumerate(subs):
            b += tx(66, y + 17 + 14 * k, t2, 10.5, c["gold"] if k else c["dim"], weight=600 if k else 400)
        y = nxt
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
def load_projects():
    items = json.loads((HERE / "projects.json").read_text(encoding="utf-8"))
    items = [p for p in items if not p.get("draft")]  # "draft": true -> aun sin rellenar, no se publica
    for p in items:
        p.setdefault("owner", USER); p.setdefault("public_ok", False); p.setdefault("tags", []); p.setdefault("highlights", [])
    return sorted(items, key=lambda p: p.get("order", 99))


_ME = []


def my_id():
    if not _ME:
        _ME.append(graphql("query($l:String!){user(login:$l){id}}", l=USER)["user"]["id"])
    return _ME[0]


def repo_metrics(p, cache):
    """Metricas automaticas de owner/repo; {} si no hay repo; {"private": True} si no debe mostrarse."""
    if not p.get("repo"): return {}
    sl, full = p["slug"], f'{p["owner"]}/{p["repo"]}'
    try:
        info = get(f"{API}/repos/{full}")
    except Exception as ex:
        print(f"aviso: {sl}: no pude leer el repo ({why(ex)}); uso cache o datos manuales", file=sys.stderr)
        return cache.get(sl) or ({} if p["public_ok"] else {"private": True})  # sin poder verificar, se asume privado
    if info["private"] and not p["public_ok"]:
        return {"private": True}
    m, mine = {"pushed": info["pushed_at"][:10]}, None
    if TOKEN:
        try:
            r = graphql("query($o:String!,$n:String!,$id:ID!){repository(owner:$o,name:$n){defaultBranchRef{target{... on Commit{history(author:{id:$id}){totalCount}}}}}}",
                        o=p["owner"], n=p["repo"], id=my_id())
            mine = r["repository"]["defaultBranchRef"]["target"]["history"]["totalCount"]
        except Exception as ex:
            print(f"aviso: {sl}: GraphQL de commits fallo ({why(ex)}); uso contributors", file=sys.stderr)
    try:
        people = [c for c in get(f"{API}/repos/{full}/contributors?per_page=100") if c.get("type") != "Bot" and "[bot]" not in c["login"]]
        mc = next((c["contributions"] for c in people if c["login"].lower() == USER.lower()), 0)
        m["team"] = len(people)
        if mc: m["rank"] = 1 + sum(c["contributions"] > mc for c in people)
        mine = max(mine or 0, mc)  # GraphQL puede dar 0 si el correo de los commits no esta vinculado a la cuenta
    except Exception as ex:
        print(f"aviso: {sl}: contributors fallo ({why(ex)})", file=sys.stderr)
    try:
        m["prs"] = get(f"{API}/search/issues?q=" + urllib.parse.quote(f"repo:{full} author:{USER} is:pr is:merged"))["total_count"]
    except Exception as ex:
        print(f"aviso: {sl}: busqueda de PRs fallo ({why(ex)})", file=sys.stderr)
    m["commits"] = mine
    for k, v in (cache.get(sl) or {}).items(): m.setdefault(k, v)  # lo que fallo hoy se completa con el ultimo dato bueno
    if mine == 0:
        print(f"aviso: {sl}: 0 commits tuyos en {full}. Probable: los commits se hicieron con un correo no vinculado a tu cuenta "
              f"(GitHub > Settings > Emails) o el equipo uso squash merge (la tarjeta muestra los PRs fusionados: {m.get('prs')}).", file=sys.stderr)
    return m


def project_data(projects):
    cache = json.loads(PCACHE.read_text(encoding="utf-8")) if PCACHE.exists() else {}
    out = {}
    for p in projects:
        if "--offline" in sys.argv:  # sin red: si nunca se verifico como publico, se trata como privado
            out[p["slug"]] = cache.get(p["slug"]) or ({} if (not p.get("repo") or p["public_ok"]) else {"private": True})
        else:
            out[p["slug"]] = repo_metrics(p, cache)
    PCACHE.write_text(json.dumps({k: v for k, v in out.items() if v and not v.get("private")}, indent=1, sort_keys=True), encoding="utf-8")
    return out


def link_of(p, m):
    ln = p.get("link", "")
    return ln if ln.startswith("http") and not m.get("private") else ""


def fit_kind(kind, avail):
    for size, ls in ((9.5, 1.6), (8.6, .8), (8, .3)):
        if len(kind) * (size * .62 + ls) <= avail: return size, ls, kind
    n = max(8, int(avail / (8 * .62 + .3)) - 1)
    return 8, .3, kind[:n].rstrip() + "…"


def project(th, p, m, idx):
    c, w = T[th], 480
    hl = p["highlights"][:3]
    dy = 18 * len(hl)
    h = 292 + dy
    private = bool(m.get("private"))
    mine, prs = m.get("commits"), m.get("prs")
    first = ("COMMITS", mine) if mine else (("PRS MERGED", prs) if prs else ("COMMITS", "—"))
    team = p.get("team", m.get("team", "—"))
    path = "private repository" if private else (f'{p["owner"]}/{p["repo"]}'.lower() if p.get("repo") and p["owner"].lower() != USER.lower() else "")
    b = tile(0.5, 0.5, w - 1, h - 1, th, 18)
    b += f'<rect x="0.5" y="22" width="4" height="64" rx="2" fill="{c["gold"]}"/>'
    b += tx(28, 42, f"{idx:02d}", 12, c["gold"], weight=700, serif=True, ls=1)
    used = 56
    if path:
        b += tx(54, 42, "· " + path, 9.5, c["dim"], weight=600); used = 54 + (len(path) + 2) * 5.9
    size, ls, kind = fit_kind(p["kind"].upper(), w - 26 - used - 12)
    b += tx(w - 26, 42, kind, size, c["faint"], "end", 600, ls=ls) + tx(28, 80, p["title"], 25, c["fg"], weight=700, serif=True)
    y = 106
    for ln in textwrap.wrap(p["desc"], 62)[:2]:
        b += tx(28, y, ln, 12.5, c["dim"]); y += 19
    if p.get("role"):
        o, _ = chip(28, 150, p["role"], th, 11, c["gold"], bold=True); b += o
    for i, t in enumerate(hl):
        b += f'<circle cx="32" cy="{188 + 18 * i}" r="2.6" fill="{c["gold"]}"/>' + tx(42, 192 + 18 * i, t, 11.5, c["fg"])
    b += f'<line x1="28" x2="{w - 28}" y1="{196 + dy}" y2="{196 + dy}" stroke="{c["edge"]}" stroke-opacity="{c["edgeo"]}"/>'
    third = p.get("third") or ["", "—"]
    for i, (num, lab) in enumerate([(str(first[1]), first[0]), (str(team), "PEOPLE"), (third[1], third[0].upper())]):
        mx = 28 + i * 140
        b += tx(mx, 230 + dy, num, 22 if i < 2 else 15, c["fg"] if i < 2 else c["ice"], weight=700, serif=True) + tx(mx, 247 + dy, lab, 9, c["faint"], weight=600, ls=1.6)
    x = 28
    for t in p["tags"]:
        b += tx(f"{x:.0f}", 276 + dy, "# " + t, 10, c["ice"], weight=600); x += len(t) * 6.2 + 30
    label = "private repository" if private else (p.get("link_label") or re.sub(r"^https?://", "", p.get("link", "")).rstrip("/"))
    if label: b += tx(w - 26, 276 + dy, label + (" ↗" if link_of(p, m) else ""), 10, c["faint"], "end")
    return svg(w, h, th, f"{p['title']} — {p['kind']}", f'<g opacity="1">{b}</g>' + snow(th, w, h, 6, sum(map(ord, p["slug"]))))


def pic(name, alt, link="", width="100%"):
    t = (f'<picture><source media="(prefers-color-scheme: dark)" srcset="assets/{name}-dark.svg"><source media="(prefers-color-scheme: light)" '
         f'srcset="assets/{name}-light.svg"><img alt="{html.escape(alt, quote=True)}" src="assets/{name}-dark.svg" width="{width}"></picture>')
    return f'<a href="{link}">{t}</a>' if link else t


def update_readme(projects, pm):
    """Reescribe solo el bloque entre <!-- projects:start --> y <!-- projects:end --> (orden = campo "order")."""
    rd = HERE.parent / "README.md"
    if not rd.exists(): return
    txt = rd.read_text(encoding="utf-8")
    a, b = txt.find("<!-- projects:start -->"), txt.find("<!-- projects:end -->")
    if a < 0 or b < a: return
    cards = [pic(f"project-{p['slug']}", p["title"], link_of(p, pm[p["slug"]]), "49%") + ("<br>" if i % 2 else "") for i, p in enumerate(projects)]
    rd.write_text(txt[:a] + "<!-- projects:start -->\n" + "\n".join(cards) + "\n" + txt[b:], encoding="utf-8")


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
          tx(40, 128, f"in the last 12 months  ·  {active} active days  ·  longest streak {best} days  ·  current {cur}" + (f"  ·  includes {d['private_1y']} private" if d.get("private_1y") else ""), 12.5, c["dim"]))
    for i, (num, lab) in enumerate([(d.get("contributed") or d["user"]["repos"], "REPOS CONTRIBUTED TO" if d.get("contributed") else "REPOSITORIES"), (d["commits"], "COMMITS"), (d["prs"], "PULL REQUESTS"), (active, "ACTIVE DAYS")]):
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
    projects = load_projects()
    pm = project_data(projects)
    for th in T:
        (OUT / f"hero-{th}.svg").write_text(hero(th, d), encoding="utf-8")
        (OUT / f"about-{th}.svg").write_text(about(th, d), encoding="utf-8")
        (OUT / f"activity-{th}.svg").write_text(activity(th, d), encoding="utf-8")
        for i, p in enumerate(projects, 1):
            (OUT / f"project-{p['slug']}-{th}.svg").write_text(project(th, p, pm[p["slug"]], i), encoding="utf-8")
    keep = {f"project-{p['slug']}-{th}.svg" for p in projects for th in T}
    for f in OUT.glob("project-*.svg"):  # solo se borran las tarjetas de proyectos que ya no estan en projects.json
        if f.name not in keep: f.unlink()
    update_readme(projects, pm)
    print("ok:", len(list(OUT.glob("*.svg"))), "svg en", OUT)
