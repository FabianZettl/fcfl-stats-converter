-- FCFL: logs every moment the game reads a database file (common\etc\pesdb\*) out of livecpk, with the time and size.
-- Purpose: find out whether Player.bin / PlayerAssignment.bin / Tactics*.bin are read again during one session (new mode, load a save, back to the menu),
-- so we know if the converter can write them into livecpk and the game takes them without a restart. Writes nothing, changes nothing.
-- Install: copy to <SiderAddons>\modules\ and add   lua.module = "fcfl_dblog.lua"   to sider.ini. Read with:  grep fcfl_dblog sider.log
local m = {}
local seen = {}

local function on_read(ctx, filename, addr, len, total_size, offset)
  local f = string.lower(filename)
  if offset == 0 and string.find(f, "common\\etc\\pesdb\\", 1, true) then
    seen[f] = (seen[f] or 0) + 1
    log(string.format("fcfl_dblog %s read #%d  %s  (%d bytes)", os.date("%H:%M:%S"), seen[f], filename, total_size))
  end
end

function m.init(ctx)
  ctx.register("livecpk_read", on_read)
  log("fcfl_dblog: watching common\\etc\\pesdb\\ reads")
end

return m
