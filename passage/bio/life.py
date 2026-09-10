"""What the lineage eats, which is not the same as what it meant to eat.

Two things change a diet, and they are the same mechanism seen from either
side.

**An intention** is what the player asks for: eat more fish, cut the processed
meat, drink less. It is a direction rather than a menu, because that is how
dietary advice is actually given and actually followed. And it lands
imperfectly, for two honest reasons.

The first is that nobody eats a number. Aim to halve the fat and you might
manage a third of it, or overshoot; the amount that lands is drawn from the
lineage's own seeded stream, so a run is reproducible and a given nudge is not
predictable.

The second is **substitution**, and it is the one that matters. Food removed
from a diet does not leave a hole -- something fills it, and what fills it is
whatever is nearest to hand. Cut the red meat without deciding what replaces it
and a good part of what comes back is sweet, because that is what is easy. A
player who nudges without watching what moves in behind will end up eating worse
than they started, having done exactly what they were told.

**An event** is what happens anyway. A night out, a bad week, a stretch of flu.
These are not punishments for playing badly and they are not random in the sense
of being unfair: every one of them is listed in the appendix from the first
second, and each announces itself in the margin when it arrives. What they are
is *outside the plan* -- a diet you did not choose, for a while, whatever you
had configured for. The lineage that survives them is the one that left itself
some room.

Nothing here is hidden and nothing here is a surprise in the cheap sense. The
appendix says which events a run can bring and what each does. What it cannot
tell you is when.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .. import tuning
from ..data import foods as food_data


@dataclass(frozen=True)
class Intention:
    """A direction a player asks the eating to move in."""

    id: str
    label: str
    #: Multipliers on portions, by food. Below 1 is less of it.
    shift: dict[str, float] = field(default_factory=dict)
    #: Multipliers on every food not named in ``shift``.
    rest: float = 1.0
    note: str = ""


@dataclass(frozen=True)
class Event:
    """Something that happens to the eater, whatever they had planned."""

    id: str
    label: str
    #: What it puts on top of the diet, in portions, for as long as it lasts.
    adds: dict[str, float] = field(default_factory=dict)
    #: Multipliers on the ordinary diet while it runs.
    scales: dict[str, float] = field(default_factory=dict)
    everything: float = 1.0
    seconds: float = 45.0
    #: What the margin says when it lands.
    tells: str = ""


#: The nudges. Deliberately the shape real advice takes -- a direction and a
#: food, not a quantity -- and deliberately not a full set of dials.
INTENTIONS: list[Intention] = [
    Intention("more_fish", "eat more fish",
              {"fish": 1.6}, rest=0.94,
              note="the one rich food in the game that costs nothing"),
    Intention("less_processed", "cut the processed meat",
              {"processed_meat": 0.35, "red_meat": 0.7},
              note="the steepest bill on the menu, and the easiest to replace "
                   "with something equally steep"),
    Intention("less_sugar", "less sweet",
              {"sweets": 0.4},
              note="half of what sweet food brings is fructose, which does not "
                   "go past the regulation point"),
    Intention("more_veg", "more vegetables and pulses",
              {"vegetables": 1.5, "legumes": 1.5}, rest=0.9,
              note="bulk without density; you need a great deal of it"),
    Intention("more_fat", "more fat",
              {"butter": 1.7, "fish": 1.2},
              note="fat is the only fuel that has to be oxidised — there is no "
                   "fermenting your way out of it"),
    Intention("less_fat", "less fat",
              {"butter": 0.4, "red_meat": 0.7, "dairy": 0.75},
              note="carbon has to come from somewhere, and what fills the gap "
                   "is usually starch"),
    Intention("less_drink", "drink less",
              {"drink": 0.35},
              note="ethanol needs no door, so the only lever is how much "
                   "arrives"),
    Intention("eat_less", "eat less of everything",
              {}, rest=0.75,
              note="the one nudge with no substitution in it, and the only "
                   "one that lowers what a lineage has to work with"),
]

BY_ID: dict[str, Intention] = {i.id: i for i in INTENTIONS}

#: What fills a gap when something is taken out of a diet. Convenience food,
#: because that is what is nearest to hand -- and this is where a well-meant
#: nudge goes wrong.
FILLS: tuple[tuple[str, float], ...] = (
    ("sweets", 0.42), ("wholegrain", 0.28), ("processed_meat", 0.18),
    ("dairy", 0.12),
)

#: Everything a run can bring. All of it is printed in the appendix.
EVENTS: list[Event] = [
    Event("night_out", "a night out",
          adds={"drink": 2.6, "processed_meat": 0.9, "sweets": 0.5},
          seconds=50.0,
          tells="Someone's leaving do. Drink and, at one in the morning, "
                "chips — ethanol crosses the membrane on its own, so nothing "
                "on the register keeps it out."),
    Event("heartbreak", "a bad three days",
          adds={"sweets": 2.4, "dairy": 1.2},
          scales={"vegetables": 0.5, "legumes": 0.4, "fish": 0.3},
          seconds=110.0,
          tells="It ended badly. Ice cream, mostly, and not much else, for "
                "what feels like a long time."),
    Event("flu", "a week of flu",
          everything=0.55,
          seconds=80.0,
          tells="Ill, and off food. Less of everything arrives, which is "
                "restful for a lineage that was overfed and hard on one that "
                "was not."),
    Event("deadline", "a fortnight of deadlines",
          adds={"sweets": 1.1, "processed_meat": 0.8},
          scales={"vegetables": 0.6, "legumes": 0.5},
          seconds=90.0,
          tells="No time to cook. Whatever is quickest, for a fortnight."),
    Event("good_stretch", "a good stretch",
          adds={"fish": 1.0, "vegetables": 1.0, "legumes": 0.6},
          scales={"sweets": 0.5, "processed_meat": 0.4, "drink": 0.4},
          seconds=90.0,
          tells="A calm patch, and time to cook properly. It will not last, "
                "and it is worth using."),
]

EVENTS_BY_ID: dict[str, Event] = {e.id: e for e in EVENTS}


def aim(diet: dict[str, float], intention: Intention,
        rng: np.random.Generator) -> tuple[dict[str, float], dict[str, float]]:
    """Try to eat the way you meant to. Returns the new diet and what moved.

    The nudge lands somewhere between half and half again of what was asked
    for, and whatever it takes out is partly replaced by what is nearest to
    hand. The total is held roughly where it was, because a person who eats
    less of one thing eats more of another -- that substitution is the point of
    the mechanic and the reason a sensible-sounding nudge can leave a lineage
    worse off.
    """
    landed = float(rng.uniform(*tuning.INTENTION_LANDS))
    wanted = dict(diet)
    for food, factor in intention.shift.items():
        if food not in wanted and factor > 1.0:
            wanted[food] = tuning.INTENTION_INTRODUCES
        if food in wanted:
            wanted[food] *= 1.0 + (factor - 1.0) * landed
    if intention.rest != 1.0:
        for food in wanted:
            if food not in intention.shift:
                wanted[food] *= 1.0 + (intention.rest - 1.0) * landed

    before = sum(diet.values())
    gap = before - sum(wanted.values())
    if gap > 1e-9 and intention.id != "eat_less":
        share = float(rng.uniform(*tuning.INTENTION_SUBSTITUTES))
        for food, weight in FILLS:
            wanted[food] = wanted.get(food, 0.0) + gap * share * weight

    wanted = {f: round(p, 3) for f, p in wanted.items() if p > 0.02}
    moved = {f: round(wanted.get(f, 0.0) - diet.get(f, 0.0), 3)
             for f in set(wanted) | set(diet)}
    return wanted, {f: d for f, d in moved.items() if abs(d) > 0.02}


def befalls(diet: dict[str, float], event: Event) -> dict[str, float]:
    """The diet as an event leaves it, for as long as the event lasts."""
    out = {f: p * event.everything for f, p in diet.items()}
    for food, factor in event.scales.items():
        if food in out:
            out[food] *= factor
    for food, portions in event.adds.items():
        out[food] = out.get(food, 0.0) + portions
    return {f: round(p, 3) for f, p in out.items() if p > 0.02}


class Life:
    """The run's own schedule of things that happen to it.

    Drawn once, at the start, from the lineage's seed -- so a run is
    reproducible and can be replayed, and so the appendix can be honest that
    the *list* is fixed even though the timing is not.
    """

    def __init__(self, seed: int = 0, length: float | None = None) -> None:
        self.rng = np.random.default_rng(seed ^ 0x11FE)
        self.length = tuning.RUN_LENGTH if length is None else length
        self.schedule = self._draw()
        self.happened: list[tuple[float, Event]] = []
        self.current: Event | None = None
        self.until = 0.0

    def _draw(self) -> list[tuple[float, Event]]:
        """When things happen. Never in the opening stretch, because a run
        that is derailed before the player has read the page is not a run."""
        first = tuning.EVENT_QUIET_OPENING
        room = max(0.0, self.length - first - tuning.EVENT_QUIET_ENDING)
        count = int(tuning.EVENTS_PER_RUN)
        if room <= 0 or count <= 0:
            return []
        picks = self.rng.choice(len(EVENTS), size=count,
                                replace=count > len(EVENTS))
        times = sorted(first + self.rng.uniform(0.0, room, size=count))
        # never two at once: a lineage should meet them one at a time
        spread: list[float] = []
        for t in times:
            if spread and t - spread[-1] < tuning.EVENT_APART:
                t = spread[-1] + tuning.EVENT_APART
            spread.append(min(t, self.length - 20.0))
        return [(t, EVENTS[int(i)]) for t, i in zip(spread, picks)]

    def update(self, elapsed: float) -> Event | None:
        """Advance the clock. Returns an event on the tick it arrives."""
        if self.current is not None and elapsed >= self.until:
            self.current = None
        arrived = None
        for when, event in self.schedule:
            if when <= elapsed and all(w != when for w, _ in self.happened):
                self.happened.append((when, event))
                self.current = event
                self.until = elapsed + event.seconds
                arrived = event
        return arrived

    def left(self, elapsed: float) -> float:
        return max(0.0, self.until - elapsed) if self.current else 0.0

    def coming(self, elapsed: float) -> int:
        return sum(1 for when, _ in self.schedule if when > elapsed)
