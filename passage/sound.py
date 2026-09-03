"""Procedural audio. Four sounds, no music, nothing else.

The art direction is blunt about which of these matters: the continuous hum is
**the most useful instrument in the game**, because its pitch tracks total
throughput and a player learns to *hear* the factory slow down before they see
it. Everything else here is punctuation.

* **Hum** -- low, continuous, pitch following throughput. Never stops while the
  lineage lives.
* **Pen scratch** -- on placing a mark. It should sound like writing.
* **Wet tick** -- on division.
* **Sour tone** -- on spillover, in the same register as the alarm colour, and
  used for nothing else, exactly as the colour is.

Everything is synthesised into numpy at startup. Nothing is loaded from disk,
because the whole game is one .ttf and two libraries.

The hum cannot be re-synthesised every time the throughput moves -- that would
allocate and click. Instead a bank of seamless loops is built once, one per
pitch step, and the mixer crossfades between adjacent steps on two channels.
Each loop holds a whole number of cycles, so it repeats without a seam.

If there is no audio device -- a headless box, a container, a machine with the
mixer taken -- every call here becomes a no-op and the game runs silently. Audio
is never allowed to be the reason the game will not start.
"""

from __future__ import annotations

import math

import numpy as np

RATE = 44_100
BITS = -16

#: The hum's range, in hertz. Low enough to sit under everything, wide enough
#: that the ear reads a change of a step or two without being told to listen.
HUM_LOW = 52.0
HUM_HIGH = 156.0
HUM_STEPS = 24
HUM_GAIN = 0.30
CROSSFADE = 0.22            # seconds to slide between two pitch steps

#: Throughput that counts as the factory running flat out. Above this the hum
#: is simply at the top of its range.
REFERENCE_THROUGHPUT = 12.0


def _envelope(n: int, attack: float, decay: float) -> np.ndarray:
    a = max(1, int(n * attack))
    d = max(1, n - a)
    return np.concatenate([np.linspace(0.0, 1.0, a) ** 0.5,
                           np.exp(-np.linspace(0.0, 1.0, d) * decay)])


def _soften(wave: np.ndarray, width: int) -> np.ndarray:
    """A cheap low-pass. Everything in this game is warm and none of it is bright."""
    if width < 2:
        return wave
    kernel = np.ones(width) / width
    return np.convolve(wave, kernel, mode="same")


def _to_int16(wave: np.ndarray) -> np.ndarray:
    return (np.clip(wave, -1.0, 1.0) * 32767).astype(np.int16)


def hum_loop(freq: float, seed: int = 0) -> np.ndarray:
    """One seamless cycle-aligned loop of the hum, at the given pitch.

    A plain sine reads as a test tone. What makes this sound like a room with
    something running in it is the pair of slightly detuned fundamentals beating
    against each other, and a little breath of noise under them.
    """
    cycles = max(8, int(round(freq * 0.55)))
    n = int(round(RATE * cycles / freq))

    # Phase is counted in whole cycles across exactly n samples, not derived
    # from a rounded duration. Rounding the length instead leaves the loop a
    # fraction of a cycle short, and that fraction is an audible click on every
    # repeat -- once a second, for the whole game.
    turn = 2 * np.pi * np.arange(n) / n
    wave = (1.00 * np.sin(cycles * turn)
            + 0.42 * np.sin(2 * cycles * turn + 0.6)
            + 0.17 * np.sin(3 * cycles * turn + 1.1)
            + 0.30 * np.sin((cycles + 1) * turn))       # a slow beat against it
    wave = np.tanh(wave * 0.85) / 1.2

    wave = wave * 0.94 + _periodic_breath(n, seed) * 0.06
    return wave / (np.abs(wave).max() or 1.0)


def _periodic_breath(n: int, seed: int) -> np.ndarray:
    """Low-passed noise that is periodic over exactly n samples.

    Built in the frequency domain and kept to whole bins, so it wraps cleanly.
    Filtering ordinary noise in the time domain would not: the two ends would
    not meet, and the seam would click.
    """
    rng = np.random.default_rng(seed)
    spectrum = rng.normal(0, 1, n // 2 + 1) + 1j * rng.normal(0, 1, n // 2 + 1)
    bins = np.arange(len(spectrum))
    spectrum *= np.exp(-bins / 40.0)                     # a soft low pass
    spectrum[0] = 0.0                                    # no DC offset
    breath = np.fft.irfft(spectrum, n)
    return breath / (np.abs(breath).max() or 1.0)


def pen_scratch(seed: int = 0) -> np.ndarray:
    """A nib on paper: filtered noise, a couple of catches, gone in a moment."""
    n = int(RATE * 0.26)
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, 1, n)
    body = _soften(noise, 9) - _soften(noise, 60)        # a band, not a hiss
    drag = 1.0 + 0.5 * np.sin(np.linspace(0, 11.0, n))   # the nib catching
    wave = body * drag * _envelope(n, 0.06, 5.0)
    return wave / (np.abs(wave).max() or 1.0) * 0.55


def wet_tick(seed: int = 0) -> np.ndarray:
    """Division: a soft click with the pitch falling away. Wet, not clicky."""
    n = int(RATE * 0.16)
    t = np.arange(n) / RATE
    freq = 320.0 * np.exp(-t * 16.0) + 90.0
    wave = np.sin(2 * np.pi * np.cumsum(freq) / RATE)
    rng = np.random.default_rng(seed)
    wave = wave * 0.85 + _soften(rng.normal(0, 1, n), 40) * 0.15
    wave = _soften(wave, 5) * _envelope(n, 0.02, 7.0)
    return wave / (np.abs(wave).max() or 1.0) * 0.5


def sour_tone(seed: int = 0) -> np.ndarray:
    """Spillover: two pitches a tritone apart, deliberately unpleasant.

    In the same register as the hum, so it sounds like the factory going wrong
    rather than like a notification arriving from somewhere else.
    """
    n = int(RATE * 0.7)
    t = np.arange(n) / RATE
    low = 96.0
    wave = (np.sin(2 * np.pi * low * t)
            + 0.9 * np.sin(2 * np.pi * low * 1.414 * t)     # the tritone
            + 0.4 * np.sin(2 * np.pi * low * 2.02 * t))     # and a sour octave
    wave = _soften(wave, 4) * _envelope(n, 0.10, 3.2)
    return wave / (np.abs(wave).max() or 1.0) * 0.42


class Sound:
    """The mixer, the pitch bank, and the crossfade. Silent if there is no device."""

    def __init__(self, enabled: bool = True) -> None:
        self.ok = False
        self.pitch = 0.0
        self._step = -1
        self._slot = 0
        self._blend = 1.0
        self._since_sour = 99.0
        if not enabled:
            return
        try:
            import pygame

            pygame.mixer.pre_init(RATE, BITS, 1, 512)
            pygame.mixer.init(RATE, BITS, 1, 512)
            pygame.mixer.set_num_channels(8)
            self._pygame = pygame
            self._bank = [pygame.sndarray.make_sound(_to_int16(hum_loop(f, i)))
                          for i, f in enumerate(self._pitches())]
            self._scratch = pygame.sndarray.make_sound(_to_int16(pen_scratch(1)))
            self._tick = pygame.sndarray.make_sound(_to_int16(wet_tick(2)))
            self._sour = pygame.sndarray.make_sound(_to_int16(sour_tone(3)))
            self._channels = [pygame.mixer.Channel(0), pygame.mixer.Channel(1)]
            self._voice = pygame.mixer.Channel(2)
            self.ok = True
        except Exception:
            # No device, no mixer, no audio. The game still runs.
            self.ok = False

    @staticmethod
    def _pitches() -> list[float]:
        """Geometric, because pitch is heard in ratios and not in hertz."""
        return [HUM_LOW * (HUM_HIGH / HUM_LOW) ** (i / (HUM_STEPS - 1))
                for i in range(HUM_STEPS)]

    # -- the hum ----------------------------------------------------------
    def set_throughput(self, throughput: float) -> None:
        """Move the hum to match how much the factory is doing.

        Compressed, so that the difference between a stalled cell and a slow one
        is audible rather than lost at the bottom of the range.
        """
        share = min(1.0, max(0.0, throughput / REFERENCE_THROUGHPUT)) ** 0.6
        step = int(round(share * (HUM_STEPS - 1)))
        self.pitch = self._pitches()[step] if self.ok else 0.0
        if not self.ok or step == self._step:
            return
        self._slot ^= 1
        self._blend = 0.0
        self._step = step
        self._channels[self._slot].play(self._bank[step], loops=-1)
        self._channels[self._slot].set_volume(0.0)

    def update(self, dt: float) -> None:
        """Slide the crossfade along. Called once a frame."""
        self._since_sour += dt
        if not self.ok or self._step < 0:
            return
        self._blend = min(1.0, self._blend + dt / CROSSFADE)
        self._channels[self._slot].set_volume(HUM_GAIN * self._blend)
        self._channels[self._slot ^ 1].set_volume(HUM_GAIN * (1.0 - self._blend))
        if self._blend >= 1.0:
            self._channels[self._slot ^ 1].stop()

    # -- punctuation -------------------------------------------------------
    def scratch(self) -> None:
        """A mark being placed. It should feel like writing."""
        if self.ok:
            self._voice.play(self._scratch)

    def tick(self) -> None:
        if self.ok:
            self._voice.play(self._tick)

    def sour(self) -> None:
        """Spillover. Rate-limited, or a badly-run cell becomes a car alarm."""
        if self.ok and self._since_sour > 1.6:
            self._since_sour = 0.0
            self._voice.play(self._sour)

    def close(self) -> None:
        if self.ok:
            self._pygame.mixer.quit()
            self.ok = False
