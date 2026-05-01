"""
Performance metrics — quantifies how well the controller is doing.

ISE  (Integral of Squared Error)   — penalizes large errors heavily
IAE  (Integral of Absolute Error)  — balanced penalty
ITAE (Integral of Time-weighted AE)— penalizes errors that persist long
"""

import numpy as np
from core.simulator import SimResult


def compute_metrics(result: SimResult) -> dict:
    t, y, u, e, ysp, d = result.as_arrays()

    sp_final = ysp[-1]
    sp_change = abs(ysp.max() - ysp.min())

    # ── Error integrals ───────────────────────────────────────────────────
    _trapz = np.trapezoid if hasattr(np, "trapezoid") else np.trapz
    ISE  = float(_trapz(e**2,          t))
    IAE  = float(_trapz(np.abs(e),     t))
    ITAE = float(_trapz(t * np.abs(e), t))

    # ── Overshoot (servo) ─────────────────────────────────────────────────
    if sp_change > 0.01:
        # Find index where setpoint first changes
        step_idx = int(np.argmax(np.abs(np.diff(ysp)) > 0.01))
        y_after  = y[step_idx:]
        peak     = y_after.max() if sp_final > 0 else y_after.min()
        overshoot = max(0.0, (peak - sp_final) / abs(sp_change) * 100)
    else:
        overshoot = 0.0

    # ── Settling time (2% band around final setpoint) ────────────────────
    band        = 0.02 * max(abs(sp_final), 0.01)
    in_band     = np.abs(y - sp_final) <= band
    settling_time = t[-1]
    for i in range(len(in_band) - 1, -1, -1):
        if not in_band[i]:
            settling_time = t[min(i + 1, len(t) - 1)]
            break

    # ── Steady-state error (average of last 10% of simulation) ───────────
    tail       = y[int(0.9 * len(y)):]
    ss_error   = float(abs(np.mean(tail) - sp_final))

    # ── Total variation of MV (how much the valve is moving) ─────────────
    tv_u = float(np.sum(np.abs(np.diff(u))))

    return {
        "ISE":              round(ISE,          3),
        "IAE":              round(IAE,          3),
        "ITAE":             round(ITAE,         3),
        "overshoot_%":      round(overshoot,    2),
        "settling_time_s":  round(settling_time, 1),
        "ss_error":         round(ss_error,     5),
        "tv_u":             round(tv_u,         3),
    }