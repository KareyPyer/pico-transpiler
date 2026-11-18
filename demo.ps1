# Genere par pico2ps - ne pas editer a la main
# --- Runtime pico2ps -------------------------------------------------------
$script:_t0 = [DateTime]::UtcNow
function _tostr($v) {
    if ($null -eq $v) { return 'nil' }
    if ($v -is [bool]) { if ($v) { return 'true' } else { return 'false' } }
    if ($v -is [hashtable]) { return '[table]' }
    return [string]$v
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
        $k = $h[$i]
        $v = $h[$i + 1]
        _set $t $k $v
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
function _all($t) { return , $t.a.ToArray() }
function _pairs($t) {
    $l = [System.Collections.ArrayList]::new()
    for ($i = 0; $i -lt $t.a.Count; $i++) { [void]$l.Add(@(($i + 1), $t.a[$i])) }
    foreach ($k in @($t.h.Keys)) { [void]$l.Add(@($k, $t.h[$k])) }
    return , $l
}
function _foreach($t, $f) { foreach ($x in $t.a.ToArray()) { [void](& $f $x) } }
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

function fn_fib {
    param($n)
    if ($n -lt 2) {
        return $n
    }
    return ((fn_fib ($n - 1)) + (fn_fib ($n - 2)))
}

function fn_carre {
    param($x)
    return ($x * $x)
}

function fn__init {
    $script:pts = (_tbl @() @())
    for ($i = 1; $i -le 5; $i += 1) {
        $null = (_add $script:pts (_tbl @() @('x', $i, 'y', (fn_carre $i))))
    }
}

$score = 0
$names = (_tbl @('alpha', 'beta', 'gamma') @())
$null = (fn__init)
foreach ($p in (_all $pts)) {
    $null = (_print ((_tostr 'x=') + (_tostr ((_tostr (_get $p 'x')) + (_tostr ((_tostr ' y=') + (_tostr (_get $p 'y'))))))))
}
$_t2 = 1
$_t3 = 2
$a = $_t2
$b = $_t3
$_t4 = $b
$_t5 = $a
$a = $_t4
$b = $_t5
$null = (_print ((_tostr 'a=') + (_tostr ((_tostr $a) + (_tostr ((_tostr ' b=') + (_tostr $b)))))))
for ($i = 10; $i -ge 0; $i += (-5)) {
    $null = (_print $i)
}
$n = 0
while ($n -lt 3) {
    $n = ($n + 1)
    if ($n -eq 2) {
        $null = (_print 'deux')
    }
}
do {
    $n = ($n - 1)
} until ($n -le 0)
$null = (_foreach $names '_print')
foreach ($_p7 in (_pairs (_tbl @() @('u', 1, 'w', 2)))) {
    $k = $_p7[0]
    $v = $_p7[1]
    $null = (_print ((_tostr $k) + (_tostr ((_tostr '=') + (_tostr $v)))))
}
$null = (_print ((_tostr 'fib(10)=') + (_tostr (fn_fib 10))))
$null = (_print ((_tostr '7\2=') + (_tostr ((_tostr ([math]::Floor(7 / 2))) + (_tostr ((_tostr ' -7%3=') + (_tostr ((_tostr (_mod (-7) 3)) + (_tostr ((_tostr ' #names=') + (_tostr (_len $names))))))))))))
$null = (_print ((_tostr (_flr 3.7)) + (_tostr ((_tostr ' ') + (_tostr ((_tostr (_sub 'bonjour' 1 3)) + (_tostr ((_tostr ' ') + (_tostr (_tostr $true))))))))))

$null = fn__init
while ($true) {
    _flip
}
