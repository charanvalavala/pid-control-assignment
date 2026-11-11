import numpy as np

from pid import PID


def rk4(state, force, dt, model="block", mass=1.0):
    def rhs(z):
        if model == "block":
            return np.array([z[1], (force - 10 * z[1] - 20 * z[0]) / mass])
        return np.array([force - z[0], z[0] - z[1], z[1] - z[2]])
    a = rhs(state)
    b = rhs(state + dt * a / 2)
    c = rhs(state + dt * b / 2)
    d = rhs(state + dt * c)
    return state + dt * (a + 2 * b + 2 * c + d) / 6


def simulate(controller, duration=12.0, dt=0.002, model="block", noise=0.0,
             target=None, mass=1.0, seed=17):
    if duration <= 0 or dt <= 0 or mass <= 0:
        raise ValueError("Duration, dt and mass must be positive")
    controller.reset()
    t = np.arange(round(duration / dt) + 1) * dt
    state = np.zeros(2 if model == "block" else 3)
    rng = np.random.default_rng(seed)
    x, u, integral, reference = (np.zeros(len(t)) for _ in range(4))
    for j, now in enumerate(t):
        reference[j] = 1.0 if target is None else target(now)
        x[j] = state[0] if model == "block" else state[2]
        measured = x[j] + rng.uniform(-noise, noise)
        u[j] = controller.update(reference[j], measured, dt)
        integral[j] = controller.integral
        if j < len(t) - 1:
            remaining = dt
            while remaining > 1e-12:
                h = min(0.002, remaining)
                state = rk4(state, u[j], h, model, mass)
                remaining -= h
    return dict(t=t, x=x, u=u, integral=integral, target=reference)


def metrics(run):
    t, x = run["t"], run["x"]
    def crossing(level):
        indices = np.flatnonzero(x >= level)
        if not len(indices):
            return None
        j = indices[0]
        if j == 0:
            return float(t[0])
        return float(t[j - 1] + (level - x[j - 1]) * (t[j] - t[j - 1]) / (x[j] - x[j - 1]))
    a, b = crossing(0.1), crossing(0.9)
    outside = np.flatnonzero(np.abs(x - 1) > 0.02)
    settled = 0.0 if not len(outside) else (float(t[outside[-1] + 1]) if outside[-1] < len(t) - 1 else None)
    return dict(rise=None if a is None or b is None else b - a,
                overshoot=float(max(0, (x.max() - 1) * 100)),
                settling=settled, final_error=float(1 - x[-1]))
