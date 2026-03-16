"""
Ma no Kuni - Music Engine

Layered music playback and mixing system. Four layers breathe together:
  - Base layer:    The drone, the earth tone, the heartbeat of the place
  - Melodic layer: The melody that tells you where you are
  - Harmonic layer: The harmony that tells you how it feels
  - Spirit layer:  The otherworld bleeding through in sound

During moments of ma, all layers strip away until only a single
sustained note remains -- and then even that fades, leaving the
silence that is itself the deepest music.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MusicLayer(Enum):
    """The four strata of the soundtrack."""
    BASE = "base"
    MELODIC = "melodic"
    HARMONIC = "harmonic"
    SPIRIT = "spirit"


class TransitionType(Enum):
    """How one piece of music becomes another."""
    CROSSFADE = auto()         # Smooth volume blend
    HARD_CUT = auto()          # Immediate switch (for shock / battle start)
    FADE_TO_SILENCE = auto()   # Current fades out, pause, new fades in
    MA_TRANSITION = auto()     # Gradual strip-down, silence, single note in
    SPIRIT_BLEED = auto()      # Spirit layer creeps in over material music
    MEMORY_WASH = auto()       # Everything blurs into reverb, reforms as new track


class PlaybackState(Enum):
    """Current state of a layer or track."""
    STOPPED = auto()
    PLAYING = auto()
    FADING_IN = auto()
    FADING_OUT = auto()
    SUSTAINING = auto()        # Holding a single note (ma moments)
    PAUSED = auto()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class FadeEnvelope:
    """
    Controls the volume curve of a fade-in or fade-out.
    Uses an exponential curve -- linear fades sound abrupt to the ear.
    """
    start_volume: float = 0.0
    target_volume: float = 1.0
    duration: float = 2.0          # seconds
    elapsed: float = 0.0
    curve_exponent: float = 2.0    # >1 = slow start, fast end; <1 = fast start
    complete: bool = False

    @property
    def current_volume(self) -> float:
        if self.duration <= 0.0:
            return self.target_volume
        t = min(self.elapsed / self.duration, 1.0)
        curved_t = t ** self.curve_exponent
        return self.start_volume + (self.target_volume - self.start_volume) * curved_t

    def update(self, delta: float) -> float:
        """Advance the envelope, return current volume."""
        self.elapsed += delta
        if self.elapsed >= self.duration:
            self.elapsed = self.duration
            self.complete = True
        return self.current_volume


@dataclass
class LayerState:
    """
    Runtime state for a single music layer.
    """
    layer: MusicLayer
    track_id: Optional[str] = None
    volume: float = 0.0
    target_volume: float = 0.0
    max_volume: float = 1.0
    pan: float = 0.0               # -1.0 (left) to 1.0 (right)
    playback_state: PlaybackState = PlaybackState.STOPPED
    fade: Optional[FadeEnvelope] = None
    loop: bool = True
    playback_position: float = 0.0  # seconds into the track
    reverb_send: float = 0.0        # 0.0 = dry, 1.0 = full reverb
    delay_send: float = 0.0
    low_pass_cutoff: float = 20000.0  # Hz -- full spectrum by default
    pitch_shift: float = 0.0          # semitones

    def start_fade(self, target: float, duration: float,
                   curve: float = 2.0) -> None:
        """Begin fading to a target volume."""
        self.fade = FadeEnvelope(
            start_volume=self.volume,
            target_volume=target,
            duration=duration,
            curve_exponent=curve,
        )
        if target > self.volume:
            self.playback_state = PlaybackState.FADING_IN
        else:
            self.playback_state = PlaybackState.FADING_OUT

    def update(self, delta: float) -> None:
        """Advance this layer by *delta* seconds."""
        if self.fade is not None:
            self.volume = self.fade.update(delta)
            if self.fade.complete:
                self.volume = self.fade.target_volume
                if self.volume <= 0.0:
                    self.playback_state = PlaybackState.STOPPED
                else:
                    self.playback_state = PlaybackState.PLAYING
                self.fade = None
        if self.playback_state == PlaybackState.PLAYING:
            self.playback_position += delta


@dataclass
class TrackTransition:
    """
    A pending transition between two tracks (or track states).
    """
    from_track_id: Optional[str]
    to_track_id: str
    transition_type: TransitionType
    duration: float = 2.0          # total transition time in seconds
    elapsed: float = 0.0
    silence_gap: float = 0.0       # for FADE_TO_SILENCE / MA_TRANSITION
    phase: str = "out"             # "out", "gap", "in"
    complete: bool = False

    @property
    def progress(self) -> float:
        total = self.duration + self.silence_gap
        if total <= 0.0:
            return 1.0
        return min(self.elapsed / total, 1.0)


@dataclass
class TrackDefinition:
    """
    Describes a track that the engine can play. Loaded from soundtrack.yaml.
    """
    track_id: str
    name: str
    tempo_bpm: float = 120.0
    key: str = "C"
    time_signature: str = "4/4"
    base_layer_asset: Optional[str] = None
    melodic_layer_asset: Optional[str] = None
    harmonic_layer_asset: Optional[str] = None
    spirit_layer_asset: Optional[str] = None
    base_volume: float = 0.7
    melodic_volume: float = 0.8
    harmonic_volume: float = 0.6
    spirit_volume: float = 0.5
    spirit_permeability_threshold: float = 0.3
    loop: bool = True
    intro_beats: int = 0
    tags: list[str] = field(default_factory=list)


@dataclass
class MaLayerConfig:
    """
    How music behaves during moments of ma (間).

    When ma deepens, layers peel away. At the deepest ma,
    only a single note -- or nothing -- remains.
    """
    strip_order: list[MusicLayer] = field(default_factory=lambda: [
        MusicLayer.HARMONIC,
        MusicLayer.MELODIC,
        MusicLayer.SPIRIT,
        MusicLayer.BASE,
    ])
    sustain_note_midi: int = 62       # D4 -- the tonic of Aoi's theme
    sustain_velocity: int = 30        # Very soft
    sustain_duration: float = 8.0     # Long, breathing note
    silence_between: float = 4.0     # Seconds of silence between sustained notes
    reverb_send: float = 0.9         # Deep reverb on the sustained note
    low_pass_cutoff: float = 2000.0  # Warmth; cut highs


# ---------------------------------------------------------------------------
# Music Engine
# ---------------------------------------------------------------------------

class MusicEngine:
    """
    The heart of Ma no Kuni's adaptive music system.

    Manages four simultaneous layers, crossfades between tracks,
    responds to game state, location, spirit permeability, and time
    of day. During moments of ma, it knows how to fall silent with
    grace.

    Usage
    -----
    >>> engine = MusicEngine()
    >>> engine.load_track(TrackDefinition(track_id="aoi_theme", name="Aoi's Theme"))
    >>> engine.play_track("aoi_theme")
    >>> engine.update(0.016)  # call every frame
    """

    def __init__(self, master_volume: float = 0.8) -> None:
        self.master_volume: float = master_volume
        self.layers: dict[MusicLayer, LayerState] = {
            layer: LayerState(layer=layer) for layer in MusicLayer
        }
        self.tracks: dict[str, TrackDefinition] = {}
        self.current_track_id: Optional[str] = None
        self.pending_transition: Optional[TrackTransition] = None
        self.transition_history: list[str] = []
        self.ma_config: MaLayerConfig = MaLayerConfig()
        self._ma_active: bool = False
        self._ma_depth: float = 0.0
        self._ma_sustain_timer: float = 0.0
        self._ma_phase: str = "silence"  # "silence" or "sustain"
        self._spirit_permeability: float = 0.0
        self._time_of_day: str = "morning"
        self._default_fade_duration: float = 2.0

    # ----- Track management ------------------------------------------------

    def load_track(self, track_def: TrackDefinition) -> None:
        """Register a track definition with the engine."""
        self.tracks[track_def.track_id] = track_def

    def unload_track(self, track_id: str) -> None:
        """Remove a track definition. Stops it first if playing."""
        if self.current_track_id == track_id:
            self.stop_all(fade_duration=0.5)
        self.tracks.pop(track_id, None)

    def get_track(self, track_id: str) -> Optional[TrackDefinition]:
        return self.tracks.get(track_id)

    # ----- Playback --------------------------------------------------------

    def play_track(
        self,
        track_id: str,
        transition: TransitionType = TransitionType.CROSSFADE,
        transition_duration: float = 2.0,
        silence_gap: float = 1.0,
    ) -> None:
        """
        Begin playing a track. If another track is already playing,
        transition according to the specified type.
        """
        if track_id not in self.tracks:
            return
        if track_id == self.current_track_id and not self._ma_active:
            return  # already playing

        if self._ma_active:
            self._exit_ma()

        if self.current_track_id is not None:
            self.pending_transition = TrackTransition(
                from_track_id=self.current_track_id,
                to_track_id=track_id,
                transition_type=transition,
                duration=transition_duration,
                silence_gap=silence_gap if transition in (
                    TransitionType.FADE_TO_SILENCE,
                    TransitionType.MA_TRANSITION,
                ) else 0.0,
            )
            self._begin_transition()
        else:
            self._start_track(track_id)

    def stop_all(self, fade_duration: float = 1.0) -> None:
        """Fade all layers to silence."""
        for layer_state in self.layers.values():
            if layer_state.playback_state != PlaybackState.STOPPED:
                layer_state.start_fade(0.0, fade_duration)
        self.current_track_id = None

    # ----- Layer control ---------------------------------------------------

    def set_layer_volume(self, layer: MusicLayer, volume: float,
                         fade_duration: float = 0.5) -> None:
        """Adjust a layer's volume with a smooth fade."""
        state = self.layers[layer]
        state.target_volume = max(0.0, min(1.0, volume))
        state.start_fade(state.target_volume, fade_duration)

    def set_layer_effect(self, layer: MusicLayer, *,
                         reverb: Optional[float] = None,
                         delay: Optional[float] = None,
                         low_pass: Optional[float] = None,
                         pitch_shift: Optional[float] = None) -> None:
        """Apply DSP effects to a layer."""
        state = self.layers[layer]
        if reverb is not None:
            state.reverb_send = max(0.0, min(1.0, reverb))
        if delay is not None:
            state.delay_send = max(0.0, min(1.0, delay))
        if low_pass is not None:
            state.low_pass_cutoff = max(20.0, min(20000.0, low_pass))
        if pitch_shift is not None:
            state.pitch_shift = max(-24.0, min(24.0, pitch_shift))

    # ----- Spirit permeability ---------------------------------------------

    def set_spirit_permeability(self, value: float) -> None:
        """
        Update the spirit-world permeability (0.0 -- 1.0).
        Controls the spirit layer and adds ethereal effects to other layers.
        """
        self._spirit_permeability = max(0.0, min(1.0, value))
        self._apply_spirit_permeability()

    def _apply_spirit_permeability(self) -> None:
        """Modulate layers based on current spirit permeability."""
        perm = self._spirit_permeability
        spirit = self.layers[MusicLayer.SPIRIT]
        track = self.tracks.get(self.current_track_id or "")

        if track is not None and perm >= track.spirit_permeability_threshold:
            # Fade spirit layer in proportionally
            intensity = (perm - track.spirit_permeability_threshold) / (
                1.0 - track.spirit_permeability_threshold + 1e-9
            )
            target = track.spirit_volume * intensity
            if abs(spirit.volume - target) > 0.01:
                spirit.start_fade(target, 3.0, curve=1.5)
        elif spirit.volume > 0.0:
            spirit.start_fade(0.0, 2.0)

        # Add ethereal effects to other layers at high permeability
        if perm > 0.6:
            bleed = (perm - 0.6) / 0.4  # 0..1 over the 0.6..1.0 range
            for layer in (MusicLayer.MELODIC, MusicLayer.HARMONIC):
                state = self.layers[layer]
                state.reverb_send = min(0.8, state.reverb_send + bleed * 0.3)
                state.low_pass_cutoff = max(
                    3000.0, 20000.0 - bleed * 12000.0
                )

    # ----- Time of day -----------------------------------------------------

    def set_time_of_day(self, time_of_day: str) -> None:
        """
        Adjust layer balance based on the hour. Night music is sparser;
        dawn and dusk have the most layered, liminal sound.
        """
        self._time_of_day = time_of_day
        modifiers = {
            "dawn":      {"base": 0.8, "melodic": 0.6, "harmonic": 0.7, "spirit": 0.4},
            "morning":   {"base": 0.7, "melodic": 0.9, "harmonic": 0.6, "spirit": 0.1},
            "midday":    {"base": 0.6, "melodic": 0.8, "harmonic": 0.5, "spirit": 0.1},
            "afternoon": {"base": 0.7, "melodic": 0.7, "harmonic": 0.6, "spirit": 0.2},
            "dusk":      {"base": 0.9, "melodic": 0.7, "harmonic": 0.8, "spirit": 0.5},
            "evening":   {"base": 0.8, "melodic": 0.5, "harmonic": 0.7, "spirit": 0.6},
            "midnight":  {"base": 0.5, "melodic": 0.3, "harmonic": 0.4, "spirit": 0.8},
            "witching":  {"base": 0.4, "melodic": 0.2, "harmonic": 0.3, "spirit": 0.9},
        }
        mods = modifiers.get(time_of_day, modifiers["morning"])
        for layer_enum in MusicLayer:
            key = layer_enum.value
            if key in mods:
                self.set_layer_volume(layer_enum, mods[key], fade_duration=4.0)

    # ----- Ma (間) ----------------------------------------------------------

    def enter_ma(self, depth: float = 1.0) -> None:
        """
        Enter a moment of ma. Music strips down to almost nothing.

        *depth* controls how far the stripping goes:
            0.0 -- 0.3 : harmonic layer removed
            0.3 -- 0.5 : melodic layer also removed
            0.5 -- 0.8 : spirit layer also removed
            0.8 -- 1.0 : base fades to single sustained note, then silence
        """
        self._ma_active = True
        self._ma_depth = max(0.0, min(1.0, depth))
        self._ma_sustain_timer = 0.0
        self._ma_phase = "sustain"

        thresholds = [0.0, 0.3, 0.5, 0.8]
        for i, layer in enumerate(self.ma_config.strip_order):
            if self._ma_depth >= thresholds[i]:
                fade_time = 2.0 + i * 1.0  # each layer fades slightly slower
                self.layers[layer].start_fade(0.0, fade_time, curve=1.5)

        if self._ma_depth >= 0.8:
            # Prepare the sustained note on the base layer
            base = self.layers[MusicLayer.BASE]
            base.reverb_send = self.ma_config.reverb_send
            base.low_pass_cutoff = self.ma_config.low_pass_cutoff
            base.playback_state = PlaybackState.SUSTAINING

    def _exit_ma(self) -> None:
        """Return from ma to normal music."""
        self._ma_active = False
        self._ma_depth = 0.0

    def _update_ma(self, delta: float) -> None:
        """Advance the ma music state -- sustained note / silence cycle."""
        if self._ma_depth < 0.8:
            return  # lighter ma levels just remove layers; no sustain logic

        self._ma_sustain_timer += delta
        base = self.layers[MusicLayer.BASE]

        if self._ma_phase == "sustain":
            if self._ma_sustain_timer >= self.ma_config.sustain_duration:
                # Fade the sustained note out
                base.start_fade(0.0, 2.0, curve=1.5)
                self._ma_phase = "silence"
                self._ma_sustain_timer = 0.0
            else:
                # Gentle swell curve on the sustained note
                progress = self._ma_sustain_timer / self.ma_config.sustain_duration
                swell = math.sin(progress * math.pi) * 0.25
                base.volume = max(0.0, min(1.0, 0.1 + swell))

        elif self._ma_phase == "silence":
            if self._ma_sustain_timer >= self.ma_config.silence_between:
                # Begin the next sustained note
                base.start_fade(0.15, 3.0, curve=0.5)
                base.playback_state = PlaybackState.SUSTAINING
                self._ma_phase = "sustain"
                self._ma_sustain_timer = 0.0

    # ----- Transitions -----------------------------------------------------

    def _begin_transition(self) -> None:
        """Kick off the outgoing phase of a track transition."""
        trans = self.pending_transition
        if trans is None:
            return

        if trans.transition_type == TransitionType.HARD_CUT:
            self._hard_cut(trans.to_track_id)
            trans.complete = True
            return

        # For all other types, fade out current layers
        fade_out = trans.duration / 2.0
        for layer_state in self.layers.values():
            if layer_state.playback_state != PlaybackState.STOPPED:
                if trans.transition_type == TransitionType.MEMORY_WASH:
                    layer_state.reverb_send = 1.0
                    layer_state.low_pass_cutoff = 1500.0
                layer_state.start_fade(0.0, fade_out, curve=1.8)
        trans.phase = "out"

    def _advance_transition(self, delta: float) -> None:
        """Tick the transition state machine."""
        trans = self.pending_transition
        if trans is None or trans.complete:
            return

        trans.elapsed += delta

        if trans.phase == "out":
            # Check if all layers have finished fading out
            all_done = all(
                ls.fade is None or ls.fade.complete
                for ls in self.layers.values()
            )
            if all_done:
                if trans.silence_gap > 0.0:
                    trans.phase = "gap"
                    trans.elapsed = 0.0
                else:
                    self._finish_transition()

        elif trans.phase == "gap":
            if trans.elapsed >= trans.silence_gap:
                self._finish_transition()

    def _finish_transition(self) -> None:
        """Complete a transition by starting the new track."""
        trans = self.pending_transition
        if trans is None:
            return
        self.transition_history.append(
            f"{trans.from_track_id}->{trans.to_track_id}"
        )
        self._start_track(trans.to_track_id)
        trans.complete = True
        self.pending_transition = None

    def _hard_cut(self, track_id: str) -> None:
        """Immediately switch to a new track with no fade."""
        for layer_state in self.layers.values():
            layer_state.volume = 0.0
            layer_state.playback_state = PlaybackState.STOPPED
            layer_state.fade = None
        self._start_track(track_id)

    def _start_track(self, track_id: str) -> None:
        """Initialize layers for a new track and fade them in."""
        track = self.tracks.get(track_id)
        if track is None:
            return

        self.current_track_id = track_id

        layer_assets = {
            MusicLayer.BASE: (track.base_layer_asset, track.base_volume),
            MusicLayer.MELODIC: (track.melodic_layer_asset, track.melodic_volume),
            MusicLayer.HARMONIC: (track.harmonic_layer_asset, track.harmonic_volume),
            MusicLayer.SPIRIT: (track.spirit_layer_asset, track.spirit_volume),
        }

        for layer_enum, (asset, vol) in layer_assets.items():
            state = self.layers[layer_enum]
            state.track_id = asset
            state.playback_position = 0.0
            state.loop = track.loop
            state.reverb_send = 0.0
            state.delay_send = 0.0
            state.low_pass_cutoff = 20000.0
            state.pitch_shift = 0.0
            state.pan = 0.0

            if asset is not None:
                target_vol = vol
                # Spirit layer starts silent unless permeability is high
                if layer_enum == MusicLayer.SPIRIT:
                    if self._spirit_permeability < track.spirit_permeability_threshold:
                        target_vol = 0.0
                state.start_fade(target_vol, self._default_fade_duration)
                state.playback_state = PlaybackState.FADING_IN
            else:
                state.volume = 0.0
                state.playback_state = PlaybackState.STOPPED

    # ----- Main update -----------------------------------------------------

    def update(self, delta: float) -> None:
        """
        Advance the music engine by *delta* seconds.
        Call once per frame.
        """
        # Advance any pending transition
        if self.pending_transition is not None and not self.pending_transition.complete:
            self._advance_transition(delta)

        # Ma logic
        if self._ma_active:
            self._update_ma(delta)

        # Advance every layer's fade / position
        for layer_state in self.layers.values():
            layer_state.update(delta)

    # ----- Queries ---------------------------------------------------------

    def get_layer_volumes(self) -> dict[str, float]:
        """Return current effective volumes for all layers."""
        return {
            layer.value: state.volume * self.master_volume
            for layer, state in self.layers.items()
        }

    def is_playing(self) -> bool:
        return any(
            s.playback_state not in (PlaybackState.STOPPED, PlaybackState.PAUSED)
            for s in self.layers.values()
        )

    def is_transitioning(self) -> bool:
        return (
            self.pending_transition is not None
            and not self.pending_transition.complete
        )

    def is_in_ma(self) -> bool:
        return self._ma_active

    def get_state_snapshot(self) -> dict:
        """Full diagnostic snapshot for debugging / UI."""
        return {
            "master_volume": self.master_volume,
            "current_track": self.current_track_id,
            "ma_active": self._ma_active,
            "ma_depth": self._ma_depth,
            "spirit_permeability": self._spirit_permeability,
            "time_of_day": self._time_of_day,
            "transitioning": self.is_transitioning(),
            "layers": {
                layer.value: {
                    "volume": state.volume,
                    "state": state.playback_state.name,
                    "position": round(state.playback_position, 2),
                    "reverb": state.reverb_send,
                    "low_pass": state.low_pass_cutoff,
                }
                for layer, state in self.layers.items()
            },
        }
