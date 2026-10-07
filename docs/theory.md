# Theory

The formulas the app uses, and where they come from. Code: `src/random_walk/theory.py`.

## The step

Each step is +1 (right) or -1 (left). The slope angle theta (degrees, -90 to 90) sets the bias:

    P(right) = 0.5 - 0.5 sin(theta)
    P(left)  = 1 - P(right) = 0.5 + 0.5 sin(theta)

Positive theta biases left and negative theta biases right. theta = 0 is the fair 50/50 walk,
and theta = +/-90 makes every step go the same way.

Mean and variance of one step, with p = P(right):

    E[step]   = p(+1) + (1 - p)(-1) = 2p - 1                 = -sin(theta)
    Var[step] = E[step^2] - E[step]^2 = 1 - sin^2(theta)     =  cos^2(theta)

## No wall

The final position after STEPS = n steps is a sum of n independent steps, so

    mean = -n sin(theta)
    sd   = sqrt(n) |cos(theta)|

By the central limit theorem, for large n the final position is approximately
Normal(mean, sd). That is the theory curve drawn when the wall is off.

At theta = +/-90 the sd is 0 and the walk is deterministic, so there is no normal curve to
draw. See *Known limitations* below.

## Parity

Every step changes the position by an odd amount, so after n steps the position has the same
parity as n. Histograms therefore use width-2 bins centred on positions of that parity
(`simulation.parity_bins`). Width-1 bins would leave every other bin empty.

## The reflecting wall

With the wall at w, a step that lands below w is mirrored back: position -> 2w - position.
Once the walk is at or above the wall, that only ever happens one step past it, so w - 1
becomes w + 1. If the wall is above the start (w > 0), the first step lands further below and
is mirrored to 2w - (+/-1), which puts it above the wall from then on.

This is a reflection, not a clamp. Clamping (w - 1 -> w) would change the parity. Reflection
keeps it, because 2w - x has the same parity as x.

The simulation applies the rule as a fold after every step, x -> w + |x - w|. That is
identical to the mirror for positions below w and does nothing at or above w.

### Theory curve with a wall (theta = 0 only)

For a fair walk, the walk reflected at w has the same distribution as the free walk folded
at w (the reflection principle): Y = w + |X - w|, with X ~ Normal(0, sqrt(n)). Its density for
y >= w is

    f(y) = phi(y) + phi(2w - y)        where phi is the Normal(0, sqrt(n)) density

The app currently draws the simpler half-normal centred on the wall:

    f(y) = 2 phi(y - w)                (half_normal_pdf, sd = sqrt(n))

The two agree only when the walk starts at the wall (w = 0). See *Known limitations*.

The reflection principle needs a driftless walk. A biased walk reflected off a wall is a
different and harder problem, so the wall curve is hidden whenever theta != 0.

## Known limitations

These are recorded here and deliberately left unchanged by the package refactor.

- **theta = +/-90:** sd = 0, so the curve formulas divide by zero. You get NaNs and numpy
  warnings instead of a curve.
- **Wall curve ignores the starting offset:** the half-normal assumes the walk starts at the
  wall, but it starts at 0. With the defaults (wall -30, 1000 steps, sd about 31.6) the offset
  is about one sd and the curve visibly misfits. The folded normal above is the large-n fix
  for theta = 0, and also handles a wall above 0.
