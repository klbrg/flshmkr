"""Compile-and-run verification gate for Go flashcards.

A card may carry a `verify` payload the card-writer produced:
  {"verify": {"code": "<full runnable go program>"}}              -> must COMPILE
  {"verify": {"code": "<...>", "stdout": "<expected output>"}}    -> must compile AND print exactly this
The gate executes each with the real `go` toolchain; precision-first, only flags what actually fails.
"""
import json, subprocess, tempfile, os, sys

def go_available():
    try:
        return subprocess.run(["go", "version"], capture_output=True).returncode == 0
    except Exception:
        return False

def run_go(code, expected_stdout=None, expect_compile_error=False, timeout=20):
    """Return ('ok'|'MISMATCH', detail)."""
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "main.go"), "w") as f:
            f.write(code)
        subprocess.run(["go", "mod", "init", "verifytmp"], cwd=d, capture_output=True)
        try:
            if expect_compile_error:
                r = subprocess.run(["go", "build", "-o", os.devnull, "."],
                                   cwd=d, capture_output=True, text=True, timeout=timeout)
                return ("ok", "") if r.returncode != 0 else ("MISMATCH", "expected a compile error but it compiled")
            if expected_stdout is None:
                r = subprocess.run(["go", "build", "-o", os.devnull, "."],
                                   cwd=d, capture_output=True, text=True, timeout=timeout)
                return ("ok", "") if r.returncode == 0 else ("MISMATCH", "compile error: " + r.stderr.strip()[:400])
            r = subprocess.run(["go", "run", "."], cwd=d, capture_output=True, text=True, timeout=timeout)
            if r.returncode != 0:
                return ("MISMATCH", "compile/run error: " + r.stderr.strip()[:400])
            got, exp = r.stdout.strip(), expected_stdout.strip()
            return ("ok", "") if got == exp else ("MISMATCH", f"expected {exp!r} got {got!r}")
        except subprocess.TimeoutExpired:
            return ("MISMATCH", "timeout")

def verify_cards(cards):
    """Return (checked, ok, failures[])."""
    checked = ok = 0
    fails = []
    for c in cards:
        v = c.get("verify")
        if not isinstance(v, dict) or not v.get("code"):
            continue
        checked += 1
        if v.get("compile_error"):
            status, detail = run_go(v["code"], expect_compile_error=True)
        else:
            status, detail = run_go(v["code"], v.get("stdout"))
        if status == "ok":
            ok += 1
        else:
            fails.append({"front": c.get("front", c.get("Front", "")), "detail": detail})
    return checked, ok, fails

if __name__ == "__main__":
    if not go_available():
        print("go toolchain not found"); sys.exit(2)
    data = json.load(open(sys.argv[1]))
    cards = data["cards"] if isinstance(data, dict) else data
    checked, ok, fails = verify_cards(cards)
    import re
    name = sys.argv[1].split("/")[-1]
    print(f"{name}: verifierbara={checked} korrekta={ok} avvikelser={len(fails)}")
    for f in fails:
        print("  [AVVIK]", re.sub("<[^>]+>", " ", f["front"])[:70], "->", f["detail"][:120])
    sys.exit(1 if fails else 0)
