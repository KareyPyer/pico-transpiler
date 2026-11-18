pico-8 cartridge // http://www.pico-8.com
version 41
__lua__
-- demo pico2ps
score = 0
names = {"alpha", "beta", "gamma"}

function fib(n)
  if n < 2 then return n end
  return fib(n-1) + fib(n-2)
end

function carre(x) return x*x end

function _init()
  pts = {}
  for i=1,5 do
    add(pts, {x=i, y=carre(i)})
  end
end

_init()

for p in all(pts) do
  print("x="..p.x.." y="..p.y)
end

local a, b = 1, 2
a, b = b, a
print("a="..a.." b="..b)

for i=10,0,-5 do print(i) end

local n = 0
while n < 3 do
  n += 1
  if (n == 2) print("deux")
end

repeat n -= 1 until n <= 0

foreach(names, print)

for k, v in pairs({u=1, w=2}) do
  print(k.."="..v)
end

print("fib(10)="..fib(10))
print("7\\2="..(7\2).." -7%3="..(-7%3).." #names="..#names)
print(flr(3.7).." "..sub("bonjour",1,3).." "..tostr(true))
