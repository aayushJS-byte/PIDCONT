"""
Process models — implements g_p(s) and g_d(s) from pages 171-173.

The process takes two inputs:
  u(t) — manipulated variable (MV), e.g. valve position
  d(t) — disturbance variable (DV), e.g. feed temperature change

And produces one output:
  y(t) — controlled variable (CV), e.g. reactor temperature

Transfer function (Laplace domain):
  y(s) = g_p(s)·u(s) + g_d(s)·d(s)

In time domain for a first-order process:
  τ_p · dy/dt + y = K_p·u + K_d·d
"""

import numpy as np


class FirstOrderProcess:
    """
    First-order process with disturbance input.
    Models a CSTR, tank level, heat exchanger, etc.

    Parameters
    ----------
    K_p   : process gain (how much y changes per unit u)
    tau_p : process time constant in seconds (sluggishness)
    K_d   : disturbance gain (how hard disturbances hit)
    theta : dead time in seconds (transportation delay)
    """

    def __init__(self, K_p: float = 1.0, tau_p: float = 5.0,
                 K_d: float = 0.5, theta: float = 0.0):
        self.K_p   = K_p
        self.tau_p = tau_p
        self.K_d   = K_d
        self.theta = theta

        self.y = 0.0          # current output, deviation form
        self._dead_buf = []   # buffer for dead-time approximation

    def step(self, u: float, d: float, dt: float) -> float:
        """
        Advance process by one time step using Euler integration.

        Args:
            u  : controller output (MV) at current time
            d  : disturbance value at current time
            dt : time step size in seconds

        Returns:
            y  : process output (CV) after this step
        """
        # Dead-time: delay u by theta seconds
        self._dead_buf.append(u)
        dead_steps = max(1, int(self.theta / dt))
        u_delayed = self._dead_buf[-dead_steps] if len(self._dead_buf) >= dead_steps else 0.0

        # ODE: τ·dy/dt = K_p·u + K_d·d - y
        dydt = (self.K_p * u_delayed + self.K_d * d - self.y) / self.tau_p
        self.y += dydt * dt
        return self.y

    def reset(self):
        self.y = 0.0
        self._dead_buf = []


class SecondOrderProcess:
    """
    Second-order underdamped process — shows oscillatory response.
    Useful for demonstrating why derivative action matters.

    Transfer function: g_p(s) = K_p / (τ²s² + 2ζτs + 1)
    """

    def __init__(self, K_p: float = 1.0, tau: float = 5.0,
                 zeta: float = 0.5, K_d: float = 0.3):
        self.K_p  = K_p
        self.tau  = tau
        self.zeta = zeta   # damping ratio (< 1 = underdamped, oscillatory)
        self.K_d  = K_d

        # State variables for second-order ODE
        self.y   = 0.0
        self.dy  = 0.0

    def step(self, u: float, d: float, dt: float) -> float:
        # Second-order ODE: τ²·y'' + 2ζτ·y' + y = K_p·u + K_d·d
        ddy = (self.K_p * u + self.K_d * d - self.y
               - 2 * self.zeta * self.tau * self.dy) / (self.tau ** 2)
        self.dy += ddy * dt
        self.y  += self.dy * dt
        return self.y

    def reset(self):
        self.y  = 0.0
        self.dy = 0.0