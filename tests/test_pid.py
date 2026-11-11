import unittest
import numpy as np

from pid import PID
from simulation import simulate, metrics


class ControllerTests(unittest.TestCase):
    def test_p_equilibrium(self):
        for kp in [10, 40, 100, 300]:
            run = simulate(PID(kp))
            self.assertAlmostEqual(run["x"][-1], kp / (20 + kp), places=6)

    def test_integral_holds_spring_force(self):
        c = PID(100, 80, 12)
        r = simulate(c)
        self.assertLess(abs(1 - r["x"][-1]), 1e-4)
        self.assertAlmostEqual(c.integral, 20, places=2)

    def test_windup_protection(self):
        c = PID(100, 80, limits=(-30, 30))
        for _ in range(100):
            self.assertEqual(c.update(1, 0, 0.01), 30)
        self.assertEqual(c.integral, 0)
        c.integral = 40
        c.update(0, 0.01, 0.01)
        self.assertLess(c.integral, 40)

    def test_measurement_derivative_avoids_kick(self):
        a = PID(0, 0, 12, tau=0)
        b = PID(0, 0, 12, tau=0, derivative_on_measurement=False)
        a.update(0, 0, 0.002)
        b.update(0, 0, 0.002)
        self.assertEqual(a.update(1, 0, 0.002), 0)
        self.assertEqual(b.update(1, 0, 0.002), 6000)

    def test_filter_reduces_noise(self):
        a = simulate(PID(100, 80, 12, tau=0), noise=0.001)
        b = simulate(PID(100, 80, 12, tau=0.02), noise=0.001)
        self.assertLess(np.std(b["u"][-1000:]), np.std(a["u"][-1000:]) / 5)

    def test_force_limit(self):
        r = simulate(PID(100, 80, 12, limits=(-30, 30)), noise=0.001)
        self.assertTrue(np.all(np.abs(r["u"]) <= 30))

    def test_reset_reproducibility(self):
        c = PID(100, 80, 12)
        a = simulate(c, noise=0.001)
        b = simulate(c, noise=0.001)
        np.testing.assert_array_equal(a["x"], b["x"])

    def test_time_step_convergence(self):
        coarse = simulate(PID(100, 80, 12), dt=0.004)
        a = simulate(PID(100, 80, 12), dt=0.002)
        b = simulate(PID(100, 80, 12), dt=0.001)
        coarse_difference = np.max(np.abs(coarse["x"] - a["x"][::2]))
        fine_difference = np.max(np.abs(a["x"] - b["x"][::2]))
        self.assertLess(fine_difference, 0.003)
        self.assertLess(fine_difference, 0.6 * coarse_difference)
        self.assertLess(abs(metrics(a)["settling"] - metrics(b)["settling"]), 0.02)

    def test_invalid_time_step(self):
        for dt in [0, -1, float("nan")]:
            with self.assertRaises(ValueError):
                PID(1).update(1, 0, dt)


if __name__ == "__main__":
    unittest.main()
