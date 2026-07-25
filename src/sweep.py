"""
run_sweep.py — OVERNIGHT SWEEP. Reads sweep_table.xlsx, calls solver_core's
solve_case + extract_case for each row (SAME functions run_one uses).
One case failing does NOT stop the sweep.

Outputs:
  results/solutions/<case_id>.cas.h5
  results/data/<case_id>.xlsx
  results/sweep_log.txt

Run:  python src/run_sweep.py   (check results/sweep_log.txt in the morning)
"""
import pandas as pd
import os, time, traceback
from solver_core import solve_case, extract_case

TABLE   = "sweep_table.xlsx"
MESHDIR = "results/meshes"
SOLDIR  = "results/solutions"
DATADIR = "results/data"
LOG     = "results/sweep_log.txt"
for d in (SOLDIR, DATADIR): os.makedirs(d, exist_ok=True)

def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line)
    with open(LOG, "a") as f: f.write(line + "\n")

open(LOG, "w").close()
df = pd.read_excel(TABLE)

# Column headers in the Excel have units, e.g. "T_static (K)", which break
# dot-access (c.T_static). Strip the "(...)" and whitespace so names are clean.
import re
df.columns = [re.sub(r"\s*\(.*?\)", "", str(col)).strip() for col in df.columns]
print("normalized columns:", list(df.columns))
log(f"SWEEP START: {len(df)} cases")
ok = fail = 0

for c in df.itertuples(index=False):
    mesh = os.path.abspath(f"{MESHDIR}/{c.geometry}_coarse.msh.h5").replace("\\","/")
    sol  = os.path.abspath(f"{SOLDIR}/{c.case_id}.cas.h5").replace("\\","/")
    data = os.path.abspath(f"{DATADIR}/{c.case_id}.xlsx").replace("\\","/")
    if os.path.exists(data):
        log(f"SKIP {c.case_id}: already done (resume)"); ok += 1; continue
    if not os.path.exists(mesh):
        log(f"SKIP {c.case_id}: mesh missing -> {mesh}"); fail += 1; continue
    log(f"START {c.case_id}: {c.geometry} M{c.Mach} Re{c.Re:.1e}")
    try:
        t0 = time.time()
        iters = solve_case(mesh, sol, c.Mach, c.T_static, c.op_pressure,
                           c.velocity, c.L_ref, log=log)
        log(f"  solved {c.case_id} ({iters} iters, {time.time()-t0:.0f}s)")
        extract_case(sol, data, meta={
            "case_id":c.case_id, "geometry":c.geometry, "angle_deg":c.angle_deg,
            "Mach":c.Mach, "Re":c.Re})
        log(f"  OK   {c.case_id} -> {data}")
        log(f"  saved solution: {sol}")   # kept for inspection (contours, convergence)
        ok += 1
    except Exception as e:
        log(f"  FAIL {c.case_id}: {e}")
        log(traceback.format_exc())
        fail += 1

log(f"SWEEP DONE: {ok} ok, {fail} failed. Data in {DATADIR}/")