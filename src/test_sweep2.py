"""
run_two.py — PRE-FLIGHT: run TWO cases through the sweep mechanism.

Why two: one case tests the functions; TWO tests the LOOP — fresh Fluent per
case, unique filenames, mesh-swapping, no state bleeding between cases. If two
cases flow through cleanly, the full sweep mechanism is sound.

Uses the SAME solver_core functions as run_sweep.py, at short iterations.

Run:  python src/run_two.py
"""
import os, math, time, traceback
from solver_core import solve_case, extract_case

# ---- two test cases (different geometries -> also tests mesh swap) ----
CASES = [
    {"case_id":"test_fin00", "geometry":"fin_00", "Mach":0.86,
     "T_static":271.0, "op_pressure":60727.0, "L_ref":0.05},
    {"case_id":"test_fin14", "geometry":"fin_14", "Mach":0.86,
     "T_static":271.0, "op_pressure":60727.0, "L_ref":0.05},
]

MESHDIR = "results/meshes"
SOLDIR  = "results/solutions"
DATADIR = "results/data"
for d in (SOLDIR, DATADIR): os.makedirs(d, exist_ok=True)

ok = fail = 0
for c in CASES:
    mesh = os.path.abspath(f"{MESHDIR}/{c['geometry']}.msh.h5").replace("\\","/")
    sol  = os.path.abspath(f"{SOLDIR}/{c['case_id']}.cas.h5").replace("\\","/")
    data = os.path.abspath(f"{DATADIR}/{c['case_id']}.xlsx").replace("\\","/")
    if not os.path.exists(mesh):
        print(f"SKIP {c['case_id']}: mesh missing -> {mesh}"); fail += 1; continue
    print(f"\n=== START {c['case_id']} ({c['geometry']}) ===")
    try:
        V = c["Mach"] * math.sqrt(1.4*287.0*c["T_static"])
        t0 = time.time()
        iters = solve_case(mesh, sol, c["Mach"], c["T_static"], c["op_pressure"],
                           V, c["L_ref"], warmup=1, main=0, drag_tol=1e-1)  # SHORT test
        print(f"  solved in {iters} iters, {time.time()-t0:.0f}s -> {sol}")
        extract_case(sol, data, meta={
            "case_id":c["case_id"], "geometry":c["geometry"], "Mach":c["Mach"]})
        print(f"  OK -> {data}")
        ok += 1
    except Exception as e:
        print(f"  FAIL {c['case_id']}: {e}")
        traceback.print_exc()
        fail += 1

print(f"\n=== PRE-FLIGHT DONE: {ok} ok, {fail} failed ===")
if ok == len(CASES):
    print("Both cases flowed through -> sweep mechanism is sound.")
    print("Now bump iterations to real values and run run_sweep.py.")
else:
    print("Fix the failures above before trusting the full sweep.")