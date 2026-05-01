"""
Simulator — runs the closed feedback loop numerically.

Implements equation (5) from page 175:
  y(s) = [g(s)/(1 + g(s)·g_m(s))]·y_sp(s)
        + [g_d(s)/(1 + g(s)·g_m(s))]·d(s)

In discrete time this becomes a loop:
  1. Read setpoint y_sp(t) and disturbance d(t)
  2. Measure output: y_m = g_m · y  (assume g_m=1, ideal sensor)
  3. Compute error: ε = y_sp - y_m   [comparator, page 172]
  4. Controller computes u = g_c(ε)
  5. Process updates:  y = process.step(u, d, dt)
  6. Record everything. Repeat.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Callable, List


@dataclass
class SimResult:
    """Container for all signals recorded during simulation."""
    t:   List[float] = field(default_factory=list)   # time axis
    y:   List[float] = field(default_factory=list)   # output CV y(t)
    u:   List[float] = field(default_factory=list)   # MV u(t)
    e:   List[float] = field(default_factory=list)   # error ε(t)
    ysp: List[float] = field(default_factory=list)   # setpoint y_sp(t)
    d:   List[float] = field(default_factory=list)   # disturbance d(t)

    def as_arrays(self):
        return (np.array(self.t), np.array(self.y),
                np.array(self.u), np.array(self.e),
                np.array(self.ysp), np.array(self.d))


def run_simulation(
    process,
    controller,
    setpoint_fn:    Callable[[float], float],
    disturbance_fn: Callable[[float], float],
    t_end: float = 200.0,
    dt:    float = 0.1,
    g_m:   float = 1.0,       # measuring device gain (1.0 = ideal sensor)
) -> SimResult:
    """
    Run the closed feedback loop.

    Args:
        process        : FirstOrderProcess or SecondOrderProcess instance
        controller     : PIDController or NeuralController instance
        setpoint_fn    : function(t) → y_sp value at time t
        disturbance_fn : function(t) → d value at time t
        t_end          : total simulation time in seconds
        dt             : integration step size in seconds
        g_m            : measuring device gain (page 171 eq.2)

    Returns:
        SimResult with all recorded signals
    """
    process.reset()
    controller.reset()
    result = SimResult()

    t = 0.0
    n_steps = int(t_end / dt) + 1

    for _ in range(n_steps):
        ysp = setpoint_fn(t)
        d   = disturbance_fn(t)

        # Measuring device: y_m(s) = g_m(s)·y(s)  [page 171 eq.2]
        y_m = g_m * process.y

        # Comparator: ε = y_sp - y_m  [page 172 eq.3]
        error = ysp - y_m

        # Controller: c'(s) = g_c(s)·ε(s)  [page 172 eq.4]
        u = controller.compute(error, process.y, dt)

        # Process: y advances by one step  [page 171 eq.1]
        y = process.step(u, d, dt)

        result.t.append(round(t, 6))
        result.y.append(round(y, 8))
        result.u.append(round(u, 8))
        result.e.append(round(error, 8))
        result.ysp.append(ysp)
        result.d.append(d)

        t = round(t + dt, 6)

    return result