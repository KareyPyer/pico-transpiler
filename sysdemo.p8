pico-8 cartridge // http://www.pico-8.com
version 41
__lua__
-- sysdemo : tour d'horizon de la bibliotheque systeme
-- (lecture seule, sauf un fichier temporaire ; essaie d'abord avec  -DryRun)

info = sys_info()
print("machine : "..info.host.." / "..info.user.." admin="..tostr(info.admin))

print("-- disques")
for d in all(disk_list()) do
  if d.ready then
    print(d.name.." "..flr(d.free/2^30).." Go libres sur "..flr(d.total/2^30))
  end
end

print("-- reseau")
for a in all(net_adapters()) do
  print(a.name.." "..a.ip.." "..a.status)
end
print("ping 1.1.1.1 : "..tostr(net_ping("1.1.1.1")))
print("443 ouvert en local : "..tostr(net_port("127.0.0.1", 443, 300)))

print("-- registre")
print(reg_get("HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion", "ProductName"))

print("-- services / planificateur")
print("spooler : "..tostr(svc_status("Spooler")))
print(count(task_list("*Update*")).." taches Update")

print("-- mises a jour")
pend = upd_pending()
print(count(pend).." en attente, reboot requis : "..tostr(upd_reboot()))

print("-- materiel")
for p in all(serial_list()) do print("port serie : "..p) end
for u in all(usb_list()) do print("usb : "..u.name) end

print("-- fichiers + json")
tmp = fs_tmp()
fs_write(tmp, json_encode({nom="pico2ps", n=3, liste={1,2,3}}))
doc = json_decode(fs_cat(tmp))
print(doc.nom.." "..doc.n.." sha="..sub(fs_hash(tmp), 1, 12))
fs_rm(tmp)

-- exemples d'actions (a tester avec -DryRun) :
-- task_addps("NettoyageNuit", "C:\\scripts\\clean.ps1", "daily@03:00")
-- reg_set("HKCU\\Software\\Demo", "Valeur", 42)
-- net_wol("AA:BB:CC:DD:EE:FF")
