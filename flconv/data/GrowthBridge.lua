-- GrowthBridge.lua (Karijera 26)
-- Applies training/growth from the app (bridge\growth.csv) to player attributes, form and affection in game memory.
-- How to use: press F7 in PlayerDump once per game launch, then switch the Sider overlay (Space, then 1) to "GrowthBridge".
--   AUTO: while GrowthBridge is shown in the overlay, new commands from the app are applied within ~5 s. F6 = apply now.
-- SAFETY: without bridge\growth.enabled (the "Enable live writes" switch in the app) it runs in TEST MODE:
--   it only logs what it would do (growth-result.csv status "dry"), nothing is written.
-- Result: bridge\growth-result.csv (txid,status,old,new)  status: ok | dry | skip:<reason>
local m = { version = "1.27" }
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

local BRIDGE = "content\\ml-immersion\\bridge\\"
local F_CMD, F_ON, F_APPLIED, F_RESULT, F_LOG = BRIDGE .. "growth.csv", BRIDGE .. "growth.enabled",
    BRIDGE .. "growth-applied.txt", BRIDGE .. "growth-result.csv", BRIDGE .. "growth.log"
local BLOCK = 0x17C
local KEY_F6 = 0x75
local SEEDS = { "E. Haaland", "M. Salah", "L. Messi", "K. Mbapp", "V. van Dijk", "K. De Bruyne", "R. Lewandowski", "Neymar" }
local MAX_PER_RUN, MAX_STEP = 3000, 3

-- polje = {off, shift, len, min, max}
local FIELDS = {
    OffensiveAwareness = {0x03, 0, 7, 40, 99}, BallControl = {0x06, 5, 7, 40, 99}, Dribbling = {0x05, 6, 7, 40, 99},
    TightPossession = {0x08, 0, 7, 40, 99}, Finishing = {0x08, 7, 7, 40, 99}, LowPass = {0x09, 6, 7, 40, 99},
    LoftedPass = {0x0A, 5, 7, 40, 99}, Heading = {0x0C, 0, 7, 40, 99}, PlaceKicking = {0x0E, 5, 7, 40, 99},
    Curl = {0x10, 0, 7, 40, 99}, Speed = {0x14, 7, 7, 40, 99}, Acceleration = {0x18, 7, 7, 40, 99},
    KickingPower = {0x18, 0, 7, 40, 99}, Jump = {0x19, 6, 7, 40, 99}, PhysicalContact = {0x15, 6, 7, 40, 99},
    Balance = {0x16, 5, 7, 40, 99}, Stamina = {0x1A, 5, 7, 40, 99}, DefensiveAwareness = {0x04, 0, 7, 40, 99},
    BallWinning = {0x0C, 7, 7, 40, 99}, Aggression = {0x0D, 6, 7, 40, 99}, GKAwareness = {0x04, 7, 7, 40, 99},
    GKCatching = {0x10, 7, 7, 40, 99}, GKClearing = {0x11, 6, 7, 40, 99}, GKReflexes = {0x12, 5, 7, 40, 99},
    GKReach = {0x14, 0, 7, 40, 99},
    Form = {0x17, 4, 3, 0, 7}, Affection = {0x13E, 2, 7, 0, 100, true},
    Injury = {0x148, 0, 8, 0, 255},   -- patch verletzungen: injury days (the game counts them down by itself)
}
-- profile of the player (written by the FCFL Stats Converter): skills / COM styles = 1 bit (B<bit>), positions = 2 bit 0..2 (P<bit>), playing style (Style, 0..21).
--      The bit numbers are the ones of the 380 byte block of the player (the same as in the Gaffer dump); only these bits can be written.
for _, k in ipairs({291,292,293,294,295,296,297,298,300,301,302,303,304,305,306,308,309,310,311,312,313,314,315,316,318,320,322,323,324,325,327,328,329,330,331,
                    223,255,286,287,288,289,290}) do
    FIELDS["B" .. k] = {math.floor(k / 8), k % 8, 1, 0, 1}
end
for _, l in ipairs({274,268,270,272,260,262,264,266,258,253,256,251,249}) do
    FIELDS["P" .. l] = {math.floor(l / 8), l % 8, 2, 0, 2}
end
FIELDS.Style = {0x1D, 3, 5, 0, 21}
-- body data (fields of the 380 byte block, found by comparing the dump with Player.bin): height in cm (byte 0), weight in kg (byte 1), foot 0 right / 1 left (bit 191), weak foot use (bit 280) and accuracy (bit 276), 0..3 = 1..4
FIELDS.Height = {0, 0, 8, 100, 220}; FIELDS.Weight = {1, 0, 8, 30, 157}; FIELDS.Foot = {23, 7, 1, 0, 1}; FIELDS.WeakUse = {35, 0, 2, 0, 3}; FIELDS.WeakAcc = {34, 4, 2, 0, 3}
-- 1.2: morale is 7 bits at +0x13E bit 2 (0-100 in game); bits 0-1 are other flags and are left alone.
--      The app still sends Affection on its own 0-255 scale: 'set' is mapped to game points, 'add' is scaled (3 app = 1 point).
local MP = { {0, 0}, {15, 40}, {30, 50}, {55, 70}, {100, 100} }   -- app percent -> game morale
local function aff_game(v)
    local p = math.max(0, math.min(100, v / 2.55))
    for i = 2, #MP do
        local a, b = MP[i - 1], MP[i]
        if p <= b[1] then return math.floor(a[2] + (p - a[1]) / (b[1] - a[1]) * (b[2] - a[2]) + 0.5) end
    end
    return 100
end
local function aff_step(v)
    if v == 0 then return 0 end
    local n = math.max(1, math.floor(math.abs(v) / 3 + 0.5))
    if v < 0 then return -n end
    return n
end

local ctx_ref
local INIT_TIME = os.time()
local META_COUNT = 0
local applied, seen = {}, {}
local index, index_base, index_n = nil, nil, 0
local last_run, last_msg = 0, "GrowthBridge: training from the app is applied here (F6 = apply now)"
local stride = BLOCK

local function path(rel) return ctx_ref.sider_dir .. rel end

local quiet = false
local function log(s)
    last_msg = s
    if quiet then return end
    local f = io.open(path(F_LOG), "a")
    if f then f:write(os.date("%Y-%m-%d %H:%M:%S  ") .. s .. "\n"); f:close() end
end

local function file_exists(p) local f = io.open(p, "r"); if f then f:close(); return true end return false end

-- 1.9: citanje preko ReadProcessMemory (LuaJIT ffi), kao PlayerDump 1.5+: losa adresa vrati nil umjesto rusenja igre
--      (memory.read na neispravnoj adresi je access violation koji pcall ne hvata). Bez ffi ostaje staro citanje.
local GB_RPM = nil
do
    local ffi = ffi
    if ffi == nil and type(require) == "function" then
        local okr, r = pcall(require, "ffi")
        if okr then ffi = r end
    end
    if type(ffi) == "table" or type(ffi) == "userdata" then
        pcall(ffi.cdef, [[
            void* GB_GetCurrentProcess(void) __asm__("GetCurrentProcess");
            int GB_ReadProcessMemory(void* hProcess, const void* lpBaseAddress, void* lpBuffer, size_t nSize, size_t* lpNumberOfBytesRead) __asm__("ReadProcessMemory");
        ]])
        local okp, proc = pcall(function() return ffi.C.GB_GetCurrentProcess() end)
        if okp and proc then
            local cap = 0x10000
            local buf = ffi.new("uint8_t[?]", cap)
            local got = ffi.new("size_t[1]")
            GB_RPM = function(addr, len)
                -- 64-bitni broj iz memory.unpack / adresa iz memory.get_process_info je u LuaJIT-u cdata (int64 ili pokazivac).
                -- tonumber(pokazivac) vraca nil, pa je ReadProcessMemory uvijek odbio lanac stanja igre (logovi testera 4.11.:
                -- "first read via memory.read (rpm=true, addr type=cdata)") -> cast u uint64 pa broj.
                if type(addr) == "cdata" then
                    local okc, n = pcall(function() return tonumber(ffi.cast("uint64_t", addr)) end)
                    addr = okc and n or addr
                else
                    addr = tonumber(addr) or addr
                end
                if type(addr) ~= "number" or addr < 0x10000 or len <= 0 or len > 0x4000000 then return nil end
                if len > cap then cap = len; buf = ffi.new("uint8_t[?]", cap) end
                got[0] = 0
                local r = ffi.C.GB_ReadProcessMemory(proc, ffi.cast("const void*", addr), buf, len, got)
                if r == 0 or tonumber(got[0]) ~= len then return nil end
                return ffi.string(buf, len)
            end
        end
    end
end

local function safe_read(addr, len)
    if GB_RPM then
        local okr, res = pcall(GB_RPM, addr, len)
        if okr then return res end
    end
    local ok, res = pcall(memory.read, addr, len)
    if ok and res and #res == len then return res end
    return nil
end

local function u32(s, off) return memory.unpack("u32", s:sub(off + 1, off + 4)) end

-- 1.6: je li igra u Master Ligi ili u glavnom izborniku (za The Gaffer: upis bez klika "I am on the main menu").
-- Lanac (tester, FL26 + FL27): u64 [exe + 0x3705E10] -> objekt; u64 [objekt + 0x48] -> tablica; [tablica + 0x1642A24] datum
-- (u16 godina, u8 mjesec, u8 dan). U ML-u valjan datum, u izborniku 65535-00-00, prije prvog ucitavanja objekt = 0.
-- Samo citanje; bridge\game_state.txt se pise samo kad se stanje promijeni: "stanje sesija vrijeme_promjene vidio_ml datum".
local F_STATE = BRIDGE .. "game_state.txt"
local gs_t, gs_last, gs_seen_ml, gs_base = -100, nil, 0, nil
local function exe_base()
    if gs_base then return gs_base end
    local b = 5 * 2 ^ 30   -- 0x140000000 (64-bitni heks literal se u nekim Lua verzijama sijece)
    local ok, info = pcall(memory.get_process_info)
    if ok and type(info) == "table" then b = info.base or info.base_address or b end
    gs_base = b
    return b
end
-- 1.10: lanac stanja igre se cita kao u 1.8 (memory.read) ako ReadProcessMemory ne uspije (1.9: stanje je uvijek bilo
--       'unknown', pa app nije sam vidio glavni izbornik). Prvi put se u log zapise koji je nacin radio.
local st_diag = false
local function st_read(addr, len)
    -- 1.11: memory.read se NE koristi kad ReadProcessMemory postoji i vrati nil: to znaci da adresa nije citljiva
    --       (pri ulasku u Master League lanac kratko pokazuje na oslobodjenu memoriju), a memory.read na takvoj adresi
    --       srusi igru (pcall to ne hvata). Korisnici 4.11.: pad pri ulasku u ML s 1.10. Bez ffi ostaje staro citanje (1.8).
    local r = safe_read(addr, len)
    local how = r and "rpm" or "failed"
    if not st_diag then
        st_diag = true
        log(string.format("game state: first read via %s (rpm=%s, addr type=%s)", how, tostring(GB_RPM ~= nil), type(addr)))
    end
    return r
end
-- 1.23 (pc510x, FL Mod Studio svijet s 2400 klubova): na tbl+0x1642A24 su nule, datum je pomaknut (izmjereno tbl+0x1789478).
-- Struktura kalendara (u32): [-12] pocetak sezone, [-8] mali broj, [-4] prethodni datum, [0] danasnji datum.
-- Ako standardno mjesto nema ni datum ni 65535-00-00, potrazi se ta struktura (samo ReadProcessMemory, nikad memory.read),
-- a pomak se zapamti u bridge\date_off.txt.
local F_DOFF = BRIDGE .. "date_off.txt"
local DOFF, DOFF_LOADED, DOFF_T, DOFF_N = nil, false, -100, 0
local function dval(s, o)
    local y = memory.unpack("u16", s:sub(o + 1, o + 2))
    local mo, dd = s:byte(o + 3), s:byte(o + 4)
    if y >= 2000 and y <= 2200 and mo >= 1 and mo <= 12 and dd >= 1 and dd <= 31 then return y * 10000 + mo * 100 + dd end
    return nil
end
local function ok_or_home(s)
    if not s or #s < 4 then return false end
    if dval(s, 0) then return true end
    return memory.unpack("u16", s:sub(1, 2)) == 65535 and s:byte(3) == 0 and s:byte(4) == 0
end
local function doff_scan(tbl)
    if not GB_RPM then return nil end
    local found, n = nil, 0
    local CH = 0x100000
    for c = 0x1500000, 0x2600000 - 1, CH do
        local raw = safe_read(tbl + c - 16, CH + 16)
        if raw then
            local p = 17
            while true do
                local i = raw:find("[\7\8][\1-\12][\1-\31]", p)
                if not i then break end
                local o = i - 2                      -- pocetak u32 (0-based)
                if o >= 16 and o % 4 == 0 and o + 4 <= #raw then
                    local cur, prev, st = dval(raw, o), dval(raw, o - 4), dval(raw, o - 12)
                    if cur and prev and st and st <= prev and prev <= cur and math.floor(cur / 10000) - math.floor(st / 10000) <= 1
                       and memory.unpack("u32", raw:sub(o - 7, o - 4)) < 400 then
                        n = n + 1
                        found = c - 16 + o
                    end
                end
                p = i + 1
            end
        end
    end
    if n == 1 then return found end
    return nil
end
local function date_off(tbl)
    local d = st_read(tbl + 0x1642A24, 4)
    if ok_or_home(d) then return 0x1642A24 end
    if not DOFF_LOADED then
        DOFF_LOADED = true
        local f = io.open(path(F_DOFF), "r")
        if f then DOFF = tonumber(f:read("*l") or ""); f:close() end
    end
    if DOFF and ok_or_home(st_read(tbl + DOFF, 4)) then return DOFF end
    -- 1.26 (jubileu009: trzanje u utakmici i s 1.25, s verzijom iz pc506 glatko): pretraga cita ~17 MB memorije, a pokretala se
    -- svakih 20 s kad standardno mjesto nije datum - sto u utakmici zna biti i na obicnom svijetu. Sada samo kad su tamo nule
    -- (Mod Studio svijet), najvise 3 puta po pokretanju igre.
    if not d or d ~= "\0\0\0\0" or DOFF_N >= 3 then return 0x1642A24 end
    local now = os.clock()
    if now - DOFF_T > 20 then
        DOFF_T = now
        DOFF_N = DOFF_N + 1
        local okf, f_ = pcall(doff_scan, tbl)
        if okf and f_ then
            DOFF = f_
            local f = io.open(path(F_DOFF), "w")
            if f then f:write(string.format("%d\n", f_)); f:close() end
            log(string.format("game state: date found at table+0x%X (Mod Studio world)", f_))
            return f_
        end
    end
    return 0x1642A24
end
local function read_state()
    local s = st_read(exe_base() + 0x3705E10, 8)
    if not s then return "unknown", "" end
    local obj = memory.unpack("u64", s)
    if obj == 0 then return "null", "" end
    local t = st_read(obj + 0x48, 8)
    if not t then return "unknown", "" end
    local tbl = memory.unpack("u64", t)
    if tbl == 0 then return "unknown", "" end
    local d = st_read(tbl + date_off(tbl), 4)
    if not d then return "unknown", "" end
    local y, mo, dd = memory.unpack("u16", d:sub(1, 2)), d:byte(3), d:byte(4)
    if y >= 2000 and y <= 2200 and mo >= 1 and mo <= 12 and dd >= 1 and dd <= 31 then
        return "ml", string.format("%d-%02d-%02d", y, mo, dd)
    end
    if y == 65535 and mo == 0 and dd == 0 then return "home", "" end
    return "unknown", string.format("%d-%d-%d", y, mo, dd)
end
local function state_tick(force)
    local now = os.clock()
    if not force and now - gs_t < 1 then return end
    gs_t = now
    local ok, st, dt = pcall(read_state)
    if not ok then st, dt = "error", "" end
    if st == "ml" then gs_seen_ml = 1 end
    if st ~= gs_last or force then
        gs_last = st
        local f = io.open(path(F_STATE), "w")
        if f then f:write(string.format("%s %d %d %d %s\n", st, INIT_TIME, os.time(), gs_seen_ml, dt or "")); f:close() end
    end
end
function m.make_key(ctx, filename)
    pcall(state_tick)
    return nil
end
-- 1.7: pri izlasku iz ML-a u glavni izbornik igra cesto ne ucita nijednu datoteku; stanje se osvjezi i na pritisak
-- kontrolera i u izbornicima (isti obrazac kao Micheleov injuries_for_all: funkcija modula, samo vrati nil).
-- (1.7 prva verzija s livecpk_data_ready je srusila igru; ta i get_filepath se vise ne koriste.)
function m.gamepad_input(ctx)
    pcall(state_tick)
    return nil
end
function m.get_stadium_name(ctx)
    pcall(state_tick)
    return nil
end

-- 1.22 (pc510k): valjan ID igraca. Obicni do 2^20; patchevi stavljaju oznaku u gornja 4 bita (GOGOSZ 0x40000000+n),
-- pa vrijedi svaki takav oblik (bitovi 20-27 nula) - iduci patch s drugom oznakom radi bez nove verzije.
local function id_ok(id)
    if not id then return false end
    if id >= 1 and id <= 1048575 then return true end
    return id >= 0x10000000 and id < 0xF0000000 and math.floor(id / 1048576) % 256 == 0
end

local function valid(addr)
    local blk = safe_read(addr + 0x30, 0x20)
    if not blk then return false end
    local id = u32(blk, 0)
    if not id_ok(id) then return false end
    local c = blk:byte(9)
    return c ~= nil and c >= 0x20
end

local function detect_stride(base)
    for s = 0x17C, 0x400, 4 do
        if valid(base + s) and valid(base + 2 * s) and valid(base + 3 * s) then return s end
    end
    return nil
end

-- 1) adresa tablice iz players_dump.meta (zadnji F7 u OVOM pokretanju igre; stara adresa se odbaci provjerom)
-- tonumber(x,16) u ovom Lua-u siece na 32 bita (4294967295) -> rucno parsiranje
local function hex(h)
    local v = 0
    for c in h:gmatch(".") do v = v * 16 + tonumber(c, 16) end
    return v
end

local function base_from_meta()
    log("meta: opening")
    local f = io.open(path(BRIDGE .. "players_dump.meta"), "r")
    if not f then log("meta: file not found"); return nil end
    local t = f:read("*a") or ""
    f:close()
    local fa = t:match("first_addr=0x(%x+)")
    local st = t:match("stride=0x(%x+)")
    local wr = tonumber(t:match("written=(%d+)") or "0")
    META_COUNT = tonumber(t:match("count=(%d+)") or "0")
    log(string.format("meta: first=%s stride=%s count=%d written=%d init=%d", tostring(fa), tostring(st), META_COUNT, wr, INIT_TIME))
    if not fa or not st or wr < INIT_TIME then log("meta: old or incomplete, skipping"); return nil end
    local base = hex(fa)
    local s = hex(st)
    if base < 0x100000000 or base > 0x7FFFFFFFFFFF or s < 0x100 or s > 0x1000 then log("meta: address out of range"); return nil end
    log(string.format("meta: checking first block @%.0f", base))
    if not valid(base) then log("meta: first block is not valid"); return nil end
    log("meta: first block valid, checking the second")
    if not valid(base + s) then log("meta: second block is not valid"); return nil end
    log("meta: ok")
    return base, s
end

local function find_base()
    return base_from_meta()
end

-- 1.3: is this the live career table? The game also keeps a database copy of the player table (same layout, morale 0
--      everywhere). After some game actions the address from the last F7 can hold that copy; writing there changes nothing
--      the player sees. The career table has morale (+0x13E, bits 2-8) set on almost every player.
local function live_ok(base, s, n)
    local tot, live = 0, 0
    local k = 0
    while k < math.min(n or 0, 3000) do
        local d = safe_read(base + k * s + 0x13E, 2)
        if d then
            tot = tot + 1
            if math.floor((d:byte(1) + d:byte(2) * 256) / 4) % 128 ~= 0 then live = live + 1 end
        end
        k = k + 5
    end
    return tot > 0 and live >= tot * 0.3, live, tot
end

-- gradi mapu id -> adresa bloka (jednom; provjerava se prije svakog upisa)
local function build_index()
    log("step 1: looking for the player table from meta")
    local base, s = find_base()
    if base then log(string.format("step 2: table @0x%X stride 0x%X blocks %d", base, s, META_COUNT)) end
    if not base then return false, "player table not found: press F7 in PlayerDump first, then F6" end
    stride = s
    local first, n = base, 0
    index, index_n = {}, 0
    local a = first
    while index_n < math.min(META_COUNT, 1000000) and valid(a) do   -- 1.24: bez granice od 60.000 (Mod Studio baza ima >50.000 igraca)
        local blk = safe_read(a + 0x30, 4)
        if blk then index[u32(blk, 0)] = a end
        a = a + stride; index_n = index_n + 1
    end
    index_base = first
    local ok_, lv_, tt_ = live_ok(first, stride, index_n)
    if not ok_ then
        index = nil
        log(string.format("the table from the last F7 is not the career table (morale on %d of %d): press F7 in PlayerDump again", lv_, tt_))
        return false, "not the career table: press F7 in PlayerDump again"
    end
    log(string.format("player index: %d blocks, stride 0x%X, first @0x%X", index_n, stride, first))
    return true
end

local batch_fail = nil   -- 1.9: u jednoj obradi tablica se trazi najvise jednom (prije: novo trazenje za svaku naredbu, igra stala)
local function addr_of(pid)
    if not index then
        if batch_fail then return nil, batch_fail end
        local ok, err = build_index()
        if not ok then batch_fail = err or "table not found"; return nil, err end
    end
    local a = index[pid]
    if not a then return nil, "player not in the table" end
    local blk = safe_read(a + 0x30, 4)
    if not blk or u32(blk, 0) ~= pid then   -- tablica se pomaknula
        index = nil
        if batch_fail then return nil, batch_fail end
        local ok, err = build_index()
        if not ok then batch_fail = err or "table not found"; return nil, err end
        a = index[pid]
        if not a then return nil, "player not in the table" end
    end
    return a
end

local function get_field(a, f)
    local d = safe_read(a + f[1], 4)
    if not d then return nil end
    local v = memory.unpack("u32", d)
    return math.floor(v / (2 ^ f[2])) % (2 ^ f[3])
end

local function set_field(a, f, val)
    local d = safe_read(a + f[1], 4)
    if not d then return false end
    local cur = memory.unpack("u32", d)
    local low, high = 2 ^ f[2], 2 ^ (f[2] + f[3])
    local final = (cur % low) + (math.floor(cur / high) * high) + ((val % (2 ^ f[3])) * low)
    memory.write(a + f[1], memory.pack("u32", final))
    local chk = get_field(a, f)
    return chk == val
end

local function load_applied()
    local f = io.open(path(F_APPLIED), "r")
    if not f then return end
    for line in f:lines() do line = line:gsub("%s+", ""); if line ~= "" then applied[line] = true end end
    f:close()
end

local function remember(tx)
    applied[tx] = true
    if tx:sub(1, 4) == "fldb" then return end   -- 'set' commands of the converter are idempotent, they need no entry in the (slow to load) list
    local f = io.open(path(F_APPLIED), "a")
    if f then f:write(tx .. "\n"); f:close() end
end

local function split(line)
    local out = {}
    for p in (line .. ","):gmatch("([^,]*),") do out[#out + 1] = p:gsub("^%s+", ""):gsub("%s+$", "") end
    return out
end

local function process(force)
    -- 1.3: the table can move after F7 (game menus, saving): check it again before every batch
    if index and index_base and not live_ok(index_base, stride, index_n) then
        index = nil
        log("player table changed since F7: rebuilding")
    end
    local f = io.open(path(F_CMD), "r")
    if not f then return end
    local blob = f:read("*a") or ""
    f:close()
    -- 1.9: zadnji red bez kraja retka app mozda jos pise: preskoci ga (procita se iduci put cijeli)
    if blob ~= "" and not blob:find("[\r\n]$") then blob = blob:match("^(.*[\r\n])") or "" end
    batch_fail = nil
    local live = file_exists(path(F_ON))
    if force then seen = {} end
    local res, n, done = {}, 0, 0
    for line in blob:gmatch("[^\r\n]+") do
        line = line:gsub("^%s+", "")
        if line ~= "" and line:sub(1, 1) ~= "#" then
            local r = split(line)
            local tx, pid, field, op, val = r[1], tonumber(r[2]), r[3], r[4], tonumber(r[5])
            if tx and tx ~= "" and not applied[tx] and not seen[tx] and n < MAX_PER_RUN then
                n = n + 1
                seen[tx] = true
                local fd = FIELDS[field or ""]
                if not pid or not fd or not val or (op ~= "add" and op ~= "set") then
                    res[#res + 1] = tx .. ",skip:invalid command,,"
                    remember(tx)
                else
                    local a, err = addr_of(pid)
                    if not a then
                        res[#res + 1] = tx .. ",skip:" .. tostring(err) .. ",,"   -- ne pamti se: pokusat ce opet
                    else
                        local old = get_field(a, fd)
                        if old == nil then
                            res[#res + 1] = tx .. ",skip:read failed,,"
                        else
                            local new = val
                            if fd[6] then val = (op == "add") and aff_step(val) or aff_game(val); new = val end
                            local cap = fd[6] and 12 or MAX_STEP   -- 1.9: moral (bodovi igre 0-100) ima svoju granicu; prije je i +8 postalo +3
                            if op == "add" then new = old + math.max(-cap, math.min(cap, val)) end
                            new = math.max(fd[4], math.min(fd[5], new))
                            if not live then
                                res[#res + 1] = string.format("%s,dry,%d,%d", tx, old, new)
                            elseif set_field(a, fd, new) then
                                res[#res + 1] = string.format("%s,ok,%d,%d", tx, old, new)
                                remember(tx); done = done + 1
                            else
                                res[#res + 1] = string.format("%s,skip:write not confirmed,%d,%d", tx, old, new)
                            end
                        end
                    end
                end
            end
        end
    end
    if #res > 0 then
        local o = io.open(path(F_RESULT), "a")
        if o then o:write(table.concat(res, "\n") .. "\n"); o:close() end
        log(string.format("processed %d commands (%s), written %d", #res, live and "LIVE" or "TEST MODE", done))
    end
end

-- v0.9: AUTO = kad app posalje nove naredbe i igra je UZIVO (growth.enabled), modul ih sam primijeni (bez F6).
-- Uvjet: u ovom pokretanju igre je jednom pritisnut F7 (inace nema valjane tablice igraca) - tada samo javlja u overlayu.
-- Pokrece se iz overlay_on i iz key_down (bilo koja tipka), najvise svakih 5 s.
local AUTO = true
local last_auto, auto_tried, auto_wait = -100, {}, 0

local pc_sz, pc_n = -1, -1
local function pending_count()
    local f = io.open(path(F_CMD), "r")
    if not f then return 0 end
    -- 1.1: datoteka se cita samo kad joj se promijeni velicina (ili ima naredbi na cekanju)
    local sz = f:seek("end") or 0
    if sz == pc_sz and pc_n == 0 then f:close(); return 0 end
    f:seek("set", 0)
    local blob = f:read("*a") or ""
    f:close()
    pc_sz = sz
    local n = 0
    for line in blob:gmatch("[^\r\n]+") do
        line = line:gsub("^%s+", "")
        if line ~= "" and line:sub(1, 1) ~= "#" then
            local tx = line:match("^([^,]*)")
            if tx and tx ~= "" and not applied[tx] and not auto_tried[tx] then n = n + 1 end
        end
    end
    pc_n = n
    return n
end

local function mark_tried()
    -- only what this pass really processed counts as tried (the pass is limited to MAX_PER_RUN): the rest stays pending and the next auto pass takes it
    for tx in pairs(seen) do auto_tried[tx] = true end
end

local function auto_tick()
    if not AUTO or not ctx_ref then return end
    local now = os.clock()
    if now - last_auto < 5 then return end
    last_auto = now
    local n = pending_count()
    auto_wait = 0
    if n == 0 then return end
    if not file_exists(path(F_ON)) then return end          -- probni nacin: samo rucno (F6)
    if not index then
        quiet = true
        local ok, r1 = pcall(build_index)
        quiet = false
        if not ok or not r1 then
            auto_wait = n
            last_auto = now + 25                              -- ne pokusavaj cesce od ~30 s dok nema F7
            last_msg = string.format("AUTO: %d commands waiting - switch to PlayerDump and press F7 (once per game launch)", n)
            return
        end
    end
    local ok, err = pcall(process, true)
    mark_tried()
    if not ok then log("ERROR (auto): " .. tostring(err)) end
end

function m.key_down(ctx, vkey)
    pcall(state_tick)
    if vkey == KEY_F6 then
        local ok, err = pcall(process, true)
        if not ok then log("ERROR: " .. tostring(err)) end
    else
        local ok, err = pcall(auto_tick)
        if not ok then quiet = false end
    end
end

-- 1.1: overlay_on se zove svaki frame; provjera datoteke (io.open) svaki frame je usporavala Sider overlay
local live_t, live_v = -100, false
local function live_on()
    local now = os.clock()
    if now - live_t > 5 then live_t = now; live_v = file_exists(path(F_ON)) end
    return live_v
end

function m.overlay_on(ctx)
    pcall(state_tick)
    local ok = pcall(auto_tick)
    if not ok then quiet = false end
    return string.format(" GrowthBridge v%s  [F6 / AUTO]  %s\n %s", m.version, live_on() and "LIVE" or "TEST MODE (nothing is written; enable live writes in the app)", last_msg)
end

-- 1.4: write waiting points automatically before every match you play (Sider "set_teams", right after PlayerDump's
--      automatic F7), and once more when the match conditions are set. No overlay needed.
local last_ev = {}
local function on_match(ctx, ev)
    -- 1.5: throttle per event (FL26 loads GrowthBridge before PlayerDump: at set_teams the new F7 is not there yet,
    --      so after_set_conditions, which comes a moment later, must still run)
    if os.clock() - (last_ev[ev] or -100) < 3 then return end
    last_ev[ev] = os.clock()
    if not file_exists(path(F_ON)) then return end
    -- 1.8: samo u Master League (prijateljska / slobodni trening: nista se ne pise ni ne trazi)
    local okst, st = pcall(read_state)
    if okst and (st == "home" or st == "null") then return end   -- "unknown"/greska: kao prije (drugi exe)
    local ok, err = pcall(process, true)
    if ok then pcall(mark_tried) else log("ERROR (match): " .. tostring(err)) end
end
function m.set_teams(ctx, home, away) pcall(state_tick); on_match(ctx, 1) end
function m.after_set_conditions(ctx) on_match(ctx, 2) end

-- 1.19 (The Gaffer pc495): prebacivanje igra -> app kontrolerom (LT+RT ili Back+Start).
-- Blokadu kontrolera dok si u appu radi Sider (gamepad.ini: xinput ukljucen, LT+RT otvara overlay; sider.ini:
-- overlay.block-input-when-on = 1). Igra radi kao administrator, pa Windows ne da appu da preuzme prvi plan dok je igra
-- naprijed. Zato ovaj modul, dok drzis kombinaciju, kaze Windowsu da smije bilo tko (AllowSetForegroundWindow) - igra kao
-- prozor u prvom planu to smije dopustiti. (Lua blokada iz 1.12-1.17 je maknuta: Sider je dopusta samo modulu overlaya.)
local SW = { ok = nil, n = 0, was = false }
local function sw_init()
    if SW.ok ~= nil then return SW.ok end
    SW.ok = false
    local ffi = ffi
    if ffi == nil and type(require) == "function" then
        local okr, r = pcall(require, "ffi")
        if okr then ffi = r end
    end
    if ffi == nil then return false end
    pcall(ffi.cdef, [[
        typedef struct { uint16_t wButtons; uint8_t bLT; uint8_t bRT; int16_t lx, ly, rx, ry; } GB_XPAD;
        typedef struct { uint32_t dwPacketNumber; GB_XPAD pad; } GB_XSTATE;
        uint32_t GB_XInputGetState(uint32_t idx, GB_XSTATE* st) __asm__("XInputGetState");
        int GB_AllowSetForegroundWindow(uint32_t pid) __asm__("AllowSetForegroundWindow");
    ]])
    local lib = nil
    for _, n in ipairs({ "xinput1_4", "xinput1_3", "xinput9_1_0" }) do
        local okl, l = pcall(ffi.load, n)
        if okl and l then lib = l; break end
    end
    if not lib then log("switch: XInput not found"); return false end
    SW.ffi, SW.lib, SW.st = ffi, lib, ffi.new("GB_XSTATE")
    SW.ok = true
    log("switch: ready (hold LT+RT to go to the app)")
    return true
end
local function sw_combo()
    -- 1.25 (jubileu009: trzanje u utakmici, bez GrowthBridgea glatko): XInputGetState za NEPRIKLJUCEN kontroler zna trajati
    -- nekoliko ms. Prije su se sva 4 mjesta provjeravala svakih 120 frameova (svake 2 s = trzaj). Sada: prvi put sva cetiri,
    -- poslije samo prikljuceni svaki frame, a jedno prazno mjesto tek svakih 600 frameova (redom, jedno po jedno).
    if SW.live == nil then
        SW.live = {}
        for i = 0, 3 do SW.live[i] = (SW.lib.GB_XInputGetState(i, SW.st) == 0) end
    elseif SW.n % 600 == 0 then
        SW.probe = ((SW.probe or 3) + 1) % 4
        if not SW.live[SW.probe] then SW.live[SW.probe] = (SW.lib.GB_XInputGetState(SW.probe, SW.st) == 0) end
    end
    for i = 0, 3 do
        local rc = 1
        if SW.live[i] then
            rc = SW.lib.GB_XInputGetState(i, SW.st)
            if rc ~= 0 then SW.live[i] = false end
        end
        if rc == 0 then
            local p = SW.st.pad
            if p.bLT > 120 and p.bRT > 120 then return true end
            local b = tonumber(p.wButtons)
            if (math.floor(b / 16) % 4) == 3 then return true end   -- Back + Start
        end
    end
    return false
end
function m.display_frame(ctx)
    pcall(auto_tick)   -- patch: auto-apply without key press / overlay (throttled to every 5 s inside auto_tick)
    SW.n = SW.n + 1
    if not sw_init() then return end
    local ok, held = pcall(sw_combo)
    if not ok then
        if not SW.err then SW.err = true; log("switch: read error " .. tostring(held)) end
        return
    end
    if held then
        if SW.n % 6 == 0 or not SW.was then
            local oka, ra = pcall(SW.ffi.C.GB_AllowSetForegroundWindow, 0xFFFFFFFF)
            if not SW.was and not SW.logged then SW.logged = true; log("switch: app allowed to come to the front (" .. tostring(oka and ra) .. ")") end
        end
    end
    SW.was = held
end

function m.init(ctx)
    ctx_ref = ctx
    local t0 = os.clock()
    load_applied()
    log(string.format("init: applied list read in %.2f s", os.clock() - t0))
    ctx.register("key_down", m.key_down)
    ctx.register("overlay_on", m.overlay_on)
    ctx.register("set_teams", m.set_teams)
    ctx.register("after_set_conditions", m.after_set_conditions)
    ctx.register("livecpk_make_key", m.make_key)   -- 1.6: stanje igre se osvjezi pri svakom ucitavanju datoteka (izbornik <-> ML)
    ctx.register("gamepad_input", m.gamepad_input)
    ctx.register("get_stadium_name", m.get_stadium_name)
    pcall(ctx.register, "display_frame", m.display_frame)   -- 1.19: prebacivanje u app kontrolerom
    local t1 = os.clock()
    pcall(state_tick, true)
    log(string.format("init: first state read %.2f s, init total %.2f s", os.clock() - t1, os.clock() - t0))
    log("GrowthBridge loaded")
end

return m
