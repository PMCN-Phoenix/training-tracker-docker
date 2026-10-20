import requests, collections, datetime, sys

TOKEN = "training-super-secret-token-2026"
ORG = "training-org"
URL = "http://127.0.0.1:8086/api/v2/query"

def flux(q):
    r = requests.post(URL, params={"org": ORG}, headers={
        "Authorization": f"Token {TOKEN}",
        "Accept": "application/csv",
        "Content-Type": "application/vnd.flux",
    }, data=q.encode("utf-8"), timeout=90)
    if r.status_code >= 300:
        print("ERR", r.status_code, r.text[:400]); sys.exit(1)
    lines = [l for l in r.text.split("\r\n") if l and not l.startswith("#")]
    if len(lines) < 2:
        return []
    hdr = lines[0].split(",")
    return [dict(zip(hdr, l.split(","))) for l in lines[1:]]

def bj(ts):
    t = datetime.datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")
    return (t + datetime.timedelta(hours=8)).strftime("%m-%d")

Q = '''
from(bucket: "training")
  |> range(start: -70d)
  |> filter(fn: (r) => r._measurement =~ /^ppl_(push|pull|squat)_/)
  |> keep(columns: ["_time","_field","_value","_measurement","session_id","set_index","exercise","direction"])
  |> sort(columns:["_time"])
'''
rows = flux(Q)

# (session, measurement, set_index) -> {field: value}
cells = collections.defaultdict(dict)
meta = {}
for r in rows:
    key = (r["session_id"], r["_measurement"], r["set_index"])
    cells[key][r["_field"]] = r["_value"]
    meta[r["session_id"]] = (r["_time"], r.get("direction", ""))

sessions = collections.defaultdict(lambda: {"dir": "", "acts": collections.defaultdict(list)})
for (sid, meas, si), f in cells.items():
    t, d = meta[sid]
    sessions[sid]["dir"] = d
    sessions[sid]["acts"][meas].append((int(si), float(f.get("weight_kg", 0) or 0), float(f.get("reps", 0) or 0)))

order = sorted(sessions.items(), key=lambda kv: meta[kv[0]][0])

print("=== SESSION 汇总（近70天，北京时间）===")
print(f"{'日期':<8}{'部位':<7}{'动作':>4}{'组数':>5}{'总次数':>7}{'总容量kg':>10}  明细")
for sid, s in order:
    d = bj(meta[sid][0])
    tot_sets = sum(len(v) for v in s["acts"].values())
    tot_reps = sum(r for v in s["acts"].values() for _, _, r in v)
    tot_vol = sum(w * r for v in s["acts"].values() for _, w, r in v)
    detail = " ".join(f"{m.replace('ppl_','')}:{len(v)}x{v[0][1]:g}/{v[0][2]:g}" for m, v in s["acts"].items())
    print(f"{d:<8}{s['dir']:<7}{len(s['acts']):>4}{tot_sets:>5}{tot_reps:>7.0f}{tot_vol:>10.0f}  {detail}")
