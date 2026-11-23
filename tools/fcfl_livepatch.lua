-- FCFL live patch (experiment): writes changed player attributes into the player table(s) of the RUNNING game, no restart.
-- ScrollLock = find the 380 byte player tables in memory (log only). Pause = apply <sider>\content\fcfl-livepatch\patch.txt to every table found.
-- patch.txt: one line per field "pid byte_offset bit_shift bit_width old new" (offsets of the 380 byte block), made by tools/livepatch_make.py.
-- A field is only written when memory holds `old` (so a wrong layout or an already patched player is skipped). Everything is logged with times.
local m = {}
local KEY_FIND, KEY_APPLY = 0x91, 0x13
local BLOCK, IDOFF = 0x17C, 0x30
local ctx_ref
local RPM, REGIONS
local tables = {}   -- { base, count, live, index }

local function out(s)
  log("fcfl_livepatch: " .. s)
end

do
  local ffi = ffi
  if ffi == nil and type(require) == "function" then local ok, r = pcall(require, "ffi"); if ok then ffi = r end end
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

function m.key_down(ctx, vkey)
  vkey = tonumber(vkey)
  if vkey == KEY_FIND then
    local lines = read_patch()
    if not lines or #lines == 0 then out("need a patch file (its first player id is searched)"); return end
    find_tables(lines[1][1])
  elseif vkey == KEY_APPLY then
    local ok, e = pcall(apply)
    if not ok then out("ERROR " .. tostring(e)) end
  end
end

function m.init(ctx)
  ctx_ref = ctx
  ctx.register("key_down", m.key_down)
  out(string.format("ready (ScrollLock = find tables, Pause = apply patch), ffi %s", RPM and "ok" or "MISSING"))
end

return m
