"""Set-up of the Sider module PESM-LivePatch: copies the module, adds one line to sider.ini (backup first, line endings kept), asks nothing twice. Runs on a made-up Sider folder."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'flconv'))
import server  # noqa: E402

root = tempfile.mkdtemp()
sd = os.path.join(root, 'SiderAddons')
db = os.path.join(sd, 'livecpk', 'x', 'common', 'etc', 'pesdb')
os.makedirs(db)
os.makedirs(os.path.join(sd, 'modules'))
ini = os.path.join(sd, 'sider.ini')
open(ini, 'wb').write(b'[sider]\r\n\tdebug = 0\r\n\tlua.module = "a.lua"\r\n\t;lua.module = "b.lua"\r\n\tlua.module = "c.lua"\r\n\tvkey.reload-1 = 0x10')
server.CFG['pesdb'] = db
server.DATA = tempfile.mkdtemp()
server.SET.pop('lp_hide', None)

assert server.lp_status()['state'] == 'ask'
r = server.lp_install()
assert r['ok'] and os.path.isfile(r['backup']) and os.path.isfile(os.path.join(sd, 'modules', 'pesm-livepatch.lua'))
new = open(ini, 'rb').read()
assert new.count(b'pesm-livepatch.lua') == 1
assert b'\tlua.module = "c.lua"\r\n\tlua.module = "pesm-livepatch.lua"\r\n\tvkey.reload-1 = 0x10' in new   # after the last active module line, same indent and line ending
assert open(r['backup'], 'rb').read().count(b'pesm-livepatch') == 0   # the backup is the old file
assert server.lp_status()['state'] == 'ok'
assert server.lp_install()['ok'] and open(ini, 'rb').read().count(b'pesm-livepatch.lua') == 1   # again: no second line
open(os.path.join(sd, 'modules', 'pesm-livepatch.lua'), 'w').write('-- old version')
assert server.lp_status()['state'] == 'ok' and b'PESM-LivePatch' in open(os.path.join(sd, 'modules', 'pesm-livepatch.lua'), 'rb').read()   # an older module is replaced
server.CFG['pesdb'] = '/nowhere/pesdb'
assert server.lp_status()['state'] == 'none'
print('ok')
