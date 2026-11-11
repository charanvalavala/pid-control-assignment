from dataclasses import dataclass
import math


@dataclass
class PID:
    kp: float
    ki: float = 0.0
    kd: float = 0.0
    limits: tuple = (-math.inf, math.inf)
    tau: float = 0.02
    anti_windup: bool = True
    derivative_on_measurement: bool = True

    def __post_init__(self):
        if self.tau < 0 or self.limits[0] >= self.limits[1]:
            raise ValueError("Invalid filter time or output limits")
        self.reset()

    def reset(self):
        self.integral = 0.0
        self.derivative = 0.0
        self.previous = None

    def update(self, target, measured, dt):
        if not all(math.isfinite(v) for v in (target, measured, dt)) or dt <= 0:
            raise ValueError("Inputs must be finite and dt must be positive")
        error = target - measured
        signal = -measured if self.derivative_on_measurement else error
        raw = 0.0 if self.previous is None else (signal - self.previous) / dt
        alpha = self.tau / (self.tau + dt)
        self.derivative = alpha * self.derivative + (1 - alpha) * raw
        candidate = self.integral + self.ki * error * dt
        trial = self.kp * error + candidate + self.kd * self.derivative
        lo, hi = self.limits
        blocked = (trial > hi and self.ki * error > 0) or (trial < lo and self.ki * error < 0)
        if not self.anti_windup or not blocked:
            self.integral = candidate
        output = self.kp * error + self.integral + self.kd * self.derivative
        self.previous = signal
        return min(hi, max(lo, output))
