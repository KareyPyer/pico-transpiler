# Genere par pico2ps - ne pas editer a la main
[CmdletBinding()]
param([switch]$DryRun)
# --- Runtime pico2ps -------------------------------------------------------
$script:_t0 = [DateTime]::UtcNow
function _tostr($v) {
    if ($null -eq $v) { return 'nil' }
    if ($v -is [bool]) { if ($v) { return 'true' } else { return 'false' } }
    if ($v -is [hashtable]) { return _dump $v 0 }
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
            if ($n -eq '') { $n = '(default)' }
            _set $t $n $v
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

$info = (_sys_info)
$null = (_print ((_tostr 'machine : ') + (_tostr ((_tostr (_get $info 'host')) + (_tostr ((_tostr ' / ') + (_tostr ((_tostr (_get $info 'user')) + (_tostr ((_tostr ' admin=') + (_tostr (_tostr (_get $info 'admin')))))))))))))
$null = (_print '-- disques')
foreach ($d in (_all (_disk_list))) {
    if (_truthy (_get $d 'ready')) {
        $null = (_print ((_tostr (_get $d 'name')) + (_tostr ((_tostr ' ') + (_tostr ((_tostr (_flr ((_get $d 'free') / ([math]::Pow(2, 30))))) + (_tostr ((_tostr ' Go libres sur ') + (_tostr (_flr ((_get $d 'total') / ([math]::Pow(2, 30)))))))))))))
    }
}
$null = (_print '-- reseau')
foreach ($a in (_all (_net_adapters))) {
    $null = (_print ((_tostr (_get $a 'name')) + (_tostr ((_tostr ' ') + (_tostr ((_tostr (_get $a 'ip')) + (_tostr ((_tostr ' ') + (_tostr (_get $a 'status'))))))))))
}
$null = (_print ((_tostr 'ping 1.1.1.1 : ') + (_tostr (_tostr (_net_ping '1.1.1.1')))))
$null = (_print ((_tostr '443 ouvert en local : ') + (_tostr (_tostr (_net_port '127.0.0.1' 443 300)))))
$null = (_print '-- registre')
$null = (_print (_reg_get 'HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion' 'ProductName'))
$null = (_print '-- services / planificateur')
$null = (_print ((_tostr 'spooler : ') + (_tostr (_tostr (_svc_status 'Spooler')))))
$null = (_print ((_tostr (_count (_task_list '*Update*'))) + (_tostr ' taches Update')))
$null = (_print '-- mises a jour')
$pend = (_upd_pending)
$null = (_print ((_tostr (_count $pend)) + (_tostr ((_tostr ' en attente, reboot requis : ') + (_tostr (_tostr (_upd_reboot)))))))
$null = (_print '-- materiel')
foreach ($p in (_all (_serial_list))) {
    $null = (_print ((_tostr 'port serie : ') + (_tostr $p)))
}
foreach ($u in (_all (_usb_list))) {
    $null = (_print ((_tostr 'usb : ') + (_tostr (_get $u 'name'))))
}
$null = (_print '-- fichiers + json')
$tmp = (_fs_tmp)
$null = (_fs_write $tmp (_json_encode (_tbl @() @('nom', 'pico2ps', 'n', 3, 'liste', (_tbl @(1, 2, 3) @())))))
$doc = (_json_decode (_fs_cat $tmp))
$null = (_print ((_tostr (_get $doc 'nom')) + (_tostr ((_tostr ' ') + (_tostr ((_tostr (_get $doc 'n')) + (_tostr ((_tostr ' sha=') + (_tostr (_sub (_fs_hash $tmp) 1 12))))))))))
$null = (_fs_rm $tmp)
