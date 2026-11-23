-- FCFL live patch (experiment): writes changed player attributes into the player table(s) of the RUNNING game, no restart.
-- Open the Sider overlay (Space), switch to this module with the 1 key. F6 = find the 380 byte player tables in memory (log only). F7 = apply <sider>\content\fcfl-livepatch\patch.txt to every table found.
-- patch.txt: one line per field "pid byte_offset bit_shift bit_width old new" (offsets of the 380 byte block), made by tools/livepatch_make.py.
-- A field is only written when memory holds `old` (so a wrong layout or an already patched player is skipped). Everything is logged with times.
local m = {}

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
local KEY_FIND, KEY_APPLY = 0x75, 0x76   -- F6 = find, F7 = apply
local BLOCK, IDOFF = 0x17C, 0x30
local ctx_ref
local RPM, REGIONS, FFI
local tables = {}   -- { base, count, live, index }
local LAST = {}     -- needle name -> first hit of the last F10 search

local last_msg = ""
local function out(s)
  last_msg = s
  log("fcfl_livepatch: " .. s)
end

do
  local ffi = ffi
  if ffi == nil and type(require) == "function" then local ok, r = pcall(require, "ffi"); if ok then ffi = r end end
  FFI = ffi
  if ffi then
    pcall(ffi.cdef, [[
      void* FP_GetCurrentProcess(void) __asm__("GetCurrentProcess");
      int FP_ReadProcessMemory(void* h, const void* a, void* b, size_t n, size_t* got) __asm__("ReadProcessMemory");
      typedef struct { void* BaseAddress; void* AllocationBase; uint32_t AllocationProtect; uint16_t PartitionId;
                       size_t RegionSize; uint32_t State; uint32_t Protect; uint32_t Type; } FP_MBI;
      size_t FP_VirtualQuery(const void* a, FP_MBI* b, size_t n) __asm__("VirtualQuery");
    ]])
    local okp, proc = pcall(function() return ffi.C.FP_GetCurrentProcess() end)
    if okp and proc then
      local cap, buf, got = 0x10000, nil, ffi.new("size_t[1]")
      buf = ffi.new("uint8_t[?]", cap)
      RPM = function(addr, len)   -- nil instead of a crash on a bad address
        if type(addr) ~= "number" or addr < 0x10000 or len <= 0 or len > 0x4000000 then return nil end
        if len > cap then cap = len; buf = ffi.new("uint8_t[?]", cap) end
        got[0] = 0
        local r = ffi.C.FP_ReadProcessMemory(proc, ffi.cast("const void*", addr), buf, len, got)
        if r == 0 or tonumber(got[0]) ~= len then return nil end
        return ffi.string(buf, len)
      end
      local mbi = ffi.new("FP_MBI[1]")
      REGIONS = function(min_size)
        local res, addr, sz = {}, 0x10000, ffi.sizeof("FP_MBI")
        while addr < 0x7FFFFFFF0000 and #res < 20000 do
          local r = ffi.C.FP_VirtualQuery(ffi.cast("const void*", addr), mbi, sz)
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

local function id_ok(id)
  return id >= 1 and id <= 1048575 or (id >= 0x10000000 and id < 0xF0000000 and math.floor(id / 1048576) % 256 == 0)
end

local function valid(addr)   -- a block: plausible id at +0x30 and a letter of the name at +0x38
  local b = RPM(addr + IDOFF, 0x20)
  return b ~= nil and id_ok(u32(b, 0)) and b:byte(9) >= 0x20
end

local function read_patch()
  local p = ctx_ref.sider_dir .. "content\\fcfl-livepatch\\patch.txt"
  local f = io.open(p, "r")
  if not f then return nil, "no patch file: " .. p end
  local lines = {}
  for l in f:lines() do
    local a, b, c, d, e, g = l:match("^(%d+) (%d+) (%d+) (%d+) (%d+) (%d+)")
    if a then lines[#lines + 1] = { tonumber(a), tonumber(b), tonumber(c), tonumber(d), tonumber(e), tonumber(g) } end
  end
  f:close()
  return lines
end

-- every table: start = walk back while valid, count = walk forward while valid; live = morale set (career copy), 0 = database copy
local function find_tables(pid)
  local t0 = os.clock()
  tables = {}
  if not RPM or not REGIONS then out("no ffi: cannot scan"); return end
  local needle = memory.pack("u32", pid)
  local regs = REGIONS(0x100000)
  out(string.format("scan: %d regions, looking for id %d", #regs, pid))
  local CH, seen = 0x400000, {}
  for _, rg in ipairs(regs) do
    local off = 0
    while off < rg[2] do
      local len = math.min(CH + 0x40, rg[2] - off)
      local s = RPM(rg[1] + off, len)
      if s then
        local init = 1
        while true do
          local h = s:find(needle, init, true)
          if not h then break end
          init = h + 1
          local base = rg[1] + off + h - 1 - IDOFF
          if base > 0x10000 and valid(base) and valid(base + BLOCK) and valid(base + 2 * BLOCK) then
            local a = base
            while valid(a - BLOCK) do a = a - BLOCK end
            if not seen[a] then
              seen[a] = true
              local n, b = 0, a
              while n < 1000000 and valid(b) do b = b + BLOCK; n = n + 1 end
              local live = 0
              for k = 0, math.min(n, 4000) - 1 do
                local x = RPM(a + k * BLOCK + 0x13E, 1)
                if x and x:byte(1) ~= 0 then live = live + 1 end
              end
              tables[#tables + 1] = { base = a, count = n, live = live }
              out(string.format("table @0x%X, %d players, morale set on %d of %d sampled (%s)", a, n, live, math.min(n, 4000), live > 0 and "career copy" or "database copy"))
            end
          end
        end
      end
      off = off + CH
    end
  end
  out(string.format("scan done: %d table(s) in %.2f s", #tables, os.clock() - t0))
end

local function build_index(t)
  local t0, idx, CH = os.clock(), {}, 0x20000 * BLOCK
  local k = 0
  while k < t.count do
    local n = math.min(t.count - k, 0x20000)
    local s = RPM(t.base + k * BLOCK, n * BLOCK)
    if not s then break end
    for i = 0, n - 1 do idx[u32(s, i * BLOCK + IDOFF)] = t.base + (k + i) * BLOCK end
    k = k + n
  end
  t.index = idx
  out(string.format("index of table @0x%X built in %.2f s", t.base, os.clock() - t0))
end

local function apply()
  local lines, err = read_patch()
  if not lines then out(err); return end
  if #lines == 0 then out("patch file is empty"); return end
  if #tables == 0 then find_tables(lines[1][1]) end
  local t0 = os.clock()
  for _, t in ipairs(tables) do
    if not t.index then build_index(t) end
    local done, same, bad, miss = 0, 0, 0, 0
    local t1 = os.clock()
    for _, L in ipairs(lines) do
      local pid, off, sh, w, old, new = L[1], L[2], L[3], L[4], L[5], L[6]
      local a = t.index[pid]
      if not a then miss = miss + 1
      else
        local b = RPM(a + off, 4)
        local blk = RPM(a + IDOFF, 4)
        if not b or not blk or u32(blk, 0) ~= pid then bad = bad + 1
        else
          local v = u32(b, 0)
          local f = math.floor(v / 2 ^ sh) % 2 ^ w
          if f == new then same = same + 1
          elseif f ~= old then bad = bad + 1; if bad <= 5 then out(string.format("skip pid %d off %d: memory holds %d, expected %d", pid, off, f, old)) end
          else
            local ok = pcall(memory.write, a + off, memory.pack("u32", v - f * 2 ^ sh + new * 2 ^ sh))
            if ok then done = done + 1 else bad = bad + 1 end
          end
        end
      end
    end
    out(string.format("table @0x%X (%s): %d written, %d already new, %d skipped (value differs), %d player(s) not in the table, %d lines in %.3f s",
        t.base, t.live > 0 and "career" or "database", done, same, bad, miss, #lines, os.clock() - t1))
  end
  out(string.format("apply done in %.2f s", os.clock() - t0))
end


-- Tables that sit in memory as an unchanged image of their database file (found by the F8 probe): PlayerAssignment, Tactics, TacticsFormation, Team, Competition,
-- CompetitionEntry. raw\\<name>.raw = decompressed file (the converter writes them after every change, or tools/export_raw.py).
-- F8 = look for the images and log how many rows are identical (reads only). F9 = write every row that differs from the new file into the image, then check.
local PROBES = { { "PlayerAssignment", 16 }, { "Tactics", 12 }, { "TacticsFormation", 12 }, { "Team", 1532 }, { "Competition", 36 }, { "CompetitionEntry", 12 } }

local function rows_same(mem, raw, n, rs)
  local same = 0
  for r = 0, n - 1 do
    local o = r * rs
    if mem:sub(o + 1, o + rs) == raw:sub(o + 1, o + rs) then same = same + 1 end
  end
  return same
end

-- returns items { name, rs, n, raw, images = { {base, mem, same} ... } } ; images = places in memory where the file is found (>= 50 % of the rows identical)
local function find_images()
  local t0 = os.clock()
  local dir = ctx_ref.sider_dir .. "content\\fcfl-livepatch\\raw\\"
  local items, needles = {}, {}
  for _, P in ipairs(PROBES) do
    local f = io.open(dir .. P[1] .. ".raw", "rb")
    if f then
      local raw = f:read("*a"); f:close()
      local rs, n = P[2], math.floor(#raw / P[2])
      local it = { name = P[1], rs = rs, n = n, raw = raw, hits = {}, images = {} }
      -- the module's own copy of the file (a Lua string) is found by the scan as well: remember where it is and leave it out
      it.own = {}
      local okp, pa = pcall(function() return tonumber(FFI.cast("uintptr_t", FFI.cast("const char*", raw))) end)
      if okp and pa then it.own[pa] = true; out(string.format("%s: the module's own copy of the file is @0x%X (left out)", P[1], pa)) end
      items[#items + 1] = it
      for _, fr in ipairs({ 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9 }) do   -- several samples: a row the converter just changed does not match
        local k = math.floor(n * fr)
        needles[#needles + 1] = { it = it, k = k, s = raw:sub(k * rs + 1, (k + 4) * rs) }
      end
    else
      out("no raw file for " .. P[1])
    end
  end
  local CH, OV = 0x400000, 0x2000
  local regs = REGIONS(0x1000)
  for _, rg in ipairs(regs) do
    local off = 0
    while off < rg[2] do
      local s = RPM(rg[1] + off, math.min(CH + OV, rg[2] - off))
      if s then
        for _, nd in ipairs(needles) do
          local init = 1
          while true do
            local h = s:find(nd.s, init, true)
            if not h then break end
            init = h + 1
            if h - 1 < CH and #nd.it.hits < 40 then nd.it.hits[#nd.it.hits + 1] = rg[1] + off + h - 1 - nd.k * nd.it.rs end
          end
        end
      end
      off = off + CH
    end
  end
  for _, it in ipairs(items) do
    local seen = {}
    for _, base in ipairs(it.hits) do
      if not seen[base] and base > 0x10000 and not it.own[base] then
        seen[base] = true
        local mem = RPM(base, it.n * it.rs)
        if mem then
          local same = rows_same(mem, it.raw, it.n, it.rs)
          if same * 2 >= it.n then it.images[#it.images + 1] = { base = base, same = same } end
        end
      end
    end
  end
  out(string.format("images searched in %d regions in %.2f s", #regs, os.clock() - t0))
  return items
end

local function probe()
  for _, it in ipairs(find_images()) do
    if #it.images == 0 then out("probe " .. it.name .. ": no image of the file in memory (the game converts it)") end
    for _, im in ipairs(it.images) do
      out(string.format("probe %s: image @0x%X, %d of %d rows identical to the file", it.name, im.base, im.same, it.n))
    end
  end
end

local function apply_tables()
  local t0 = os.clock()
  for _, it in ipairs(find_images()) do
    if #it.images == 0 then out(it.name .. ": no image found (not written)")
    else
      for _, im in ipairs(it.images) do
        local mem = RPM(im.base, it.n * it.rs)
        local w, bad = 0, 0
        if mem then
          for r = 0, it.n - 1 do
            local o = r * it.rs
            local row = it.raw:sub(o + 1, o + it.rs)
            if mem:sub(o + 1, o + it.rs) ~= row then
              if pcall(memory.write, im.base + o, row) then w = w + 1 else bad = bad + 1 end
            end
          end
        end
        local after = RPM(im.base, it.n * it.rs)
        local same = after and rows_same(after, it.raw, it.n, it.rs) or -1
        out(string.format("%s @0x%X: %d row(s) written, %d failed, now %d of %d rows identical to the file", it.name, im.base, w, bad, same, it.n))
      end
    end
  end
  out(string.format("tables done in %.2f s", os.clock() - t0))
end


-- F10: search the byte strings of content\\fcfl-livepatch\\needles.txt ("name hexbytes" per line, made by tools/make_needles.py) in the whole process and log the bytes around every hit,
-- to find out how the game keeps a table that is NOT an image of its file. Reads only. Hits with the same surroundings (copies) are listed once with their addresses.
local function hex(str) return (str:gsub(".", function(c) return string.format("%02x", c:byte()) end)) end

local function needles_search()
  local t0 = os.clock()
  local f = io.open(ctx_ref.sider_dir .. "content\\fcfl-livepatch\\needles.txt", "r")
  if not f then out("needles: no needles.txt"); return end
  local list = {}
  for l in f:lines() do
    local name, hx = l:match("^(%S+) (%x+)")
    if name then
      local b = hx:gsub("%x%x", function(h) return string.char(tonumber(h, 16)) end)
      list[#list + 1] = { name = name, s = b, hits = {}, own = nil }
      local okp, pa = pcall(function() return tonumber(FFI.cast("uintptr_t", FFI.cast("const char*", b))) end)
      if okp then list[#list].own = pa end
    end
  end
  f:close()
  collectgarbage()
  local CH, OV, BEF, AFT = 0x400000, 0x2000, 64, 160
  local regs = REGIONS(0x1000)
  for _, rg in ipairs(regs) do
    local off = 0
    while off < rg[2] do
      local s = RPM(rg[1] + off, math.min(CH + OV, rg[2] - off))
      if s then
        for _, nd in ipairs(list) do
          local init = 1
          while #nd.hits < 30 do
            local h = s:find(nd.s, init, true)
            if not h then break end
            init = h + 1
            if h - 1 < CH then
              local a = rg[1] + off + h - 1
              if a ~= nd.own then nd.hits[#nd.hits + 1] = a end
            end
          end
        end
      end
      off = off + CH
    end
  end
  for _, nd in ipairs(list) do
    out(string.format("needle %s (%d bytes): %d hit(s)", nd.name, #nd.s, #nd.hits))
    LAST[nd.name] = nd.hits[1]
    local groups, order = {}, {}
    for _, a in ipairs(nd.hits) do
      local ctx_bytes = RPM(a - BEF, BEF + AFT) or RPM(a, #nd.s) or ""
      local key = hex(ctx_bytes)
      if not groups[key] then groups[key] = { addrs = {} }; order[#order + 1] = key end
      groups[key].addrs[#groups[key].addrs + 1] = a
    end
    for gi, key in ipairs(order) do
      if gi > 6 then break end
      local g = groups[key]
      local al = {}
      for i = 1, math.min(#g.addrs, 4) do al[#al + 1] = string.format("0x%X", g.addrs[i]) end
      out(string.format("  context %d: %d copy(ies) @ %s  (hit is at byte %d)", gi, #g.addrs, table.concat(al, " "), BEF))
      for i = 1, #key, 64 do out("    " .. key:sub(i, i + 63)) end
    end
  end
  out(string.format("needles done in %.2f s", os.clock() - t0))
end


-- F11: write the memory around the first hit of fm_codes and squad_by_slot4 (from the last F10 search) to content\\fcfl-livepatch\\dump-<name>.bin for offline analysis.
-- The log line says the start address. 64 KB pieces that cannot be read are filled with zeros.
local function dump_around(name, before, size)
  local a = LAST[name]
  if not a then out("dump: no hit for " .. name .. " (press F10 first)"); return end
  local base = math.max(0x10000, a - before)
  local f = io.open(ctx_ref.sider_dir .. "content\\fcfl-livepatch\\dump-" .. name .. ".bin", "wb")
  if not f then out("dump: cannot write the file"); return end
  local bad, PIECE = 0, 0x10000
  for o = 0, size - 1, PIECE do
    local s = RPM(base + o, PIECE)
    if s then f:write(s) else f:write(string.rep("\0", PIECE)); bad = bad + 1 end
  end
  f:close()
  out(string.format("dump %s: start 0x%X, hit at 0x%X (offset %d), %d bytes, %d unreadable piece(s)", name, base, a, a - base, size, bad))
end


-- F12: write squad order, shirt numbers and formations of teams into the team objects of the game (teams.txt, tools/team_patch_make.py).
-- Team object of rank r: base + r*1680; 40 x (pid u32, u32) at +0; 40 x u16 shirt numbers at +330; formation 1 / 2 (99 bytes) at +784 / +944.
-- The base is found from the "LOC" team (not patched): its first formation block is searched, base = hit - 784 - rank*1680. A candidate base is only accepted if the squad
-- of the first patched team in memory has the same players as the patch (only the order may change); otherwise nothing is written.
local TOBJ, SQ, NUM, FM1, FM2 = 1680, 0, 330, 784, 944

local function team_patch()
  local t0 = os.clock()
  local f = io.open(ctx_ref.sider_dir .. "content\\fcfl-livepatch\\teams.txt", "r")
  if not f then out("teams: no teams.txt"); return end
  local loc, T, N, FMS = nil, {}, {}, {}
  for l in f:lines() do
    local kind, rest = l:match("^(%a+) (.*)$")
    if kind == "LOC" then
      local r, hx = rest:match("^(%d+) (%x+)")
      loc = { rank = tonumber(r), s = hx:gsub("%x%x", function(h) return string.char(tonumber(h, 16)) end) }
    elseif kind == "T" or kind == "N" then
      local r, tail = rest:match("^(%d+) ?(.*)$")
      local v = {}
      for x in tail:gmatch("%d+") do v[#v + 1] = tonumber(x) end
      (kind == "T" and T or N)[tonumber(r)] = v
    elseif kind == "F" then
      local r, w, hx = rest:match("^(%d+) (%d) (%x+)")
      FMS[#FMS + 1] = { rank = tonumber(r), which = tonumber(w), s = hx:gsub("%x%x", function(h) return string.char(tonumber(h, 16)) end) }
    end
  end
  f:close()
  if not loc then out("teams: no LOC line"); return end
  local hits = {}
  local CH, OV = 0x400000, 0x2000
  for _, rg in ipairs(REGIONS(0x1000)) do
    local off = 0
    while off < rg[2] and #hits < 12 do
      local s = RPM(rg[1] + off, math.min(CH + OV, rg[2] - off))
      if s then
        local init = 1
        while #hits < 12 do
          local h = s:find(loc.s, init, true)
          if not h then break end
          init = h + 1
          if h - 1 < CH then hits[#hits + 1] = rg[1] + off + h - 1 end
        end
      end
      off = off + CH
    end
  end
  out(string.format("teams: %d candidate(s) for the base, scan %.2f s", #hits, os.clock() - t0))
  local firstrank
  for r in pairs(T) do if not firstrank or r < firstrank then firstrank = r end end
  local base
  for _, h in ipairs(hits) do
    local b = h - FM1 - loc.rank * TOBJ
    local mem = RPM(b + firstrank * TOBJ + SQ, 40 * 8)
    if mem then
      local want, have = {}, {}
      for _, p in ipairs(T[firstrank]) do want[p] = true end
      local ok, n = true, 0
      for j = 0, 39 do
        local p = u32(mem, j * 8)
        if p ~= 0 then n = n + 1; if not want[p] then ok = false end end
      end
      if ok and n == #T[firstrank] then base = b; break end
    end
  end
  if not base then out("teams: no candidate base fits the squad of the first team (nothing written)"); return end
  out(string.format("teams: base 0x%X", base))
  local wrote, skipped = 0, 0
  for r, pids in pairs(T) do
    local o = base + r * TOBJ
    local mem = RPM(o + SQ, 40 * 8)
    local want, ok = {}, mem ~= nil
    for _, p in ipairs(pids) do want[p] = true end
    if ok then
      local n = 0
      for j = 0, 39 do
        local p = u32(mem, j * 8)
        if p ~= 0 then n = n + 1; if not want[p] then ok = false end end
      end
      if n ~= #pids then ok = false end
    end
    if not ok then skipped = skipped + 1; out(string.format("team rank %d skipped: the squad in memory differs from the patch", r))
    else
      for j, p in ipairs(pids) do pcall(memory.write, o + SQ + (j - 1) * 8, memory.pack("u32", p)) end
      if N[r] then for j, n in ipairs(N[r]) do pcall(memory.write, o + NUM + (j - 1) * 2, memory.pack("u16", n)) end end
      wrote = wrote + 1
    end
  end
  for _, fm in ipairs(FMS) do
    local o = base + fm.rank * TOBJ + (fm.which == 1 and FM1 or FM2)
    if T[fm.rank] and #fm.s == 99 then pcall(memory.write, o, fm.s) end
  end
  out(string.format("teams: %d team(s) written, %d skipped, %d formation block(s) in %.2f s", wrote, skipped, #FMS, os.clock() - t0))
end

function m.key_down(ctx, vkey)
  vkey = tonumber(vkey)
  if vkey == KEY_FIND then
    local lines = read_patch()
    if not lines or #lines == 0 then out("need a patch file (its first player id is searched)"); return end
    find_tables(lines[1][1])
  elseif vkey == 0x77 then   -- F8
    local ok, e = pcall(probe)
    if not ok then out("ERROR " .. tostring(e)) end
  elseif vkey == 0x7B then   -- F12
    local ok, e = pcall(team_patch)
    if not ok then out("ERROR " .. tostring(e)) end
  elseif vkey == 0x7A then   -- F11
    local ok, e = pcall(function() dump_around("fm_codes", 0x80000, 0x400000); dump_around("squad_by_slot4", 0x80000, 0x400000) end)
    if not ok then out("ERROR " .. tostring(e)) end
  elseif vkey == 0x79 then   -- F10
    local ok, e = pcall(needles_search)
    if not ok then out("ERROR " .. tostring(e)) end
  elseif vkey == 0x78 then   -- F9
    local ok, e = pcall(apply_tables)
    if not ok then out("ERROR " .. tostring(e)) end
  elseif vkey == KEY_APPLY then
    local ok, e = pcall(apply)
    if not ok then out("ERROR " .. tostring(e)) end
  end
end

-- Sider only delivers key_down while the overlay (Space) is on and this module is the one shown (switch with the 1 key)
function m.overlay_on(ctx)
  return string.format(" FCFL live patch  [F6] find tables  [F7] apply patch  [F8] probe tables  [F9] apply tables  [F10] needles  [F11] dump  [F12] team patch\n %s", last_msg)
end

function m.init(ctx)
  ctx_ref = ctx
  ctx.register("key_down", m.key_down)
  ctx.register("overlay_on", m.overlay_on)
  out(string.format("ready (F6 = find tables, F7 = apply patch), ffi %s", RPM and "ok" or "MISSING"))
end

return m
