# viz_event.py (or just put this in a notebook cell)
from typing import Dict, Tuple, Optional
import math
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# Material → color map (tweak as you like)
MAT_COLOR: Dict[str, str] = {
    "G4_POLYSTYRENE": "#66c2a5",
    "G4_Pb":          "#b2182b",
    "G4_Fe":          "#2166ac",
    "G4_W":           "#542788",
    "G4_Cu":          "#a6611a",
    "G4_BRASS":       "#d95f02",
    "G4_PbWO4":       "#ffd92f",
}

def _layer_edges_mm(gd) -> Tuple[list, list, list]:
    """
    Return (z_edges_mm, z_centers_mm, layer_info) where:
      - z_edges_mm: cumulative z boundaries in mm
      - z_centers_mm: center z of each layer (mm)
      - layer_info: list of (thickness_mm, material, sensitive)
    """
    z = 0.0
    edges = [0.0]
    info = []
    for L in gd.layers:
        t_mm = float(L.thickness_cm) * 10.0
        info.append((t_mm, L.material, bool(L.sensitive)))
        z += t_mm
        edges.append(z)
    centers = [(edges[i] + edges[i+1]) * 0.5 for i in range(len(edges)-1)]
    return edges, centers, info

def display_event(
    gd,
    particle: str = "pi+",
    energy_GeV: float = 1.0,
    n_events: int = 1,
    threads: int = 1,
    *,
    show_hits: bool = True,
    figsize: Tuple[int, int] = (10, 6),
    title: Optional[str] = None,
):
    """
    Visualize the layered geometry along z and (optionally) one event's hits.

    Parameters
    ----------
    gd : GeometryDescriptor
        Your geometry with .layers (thickness_cm, material, sensitive)
    particle : str
        PDG name, e.g. "pi+", "gamma", "e-", "proton", ...
    energy_GeV : float
        Kinetic energy in GeV (the g4python bridge expects GeV)
    n_events : int
        # events to run (1 is typical for a quick look)
    threads : int
        G4 threads (1 keeps logs quieter)
    show_hits : bool
        If True, try to import g4python and overlay hits
    figsize : (w, h)
        Figure size
    title : str | None
        Figure title override
    """
    # Build geometry view (z in mm)
    z_edges, z_centers, layer_info = _layer_edges_mm(gd)
    total_z = z_edges[-1] if z_edges else 0.0

    fig, (ax_geom, ax_hits) = plt.subplots(
        2, 1, figsize=figsize, gridspec_kw={"height_ratios": [1, 1.2]}
    )

    # --- Geometry panel ---
    ax_geom.set_xlim(0, max(total_z, 1.0))
    ax_geom.set_ylim(0, 1)
    ax_geom.set_yticks([])
    ax_geom.set_xlabel("z [mm]")
    ax_geom.set_title(title or f"Geometry & event display — {particle} @ {energy_GeV:g} GeV")

    # draw layers as horizontal bars (single row, y from 0→1)
    for i, (t_mm, mat, sens) in enumerate(layer_info):
        z0 = z_edges[i]
        color = MAT_COLOR.get(mat, "#cccccc")
        hatch = "////" if sens else None
        rect = Rectangle((z0, 0.1), t_mm, 0.8, facecolor=color, edgecolor="black", hatch=hatch, linewidth=0.6)
        ax_geom.add_patch(rect)

    # minimal legend (unique materials)
    seen = {}
    for _, mat, sens in layer_info:
        key = (mat, sens)
        if key not in seen:
            seen[key] = (MAT_COLOR.get(mat, "#cccccc"), sens)
    # build legend handles
    handles = []
    labels = []
    for (mat, sens), (c, sflag) in seen.items():
        patch = Rectangle((0,0), 1, 1, facecolor=c, edgecolor="black", hatch=("////" if sflag else None))
        handles.append(patch)
        labels.append(f"{mat}" + (" (sensitive)" if sflag else ""))
    if handles:
        ax_geom.legend(handles, labels, loc="upper right", frameon=True)

    # --- Hits panel ---
    ax_hits.set_xlim(0, max(total_z, 1.0))
    ax_hits.set_xlabel("z [mm]")
    ax_hits.set_ylabel("radius r = √(x²+y²) [mm]")
    ax_hits.grid(True, alpha=0.3)

    df = None
    if show_hits:
        try:
            import os
            os.environ["G4FORCENUMBEROFTHREADS"] = str(int(threads))

            import g4python as g4p  # your pybind11 module
            df = g4p.simulate_df(str(particle), float(energy_GeV), int(n_events))
        except Exception as e:
            ax_hits.text(0.02, 0.95, f"no hits (sim failed?)\n{e}", transform=ax_hits.transAxes,
                         va="top", ha="left", fontsize=9, color="red")

    if df is not None and len(df):
        # radius vs z with bubble area ~ E_dep
        import numpy as np
        z = df["z_mm"].to_numpy()
        x = df["x_mm"].to_numpy()
        y = df["y_mm"].to_numpy()
        e = df["edep_MeV"].to_numpy()

        r = np.sqrt(x*x + y*y)
        # marker size scaling: a gentle function of edep (MeV)
        s = np.clip(e, 0, np.percentile(e, 95))  # clip long tail for visibility
        s = 10.0 + 60.0 * (s / (s.max() if s.max() > 0 else 1.0))

        ax_hits.scatter(z, r, s=s, alpha=0.5, linewidths=0, label="hits")
        ax_hits.legend(loc="upper right")
    else:
        ax_hits.text(0.02, 0.95, "No hits to plot", transform=ax_hits.transAxes,
                     va="top", ha="left", fontsize=9, color="gray")

    plt.tight_layout()
    plt.show()
