#!/usr/bin/env python3
"""
pico2ps - transpileur d'un sous-ensemble de PICO-8 (Lua) vers PowerShell.

Usage :
    python pico2ps.py jeu.p8            -> jeu.ps1
    python pico2ps.py jeu.lua -o out.ps1
    python pico2ps.py jeu.p8 --loop     -> ajoute la boucle _init/_update/_draw
    python pico2ps.py jeu.p8 --stats    -> statistiques AST
    python pico2ps.py jeu.p8 --check    -> parse sans ecrire
    python pico2ps.py --list-modules    -> modules disponibles
    python pico2ps.py --api             -> fonctions systeme detaillees

Sous-ensemble supporte :
  * variables locales/globales, nombres (dec, 0x, 0b), chaines, true/false/nil
  * + - * / \\ % ^ .. == ~= != < <= > >= and or not # & | ^^ << >> ~
  * += -= *= /= \\= %= ^= ..= |= &=   et affectations multiples (a,b = b,a)
  * if/elseif/else/end, forme courte  if (cond) instruction
  * while, repeat/until, for i=a,b[,pas], for v in all(t), for k,v in pairs(t), break
  * function nom(params) ... end, local function, return (une seule valeur)
  * tables {1,2,3}, {x=1,y=2}, t[i] (indexe a partir de 1), t.x, #t
  * builtins : flr ceil abs sqrt min max mid sgn rnd srand sin cos atan2 sub tostr
             tonum chr ord split add del deli count all pairs foreach print printh
             cls time t flip
  * bibliotheque systeme :
      crypto_hash crypto_hmac crypto_rng crypto_uuid crypto_seal crypto_open
      mathx_clamp mathx_lerp mathx_smooth mathx_map mathx_dist mathx_noise
      fs_* fichiers   reg_* registre   net_* reseau   task_* planificateur
      disk_* disques  proc_* processus svc_* services  upd_* mises a jour
      sys_* systeme   serial_* / usb_* materiel   json_* / str_* utilitaires
    Les modules utilises sont injectes dans le .ps1 ; les fonctions destructrices
    respectent le commutateur  -DryRun  du script genere (simulation sans effet).
Limites connues : pas de closures/fonctions anonymes, pas de methodes (a:b()),
pas de goto, pas de retours multiples ; `a or b` renvoie un booleen (pas la valeur).
"""
import argparse
import os
import re
import shutil
import sys


# ----------------------------------------------------------------------------
# Palette Feng-Shui (activee si stdout est un terminal et pas de NO_COLOR)
# ----------------------------------------------------------------------------
class Palette:
    def __init__(self):
        self.on = (os.environ.get('NO_COLOR') is None
                   and hasattr(sys.stdout, 'isatty')
                   and sys.stdout.isatty())
        if self.on:
            self.reset = '\x1b[0m'
            self.dim = '\x1b[2m'
            self.bold = '\x1b[1m'
            self.jade = '\x1b[38;5;79m'
            self.zin = '\x1b[38;5;110m'
            self.sand = '\x1b[38;5;180m'
            self.rose = '\x1b[38;5;210m'
            self.ink = '\x1b[38;5;245m'
            self.warn = '\x1b[38;5;215m'
            self.err = '\x1b[38;5;203m'
            self.ok = '\x1b[38;5;114m'
        else:
            for a in ('reset', 'dim', 'bold', 'jade', 'zin', 'sand', 'rose',
                      'ink', 'warn', 'err', 'ok'):
                setattr(self, a, '')


PAL = Palette()


def banner():
    if not PAL.on:
        return
    print(f'{PAL.zin}   ╭─ {PAL.bold}pico2ps{PAL.reset}'
          f'{PAL.zin} ── souffle de code ─╮{PAL.reset}')
    print(f'{PAL.ink}   │  Lua → PowerShell · respiration & métabolisme  │{PAL.reset}')
    print(f'{PAL.zin}   ╰────────────────────────────────────────────────╯{PAL.reset}')
    print()


def phase(n, total, title):
    if not PAL.on:
        return
    bar_len = 24
    filled = int(bar_len * n / total)
    bar = f'{PAL.jade}{"▰" * filled}{PAL.ink}{"▱" * (bar_len - filled)}{PAL.reset}'
    print(f'  {bar}  {PAL.zin}{n}/{total}{PAL.reset}  {PAL.sand}{title}{PAL.reset}')


def whisper(msg):
    if PAL.on:
        print(f'  {PAL.ink}· {msg}{PAL.reset}')


def note(msg):
    if PAL.on:
        print(f'  {PAL.zin}✦ {msg}{PAL.reset}')
    else:
        print(msg)


def caution(msg):
    if PAL.on:
        print(f'  {PAL.warn}⚠ {msg}{PAL.reset}', file=sys.stderr)
    else:
        print(f'Avertissement: {msg}', file=sys.stderr)


def hush(msg):
    if PAL.on:
        print(f'  {PAL.err}✗ {msg}{PAL.reset}', file=sys.stderr)
    else:
        print(f'Erreur: {msg}', file=sys.stderr)


# ----------------------------------------------------------------------------
# Erreur de transpilation (avec contexte exploitable par l'affichage)
# ----------------------------------------------------------------------------
class TranspileError(Exception):
    def __init__(self, msg, line=None, col=None):
        super().__init__(msg)
        self.msg, self.line, self.col = msg, line, col

    def render(self, source_lines=None):
        if not PAL.on:
            loc = f' (ligne {self.line})' if self.line else ''
            return f'{self.msg}{loc}'
        out = [f'{PAL.err}✗ {self.msg}{PAL.reset}']
        if self.line:
            out.append(f'  {PAL.ink}ligne {self.line}{PAL.reset}')
        if source_lines and self.line and 1 <= self.line <= len(source_lines):
            txt = source_lines[self.line - 1]
            out.append(f'  {PAL.sand}{txt}{PAL.reset}')
            if self.col:
                out.append('  ' + ' ' * (self.col - 1) + f'{PAL.rose}^{PAL.reset}')
        return '\n'.join(out)


# ----------------------------------------------------------------------------
# Lexer
# ----------------------------------------------------------------------------
KEYWORDS = {'and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for',
            'function', 'goto', 'if', 'in', 'local', 'nil', 'not', 'or',
            'repeat', 'return', 'then', 'true', 'until', 'while'}
OPS3 = ['^^=', '..=']
OPS2 = ['^^', '<<', '>>', '<=', '>=', '==', '~=', '!=', '..', '+=', '-=',
        '*=', '/=', '%=', '\\=', '^=', '|=', '&=']
OPS1 = set('+-*/%\\^#<>=(){}[];,.:&|~?')
NUM_RE = re.compile(r'0[xX][0-9a-fA-F]+(?:\.[0-9a-fA-F]+)?|0[bB][01]+|'
                    r'(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?')
NAME_RE = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
ESCAPES = {'n': '\n', 't': '\t', 'r': '\r', 'a': '\a', 'b': '\b',
           'f': '\f', 'v': '\v', '\\': '\\', '"': '"', "'": "'", '0': '\0'}


class Tok:
    __slots__ = ('kind', 'val', 'line', 'col')

    def __init__(self, kind, val, line, col=1):
        self.kind, self.val, self.line, self.col = kind, val, line, col

    def __repr__(self):
        return f'Tok({self.kind},{self.val!r},{self.line})'


def lex(src):
    toks, i, n, line = [], 0, len(src), 1
    line_start = 0
    while i < n:
        c = src[i]
        if c == '\n':
            line += 1
            line_start = i + 1
            i += 1
            continue
        if c in ' \t\r':
            i += 1
            continue
        if src.startswith('--', i) or src.startswith('//', i):
            if src.startswith('--[[', i):
                j = src.find(']]', i + 4)
                j = n if j < 0 else j + 2
                line += src.count('\n', i, j)
                nl = src.rfind('\n', i, j)
                if nl >= 0:
                    line_start = nl + 1
                i = j
            else:
                j = src.find('\n', i)
                i = n if j < 0 else j
            continue
        if src.startswith('[[', i):
            j = src.find(']]', i + 2)
            if j < 0:
                raise TranspileError('chaine [[ non terminee', line, i - line_start + 1)
            toks.append(Tok('str', src[i + 2:j], line, i - line_start + 1))
            line += src.count('\n', i, j)
            i = j + 2
            continue
        col = i - line_start + 1
        if c.isdigit() or (c == '.' and i + 1 < n and src[i + 1].isdigit()):
            m = NUM_RE.match(src, i)
            txt = m.group(0)
            if txt[:2] in ('0x', '0X'):
                if '.' not in txt:
                    txt = str(int(txt[2:], 16))
                else:
                    ip, fp = txt[2:].split('.')
                    txt = repr(int(ip, 16) + int(fp, 16) / 16 ** len(fp))
            elif txt[:2] in ('0b', '0B'):
                txt = str(int(txt[2:], 2))
            elif txt.endswith('.'):
                txt += '0'
            toks.append(Tok('num', txt, line, col))
            i = m.end()
            continue
        if c in '"\'':
            q, j, buf = c, i + 1, []
            while True:
                if j >= n or src[j] == '\n':
                    raise TranspileError('chaine non terminee', line, col)
                ch = src[j]
                if ch == q:
                    break
                if ch == '\\' and j + 1 < n:
                    j += 1
                    e = src[j]
                    if e == 'x' and j + 2 < n:
                        buf.append(chr(int(src[j + 1:j + 3], 16)))
                        j += 2
                    elif e.isdigit() and e != '0':
                        m = re.match(r'\d{1,3}', src[j:])
                        buf.append(chr(int(m.group(0))))
                        j += len(m.group(0)) - 1
                    else:
                        buf.append(ESCAPES.get(e, e))
                else:
                    buf.append(ch)
                j += 1
            toks.append(Tok('str', ''.join(buf), line, col))
            i = j + 1
            continue
        if c.isalpha() or c == '_':
            m = NAME_RE.match(src, i)
            w = m.group(0)
            toks.append(Tok('kw' if w in KEYWORDS else 'name', w, line, col))
            i = m.end()
            continue
        for ops in (OPS3, OPS2):
            for o in ops:
                if src.startswith(o, i):
                    toks.append(Tok('op', o, line, col))
                    i += len(o)
                    break
            else:
                continue
            break
        else:
            if c in OPS1:
                toks.append(Tok('op', c, line, col))
                i += 1
            else:
                raise TranspileError(f'caractere inattendu {c!r}', line, col)
    toks.append(Tok('eof', '<eof>', line, 1))
    return toks


# ----------------------------------------------------------------------------
# Parser -> AST (tuples)
# ----------------------------------------------------------------------------
BIN = {'or': (1, 'l'), 'and': (2, 'l'),
       '<': (3, 'l'), '>': (3, 'l'), '<=': (3, 'l'), '>=': (3, 'l'),
       '~=': (3, 'l'), '!=': (3, 'l'), '==': (3, 'l'),
       '|': (4, 'l'), '^^': (5, 'l'), '&': (6, 'l'), '<<': (7, 'l'), '>>': (7, 'l'),
       '..': (8, 'r'), '+': (9, 'l'), '-': (9, 'l'),
       '*': (10, 'l'), '/': (10, 'l'), '\\': (10, 'l'), '%': (10, 'l'),
       '^': (12, 'r')}
UNARY_PREC = 11
COMPOUND = {'+=': '+', '-=': '-', '*=': '*', '/=': '/', '%=': '%', '\\=': '\\',
            '^=': '^', '..=': '..', '|=': '|', '&=': '&', '^^=': '^^'}
BLOCK_END = {'end', 'else', 'elseif', 'until'}


class Parser:
    def __init__(self, toks):
        self.t, self.p = toks, 0

    def peek(self, o=0):
        return self.t[min(self.p + o, len(self.t) - 1)]

    def next(self):
        tk = self.t[self.p]
        if tk.kind != 'eof':
            self.p += 1
        return tk

    def check(self, kind, val=None, o=0):
        tk = self.peek(o)
        return tk.kind == kind and (val is None or tk.val == val)

    def accept(self, kind, val=None):
        if self.check(kind, val):
            return self.next()
        return None

    def expect(self, kind, val=None):
        if self.check(kind, val):
            return self.next()
        tk = self.peek()
        want = val or kind
        raise TranspileError(f'{want!r} attendu, trouve {tk.val!r}',
                             tk.line, tk.col)

    def err(self, msg, tk=None):
        tk = tk or self.peek()
        raise TranspileError(msg, tk.line, tk.col)

    def parse_chunk(self):
        body = self.parse_block()
        if not self.check('eof'):
            self.err(f'{self.peek().val!r} inattendu')
        return body

    def parse_block(self):
        stmts = []
        while (not self.check('eof')
               and not (self.peek().kind == 'kw'
                        and self.peek().val in BLOCK_END)):
            s = self.parse_stmt()
            if s:
                stmts.append(s)
        return stmts

    def short_body(self, line):
        body = []
        while (not self.check('eof') and self.peek().line == line
               and not (self.peek().kind == 'kw'
                        and self.peek().val in BLOCK_END)):
            s = self.parse_stmt()
            if s:
                body.append(s)
        return body

    def parse_funcbody(self, name, local):
        self.expect('op', '(')
        params = []
        if not self.check('op', ')'):
            params.append(self.expect('name').val)
            while self.accept('op', ','):
                params.append(self.expect('name').val)
        self.expect('op', ')')
        body = self.parse_block()
        self.expect('kw', 'end')
        return ('func', name, params, body, local)

    def parse_stmt(self):
        tk = self.peek()
        if tk.kind == 'op':
            if tk.val == ';':
                self.next()
                return None
            if tk.val == '?':
                self.next()
                return ('callstat',
                        ('call', ('name', 'print'), [self.parse_expr()]))
        if tk.kind == 'kw':
            v = tk.val
            if v == 'local':
                self.next()
                if self.accept('kw', 'function'):
                    name = self.expect('name').val
                    return self.parse_funcbody(name, True)
                names = [self.expect('name').val]
                while self.accept('op', ','):
                    names.append(self.expect('name').val)
                exprs = []
                if self.accept('op', '='):
                    exprs.append(self.parse_expr())
                    while self.accept('op', ','):
                        exprs.append(self.parse_expr())
                return ('local', names, exprs)
            if v == 'function':
                self.next()
                name = self.expect('name').val
                if self.check('op', '.') or self.check('op', ':'):
                    self.err('fonctions de table/methodes non supportees')
                return self.parse_funcbody(name, False)
            if v == 'if':
                self.next()
                cond = self.parse_expr()
                if self.accept('kw', 'then'):
                    clauses = [(cond, self.parse_block())]
                    els = None
                    while True:
                        if self.accept('kw', 'elseif'):
                            c = self.parse_expr()
                            self.expect('kw', 'then')
                            clauses.append((c, self.parse_block()))
                        elif self.accept('kw', 'else'):
                            els = self.parse_block()
                            self.expect('kw', 'end')
                            break
                        else:
                            self.expect('kw', 'end')
                            break
                    return ('if', clauses, els)
                return ('if', [(cond, self.short_body(tk.line))], None)
            if v == 'while':
                self.next()
                cond = self.parse_expr()
                if self.accept('kw', 'do'):
                    body = self.parse_block()
                    self.expect('kw', 'end')
                else:
                    body = self.short_body(tk.line)
                return ('while', cond, body)
            if v == 'for':
                self.next()
                n1 = self.expect('name').val
                if self.accept('op', '='):
                    start = self.parse_expr()
                    self.expect('op', ',')
                    stop = self.parse_expr()
                    step = self.parse_expr() if self.accept('op', ',') else None
                    self.expect('kw', 'do')
                    body = self.parse_block()
                    self.expect('kw', 'end')
                    return ('for', n1, start, stop, step, body)
                names = [n1]
                while self.accept('op', ','):
                    names.append(self.expect('name').val)
                self.expect('kw', 'in')
                e = self.parse_expr()
                self.expect('kw', 'do')
                body = self.parse_block()
                self.expect('kw', 'end')
                return ('forin', names, e, body)
            if v == 'repeat':
                self.next()
                body = self.parse_block()
                self.expect('kw', 'until')
                return ('repeat', body, self.parse_expr())
            if v == 'return':
                self.next()
                nx = self.peek()
                if (nx.kind == 'eof' or nx.line != tk.line
                        or (nx.kind == 'kw' and nx.val in BLOCK_END)
                        or (nx.kind == 'op' and nx.val == ';')):
                    return ('return', None)
                e = self.parse_expr()
                if self.check('op', ','):
                    self.err('retours multiples non supportes')
                return ('return', e)
            if v == 'break':
                self.next()
                return ('break',)
            if v == 'do':
                self.next()
                body = self.parse_block()
                self.expect('kw', 'end')
                return ('do', body)
            if v == 'goto':
                self.err('goto non supporte')
        e = self.parse_suffixed()
        nx = self.peek()
        if nx.kind == 'op' and nx.val in ('=', ','):
            targets = [e]
            while self.accept('op', ','):
                targets.append(self.parse_suffixed())
            self.expect('op', '=')
            exprs = [self.parse_expr()]
            while self.accept('op', ','):
                exprs.append(self.parse_expr())
            for t in targets:
                if t[0] not in ('name', 'index'):
                    self.err("cible d'affectation invalide", tk)
            return ('assign', targets, exprs)
        if nx.kind == 'op' and nx.val in COMPOUND:
            self.next()
            if e[0] not in ('name', 'index'):
                self.err("cible d'affectation invalide", tk)
            rhs = self.parse_expr()
            return ('assign', [e], [('bin', COMPOUND[nx.val], e, rhs)])
        if e[0] == 'call':
            return ('callstat', e)
        self.err('instruction invalide', tk)

    def parse_expr(self, minp=0):
        left = self.parse_unary()
        while True:
            tk = self.peek()
            if tk.kind in ('op', 'kw') and tk.val in BIN:
                prec, assoc = BIN[tk.val]
                if prec < minp:
                    break
                self.next()
                rhs = self.parse_expr(prec if assoc == 'r' else prec + 1)
                left = ('bin', tk.val, left, rhs)
            else:
                break
        return left

    def parse_unary(self):
        tk = self.peek()
        if ((tk.kind == 'kw' and tk.val == 'not')
                or (tk.kind == 'op' and tk.val in ('-', '#', '~'))):
            self.next()
            return ('un', tk.val, self.parse_expr(UNARY_PREC))
        return self.parse_suffixed()

    def parse_suffixed(self):
        e = self.parse_primary()
        while True:
            tk = self.peek()
            if tk.kind == 'op' and tk.val == '.':
                self.next()
                e = ('index', e, ('str', self.expect('name').val))
            elif tk.kind == 'op' and tk.val == '[':
                self.next()
                k = self.parse_expr()
                self.expect('op', ']')
                e = ('index', e, k)
            elif tk.kind == 'op' and tk.val == '(':
                self.next()
                args = []
                if not self.check('op', ')'):
                    args.append(self.parse_expr())
                    while self.accept('op', ','):
                        args.append(self.parse_expr())
                self.expect('op', ')')
                e = ('call', e, args)
            elif tk.kind == 'op' and tk.val == ':':
                self.err('appels de methode (a:b()) non supportes')
            else:
                break
        return e

    def parse_primary(self):
        tk = self.next()
        if tk.kind == 'num':
            return ('num', tk.val)
        if tk.kind == 'str':
            return ('str', tk.val)
        if tk.kind == 'name':
            return ('name', tk.val)
        if tk.kind == 'kw':
            if tk.val == 'nil':
                return ('nil',)
            if tk.val in ('true', 'false'):
                return ('bool', tk.val == 'true')
            if tk.val == 'function':
                self.err('fonctions anonymes non supportees', tk)
        if tk.kind == 'op':
            if tk.val == '(':
                e = self.parse_expr()
                self.expect('op', ')')
                return e
            if tk.val == '{':
                arr, hs = [], []
                while not self.check('op', '}'):
                    if self.check('op', '['):
                        self.next()
                        k = self.parse_expr()
                        self.expect('op', ']')
                        self.expect('op', '=')
                        hs.append((k, self.parse_expr()))
                    elif self.check('name') and self.check('op', '=', 1):
                        k = self.next().val
                        self.next()
                        hs.append((('str', k), self.parse_expr()))
                    else:
                        arr.append(self.parse_expr())
                    if not (self.accept('op', ',') or self.accept('op', ';')):
                        break
                self.expect('op', '}')
                return ('table', arr, hs)
        self.err(f'expression attendue, trouve {tk.val!r}', tk)


# ----------------------------------------------------------------------------
# Runtime PowerShell (injecte en tete du script genere)
# ----------------------------------------------------------------------------
RUNTIME = r'''# --- Runtime pico2ps -------------------------------------------------------
$script:_t0 = [DateTime]::UtcNow
function _tostr($v) {
    if ($null -eq $v) { return 'nil' }
    if ($v -is [bool]) { if ($v) { return 'true' } else { return 'false' } }
    if ($v -is [hashtable] -and $v.ContainsKey('a') -and $v.ContainsKey('h')) { return _dump $v 0 }
    return [string]$v
}
function _dump($v, $d) {
    if ($v -is [hashtable] -and $v.ContainsKey('a') -and $v.ContainsKey('h')) {
        if ($d -ge 3) { return '{...}' }
        $p = @()
        foreach ($x in $v.a) { $p += (_dump $x ($d + 1)) }
        foreach ($k in $v.h.Keys) {
            $val = $v.h[$k]
            $p += ([string]$k + '=' + (_dump $val ($d + 1)))
        }
        return '{' + ($p -join ', ') + '}'
    }
    if ($v -is [string] -and $d -gt 0) { return '"' + $v + '"' }
    return _tostr $v
}
function _truthy($v) { return -not ($null -eq $v -or ($v -is [bool] -and -not $v)) }
function _key($k) {
    if ($k -is [ValueType] -and $k -isnot [bool] -and $k -isnot [char]) { return [double]$k }
    return $k
}
function _new { return @{ a = [System.Collections.ArrayList]::new(); h = @{} } }
function _set($t, $k, $v) {
    if ($null -eq $k) { return }
    $k = _key $k
    if ($k -is [double] -and $k -eq [math]::Floor($k)) {
        $i = [int]$k
        $n = $t.a.Count
        if ($i -ge 1 -and $i -le $n) { $t.a[$i - 1] = $v; return }
        if ($i -eq $n + 1 -and $null -ne $v) { [void]$t.a.Add($v); return }
    }
    if ($null -eq $v) { $t.h.Remove($k) } else { $t.h[$k] = $v }
}
function _get($t, $k) {
    if ($null -eq $t -or $null -eq $k) { return $null }
    $k = _key $k
    if ($k -is [double] -and $k -eq [math]::Floor($k)) {
        $i = [int]$k
        if ($i -ge 1 -and $i -le $t.a.Count) { return $t.a[$i - 1] }
    }
    return $t.h[$k]
}
function _tbl($a, $h) {
    $t = _new
    foreach ($v in $a) { [void]$t.a.Add($v) }
    for ($i = 0; $i -lt $h.Count; $i += 2) {
        _set $t $h[$i] $h[$i + 1]
    }
    return $t
}
function _len($v) {
    if ($null -eq $v) { return 0 }
    if ($v -is [string]) { return $v.Length }
    return $v.a.Count
}
function _count($t) { return $t.a.Count }
function _add($t, $v) { [void]$t.a.Add($v); return $v }
function _del($t, $v) {
    for ($i = 0; $i -lt $t.a.Count; $i++) {
        if ($t.a[$i] -eq $v) { $t.a.RemoveAt($i); return $v }
    }
}
function _deli($t, $i) {
    $i = [int]$i
    if ($i -ge 1 -and $i -le $t.a.Count) { $v = $t.a[$i - 1]; $t.a.RemoveAt($i - 1); return $v }
}
function _all($t) {
    if ($null -eq $t) { return , @() }
    return , $t.a.ToArray()
}
function _pairs($t) {
    $l = [System.Collections.ArrayList]::new()
    if ($null -eq $t) { return , $l }
    for ($i = 0; $i -lt $t.a.Count; $i++) { [void]$l.Add(@(($i + 1), $t.a[$i])) }
    foreach ($k in @($t.h.Keys)) { [void]$l.Add(@($k, $t.h[$k])) }
    return , $l
}
function _foreach($t, $f) { if ($null -ne $t) { foreach ($x in $t.a.ToArray()) { [void](& $f $x) } } }
function _mod($a, $b) { return $a - [math]::Floor($a / $b) * $b }
function _flr([double]$x) { return [math]::Floor($x) }
function _ceil([double]$x) { return [math]::Ceiling($x) }
function _abs([double]$x) { return [math]::Abs($x) }
function _sqrt([double]$x) { if ($x -lt 0) { return 0 } return [math]::Sqrt($x) }
function _min([double]$a, [double]$b) { return [math]::Min($a, $b) }
function _max([double]$a, [double]$b) { return [math]::Max($a, $b) }
function _mid([double]$a, [double]$b, [double]$c) {
    return (@($a, $b, $c) | Sort-Object)[1]
}
function _sgn([double]$x) { if ($x -lt 0) { return -1 } return 1 }
function _sin([double]$x) { return [math]::Sin(-$x * 2 * [math]::PI) }
function _cos([double]$x) { return [math]::Cos($x * 2 * [math]::PI) }
function _atan2([double]$dx, [double]$dy) {
    $r = [math]::Atan2(-$dy, $dx) / (2 * [math]::PI)
    if ($r -lt 0) { $r += 1 }
    return $r
}
function _rnd($x = 1) {
    if ($x -is [hashtable]) { return $x.a[(Get-Random -Maximum $x.a.Count)] }
    return (Get-Random -Minimum 0.0 -Maximum ([double]$x))
}
function _srand($x) { $null = Get-Random -SetSeed ([int]$x) }
function _time { return ([DateTime]::UtcNow - $script:_t0).TotalSeconds }
function _sub($s, $i = 1, $j = $null) {
    $s = _tostr $s
    $n = $s.Length
    if ($i -lt 0) { $i = $n + $i + 1 }
    if ($i -lt 1) { $i = 1 }
    if ($null -eq $j) { $j = $n } elseif ($j -lt 0) { $j = $n + $j + 1 }
    if ($j -gt $n) { $j = $n }
    if ($i -gt $j) { return '' }
    return $s.Substring([int]$i - 1, [int]$j - [int]$i + 1)
}
function _tonum($v) {
    $d = 0.0
    $ok = [double]::TryParse([string]$v, [Globalization.NumberStyles]::Float,
                             [Globalization.CultureInfo]::InvariantCulture, [ref]$d)
    if ($ok) { return $d }
    return $null
}
function _chr($n) { return [string][char][int]$n }
function _ord($s, $i = 1) { return [int]([string]$s)[[int]$i - 1] }
function _split($s, $sep = ',') {
    $t = _new
    foreach ($p in ([string]$s -split [regex]::Escape([string]$sep))) {
        $n = _tonum $p
        if ($null -ne $n) { [void]$t.a.Add($n) } else { [void]$t.a.Add($p) }
    }
    return $t
}
function _print { Write-Host (_tostr $args[0]) }
function _printh { Write-Host (_tostr $args[0]) }
function _cls { Clear-Host }
function _flip { Start-Sleep -Milliseconds 33 }
# --- Fin du runtime --------------------------------------------------------
'''

BUILTINS = {n: '_' + n for n in (
    'flr ceil abs sqrt min max mid sgn rnd srand sin cos atan2 sub tostr tonum '
    'chr ord split add del deli count all pairs foreach print printh cls time flip'
).split()}
BUILTINS['t'] = '_time'


# ----------------------------------------------------------------------------
# Bibliotheque systeme : modules PowerShell injectes a la demande
# Convention : fonction PowerShell  _<module>_<nom>  <->  appel PICO-8  <module>_<nom>
# Les helpers internes n'ont qu'un seul underscore (_abs, _rec, _list...).
# ----------------------------------------------------------------------------
SYS_MODULES = {}

SYS_MODULES['core'] = r'''
# --- Bibliotheque systeme : outils internes ---------------------------------
$script:_win = ($PSVersionTable.PSEdition -eq 'Desktop') -or ($IsWindows -eq $true)
$script:_dry = [bool]$DryRun
function _warn($m) { Write-Warning ([string]$m) }
function _dry($m) {
    if ($script:_dry) { Write-Host ('[dry-run] ' + [string]$m) -ForegroundColor Yellow; return $true }
    return $false
}
function _needwin($f) {
    if ($script:_win) { return $true }
    Write-Warning ($f + ' : disponible sous Windows uniquement')
    return $false
}
function _abs($p) { return $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath([string]$p) }
function _rec($h) {
    $t = _new
    foreach ($k in $h.Keys) {
        $v = $h[$k]
        _set $t ([string]$k) $v
    }
    return $t
}
function _list($items) {
    $t = _new
    foreach ($i in @($items)) { if ($null -ne $i) { [void]$t.a.Add($i) } }
    return $t
}
'''

# --- NOUVEAU : crypto (integrite, alea, coffre-fort AES-GCM) ---
SYS_MODULES['crypto'] = r'''
# --- crypto : integrite, alea cryptographique, coffre-fort -----------------
function _crypto_hash($s, $algo = 'SHA256') {
    try {
        $h = [Security.Cryptography.HashAlgorithm]::Create([string]$algo)
        return (($h.ComputeHash([Text.Encoding]::UTF8.GetBytes([string]$s)) |
                 ForEach-Object { $_.ToString('x2') }) -join '')
    } catch { _warn $_; return $null }
}
function _crypto_hmac($s, $key, $algo = 'SHA256') {
    try {
        $h = [Security.Cryptography.HMAC]::Create([string]$algo)
        $h.Key = [Text.Encoding]::UTF8.GetBytes([string]$key)
        return (($h.ComputeHash([Text.Encoding]::UTF8.GetBytes([string]$s)) |
                 ForEach-Object { $_.ToString('x2') }) -join '')
    } catch { _warn $_; return $null }
}
function _crypto_rng($a = 0, $b = 1) {
    if (_dry 'crypto_rng') { return [int64]$a }
    $bytes = New-Object byte[] 8
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $n = [BitConverter]::ToUInt64($bytes, 0)
    $lo = [int64]$a; $hi = [int64]$b
    if ($hi -lt $lo) { $tmp = $lo; $lo = $hi; $hi = $tmp }
    return [int64]($lo + ($n % ([uint64]($hi - $lo + 1))))
}
function _crypto_uuid() {
    if (_dry 'crypto_uuid') { return '00000000-0000-0000-0000-000000000000' }
    return [guid]::NewGuid().ToString()
}
function _crypto_seal($plaintext, $keyString) {
    if (_dry 'crypto_seal') { return 'DRYRUN_SEALED' }
    try {
        $keyBytes = [Text.Encoding]::UTF8.GetBytes(([string]$keyString).PadRight(32, '0').Substring(0, 32))
        $aes = [Security.Cryptography.AesGcm]::new($keyBytes)
        $nonce = New-Object byte[] 12
        [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($nonce)
        $pt = [Text.Encoding]::UTF8.GetBytes([string]$plaintext)
        $ct = New-Object byte[] $pt.Length
        $tag = New-Object byte[] 16
        $aes.Encrypt($nonce, $pt, $ct, $tag)
        return [Convert]::ToBase64String($nonce + $tag + $ct)
    } catch { _warn $_; return $null }
}
function _crypto_open($b64, $keyString) {
    if (_dry 'crypto_open') { return 'DRYRUN_OPENED' }
    try {
        $keyBytes = [Text.Encoding]::UTF8.GetBytes(([string]$keyString).PadRight(32, '0').Substring(0, 32))
        $aes = [Security.Cryptography.AesGcm]::new($keyBytes)
        $raw = [Convert]::FromBase64String([string]$b64)
        $nonce = $raw[0..11]; $tag = $raw[12..27]; $ct = $raw[28..($raw.Length - 1)]
        $pt = New-Object byte[] $ct.Length
        $aes.Decrypt($nonce, $ct, $tag, $pt)
        return [Text.Encoding]::UTF8.GetString($pt)
    } catch { _warn $_; return $null }
}
'''

# --- NOUVEAU : mathx (geometrie douce, interpolation, bruit organique) ---
SYS_MODULES['mathx'] = r'''
# --- mathx : geometrie douce, interpolation, bruit organique ---------------
function _mathx_clamp($v, $lo, $hi) {
    if ($v -lt $lo) { return $lo }
    if ($v -gt $hi) { return $hi }
    return $v
}
function _mathx_lerp($a, $b, $t) { return ($a + ($b - $a) * $t) }
function _mathx_smooth($t) { return ($t * $t * (3 - 2 * $t)) }
function _mathx_map($v, $i0, $i1, $o0, $o1) {
    if ($i1 -eq $i0) { return $o0 }
    return ($o0 + ($o1 - $o0) * (($v - $i0) / ($i1 - $i0)))
}
function _mathx_dist($x1, $y1, $x2, $y2) {
    $dx = $x2 - $x1; $dy = $y2 - $y1
    return [math]::Sqrt($dx * $dx + $dy * $dy)
}
function _mathx_noise($x, $seed = 0) {
    $xi = [math]::Floor($x)
    $xf = _mathx_smooth ($x - $xi)
    $h = {
        param($n)
        $n = ([int64]$n * 374761393 + [int64]$seed) -band 0xFFFFFFFF
        $n = (($n -bxor ($n -shr 13)) * 1274126177) -band 0xFFFFFFFF
        return (($n % 2001) / 1000.0) - 1.0
    }
    $n1 = & $h $xi
    $n2 = & $h ($xi + 1)
    return (_mathx_lerp $n1 $n2 $xf)
}
'''

SYS_MODULES['fs'] = r'''
# --- fs : systeme de fichiers -------------------------------------------------
function _fsguard($p) {
    try {
        $full = (_abs $p).TrimEnd('\', '/')
        $h = ([string]$HOME).TrimEnd('\', '/')
        $w = [Environment]::GetFolderPath('Windows')
        if ($full.Length -le 2) { return $false }
        if ($full -ieq $h) { return $false }
        if ($w -and ($full -ieq $w.TrimEnd('\', '/'))) { return $false }
        return $true
    } catch { return $false }
}
function _fs_ls($p = '.', $pat = '*') {
    try { return _list (Get-ChildItem -LiteralPath ([string]$p) -Filter ([string]$pat) -Force -ErrorAction Stop | ForEach-Object { $_.FullName }) } catch { _warn $_; return $null }
}
function _fs_find($p = '.', $pat = '*') {
    try { return _list (Get-ChildItem -LiteralPath ([string]$p) -Filter ([string]$pat) -Recurse -Force -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }) } catch { _warn $_; return $null }
}
function _fs_exists($p) { return (Test-Path -LiteralPath ([string]$p)) }
function _fs_isdir($p) { return (Test-Path -LiteralPath ([string]$p) -PathType Container) }
function _fs_mkdir($p) {
    try { [void](New-Item -ItemType Directory -Force -Path ([string]$p) -ErrorAction Stop); return $true } catch { _warn $_; return $false }
}
function _fs_rm($p) {
    try {
        if (-not (_fsguard $p)) { _warn ('fs_rm : chemin refuse : ' + $p); return $false }
        if (_dry ('rm -r ' + $p)) { return $true }
        Remove-Item -LiteralPath ([string]$p) -Recurse -Force -ErrorAction Stop
        return $true
    } catch { _warn $_; return $false }
}
function _fs_cp($a, $b) {
    try {
        if (_dry ('cp ' + $a + ' -> ' + $b)) { return $true }
        Copy-Item -LiteralPath ([string]$a) -Destination ([string]$b) -Recurse -Force -ErrorAction Stop
        return $true
    } catch { _warn $_; return $false }
}
function _fs_mv($a, $b) {
    try {
        if (_dry ('mv ' + $a + ' -> ' + $b)) { return $true }
        Move-Item -LiteralPath ([string]$a) -Destination ([string]$b) -Force -ErrorAction Stop
        return $true
    } catch { _warn $_; return $false }
}
function _fs_cat($p) {
    try { return (Get-Content -LiteralPath ([string]$p) -Raw -ErrorAction Stop) } catch { _warn $_; return $null }
}
function _fs_lines($p) {
    try { return _list (Get-Content -LiteralPath ([string]$p) -ErrorAction Stop) } catch { _warn $_; return $null }
}
function _fs_write($p, $s) {
    try {
        if (_dry ('write ' + $p)) { return $true }
        [IO.File]::WriteAllText((_abs $p), (_tostr $s))
        return $true
    } catch { _warn $_; return $false }
}
function _fs_append($p, $s) {
    try {
        if (_dry ('append ' + $p)) { return $true }
        [IO.File]::AppendAllText((_abs $p), (_tostr $s))
        return $true
    } catch { _warn $_; return $false }
}
function _fs_size($p) {
    try {
        $i = Get-Item -LiteralPath ([string]$p) -Force -ErrorAction Stop
        if ($i.PSIsContainer) {
            $s = (Get-ChildItem -LiteralPath $i.FullName -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
            if ($null -eq $s) { return 0 }
            return [double]$s
        }
        return [double]$i.Length
    } catch { _warn $_; return $null }
}
function _fs_mtime($p) {
    try { return ([DateTimeOffset](Get-Item -LiteralPath ([string]$p) -Force -ErrorAction Stop).LastWriteTimeUtc).ToUnixTimeSeconds() } catch { _warn $_; return $null }
}
function _fs_hash($p, $algo = 'SHA256') {
    try { return (Get-FileHash -LiteralPath ([string]$p) -Algorithm ([string]$algo) -ErrorAction Stop).Hash.ToLowerInvariant() } catch { _warn $_; return $null }
}
function _fs_cwd() { return (Get-Location).Path }
function _fs_cd($p) {
    try { Set-Location -LiteralPath ([string]$p) -ErrorAction Stop; return $true } catch { _warn $_; return $false }
}
function _fs_tmp() { return [IO.Path]::GetTempFileName() }
function _fs_home() { return [string]$HOME }
function _fs_link($link, $target) {
    try {
        if (_dry ('symlink ' + $link + ' -> ' + $target)) { return $true }
        [void](New-Item -ItemType SymbolicLink -Path ([string]$link) -Target ([string]$target) -ErrorAction Stop)
        return $true
    } catch { _warn $_; return $false }
}
function _fs_streams($p) {
    if (-not (_needwin 'fs_streams')) { return $null }
    try {
        $out = @()
        foreach ($s in Get-Item -LiteralPath ([string]$p) -Stream * -ErrorAction Stop) {
            $out += _rec @{ name = $s.Stream; size = [double]$s.Length }
        }
        return _list $out
    } catch { _warn $_; return $null }
}
function _fs_watch($p, $ms = 10000) {
    $w = $null
    try {
        $w = New-Object IO.FileSystemWatcher (_abs $p)
        $w.Filter = '*'
        $w.IncludeSubdirectories = $true
        $r = $w.WaitForChanged([IO.WatcherChangeTypes]::All, [int]$ms)
        return _rec @{ name = $r.Name; type = [string]$r.ChangeType; timeout = [bool]$r.TimedOut }
    } catch { _warn $_; return $null } finally { if ($null -ne $w) { $w.Dispose() } }
}
'''

SYS_MODULES['reg'] = r'''
# --- reg : registre Windows ---------------------------------------------------
function _regpath($p) {
    $p = ([string]$p).Replace('/', '\').TrimEnd('\')
    $map = @{ HKLM = 'HKEY_LOCAL_MACHINE'; HKCU = 'HKEY_CURRENT_USER'; HKCR = 'HKEY_CLASSES_ROOT'; HKU = 'HKEY_USERS'; HKCC = 'HKEY_CURRENT_CONFIG' }
    if ($p -match '^(HK[A-Z_]+):?(\\(.*))?$') {
        $root = $Matches[1]
        $rest = $Matches[3]
        if ($map.ContainsKey($root)) { $root = $map[$root] }
        if ($rest) { return ('Registry::' + $root + '\' + $rest) }
        return ('Registry::' + $root)
    }
    return $p
}
function _reg_exists($p) {
    if (-not (_needwin 'reg_exists')) { return $false }
    return (Test-Path -LiteralPath (_regpath $p))
}
function _reg_get($p, $n = '(default)') {
    if (-not (_needwin 'reg_get')) { return $null }
    try {
        $nn = [string]$n
        $o = Get-ItemProperty -LiteralPath (_regpath $p) -Name $nn -ErrorAction Stop
        return $o.$nn
    } catch { return $null }
}
function _reg_set($p, $n, $v, $type = $null) {
    if (-not (_needwin 'reg_set')) { return $false }
    try {
        $rp = _regpath $p
        if ($null -eq $type) {
            if ($v -is [double] -or $v -is [int] -or $v -is [long]) { $type = 'DWord' } else { $type = 'String' }
        }
        if (_dry ('reg_set ' + $rp + ' ' + $n + ' = ' + (_tostr $v) + ' (' + $type + ')')) { return $true }
        if ($type -eq 'DWord') {
            $u = [uint32]([long]$v -band 0xFFFFFFFFL)
            $v = [BitConverter]::ToInt32([BitConverter]::GetBytes($u), 0)
        } elseif ($type -eq 'QWord') {
            $v = [long]$v
        }
        if (-not (Test-Path -LiteralPath $rp)) { [void](New-Item -Path $rp -Force) }
        Set-ItemProperty -LiteralPath $rp -Name ([string]$n) -Value $v -Type $type -ErrorAction Stop
        return $true
    } catch { _warn $_; return $false }
}
function _reg_del($p, $n = $null) {
    if (-not (_needwin 'reg_del')) { return $false }
    try {
        $rp = _regpath $p
        if ($rp -match '^Registry::HKEY_[A-Z_]+(\\[^\\]+)?$') { _warn ('reg_del : cle trop haute refusee : ' + $rp); return $false }
        if (_dry ('reg_del ' + $rp + ' ' + $n)) { return $true }
        if ($null -eq $n) { Remove-Item -LiteralPath $rp -Recurse -Force -ErrorAction Stop }
        else { Remove-ItemProperty -LiteralPath $rp -Name ([string]$n) -ErrorAction Stop }
        return $true
    } catch { _warn $_; return $false }
}
function _reg_keys($p) {
    if (-not (_needwin 'reg_keys')) { return $null }
    try { return _list (Get-ChildItem -LiteralPath (_regpath $p) -ErrorAction Stop | ForEach-Object { $_.PSChildName }) } catch { _warn $_; return $null }
}
function _reg_values($p) {
    if (-not (_needwin 'reg_values')) { return $null }
    try {
        $k = Get-Item -LiteralPath (_regpath $p) -ErrorAction Stop
        $t = _new
        foreach ($n in $k.GetValueNames()) {
            $v = $k.GetValue($n)
            $nn = $n
            if ($nn -eq '') { $nn = '(default)' }
            _set $t $nn $v
        }
        return $t
    } catch { _warn $_; return $null }
}
function _reg_export($p, $file) {
    if (-not (_needwin 'reg_export')) { return $false }
    try {
        if (_dry ('reg export ' + $p + ' -> ' + $file)) { return $true }
        $src = ([string]$p) -replace '^(HK[A-Za-z_]+):', '$1'
        & reg.exe export $src (_abs $file) /y | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch { _warn $_; return $false }
}
'''

SYS_MODULES['net'] = r'''
# --- net : reseau -------------------------------------------------------------
function _net_ping($h, $ms = 1000) {
    $p = $null
    try {
        $p = New-Object Net.NetworkInformation.Ping
        $r = $p.Send([string]$h, [int]$ms)
        if ($r.Status -eq 'Success') { return [double]$r.RoundtripTime }
        return $null
    } catch { return $null } finally { if ($null -ne $p) { $p.Dispose() } }
}
function _net_port($h, $port, $ms = 1000) {
    $c = New-Object Net.Sockets.TcpClient
    try {
        $iar = $c.BeginConnect([string]$h, [int]$port, $null, $null)
        if ($iar.AsyncWaitHandle.WaitOne([int]$ms, $false) -and $c.Connected) { $c.EndConnect($iar); return $true }
        return $false
    } catch { return $false } finally { $c.Close() }
}
function _net_scan($h, $a, $b, $ms = 200) {
    $out = @()
    for ($p = [int]$a; $p -le [int]$b; $p++) {
        if (_net_port $h $p $ms) { $out += $p }
    }
    return _list $out
}
function _net_get($u, $timeout = 30) {
    $ProgressPreference = 'SilentlyContinue'
    try {
        $r = Invoke-WebRequest -Uri ([string]$u) -UseBasicParsing -TimeoutSec ([int]$timeout) -ErrorAction Stop
        return [string]$r.Content
    } catch { _warn $_; return $null }
}
function _net_post($u, $body, $ctype = 'application/json') {
    $ProgressPreference = 'SilentlyContinue'
    try {
        $r = Invoke-WebRequest -Uri ([string]$u) -Method Post -Body ([string]$body) -ContentType ([string]$ctype) -UseBasicParsing -ErrorAction Stop
        return [string]$r.Content
    } catch { _warn $_; return $null }
}
function _net_download($u, $path) {
    $ProgressPreference = 'SilentlyContinue'
    try {
        if (_dry ('download ' + $u + ' -> ' + $path)) { return $true }
        Invoke-WebRequest -Uri ([string]$u) -OutFile (_abs $path) -UseBasicParsing -ErrorAction Stop
        return $true
    } catch { _warn $_; return $false }
}
function _net_dns($name) {
    try { return _list ([Net.Dns]::GetHostAddresses([string]$name) | ForEach-Object { $_.IPAddressToString }) } catch { _warn $_; return $null }
}
function _net_rdns($ip) {
    try { return [Net.Dns]::GetHostEntry([string]$ip).HostName } catch { return $null }
}
function _net_adapters() {
    try {
        $out = @()
        foreach ($n in [Net.NetworkInformation.NetworkInterface]::GetAllNetworkInterfaces()) {
            $ip = ($n.GetIPProperties().UnicastAddresses | Where-Object { $_.Address.AddressFamily -eq 'InterNetwork' } | ForEach-Object { $_.Address.IPAddressToString }) -join ','
            $out += _rec @{ name = $n.Name; ip = $ip; mac = [string]$n.GetPhysicalAddress(); status = [string]$n.OperationalStatus; speed = [double]$n.Speed }
        }
        return _list $out
    } catch { _warn $_; return $null }
}
function _net_conns() {
    try {
        $out = @()
        if ($script:_win) {
            foreach ($c in Get-NetTCPConnection -ErrorAction Stop) {
                $out += _rec @{ local = [string]$c.LocalAddress; lport = $c.LocalPort; remote = [string]$c.RemoteAddress; rport = $c.RemotePort; state = [string]$c.State; pid = $c.OwningProcess }
            }
        } else {
            foreach ($c in [Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpConnections()) {
                $out += _rec @{ local = $c.LocalEndPoint.Address.ToString(); lport = $c.LocalEndPoint.Port; remote = $c.RemoteEndPoint.Address.ToString(); rport = $c.RemoteEndPoint.Port; state = [string]$c.State }
            }
        }
        return _list $out
    } catch { _warn $_; return $null }
}
function _net_wifi() {
    if (-not (_needwin 'net_wifi')) { return $null }
    try {
        $out = @()
        $cur = $null
        foreach ($l in (& netsh.exe wlan show networks mode=bssid)) {
            if ($l -match '^\s*SSID\s+\d+\s*:\s*(.*)$') {
                if ($null -ne $cur) { $out += $cur }
                $cur = _rec @{ ssid = $Matches[1].Trim() }
            } elseif ($null -ne $cur -and $l -match '^\s*Signal\s*:\s*(\d+)\s*%') {
                $sig = [int]$Matches[1]
                if ($null -eq (_get $cur 'signal')) { _set $cur 'signal' $sig }
            }
        }
        if ($null -ne $cur) { $out += $cur }
        return _list $out
    } catch { _warn $_; return $null }
}
function _net_wol($mac, $bcast = '255.255.255.255') {
    $u = $null
    try {
        $hex = ([string]$mac) -replace '[^0-9A-Fa-f]', ''
        if ($hex.Length -ne 12) { _warn 'net_wol : MAC invalide'; return $false }
        if (_dry ('wake-on-lan ' + $mac)) { return $true }
        $bytes = [byte[]](0..5 | ForEach-Object { [Convert]::ToByte($hex.Substring($_ * 2, 2), 16) })
        $pkt = [byte[]]((,0xFF * 6) + ($bytes * 16))
        $u = New-Object Net.Sockets.UdpClient
        $u.EnableBroadcast = $true
        [void]$u.Send($pkt, $pkt.Length, [string]$bcast, 9)
        return $true
    } catch { _warn $_; return $false } finally { if ($null -ne $u) { $u.Close() } }
}
'''

SYS_MODULES['task'] = r'''
# --- task : planificateur de taches Windows -----------------------------------
function _taskwhen($w) {
    $w = ([string]$w).Trim()
    if ($w -ieq 'boot') { return (New-ScheduledTaskTrigger -AtStartup) }
    if ($w -ieq 'logon') { return (New-ScheduledTaskTrigger -AtLogOn) }
    if ($w -match '^daily@(\d{1,2}:\d{2})$') { return (New-ScheduledTaskTrigger -Daily -At $Matches[1]) }
    if ($w -match '^weekly@([A-Za-z,]+)@(\d{1,2}:\d{2})$') {
        $days = $Matches[1] -split ','
        return (New-ScheduledTaskTrigger -Weekly -DaysOfWeek $days -At $Matches[2])
    }
    if ($w -match '^every@(\d+)$') {
        $mins = [int]$Matches[1]
        return (New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes $mins) -RepetitionDuration (New-TimeSpan -Days 3650))
    }
    throw ('declencheur inconnu : ' + $w + ' (boot | logon | daily@HH:MM | weekly@Mon,Fri@HH:MM | every@minutes)')
}
function _task_list($filter = '*') {
    if (-not (_needwin 'task_list')) { return $null }
    try {
        $out = @()
        foreach ($t in (Get-ScheduledTask -ErrorAction Stop | Where-Object { $_.TaskName -like ([string]$filter) })) {
            $out += _rec @{ name = $t.TaskName; path = $t.TaskPath; state = [string]$t.State }
        }
        return _list $out
    } catch { _warn $_; return $null }
}
function _task_info($name) {
    if (-not (_needwin 'task_info')) { return $null }
    try {
        $i = Get-ScheduledTaskInfo -TaskName ([string]$name) -ErrorAction Stop
        return _rec @{ last = $i.LastRunTime.ToString('s'); next = $i.NextRunTime.ToString('s'); result = $i.LastTaskResult; missed = $i.NumberOfMissedRuns }
    } catch { _warn $_; return $null }
}
function _task_add($name, $exe, $when, $argstr = '', $highest = $false) {
    if (-not (_needwin 'task_add')) { return $false }
    try {
        $trig = _taskwhen $when
        if (_dry ('task_add ' + $name + ' : ' + $exe + ' ' + $argstr + ' @ ' + $when)) { return $true }
        if ($argstr) { $act = New-ScheduledTaskAction -Execute ([string]$exe) -Argument ([string]$argstr) }
        else { $act = New-ScheduledTaskAction -Execute ([string]$exe) }
        $params = @{ TaskName = [string]$name; Action = $act; Trigger = $trig; Force = $true }
        if ($highest) { $params.RunLevel = 'Highest' }
        [void](Register-ScheduledTask @params -ErrorAction Stop)
        return $true
    } catch { _warn $_; return $false }
}
function _task_addps($name, $script, $when, $highest = $false) {
    $a = '-NoProfile -ExecutionPolicy Bypass -File "' + (_abs $script) + '"'
    return (_task_add $name 'powershell.exe' $when $a $highest)
}
function _task_del($name) {
    if (-not (_needwin 'task_del')) { return $false }
    try {
        if (_dry ('task_del ' + $name)) { return $true }
        Unregister-ScheduledTask -TaskName ([string]$name) -Confirm:$false -ErrorAction Stop
        return $true
    } catch { _warn $_; return $false }
}
function _task_run($name) {
    if (-not (_needwin 'task_run')) { return $false }
    try {
        if (_dry ('task_run ' + $name)) { return $true }
        Start-ScheduledTask -TaskName ([string]$name) -ErrorAction Stop
        return $true
    } catch { _warn $_; return $false }
}
function _task_enable($name, $on = $true) {
    if (-not (_needwin 'task_enable')) { return $false }
    try {
        if (_dry ('task_enable ' + $name + ' ' + $on)) { return $true }
        if ($on) { [void](Enable-ScheduledTask -TaskName ([string]$name) -ErrorAction Stop) }
        else { [void](Disable-ScheduledTask -TaskName ([string]$name) -ErrorAction Stop) }
        return $true
    } catch { _warn $_; return $false }
}
'''

SYS_MODULES['disk'] = r'''
# --- disk : volumes et disques --------------------------------------------------
function _disk_list() {
    try {
        $out = @()
        foreach ($d in [IO.DriveInfo]::GetDrives()) {
            $r = _rec @{ name = $d.Name; type = [string]$d.DriveType; ready = [bool]$d.IsReady }
            if ($d.IsReady) {
                _set $r 'label' $d.VolumeLabel
                _set $r 'fs' $d.DriveFormat
                _set $r 'total' ([double]$d.TotalSize)
                _set $r 'free' ([double]$d.AvailableFreeSpace)
            }
            $out += $r
        }
        return _list $out
    } catch { _warn $_; return $null }
}
function _disk_free($p = '.') {
    try {
        $root = [IO.Path]::GetPathRoot((_abs $p))
        return [double](New-Object IO.DriveInfo $root).AvailableFreeSpace
    } catch { _warn $_; return $null }
}
function _disk_top($p = '.', $n = 10) {
    try {
        $out = @()
        foreach ($i in Get-ChildItem -LiteralPath ([string]$p) -Force -ErrorAction Stop) {
            if ($i.PSIsContainer) {
                $s = (Get-ChildItem -LiteralPath $i.FullName -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
            } else { $s = $i.Length }
            if ($null -eq $s) { $s = 0 }
            $out += _rec @{ name = $i.Name; size = [double]$s; dir = [bool]$i.PSIsContainer }
        }
        return _list ($out | Sort-Object { $_.h['size'] } -Descending | Select-Object -First ([int]$n))
    } catch { _warn $_; return $null }
}
function _disk_phys() {
    if (-not (_needwin 'disk_phys')) { return $null }
    try {
        $out = @()
        foreach ($d in Get-PhysicalDisk -ErrorAction Stop) {
            $r = $null
            try { $r = $d | Get-StorageReliabilityCounter -ErrorAction Stop } catch { }
            $out += _rec @{ name = $d.FriendlyName; media = [string]$d.MediaType; bus = [string]$d.BusType; size = [double]$d.Size; health = [string]$d.HealthStatus; temp = $r.Temperature; wear = $r.Wear; hours = $r.PowerOnHours }
        }
        return _list $out
    } catch { _warn $_; return $null }
}
function _disk_scan($letter) {
    if (-not (_needwin 'disk_scan')) { return $null }
    try { return [string](Repair-Volume -DriveLetter (([string]$letter).Substring(0, 1)) -Scan -ErrorAction Stop) } catch { _warn $_; return $null }
}
function _disk_optimize($letter, $mode = 'trim') {
    if (-not (_needwin 'disk_optimize')) { return $false }
    try {
        $l = ([string]$letter).Substring(0, 1)
        if (_dry ('disk_optimize ' + $l + ' ' + $mode)) { return $true }
        if ($mode -eq 'defrag') { Optimize-Volume -DriveLetter $l -Defrag -ErrorAction Stop }
        else { Optimize-Volume -DriveLetter $l -ReTrim -ErrorAction Stop }
        return $true
    } catch { _warn $_; return $false }
}
'''

SYS_MODULES['proc'] = r'''
# --- proc : processus -------------------------------------------------------------
function _proc_list() {
    try {
        $out = @()
        foreach ($p in Get-Process) {
            try { $pp = $p.Path } catch { $pp = $null }
            $out += _rec @{ pid = $p.Id; name = $p.ProcessName; mem = [math]::Round($p.WorkingSet64 / 1MB, 1); cpu = $p.CPU; path = $pp }
        }
        return _list $out
    } catch { _warn $_; return $null }
}
function _proc_exists($name) { return ($null -ne (Get-Process -Name ([string]$name) -ErrorAction SilentlyContinue)) }
function _proc_kill($t) {
    try {
        if (_dry ('kill ' + $t)) { return $true }
        if ($t -is [ValueType]) { Stop-Process -Id ([int]$t) -Force -ErrorAction Stop }
        else { Stop-Process -Name ([string]$t) -Force -ErrorAction Stop }
        return $true
    } catch { _warn $_; return $false }
}
function _proc_start($exe, $argstr = '') {
    try {
        if (_dry ('start ' + $exe + ' ' + $argstr)) { return 0 }
        $params = @{ FilePath = [string]$exe; PassThru = $true }
        if ($argstr) { $params.ArgumentList = [string]$argstr }
        $p = Start-Process @params -ErrorAction Stop
        return $p.Id
    } catch { _warn $_; return $null }
}
function _proc_run($exe, $argstr = '') {
    try {
        if (_dry ('run ' + $exe + ' ' + $argstr)) { return 0 }
        $params = @{ FilePath = [string]$exe; PassThru = $true; Wait = $true }
        if ($argstr) { $params.ArgumentList = [string]$argstr }
        $p = Start-Process @params -ErrorAction Stop
        return $p.ExitCode
    } catch { _warn $_; return $null }
}
'''

SYS_MODULES['svc'] = r'''
# --- svc : services Windows --------------------------------------------------------
function _svc_list($filter = '*') {
    if (-not (_needwin 'svc_list')) { return $null }
    try {
        $out = @()
        foreach ($s in Get-Service -Name ([string]$filter) -ErrorAction Stop) {
            $out += _rec @{ name = $s.Name; display = $s.DisplayName; status = [string]$s.Status; start = [string]$s.StartType }
        }
        return _list $out
    } catch { _warn $_; return $null }
}
function _svc_status($name) {
    if (-not (_needwin 'svc_status')) { return $null }
    try { return [string](Get-Service -Name ([string]$name) -ErrorAction Stop).Status } catch { return $null }
}
function _svc_start($name) {
    if (-not (_needwin 'svc_start')) { return $false }
    try {
        if (_dry ('svc_start ' + $name)) { return $true }
        Start-Service -Name ([string]$name) -ErrorAction Stop
        return $true
    } catch { _warn $_; return $false }
}
function _svc_stop($name) {
    if (-not (_needwin 'svc_stop')) { return $false }
    try {
        if (_dry ('svc_stop ' + $name)) { return $true }
        Stop-Service -Name ([string]$name) -Force -ErrorAction Stop
        return $true
    } catch { _warn $_; return $false }
}
function _svc_restart($name) {
    if (-not (_needwin 'svc_restart')) { return $false }
    try {
        if (_dry ('svc_restart ' + $name)) { return $true }
        Restart-Service -Name ([string]$name) -Force -ErrorAction Stop
        return $true
    } catch { _warn $_; return $false }
}
function _svc_mode($name, $mode) {
    if (-not (_needwin 'svc_mode')) { return $false }
    try {
        if (_dry ('svc_mode ' + $name + ' ' + $mode)) { return $true }
        Set-Service -Name ([string]$name) -StartupType ([string]$mode) -ErrorAction Stop
        return $true
    } catch { _warn $_; return $false }
}
'''

SYS_MODULES['upd'] = r'''
# --- upd : mises a jour (Windows Update, winget) ----------------------------------
function _upd_pending() {
    if (-not (_needwin 'upd_pending')) { return $null }
    try {
        $s = New-Object -ComObject Microsoft.Update.Session
        $r = $s.CreateUpdateSearcher().Search('IsInstalled=0 and IsHidden=0')
        $out = @()
        foreach ($u in $r.Updates) {
            $out += _rec @{ title = $u.Title; kb = (($u.KBArticleIDs) -join ','); size = [double]$u.MaxDownloadSize; severity = [string]$u.MsrcSeverity }
        }
        return _list $out
    } catch { _warn $_; return $null }
}
function _upd_install() {
    if (-not (_needwin 'upd_install')) { return $null }
    try {
        if (_dry 'installer toutes les mises a jour Windows en attente') { return 0 }
        $s = New-Object -ComObject Microsoft.Update.Session
        $r = $s.CreateUpdateSearcher().Search('IsInstalled=0 and IsHidden=0')
        if ($r.Updates.Count -eq 0) { return 0 }
        $c = New-Object -ComObject Microsoft.Update.UpdateColl
        foreach ($u in $r.Updates) {
            if (-not $u.InstallationBehavior.CanRequestUserInput) { [void]$c.Add($u) }
        }
        $d = $s.CreateUpdateDownloader()
        $d.Updates = $c
        [void]$d.Download()
        $i = $s.CreateUpdateInstaller()
        $i.Updates = $c
        $res = $i.Install()
        return [int]$res.ResultCode
    } catch { _warn $_; return $null }
}
function _upd_hotfixes() {
    if (-not (_needwin 'upd_hotfixes')) { return $null }
    try { return _list (Get-HotFix -ErrorAction Stop | ForEach-Object { _rec @{ id = $_.HotFixID; desc = $_.Description; date = [string]$_.InstalledOn } }) } catch { _warn $_; return $null }
}
function _upd_reboot() {
    if (-not $script:_win) { return (Test-Path '/var/run/reboot-required') }
    foreach ($k in @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired', 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending')) {
        if (Test-Path -LiteralPath $k) { return $true }
    }
    return $false
}
function _upd_winget($apply = $false) {
    try {
        if ($null -eq (Get-Command winget -ErrorAction SilentlyContinue)) { _warn 'winget introuvable'; return $null }
        if ($apply) {
            if (_dry 'winget upgrade --all') { return 0 }
            & winget upgrade --all --silent --accept-source-agreements --accept-package-agreements | Out-Host
            return $LASTEXITCODE
        }
        return (& winget upgrade --accept-source-agreements | Out-String)
    } catch { _warn $_; return $null }
}
'''

SYS_MODULES['sys'] = r'''
# --- sys : systeme ------------------------------------------------------------------
function _sys_isadmin() {
    try {
        if ($script:_win) {
            $p = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
            return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
        }
        return ((& id -u) -eq 0)
    } catch { return $false }
}
function _sys_info() {
    try {
        $r = _rec @{ host = [Environment]::MachineName; user = [Environment]::UserName; os = [Environment]::OSVersion.VersionString; cpus = [Environment]::ProcessorCount; x64 = [Environment]::Is64BitOperatingSystem; ps = $PSVersionTable.PSVersion.ToString(); admin = (_sys_isadmin) }
        if ($script:_win) {
            $o = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
            _set $r 'caption' $o.Caption
            _set $r 'ram' ([double]$o.TotalVisibleMemorySize * 1024)
            _set $r 'uptime' ([math]::Round(((Get-Date) - $o.LastBootUpTime).TotalSeconds))
            $c = Get-CimInstance Win32_Processor | Select-Object -First 1
            _set $r 'cpu' $c.Name
        }
        return $r
    } catch { _warn $_; return $null }
}
function _sys_ps($code) {
    try { return (Invoke-Expression ([string]$code) 2>&1 | Out-String).TrimEnd() } catch { _warn $_; return $null }
}
function _sys_cmd($line) {
    try {
        if ($script:_win) { return ((& cmd.exe /c ([string]$line) 2>&1 | Out-String).TrimEnd()) }
        return ((& sh -c ([string]$line) 2>&1 | Out-String).TrimEnd())
    } catch { _warn $_; return $null }
}
function _sys_env($name) { return [Environment]::GetEnvironmentVariable([string]$name) }
function _sys_setenv($name, $value, $scope = 'Process') {
    try {
        if ($scope -ne 'Process' -and (_dry ('setenv ' + $name + ' (' + $scope + ')'))) { return $true }
        [Environment]::SetEnvironmentVariable([string]$name, [string]$value, [string]$scope)
        return $true
    } catch { _warn $_; return $false }
}
function _sys_events($log = 'System', $n = 20) {
    if (-not (_needwin 'sys_events')) { return $null }
    try {
        $out = @()
        foreach ($e in Get-WinEvent -LogName ([string]$log) -MaxEvents ([int]$n) -ErrorAction Stop) {
            $m = [string]$e.Message
            if ($m.Length -gt 200) { $m = $m.Substring(0, 200) }
            $out += _rec @{ time = $e.TimeCreated.ToString('s'); id = $e.Id; level = [string]$e.LevelDisplayName; provider = $e.ProviderName; msg = $m }
        }
        return _list $out
    } catch { _warn $_; return $null }
}
function _sys_reboot($delay = 0) {
    try {
        if (_dry ('redemarrage dans ' + $delay + ' s')) { return $true }
        if ($script:_win) { & shutdown.exe /r /t ([int]$delay) } else { & shutdown -r ('+' + [math]::Ceiling($delay / 60)) }
        return $true
    } catch { _warn $_; return $false }
}
function _sys_shutdown($delay = 0) {
    try {
        if (_dry ('extinction dans ' + $delay + ' s')) { return $true }
        if ($script:_win) { & shutdown.exe /s /t ([int]$delay) } else { & shutdown -h ('+' + [math]::Ceiling($delay / 60)) }
        return $true
    } catch { _warn $_; return $false }
}
function _sys_abort() {
    try { if ($script:_win) { & shutdown.exe /a } else { & shutdown -c }; return $true } catch { _warn $_; return $false }
}
function _sys_lock() {
    if (-not (_needwin 'sys_lock')) { return $false }
    if (_dry 'verrouillage de la session') { return $true }
    & rundll32.exe user32.dll,LockWorkStation
    return $true
}
function _sys_sleep($ms) { Start-Sleep -Milliseconds ([int]$ms) }
function _sys_beep($freq = 800, $ms = 200) {
    try { [Console]::Beep([int]$freq, [int]$ms); return $true } catch { return $false }
}
function _sys_unix() { return [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() }
function _sys_date($fmt = 'yyyy-MM-dd HH:mm:ss') { return (Get-Date -Format ([string]$fmt)) }
function _sys_clipget() { try { return (Get-Clipboard -Raw) } catch { return $null } }
function _sys_clipset($s) {
    try { Set-Clipboard -Value (_tostr $s); return $true } catch { _warn $_; return $false }
}
'''

SYS_MODULES['serial'] = r'''
# --- serial : ports COM -------------------------------------------------------------
function _serial_list() { return _list ([IO.Ports.SerialPort]::GetPortNames()) }
function _serial_talk($port, $baud, $text = '', $ms = 500) {
    $sp = $null
    try {
        $sp = [IO.Ports.SerialPort]::new([string]$port, [int]$baud)
        $sp.ReadTimeout = 100
        $sp.Open()
        if ($null -ne $text -and ([string]$text) -ne '') { $sp.Write([string]$text) }
        $sw = [Diagnostics.Stopwatch]::StartNew()
        $buf = New-Object Text.StringBuilder
        while ($sw.ElapsedMilliseconds -lt [int]$ms) {
            [void]$buf.Append($sp.ReadExisting())
            Start-Sleep -Milliseconds 20
        }
        return $buf.ToString()
    } catch { _warn $_; return $null } finally { if ($null -ne $sp -and $sp.IsOpen) { $sp.Close() } }
}
'''

SYS_MODULES['usb'] = r'''
# --- usb : peripheriques USB --------------------------------------------------------
function _usb_list() {
    if (-not (_needwin 'usb_list')) { return $null }
    try {
        $out = @()
        foreach ($d in Get-PnpDevice -Class USB -PresentOnly -ErrorAction Stop) {
            $out += _rec @{ name = $d.FriendlyName; id = $d.InstanceId; status = [string]$d.Status }
        }
        return _list $out
    } catch { _warn $_; return $null }
}
'''

SYS_MODULES['json'] = r'''
# --- json : (de)serialisation des tables ---------------------------------------------
function _jval($v) {
    if ($v -is [hashtable] -and $v.ContainsKey('a') -and $v.ContainsKey('h')) {
        if ($v.h.Count -eq 0) {
            $l = New-Object System.Collections.ArrayList
            foreach ($x in $v.a) { [void]$l.Add((_jval $x)) }
            return , $l.ToArray()
        }
        $o = [ordered]@{}
        for ($i = 0; $i -lt $v.a.Count; $i++) { $o[[string]($i + 1)] = _jval $v.a[$i] }
        foreach ($k in $v.h.Keys) { $o[[string]$k] = _jval $v.h[$k] }
        return $o
    }
    return $v
}
function _jin($v) {
    if ($null -eq $v) { return $null }
    if ($v -is [System.Management.Automation.PSCustomObject]) {
        $t = _new
        foreach ($p in $v.PSObject.Properties) { _set $t $p.Name (_jin $p.Value) }
        return $t
    }
    if ($v -is [array]) {
        $t = _new
        foreach ($x in $v) { [void]$t.a.Add((_jin $x)) }
        return $t
    }
    return $v
}
function _json_encode($t, $pretty = $false) {
    try {
        $o = _jval $t
        if ($pretty) { return (ConvertTo-Json -InputObject $o -Depth 20) }
        return (ConvertTo-Json -InputObject $o -Depth 20 -Compress)
    } catch { _warn $_; return $null }
}
function _json_decode($s) {
    try { return (_jin (ConvertFrom-Json -InputObject ([string]$s))) } catch { _warn $_; return $null }
}
function _json_load($p) {
    try { return (_json_decode (Get-Content -LiteralPath ([string]$p) -Raw -ErrorAction Stop)) } catch { _warn $_; return $null }
}
function _json_save($p, $t) {
    try {
        if (_dry ('json_save ' + $p)) { return $true }
        [IO.File]::WriteAllText((_abs $p), (_json_encode $t $true))
        return $true
    } catch { _warn $_; return $false }
}
'''

SYS_MODULES['str'] = r'''
# --- str : chaines et encodages ------------------------------------------------------
function _str_upper($s) { return ([string]$s).ToUpperInvariant() }
function _str_lower($s) { return ([string]$s).ToLowerInvariant() }
function _str_trim($s) { return ([string]$s).Trim() }
function _str_replace($s, $a, $b) { return ([string]$s).Replace([string]$a, [string]$b) }
function _str_match($s, $re) {
    $m = [regex]::Match([string]$s, [string]$re)
    if (-not $m.Success) { return $null }
    $t = _new
    foreach ($g in $m.Groups) { [void]$t.a.Add($g.Value) }
    return $t
}
function _str_b64e($s) { return [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes([string]$s)) }
function _str_b64d($s) {
    try { return [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String([string]$s)) } catch { return $null }
}
function _str_hex($s) { return (([Text.Encoding]::UTF8.GetBytes([string]$s) | ForEach-Object { $_.ToString('x2') }) -join '') }
function _str_hash($s, $algo = 'SHA256') {
    try {
        $h = [Security.Cryptography.HashAlgorithm]::Create([string]$algo)
        return (($h.ComputeHash([Text.Encoding]::UTF8.GetBytes([string]$s)) | ForEach-Object { $_.ToString('x2') }) -join '')
    } catch { _warn $_; return $null }
}
'''


def _sys_builtins():
    out = {}
    for mod, code in SYS_MODULES.items():
        for m in re.finditer(r'^function _(' + mod + r'_\w+)', code, re.M):
            out[m.group(1)] = '_' + m.group(1)
    return out


SYS_BUILTINS = _sys_builtins()
BUILTINS.update(SYS_BUILTINS)


def api_listing():
    lines = []
    for mod, code in SYS_MODULES.items():
        if mod == 'core':
            continue
        lines.append(f'[{mod}]')
        for m in re.finditer(r'^function _(' + mod + r'_\w+)\s*\((.*?)\)\s*\{', code, re.M):
            params = re.sub(r'\s*=\s*', '=', m.group(2).replace('$', ''))
            lines.append(f'  {m.group(1)}({params})')
    return '\n'.join(lines)


RESERVED = {'args', 'input', 'error', 'host', 'home', 'pid', 'pwd', 'true', 'false',
            'null', 'this', 'matches', 'profile', 'shellid', 'event', 'sender',
            'foreach', 'switch', 'psitem', 'myinvocation', 'pscmdlet',
            'executioncontext', 'lastexitcode', 'stacktrace', 'psversiontable',
            'env', 'pshome', 'ofs', 'confirmpreference', 'verbosepreference',
            'debugpreference', 'erroractionpreference', 'dryrun'}
CMP = {'==': '-eq', '~=': '-ne', '!=': '-ne', '<': '-lt', '<=': '-le', '>': '-gt', '>=': '-ge'}
BITOPS = {'&': '-band', '|': '-bor', '^^': '-bxor', '<<': '-shl', '>>': '-shr'}


def safe(n):
    return n + '_' if n.lower() in RESERVED else n


def psstr(s):
    parts, cur = [], ''

    def flush():
        return "'" + re.sub("(['\u2018\u2019\u201a\u201b])", r'\1\1', cur) + "'"

    for ch in s:
        if ord(ch) < 32 or ch == '\x7f':
            if cur:
                parts.append(flush())
                cur = ''
            parts.append(f'[string][char]{ord(ch)}')
        else:
            cur += ch
    if cur or not parts:
        parts.append(flush())
    return parts[0] if len(parts) == 1 else '(' + ' + '.join(parts) + ')'


def const_num(e):
    if e[0] == 'num':
        return float(e[1])
    if e[0] == 'un' and e[1] == '-' and e[2][0] == 'num':
        return -float(e[2][1])
    return None


def walk(stmts, fn):
    for s in stmts:
        fn(s)
        k = s[0]
        if k == 'if':
            for _, b in s[1]:
                walk(b, fn)
            if s[2]:
                walk(s[2], fn)
        elif k == 'while':
            walk(s[2], fn)
        elif k == 'for':
            walk(s[5], fn)
        elif k == 'forin':
            walk(s[3], fn)
        elif k == 'repeat' or k == 'do':
            walk(s[1], fn)
        elif k == 'func':
            walk(s[3], fn)


# ----------------------------------------------------------------------------
# Generateur
# ----------------------------------------------------------------------------
class Gen:
    def __init__(self, ast):
        self.funcs, self.varnames = set(), set()
        self.warnings = []
        self.used_mods = set()
        self.used_syms = set()

        def collect(s):
            if s[0] == 'func':
                self.funcs.add(s[1])
            elif s[0] == 'local':
                self.varnames.update(s[1])
            elif s[0] == 'assign':
                self.varnames.update(t[1] for t in s[1] if t[0] == 'name')
            elif s[0] == 'for':
                self.varnames.add(s[1])
            elif s[0] == 'forin':
                self.varnames.update(s[1])

        walk(ast, collect)
        self.ast = ast
        self.lines, self.ind = [], 0
        self.scopes, self.in_func, self.tmp = [set()], False, 0

    def emit(self, s):
        self.lines.append('    ' * self.ind + s)

    def use(self, n):
        if n in SYS_BUILTINS:
            self.used_mods.add(n.split('_')[0])
            self.used_syms.add(n)

    def new_tmp(self):
        self.tmp += 1
        return f'$_t{self.tmp}'

    def is_local(self, n):
        return any(n in s for s in self.scopes)

    def declare(self, n):
        self.scopes[-1].add(n)

    def var(self, n):
        if self.in_func and not self.is_local(n):
            return '$script:' + safe(n)
        return '$' + safe(n)

    def cond(self, e):
        k = e[0]
        if k == 'bool':
            return '$true' if e[1] else '$false'
        if k == 'nil':
            return '$false'
        if k == 'bin' and (e[1] in CMP or e[1] in ('and', 'or')):
            return self.expr(e)
        if k == 'un' and e[1] == 'not':
            return self.expr(e)
        return f'(_truthy {self.expr(e)})'

    @staticmethod
    def paren(c):
        return c if c.startswith('(') else f'({c})'

    def expr(self, e):
        k = e[0]
        if k == 'num':
            return e[1]
        if k == 'str':
            return psstr(e[1])
        if k == 'nil':
            return '$null'
        if k == 'bool':
            return '$true' if e[1] else '$false'
        if k == 'name':
            n = e[1]
            if not self.is_local(n) and n not in self.varnames:
                if n in self.funcs:
                    return f"'fn_{n}'"
                if n in BUILTINS:
                    self.use(n)
                    return f"'{BUILTINS[n]}'"
            return self.var(n)
        if k == 'index':
            return f'(_get {self.expr(e[1])} {self.expr(e[2])})'
        if k == 'call':
            return self.call(e)
        if k == 'table':
            arr = ', '.join(self.expr(a) for a in e[1])
            hs = ', '.join(f'{self.expr(kk)}, {self.expr(v)}' for kk, v in e[2])
            return f'(_tbl @({arr}) @({hs}))'
        if k == 'un':
            op, x = e[1], e[2]
            if op == '-':
                return f'(-{self.expr(x)})'
            if op == 'not':
                return f'(-not {self.cond(x)})'
            if op == '#':
                return f'(_len {self.expr(x)})'
            if op == '~':
                return f'(-bnot [int]{self.expr(x)})'
        if k == 'bin':
            op, l, r = e[1], e[2], e[3]
            if op in ('and', 'or'):
                return f'({self.cond(l)} -{op} {self.cond(r)})'
            L, R = self.expr(l), self.expr(r)
            if op in CMP:
                return f'({L} {CMP[op]} {R})'
            if op in ('+', '-', '*', '/'):
                return f'({L} {op} {R})'
            if op == '%':
                return f'(_mod {L} {R})'
            if op == '\\':
                return f'([math]::Floor({L} / {R}))'
            if op == '^':
                return f'([math]::Pow({L}, {R}))'
            if op == '..':
                return f'((_tostr {L}) + (_tostr {R}))'
            if op in BITOPS:
                return f'([int]{L} {BITOPS[op]} [int]{R})'
        raise TranspileError(f'expression non geree: {e}')

    def call(self, e):
        callee, args = e[1], e[2]
        argstr = ''.join(' ' + self.expr(a) for a in args)
        if callee[0] == 'name':
            n = callee[1]
            if not self.is_local(n):
                if n in self.funcs:
                    return f'(fn_{n}{argstr})'
                if n in BUILTINS:
                    self.use(n)
                    return f'({BUILTINS[n]}{argstr})'
                if n not in self.varnames:
                    self.warnings.append(f"fonction inconnue '{n}' (appelee comme fn_{n})")
                    return f'(fn_{n}{argstr})'
        return f'(& {self.expr(callee)}{argstr})'

    def block(self, stmts):
        self.scopes.append(set())
        for s in stmts:
            self.stmt(s)
        self.scopes.pop()

    def indented(self, stmts):
        self.ind += 1
        self.block(stmts)
        self.ind -= 1

    def assign_to(self, target, val):
        if target[0] == 'name':
            return f'{self.var(target[1])} = {val}'
        return f'_set {self.expr(target[1])} {self.expr(target[2])} {val}'

    def stmt(self, s):
        k = s[0]
        if k == 'local':
            names, exprs = s[1], s[2]
            vals = [self.expr(e) for e in exprs]
            vals += ['$null'] * (len(names) - len(vals))
            if len(names) == 1:
                self.declare(names[0])
                self.emit(f'{self.var(names[0])} = {vals[0]}')
            else:
                tmps = []
                for v in vals[:len(names)]:
                    t = self.new_tmp()
                    self.emit(f'{t} = {v}')
                    tmps.append(t)
                for n, t in zip(names, tmps):
                    self.declare(n)
                    self.emit(f'{self.var(n)} = {t}')
        elif k == 'assign':
            targets, exprs = s[1], s[2]
            vals = [self.expr(e) for e in exprs]
            vals += ['$null'] * (len(targets) - len(vals))
            if len(targets) == 1:
                self.emit(self.assign_to(targets[0], vals[0]))
            else:
                tmps = []
                for v in vals[:len(targets)]:
                    t = self.new_tmp()
                    self.emit(f'{t} = {v}')
                    tmps.append(t)
                for tg, t in zip(targets, tmps):
                    self.emit(self.assign_to(tg, t))
        elif k == 'callstat':
            self.emit('$null = ' + self.expr(s[1]))
        elif k == 'if':
            for i, (c, body) in enumerate(s[1]):
                head = 'if' if i == 0 else '} elseif'
                self.emit(f'{head} {self.paren(self.cond(c))} {{')
                self.indented(body)
            if s[2] is not None:
                self.emit('} else {')
                self.indented(s[2])
            self.emit('}')
        elif k == 'while':
            self.emit(f'while {self.paren(self.cond(s[1]))} {{')
            self.indented(s[2])
            self.emit('}')
        elif k == 'repeat':
            self.emit('do {')
            self.ind += 1
            self.scopes.append(set())
            for st in s[1]:
                self.stmt(st)
            c = self.paren(self.cond(s[2]))
            self.scopes.pop()
            self.ind -= 1
            self.emit(f'}} until {c}')
        elif k == 'for':
            self.gen_for(s)
        elif k == 'forin':
            self.gen_forin(s)
        elif k == 'return':
            self.emit('return' if s[1] is None else f'return {self.expr(s[1])}')
        elif k == 'break':
            self.emit('break')
        elif k == 'do':
            self.block(s[1])
        elif k == 'func':
            self.gen_func(s)
        else:
            raise TranspileError(f'instruction non geree: {k}')

    def gen_for(self, s):
        _, name, start, stop, step, body = s
        st_val = self.expr(start)
        n = self.tmp = self.tmp + 1
        cstop = const_num(stop)
        cstep = 1.0 if step is None else const_num(step)
        if cstop is not None:
            e_val = self.expr(stop)
        else:
            e_val = f'$_e{n}'
            self.emit(f'{e_val} = {self.expr(stop)}')
        if cstep is None:
            s_val = f'$_s{n}'
            self.emit(f'{s_val} = {self.expr(step)}')
        else:
            s_val = self.expr(step) if step is not None else '1'
        self.scopes.append({name})
        v = self.var(name)
        if cstep is not None:
            cmp_ = '-le' if cstep >= 0 else '-ge'
            self.emit(f'for ({v} = {st_val}; {v} {cmp_} {e_val}; {v} += {s_val}) {{')
        else:
            self.emit(f'for ({v} = {st_val}; ({s_val} -gt 0 -and {v} -le {e_val}) -or '
                      f'({s_val} -le 0 -and {v} -ge {e_val}); {v} += {s_val}) {{')
        self.indented(body)
        self.scopes.pop()
        self.emit('}')

    def gen_forin(self, s):
        _, names, e, body = s
        if not (e[0] == 'call' and e[1][0] == 'name'
                and e[1][1] in ('all', 'pairs')
                and len(e[2]) == 1 and not self.is_local(e[1][1])):
            raise TranspileError('for ... in : seuls all(t) et pairs(t) sont supportes')
        src = self.expr(e[2][0])
        self.scopes.append(set(names))
        if e[1][1] == 'all':
            if len(names) != 1:
                raise TranspileError('for ... in all(t) : une seule variable attendue')
            self.emit(f'foreach ({self.var(names[0])} in (_all {src})) {{')
            self.indented(body)
        else:
            if len(names) != 2:
                raise TranspileError('for ... in pairs(t) : deux variables attendues (k, v)')
            tmp = f'$_p{self.tmp + 1}'
            self.tmp += 1
            self.emit(f'foreach ({tmp} in (_pairs {src})) {{')
            self.ind += 1
            self.emit(f'{self.var(names[0])} = {tmp}[0]')
            self.emit(f'{self.var(names[1])} = {tmp}[1]')
            self.ind -= 1
            self.indented(body)
        self.scopes.pop()
        self.emit('}')

    def gen_func(self, s):
        _, name, params, body, _local = s
        saved = (self.scopes, self.in_func)
        self.scopes, self.in_func = [set(params)], True
        self.emit(f'function fn_{name} {{')
        self.ind += 1
        if params:
            self.emit('param(' + ', '.join('$' + safe(p) for p in params) + ')')
        self.block(body)
        self.ind -= 1
        self.emit('}')
        self.scopes, self.in_func = saved

    def generate(self, loop=False):
        funcs = [s for s in self.ast if s[0] == 'func']
        rest = [s for s in self.ast if s[0] != 'func']
        for f in funcs:
            self.gen_func(f)
            self.emit('')
        self.scopes = [set()]
        for s in rest:
            self.stmt(s)
        if loop:
            self.emit('')
            if '_init' in self.funcs:
                self.emit('$null = fn__init')
            self.emit('while ($true) {')
            self.ind += 1
            for h in ('_update', '_update60', '_draw'):
                if h in self.funcs:
                    self.emit(f'$null = fn_{h}')
            self.emit('_flip')
            self.ind -= 1
            self.emit('}')
        return '\n'.join(self.lines) + '\n'


def ast_stats(ast):
    counts = {}

    def fn(s):
        k = s[0]
        counts[k] = counts.get(k, 0) + 1

    walk(ast, fn)
    return counts


def extract_lua(text):
    """Si le fichier est une cartouche .p8, ne garde que la section __lua__."""
    m = re.search(r'^__lua__\s*$', text, re.M)
    if not m:
        return text
    rest = text[m.end():]
    m2 = re.search(r'^__[a-z]+__\s*$', rest, re.M)
    return rest[:m2.start()] if m2 else rest


def transpile(src, loop=False):
    ast = Parser(lex(extract_lua(src))).parse_chunk()
    gen = Gen(ast)
    body = gen.generate(loop)
    parts = ['# Genere par pico2ps - ne pas editer a la main\n']
    mods = [m for m in SYS_MODULES if m != 'core' and m in gen.used_mods]
    if mods:
        parts.append('[CmdletBinding()]\nparam([switch]$DryRun)\n')
    parts.append(RUNTIME)
    if mods:
        parts.append(SYS_MODULES['core'])
        parts.extend(SYS_MODULES[m] for m in mods)
    parts.append('\n' + body)
    return ''.join(parts), gen.warnings, gen.used_mods, gen.used_syms


def main():
    ap = argparse.ArgumentParser(
        description='Transpile PICO-8 (Lua) vers PowerShell (v2.1 Vivant)')
    ap.add_argument('input', nargs='?')
    ap.add_argument('--api', action='store_true',
                    help='liste les fonctions systeme disponibles')
    ap.add_argument('--list-modules', action='store_true',
                    help='liste les modules et leurs fonctions')
    ap.add_argument('-o', '--output')
    ap.add_argument('--loop', action='store_true',
                    help='ajoute la boucle _init/_update/_draw')
    ap.add_argument('--stats', action='store_true',
                    help='affiche les statistiques AST')
    ap.add_argument('--check', action='store_true',
                    help='parse sans ecrire de fichier')
    ap.add_argument('--no-progress', action='store_true',
                    help='desactive la barre de progression')
    a = ap.parse_args()

    if a.api:
        print(api_listing())
        return
    if a.list_modules:
        for mod in SYS_MODULES:
            if mod == 'core':
                continue
            fns = [m.group(1) for m in re.finditer(
                r'^function _(' + mod + r'_\w+)', SYS_MODULES[mod], re.M)]
            if PAL.on:
                print(f'{PAL.zin}{mod}{PAL.reset} : ' + ', '.join(fns))
            else:
                print(f'{mod} : ' + ', '.join(fns))
        return
    if not a.input:
        ap.error('fichier source requis')

    progress = not a.no_progress
    if progress:
        banner()
    T = 5

    try:
        with open(a.input, encoding='utf-8') as f:
            src = f.read()
        if progress:
            phase(1, T, f'lecture {a.input}')
        lua = extract_lua(src)
        src_lines = lua.splitlines()

        if progress:
            phase(2, T, 'lexage')
        toks = lex(lua)

        if progress:
            phase(3, T, 'parsing')
        ast = Parser(toks).parse_chunk()

        if a.stats:
            st = ast_stats(ast)
            note('AST : ' + ', '.join(f'{k}×{v}' for k, v in sorted(st.items())))

        if progress:
            phase(4, T, 'transpilation')
        gen = Gen(ast)
        body = gen.generate(a.loop)

        if progress:
            phase(5, T, 'assemblage des modules')
        parts = ['# Genere par pico2ps - ne pas editer a la main\n']
        mods = [m for m in SYS_MODULES if m != 'core' and m in gen.used_mods]
        if mods:
            parts.append('[CmdletBinding()]\nparam([switch]$DryRun)\n')
        parts.append(RUNTIME)
        if mods:
            parts.append(SYS_MODULES['core'])
            parts.extend(SYS_MODULES[m] for m in mods)
        parts.append('\n' + body)
        out = ''.join(parts)

        for w in gen.warnings:
            caution(w)
        if gen.used_syms:
            whisper(f'{len(gen.used_syms)} symbole(s) système : '
                    + ', '.join(sorted(gen.used_syms)))
        if mods:
            whisper(f'modules injectés : {", ".join(sorted(mods))}')

        if a.check:
            note('check OK (aucun fichier écrit)')
            return

        path = a.output or re.sub(r'\.[^.]+$', '', a.input) + '.ps1'
        with open(path, 'w', encoding='utf-8-sig', newline='\r\n') as f:
            f.write(out)
        note(f'→ {path}')

    except TranspileError as e:
        hush(e.render(src_lines if 'src_lines' in locals() else None))
        sys.exit(1)
    except FileNotFoundError:
        hush(f'fichier introuvable : {a.input}')
        sys.exit(1)


if __name__ == '__main__':
    main()