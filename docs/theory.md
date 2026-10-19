# Theory

The formulas the app uses, and where they come from. Code: `src/random_walk/theory.py`.

## The step

Each step is +1 (right) with probability p = P(right), between 0 and 1, and -1 (left)
otherwise:

    P(right) = p
    P(left)  = 1 - p

p > 0.5 drifts right and p < 0.5 drifts left. p = 0.5 is the fair 50/50 walk, and p = 0 or 1
makes every step go the same way.

Mean and variance of one step:

    E[step]   = p(+1) + (1 - p)(-1)          = 2p - 1
    Var[step] = E[step^2] - E[step]^2 = 1 - (2p - 1)^2 = 4p(1 - p)

Until v0.3.0 the bias was a slope angle theta (degrees, -90 to 90), with
P(right) = 0.5 - 0.5 sin(theta), so positive theta drifted left. p = 0.5 corresponds to
theta = 0 and draws exactly the same walks from the same seed.

## No wall

The final position after STEPS = n steps is a sum of n independent steps, so

    mean = n (2p - 1)
    sd   = sqrt(4p(1 - p) n)

By the central limit theorem, for large n the final position is approximately
Normal(mean, sd). That is the theory curve drawn when the wall is off.

At p = 0 or 1 the sd is exactly 0 and the walk is deterministic: every walk ends at -n or +n.
There is no spread for a curve to describe (and the normal density would divide by zero), so
the app hides the theory curve, with or without a wall.

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

### Theory curve with a wall (p = 0.5 only)

For a fair walk, the walk reflected at w has the same distribution as the free walk folded
at w (the reflection principle): Y = w + |X - w|, with X ~ Normal(0, sqrt(n)). Its density for
y >= w is

    f(y) = phi(y) + phi(2w - y)        where phi is the Normal(0, sqrt(n)) density

The app currently draws the simpler half-normal centred on the wall:

    f(y) = 2 phi(y - w)                (half_normal_pdf, sd = sqrt(n))

The two agree only when the walk starts at the wall (w = 0). See *Known limitations*.

The reflection principle needs a driftless walk. A biased walk reflected off a wall is a
different and harder problem, so the wall curve is hidden whenever p != 0.5.

## Known limitations

- **Wall curve ignores the starting offset:** the half-normal assumes the walk starts at the
  wall, but it starts at 0. With the defaults (wall -30, 1000 steps, sd about 31.6) the offset
  is about one sd and the curve visibly misfits. The folded normal above is the large-n fix
  for p = 0.5, and also handles a wall above 0.
