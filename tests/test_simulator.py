"""
Tests — verify the control system math is correct.
Run with: pytest tests/
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pytest
from core.process     import FirstOrderProcess
from core.controllers import PIDController
from core.simulator   import run_simulation
from core.metrics     import compute_metrics


# ── Process tests ─────────────────────────────────────────────────────────────

def test_process_starts_at_zero():
    """Process output must start at zero (deviation form)."""
    p = FirstOrderProcess()
    assert p.y == 0.0

def test_process_responds_to_input():
    """Applying a positive u must increase y over time."""
    p = FirstOrderProcess(K_p=1.0, tau_p=5.0)
    for _ in range(100):
        y = p.step(u=1.0, d=0.0, dt=0.1)
    assert y > 0.5    # should have moved significantly

def test_process_steady_state():
    """
    At steady state with constant u=1, y should approach K_p.
    (From transfer function: y_ss = K_p · u_ss)
    """
    p = FirstOrderProcess(K_p=2.0, tau_p=3.0)
    for _ in range(2000):
        y = p.step(u=1.0, d=0.0, dt=0.1)
    assert abs(y - 2.0) < 0.01, f"Expected ~2.0, got {y}"

def test_process_reset():
    """Reset must restore process to initial state."""
    p = FirstOrderProcess()
    for _ in range(50):
        p.step(1.0, 0.0, 0.1)
    assert p.y != 0.0
    p.reset()
    assert p.y == 0.0

def test_disturbance_effect():
    """Disturbance should push output even with u=0."""
    p = FirstOrderProcess(K_d=1.0, K_p=1.0, tau_p=5.0)
    for _ in range(200):
        y = p.step(u=0.0, d=1.0, dt=0.1)
    assert y > 0.3


# ── Controller tests ──────────────────────────────────────────────────────────

def test_pid_proportional_only():
    """Pure P controller output = Kc * error."""
    pid = PIDController(Kc=3.0, tau_I=0.0, tau_D=0.0)
    u = pid.compute(error=2.0, y=0.0, dt=0.1)
    assert abs(u - 6.0) < 0.01, f"Expected 6.0, got {u}"

def test_pid_reset():
    pid = PIDController(Kc=1.0, tau_I=5.0)
    for _ in range(20):
        pid.compute(1.0, 0.0, 0.1)
    pid.reset()
    assert pid._integral == 0.0

def test_pid_anti_windup():
    """With large error, output must be clamped to u_max."""
    pid = PIDController(Kc=10.0, tau_I=1.0, u_max=5.0, u_min=-5.0)
    u = pid.compute(error=100.0, y=0.0, dt=0.1)
    assert u <= 5.0


# ── Simulation tests ──────────────────────────────────────────────────────────

def test_simulation_runs():
    """Basic smoke test — simulation must complete without error."""
    proc = FirstOrderProcess()
    ctrl = PIDController(Kc=2.0, tau_I=5.0)
    result = run_simulation(proc, ctrl,
                            setpoint_fn=lambda t: 1.0 if t > 10 else 0.0,
                            disturbance_fn=lambda t: 0.0,
                            t_end=50.0, dt=0.1)
    assert len(result.t) > 0
    assert len(result.y) == len(result.t)

def test_simulation_output_length():
    """Number of time steps must match t_end / dt."""
    proc = FirstOrderProcess()
    ctrl = PIDController()
    result = run_simulation(proc, ctrl,
                            lambda t: 1.0, lambda t: 0.0,
                            t_end=10.0, dt=0.1)
    expected = int(10.0 / 0.1) + 1
    assert abs(len(result.t) - expected) <= 1

def test_servo_tracking():
    """
    With a well-tuned PID and no disturbance,
    the output must reach within 5% of setpoint by end of simulation.
    Tests the servo control problem (page 177 C1).
    """
    proc = FirstOrderProcess(K_p=1.0, tau_p=5.0)
    ctrl = PIDController(Kc=3.0, tau_I=5.0)
    result = run_simulation(proc, ctrl,
                            lambda t: 1.0 if t >= 10 else 0.0,
                            lambda t: 0.0,
                            t_end=150.0, dt=0.1)
    y_final = result.y[-1]
    assert abs(y_final - 1.0) < 0.05, f"Servo failed: y_final={y_final}"

def test_regulator_rejection():
    """
    With setpoint=0 and disturbance applied,
    output must return close to zero (regulator problem, page 177 C2).
    """
    proc = FirstOrderProcess(K_p=1.0, tau_p=5.0, K_d=0.5)
    ctrl = PIDController(Kc=3.0, tau_I=3.0)
    result = run_simulation(proc, ctrl,
                            lambda t: 0.0,
                            lambda t: 1.0 if t >= 20 else 0.0,
                            t_end=200.0, dt=0.1)
    y_final = result.y[-1]
    assert abs(y_final) < 0.1, f"Regulator failed: y_final={y_final}"


# ── Metrics tests ─────────────────────────────────────────────────────────────

def test_metrics_keys():
    """Metrics dict must contain all required keys."""
    proc = FirstOrderProcess()
    ctrl = PIDController(Kc=2.0, tau_I=5.0)
    result = run_simulation(proc, ctrl,
                            lambda t: 1.0 if t > 5 else 0.0,
                            lambda t: 0.0,
                            t_end=100.0, dt=0.1)
    m = compute_metrics(result)
    for key in ["ISE", "IAE", "ITAE", "overshoot_%", "settling_time_s", "ss_error"]:
        assert key in m, f"Missing metric: {key}"

def test_perfect_control_zero_ISE():
    """
    For a well-controlled system, steady-state error should be near zero
    and ISE should be reasonably small (not necessarily near zero due to transients).
    """
    proc = FirstOrderProcess(K_p=1.0, tau_p=0.5)
    ctrl = PIDController(Kc=5.0, tau_I=2.0)

    result = run_simulation(
        proc, ctrl,
        lambda t: 1.0 if t > 5 else 0.0,
        lambda t: 0.0,
        t_end=100.0, dt=0.05
    )

    m = compute_metrics(result)

    # Primary condition: good tracking
    assert m["ss_error"] < 0.02, f"Steady-state error too high: {m['ss_error']}"

    # Secondary condition: reasonable performance
    assert m["ISE"] < 50, f"ISE too high: {m['ISE']}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])