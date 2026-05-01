import numpy as np


class PIDController:
    def __init__(self, Kc: float = 2.0, tau_I: float = 5.0,
                 tau_D: float = 0.0, u_min: float = -10.0, u_max: float = 10.0):
        self.Kc    = Kc
        self.tau_I = tau_I
        self.tau_D = tau_D
        self.u_min = u_min
        self.u_max = u_max

        self._integral   = 0.0
        self._prev_y     = 0.0

    def compute(self, error: float, y: float, dt: float) -> float:
        # Proportional
        P = self.Kc * error

        # Integral
        self._integral += error * dt
        I = (self.Kc / self.tau_I * self._integral) if self.tau_I > 0 else 0.0

        # Derivative (on measurement)
        if self.tau_D > 0 and dt > 0:
            D = -self.Kc * self.tau_D * (y - self._prev_y) / dt
        else:
            D = 0.0

        self._prev_y = y

        u_raw = P + I + D
        u = float(np.clip(u_raw, self.u_min, self.u_max))

        # Anti-windup
        if u != u_raw and self.tau_I > 0:
            self._integral -= error * dt

        return u

    def reset(self):
        self._integral = 0.0
        self._prev_y   = 0.0

    @property
    def name(self):
        return "PID Controller"