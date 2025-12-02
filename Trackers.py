from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from math import pi

# -----------------------------
# Material price list (CHF/(cm·m^2))
# -----------------------------
# If you add 1 cm of Pb over 1 m², it costs 300 CHF.
COST_CHF_PER_CM_M2: Dict[str, float] = {
    "G4_POLYSTYRENE": 0.0,
    "G4_Pb":          300.0,
    "G4_Fe":           50.0,
    "G4_W":          6000.0,
    "G4_Cu":          800.0,
    "G4_BRASS":       200.0,
    "G4_PbWO4":     30000.0,
}

# -----------------------------
# Material properties for X0 and λI (cm)
# -----------------------------
MATERIAL_PROP: Dict[str, Dict[str, float]] = {
    #           X0_cm   lambdaI_cm
    "G4_POLYSTYRENE": {"X0_cm": 42.4, "lambdaI_cm": 77.0},
    "G4_Pb":          {"X0_cm": 0.56, "lambdaI_cm": 17.1},
    "G4_Fe":          {"X0_cm": 1.76, "lambdaI_cm": 16.8},
    "G4_W":           {"X0_cm": 0.35, "lambdaI_cm": 9.6},
    "G4_Cu":          {"X0_cm": 1.43, "lambdaI_cm": 15.3},
    "G4_BRASS":       {"X0_cm": 1.50, "lambdaI_cm": 15.0}, # approx
    "G4_PbWO4":       {"X0_cm": 0.89, "lambdaI_cm": 20.7},
}


# --- convenience lookups (expected by Design.py) ---
X0_CM = {k: v["X0_cm"] for k, v in MATERIAL_PROP.items()}
LAMBDA_INT_CM = {k: v["lambdaI_cm"] for k, v in MATERIAL_PROP.items()}


# -----------------------------
# Transverse area helpers
# -----------------------------
def area_rect_m2(width_cm: float, height_cm: float) -> float:
    """m² for a 50×50 cm slab -> area_rect_m2(50,50)=0.25"""
    return float(width_cm) * float(height_cm) * 1e-4

def area_cyl_m2(radius_cm: float) -> float:
    """m² for a right circular cylinder face (π r²)."""
    r_m = float(radius_cm) * 1e-2
    return pi * r_m * r_m

# -----------------------------
# Primitive cost computation
# -----------------------------
def cost_of_layer(thickness_cm: float, material: str, area_m2: float) -> float:
    """cost = thickness_cm × area_m2 × unit_price."""
    try:
        rate = float(COST_CHF_PER_CM_M2[material])
    except KeyError as e:
        raise KeyError(f"Unknown material for cost model: {material}") from e
    return float(thickness_cm) * float(area_m2) * rate

# -----------------------------
# Cost + X0/λI tracker
# -----------------------------
@dataclass
class CostTracker:
    """
    Accumulates:
      • thickness per material (cm)
      • CHF per material
      • total X0 and λI equivalents (both per material and totals)

    API stays the same:
      add(), add_pair(), add_period(), summary(), pretty_print()
    """
    area_m2: float

    # per-material accumulators
    by_material_cm: Dict[str, float] = field(default_factory=dict)
    by_material_chf: Dict[str, float] = field(default_factory=dict)
    by_material_X0: Dict[str, float] = field(default_factory=dict)        # in units of X0
    by_material_lambdaI: Dict[str, float] = field(default_factory=dict)   # in units of λI

    # totals
    total_length_cm: float = 0.0
    total_cost_chf: float = 0.0
    total_X0: float = 0.0
    total_lambdaI: float = 0.0

    # --- configuration helpers ---
    def set_price(self, material: str, chf_per_cm_m2: float) -> None:
        """Override the price list entry."""
        COST_CHF_PER_CM_M2[material] = float(chf_per_cm_m2)

    def set_material_props(self, material: str, X0_cm: float, lambdaI_cm: float) -> None:
        """Override X0 and λI for a material (cm)."""
        MATERIAL_PROP[material] = {"X0_cm": float(X0_cm), "lambdaI_cm": float(lambdaI_cm)}

    # --- internal checks ---
    def _check_material(self, material: str) -> None:
        if material not in COST_CHF_PER_CM_M2:
            raise KeyError(f"Unknown material for cost model: {material}")
        if material not in MATERIAL_PROP:
            raise KeyError(f"Missing MATERIAL_PROP entry for: {material}")

    # --- accumulation API ---
    def add(self, material: str, thickness_cm: float, count: int = 1) -> None:
        """
        Add a homogeneous layer (or the same layer repeated).
        Example: add("G4_Pb", 0.15, count=96) → 96 layers of 1.5 mm Pb.
        """
        self._check_material(material)

        tcm = float(thickness_cm) * int(count)
        chf = cost_of_layer(tcm, material, self.area_m2)

        # convert to X0 and λI units
        props = MATERIAL_PROP[material]
        x0_units = tcm / float(props["X0_cm"])
        li_units = tcm / float(props["lambdaI_cm"])

        # per-material
        self.by_material_cm[material] = self.by_material_cm.get(material, 0.0) + tcm
        self.by_material_chf[material] = self.by_material_chf.get(material, 0.0) + chf
        self.by_material_X0[material] = self.by_material_X0.get(material, 0.0) + x0_units
        self.by_material_lambdaI[material] = self.by_material_lambdaI.get(material, 0.0) + li_units

        # totals
        self.total_length_cm += tcm
        self.total_cost_chf += chf
        self.total_X0 += x0_units
        self.total_lambdaI += li_units

    def add_pair(self, layers: Tuple[str, float, str, float], count: int = 1) -> None:
        """
        Add (absorber + scint) as one “period”, repeated.
        Example: add_pair(("G4_Pb", 0.15, "G4_POLYSTYRENE", 0.10), count=96).
        """
        m1, t1, m2, t2 = layers
        self.add(m1, t1, count=count)
        self.add(m2, t2, count=count)

    def add_period(self, spec: List[Tuple[str, float]], count: int = 1) -> None:
        """
        period = [("G4_Fe", 0.20), ("G4_POLYSTYRENE", 0.10), ...]
        ct.add_period(period, count=200)
        """
        for _ in range(int(count)):
            for mat, tcm in spec:
                self.add(mat, tcm, count=1)

    # --- reporting ---
    def summary(self) -> Dict:
        mats = sorted(set().union(
            self.by_material_cm.keys(),
            self.by_material_chf.keys(),
            self.by_material_X0.keys(),
            self.by_material_lambdaI.keys()
        ))
        by_mat = {
            m: {
                "total_cm": self.by_material_cm.get(m, 0.0),
                "total_X0": self.by_material_X0.get(m, 0.0),
                "total_lambdaI": self.by_material_lambdaI.get(m, 0.0),
                "total_cost_chf": self.by_material_chf.get(m, 0.0),
                "price_chf_per_cm_m2": COST_CHF_PER_CM_M2[m],
                "X0_cm": MATERIAL_PROP[m]["X0_cm"],
                "lambdaI_cm": MATERIAL_PROP[m]["lambdaI_cm"],
            }
            for m in mats
        }
        return {
            "area_m2": self.area_m2,
            "by_material": by_mat,
            "total_length_cm": self.total_length_cm,
            "total_X0": self.total_X0,
            "total_lambdaI": self.total_lambdaI,
            "total_cost_chf": self.total_cost_chf,
        }

    def pretty_print(self, title: str = "Cost breakdown (with X0 & λI)") -> None:
        s = self.summary()
        print(f"=== {title} (area = {s['area_m2']:.4f} m^2) ===")
        for mat, row in s["by_material"].items():
            rate = row["price_chf_per_cm_m2"]
            print(
                f"{mat:>15}: {row['total_cm']:7.2f} cm"
                f" | {row['total_X0']:6.2f} X0"
                f" | {row['total_lambdaI']:6.2f} λI"
                f" | {rate:8.2f} CHF/(cm·m²)"
                f" -> {row['total_cost_chf']:10.2f} CHF"
                f"   (X0={row['X0_cm']:.3f} cm, λI={row['lambdaI_cm']:.2f} cm)"
            )
        print("-" * 78)
        print(f"TOTAL length: {s['total_length_cm']:.2f} cm")
        print(f"TOTAL X0:     {s['total_X0']:.2f}")
        print(f"TOTAL λI:     {s['total_lambdaI']:.2f}")
        print(f"TOTAL cost:   {s['total_cost_chf']:.2f} CHF")
