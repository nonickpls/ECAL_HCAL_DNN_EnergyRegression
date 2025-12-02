from typing import Dict, Tuple
from G4Calo import GeometryDescriptor
from Trackers import LAMBDA_INT_CM  # your interaction-length map

def build_ecal_pbwo4_26X0_then_graded_fe_scint_hcal_200cm_v1(
    # --- ECAL ---
    total_X0: float = 26.0,                 # target depth in X0
    X0_cm: float = 0.89,                    # PbWO4 X0 in cm (≈ 0.89 cm)
    ecal_slices: int = 30,                  # slice ECAL to make nice layer histos
    ecal_material: str = "G4_PbWO4",
    # --- HCAL sections (front → mid → back), ~200 cm total length ---
    front_pairs: int = 16, fe_front: float = 0.8, sc_front: float = 0.8,   # 25.6 cm
    mid_pairs:   int = 32, fe_mid:   float = 1.2, sc_mid:   float = 0.6,   # 57.6 cm
    back_pairs:  int = 47, fe_back:  float = 1.5, sc_back:  float = 0.5,   # 94.0 cm
    absorber: str = "G4_Fe",
    active:   str = "G4_POLYSTYRENE",
    sensitive_active_only: bool = True,
    # optional cost tracker (your Trackers.CostTracker instance or None)
    cost_tracker=None,
) -> Tuple[GeometryDescriptor, Dict]:

    gd = GeometryDescriptor()

    ecal_len_cm  = float(total_X0) * float(X0_cm)     # ~ 26 * 0.89 = 23.14 cm
    ecal_slice   = ecal_len_cm / int(ecal_slices)

    for _ in range(int(ecal_slices)):
        gd.addLayer(ecal_slice, ecal_material, True)
        if cost_tracker is not None:
            cost_tracker.add(ecal_material, ecal_slice)


    def add_section(n_pairs: int, t_abs_cm: float, t_act_cm: float) -> None:
        for _ in range(int(n_pairs)):
            gd.addLayer(float(t_abs_cm), absorber, False)
            gd.addLayer(float(t_act_cm), active,   bool(sensitive_active_only))
            if cost_tracker is not None:
                cost_tracker.add(absorber, t_abs_cm)
                cost_tracker.add(active,   t_act_cm)

    add_section(front_pairs, fe_front, sc_front)
    add_section(mid_pairs,   fe_mid,   sc_mid)
    add_section(back_pairs,  fe_back,  sc_back)

    # lengths
    hcal_len_cm = (
        front_pairs * (fe_front + sc_front)
        + mid_pairs * (fe_mid + sc_mid)
        + back_pairs * (fe_back + sc_back)
    )
    total_len_cm = ecal_len_cm + hcal_len_cm

    # interaction length contribution of ECAL
    ecal_lambda = ecal_len_cm / float(LAMBDA_INT_CM[ecal_material])

    # interaction-length (λ) accounting for HCAL
    def lam_pair(t_abs_cm: float, t_act_cm: float) -> float:
        return (float(t_abs_cm) / float(LAMBDA_INT_CM[absorber])) + \
               (float(t_act_cm) / float(LAMBDA_INT_CM[active]))

    lam_front = front_pairs * lam_pair(fe_front, sc_front)
    lam_mid   = mid_pairs   * lam_pair(fe_mid,   sc_mid)
    lam_back  = back_pairs  * lam_pair(fe_back,  sc_back)
    hcal_lambda = lam_front + lam_mid + lam_back
    total_lambda = ecal_lambda + hcal_lambda

    specs: Dict[str, float] = {
        # ECAL
        "ecal_len_cm": ecal_len_cm,
        "ecal_slice_cm": ecal_slice,
        "ecal_lambda": ecal_lambda,
        # HCAL config
        "front_pairs": float(front_pairs), "fe_front": fe_front, "sc_front": sc_front,
        "mid_pairs":   float(mid_pairs),   "fe_mid":   fe_mid,   "sc_mid":   sc_mid,
        "back_pairs":  float(back_pairs),  "fe_back":  fe_back,  "sc_back":  sc_back,
        # HCAL / totals
        "hcal_len_cm": hcal_len_cm,
        "hcal_lambda": hcal_lambda,
        "total_len_cm": total_len_cm,     # ≈ 200.3 cm with defaults
        "total_lambda": total_lambda,      # ≈ 8.8 λ_int with defaults
    }

    return gd, specs

#--- 2nd design:

# Design.py — Budget-friendly ECAL (Pb/Scint sampling) + graded Fe/Scint HCAL (~200 cm)

def build_pb_scint_ecal_then_graded_fe_scint_hcal_200cm_v2(
    # --- ECAL: Pb/Scint sampling (fine sampling, ~24 cm total, ~21–22 X0)
    ecal_pairs: int = 60,          # 60 × (0.20 Pb + 0.20 Sc) → ~24.0 cm ECAL
    pb_per_pair_cm: float = 0.20,  # lead per period (cm)
    sc_per_pair_cm: float = 0.20,  # scint per period (cm)
    ecal_absorber: str = "G4_Pb",
    ecal_active:   str = "G4_POLYSTYRENE",
    # --- HCAL: graded Fe/Scint (front transition → mid → back)
    front_pairs: int = 18, fe_front: float = 0.5, sc_front: float = 1.0,   # 27.0 cm
    mid_pairs:   int = 28, fe_mid:   float = 1.0, sc_mid:   float = 0.7,   # 47.6 cm
    back_pairs:  int = 50, fe_back:  float = 1.5, sc_back:  float = 0.5,   # 100.0 cm
    absorber: str = "G4_Fe",
    active:   str = "G4_POLYSTYRENE",
    sensitive_active_only: bool = True,
    cost_tracker=None,
) -> Tuple[GeometryDescriptor, Dict]:
    """
    2.0 m hybrid design tuned for 1–100 GeV, ~50% π± / 50% γ.
      • ECAL: fine Pb/Scint sampling (~24 cm total), much cheaper than PbWO4.
      • HCAL: graded Fe/Scint with a thin-Fe/thicker-Sc transition section,
              then mid and back sections.

    With defaults: total length ≈ 198.6 cm.
    Returns (geometry, specs). No printing.
    """

    gd = GeometryDescriptor()

    # ---------------------------
    # ECAL (Pb/Scint sampling)
    # ---------------------------
    for _ in range(int(ecal_pairs)):
        # absorber (Pb), not sensitive
        gd.addLayer(float(pb_per_pair_cm), ecal_absorber, False)
        # active (Scint), sensitive so layer histograms show bars
        gd.addLayer(float(sc_per_pair_cm), ecal_active, True)
        if cost_tracker is not None:
            cost_tracker.add(ecal_absorber, pb_per_pair_cm)
            cost_tracker.add(ecal_active,   sc_per_pair_cm)

    ecal_len_cm = float(ecal_pairs) * (float(pb_per_pair_cm) + float(sc_per_pair_cm))

    # ---------------------------
    # HCAL (graded Fe/Scint)
    # ---------------------------
    def add_section(n_pairs: int, t_abs_cm: float, t_act_cm: float) -> None:
        for _ in range(int(n_pairs)):
            gd.addLayer(float(t_abs_cm), absorber, False)
            gd.addLayer(float(t_act_cm), active,   bool(sensitive_active_only))
            if cost_tracker is not None:
                cost_tracker.add(absorber, t_abs_cm)
                cost_tracker.add(active,   t_act_cm)

    add_section(front_pairs, fe_front, sc_front)  # transition: reduces ECAL→HCAL step
    add_section(mid_pairs,   fe_mid,   sc_mid)
    add_section(back_pairs,  fe_back,  sc_back)

    hcal_len_cm = (
        float(front_pairs) * (float(fe_front) + float(sc_front))
        + float(mid_pairs) * (float(fe_mid)   + float(sc_mid))
        + float(back_pairs) * (float(fe_back) + float(sc_back))
    )

    specs: Dict[str, float] = {
        # ECAL sampling specs
        "ecal_pairs": float(ecal_pairs),
        "pb_per_pair_cm": float(pb_per_pair_cm),
        "sc_per_pair_cm": float(sc_per_pair_cm),
        "ecal_absorber": ecal_absorber,
        "ecal_active": ecal_active,
        "ecal_len_cm": ecal_len_cm,                  # ~24.0 cm
        # HCAL graded specs
        "front_pairs": float(front_pairs), "fe_front": float(fe_front), "sc_front": float(sc_front),
        "mid_pairs":   float(mid_pairs),   "fe_mid":   float(fe_mid),   "sc_mid":   float(sc_mid),
        "back_pairs":  float(back_pairs),  "fe_back":  float(fe_back),  "sc_back":  float(sc_back),
        "hcal_len_cm": hcal_len_cm,                   # ~174.6 cm
        # Totals
        "total_len_cm": ecal_len_cm + hcal_len_cm,    # ~198.6 cm
        # Convenience for run_batch-style sims: use ECAL scint plate as layer thickness
        "ecal_slice_cm": float(sc_per_pair_cm),
    }

    return gd, specs

# Design.py — v4.2 triple ECAL with scint end-cap + HCAL transition (no printouts)

from typing import Tuple, Dict, Optional
from G4Calo import GeometryDescriptor

def build_triple_ecal_then_fe_scint_hcal_2m_v4_2(
    # --- ECAL triple period: [Pb, Scint(sens), PbWO4]
    ecal_pairs: int = 60,
    pb_cm: float = 0.15,
    sc_cm: float = 0.20,
    pbwo4_cm: float = 0.10,
    add_scint_endcap: bool = True,          # adds one extra scint layer after ECAL
    ecal_pb: str = "G4_Pb",
    ecal_scint: str = "G4_POLYSTYRENE",
    ecal_pbwo4: str = "G4_PbWO4",

    # --- HCAL: transition → nominal
    trans_pairs: int = 8,   fe_trans: float = 0.30, sc_trans: float = 1.20,  
    mid_pairs:   int = 24,  fe_mid:   float = 1.00, sc_mid:   float = 0.70,
    back_pairs:  int = 50,  fe_back:  float = 1.50, sc_back:  float = 0.50,
    hcal_absorber: str = "G4_Fe",
    hcal_active:   str = "G4_POLYSTYRENE",
    sensitive_active_only: bool = True,

    # --- Length target shim to hit ~2.00 m exactly (optional)
    target_total_len_cm: float = 200.0,

    # Optional cost tracker (e.g., Trackers.CostTracker) or None
    cost_tracker: Optional[object] = None,
) -> Tuple[GeometryDescriptor, Dict]:
    gd = GeometryDescriptor()

    # ---------------------------
    # ECAL (strict triplets)
    # ---------------------------
    for _ in range(int(ecal_pairs)):
        # Pb (passive)
        gd.addLayer(float(pb_cm),    ecal_pb,    False)
        # Scint (active)
        gd.addLayer(float(sc_cm),    ecal_scint, True)
        # PbWO4 (passive)
        gd.addLayer(float(pbwo4_cm), ecal_pbwo4, False)
        if cost_tracker is not None:
            cost_tracker.add(ecal_pb,    pb_cm)
            cost_tracker.add(ecal_scint, sc_cm)
            cost_tracker.add(ecal_pbwo4, pbwo4_cm)

    ecal_len = float(ecal_pairs) * (float(pb_cm) + float(sc_cm) + float(pbwo4_cm))

    # Optional scint end-cap to avoid absorber→absorber boundary
    if add_scint_endcap:
        gd.addLayer(float(sc_cm), ecal_scint, True)
        if cost_tracker is not None:
            cost_tracker.add(ecal_scint, sc_cm)
        ecal_len += float(sc_cm)

    # ---------------------------
    # HCAL (transition → mid → back)
    # ---------------------------
    def _add_section(n_pairs: int, t_abs: float, t_act: float) -> None:
        for _ in range(int(n_pairs)):
            gd.addLayer(float(t_abs), hcal_absorber, False)
            gd.addLayer(float(t_act), hcal_active,   bool(sensitive_active_only))
            if cost_tracker is not None:
                cost_tracker.add(hcal_absorber, t_abs)
                cost_tracker.add(hcal_active,   t_act)

    _add_section(trans_pairs, fe_trans, sc_trans)
    _add_section(mid_pairs,   fe_mid,   sc_mid)
    _add_section(back_pairs,  fe_back,  sc_back)

    total_len = (
        ecal_len
        + float(trans_pairs) * (float(fe_trans) + float(sc_trans))
        + float(mid_pairs)   * (float(fe_mid)   + float(sc_mid))
        + float(back_pairs)  * (float(fe_back)  + float(sc_back))
    )

    # Optional shim (passive Fe) to reach target_total_len_cm
    leftover = float(target_total_len_cm) - float(total_len)
    if leftover > 1e-6:
        gd.addLayer(float(leftover), hcal_absorber, False)
        if cost_tracker is not None:
            cost_tracker.add(hcal_absorber, leftover)
        total_len += float(leftover)

    specs: Dict[str, float] = {
        # ECAL
        "ecal_pairs": float(ecal_pairs),
        "pb_cm": float(pb_cm), "sc_cm": float(sc_cm), "pbwo4_cm": float(pbwo4_cm),
        "scint_endcap": bool(add_scint_endcap),
        "ecal_len_cm": float(ecal_len),
        # HCAL
        "trans_pairs": float(trans_pairs), "fe_trans": float(fe_trans), "sc_trans": float(sc_trans),
        "mid_pairs":   float(mid_pairs),   "fe_mid":   float(fe_mid),   "sc_mid":   float(sc_mid),
        "back_pairs":  float(back_pairs),  "fe_back":  float(fe_back),  "sc_back":  float(sc_back),
        # Totals
        "total_len_cm": float(total_len),
        # Convenience for sims: use scint thickness (from ECAL) as per-layer thickness
        "ecal_slice_cm": float(sc_cm),
    }

    return gd, specs