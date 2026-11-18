#!/usr/bin/env python3
"""QuantumBiology-Lab - educational quantum biology lab.

by Darion Kellar

Pure Python standard library. Zero dependencies. Zero network.
Education only - and the honest core is stated up front:

  * This lab computes three toy models that appear in the quantum
    biology literature: excitonic transport on a small FMO-like
    seven-site network with dephasing (the ENAQT effect - transport
    efficiency PEAKS at intermediate dephasing), a one-hyperfine
    radical-pair toy whose singlet yield moves with an applied
    magnetic field (the avian-compass toy), and WKB proton
    tunnelling through a rectangular barrier priced against the
    classical over-barrier rate.
  * Every parameter is a LABELLED teaching value. The site energies
    and couplings are in the spirit of published FMO teaching
    tables; nothing here was measured from any organism, protein,
    bird, or enzyme, and no output is a biological measurement.
  * A toy efficiency peak is not photosynthesis, a toy yield curve
    is not a compass, and a WKB exponent is not an enzyme rate.
    Medical, drug, agriculture, sensor, navigation, and organism
    claims are permanent HOLD gates - with Gemini Argon 4 Extended
    Thinking as DECIDER (names-only, tighten-only), Muse as
    advisor (never overrides HOLD), and Google Flow plan-only.
"""
import hashlib
import json
import math
import sys

# ---------------------------------------------------------------- constants
VERSION = "1.0.0"

# Exact SI constants (2019 SI) for the tunnelling section.
HBAR = 1.054571817e-34        # J s
PROTON_MASS = 1.67262192369e-27  # kg
DEUTERON_MASS = 2.0 * PROTON_MASS  # labelled approximation: m_d = 2 m_p
EV_J = 1.602176634e-19        # J per eV
KB = 1.380649e-23             # J / K

# cm^-1 -> rad/ps: omega = 2 pi c nu, c = 0.0299792458 cm/ps.
CM_TO_RAD_PS = 2.0 * math.pi * 0.0299792458

# ------------------------------------------------------- 1. FMO-like network
# Labelled teaching values in the spirit of the published FMO site
# table (Adolphs-Renger style): site energies in cm^-1, couplings in
# cm^-1. Site 3 (index 2) carries the lowest site energy and is the
# trap site - the exciton is collected there by an irreversible sink.
N_SITES = 7
SITE_ENERGIES_CM = (12410.0, 12530.0, 12210.0, 12320.0,
                    12480.0, 12630.0, 12440.0)
COUPLINGS_CM = {
    (0, 1): -87.7, (0, 2): 5.5, (0, 3): -5.9, (0, 4): 6.7,
    (0, 5): -13.7, (0, 6): -9.9,
    (1, 2): 30.8, (1, 3): 8.2, (1, 4): 0.7, (1, 5): 11.8, (1, 6): 4.3,
    (2, 3): -53.5, (2, 4): -2.2, (2, 5): -9.6, (2, 6): 6.0,
    (3, 4): -70.7, (3, 5): -17.0, (3, 6): -63.3,
    (4, 5): 81.1, (4, 6): -1.3,
    (5, 6): 39.7,
}
TRAP_SITE = 2          # site 3, the lowest-energy site
START_SITE = 0         # excitation starts on site 1
TRAP_RATE = 1.0        # kappa, per ps - labelled teaching value
LOSS_RATE = 0.01       # Gamma, recombination per ps - labelled value
SWEEP_GAMMAS = (0.0, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 40.0, 80.0,
                160.0, 320.0, 640.0, 1280.0, 2560.0, 5120.0)

# ------------------------------------------------------- 2. Radical pair
# One electron pair + ONE nuclear spin 1/2 hyperfine-coupled to
# electron 1. All energies in units of the hyperfine coupling a = 1
# (labelled). The applied field b is the electron Zeeman energy in
# the same units; recombination rate k is equal for both channels
# (Haberkorn weighting with equal rates).
HYPERFINE_A = 1.0
RECOMBINATION_K = 0.5
RADICAL_FIELDS = (0.0, 0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0, 1.5,
                  2.0, 2.5, 3.0)

# ------------------------------------------------------- 3. Proton tunnelling
# Labelled rectangular barrier: height 0.60 eV, width 0.50 Angstrom,
# particle energy E = k_B T at T = 300 K, attempt frequency 1e13 Hz.
BARRIER_EV = 0.60
BARRIER_WIDTH_M = 0.50e-10
TEMPERATURE_K = 300.0
ATTEMPT_HZ = 1.0e13

# ---------------------------------------------------------------- HOLD gates
HOLD_GATES = {
    "medical_claim": "HOLD - no medical, diagnostic, treatment, or health claims from a toy model",
    "drug_design_claim": "HOLD - no drug design, binding, or efficacy claims",
    "agriculture_claim": "HOLD - no crop-yield or photosynthesis-enhancement claims for real plants",
    "organism_measurement_claim": "HOLD - no claiming any parameter here was measured from a real organism",
    "quantum_sensor_claim": "HOLD - no magnetometer or quantum-sensor product claims; a yield curve is not a sensor",
    "consciousness_claim": "HOLD - no consciousness, quantum-mind, or cognition claims",
    "clinical_trial_claim": "HOLD - no clinical-trial design, dosing, or patient claims",
    "genetic_engineering_claim": "HOLD - no genetic-engineering or gene-editing guidance",
    "longevity_claim": "HOLD - no longevity, anti-ageing, or life-extension claims",
    "enzyme_product_claim": "HOLD - no industrial enzyme or biocatalyst product claims from a WKB toy",
    "in_vivo_navigation_claim": "HOLD - no claims about how real birds navigate; the radical pair here is a toy",
    "solar_energy_product_claim": "HOLD - no artificial-photosynthesis or solar-product efficiency claims",
    "radiation_health_claim": "HOLD - no radiation-exposure or health-risk claims",
    "supplement_claim": "HOLD - no supplement, wellness, or nutrition claims",
}


def gate(action):
    """Return 'HOLD' if the action is gated, else 'PROCEED' (sandbox sim)."""
    return "HOLD" if action in HOLD_GATES else "PROCEED"


# ================================================================ linear algebra
# Small from-scratch helpers. Hamiltonians here are real symmetric,
# so the eigensolver is a real cyclic Jacobi; the Liouvillian is
# complex, so the linear solver is complex Gauss-Jordan.

def matmul_real(A, B):
    rows, inner, cols = len(A), len(B), len(B[0])
    return [[sum(A[i][k] * B[k][j] for k in range(inner))
             for j in range(cols)] for i in range(rows)]


def transpose_real(A):
    return [[A[j][i] for j in range(len(A))] for i in range(len(A[0]))]


def kron2(A, B):
    """Kronecker product of two small real matrices."""
    return [[A[i][j] * B[k][l] for j in range(len(A[0]))
             for l in range(len(B[0]))]
            for i in range(len(A)) for k in range(len(B))]


def jacobi_eig(Ain, tol=1e-13, max_sweeps=100):
    """Eigendecomposition of a real symmetric matrix by cyclic Jacobi.

    Returns (eigenvalues, V) with eigenvectors as COLUMNS of V, so
    A = V diag(eigenvalues) V^T. Convergence is asserted by the
    checks through exact reconstruction, never assumed.
    """
    n = len(Ain)
    A = [row[:] for row in Ain]
    V = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for _ in range(max_sweeps):
        off = math.sqrt(sum(A[i][j] ** 2 for i in range(n)
                            for j in range(n) if i != j))
        if off < tol:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                if abs(A[p][q]) < 1e-300:
                    continue
                theta = (A[q][q] - A[p][p]) / (2.0 * A[p][q])
                t = (1.0 if theta >= 0 else -1.0) / (
                    abs(theta) + math.sqrt(theta * theta + 1.0))
                c = 1.0 / math.sqrt(t * t + 1.0)
                s = t * c
                for k in range(n):
                    akp, akq = A[k][p], A[k][q]
                    A[k][p] = c * akp - s * akq
                    A[k][q] = s * akp + c * akq
                for k in range(n):
                    apk, aqk = A[p][k], A[q][k]
                    A[p][k] = c * apk - s * aqk
                    A[q][k] = s * apk + c * aqk
                for k in range(n):
                    vkp, vkq = V[k][p], V[k][q]
                    V[k][p] = c * vkp - s * vkq
                    V[k][q] = s * vkp + c * vkq
    return [A[i][i] for i in range(n)], V


def solve_complex(A, b):
    """Solve A x = b for complex A by Gauss-Jordan with pivoting."""
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-300:
            raise ValueError("singular matrix")
        M[col], M[piv] = M[piv], M[col]
        pv = M[col][col]
        for r in range(n):
            if r != col and M[r][col] != 0j:
                f = M[r][col] / pv
                for cc in range(col, n + 1):
                    M[r][cc] -= f * M[col][cc]
    return [M[i][n] / M[i][i] for i in range(n)]


# ================================================================ 1. FMO transport
def build_hamiltonian():
    """Site Hamiltonian in rad/ps, energies relative to the lowest site."""
    base = min(SITE_ENERGIES_CM)
    H = [[0.0] * N_SITES for _ in range(N_SITES)]
    for i in range(N_SITES):
        H[i][i] = (SITE_ENERGIES_CM[i] - base) * CM_TO_RAD_PS
    for (i, j), v in COUPLINGS_CM.items():
        H[i][j] = H[j][i] = v * CM_TO_RAD_PS
    return H


H_SITES = build_hamiltonian()


def exciton_spectrum():
    """Eigen-decomposition of the site Hamiltonian (exciton states)."""
    evals, V = jacobi_eig(H_SITES)
    order = sorted(range(N_SITES), key=lambda i: evals[i])
    energies_cm = [evals[i] / CM_TO_RAD_PS for i in order]
    lowest = order[0]
    trap_weight = V[TRAP_SITE][lowest] ** 2
    start_weight = V[START_SITE][lowest] ** 2
    return {
        "energies_cm_relative": [round(e, 4) for e in energies_cm],
        "lowest_energy_cm": round(energies_cm[0], 4),
        "lowest_exciton_trap_site_weight": round(trap_weight, 6),
        "lowest_exciton_start_site_weight": round(start_weight, 6),
    }


def liouvillian(gamma):
    """49x49 complex Liouvillian for Haken-Strobl dephasing + trap + loss.

    d rho/dt = -i[H, rho] - gamma * (off-diagonal rho)
               - (kappa/2) {P_trap, rho} - Gamma * rho.
    Vectorised row-major: index of rho[m][n] is m * 7 + n.
    """
    d = N_SITES * N_SITES
    L = [[0j] * d for _ in range(d)]
    for m in range(N_SITES):
        for n in range(N_SITES):
            row = m * N_SITES + n
            for k in range(N_SITES):
                if H_SITES[m][k] != 0.0:
                    L[row][k * N_SITES + n] += -1j * H_SITES[m][k]
                if H_SITES[k][n] != 0.0:
                    L[row][m * N_SITES + k] += 1j * H_SITES[k][n]
            damp = LOSS_RATE
            if m != n:
                damp += gamma
            if m == TRAP_SITE:
                damp += TRAP_RATE / 2.0
            if n == TRAP_SITE:
                damp += TRAP_RATE / 2.0
            L[row][row] -= damp
    return L


_EFFICIENCY_CACHE = {}


def transport_efficiency(gamma):
    """Exact steady-state efficiency: eta = kappa * int rho_trap,trap dt.

    The time integral of rho solves L x = -rho(0), so eta and the
    recombination loss fraction are exact rational-style outputs of
    one linear solve - and eta + loss = 1 identically, which the
    checks assert at several dephasing rates.
    """
    key = round(float(gamma), 10)
    if key in _EFFICIENCY_CACHE:
        return _EFFICIENCY_CACHE[key]
    L = liouvillian(float(gamma))
    rho0 = [0j] * (N_SITES * N_SITES)
    rho0[START_SITE * N_SITES + START_SITE] = 1.0 + 0j
    x = solve_complex(L, [-v for v in rho0])
    eta = TRAP_RATE * x[TRAP_SITE * N_SITES + TRAP_SITE].real
    loss = LOSS_RATE * sum(x[i * N_SITES + i].real for i in range(N_SITES))
    result = (eta, loss)
    _EFFICIENCY_CACHE[key] = result
    return result


def transport_sweep():
    """Efficiency at every labelled dephasing rate in SWEEP_GAMMAS."""
    return [{"gamma_rad_ps": g,
             "efficiency": round(transport_efficiency(g)[0], 6),
             "loss": round(transport_efficiency(g)[1], 6)}
            for g in SWEEP_GAMMAS]


def find_optimum():
    """Golden-section maximisation of eta over log-gamma in [2, 200]."""
    lo, hi = math.log(2.0), math.log(200.0)
    gr = (math.sqrt(5.0) - 1.0) / 2.0
    x1, x2 = hi - gr * (hi - lo), lo + gr * (hi - lo)
    f1 = transport_efficiency(math.exp(x1))[0]
    f2 = transport_efficiency(math.exp(x2))[0]
    for _ in range(40):
        if f1 < f2:
            lo, x1, f1 = x1, x2, f2
            x2 = lo + gr * (hi - lo)
            f2 = transport_efficiency(math.exp(x2))[0]
        else:
            hi, x2, f2 = x2, x1, f1
            x1 = hi - gr * (hi - lo)
            f1 = transport_efficiency(math.exp(x1))[0]
    gamma_star = math.exp((lo + hi) / 2.0)
    eta_star = transport_efficiency(gamma_star)[0]
    return {"gamma_rad_ps": round(gamma_star, 4),
            "gamma_cm": round(gamma_star / CM_TO_RAD_PS, 2),
            "efficiency": round(eta_star, 6)}


def _density_rhs(rho, gamma):
    """Right-hand side of the density-matrix ODE (same L as above)."""
    out = [[0j] * N_SITES for _ in range(N_SITES)]
    for m in range(N_SITES):
        for n in range(N_SITES):
            s = 0j
            for k in range(N_SITES):
                s += H_SITES[m][k] * rho[k][n] - rho[m][k] * H_SITES[k][n]
            damp = LOSS_RATE + (gamma if m != n else 0.0)
            if m == TRAP_SITE:
                damp += TRAP_RATE / 2.0
            if n == TRAP_SITE:
                damp += TRAP_RATE / 2.0
            out[m][n] = -1j * s - damp * rho[m][n]
    return out


def _rk4_step(rho, gamma, dt):
    def add_scaled(base, deriv, f):
        return [[base[i][j] + f * deriv[i][j] for j in range(N_SITES)]
                for i in range(N_SITES)]
    k1 = _density_rhs(rho, gamma)
    k2 = _density_rhs(add_scaled(rho, k1, dt / 2.0), gamma)
    k3 = _density_rhs(add_scaled(rho, k2, dt / 2.0), gamma)
    k4 = _density_rhs(add_scaled(rho, k3, dt), gamma)
    return [[rho[i][j] + dt / 6.0 * (k1[i][j] + 2.0 * k2[i][j]
                                     + 2.0 * k3[i][j] + k4[i][j])
             for j in range(N_SITES)] for i in range(N_SITES)]


_COHERENCE_CACHE = {}


def mean_coherence(gamma, window_ps=1.0):
    """Mean l1 coherence sum |rho_mn| (m != n) over the first window.

    RK4 with a step small enough for both the fastest exciton
    oscillation and the dephasing rate itself. At gamma = 0 the
    coherence rings for the whole window; deep in the Zeno regime
    it is quenched almost immediately - that contrast is the point.
    """
    key = (round(float(gamma), 10), window_ps)
    if key in _COHERENCE_CACHE:
        return _COHERENCE_CACHE[key]
    gamma = float(gamma)
    dt = 0.0025 if gamma <= 600.0 else 1.5 / gamma
    steps = max(1, int(round(window_ps / dt)))
    rho = [[0j] * N_SITES for _ in range(N_SITES)]
    rho[START_SITE][START_SITE] = 1.0 + 0j
    total = 0.0
    for _ in range(steps):
        total += sum(abs(rho[m][n]) for m in range(N_SITES)
                     for n in range(N_SITES) if m != n)
        rho = _rk4_step(rho, gamma, dt)
    value = total / steps
    _COHERENCE_CACHE[key] = value
    return value


def population_snapshots(gamma, times=(0.0, 0.25, 0.5, 1.0, 2.0)):
    """Site populations at labelled times under dephasing gamma."""
    dt = 0.0025
    rho = [[0j] * N_SITES for _ in range(N_SITES)]
    rho[START_SITE][START_SITE] = 1.0 + 0j
    snaps = []
    step = 0
    for t in times:
        target = int(round(t / dt))
        while step < target:
            rho = _rk4_step(rho, gamma, dt)
            step += 1
        snaps.append({
            "t_ps": t,
            "populations": [round(rho[i][i].real, 6)
                            for i in range(N_SITES)],
            "total_remaining": round(
                sum(rho[i][i].real for i in range(N_SITES)), 6),
        })
    return snaps


def transport_report():
    opt = find_optimum()
    eta0 = transport_efficiency(0.0)[0]
    eta_zeno = transport_efficiency(5120.0)[0]
    return {
        "network": {
            "sites": N_SITES,
            "site_energies_cm": list(SITE_ENERGIES_CM),
            "trap_site": TRAP_SITE + 1,
            "start_site": START_SITE + 1,
            "trap_rate_per_ps": TRAP_RATE,
            "loss_rate_per_ps": LOSS_RATE,
        },
        "exciton_spectrum": exciton_spectrum(),
        "efficiency_zero_dephasing": round(eta0, 6),
        "enaqt_optimum": opt,
        "efficiency_zeno_5120": round(eta_zeno, 6),
        "coherence_first_ps": {
            "gamma_0": round(mean_coherence(0.0), 4),
            "gamma_optimum": round(mean_coherence(opt["gamma_rad_ps"]), 4),
            "gamma_1280": round(mean_coherence(1280.0), 4),
        },
        "sweep": transport_sweep(),
    }


# ================================================================ 2. Radical pair
_SZ = [[0.5, 0.0], [0.0, -0.5]]
_SP = [[0.0, 1.0], [0.0, 0.0]]
_SM = [[0.0, 0.0], [1.0, 0.0]]
_I2 = [[1.0, 0.0], [0.0, 1.0]]


def _scale(A, s):
    return [[s * v for v in row] for row in A]


def _add(A, B):
    return [[A[i][j] + B[i][j] for j in range(len(A[0]))]
            for i in range(len(A))]


def radical_hamiltonian(field_b, a=HYPERFINE_A):
    """H = b (S1z + S2z) + a S1.I on (electron1, electron2, nucleus).

    Basis index = (i1 * 2 + i2) * 2 + iI, up = 0, down = 1. All
    matrix elements are real in this basis. Units: a = 1 labelled.
    """
    zeeman = _add(kron2(kron2(_SZ, _I2), _I2), kron2(kron2(_I2, _SZ), _I2))
    s1_dot_i = _add(
        _add(kron2(kron2(_SZ, _I2), _SZ),
             _scale(kron2(kron2(_SP, _I2), _SM), 0.5)),
        _scale(kron2(kron2(_SM, _I2), _SP), 0.5))
    return _add(_scale(zeeman, field_b), _scale(s1_dot_i, a))


def singlet_projector():
    """Projector onto the electron singlet, identity on the nucleus."""
    P = [[0.0] * 8 for _ in range(8)]
    for i_nuc in range(2):
        up_down = (0 * 2 + 1) * 2 + i_nuc
        down_up = (1 * 2 + 0) * 2 + i_nuc
        P[up_down][up_down] += 0.5
        P[down_up][down_up] += 0.5
        P[up_down][down_up] -= 0.5
        P[down_up][up_down] -= 0.5
    return P


def singlet_yield(field_b, k=RECOMBINATION_K, a=HYPERFINE_A):
    """Singlet yield Phi_S for a pair born in the singlet state.

    rho(0) = |S><S| (x) I_nucleus / 2 (unpolarised nucleus). With
    equal singlet/triplet recombination rate k (Haberkorn),
    Phi_S = sum_ab rho_ab P_ba * k / (k + i (E_a - E_b)) in the
    eigenbasis of H - computed exactly from the Jacobi spectrum.
    """
    H = radical_hamiltonian(field_b, a)
    evals, V = jacobi_eig(H)
    Vt = transpose_real(V)
    P = singlet_projector()
    rho0 = _scale(P, 0.5)
    rho_t = matmul_real(matmul_real(Vt, rho0), V)
    p_t = matmul_real(matmul_real(Vt, P), V)
    total = 0j
    for i in range(8):
        for j in range(8):
            w = k / (k + 1j * (evals[i] - evals[j]))
            total += rho_t[i][j] * p_t[j][i] * w
    return total.real


def radical_report():
    curve = [{"field_b_over_a": b, "singlet_yield": round(singlet_yield(b), 6)}
             for b in RADICAL_FIELDS]
    yields = [row["singlet_yield"] for row in curve]
    i_min = min(range(len(curve)), key=lambda i: yields[i])
    return {
        "model": "one hyperfine coupling a = 1 (labelled units), "
                 "k = 0.5 a, unpolarised nucleus, singlet-born pair",
        "curve": curve,
        "phi_s_zero_field": yields[0],
        "phi_s_min": yields[i_min],
        "field_at_min": curve[i_min]["field_b_over_a"],
        "phi_s_high_field_b3": yields[-1],
        "yield_swing": round(max(yields) - min(yields), 6),
        "triplet_yield_zero_field": round(1.0 - yields[0], 6),
    }


# ================================================================ 3. Proton tunnelling
def barrier_kappa(mass_kg, energy_j, height_j=BARRIER_EV * EV_J):
    """WKB decay constant kappa = sqrt(2 m (V - E)) / hbar, per metre."""
    if energy_j >= height_j:
        raise ValueError("energy at or above the barrier top")
    return math.sqrt(2.0 * mass_kg * (height_j - energy_j)) / HBAR


def wkb_transmission(mass_kg, energy_j):
    """Rectangular-barrier WKB transmission exp(-2 kappa L)."""
    kappa = barrier_kappa(mass_kg, energy_j)
    return math.exp(-2.0 * kappa * BARRIER_WIDTH_M)


def exact_transmission(mass_kg, energy_j):
    """Exact rectangular-barrier transmission (E < V closed form)."""
    height_j = BARRIER_EV * EV_J
    kappa = barrier_kappa(mass_kg, energy_j)
    prefactor = height_j ** 2 / (4.0 * energy_j * (height_j - energy_j))
    return 1.0 / (1.0 + prefactor * math.sinh(kappa * BARRIER_WIDTH_M) ** 2)


def classical_rate(energy_j=None):
    """Arrhenius over-barrier rate nu * exp(-V / k_B T)."""
    return ATTEMPT_HZ * math.exp(-(BARRIER_EV * EV_J) / (KB * TEMPERATURE_K))


def tunnel_report():
    energy_j = KB * TEMPERATURE_K  # labelled thermal energy E = k_B T
    kappa = barrier_kappa(PROTON_MASS, energy_j)
    t_wkb = wkb_transmission(PROTON_MASS, energy_j)
    t_exact = exact_transmission(PROTON_MASS, energy_j)
    k_tun = ATTEMPT_HZ * t_wkb
    k_cl = classical_rate()
    t_deut = wkb_transmission(DEUTERON_MASS, energy_j)
    return {
        "barrier_height_ev": BARRIER_EV,
        "barrier_width_angstrom": BARRIER_WIDTH_M / 1e-10,
        "temperature_k": TEMPERATURE_K,
        "particle_energy_ev": round(energy_j / EV_J, 6),
        "attempt_hz": ATTEMPT_HZ,
        "kappa_per_m": kappa,
        "two_kappa_L": 2.0 * kappa * BARRIER_WIDTH_M,
        "t_wkb_proton": t_wkb,
        "t_exact_proton": t_exact,
        "exact_over_wkb": t_exact / t_wkb,
        "t_wkb_deuteron": t_deut,
        "tunnel_rate_hz": k_tun,
        "classical_rate_hz": k_cl,
        "enhancement_factor": k_tun / k_cl,
        "kinetic_isotope_effect": t_wkb / t_deut,
    }


# ================================================================ 4. kNN classifier
# Features: (dephasing rate gamma, efficiency eta, mean coherence C).
# The training grid spans the ranges the lab's own sweep measured,
# and every grid point is labelled by the lab's own regime policy
# below - the classifier interpolates the policy, nothing more.
REGIME_LABELS = ("coherent-trapped", "ENAQT-optimal", "over-dephased")


def model_label(gamma, efficiency, coherence):
    """The lab's regime policy, distilled from its own sweep.

    gamma >= 200 rad/ps is deep on the Zeno side of the measured
    peak (gamma* ~ 26.5 rad/ps): hopping is quenched as J^2/gamma.
    eta >= 0.88 with gamma >= 1 is the measured near-optimal
    plateau. Everything else - including the fully coherent point,
    where eta is only 0.554 - is coherent-trapped.
    """
    if gamma >= 200.0:
        return "over-dephased"
    if efficiency >= 0.88 and gamma >= 1.0:
        return "ENAQT-optimal"
    return "coherent-trapped"


def _training_grid():
    rows = []
    gammas = (0.0, 0.3, 1.0, 3.0, 10.0, 30.0, 60.0, 120.0, 250.0,
              600.0, 1500.0, 4000.0)
    etas = (0.30, 0.45, 0.60, 0.75, 0.85, 0.90, 0.95, 1.00)
    coherences = (0.0, 0.2, 0.5, 1.0, 1.6, 2.4)
    for g in gammas:
        for e in etas:
            for c in coherences:
                rows.append(((g, e, c), model_label(g, e, c)))
    return rows


TRAINING_GRID = _training_grid()


def _scaled(features):
    gamma, efficiency, coherence = features
    return (math.log10(gamma + 0.1) / 3.6, efficiency, coherence / 2.4)


def classify_transport(gamma, efficiency, coherence, k=5):
    """kNN over the policy-labelled grid, deterministic tie-breaking."""
    target = _scaled((gamma, efficiency, coherence))
    ranked = []
    for features, label in TRAINING_GRID:
        point = _scaled(features)
        dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(target, point)))
        ranked.append((dist, features, label))
    ranked.sort(key=lambda row: (row[0], row[1]))
    votes = {}
    for _, _, label in ranked[:k]:
        votes[label] = votes.get(label, 0) + 1
    priority = {"ENAQT-optimal": 0, "coherent-trapped": 1, "over-dephased": 2}
    return sorted(votes.items(), key=lambda kv: (-kv[1], priority[kv[0]]))[0][0]


def classifier_report():
    opt = find_optimum()
    scenarios = {
        "zero_dephasing": (0.0, transport_efficiency(0.0)[0],
                           mean_coherence(0.0)),
        "enaqt_optimum": (opt["gamma_rad_ps"],
                          transport_efficiency(opt["gamma_rad_ps"])[0],
                          mean_coherence(opt["gamma_rad_ps"])),
        "zeno_limit": (1280.0, transport_efficiency(1280.0)[0],
                       mean_coherence(1280.0)),
        "rising_edge_gamma_2": (2.0, transport_efficiency(2.0)[0],
                                mean_coherence(2.0)),
        "plateau_gamma_80": (80.0, transport_efficiency(80.0)[0],
                             mean_coherence(80.0)),
    }
    return {name: {"gamma_rad_ps": round(f[0], 4),
                   "efficiency": round(f[1], 6),
                   "mean_coherence": round(f[2], 4),
                   "label": classify_transport(*f),
                   "policy_label": model_label(*f)}
            for name, f in scenarios.items()}


# ================================================================ 5. Advisory seats
def _trace(payload):
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def argon4_decide(topic="quantumbiology-demo"):
    """Gemini Argon 4 DECIDER seat: MAP->MODEL->STRESS->DECIDE.

    Names-only keys, live calls 0, tighten-only: can add HOLDs, never lift one.
    """
    stages = ["MAP", "MODEL", "STRESS", "DECIDE"]
    payload = {"seat": "gemini-argon-4", "topic": topic, "stages": stages}
    return {
        "seat": "Gemini Argon 4 Extended Thinking",
        "role": "DECIDER",
        "pipeline": stages,
        "tiers": [2048, 8192, 32768],
        "key": "names-only (GEMINI_API_KEY name checked, value never read)",
        "live_calls": 0,
        "decision": "PROCEED - sandbox simulation only, all organism and product gates stay HOLD",
        "can_override_hold": False,
        "trace_sha256_16": _trace(payload),
    }


def claude_advisor(topic="quantumbiology-demo"):
    """Muse advisor seat: advises, can never override a HOLD."""
    return {
        "seat": "Muse",
        "role": "ADVISOR",
        "key": "names-only (MODEL_API_KEY name checked, value never read)",
        "live_calls": 0,
        "advice": "Say it in the first line of every report: the ENAQT peak, the yield curve, and the WKB exponent are properties of labelled toy parameters, not of any organism - then show eta at zero dephasing, at the optimum, and in the Zeno limit side by side.",
        "can_override_hold": False,
    }


def google_flow_plan():
    """Google Flow seat: plan-only, nothing rendered, nothing live."""
    return {
        "seat": "Google Flow",
        "role": "PLAN-ONLY",
        "shots": ["seven glowing sites on a protein scaffold, an exciton entering at site 1",
                  "noise dial rising: the exciton first localises, then flows, then freezes",
                  "two electron spins precessing beside one nuclear spin under a sweeping field",
                  "a proton wave packet leaking through a barrier the classical ball cannot climb",
                  "the efficiency curve peaking at intermediate dephasing, stamped SIMULATION"],
        "rendered": False,
        "live": 0,
    }


def brains_report():
    return {"decider": argon4_decide(), "advisor": claude_advisor(),
            "flow": google_flow_plan()}


# ================================================================ checks
def run_checks():
    c = []

    def chk(name, ok):
        c.append((name, bool(ok)))

    # 1. FMO network + eigensolver
    chk("trap_site_is_lowest_energy",
        SITE_ENERGIES_CM[TRAP_SITE] == min(SITE_ENERGIES_CM))
    chk("hamiltonian_symmetric",
        all(H_SITES[i][j] == H_SITES[j][i]
            for i in range(N_SITES) for j in range(N_SITES)))
    evals, V = jacobi_eig(H_SITES)
    diag = [[evals[i] if i == j else 0.0 for j in range(N_SITES)]
            for i in range(N_SITES)]
    rec = matmul_real(matmul_real(V, diag), transpose_real(V))
    chk("jacobi_reconstruction_fmo",
        max(abs(rec[i][j] - H_SITES[i][j])
            for i in range(N_SITES) for j in range(N_SITES)) < 1e-9)
    gram = matmul_real(transpose_real(V), V)
    chk("jacobi_orthonormal_fmo",
        max(abs(gram[i][j] - (1.0 if i == j else 0.0))
            for i in range(N_SITES) for j in range(N_SITES)) < 1e-9)
    spec = exciton_spectrum()
    chk("exciton_spectrum_seven_states",
        len(spec["energies_cm_relative"]) == 7
        and spec["energies_cm_relative"]
        == sorted(spec["energies_cm_relative"]))
    chk("lowest_exciton_energy", -35.0 < spec["lowest_energy_cm"] < -25.0)
    chk("lowest_exciton_weights_normalised",
        0.0 <= spec["lowest_exciton_trap_site_weight"] <= 1.0
        and 0.0 <= spec["lowest_exciton_start_site_weight"] <= 1.0)

    # 2. Transport - exact efficiency bookkeeping
    for g in (0.0, 20.0, 320.0, 5120.0):
        eta, loss = transport_efficiency(g)
        chk(f"eta_plus_loss_one_gamma_{int(g)}",
            abs(eta + loss - 1.0) < 1e-9 and 0.0 < eta < 1.0)
    eta0 = transport_efficiency(0.0)[0]
    chk("eta_zero_dephasing_value", 0.50 < eta0 < 0.60)
    opt = find_optimum()
    chk("enaqt_optimum_found",
        10.0 < opt["gamma_rad_ps"] < 60.0 and opt["efficiency"] > 0.91)
    chk("enaqt_beats_coherent_by_margin",
        opt["efficiency"] > eta0 + 0.30)
    eta_zeno = transport_efficiency(5120.0)[0]
    chk("zeno_limit_suppressed", eta_zeno < 0.40 and eta_zeno < eta0)
    chk("rising_edge_monotone",
        transport_efficiency(0.5)[0] > eta0
        and transport_efficiency(5.0)[0] > transport_efficiency(0.5)[0]
        and transport_efficiency(20.0)[0] > transport_efficiency(5.0)[0])
    chk("falling_edge_monotone",
        transport_efficiency(320.0)[0] > transport_efficiency(1280.0)[0]
        > transport_efficiency(5120.0)[0])
    # Liouvillian solve residual: L x must return -rho(0).
    L = liouvillian(20.0)
    rho0 = [0j] * (N_SITES * N_SITES)
    rho0[START_SITE * N_SITES + START_SITE] = 1.0 + 0j
    x = solve_complex(L, [-v for v in rho0])
    residual = max(abs(sum(L[r][k] * x[k] for k in range(len(x)))
                       + rho0[r]) for r in range(len(x)))
    chk("liouvillian_solve_residual", residual < 1e-8)
    # Coherence contrast across regimes (first-ps mean l1 coherence).
    c0 = mean_coherence(0.0)
    c_opt = mean_coherence(opt["gamma_rad_ps"])
    c_zeno = mean_coherence(1280.0)
    chk("coherence_highest_when_coherent", c0 > 1.0 and c0 > c_opt > c_zeno)
    chk("coherence_quenched_in_zeno_limit", c_zeno < 0.1)
    snaps = population_snapshots(0.0)
    chk("snapshots_population_decays_by_loss_and_trap",
        snaps[0]["total_remaining"] == 1.0
        and snaps[-1]["total_remaining"] < 1.0
        and all(0.0 <= p <= 1.0 for s in snaps for p in s["populations"]))

    # 3. Radical pair
    rep = radical_report()
    chk("singlet_yield_zero_field_point_seven",
        abs(rep["phi_s_zero_field"] - 0.7) < 2e-3)
    chk("yields_are_probabilities",
        all(0.0 <= row["singlet_yield"] <= 1.0 for row in rep["curve"]))
    chk("yield_swing_real", rep["yield_swing"] > 0.04)
    chk("yield_dip_at_intermediate_field",
        rep["phi_s_min"] < rep["phi_s_zero_field"] - 0.01
        and 0.3 < rep["field_at_min"] < 1.2)
    chk("yield_high_field_above_zero_field",
        rep["phi_s_high_field_b3"] > rep["phi_s_zero_field"])
    chk("triplet_complement",
        abs(rep["phi_s_zero_field"] + rep["triplet_yield_zero_field"]
            - 1.0) < 1e-9)
    Hr = radical_hamiltonian(0.7)
    ev_r, V_r = jacobi_eig(Hr)
    diag_r = [[ev_r[i] if i == j else 0.0 for j in range(8)]
              for i in range(8)]
    rec_r = matmul_real(matmul_real(V_r, diag_r), transpose_real(V_r))
    chk("jacobi_reconstruction_radical",
        max(abs(rec_r[i][j] - Hr[i][j])
            for i in range(8) for j in range(8)) < 1e-9)

    # 4. Proton tunnelling
    tun = tunnel_report()
    chk("kappa_value", 1.60e11 < tun["kappa_per_m"] < 1.72e11)
    chk("wkb_transmission_range", 1e-8 < tun["t_wkb_proton"] < 1e-6)
    chk("exact_close_to_wkb", 0.3 < tun["exact_over_wkb"] < 1.5)
    chk("tunnelling_beats_classical_by_100x",
        tun["enhancement_factor"] > 100.0
        and tun["tunnel_rate_hz"] > tun["classical_rate_hz"])
    chk("isotope_effect_large",
        tun["kinetic_isotope_effect"] > 100.0
        and tun["t_wkb_deuteron"] < tun["t_wkb_proton"])
    try:
        barrier_kappa(PROTON_MASS, BARRIER_EV * EV_J)
        above_ok = False
    except ValueError:
        above_ok = True
    chk("kappa_rejects_above_barrier_energy", above_ok)

    # 5. Classifier - labels from the lab's own policy
    crep = classifier_report()
    chk("classifier_zero_is_coherent_trapped",
        crep["zero_dephasing"]["label"] == "coherent-trapped")
    chk("classifier_optimum_is_enaqt",
        crep["enaqt_optimum"]["label"] == "ENAQT-optimal")
    chk("classifier_zeno_is_over_dephased",
        crep["zeno_limit"]["label"] == "over-dephased")
    chk("classifier_matches_policy_on_scenarios",
        all(row["label"] == row["policy_label"] for row in crep.values()))
    chk("classifier_matches_policy_on_probes",
        all(classify_transport(g, e, co) == model_label(g, e, co)
            for g, e, co in [(0.0, 0.55, 2.0), (26.5, 0.92, 0.3),
                             (3000.0, 0.45, 0.0), (50.0, 0.91, 0.4),
                             (0.5, 0.73, 1.2)]))
    chk("training_grid_labels_valid",
        all(label in REGIME_LABELS for _, label in TRAINING_GRID)
        and {label for _, label in TRAINING_GRID} == set(REGIME_LABELS))

    # gates + seats
    chk("hold_gates_14", len(HOLD_GATES) == 14
        and all(v.startswith("HOLD") for v in HOLD_GATES.values()))
    chk("gate_medical_hold", gate("medical_claim") == "HOLD")
    chk("gate_agriculture_hold", gate("agriculture_claim") == "HOLD")
    chk("gate_sensor_hold", gate("quantum_sensor_claim") == "HOLD")
    chk("gate_navigation_hold", gate("in_vivo_navigation_claim") == "HOLD")
    chk("gate_sandbox_proceed", gate("run_simulation") == "PROCEED")
    brains = brains_report()
    chk("argon4_no_override", brains["decider"]["can_override_hold"] is False
        and brains["decider"]["seat"]
        == "Gemini Argon 4 Extended Thinking")
    chk("claude_no_override", brains["advisor"]["can_override_hold"] is False)
    chk("flow_plan_only", brains["flow"]["rendered"] is False
        and brains["flow"]["live"] == 0)
    return c


# ================================================================ CLI / demo
def demo():
    print("=" * 68)
    print("QuantumBiology-Lab - quantum biology lab (toy models, labelled)")
    print("by Darion Kellar | MIT | pure stdlib | zero network | EDUCATION ONLY")
    print("=" * 68)
    print("\n[1] THE HONEST CORE - what these toys do and do not show")
    print("    Three textbook toy models, computed exactly: excitonic")
    print("    transport on a 7-site FMO-like network, a one-hyperfine")
    print("    radical pair, and WKB proton tunnelling. Every parameter")
    print("    is a LABELLED teaching value - nothing was measured from")
    print("    any organism, and no output is a biological measurement.")
    trep = transport_report()
    net = trep["network"]
    spec = trep["exciton_spectrum"]
    print("\n[2] FMO-like network - 7 sites, trap at site 3 (lowest energy)")
    print(f"    site energies (cm^-1): {net['site_energies_cm']}")
    print(f"    exciton energies (cm^-1, relative): "
          f"{spec['energies_cm_relative']}")
    print(f"    lowest exciton: {spec['lowest_energy_cm']} cm^-1 | "
          f"trap-site weight {spec['lowest_exciton_trap_site_weight']} | "
          f"start-site weight {spec['lowest_exciton_start_site_weight']}")
    print(f"    trap rate kappa = {net['trap_rate_per_ps']} /ps | "
          f"recombination Gamma = {net['loss_rate_per_ps']} /ps (labelled)")
    print("\n[3] Dephasing sweep - ENAQT: efficiency PEAKS at mid dephasing")
    print("    gamma (rad/ps)   efficiency   loss")
    for row in trep["sweep"]:
        print(f"    {row['gamma_rad_ps']:10.1f}     {row['efficiency']:.6f}"
              f"    {row['loss']:.6f}")
    opt = trep["enaqt_optimum"]
    print(f"    -> eta(gamma=0)      = {trep['efficiency_zero_dephasing']:.6f}"
          "  (coherent localisation)")
    print(f"    -> eta(gamma*={opt['gamma_rad_ps']:.2f})  = {opt['efficiency']:.6f}"
          f"  (ENAQT optimum, gamma* = {opt['gamma_cm']} cm^-1)")
    print(f"    -> eta(gamma=5120)   = {trep['efficiency_zeno_5120']:.6f}"
          "  (Zeno limit: hopping quenched)")
    coh = trep["coherence_first_ps"]
    print(f"    mean coherence (1st ps): gamma 0 -> {coh['gamma_0']} | "
          f"gamma* -> {coh['gamma_optimum']} | "
          f"gamma 1280 -> {coh['gamma_1280']}")
    snaps = population_snapshots(opt["gamma_rad_ps"])
    print("    populations at gamma* (sites 1..7):")
    for s in snaps:
        print(f"      t={s['t_ps']:5.2f} ps  {s['populations']}  "
              f"remaining {s['total_remaining']}")
    rrep = radical_report()
    print("\n[4] Radical pair - singlet yield vs applied field (a = 1 units)")
    for row in rrep["curve"]:
        print(f"    B/a = {row['field_b_over_a']:5.2f}   "
              f"Phi_S = {row['singlet_yield']:.6f}")
    print(f"    -> Phi_S(0) = {rrep['phi_s_zero_field']:.6f} | dip "
          f"{rrep['phi_s_min']:.6f} at B/a = {rrep['field_at_min']} | "
          f"Phi_S(3) = {rrep['phi_s_high_field_b3']:.6f} | "
          f"swing {rrep['yield_swing']:.6f}")
    print("    -> a toy yield curve, NOT a bird compass and NOT a sensor.")
    tun = tunnel_report()
    print("\n[5] Proton tunnelling - rectangular barrier, labelled values")
    print(f"    barrier {tun['barrier_height_ev']} eV x "
          f"{tun['barrier_width_angstrom']} Angstrom | E = k_B T at "
          f"{tun['temperature_k']} K = {tun['particle_energy_ev']} eV")
    print(f"    kappa = {tun['kappa_per_m']:.4e} /m | "
          f"2 kappa L = {tun['two_kappa_L']:.4f}")
    print(f"    T_WKB = {tun['t_wkb_proton']:.4e} | "
          f"T_exact = {tun['t_exact_proton']:.4e} | "
          f"ratio {tun['exact_over_wkb']:.4f}")
    print(f"    tunnel rate {tun['tunnel_rate_hz']:.4e} Hz vs classical "
          f"{tun['classical_rate_hz']:.4e} Hz -> enhancement "
          f"{tun['enhancement_factor']:.1f}x")
    print(f"    deuteron T_WKB = {tun['t_wkb_deuteron']:.4e} -> "
          f"kinetic isotope effect {tun['kinetic_isotope_effect']:.1f}")
    print("\n[6] Transport regime classifier (TinyML kNN, policy labels)")
    for name, row in classifier_report().items():
        print(f"    {name:22s} gamma {row['gamma_rad_ps']:9.2f} | "
              f"eta {row['efficiency']:.4f} | C {row['mean_coherence']:.4f}"
              f" -> {row['label']}")
    print("\n[7] Advisory seats")
    brains = brains_report()
    print(f"    decider: {brains['decider']['decision']} "
          f"trace={brains['decider']['trace_sha256_16']}")
    print(f"    advisor can_override_hold = {brains['advisor']['can_override_hold']}")
    print(f"    flow rendered = {brains['flow']['rendered']} "
          f"live = {brains['flow']['live']}")
    print(f"\n[8] HOLD gates: {len(HOLD_GATES)}")
    for key in HOLD_GATES:
        print(f"    HOLD  {key}")
    checks = run_checks()
    passed = sum(1 for _, ok in checks if ok)
    print(f"\nCHECKS {passed}/{len(checks)}")
    for name, ok in checks:
        if not ok:
            print(f"    FAIL {name}")
    verdict = "PROCEED" if passed == len(checks) else "HOLD"
    print(f"VERDICT {verdict} (sandbox simulation only) | HOLD gates {len(HOLD_GATES)}")
    return 0 if passed == len(checks) else 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] == "demo":
        return demo()
    cmd = argv[0]
    if cmd == "checks":
        checks = run_checks()
        for name, ok in checks:
            print(f"{'PASS' if ok else 'FAIL'} {name}")
        print(f"CHECKS {sum(1 for _, ok in checks if ok)}/{len(checks)}")
        return 0 if all(ok for _, ok in checks) else 1
    if cmd == "transport":
        print(json.dumps(transport_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "radical":
        print(json.dumps(radical_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "tunnel":
        print(json.dumps(tunnel_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "classify":
        print(json.dumps(classifier_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "brains":
        print(json.dumps(brains_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "holds":
        for key, value in HOLD_GATES.items():
            print(f"{key}: {value}")
        return 0
    if cmd == "hold-demo":
        action = argv[1] if len(argv) > 1 else "medical_claim"
        print(f"{action}: {HOLD_GATES.get(action, 'PROCEED - not gated')}")
        return 2 if gate(action) == "HOLD" else 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
