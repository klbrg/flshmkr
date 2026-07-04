import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from goverify import run_go, verify_cards, go_available

assert go_available(), "go toolchain required for these tests"

CASES = [
    # (code, expected_stdout, want_status)
    ('package main\nfunc main() {}', None, 'ok'),                                   # compiles
    ('package main\nfunc main() { x }', None, 'MISMATCH'),                          # does not compile
    ('package main\nimport "fmt"\nfunc main(){ fmt.Println(2+3*4) }', '14', 'ok'),  # correct output
    ('package main\nimport "fmt"\nfunc main(){ fmt.Println(2+3*4) }', '20', 'MISMATCH'),  # wrong output claim
    # classic Go gotcha: append aliasing — verify the real printed behaviour
    ('package main\nimport "fmt"\nfunc main(){ s:=[]int{1,2,3}; a:=s[:2]; a=append(a,99); fmt.Println(s) }', '[1 2 99]', 'ok'),
    ('package main\nimport "fmt"\nfunc main(){ s:=[]int{1,2,3}; a:=s[:2]; a=append(a,99); fmt.Println(s) }', '[1 2 3]', 'MISMATCH'),
]
fails = 0
for i,(code, out, want) in enumerate(CASES):
    got,_ = run_go(code, out)
    ok = got == want
    fails += not ok
    print(f"  [{'PASS' if ok else 'FAIL'}] want={want:9} got={got:9} case {i}")

# compile_error mode: code that must NOT compile
assert run_go('package main\nimport "fmt"\nfunc main(){ fmt := "x"; fmt.Println() }', expect_compile_error=True)[0] == 'ok'
assert run_go('package main\nfunc main(){}', expect_compile_error=True)[0] == 'MISMATCH'
print("  [PASS] compile_error mode")

deck = [
    {"front": "prints 6?", "verify": {"code": 'package main\nimport "fmt"\nfunc main(){ fmt.Print(2*3) }', "stdout": "6"}},
    {"front": "concept card, no code"},
    {"front": "bad claim", "verify": {"code": 'package main\nimport "fmt"\nfunc main(){ fmt.Print(2*3) }', "stdout": "5"}},
]
chk, ok, f = verify_cards(deck)
good = (chk == 2 and ok == 1 and len(f) == 1)
fails += not good
print(f"  [{'PASS' if good else 'FAIL'}] deck: checked={chk} ok={ok} fails={len(f)} (concept card skipped)")

print(f"\n{'ALLA GRÖNA' if fails==0 else str(fails)+' RÖDA'}")
sys.exit(1 if fails else 0)
