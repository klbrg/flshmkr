import re
from sympy import sqrt, Rational, simplify, pi, Abs, Integer, ilcm, symbols
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
TR = standard_transformations + (implicit_multiplication_application,)
LOC = {'sqrt': sqrt, 'Rational': Rational, 'pi': pi, 'Abs': Abs}

def read_group(s, i):
    depth = 0
    for j in range(i, len(s)):
        if s[j] == '{': depth += 1
        elif s[j] == '}':
            depth -= 1
            if depth == 0: return s[i+1:j], j+1
    return None
def _ws(s, i):
    while i < len(s) and s[i] == ' ': i += 1
    return i
def conv(s):
    while True:
        k = s.find('\\frac')
        if k < 0: break
        i = _ws(s, k+5); g1 = read_group(s, i)
        if not g1: s = s[:k] + s[k+5:]; continue
        a, i = g1; i = _ws(s, i); g2 = read_group(s, i)
        if not g2: s = s[:k] + s[k+5:]; continue
        b, i = g2
        s = s[:k] + '((' + conv(a) + ')/(' + conv(b) + '))' + s[i:]
    while True:
        k = s.find('\\sqrt[')
        if k < 0: break
        r = s.index(']', k); n = s[k+6:r]; i = _ws(s, r+1); g = read_group(s, i)
        if not g: s = s[:k] + s[k+5:]; continue
        a, i = g
        s = s[:k] + '((' + conv(a) + ')**(Rational(1,' + conv(n) + ')))' + s[i:]
    while True:
        k = s.find('\\sqrt')
        if k < 0: break
        i = _ws(s, k+5); g = read_group(s, i)
        if not g: s = s[:k] + s[k+5:]; continue
        a, i = g
        s = s[:k] + 'sqrt(' + conv(a) + ')' + s[i:]
    return s
def l2py(s):
    s = re.sub(r'\\[()\[\]]', '', s).replace('\\left', '').replace('\\right', '')
    s = s.replace('\\dfrac', '\\frac').replace('\\tfrac', '\\frac')
    s = re.sub(r'(\d)\s*(\\frac)', r'\1+\2', s)          # mixed number: 1\frac{1}{4} -> 1+1/4
    s = s.replace('\\cdot', '*').replace('\\times', '*').replace('\\div', '/').replace('\\pi', 'pi')
    s = s.replace('\\,', '').replace('\\!', '').replace('{,}', '.').strip()
    s = conv(s)
    s = re.sub(r'\^\s*\{([^{}]*)\}', r'**(\1)', s)
    s = re.sub(r'\^\s*(-?\d+|[a-zA-Z])', r'**(\1)', s)
    s = s.replace('{', '(').replace('}', ')')
    s = re.sub(r'\\[a-zA-Z]+', '', s)
    s = re.sub(r'(\d+\.\d+)', r"Rational('\1')", s)
    return s
def val(latex):
    return simplify(parse_expr(l2py(latex), transformations=TR, local_dict=LOC))
def _isnum(e):
    return bool(getattr(e, 'is_number', False))

_strip = lambda x: re.sub(r'<[^>]+>', '', x)
_grp = lambda x: re.findall(r'\\\((.+?)\\\)', x)
_COMPUTE = re.compile(r'beräkna|förenkla|förläng|förkorta|enklaste form|vad blir|värdet av|uträkna|skriv .*som', re.I)
_NOVALUE = re.compile(r'minsta gemensam|gemensam\w* nämnare|\bbasen\b|exponent|reciprok|\binvers|inverterade|omvända|\bav\b|procent|samma sak|vad kommer|\bförst\b|ordning|vilk\w* .* före|vad kallas|vad menas|hur (dividerar|multiplicerar|bildar|adderar)', re.I)
_APPROX = re.compile(r'överslag|avrunda|avrundn|ungefär', re.I)
_MGN = re.compile(r'minsta gemensam\w* (nämnare|multipel)|\bMGN\b|least common (denominator|multiple)|\bLC[MD]\b', re.I)
_OP = re.compile(r'\\cdot|\\div|\\times|[-+]|/|frac|sqrt|\^')
def _rhs(g):
    return g.split('=')[-1] if '=' in g else g
def _numer(groups):
    for g in groups:
        try:
            v = val(_rhs(g))
            if _isnum(v): return v
        except Exception: pass
    return None

def check(front, back):
    """Return 'ok' | 'MISMATCH' | 'skip'. Precision-first: only flags cards it can verify."""
    _sp = _special(front, back)
    if _sp is not None: return _sp
    ft = _strip(front); bnum = _numer(_grp(back))
    if _MGN.search(ft):
        if bnum is None: return 'skip'
        dens = []
        for g in _grp(front):
            m = re.search(r'\\d?frac\s*\{[^{}]*\}\s*\{([^{}]*)\}', g)
            if m:
                try: dens.append(int(val(m.group(1))))
                except Exception: pass
        if not dens:
            dens = [int(x) for x in re.findall(r'\b\d+\b', ft) if int(x) != int(bnum)]
        if len(dens) >= 2:
            try: return 'ok' if int(bnum) == int(ilcm(*dens)) else 'MISMATCH'
            except Exception: return 'skip'
        return 'skip'
    if _NOVALUE.search(ft) or not _COMPUTE.search(ft): return 'skip'
    fe = [g for g in _grp(front) if _OP.search(g)]
    fv = None
    for g in reversed(fe):
        try:
            v = val(_rhs(g))
            if _isnum(v): fv = v; break
        except Exception: pass
    if fv is None or bnum is None: return 'skip'
    return 'ok' if simplify(fv - bnum) == 0 else 'MISMATCH'

def check_identity(lhs_latex, rhs_latex):
    L = parse_expr(l2py(lhs_latex), transformations=TR, local_dict=LOC)
    R = parse_expr(l2py(rhs_latex), transformations=TR, local_dict=LOC)
    syms = sorted((L.free_symbols | R.free_symbols), key=str)
    pts = [Rational(3,2), Integer(2), Integer(3), Integer(5), Integer(7), Integer(11)]
    subs = {s: pts[i % len(pts)] for i, s in enumerate(syms)}
    diff = simplify((L - R).subs(subs))
    try: return abs(complex(diff)) < 1e-9
    except Exception: return diff == 0


_BER = re.compile(r'(?:^|::)(?:ber[aä]kning|calculation)$', re.I)
def is_calc_tag(tags):
    return any(_BER.search(t) for t in (tags or []))
def _is_mgn_tag(tags):
    return any('mgn' in t.lower() for t in (tags or []))
def value_check(front, back):
    """Value-equality check for a card KNOWN (by tag) to be a calculation."""
    _sp = _special(front, back)
    if _sp is not None: return _sp
    if any(('=' in g and re.search(r'[A-Za-z]', g)) for g in _grp(front)): return 'skip'
    _sc = _answer_selfcheck(front, back)   # trust arithmetic shown in the answer (EXPR = VALUE) over a stray front fraction
    if _sc is not None: return _sc
    bnum = _numer(_grp(back))
    if bnum is None: return 'skip'
    fe = [g for g in _grp(front) if _OP.search(g)]
    fv = None
    for g in reversed(fe):
        try:
            v = val(_rhs(g))
            if _isnum(v): fv = v; break
        except Exception: pass
    if fv is not None and bnum is not None:
        return 'ok' if simplify(fv - bnum) == 0 else 'MISMATCH'
    sc = _answer_selfcheck(front, back)
    return sc if sc is not None else 'skip'
def _mgn_check(front, back):
    ft = _strip(front); bnum = _numer(_grp(back))
    if bnum is None: return 'skip'
    dens = []
    for g in _grp(front):
        m = re.search(r'\\d?frac\s*\{[^{}]*\}\s*\{([^{}]*)\}', g)
        if m:
            try: dens.append(int(val(m.group(1))))
            except Exception: pass
    if not dens:
        dens = [int(x) for x in re.findall(r'\b\d+\b', ft) if int(x) != int(bnum)]
    if len(dens) >= 2:
        try: return 'ok' if int(bnum) == int(ilcm(*dens)) else 'MISMATCH'
        except Exception: return 'skip'
    return 'skip'

from decimal import Decimal, ROUND_HALF_UP
_AVR = re.compile(r'avrunda|avrundn|\bround(?:ed|ing)?\b', re.I)
_OVER = re.compile(r'överslag|estimat', re.I)
_WORD = {'en':1,'ett':1,'två':2,'tre':3,'fyra':4,'fem':5,'sex':6}
def _dec(g):
    g = re.sub(r'\\text\{[^{}]*\}', '', g)
    g = re.sub(r'(\d)\{,\}(\d)', r'\1.\2', g)
    g = re.sub(r'(\d)\s*,\s*(\d)', r'\1.\2', g)
    g = g.replace('\\,', '').replace(' ', '')
    g = re.sub(r'\\[a-zA-Z]+', '', g).replace('{', '').replace('}', '').rstrip('.')
    try: return Decimal(g)
    except Exception: return None
def _first_num(groups):
    for g in groups:
        v = _dec(_rhs(g))
        if v is not None: return v
    return None
def _precision(ft):
    f = ft.lower()
    if 'värdesiffr' in f or 'gällande siffr' in f:
        m = re.search(r'(\d+|en|ett|två|tre|fyra|fem|sex)\s+(?:värdesiffr|gällande)', f)
        if m:
            g = m.group(1); return ('sig', int(g) if g.isdigit() else _WORD.get(g))
        return (None, None)
    for k, v in {'heltal':0, 'tiondel':1, 'hundradel':2, 'tusendel':3, 'tiotal':-1, 'hundratal':-2, 'tusental':-3}.items():
        if 'närmaste ' + k in f: return ('dec', v)
    m = re.search(r'(\d+|en|ett|två|tre|fyra|fem|sex)\s+decimal', f)
    if m:
        g = m.group(1); return ('dec', int(g) if g.isdigit() else _WORD.get(g, 1))
    if 'heltal' in f: return ('dec', 0)
    return (None, None)
def _round_check(front, back, ft):
    kind, prec = _precision(ft)
    if kind is None or prec is None: return 'skip'
    x = _first_num(_grp(front)); a = _first_num(_grp(back))
    if x is None or a is None: return 'skip'
    try:
        if kind == 'dec':
            r = x.quantize(Decimal(1).scaleb(-prec), rounding=ROUND_HALF_UP)
        else:
            r = Decimal(0) if x == 0 else x.quantize(Decimal(1).scaleb(x.adjusted()-(prec-1)), rounding=ROUND_HALF_UP)
    except Exception: return 'skip'
    return 'ok' if r == a else 'MISMATCH'
def _estimate_check(front, back):
    fe = [g for g in _grp(front) if _OP.search(g)]
    ev = None
    for g in reversed(fe):
        try:
            v = val(_rhs(g))
            if _isnum(v): ev = float(v); break
        except Exception: pass
    a = _first_num(_grp(back))
    if ev is None or a is None or ev == 0: return 'skip'
    a = float(a); lo, hi = (0.5*ev, 2*ev) if ev > 0 else (2*ev, 0.5*ev)
    return 'ok' if lo <= a <= hi else 'MISMATCH'

def _eqn_check(front, back):
    ft = _strip(front)
    if not re.search(r'\bl\xf6s\b|l\xf6sning till|l\xf6s ekvationen|l\xf6s ut|\bsolve\b', ft, re.I): return None
    sol = None
    for g in _grp(back) + [_strip(back)]:
        m = re.search(r'([a-zA-Z])\s*=\s*([^,;]+)$', g.strip())
        if m: sol = (m.group(1), m.group(2)); break
    if sol is None: return 'skip'
    try:
        v = symbols(sol[0]); x = val(sol[1])
    except Exception: return 'skip'
    eqgroups = [g for g in _grp(front) if '=' in g]
    if not eqgroups: return None
    cand = None
    if len(eqgroups) == 1:
        cand = eqgroups[0]
    else:
        for g in eqgroups:                       # pick the equation whose only free symbol is the solution variable
            try:
                p = g.split('=')
                diff = parse_expr(l2py(p[0]), transformations=TR, local_dict=LOC) - parse_expr(l2py(p[-1]), transformations=TR, local_dict=LOC)
                if diff.free_symbols == {v}: cand = g; break
            except Exception: pass
    if cand is None: return None
    try:
        p = cand.split('=')
        L = parse_expr(l2py(p[0]), transformations=TR, local_dict=LOC)
        R = parse_expr(l2py(p[-1]), transformations=TR, local_dict=LOC)
        return 'ok' if simplify((L - R).subs(v, x)) == 0 else 'MISMATCH'
    except Exception: return 'skip'
def _eval_check(front, back):
    ft = _strip(front); groups = _grp(front)
    var = vals = None
    for g in groups:
        m = re.match(r'\s*([a-zA-Z])\s*=\s*(.+)$', g.strip())
        if m: var, vals = m.group(1), m.group(2)
    if var is None:
        m = re.search(r'(?:när|för|då|when|with|given|if)\s+([a-zA-Z])\s*=\s*(-?\d+(?:[.,]\d+)?)', ft)
        if m: var, vals = m.group(1), m.group(2)
    if var is None: return None
    exprg = None
    for g in groups:
        if '=' not in g and re.search(r'(?<![A-Za-z])' + re.escape(var) + r'(?![A-Za-z])', g): exprg = g
    if exprg is None: return None
    bnum = _numer(_grp(back))
    if bnum is None: return 'skip'
    try:
        e = parse_expr(l2py(exprg), transformations=TR, local_dict=LOC)
        res = simplify(e.subs(symbols(var), val(vals)))
    except Exception: return 'skip'
    if not _isnum(res): return 'skip'
    return 'ok' if simplify(res - bnum) == 0 else 'MISMATCH'
def _simplify_check(front, back):
    ft = _strip(front)
    if not re.search(r'förenkla|faktoriser|utveckla|multiplicera in|ta bort parentes|skriv.*utan parentes|bryt ut|simplify|factor|expand|distribute', ft, re.I): return None
    exprg = None
    for g in _grp(front):
        if '=' not in g and re.search(r'[a-zA-Z]', g): exprg = g
    if exprg is None: return None
    ansg = None
    for g in _grp(back):
        r = _rhs(g)
        if re.search(r'[a-zA-Z]', r): ansg = r; break
    if ansg is None: return None
    try:
        return 'ok' if check_identity(exprg, ansg) else 'MISMATCH'
    except Exception: return 'skip'


def _answer_selfcheck(front, back):
    """Verify the arithmetic in the answer: EXPR = VALUE, tolerating rounding to VALUE's decimals."""
    from decimal import Decimal, ROUND_HALF_UP
    cand=[g for g in _grp(back) if '=' in g]
    if not cand: return None
    g=cand[-1]
    if '\\approx' in g or '%' in g or '\\%' in g or '\\text' in g or '\\pm' in g: return None
    parts=[p for p in g.split('=') if p.strip()]
    if len(parts)<2: return None
    if re.search(r'\\sqrt|\\pi|[A-Za-z]', parts[-1]): return None
    try: lhs=val(parts[0])
    except Exception: return None
    if not _isnum(lhs): return None
    rd=_dec(parts[-1])
    if rd is None: return None
    nd = -rd.as_tuple().exponent if rd.as_tuple().exponent<0 else 0
    try: ld=Decimal(str(float(lhs))).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP)
    except Exception: return None
    return 'ok' if ld==rd else 'MISMATCH'

_FUNC = re.compile(r'\b[fghvpqT]\s*\(')   # function-application notation f(x), v(t): sympy misreads as multiplication
_TRIG = re.compile(r'(?:\\)?(?:arc)?(?:sin|cos|tan)\b', re.I)   # trig: sympy uses radians, matteboken degrees
def _special(front, back):
    ft = _strip(front)
    if _TRIG.search(front) or _TRIG.search(_strip(back)): return 'skip'
    if _FUNC.search(front) or _FUNC.search(_strip(back)): return 'skip'
    if _OVER.search(ft) or '\\approx' in back or '\\approx' in front: return _estimate_check(front, back)
    if _AVR.search(ft): return _round_check(front, back, ft)
    if _MGN.search(ft): return _mgn_check(front, back)
    for fn in (_eqn_check, _eval_check, _simplify_check):
        r = fn(front, back)
        if r is not None: return r
    return None

def verify_cards(cards):
    """If the deck has berakning-tagged cards, verify exactly those (tag-driven);
    otherwise fall back to the heuristic check()."""
    tagged = any(is_calc_tag(c.get('tags', [])) for c in cards)
    checked = ok = 0; mism = []
    for c in cards:
        front = c.get('front', c.get('Front', c.get('Text', '')))
        back = c.get('back', c.get('Back', c.get('Extra', '')))
        tags = c.get('tags', [])
        if tagged:
            if not is_calc_tag(tags): continue
            v = _mgn_check(front, back) if _is_mgn_tag(tags) else value_check(front, back)
        else:
            v = check(front, back)
        if v == 'skip': continue
        checked += 1
        if v == 'ok': ok += 1
        else: mism.append({'front': front, 'back': back})
    return checked, ok, mism

if __name__ == '__main__':
    import json, sys
    data = json.load(open(sys.argv[1]))
    cards = data['cards'] if isinstance(data, dict) else data
    checked, ok, mism = verify_cards(cards)
    print(f"{sys.argv[1].split('/')[-1]}: verifierbara={checked} korrekta={ok} avvikelser={len(mism)}")
    for m in mism:
        print("  [AVVIK]", _strip(m['front'])[:80], "->", _strip(m['back'])[:40])
    sys.exit(1 if mism else 0)
