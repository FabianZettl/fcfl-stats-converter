"""Which players should the scraper fetch next? The rows of the FM list that belong to a player of the connected database but have no attributes yet (best first), and the players of the database that the list does not
have at all. Writes <data dir>/fm-todo-urls.txt (one FMInside URL per line, best first) and fm-todo-missing.csv. Usage: fm_todo.py"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'flconv'))
sys.path.insert(0, os.path.join(HERE, '..', 'flconv', 'lib'))
import fmdb  # noqa: E402
import server  # noqa: E402

server.SET.update(json.load(open(server.SET_FILE)))
server.CFG['pesdb'] = server.resolve_pesdb(server.SET.get('dbpath'))
server.load()
todo, missing = {}, []
for pid in server.M.pb.ids:
    if not server.club_name(pid) or server.match(pid)['status'] == 'ok' and False:
        continue
    fr = server.fm_row(pid)
    ovr = server.cur_ovr(pid)
    if fr is not None and not fmdb.complete(fr) and fr.get('URL'):
        todo[fr['UID']] = (ovr, fr['URL'])
    elif fr is None and server.match(pid)['status'] != 'ok':
        missing.append((ovr, server.M.name.get(pid), server.club_name(pid), server.M.age.get(pid)))
os.makedirs(server.DATA, exist_ok=True)
urls = sorted(todo.values(), key=lambda x: -x[0])
open(os.path.join(server.DATA, 'fm-todo-urls.txt'), 'w').write('\n'.join(u for _, u in urls) + '\n')
with open(os.path.join(server.DATA, 'fm-todo-missing.csv'), 'w', newline='') as f:
    w = csv.writer(f, delimiter=';')
    w.writerow(['overall', 'name', 'club', 'age'])
    w.writerows(sorted(missing, key=lambda x: -x[0]))
print('%d rows of the list have no attributes yet (fm-todo-urls.txt), %d players of the database are not in the list and not in EA FC (fm-todo-missing.csv), in %s' % (len(urls), len(missing), server.DATA))
