"""Tests for QuantumBiology-Lab: ENAQT transport, radical pair, tunnelling."""
import math

import pytest

import main as m


# ---- FMO network + eigensolver
def test_trap_site_is_lowest():
    assert m.SITE_ENERGIES_CM[m.TRAP_SITE] == min(m.SITE_ENERGIES_CM)


def test_hamiltonian_symmetric_and_diagonal():
    base = min(m.SITE_ENERGIES_CM)
    for i in range(m.N_SITES):
        assert m.H_SITES[i][i] == pytest.approx(
            (m.SITE_ENERGIES_CM[i] - base) * m.CM_TO_RAD_PS)
        for j in range(m.N_SITES):
            assert m.H_SITES[i][j] == m.H_SITES[j][i]


def test_jacobi_reconstruction():
    evals, V = m.jacobi_eig(m.H_SITES)
    diag = [[evals[i] if i == j else 0.0 for j in range(7)] for i in range(7)]
    rec = m.matmul_real(m.matmul_real(V, diag), m.transpose_real(V))
    err = max(abs(rec[i][j] - m.H_SITES[i][j]) for i in range(7) for j in range(7))
    assert err < 1e-9


def test_exciton_spectrum_sorted():
    spec = m.exciton_spectrum()
    assert len(spec["energies_cm_relative"]) == 7
    assert spec["energies_cm_relative"] == sorted(spec["energies_cm_relative"])
    assert -35.0 < spec["lowest_energy_cm"] < -25.0


# ---- Transport efficiency
@pytest.mark.parametrize("gamma", [0.0, 20.0, 320.0, 5120.0])
def test_eta_plus_loss_is_one(gamma):
    eta, loss = m.transport_efficiency(gamma)
    assert eta + loss == pytest.approx(1.0, abs=1e-9)
    assert 0.0 < eta < 1.0


def test_eta_zero_dephasing():
    assert m.transport_efficiency(0.0)[0] == pytest.approx(0.5536, abs=0.01)


def test_enaqt_optimum():
    opt = m.find_optimum()
    assert 10.0 < opt["gamma_rad_ps"] < 60.0
    assert opt["efficiency"] > 0.91
    assert opt["efficiency"] > m.transport_efficiency(0.0)[0] + 0.30


def test_zeno_limit_suppressed():
    eta_zeno = m.transport_efficiency(5120.0)[0]
    assert eta_zeno < 0.40
    assert eta_zeno < m.transport_efficiency(0.0)[0]


def test_sweep_shape():
    sweep = {row["gamma_rad_ps"]: row["efficiency"]
             for row in m.transport_sweep()}
    assert sweep[0.5] > sweep[0.0]
    assert sweep[20.0] > sweep[5.0] > sweep[0.5]
    assert sweep[320.0] > sweep[1280.0] > sweep[5120.0]
    assert max(sweep.values()) == sweep[20.0] or max(sweep.values()) == sweep[40.0]


def test_liouvillian_residual():
    L = m.liouvillian(20.0)
    rho0 = [0j] * 49
    rho0[0] = 1.0 + 0j
    x = m.solve_complex(L, [-v for v in rho0])
    residual = max(abs(sum(L[r][k] * x[k] for k in range(49)) + rho0[r])
                   for r in range(49))
    assert residual < 1e-8


def test_coherence_contrast():
    opt = m.find_optimum()
    c0 = m.mean_coherence(0.0)
    c_opt = m.mean_coherence(opt["gamma_rad_ps"])
    c_zeno = m.mean_coherence(1280.0)
    assert c0 > 1.0
    assert c0 > c_opt > c_zeno
    assert c_zeno < 0.1


def test_population_snapshots():
    snaps = m.population_snapshots(0.0)
    assert snaps[0]["total_remaining"] == pytest.approx(1.0)
    assert snaps[-1]["total_remaining"] < 1.0
    assert all(0.0 <= p <= 1.0 for s in snaps for p in s["populations"])


# ---- Radical pair
def test_singlet_yield_zero_field():
    assert m.singlet_yield(0.0) == pytest.approx(0.7, abs=2e-3)


def test_yield_curve_shape():
    rep = m.radical_report()
    assert rep["yield_swing"] > 0.04
    assert rep["phi_s_min"] < rep["phi_s_zero_field"] - 0.01
    assert 0.3 < rep["field_at_min"] < 1.2
    assert rep["phi_s_high_field_b3"] > rep["phi_s_zero_field"]
    assert all(0.0 <= row["singlet_yield"] <= 1.0 for row in rep["curve"])


def test_triplet_complement():
    rep = m.radical_report()
    assert rep["phi_s_zero_field"] + rep["triplet_yield_zero_field"] == \
        pytest.approx(1.0, abs=1e-9)


def test_radical_jacobi_reconstruction():
    H = m.radical_hamiltonian(0.7)
    evals, V = m.jacobi_eig(H)
    diag = [[evals[i] if i == j else 0.0 for j in range(8)] for i in range(8)]
    rec = m.matmul_real(m.matmul_real(V, diag), m.transpose_real(V))
    err = max(abs(rec[i][j] - H[i][j]) for i in range(8) for j in range(8))
    assert err < 1e-9


def test_singlet_projector_trace():
    P = m.singlet_projector()
    trace = sum(P[i][i] for i in range(8))
    assert trace == pytest.approx(2.0)  # singlet x 2 nuclear states
    P2 = m.matmul_real(P, P)
    assert max(abs(P2[i][j] - P[i][j]) for i in range(8)
               for j in range(8)) < 1e-12


# ---- Proton tunnelling
def test_kappa_and_wkb():
    tun = m.tunnel_report()
    assert 1.60e11 < tun["kappa_per_m"] < 1.72e11
    assert 1e-8 < tun["t_wkb_proton"] < 1e-6
    assert tun["two_kappa_L"] == pytest.approx(16.63, abs=0.05)


def test_exact_close_to_wkb():
    tun = m.tunnel_report()
    assert 0.3 < tun["exact_over_wkb"] < 1.5


def test_enhancement_and_isotope():
    tun = m.tunnel_report()
    assert tun["enhancement_factor"] > 100.0
    assert tun["tunnel_rate_hz"] > tun["classical_rate_hz"]
    assert tun["kinetic_isotope_effect"] > 100.0
    assert tun["t_wkb_deuteron"] < tun["t_wkb_proton"]


def test_kappa_rejects_above_barrier():
    with pytest.raises(ValueError):
        m.barrier_kappa(m.PROTON_MASS, m.BARRIER_EV * m.EV_J)


def test_wkb_heavier_mass_transmits_less():
    e = m.KB * m.TEMPERATURE_K
    assert m.wkb_transmission(2.0 * m.PROTON_MASS, e) < \
        m.wkb_transmission(m.PROTON_MASS, e)


# ---- Classifier
def test_classifier_canonical_labels():
    rep = m.classifier_report()
    assert rep["zero_dephasing"]["label"] == "coherent-trapped"
    assert rep["enaqt_optimum"]["label"] == "ENAQT-optimal"
    assert rep["zeno_limit"]["label"] == "over-dephased"


def test_classifier_matches_policy():
    rep = m.classifier_report()
    assert all(row["label"] == row["policy_label"] for row in rep.values())
    for features in [(0.0, 0.55, 2.0), (26.5, 0.92, 0.3),
                     (3000.0, 0.45, 0.0), (50.0, 0.91, 0.4)]:
        assert m.classify_transport(*features) == m.model_label(*features)


def test_training_grid_covers_all_labels():
    labels = {label for _, label in m.TRAINING_GRID}
    assert labels == set(m.REGIME_LABELS)


# ---- HOLD gates + seats + CLI
def test_hold_gates_14():
    assert len(m.HOLD_GATES) == 14
    assert all(v.startswith("HOLD") for v in m.HOLD_GATES.values())


@pytest.mark.parametrize("action", [
    "medical_claim", "drug_design_claim", "agriculture_claim",
    "quantum_sensor_claim", "in_vivo_navigation_claim",
    "consciousness_claim", "solar_energy_product_claim",
])
def test_gated_actions_hold(action):
    assert m.gate(action) == "HOLD"


def test_sandbox_proceeds():
    assert m.gate("run_simulation") == "PROCEED"


def test_seats_cannot_override():
    brains = m.brains_report()
    assert brains["decider"]["can_override_hold"] is False
    assert brains["decider"]["seat"] == "Gemini Argon 4 Extended Thinking"
    assert brains["advisor"]["can_override_hold"] is False
    assert brains["flow"]["rendered"] is False
    assert brains["flow"]["live"] == 0


def test_cli_checks_and_hold_demo():
    assert m.main(["checks"]) == 0
    assert m.main(["hold-demo"]) == 2
    assert m.main(["hold-demo", "medical_claim"]) == 2
    assert m.main(["hold-demo", "run_simulation"]) == 0


def test_run_checks_all_pass():
    checks = m.run_checks()
    assert all(ok for _, ok in checks)
    assert len(checks) >= 40
