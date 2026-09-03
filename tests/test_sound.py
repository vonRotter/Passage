"""Procedural audio: four sounds, no music, and never a reason not to start.

The hum is the one that matters. Its pitch tracks total throughput, and a
player is meant to hear the factory slow before they see it, so what is
asserted here is that the pitch actually moves with throughput and that the
loops repeat without a click.
"""

import numpy as np
import pytest

from passage import sound
from passage.__main__ import build


@pytest.mark.parametrize("freq", [52.0, 72.0, 96.0, 130.0, 156.0])
def test_hum_loops_have_no_seam(freq):
    """A loop that is a fraction of a cycle short clicks on every repeat --
    once a second, for the whole game."""
    wave = sound.hum_loop(freq, seed=0)
    seam = abs(wave[0] - wave[-1])
    biggest_normal_step = float(np.abs(np.diff(wave)).max())
    assert seam <= biggest_normal_step, (
        f"{freq} Hz wraps with a {seam:.4f} step, larger than any step inside "
        f"the waveform ({biggest_normal_step:.4f})")


def test_every_sound_is_bounded_and_finite():
    for name, wave in [("hum", sound.hum_loop(96.0)),
                       ("scratch", sound.pen_scratch()),
                       ("tick", sound.wet_tick()),
                       ("sour", sound.sour_tone())]:
        assert np.isfinite(wave).all(), name
        assert np.abs(wave).max() <= 1.0, name
        assert np.abs(wave).max() > 0.1, f"{name} is silent"


def test_one_shots_start_and_end_near_silence():
    """A one-shot that begins or ends on a non-zero sample clicks."""
    for name, wave in [("scratch", sound.pen_scratch()),
                       ("tick", sound.wet_tick()),
                       ("sour", sound.sour_tone())]:
        assert abs(wave[0]) < 0.05, name
        assert abs(wave[-1]) < 0.05, name


def test_the_pitch_bank_rises_and_is_geometric():
    """Pitch is heard in ratios, not in hertz, so the bank is geometric."""
    pitches = sound.Sound._pitches()
    assert len(pitches) == sound.HUM_STEPS
    assert pitches[0] == pytest.approx(sound.HUM_LOW)
    assert pitches[-1] == pytest.approx(sound.HUM_HIGH)
    ratios = [b / a for a, b in zip(pitches, pitches[1:])]
    assert max(ratios) - min(ratios) < 1e-9


def test_the_hum_tracks_throughput():
    """The whole point of the instrument.

    Throughput is total internal traffic, so a fermenter -- which runs a short
    pathway hard and has switched the rest of the plate off -- sits *below* a
    respiring cell even though it eats far more glucose. That is the honest
    reading of "how much is happening", and it is what a player should hear.
    """
    def settled(profile):
        flow, _, _ = build(profile, seed=0)
        for _ in range(6_000):
            flow.step()
        return flow.throughput()

    working, narrow, dead = (settled("growing"), settled("fermenting"),
                             settled("starved"))
    assert working > narrow > dead
    silent = sound.Sound(enabled=False)
    pitches = []
    for value in (dead, narrow, working):
        silent.ok = True                       # exercise the mapping, not the mixer
        share = min(1.0, max(0.0, value / sound.REFERENCE_THROUGHPUT)) ** 0.6
        pitches.append(sound.Sound._pitches()[
            int(round(share * (sound.HUM_STEPS - 1)))])
    assert pitches[0] < pitches[1] < pitches[2]


def test_upkeep_is_left_out_of_throughput():
    """Upkeep runs whether or not the factory works. Counting it would put a
    floor under the hum that hides the stall a player should hear coming."""
    flow, _, _ = build("starved", seed=0)
    for _ in range(6_000):
        flow.step()
    assert flow.rate_of("maintenance") >= 0.0
    assert flow.throughput() < 0.5, "a dead cell must be near-silent"


def test_no_audio_device_is_not_an_error():
    """Audio is never allowed to be the reason the game will not start."""
    silent = sound.Sound(enabled=False)
    assert silent.ok is False
    silent.set_throughput(5.0)
    silent.update(1 / 60)
    silent.scratch()
    silent.tick()
    silent.sour()
    silent.close()
