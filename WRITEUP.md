# Brief write-up

## Approach

I used the mass-spring-damper equation to connect each part of PID with a physical effect. Before comparing controllers, I calculated the P-only equilibrium and checked it against four simulated gains. I then added integral and derivative action separately, compared all four controller types, and tested the practical problems one at a time.

The controller and plant are separate Python modules. The same controller can run either the block or the three-stage lag plant used for Ziegler-Nichols tuning. All figures and measurements come from one script, with a fixed seed for the noisy sensor.

## What worked

The P-only positions matched the calculated values to six decimal places. Integral action supplied the 20 N needed to hold the spring at 1 m. Adding derivative action to the PI controller reduced the unconstrained overshoot from 9.56% to zero for the selected gains.

With Kp = 100 and Ki = 80, I also compared Kd = 6, 12 and 24. Kd = 12 gave the shortest settling time of these three in the unconstrained test. Kd = 6 rose faster but took longer to finish approaching the target; Kd = 24 gave 2.52% overshoot.

Conditional integration reduced overshoot from 24.98% to zero in the saturated windup test. Filtering the derivative reduced steady force variation from 5.00 N to 0.38 N under the same sensor noise. With all fixes enabled, the final controller settled in 2.71 s with a 30 N force limit.

## What did not work well

P and PD retained a position error because neither supplied enough force at zero error. An unfiltered derivative amplified small sensor changes. A derivative taken from error produced a large force spike when the target changed. Slow controller updates also caused oscillation even though the plant integration remained accurate.

The Ziegler-Nichols gains gave 52.58% overshoot on the second plant. Adjusting the gains reduced it to 15.06%, but increased rise time from 0.949 s to 1.471 s. The recipe was useful as a starting point, rather than a final answer.

## What I would explore next

I would test a wider range of masses and damping values, add an external disturbance force, and compare conditional integration with back-calculation anti-windup. I would also try spring-force feedforward and setpoint weighting. The current model leaves out friction, actuator lag, sensor delay and timing jitter, so hardware testing would be the next important check.

## Tool-use disclosure


