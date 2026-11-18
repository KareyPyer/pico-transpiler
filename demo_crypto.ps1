# Genere par pico2ps - ne pas editer a la main
[CmdletBinding()]
param([switch]$DryRun)
# --- Runtime pico2ps -------------------------------------------------------
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

$null = (_print '=== pico2ps / crypto + mathx demo ===')
$null = (_print '')
$null = (_print '-- 1. empreintes (hash) --')
$h1 = (_crypto_hash 'bonjour')
$h2 = (_crypto_hash 'bonjour')
$h3 = (_crypto_hash 'BONJOUR')
$null = (_print ((_tostr 'hash(''bonjour'') = ') + (_tostr $h1)))
$null = (_print ((_tostr 'hash(''bonjour'') = ') + (_tostr $h2)))
$null = (_print ((_tostr 'hash(''BONJOUR'') = ') + (_tostr $h3)))
if ($h1 -eq $h2) {
    $null = (_print '[ok] deterministe (h1 == h2)')
} else {
    $null = (_print '[ko] NON deterministe !')
}
if ($h1 -ne $h3) {
    $null = (_print '[ok] sensible a la casse (h1 != h3)')
} else {
    $null = (_print '[ko] insensible a la casse !')
}
$null = (_print '')
$null = (_print '-- 2. hmac --')
$msg = 'message authentifie'
$key = 'cle-secrete'
$sig = (_crypto_hmac $msg $key)
$null = (_print ((_tostr 'hmac = ') + (_tostr $sig)))
$sig_wrong = (_crypto_hmac $msg 'mauvaise-cle')
if ($sig -eq $sig_wrong) {
    $null = (_print '[ko] la cle n''influence pas le HMAC !')
} else {
    $null = (_print '[ok] HMAC depend de la cle')
}
$null = (_print '')
$null = (_print '-- 3. rng (de 1 a 6) --')
$counts = (_tbl @(0, 0, 0, 0, 0, 0) @())
$tirage = 0
for ($i = 1; $i -le 60; $i += 1) {
    $r = (_crypto_rng 1 6)
    _set $counts $r ((_get $counts $r) + 1)
    if ($i -le 10) {
        $null = (_print ((_tostr '  tirage ') + (_tostr ((_tostr $i) + (_tostr ((_tostr ' = ') + (_tostr $r)))))))
    }
}
$null = (_print 'frequences sur 60 tirages :')
for ($face = 1; $face -le 6; $face += 1) {
    $null = (_print ((_tostr '  face ') + (_tostr ((_tostr $face) + (_tostr ((_tostr ' : ') + (_tostr ((_tostr (_get $counts $face)) + (_tostr ' fois')))))))))
}
$null = (_print '')
$null = (_print '-- 4. uuid --')
$u1 = (_crypto_uuid)
$u2 = (_crypto_uuid)
$null = (_print ((_tostr 'uuid1 = ') + (_tostr $u1)))
$null = (_print ((_tostr 'uuid2 = ') + (_tostr $u2)))
if ($u1 -ne $u2) {
    $null = (_print '[ok] deux UUID distincts')
} else {
    $null = (_print '[ko] collision !')
}
$null = (_print '')
$null = (_print '-- 5. scellement --')
$secret = 'le tresor est sous le troisieme palmier'
$pass = 'mot-de-passe-solide'
$scelle = (_crypto_seal $secret $pass)
$null = (_print ((_tostr 'scelle (base64) = ') + (_tostr $scelle)))
$null = (_print ((_tostr 'taille du sceau  = ') + (_tostr ((_tostr (_len $scelle)) + (_tostr ' caracteres base64')))))
$ouvert = (_crypto_open $scelle $pass)
$null = (_print ((_tostr 'ouvert           = ') + (_tostr $ouvert)))
if ($ouvert -eq $secret) {
    $null = (_print '[ok] aller-retour intact')
} else {
    $null = (_print '[ko] le message a ete altere !')
}
$rate = (_crypto_open $scelle 'mauvaise-cle')
if ($rate -eq $null) {
    $null = (_print '[ok] mauvaise cle -> nil (rejet)')
} else {
    $null = (_print ((_tostr '[!] mauvaise cle a produit : ') + (_tostr (_tostr $rate))))
}
$null = (_print '')
$null = (_print '-- 6. mathx --')
$null = (_print ((_tostr 'lerp(0, 100, 0.25)  = ') + (_tostr (_mathx_lerp 0 100 0.25))))
$null = (_print ((_tostr 'lerp(0, 100, 0.75)  = ') + (_tostr (_mathx_lerp 0 100 0.75))))
$null = (_print ((_tostr 'clamp(150, 0, 100)  = ') + (_tostr (_mathx_clamp 150 0 100))))
$null = (_print ((_tostr 'clamp(-5, 0, 100)   = ') + (_tostr (_mathx_clamp (-5) 0 100))))
$null = (_print ((_tostr 'smooth(0.5)         = ') + (_tostr (_mathx_smooth 0.5))))
$null = (_print ((_tostr 'map(5, 0, 10, 0, 100) = ') + (_tostr (_mathx_map 5 0 10 0 100))))
$null = (_print ((_tostr 'dist((0,0),(3,4))   = ') + (_tostr (_mathx_dist 0 0 3 4))))
$null = (_print '')
$null = (_print 'bruit 1D sur x = 0..4 (seed=42) :')
for ($i = 0; $i -le 8; $i += 1) {
    $x = ($i * 0.5)
    $v = (_mathx_noise $x 42)
    $null = (_print ((_tostr '  x=') + (_tostr ((_tostr $x) + (_tostr ((_tostr '  ->  ') + (_tostr $v)))))))
}
$null = (_print '')
$null = (_print '-- 7. scenario : journal scelle et empreinte --')
$journal = ''
for ($i = 1; $i -le 3; $i += 1) {
    $journal = ((_tostr $journal) + (_tostr ((_tostr 'ligne ') + (_tostr ((_tostr $i) + (_tostr ' ; '))))))
}
$null = (_print ((_tostr 'journal clair  : ') + (_tostr $journal)))
$null = (_print ((_tostr 'empreinte      : ') + (_tostr (_crypto_hash $journal))))
$coffre = (_crypto_seal $journal 'cle-du-journal')
$null = (_print ((_tostr 'journal scelle : ') + (_tostr $coffre)))
$relu = (_crypto_open $coffre 'cle-du-journal')
if ($relu -eq $journal) {
    $null = (_print '[ok] journal restaure a l''identique')
} else {
    $null = (_print '[ko] corruption du journal !')
}
$null = (_print '')
$null = (_print '-- 8. verification --')
$ok = 0
$ko = 0
if ((_crypto_hash 'a') -eq (_crypto_hash 'a')) {
    $ok = ($ok + 1)
} else {
    $ko = ($ko + 1)
}
if ((_crypto_hash 'a') -ne (_crypto_hash 'b')) {
    $ok = ($ok + 1)
} else {
    $ko = ($ko + 1)
}
if ((_crypto_hmac 'm' 'k') -eq (_crypto_hmac 'm' 'k')) {
    $ok = ($ok + 1)
} else {
    $ko = ($ko + 1)
}
if ((_crypto_open (_crypto_seal 'x' 'k') 'k') -eq 'x') {
    $ok = ($ok + 1)
} else {
    $ko = ($ko + 1)
}
if ((_mathx_lerp 0 10 0.5) -eq 5) {
    $ok = ($ok + 1)
} else {
    $ko = ($ko + 1)
}
if ((_mathx_clamp 999 0 1) -eq 1) {
    $ok = ($ok + 1)
} else {
    $ko = ($ko + 1)
}
if ((_mathx_dist 0 0 3 4) -eq 5) {
    $ok = ($ok + 1)
} else {
    $ko = ($ko + 1)
}
$null = (_print ((_tostr 'reussis : ') + (_tostr $ok)))
$null = (_print ((_tostr 'echoues : ') + (_tostr $ko)))
if ($ko -eq 0) {
    $null = (_print '')
    $null = (_print '=== TOUT EST VERT : crypto et mathx fonctionnent ===')
} else {
    $null = (_print '')
    $null = (_print ((_tostr '=== ATTENTION : ') + (_tostr ((_tostr $ko) + (_tostr ' echec(s) ===')))))
}
