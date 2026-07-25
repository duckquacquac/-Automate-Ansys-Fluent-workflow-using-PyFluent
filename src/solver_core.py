"""
solver_core.py — the ONE place the solve + extract logic lives.

Two functions, parameter-driven, launched with a fresh Fluent session each:
    solve_case(params)   -> solves, saves <sol_path>, returns iters run
    extract_case(params) -> reads saved solution, writes <data_path> xlsx

Both solve_case.py-for-one and run_sweep.py-for-many import and call these,
so there is exactly one source of truth. Change a solver setting here -> it
changes everywhere.
"""
import ansys.fluent.core as pyfluent
import pandas as pd
import math

R = 287.0

# ---- physics constants shared by every case ----
FLOW_DIR = [0.0, 1.0, 0.0]
REF_AREA = 0.001
ZONES    = ["fin", "wall"]

def _launch(transcript=False):
    return pyfluent.launch_fluent(
        mode=pyfluent.FluentMode.SOLVER, precision=pyfluent.Precision.DOUBLE,
        processor_count=12, ui_mode="no_gui", start_transcript=transcript,
        cleanup_on_exit=True)


def solve_case(mesh_path, sol_path, Mach, T_static, op_pressure, velocity,
               L_ref, warmup=100, main=500, chunk=25, drag_tol=1e-4, log=print,
               transcript=False):
    """Solve one case in a fresh session; save to sol_path. Returns iters run."""
    rho = op_pressure / (R * T_static)
    solver = _launch(transcript)
    try:
        solver.tui.file.read_case(mesh_path)
        setup, sol = solver.settings.setup, solver.settings.solution

        setup.general.solver.type = "pressure-based"
        try: sol.methods.p_v_coupling.flow_scheme = "Coupled"
        except Exception: pass
        setup.models.energy.enabled = True
        setup.materials.fluid["air"].density.option = "ideal-gas"
        try: setup.materials.fluid["air"].viscosity.option = "sutherland"
        except Exception: pass
        setup.models.viscous.model = "k-omega"
        setup.models.viscous.k_omega_model = "sst"
        setup.general.operating_conditions.operating_pressure = op_pressure

        ff = setup.boundary_conditions.pressure_far_field["farfield"]
        ff.momentum.mach_number = Mach
        ff.momentum.gauge_pressure = 0.0
        ff.thermal.temperature = T_static
        try:
            for i in range(3): ff.momentum.flow_direction[i] = FLOW_DIR[i]
            ff.turbulence.turbulent_intensity = 0.01
            ff.turbulence.turbulent_viscosity_ratio = 5
        except Exception: pass

        rv = setup.reference_values
        rv.area, rv.density, rv.velocity, rv.length, rv.temperature = \
            REF_AREA, rho, velocity, L_ref, T_static

        sol.report_definitions.drag["fin-drag"] = {"zones":["fin"], "force_vector":FLOW_DIR}

        def order(o):
            d = sol.methods.spatial_discretization.discretization_scheme
            for eq in ["k","omega"]:
                try: d[eq] = o
                except Exception: pass

        sol.initialization.initialization_type = "hybrid"
        sol.initialization.hybrid_initialize()

        order("first-order-upwind"); sol.run_calculation.iterate(iter_count=warmup)
        order("second-order-upwind")
        done, prev = 0, None
        while done < main:
            n = min(chunk, main-done)
            sol.run_calculation.iterate(iter_count=n); done += n
            cd = sol.report_definitions.compute(report_defs=["fin-drag"])[0]["fin-drag"][0]
            if prev is not None and abs(cd-prev) < drag_tol:
                log(f"    converged at {done} iters"); break
            prev = cd

        # Write CASE and DATA separately -> <name>.cas.h5 AND <name>.dat.h5
        cas_path = sol_path
        dat_path = sol_path.replace(".cas.h5", ".dat.h5")
        solver.settings.file.write(file_type="case", file_name=cas_path)
        solver.settings.file.write(file_type="data", file_name=dat_path)
        return done
    finally:
        solver.exit()


def extract_case(sol_path, data_path, meta=None, transcript=False):
    """Read a saved solution; extract forces/moments/y+/CoP for all ZONES -> xlsx."""
    meta = meta or {}
    solver = _launch(transcript)
    try:
        # read case, then its matching data file (written separately by solve_case)
        solver.tui.file.read_case(sol_path)
        dat_path = sol_path.replace(".cas.h5", ".dat.h5")
        solver.tui.file.read_data(dat_path)
        sol = solver.settings.solution

        def fvec(z):
            o = {}
            for nm,v in [("Fx",[1,0,0]),("Fy",[0,1,0]),("Fz",[0,0,1])]:
                k=f"{z}-{nm}"; sol.report_definitions.force[k]={"zones":[z],"force_vector":v}
                o[nm]=sol.report_definitions.compute(report_defs=[k])[0][k][0]
            return o
        def mvec(z):
            o = {}
            for nm,ax in [("Mx",[1,0,0]),("My",[0,1,0]),("Mz",[0,0,1])]:
                k=f"{z}-{nm}"
                try:
                    sol.report_definitions.moment[k]={"zones":[z],"mom_center":[0,0,0],"mom_axis":ax}
                    o[nm]=sol.report_definitions.compute(report_defs=[k])[0][k][0]
                except Exception: o[nm]=float('nan')
            return o
        def yp(z):
            o = {}
            for nm,rt in [("yplus_max","surface-facetmax"),("yplus_avg","surface-areaavg")]:
                k=f"{z}-{nm}"
                try:
                    sol.report_definitions.surface[k]={"report_type":rt,"field":"y-plus","surface_names":[z]}
                    o[nm]=sol.report_definitions.compute(report_defs=[k])[0][k][0]
                except Exception: o[nm]=float('nan')
            return o
        def cop(F,M):
            F2=F["Fx"]**2+F["Fy"]**2+F["Fz"]**2; Fmag=F2**0.5
            if Fmag<1e-3:
                return {"CoP_x":float('nan'),"CoP_y":float('nan'),"CoP_z":float('nan'),
                        "F_mag":Fmag,"CoP_valid":"NO (ill-conditioned)"}
            return {"CoP_x":(F["Fy"]*M["Mz"]-F["Fz"]*M["My"])/F2,
                    "CoP_y":(F["Fz"]*M["Mx"]-F["Fx"]*M["Mz"])/F2,
                    "CoP_z":(F["Fx"]*M["My"]-F["Fy"]*M["Mx"])/F2,
                    "F_mag":Fmag,"CoP_valid":"yes"}

        rows=[]
        for z in ZONES:
            F=fvec(z); M=mvec(z); Y=yp(z); C=cop(F,M)
            rows.append({**meta, "zone":z, **F, **M, **Y, **C, "drag_N":F["Fy"]})
        pd.DataFrame(rows).to_excel(data_path, index=False)
        return rows
    finally:
        solver.exit()