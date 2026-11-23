"""Comprobaciones minimas: python scripts/test_build.py"""
import build

# rachas: 'hoy' sin actividad no rompe la racha actual
cal = [("2026-01-0%d" % i, c, 0) for i, c in enumerate([1, 1, 0, 2, 3, 0], 1)]
assert build.streaks(cal) == (2, 2), build.streaks(cal)
assert build.streaks([("2026-01-01", 1, 0), ("2026-01-02", 1, 0)]) == (2, 2)

# el titulo largo de un hackathon cabe o se recorta, nunca desborda
size, ls, k = build.fit_kind("HACKATHON · INNOVATION FEST 2026 · 1ST PLACE", 299)
assert len(k) * (size * .62 + ls) <= 299 or k.endswith("…")

# privacidad: un proyecto privado sin public_ok no deja rastro del repo en la tarjeta ni en el enlace
p = dict(slug="secreto", owner="Org", repo="repo-ultra-privado", title="Mi proyecto", kind="Work", role="Dev",
         desc="Texto escrito por mi.", tags=[], highlights=[], third=["Stack", "X"], link="https://github.com/Org/repo-ultra-privado", public_ok=False)
m = {"private": True}
assert build.link_of(p, m) == ""
for th in build.T:
    svg = build.project(th, p, m, 1)
    assert "repo-ultra-privado" not in svg and "github.com/Org" not in svg and "private repository" in svg
print("test_build ok")
