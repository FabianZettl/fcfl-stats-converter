-- PESM-LivePatch: changes of the database (Player.bin attributes, line-ups, shirt numbers, formations) reach the RUNNING game, no restart.
-- The converter (FCFL) or PESM writes the files into content\pesm-livepatch\ (players.txt, teams.txt); you open the Sider overlay, pick this module and press F7.
-- Everything is written into the game's memory with a check first (right table size, same players in the squad); a failed check writes nothing.
local m = { version = "1.0" }

-- Sider's Lua has no pcall in some builds (PlayerDump has the same shim): fall back to xpcall, then to a plain call
local pcall = pcall
if not pcall then
  if xpcall then
    pcall = function(f, ...)
      local a = { ... }
      return xpcall(function() return f(unpack and unpack(a) or table.unpack(a)) end, function(e) return e end)
    end
  else
    pcall = function(f, ...) return true, f(...) end
  end
end

local KEY_LOAD = 0x76   -- F7
local BLOCK, IDOFF = 0x17C, 0x30                          -- player table: 380 byte blocks, player id at +0x30
local TOBJ, SQ, NUM, FM1, FM2 = 1680, 0, 330, 784, 944    -- team objects
local ctx_ref, DIR
local RPM, REGIONS, FFI
local STATUS = {}
local pt_cache = { tables = nil }   -- player tables found (and their index), kept until the game moves them
local tb_cache = { base = nil }     -- base of the team array

local LOGO = [[
   ____  _____ ____  __  __
  |  _ \| ____/ ___||  \/  |
  | |_) |  _| \___ \| |\/| |
  |  __/| |___ ___) | |  | |
  |_|   |_____|____/|_|  |_|
      L I V E   P A T C H
]]

local function say(s)
  log("PESM-LivePatch: " .. s)
  STATUS[#STATUS + 1] = s
  if #STATUS > 4 then table.remove(STATUS, 1) end
end

do
  local ffi = ffi
  if ffi == nil and type(require) == "function" then local ok, r = pcall(require, "ffi"); if ok then ffi = r end end
  FFI = ffi
  if ffi then
    pcall(ffi.cdef, [[
      void* PL_GetCurrentProcess(void) __asm__("GetCurrentProcess");
      int PL_ReadProcessMemory(void* h, const void* a, void* b, size_t n, size_t* got) __asm__("ReadProcessMemory");
      typedef struct { void* BaseAddress; void* AllocationBase; uint32_t AllocationProtect; uint16_t PartitionId;
                       size_t RegionSize; uint32_t State; uint32_t Protect; uint32_t Type; } PL_MBI;
      size_t PL_VirtualQuery(const void* a, PL_MBI* b, size_t n) __asm__("VirtualQuery");
    ]])
    local okp, proc = pcall(function() return ffi.C.PL_GetCurrentProcess() end)
    if okp and proc then
      local cap, got = 0x10000, ffi.new("size_t[1]")
      local buf = ffi.new("uint8_t[?]", cap)
      RPM = function(addr, len)   -- nil instead of a crash on a bad address
        if type(addr) ~= "number" or addr < 0x10000 or len <= 0 or len > 0x4000000 then return nil end
        if len > cap then cap = len; buf = ffi.new("uint8_t[?]", cap) end
        got[0] = 0
        local r = ffi.C.PL_ReadProcessMemory(proc, ffi.cast("const void*", addr), buf, len, got)
        if r == 0 or tonumber(got[0]) ~= len then return nil end
        return ffi.string(buf, len)
      end
      local mbi = ffi.new("PL_MBI[1]")
      REGIONS = function(min_size)
        local res, addr, sz = {}, 0x10000, ffi.sizeof("PL_MBI")
        while addr < 0x7FFFFFFF0000 and #res < 20000 do
          local r = ffi.C.PL_VirtualQuery(ffi.cast("const void*", addr), mbi, sz)
          if r == 0 then break end
          local b, n = tonumber(ffi.cast("uintptr_t", mbi[0].BaseAddress)), tonumber(mbi[0].RegionSize)
          if not n or n <= 0 then break end
          local pr = mbi[0].Protect
          if mbi[0].State == 0x1000 and (pr == 0x04 or pr == 0x40) and n >= min_size then res[#res + 1] = { b, n } end
          addr = b + n
        end
        return res
      end
    end
  end
end

local function u32(s, o) return memory.unpack("u32", s:sub(o + 1, o + 4)) end
local function unhex(h) return (h:gsub("%x%x", function(x) return string.char(tonumber(x, 16)) end)) end

-- every place in the process where `needle` is found (RAM only, 4 MB at a time)
local function scan(needle, limit)
  local hits, CH, OV = {}, 0x400000, 0x2000
  for _, rg in ipairs(REGIONS(0x1000)) do
    local off = 0
    while off < rg[2] and #hits < limit do
      local s = RPM(rg[1] + off, math.min(CH + OV, rg[2] - off))
      if s then
        local init = 1
        while #hits < limit do
          local h = s:find(needle, init, true)
          if not h then break end
          init = h + 1
          if h - 1 < CH then hits[#hits + 1] = rg[1] + off + h - 1 end
        end
      end
      off = off + CH
    end
  end
  return hits
end

local function readfile(name)
  local f = io.open(DIR .. name, "r")
  if not f then return nil end
  local t = {}
  for l in f:lines() do t[#t + 1] = l end
  f:close()
  return t
end

---------------------------------------------------------------- player attributes
local function id_ok(id)
  return id >= 1 and id <= 1048575 or (id >= 0x10000000 and id < 0xF0000000 and math.floor(id / 1048576) % 256 == 0)
end

local function valid(addr)   -- a block: plausible id at +0x30 and a letter of the name at +0x38
  local b = RPM(addr + IDOFF, 0x20)
  return b ~= nil and id_ok(u32(b, 0)) and b:byte(9) >= 0x20
end

local function find_player_tables(pid, count)
  local found, seen = {}, {}
  for _, base0 in ipairs(scan(memory.pack("u32", pid), 40)) do
    local base = base0 - IDOFF
    if base > 0x10000 and valid(base) and valid(base + BLOCK) and valid(base + 2 * BLOCK) then
      local a = base
      while valid(a - BLOCK) do a = a - BLOCK end
      if not seen[a] then
        seen[a] = true
        local n, b = 0, a
        while n < 1000000 and valid(b) do b = b + BLOCK; n = n + 1 end
        if n == count then found[#found + 1] = { base = a, count = n } end   -- only the table of the whole database, the small ones are something else
      end
    end
  end
  return found
end

local function build_index(t)
  local idx, k = {}, 0
  while k < t.count do
    local n = math.min(t.count - k, 0x20000)
    local s = RPM(t.base + k * BLOCK, n * BLOCK)
    if not s then break end
    for i = 0, n - 1 do idx[u32(s, i * BLOCK + IDOFF)] = t.base + (k + i) * BLOCK end
    k = k + n
  end
  t.index = idx
end

local function load_players()
  local L = readfile("players.txt")
  if not L or #L < 2 then return 0, 0 end
  local count = tonumber(L[1]:match("^COUNT (%d+)"))
  local rows = {}
  for i = 2, #L do
    local a, b, c, d, e = L[i]:match("^(%d+) (%d+) (%d+) (%d+) (%d+)")
    if a then rows[#rows + 1] = { tonumber(a), tonumber(b), tonumber(c), tonumber(d), tonumber(e) } end
  end
  if not count or #rows == 0 then return 0, 0 end
  local tabs = pt_cache.tables
  if tabs then   -- still where it was?
    for _, t in ipairs(tabs) do if not (valid(t.base) and valid(t.base + (t.count - 1) * BLOCK)) then tabs = nil; break end end
  end
  if not tabs then
    tabs = find_player_tables(rows[1][1], count)
    pt_cache.tables = tabs
  end
  if #tabs == 0 then say("player table not found (" .. count .. " players)"); return 0, #rows end
  local written, bad = 0, 0
  for _, t in ipairs(tabs) do
    if not t.index then build_index(t) end
    for _, r in ipairs(rows) do
      local a = t.index[r[1]]
      local b = a and RPM(a + r[2], 4)
      local id = a and RPM(a + IDOFF, 4)
      if b and id and u32(id, 0) == r[1] then
        local v = u32(b, 0)
        local f = math.floor(v / 2 ^ r[3]) % 2 ^ r[4]
        if f ~= r[5] and pcall(memory.write, a + r[2], memory.pack("u32", v - f * 2 ^ r[3] + r[5] * 2 ^ r[3])) then written = written + 1 end
      else
        bad = bad + 1
      end
    end
  end
  return written, bad
end

---------------------------------------------------------------- teams (squad order, shirt numbers, formations)
local function squad_matches(mem, pids)
  local want, n = {}, 0
  for _, p in ipairs(pids) do want[p] = true end
  for j = 0, 39 do
    local p = u32(mem, j * 8)
    if p ~= 0 then n = n + 1; if not want[p] then return false end end
  end
  return n == #pids
end

local function load_teams()
  local L = readfile("teams.txt")
  if not L or #L < 2 then return 0, 0 end
  local loc, T, N, FMS = nil, {}, {}, {}
  for _, l in ipairs(L) do
    local kind, rest = l:match("^(%a+) (.*)$")
    if kind == "LOC" then
      local r, hx = rest:match("^(%d+) (%x+)")
      loc = { rank = tonumber(r), s = unhex(hx) }
    elseif kind == "T" or kind == "N" then
      local r, tail = rest:match("^(%d+) ?(.*)$")
      local v = {}
      for x in tail:gmatch("%d+") do v[#v + 1] = tonumber(x) end
      if kind == "T" then T[tonumber(r)] = v else N[tonumber(r)] = v end
    elseif kind == "F" then
      local r, w, hx = rest:match("^(%d+) (%d) (%x+)")
      FMS[#FMS + 1] = { rank = tonumber(r), which = tonumber(w), s = unhex(hx) }
    end
  end
  if not loc then return 0, 0 end
  local first
  for r in pairs(T) do if not first or r < first then first = r end end
  if not first then return 0, 0 end
  local base = tb_cache.base
  if base and RPM(base + loc.rank * TOBJ + FM1, #loc.s) ~= loc.s then base = nil end   -- the unpatched locator team must still look the same
  if not base then
    for _, h in ipairs(scan(loc.s, 12)) do
      local b = h - FM1 - loc.rank * TOBJ
      local mem = RPM(b + first * TOBJ + SQ, 40 * 8)
      if mem and squad_matches(mem, T[first]) then base = b; break end
    end
    tb_cache.base = base
  end
  if not base then say("team table not found (squad of team " .. first .. " does not match)"); return 0, 1 end
  local wrote, skipped = 0, 0
  for r, pids in pairs(T) do
    local o = base + r * TOBJ
    local mem = RPM(o + SQ, 40 * 8)
    if mem and squad_matches(mem, pids) then
      for j, p in ipairs(pids) do pcall(memory.write, o + SQ + (j - 1) * 8, memory.pack("u32", p)) end
      if N[r] then for j, n in ipairs(N[r]) do pcall(memory.write, o + NUM + (j - 1) * 2, memory.pack("u16", n)) end end
      for _, fm in ipairs(FMS) do
        if fm.rank == r and #fm.s == 99 then pcall(memory.write, o + (fm.which == 1 and FM1 or FM2), fm.s) end
      end
      wrote = wrote + 1
    else
      skipped = skipped + 1   -- other players than in the file (transfer): needs a restart
    end
  end
  return wrote, skipped
end

---------------------------------------------------------------- keys and overlay
local function load_all()
  local t0 = os.clock()
  if not RPM then say("no ffi: nothing loaded"); return end
  local w, b = 0, 0
  local ok, e = pcall(function() local a, c = load_players(); w, b = a, c end)
  if not ok then say("error in player values: " .. tostring(e)) end
  local tw, ts = 0, 0
  ok, e = pcall(function() local a, c = load_teams(); tw, ts = a, c end)
  if not ok then say("error in teams: " .. tostring(e)) end
  say(string.format("loaded: %d player values, %d teams (%d skipped) in %.1f s", w, tw, b + ts, os.clock() - t0))
end

function m.key_down(ctx, vkey)
  if tonumber(vkey) == KEY_LOAD then load_all() end
end

local pending_t, pending_txt = -10, ""
local function pending()
  if os.clock() - pending_t > 2 then
    pending_t = os.clock()
    local p, t = readfile("players.txt"), readfile("teams.txt")
    local np = p and math.max(0, #p - 1) or 0
    local nt = 0
    for _, l in ipairs(t or {}) do if l:sub(1, 2) == "T " then nt = nt + 1 end end
    pending_txt = string.format("Ready to load: %d player values, %d teams", np, nt)
  end
  return pending_txt
end

function m.overlay_on(ctx)
  local s = LOGO
  s = s .. "\n Load changes into the running game - no restart\n"
  s = s .. "\n 1. Change and write in the manager (PESM) or in the FCFL converter."
  s = s .. "\n 2. Here, in the main menu, press  F7."
  s = s .. "\n 3. Close the overlay (Space) and start your match as usual."
  s = s .. "\n    The changes are there at once.\n"
  s = s .. "\n Live: line-ups, shirt numbers, formations, attributes."
  s = s .. "\n Needs a restart: skills, positions, names, new players.\n"
  s = s .. "\n " .. pending()
  for _, l in ipairs(STATUS) do s = s .. "\n " .. l end
  return s
end

function m.init(ctx)
  ctx_ref = ctx
  DIR = ctx.sider_dir .. "content\\pesm-livepatch\\"
  ctx.register("key_down", m.key_down)
  ctx.register("overlay_on", m.overlay_on)
  for _, n in ipairs({ "players.txt", "teams.txt" }) do   -- the game has just loaded the files as they are: older patches are in them already
    local f = io.open(DIR .. n, "w")
    if f then f:close() end
  end
  log(string.format("PESM-LivePatch %s: ready (F7 in the overlay), ffi %s", m.version, RPM and "ok" or "MISSING"))
end

return m
