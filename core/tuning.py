def ziegler_nichols(Ku, Pu):
    """
    Ziegler–Nichols closed-loop tuning rules.

    Ku = ultimate gain
    Pu = oscillation period
    """
    Kc = 0.6 * Ku
    tau_I = Pu / 2
    tau_D = Pu / 8

    return Kc, tau_I, tau_D