import sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathverify import check, check_identity

# (front, back, expected)   expected in {'ok','MISMATCH','skip'}
CARD_TESTS = [
    # --- CORRECT calculation cards -> must pass ('ok') ---
    (r'Beräkna \(2+3\cdot4\)',                r'\(14\)',            'ok'),
    (r'Beräkna \(5^2\cdot5^4\)',              r'\(5^6\)',           'ok'),
    (r'Skriv \(4^{-2}\) som ett bråk',        r'\(\frac{1}{16}\)',  'ok'),
    (r'Beräkna \((11^3)^4\)',                 r'\(11^{12}\)',       'ok'),
    (r'Beräkna \(7-(-3)\)',                   r'\(10\)',            'ok'),
    (r'Beräkna \(\sqrt{\frac{25}{64}}\)',     r'\(\frac{5}{8}\)',   'ok'),
    (r'Förenkla \(\dfrac{\sqrt{75}}{\sqrt{3}}\)', r'\(5\)',         'ok'),   # the ex-false-positive
    (r'Beräkna \(\frac{-12}{-3}\)',           r'\(4\)',             'ok'),

    # --- WRONG cards -> SymPy MUST catch them ('MISMATCH') ---
    (r'Beräkna \(2+3\cdot4\)',                r'\(20\)',            'MISMATCH'),  # 14 not 20
    (r'Beräkna \(5^2\cdot5^4\)',              r'\(5^8\)',           'MISMATCH'),  # 5^6 not 5^8
    (r'Skriv \(4^{-2}\) som ett bråk',        r'\(\frac{1}{8}\)',   'MISMATCH'),  # 1/16 not 1/8
    (r'Beräkna \(7-(-3)\)',                   r'\(4\)',             'MISMATCH'),  # sign error: 10 not 4
    (r'Beräkna \(\sqrt{\frac{25}{64}}\)',     r'\(\frac{5}{16}\)',  'MISMATCH'),  # 5/8 not 5/16
    (r'Förenkla \(\dfrac{\sqrt{75}}{\sqrt{3}}\)', r'\(15\)',        'MISMATCH'),  # 5 not 15
    (r'Beräkna \((11^3)^4\)',                 r'\(11^{7}\)',        'MISMATCH'),  # 11^12 not 11^7


    # --- mixed-number answers (1\\frac{1}{4} = 5/4) ---
    (r'Beräkna \(\frac{3}{4}+\frac{2}{4}\)', r'\(\frac{5}{4}=1\frac{1}{4}\)', 'ok'),
    (r'Beräkna \(\frac{3}{4}+\frac{2}{4}\)', r'\(1\frac{1}{2}\)', 'MISMATCH'),
    # --- MGN (answer = lcm of denominators) ---
    (r'Vad är minsta gemensamma nämnare (MGN) till \(\frac{1}{4}\) och \(\frac{1}{6}\)?', r'\(12\)', 'ok'),
    (r'Vad är minsta gemensamma nämnare (MGN) till \(\frac{1}{4}\) och \(\frac{1}{6}\)?', r'\(24\)', 'MISMATCH'),
    # --- reciprocal / concept -> must skip ---
    (r'Att dividera med \(\frac{4}{5}\) är samma sak som att multiplicera med?', r'\(\frac{5}{4}\)', 'skip'),
    (r'Beräkna \(\frac{2}{3}\cdot\frac{3}{4}\)', r'\(\frac{2}{3}\cdot\frac{3}{4}=\frac{1}{2}\)', 'ok'),

        (r'Lös ekvationen \(f(x)=9\) där \(f(x)=2x+1\)', r'\(x=4\)','skip'),
        (r'Beräkna värdet av \(f(x)=2x-x^2\) när \(x=-3\)', r'\(f(-3)=-15\)','skip'),
        (r'Beräkna \(10\cdot\sin(30^\circ)\)', r'\(10\cdot\sin(30^\circ)=5\)','skip'),
        (r'Bestäm \(\tan(35^\circ)\)', r'\(\approx 0{,}70\)','skip'),
    # --- UNVERIFIABLE -> must NOT be false-flagged ('skip') ---
    (r'I uttrycket \(20/(5-3)+5\cdot 2^2-7\), vad beräknar du först?', r'Parenteser: \(5-3=2\)', 'skip'),  # order question
    (r'Vad är basen i \(5^4\)?',              r'\(5\)',             'skip'),  # not a calc-keyword
    (r'Förenkla \(a^m\cdot a^n\)',            r'\(a^{m+n}\)',       'ok'),  # symbolic, not numeric
]

# (lhs, rhs, is_true_identity)
IDENTITY_TESTS = [
    (r'a^m\cdot a^n',        r'a^{m+n}',        True),
    (r'\frac{a^m}{a^n}',     r'a^{m-n}',        True),
    (r'(a^m)^n',             r'a^{mn}',         True),
    (r'\sqrt{a^2}',          r'Abs(a)',         True),
    (r'a^m\cdot a^n',        r'a^{mn}',         False),  # wrong power law
    (r'(a^m)^n',             r'a^{m+n}',        False),  # wrong
    (r'\frac{a^m}{a^n}',     r'a^{m+n}',        False),  # wrong
]

def run():
    fails = 0
    print("== card checks ==")
    for front, back, exp in CARD_TESTS:
        got = check(front, back)
        ok = got == exp
        fails += not ok
        tag = 'PASS' if ok else 'FAIL'
        print(f"  [{tag}] expect={exp:9} got={got:9} | {front[:48]} -> {back[:22]}")
    print("== identity checks ==")
    for lhs, rhs, exp in IDENTITY_TESTS:
        got = check_identity(lhs, rhs)
        ok = got == exp
        fails += not ok
        tag = 'PASS' if ok else 'FAIL'
        print(f"  [{tag}] expect={str(exp):5} got={str(got):5} | {lhs} = {rhs}")
    total = len(CARD_TESTS) + len(IDENTITY_TESTS)
    print(f"\n{total-fails}/{total} tester gröna" + ("" if fails==0 else f"  ({fails} RÖDA)"))
    return fails


from mathverify import value_check, is_calc_tag, verify_cards
def run_tagtests():
    fails=0
    print("== value_check (tag-driven) ==")
    VC=[(r'\(\frac{2}{3}\cdot\frac{3}{4}\)', r'\(\frac{1}{2}\)','ok'),
        (r'\(\frac{2}{3}\cdot\frac{3}{4}\)', r'\(\frac{1}{3}\)','MISMATCH'),
        (r'Beräkna \(7-(-3)\)', r'\(10\)','ok'),
        (r'\(\frac{3}{4}+\frac{2}{4}\)', r'\(1\frac{1}{4}\)','ok'),
        (r'Gör ett överslag av \(19{,}8+4{,}1\)', r'\(19{,}8+4{,}1\approx 20+4=24\)','ok')]
    for f,b,e in VC:
        g=value_check(f,b); ok=g==e; fails+=not ok
        print(f"  [{'PASS' if ok else 'FAIL'}] expect={e:9} got={g:9} | {f[:40]} -> {b[:20]}")
    print("== tag detection + verify_cards ==")
    assert is_calc_tag(['matematik','beräkning'])
    assert is_calc_tag(['matematik::aritmetik::beräkning'])
    assert not is_calc_tag(['matematik','matematik::aritmetik::brak'])
    # deck with tags: only tagged cards checked; wrong tagged card caught
    deck=[{'front':r'\(\frac{2}{3}\cdot\frac{3}{4}\)','back':r'\(\frac{1}{3}\)','tags':['matematik','beräkning']},
          {'front':'Vad är basen i \(5^4\)?','back':r'\(5\)','tags':['matematik']}]
    chk,ok,mism=verify_cards(deck)
    good = (chk==1 and ok==0 and len(mism)==1)
    fails+=not good
    print(f"  [{'PASS' if good else 'FAIL'}] tag-driven deck: checked={chk} ok={ok} mismatch={len(mism)} (concept card ignored)")
    print(f"  tag-tester: {'gröna' if fails==0 else str(fails)+' RÖDA'}")
    return fails

sys.exit(1 if (run() + run_tagtests()) else 0)
