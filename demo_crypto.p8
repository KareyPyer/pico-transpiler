-- ============================================================
-- demo_crypto.lua — exercice des modules crypto & mathx
-- Transpiler avec : python pico2ps.py demo_crypto.lua
-- Executer avec  : powershell -File demo_crypto.ps1
-- (ajouter -DryRun pour voir les appels sensibles sans effet)
-- ============================================================

print("=== pico2ps / crypto + mathx demo ===")
print("")

-- ------------------------------------------------------------
-- 1. Empreintes : identite numerique d'une donnee
-- ------------------------------------------------------------
print("-- 1. empreintes (hash) --")
local h1 = crypto_hash("bonjour")
local h2 = crypto_hash("bonjour")
local h3 = crypto_hash("BONJOUR")

print("hash('bonjour') = " .. h1)
print("hash('bonjour') = " .. h2)
print("hash('BONJOUR') = " .. h3)

if h1 == h2 then
  print("[ok] deterministe (h1 == h2)")
else
  print("[ko] NON deterministe !")
end
if h1 != h3 then
  print("[ok] sensible a la casse (h1 != h3)")
else
  print("[ko] insensible a la casse !")
end

-- ------------------------------------------------------------
-- 2. HMAC : signature a cle partagee
-- ------------------------------------------------------------
print("")
print("-- 2. hmac --")
local msg = "message authentifie"
local key = "cle-secrete"
local sig = crypto_hmac(msg, key)
print("hmac = " .. sig)

local sig_wrong = crypto_hmac(msg, "mauvaise-cle")
if sig == sig_wrong then
  print("[ko] la cle n'influence pas le HMAC !")
else
  print("[ok] HMAC depend de la cle")
end

-- ------------------------------------------------------------
-- 3. RNG cryptographique : tirages uniformes
-- ------------------------------------------------------------
print("")
print("-- 3. rng (de 1 a 6) --")
local counts = {0, 0, 0, 0, 0, 0}
local tirage = 0
for i = 1, 60 do
  local r = crypto_rng(1, 6)
  counts[r] += 1
  if i <= 10 then
    print("  tirage " .. i .. " = " .. r)
  end
end
print("frequences sur 60 tirages :")
for face = 1, 6 do
  print("  face " .. face .. " : " .. counts[face] .. " fois")
end

-- ------------------------------------------------------------
-- 4. UUID : identifiants uniques
-- ------------------------------------------------------------
print("")
print("-- 4. uuid --")
local u1 = crypto_uuid()
local u2 = crypto_uuid()
print("uuid1 = " .. u1)
print("uuid2 = " .. u2)
if u1 != u2 then
  print("[ok] deux UUID distincts")
else
  print("[ko] collision !")
end

-- ------------------------------------------------------------
-- 5. Scellement / ouverture (AES-GCM)
-- ------------------------------------------------------------
print("")
print("-- 5. scellement --")
local secret = "le tresor est sous le troisieme palmier"
local pass = "mot-de-passe-solide"

local scelle = crypto_seal(secret, pass)
print("scelle (base64) = " .. scelle)
print("taille du sceau  = " .. #scelle .. " caracteres base64")

local ouvert = crypto_open(scelle, pass)
print("ouvert           = " .. ouvert)

if ouvert == secret then
  print("[ok] aller-retour intact")
else
  print("[ko] le message a ete altere !")
end

-- tentative avec la mauvaise cle : doit renvoyer nil
local rate = crypto_open(scelle, "mauvaise-cle")
if rate == nil then
  print("[ok] mauvaise cle -> nil (rejet)")
else
  print("[!] mauvaise cle a produit : " .. tostr(rate))
end

-- ------------------------------------------------------------
-- 6. Mathx : geometrie douce et bruit organique
-- ------------------------------------------------------------
print("")
print("-- 6. mathx --")

print("lerp(0, 100, 0.25)  = " .. mathx_lerp(0, 100, 0.25))
print("lerp(0, 100, 0.75)  = " .. mathx_lerp(0, 100, 0.75))
print("clamp(150, 0, 100)  = " .. mathx_clamp(150, 0, 100))
print("clamp(-5, 0, 100)   = " .. mathx_clamp(-5, 0, 100))
print("smooth(0.5)         = " .. mathx_smooth(0.5))
print("map(5, 0, 10, 0, 100) = " .. mathx_map(5, 0, 10, 0, 100))
print("dist((0,0),(3,4))   = " .. mathx_dist(0, 0, 3, 4))

print("")
print("bruit 1D sur x = 0..4 (seed=42) :")
for i = 0, 8 do
  local x = i * 0.5
  local v = mathx_noise(x, 42)
  print("  x=" .. x .. "  ->  " .. v)
end

-- ------------------------------------------------------------
-- 7. Petit scenario : sceau d'un journal + empreinte
-- ------------------------------------------------------------
print("")
print("-- 7. scenario : journal scelle et empreinte --")

local journal = ""
for i = 1, 3 do
  journal = journal .. "ligne " .. i .. " ; "
end
print("journal clair  : " .. journal)
print("empreinte      : " .. crypto_hash(journal))

local coffre = crypto_seal(journal, "cle-du-journal")
print("journal scelle : " .. coffre)

local relu = crypto_open(coffre, "cle-du-journal")
if relu == journal then
  print("[ok] journal restaure a l'identique")
else
  print("[ko] corruption du journal !")
end

-- ------------------------------------------------------------
-- 8. Boucle de verification finale
-- ------------------------------------------------------------
print("")
print("-- 8. verification --")
local ok = 0
local ko = 0

if crypto_hash("a") == crypto_hash("a") then ok += 1 else ko += 1 end
if crypto_hash("a") != crypto_hash("b") then ok += 1 else ko += 1 end
if crypto_hmac("m", "k") == crypto_hmac("m", "k") then ok += 1 else ko += 1 end
if crypto_open(crypto_seal("x", "k"), "k") == "x" then ok += 1 else ko += 1 end
if mathx_lerp(0, 10, 0.5) == 5 then ok += 1 else ko += 1 end
if mathx_clamp(999, 0, 1) == 1 then ok += 1 else ko += 1 end
if mathx_dist(0, 0, 3, 4) == 5 then ok += 1 else ko += 1 end

print("reussis : " .. ok)
print("echoues : " .. ko)

if ko == 0 then
  print("")
  print("=== TOUT EST VERT : crypto et mathx fonctionnent ===")
else
  print("")
  print("=== ATTENTION : " .. ko .. " echec(s) ===")
end