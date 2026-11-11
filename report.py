from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle


ROOT = Path(__file__).parent


def build_report(data):
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Body", fontName="Helvetica", fontSize=10.4, leading=15, spaceAfter=9))
    styles.add(ParagraphStyle(name="CaptionLocal", fontSize=9, leading=12, textColor=colors.HexColor("#465b65"), spaceAfter=12))
    styles.add(ParagraphStyle(name="EquationLocal", fontName="Courier", fontSize=10, leading=16, backColor=colors.HexColor("#eff4f6"), borderPadding=9, spaceBefore=6, spaceAfter=14))
    styles.add(ParagraphStyle(name="TitleLocal", fontSize=26, leading=31, spaceAfter=16, textColor=colors.HexColor("#24495d")))
    story = []
    def p(text):
        story.append(Paragraph(text, styles["Body"]))
    def title(text):
        story.append(Paragraph(text, styles["TitleLocal"]))
    def sub(text):
        story.append(Paragraph(text, styles["Heading2"]))
    def eq(text):
        story.append(Paragraph(escape(text).replace("\n", "<br/>"), styles["EquationLocal"]))
    def plot(name, caption, height=None):
        from PIL import Image as PILImage
        path = ROOT / "results" / f"{name}.png"
        with PILImage.open(path) as im:
            w, h = im.size
        width = 6.7 * inch
        if height and h / w * width > height * inch:
            width = height * inch * w / h
        story.append(Image(str(path), width=width, height=width * h / w))
        story.append(Paragraph(caption, styles["CaptionLocal"]))
    def table(rows, widths=None):
        wrapped = [[Paragraph(str(c), styles["CaptionLocal"]) for c in row] for row in rows]
        t = Table(wrapped, colWidths=widths, hAlign="LEFT")
        t.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#e4edf2")), ("VALIGN", (0,0), (-1,-1), "TOP"), ("BOTTOMPADDING", (0,0), (-1,-1), 5), ("TOPPADDING", (0,0), (-1,-1), 5), ("LINEBELOW", (0,0), (-1,0), 0.6, colors.gray), ("LINEBELOW", (0,1), (-1,-1), 0.2, colors.lightgrey)]))
        story.append(t)
        story.append(Spacer(1, 10))
    def page():
        story.append(PageBreak())
    def value(v):
        return "Not reached" if v is None else f"{v:.3f}"

    title("Learning PID control")
    p("Valavala Charan Teja<br/>Intern assignment | Modern Monk Labs")
    sub("1. The basic idea")
    p("A controller repeatedly compares what we want with what we measure, then changes an input to reduce the difference. The desired value is the <b>setpoint</b>. The difference is the <b>error</b>. The thing we are controlling is the <b>plant</b>.")
    p("Think about adjusting a shower. If the water is colder than you want, turn the hot tap up. As it gets close to the right temperature, make smaller changes. If it is warming quickly, stop turning before it gets too hot. Keep checking, because the water pressure can change.")
    eq("error = target - measurement\ne(t) = r(t) - y(t)")
    plot("01_loop", "Figure 1. The sensor closes the loop: each new measurement changes the next controller output.")
    p("For the block in this assignment, the target is 1 m and the input is force in newtons. If the position is 0.7 m, the error is +0.3 m. A positive force pushes it towards the target. If it moves beyond 1 m, the error becomes negative.")
    p("Feedback helps correct mistakes, but it is not automatically stable. An input that is too strong, too late, or based on a noisy measurement can make the motion worse.")
    page()

    title("2. The PID formula")
    p("PID adds three responses: one to the error now, one to the error accumulated so far, and one to the rate at which the error changes.")
    eq("u(t) = Kp e(t) + Ki integral[0 to t] e(q) dq\n       + Kd de(t)/dt")
    table([["Symbol", "Meaning", "Unit for this block"], ["t, q", "Time; q is the integration variable", "s"], ["r, y, e", "Target, measured position, error", "m"], ["u", "Commanded force", "N"], ["Kp", "Proportional gain", "N/m"], ["Ki", "Integral gain", "N/(m s)"], ["Kd", "Derivative gain", "N s/m"]], [65, 280, 137])
    p("<b>P: present error.</b> A larger error produces a larger push. P reacts immediately, but its force becomes zero when the error is zero.<br/><b>I: past error.</b> Small errors add up. This builds the holding force that P cannot supply at zero error.<br/><b>D: changing error.</b> With a fixed target, D opposes fast motion. It acts like extra damping. Differentiation also magnifies measurement noise.")
    sub("The small steps used by the code")
    eq("e[n] = r[n] - y[n]\nJ_trial = J[n-1] + Ki e[n] dt\nv[n] = -(y[n] - y[n-1]) / dt\na = tau / (tau + dt)\nd[n] = a d[n-1] + (1-a) v[n]\nu_raw[n] = Kp e[n] + J[n] + Kd d[n]\nu[n] = clip(u_raw[n], lower, upper)")
    p("Here n counts controller updates; dt is the time between them in seconds. J stores the integral <i>force</i> in N, so Ki is already included. d is a filtered velocity in m/s; tau is the filter time in seconds. The code differentiates -y instead of e to avoid a target-change spike. For a fixed target these derivatives agree. Setting tau = 0 removes the filter.")
    p("Normally J becomes J_trial. With anti-windup, keep the old J when the trial output exceeds a limit and the new integral increment would push it further beyond that limit. Allow increments that help it return. Start J and d at zero; the first derivative is zero because there is no previous sample.")
    page()

    title("3. The test system")
    p("The plant is a 1 kg block connected to a spring and a damper. The spring pulls it back towards its rest position. The damper opposes velocity, like a shock absorber.")
    eq("m x'' + b x' + k x = u\nm = 1 kg, b = 10 N s/m, k = 20 N/m\nx'' = (u - 10 x' - 20 x) / 1")
    p("At rest, velocity and acceleration are zero. At x = 1 m the spring pulls with 20 N, so the actuator must keep supplying 20 N. The damper needs no force at rest. A 30 N actuator can hold this target, but cannot hold a position above 1.5 m indefinitely.")
    sub("4. How to judge a result")
    p("<b>Rise time:</b> time from first reaching 10% to first reaching 90% of the 1 m target. <b>Overshoot:</b> max(0, peak position - 1) / 1, as a percentage. <b>Settling time:</b> first sampled time after which the response stays within 0.98 to 1.02 m for the rest of the run. <b>Final error:</b> target minus the last position. A finite run only estimates steady-state error.")
    plot("06_metrics", "Figure 2. All four measures are marked on the PI response. The two black dots define the 10-90% rise interval.", 3.5)
    p("The comparison uses 12 s runs, dt = 0.002 s and zero initial position/velocity. Missing rise time means 90% was never reached; missing settling time means the run did not finish inside the band. Rise crossings use linear interpolation. Settling is checked at samples, so it is only resolved to dt.")
    page()

    title("5. Each part alone")
    sub("First: P only at four strengths")
    p("P applies u = Kp(1 - x). At equilibrium this must balance the spring. Solving that balance predicts exactly where the block stops.")
    eq("20 x_ss = Kp (1 - x_ss)\nx_ss = Kp / (20 + Kp)\ne_ss = 20 / (20 + Kp)")
    plot("02_p", "Figure 3. Larger Kp reduces the final error but makes the early response more oscillatory. The curves are simulated for 12 s; the first 5 s are shown.")
    table([["Kp (N/m)", "Predicted x (m)", "Simulated x at 12 s (m)", "Error (m)"]] + [[r["kp"], f"{r['predicted']:.6f}", f"{r['simulated']:.6f}", f"{1-r['predicted']:.6f}"] for r in data["p_check"]], [90, 120, 170, 102])
    p("The prediction and simulation agree to six decimal places. With finite positive Kp, P alone stops short for this spring-loaded plant because a nonzero error is needed to generate a nonzero holding force. This is a property of this plant and controller, not a rule for every possible plant.")
    page()

    title("5. Adding I, then D")
    p("Keeping Kp = 100, I adds the missing holding force. Once the position is correct, the integral can retain 20 N even when the error is zero. Increasing Ki too far makes this stored push build faster than the block can respond.")
    plot("03_i", "Figure 4. Ki = 40, 80 and 200 remove the P-only offset; larger Ki can increase overshoot.", 2.5)
    p("Next, keep Kp = 100 and Ki = 80 and add D. For a constant target and ideal unfiltered derivative, the PD equation is x'' + (10 + Kd)x' + (20 + Kp)x = Kp r. D increases the damping coefficient. It does not supply the missing constant force at equilibrium.")
    plot("04_d", "Figure 5. Increasing Kd changes the braking. The chosen Kd = 12 removes the PI overshoot in this test; excessive braking can make the approach slower.", 2.5)
    p(f"With Ki = 80, the measured overshoot changes from {data['comparison']['PI']['overshoot']:.2f}% at Kd = 0 to {data['comparison']['PID']['overshoot']:.2f}% at Kd = 12. These plots use a 0.02 s derivative filter and no force limit, to separate the effects of the gains.")
    page()

    title("6. All together")
    p("P, PI, PD and PID are compared with the same plant, target and time step. P and PD share Kp = 100. PI and PID add Ki = 80; PD and PID use Kd = 12. The derivative filter time is 0.02 s.")
    plot("05_comparison", "Figure 6. PI removes the offset but overshoots. PD adds damping but retains the offset. PID combines the holding force and braking.")
    table([["Type", "Rise (s)", "Overshoot (%)", "Settling (s)", "Error at 12 s (m)"]] + [[key, value(r["rise"]), f"{r['overshoot']:.3f}", value(r["settling"]), f"{r['final_error']:.6f}"] for key, r in data["comparison"].items()], [55, 95, 110, 110, 112])
    p("I chose <b>Kp = 100 N/m, Ki = 80 N/(m s), Kd = 12 N s/m</b>. In this unconstrained test, PID has no measured overshoot and settles in 1.038 s. PI rises faster, but overshoots by 9.56% and settles in 2.602 s. PD never reaches 90% of the target, so its rise time is not reported.")
    p("These gains are a compromise for this model, not an optimum. The force at the start exceeds 30 N in the unconstrained experiment. Section 9 repeats the chosen gains with the actual limit and sensor noise; that result takes longer to settle.")
    page()

    title("7. Real-world problems")
    sub("(a) Force limit and integral windup")
    p("When the actuator is already at 30 N, a larger command cannot move the block any faster. An unrestricted integral still adds error during that wait. By the time the block arrives, too much positive integral force remains. The block overshoots while that stored value unwinds.")
    p("For this demonstration I use (Kp, Ki, Kd) = (100, 200, 8), tau = 0.02 s and a symmetric +/-30 N limit. Both runs have the same gains; only conditional integration changes.")
    plot("07_windup", "Figure 7. The output is clipped in both cases. Anti-windup stops the integral from storing an unnecessary push while saturation is active.", 4.7)
    a, b = data["windup"].values()
    p(f"Overshoot falls from {a['overshoot']:.2f}% to {b['overshoot']:.2f}%. Settling time changes from {a['settling']:.3f} s to {b['settling']:.3f} s. Anti-windup cannot create extra actuator force or make an unreachable target reachable.")
    page()

    title("7. Noise and target changes")
    sub("(b) A noisy sensor makes D jumpy")
    p("The sensor gets independent uniform noise between -0.001 and +0.001 m at every sample. Dividing small differences by dt = 0.002 s creates a large apparent velocity. A first-order derivative filter smooths that velocity, with a delay as the tradeoff.")
    plot("08_noise", "Figure 8. Both runs use identical noise samples. Filtering reduces the rapid force variation even though the position curves look similar.", 3.0)
    p(f"From 8 to 12 s, force standard deviation drops from {data['noise_force_std']['Unfiltered D']:.3f} N to {data['noise_force_std']['Filtered D, tau = 0.02 s']:.3f} N with tau = 0.02 s. These runs have no saturation so clipping cannot hide the derivative noise.")
    sub("(c) Derivative kick")
    p("At t = 1 s the target jumps from 0 to 1 m. Derivative of error sees a change of 1/0.002 = 500 m/s, so Kd = 12 creates a 6000 N derivative term. Differentiating the measurement avoids that target term. P still changes immediately.")
    plot("09_kick", "Figure 9. With no filter or saturation, peak total force is 6100.16 N for derivative of error and 100.16 N for derivative of measurement.", 2.1)
    page()

    title("7. Slow controller updates")
    sub("(d) Sampling time is part of the controller")
    p("A digital controller only sees the state at update times. Between updates the last force is held constant. If updates are slow, the block can move past where that force was sensible before the next correction arrives.")
    plot("10_sampling", "Figure 10. The gains and +/-30 N limit are fixed. Only the controller update interval changes; plant integration remains at 0.002 s or smaller.")
    table([["Update interval", "Overshoot (%)", "Settling (s)", "Error at 12 s (m)"]] + [[k, f"{r['overshoot']:.2f}", value(r["settling"]), f"{r['final_error']:.4f}"] for k, r in data["sampling"].items()], [150, 110, 110, 112])
    p("The 0.5 s controller does not settle during the 12 s run. Its last error is about -0.154 m. Returning to 0.002 s updates fixes the sampled-control problem for these gains. The 0.2 s case is also much slower to settle than the 0.002 s case.")
    p("The plant uses fourth-order Runge-Kutta integration with held input. Splitting a slow control interval into small plant steps keeps the comparison from being just a large-step integration error. A real controller should measure actual elapsed time, run at a reliable rate, and be retuned if the update interval changes.")
    page()

    title("8. Choosing the gains")
    sub("A practical hand-tuning sequence")
    p("1. Check signs and units. Apply a small positive force and verify that position increases. Confirm that the target can be held within the actuator limit.<br/>2. Start with Ki = Kd = 0. Increase Kp gradually until the response is quick enough, then reduce it if the motion rings too much.<br/>3. Add a small Ki to remove the remaining error. Increase it slowly; back off if overshoot or slow oscillation grows.<br/>4. Add Kd to damp the motion. Use derivative-on-measurement and filtering before testing noisy feedback.<br/>5. Enable force limits and anti-windup. Test target changes, noise, different loads and a slower update interval. Record the same four measures after each change.")
    sub("Ziegler-Nichols on a second plant")
    p("For G(s) = 1/(s+1)<super>3</super>, simulate three first-order stages: z1' = u - z1, z2' = z1 - z2, z3' = z2 - z3, y = z3. Here input and output are dimensionless, and each stage has a 1 s time constant. Use P only with no output limit and increase Kp.")
    plot("11_ultimate", "Figure 11. Kp = 4 gives decaying oscillations; Kp = 8 is close to sustained oscillation; Kp = 10 gives growing oscillations.", 3)
    eq("(s+1)^3 + Kp = 0\ns = j w: 3w - w^3 = 0 -> w = sqrt(3) rad/s\n1 - 3w^2 + Ku = 0 -> Ku = 8\nTu = 2 pi / sqrt(3) = 3.6276 s")
    p(f"The mean spacing of simulated peaks after 10 s is {data['zn']['measured_period']:.4f} s. The held-input digital simulation is slightly different from the continuous marginally stable system, so the amplitude at Kp = 8 is only approximately constant. This unsafe oscillation search belongs in simulation, not on an unprotected robot.")
    page()

    title("8. Recipe and adjustment")
    p("The closed-loop Ziegler-Nichols recipe uses ultimate gain Ku and period Tu. This table uses parallel gains, so Ki = Kp/Ti and Kd = Kp Td.")
    table([["Controller", "Kp", "Ki", "Kd"], ["P", "0.5 Ku", "0", "0"], ["PI", "0.45 Ku", "0.54 Ku / Tu", "0"], ["PID", "0.60 Ku", "1.20 Ku / Tu", "0.075 Ku Tu"]], [105, 100, 142, 135])
    eq("Ku = 8, Tu = 3.6276 s\nPID: Kp = 4.8, Ki = 2.6464 1/s, Kd = 2.1766 s")
    p("I use derivative-on-measurement without filtering for this noise-free comparison. The textbook recipe is a starting point. Its aggressive integral action gives a fast response but substantial overshoot on this plant. Reducing Kp and Ki gives the adjusted gains (3, 1, 2).")
    plot("12_tuning", "Figure 12. Adjusting the recipe reduces overshoot, with a slower rise. Neither response has an actuator limit or sensor noise.", 3.1)
    table([["Gains", "Rise (s)", "Overshoot (%)", "Settling (s)"]] + [[k, value(r["rise"]), f"{r['overshoot']:.2f}", value(r["settling"])] for k, r in data["zn"]["metrics"].items()], [190, 90, 110, 92])
    p("Overshoot drops from 52.58% to 15.06%, while rise time increases from 0.949 s to 1.471 s. I would reduce Ki further or try setpoint weighting if a lower overshoot were required. The same gains should not be transferred to the spring-block plant: the dynamics and units are different.")
    page()

    title("9. The code")
    p("<b>pid.py</b> contains a reusable PID class. It has update(target, measured, dt) and reset() methods. It keeps the integral contribution, previous derivative input and filtered derivative between updates. The controller does not know the plant equation.")
    p("<b>simulation.py</b> integrates either plant with RK4, holds the control output between updates, and calculates response measures. <b>run.py</b> creates all the experiments and graphs, saves the measurements, and can rebuild this document through <b>report.py</b>.")
    eq("controller = PID(100, 80, 12, limits=(-30, 30),\n                 tau=0.02)\nrun = simulate(controller, noise=0.001)")
    plot("13_final", "Figure 13. The chosen controller on the block with +/-30 N force, +/-1 mm sensor noise, derivative filtering, derivative-on-measurement and anti-windup.", 3.5)
    r = data["final"]
    p(f"The practical run rises in {r['rise']:.3f} s, overshoots by {r['overshoot']:.3f}%, settles in {r['settling']:.3f} s, and ends with error {r['final_error']:.7f} m. The actual position is used for these measures; the controller sees the noisy position. Force is always between -30 and +30 N.")
    p("Run <b>python run.py --report</b> to recreate every graph and the PDF. Results use a fixed random seed of 17. The CSV contains time, target, actual position, force and integral contribution. The README includes environment setup and commands for the checks.")
    page()

    title("10. Real robots &amp; myths")
    table([["Application", "What PID does", "What needs care"], ["DC motor speed", "Encoder speed is compared with the requested rpm; the output changes motor voltage or duty cycle.", "Load torque, voltage limits and low-speed measurement noise."], ["Drone attitude", "An angle loop requests angular rate; inner rate loops use gyro feedback to request motor torque.", "Fast updates, vibration and coupled axes; one PID is not the whole flight controller."], ["Robot arm joint", "Measured joint angle is compared with the desired angle; output requests motor torque.", "Gravity varies with posture; feedforward and joint limits help."], ["Line-following robot", "A sensor estimates lateral line error; the correction changes the difference between wheel speeds.", "Lost-line detection, sharp corners and limited wheel speed."]], [100, 205, 177])
    sub("Common wrong beliefs")
    p("<b>'Increasing Kp always helps.'</b> It reduces the block's offset but can increase oscillation and saturation.<br/><b>'D removes steady-state error.'</b> D is zero at rest; the PD block still has a 0.1667 m offset.<br/><b>'I is always harmless.'</b> I can wind up against a force limit; this test gives 24.98% overshoot without protection.<br/><b>'One set of gains works everywhere.'</b> Plant mass, damping, sensor quality and update rate affect suitable gains.<br/><b>'PID needs an exact plant model.'</b> It can be tuned from measured responses, but a model helps explain limitations and test changes before hardware experiments.")
    sub("References")
    p('University of Michigan, <a href="https://ctms.engin.umich.edu/CTMS/index.php?example=Introduction&amp;section=ControlPID" color="#24495d">Control Tutorials: Introduction to PID Controller Design</a>. Used for the mass-spring-damper model and the interpretation of the three terms.')
    p('University of Michigan, <a href="https://eecs.umich.edu/courses/eng100/lec5/ZieglerNichols.html" color="#24495d">Ziegler-Nichols PID tuning table</a>. Used for the closed-loop recipe factors. All plots here are generated by the submitted Python code.')
    sub("Tool-use disclosure")
    story.append(Spacer(1, 28))

    out = ROOT / "output" / "pdf"
    out.mkdir(parents=True, exist_ok=True)
    def footer(canvas, doc):
        canvas.setStrokeColor(colors.HexColor("#d0dce2"))
        canvas.line(45, 38, 550, 38)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#465b65"))
        canvas.drawString(45, 25, "PID control | Valavala Charan Teja")
        canvas.drawRightString(550, 25, str(doc.page))
    doc = SimpleDocTemplate(str(out / "pid_control.pdf"), pagesize=(595.28, 841.89), leftMargin=45, rightMargin=45, topMargin=40, bottomMargin=52, title="Learning PID control", author="Valavala Charan Teja")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"Saved {out / 'pid_control.pdf'}")
