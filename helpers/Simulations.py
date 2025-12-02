# Simulations.py — direct calls (no run_batch)

from typing import Optional, Tuple, List
import os, math, random
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# direct bridge
import g4python as g4p


def _simulate_once_direct(
    particle: str,
    energy_mev: float,
    n_events: int,
    threads: Optional[int] = 1,
) -> pd.DataFrame:
    """
    Direct call to the pybind bridge (no batching, no files).
    Returns a DataFrame with columns: event, edep_MeV, x_mm, y_mm, z_mm
    """
    if threads is not None:
        # Geant4 MT: keep logs quiet & deterministic
        os.environ["G4FORCENUMBEROFTHREADS"] = str(int(threads))
    df = g4p.simulate_df(str(particle), float(energy_mev), int(n_events))
    # ensure schema is stable
    for col in ("event", "edep_MeV", "x_mm", "y_mm", "z_mm"):
        if col not in df.columns:
            df[col] = pd.NA
    return df[["event", "edep_MeV", "x_mm", "y_mm", "z_mm"]]


def run_parametric_sample_from_gd(
    gd,                             # GeometryDescriptor (kept for API symmetry)
    n_events: int = 300,
    *,
    particle: str = "gamma",
    e_min_GeV: float = 1.0,
    e_max_GeV: float = 100.0,
    layer_thick_cm: float = 0.20,   # thickness of sensitive layer for layer-binning
    threads: int = 1,
    seed: Optional[int] = None,
    max_chunks: int = 10,
    events_per_call: int = 100,     # how many events to request per simulate_df call
) -> pd.DataFrame:
    """
    Uniformly sample energies in [e_min_GeV, e_max_GeV], call g4python.simulate_df
    several times, and concatenate results. No files, no run_batch.
    Adds 'E_MeV' per-chunk and stores 'layer_thick_cm' in df.attrs.
    """
    if seed is not None:
        random.seed(seed)

    n_events = int(n_events)
    if n_events <= 0:
        return pd.DataFrame(columns=["event", "edep_MeV", "x_mm", "y_mm", "z_mm", "E_MeV"])

    # decide the call plan
    events_per_call = max(1, int(events_per_call))
    n_calls = math.ceil(n_events / events_per_call)
    n_calls = min(n_calls, int(max_chunks))
    base = n_events // n_calls
    rem  = n_events %  n_calls
    plan: List[int] = [base + (1 if i < rem else 0) for i in range(n_calls)]

    parts: List[pd.DataFrame] = []
    for i, nev in enumerate(plan, start=1):
        if nev <= 0:
            continue
        E_GeV = random.uniform(float(e_min_GeV), float(e_max_GeV))
        E_MeV = E_GeV * 1000.0
        print(f"[{i}/{n_calls}] {particle} @ {E_GeV:.2f} GeV × {nev} events (threads={threads})")
        df = _simulate_once_direct(particle, E_MeV, nev, threads=threads)
        if not df.empty:
            df = df.copy()
            df["E_MeV"] = E_MeV
            parts.append(df)

    if parts:
        out = pd.concat(parts, ignore_index=True)
    else:
        out = pd.DataFrame(columns=["event", "edep_MeV", "x_mm", "y_mm", "z_mm", "E_MeV"])

    out.attrs["layer_thick_cm"] = float(layer_thick_cm)
    return out


def plot_mean_bar(
    df: pd.DataFrame,
    title: str = "Mean energy deposit per layer",
    layer_thick_cm: Optional[float] = None,
    ax: Optional[plt.Axes] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Bin hits along z into layers of thickness = layer_thick_cm (cm), then plot mean
    E_dep per layer as a bar chart. Returns (layer_indices, mean_edep_per_layer).
    """
    if df.empty:
        print("plot_mean_bar: dataframe is empty; nothing to plot.")
        return np.array([]), np.array([])

    if layer_thick_cm is None:
        layer_thick_cm = float(df.attrs.get("layer_thick_cm", 0.20))
    dz_mm = float(layer_thick_cm) * 10.0

    z = df["z_mm"].to_numpy(dtype=float)
    e = df["edep_MeV"].to_numpy(dtype=float)

    z0 = z.min()
    layer_idx = np.floor((z - z0) / dz_mm).astype(int)
    n_layers = int(layer_idx.max()) + 1

    sums = np.bincount(layer_idx, weights=e, minlength=n_layers).astype(float)
    counts = np.bincount(layer_idx, minlength=n_layers).astype(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        means = np.where(counts > 0, sums / counts, 0.0)

    if ax is None:
        _, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(n_layers)
    ax.bar(x, means, width=0.9)
    ax.set_xlabel("Layer index (from ECAL front)")
    ax.set_ylabel("⟨E_dep⟩ per hit [MeV]")
    ax.set_title(title)
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.show()

    return x, means
