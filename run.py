import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from pid import PID
from simulation import metrics, simulate


OUTPUT = Path(__file__).parent / "results"
GAINS = {"P": (100, 0, 0), "PI": (100, 80, 0), "PD": (100, 0, 12), "PID": (100, 80, 12)}


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUTPUT / f"{name}.png", dpi=160)
    plt.close(fig)


def style(ax, title, ylabel="Position (m)", target=True):
    ax.set(title=title, xlabel="Time (s)", ylabel=ylabel)
    if target:
        ax.axhline(1, color="black", ls="--", lw=1, label="Target: 1 m")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)


def response(name, title, runs, duration=None):
    fig, ax = plt.subplots(figsize=(7.6, 3.5))
    for label, run in runs.items():
        ax.plot(run["t"], run["x"], label=label)
    style(ax, title)
    if duration:
        ax.set_xlim(0, duration)
    save(fig, name)


def experiments():
    OUTPUT.mkdir(exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    report = {}
    fig, ax = plt.subplots(figsize=(7.6, 2.0))
    ax.set(xlim=(0, 10), ylim=(0, 3), title="Feedback: keep checking the result")
    ax.axis("off")
    boxes = [(0.7, "Target\nr = 1 m"), (3.0, "Controller\nforce u (N)"), (5.5, "Block\nposition x (m)"), (8.0, "Sensor\nmeasurement y (m)")]
    for x, label in boxes:
        ax.text(x, 1.8, label, ha="center", va="center", bbox=dict(boxstyle="round,pad=0.5", fc="#eef3f6", ec="#34657f"))
    for a, b in [(1.4, 2.2), (3.8, 4.7), (6.3, 7.1)]:
        ax.annotate("", (b, 1.8), (a, 1.8), arrowprops=dict(arrowstyle="->"))
    ax.plot([8, 8, 1.8, 1.8], [1.25, 0.5, 0.5, 1.8], color="#34657f")
    ax.annotate("", (2.2, 1.8), (1.8, 1.8), arrowprops=dict(arrowstyle="->"))
    ax.text(4.7, 0.18, "Subtract the measurement from the target: e = r - y", ha="center")
    save(fig, "01_loop")
    p_runs = {f"Kp = {kp}": simulate(PID(kp)) for kp in [10, 40, 100, 300]}
    response("02_p", "P only: stronger push, smaller remaining error", p_runs, 5)
    report["p_check"] = [{"kp": kp, "predicted": kp / (kp + 20), "simulated": r["x"][-1]} for kp, r in zip([10, 40, 100, 300], p_runs.values())]
    pi_runs = {f"Ki = {ki}": simulate(PID(100, ki)) for ki in [0, 40, 80, 200]}
    response("03_i", "Adding I: remove the remaining error", pi_runs)
    d_runs = {f"Kd = {kd}": simulate(PID(100, 80, kd)) for kd in [0, 6, 12, 24]}
    response("04_d", "Adding D: braking changes the transient", d_runs, 5)
    comparisons = {key: simulate(PID(*g)) for key, g in GAINS.items()}
    report["comparison"] = {key: metrics(run) for key, run in comparisons.items()}
    report["gain_trials"] = [dict(kp=g[0], ki=g[1], kd=g[2], **metrics(simulate(PID(*g))))
                             for g in [(100, 80, 6), (100, 80, 12), (100, 80, 24)]]
    response("05_comparison", "P, PI, PD and PID on the same block", comparisons, 8)
    run = comparisons["PI"]
    m = metrics(run)
    fig, ax = plt.subplots(figsize=(7.6, 3.7))
    ax.plot(run["t"], run["x"], label="PI: (100, 80, 0)")
    ax.axhspan(0.98, 1.02, alpha=0.15, color="green", label="2% settling band")
    for level in [0.1, 0.9]:
        j = np.flatnonzero(run["x"] >= level)[0]
        ax.plot(run["t"][j], level, "ko")
    peak = np.argmax(run["x"])
    ax.annotate(f"Overshoot: {m['overshoot']:.2f}%", (run["t"][peak], run["x"][peak]), (2.5, 1.18), arrowprops=dict(arrowstyle="->"))
    ax.text(0.7, 0.43, f"Rise from 10% to 90%: {m['rise']:.3f} s")
    ax.axvline(m["settling"], ls=":", color="green", label=f"Settling: {m['settling']:.3f} s")
    ax.annotate(f"Final error at 12 s: {m['final_error']:.5f} m", (12, run["x"][-1]), (5, 0.75), arrowprops=dict(arrowstyle="->"))
    style(ax, "Four measures of a step response")
    ax.set_ylim(0, 1.3)
    save(fig, "06_metrics")
    wind = {"Without anti-windup": simulate(PID(100, 200, 8, limits=(-30, 30), anti_windup=False)),
            "Conditional integration": simulate(PID(100, 200, 8, limits=(-30, 30)))}
    fig, axes = plt.subplots(3, 1, figsize=(7.6, 6.0), sharex=True)
    for key, ylabel in [("x", "Position (m)"), ("u", "Force (N)"), ("integral", "I contribution (N)")]:
        ax = axes[["x", "u", "integral"].index(key)]
        for label, r in wind.items():
            ax.plot(r["t"], r[key], label=label)
        style(ax, {"x": "30 N limit: windup and its fix", "u": "Applied force stays within the motor limit", "integral": "Stored integral contribution"}[key], ylabel, key == "x")
    save(fig, "07_windup")
    report["windup"] = {k: metrics(v) for k, v in wind.items()}
    noisy = {"Unfiltered D": simulate(PID(100, 80, 12, tau=0), noise=0.001),
             "Filtered D, tau = 0.02 s": simulate(PID(100, 80, 12, tau=0.02), noise=0.001)}
    fig, axes = plt.subplots(2, 1, figsize=(7.6, 4.7))
    for label, r in noisy.items():
        axes[0].plot(r["t"], r["x"], label=label)
        axes[1].plot(r["t"], r["u"], label=label, lw=0.8)
    style(axes[0], "Sensor noise: uniform +/-1 mm (seed 17)")
    style(axes[1], "Zoom: force variation after settling", "Force (N)", False)
    axes[1].set_xlim(8, 8.3)
    save(fig, "08_noise")
    report["noise_force_std"] = {k: float(np.std(r["u"][r["t"] >= 8])) for k, r in noisy.items()}
    kick = {"Derivative of error": simulate(PID(100, 80, 12, tau=0, derivative_on_measurement=False), target=lambda t: float(t >= 1)),
            "Derivative of measurement": simulate(PID(100, 80, 12, tau=0), target=lambda t: float(t >= 1))}
    fig, ax = plt.subplots(figsize=(7.6, 3.3))
    for label, r in kick.items():
        ax.plot(r["t"], r["u"], label=label)
    style(ax, "Target step at 1 s: derivative kick", "Force (N)", False)
    ax.set_xlim(0.98, 1.08)
    save(fig, "09_kick")
    report["kick_peak"] = {k: float(np.max(r["u"])) for k, r in kick.items()}
    slow = {f"dt = {dt} s": simulate(PID(100, 80, 12, limits=(-30, 30)), dt=dt) for dt in [0.002, 0.05, 0.2, 0.5]}
    response("10_sampling", "Slow updates: the controller reacts to old information", slow, 8)
    report["sampling"] = {k: metrics(v) for k, v in slow.items()}
    ku, tu = 8.0, 2 * np.pi / np.sqrt(3)
    ultimate = {f"Kp = {kp}": simulate(PID(kp, tau=0), model="lag", duration=35) for kp in [4, 8, 10]}
    fig, ax = plt.subplots(figsize=(7.6, 3.4))
    for label, r in ultimate.items():
        ax.plot(r["t"], r["x"], label=label)
    style(ax, "Second plant: approach the sustained oscillation", "Output (dimensionless)", False)
    save(fig, "11_ultimate")
    r = ultimate["Kp = 8"]
    peaks = np.flatnonzero((r["x"][1:-1] > r["x"][:-2]) & (r["x"][1:-1] >= r["x"][2:])) + 1
    peaks = peaks[r["t"][peaks] > 10]
    period = float(np.mean(np.diff(r["t"][peaks])))
    zn_gains = (0.6 * ku, 1.2 * ku / tu, 0.075 * ku * tu)
    tuning = {"Ziegler-Nichols": simulate(PID(*zn_gains, tau=0), model="lag", duration=30),
              "Adjusted (3, 1, 2)": simulate(PID(3, 1, 2, tau=0), model="lag", duration=30)}
    fig, ax = plt.subplots(figsize=(7.6, 3.5))
    for label, r in tuning.items():
        ax.plot(r["t"], r["x"], label=label)
    style(ax, "Second plant: recipe gains and adjusted gains", "Output (dimensionless)", False)
    ax.axhline(1, ls="--", color="black", label="Target: 1")
    ax.legend(fontsize=8)
    save(fig, "12_tuning")
    report["zn"] = dict(ku=ku, theoretical_period=tu, measured_period=period, gains=zn_gains,
                        metrics={k: metrics(v) for k, v in tuning.items()})
    final = simulate(PID(*GAINS["PID"], limits=(-30, 30)), noise=0.001)
    fig, axes = plt.subplots(2, 1, figsize=(7.6, 4.5), sharex=True)
    axes[0].plot(final["t"], final["x"], label="PID (100, 80, 12), noisy sensor")
    style(axes[0], "Reusable controller with all practical fixes enabled")
    axes[1].plot(final["t"], final["u"], label="Applied force")
    style(axes[1], "Force limited to +/-30 N", "Force (N)", False)
    save(fig, "13_final")
    report["final"] = metrics(final)
    with (OUTPUT / "final_run.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time_s", "target_m", "position_m", "force_N", "integral_N"])
        writer.writerows(zip(*(final[k] for k in ["t", "target", "x", "u", "integral"])))
    (OUTPUT / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    with (OUTPUT / "comparison.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["controller", "rise_s", "overshoot_percent", "settling_s", "error_at_12s_m"])
        for k, v in report["comparison"].items():
            writer.writerow([k, *v.values()])
    with (OUTPUT / "gain_trials.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["kp_N_per_m", "ki_N_per_m_s", "kd_N_s_per_m", "rise_s", "overshoot_percent", "settling_s", "error_at_12s_m"])
        writer.writerows(row.values() for row in report["gain_trials"])
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", action="store_true", help="Also rebuild the PDF document")
    args = parser.parse_args()
    data = experiments()
    print(json.dumps(data, indent=2))
    if args.report:
        from report import build_report
        build_report(data)
