"""
Ma no Kuni - Procedural Music Composition

Generates and transforms musical phrases in real-time. Motifs, chord
progressions, and melodic fragments are defined as data and recombined
dynamically based on game context.

Two musical traditions are woven together:
  - Japanese scales (Hirajoshi, In, Yo, Miyako-bushi) for the spirit world
  - Western orchestral harmony for the material world

When the worlds bleed together, so do the scales.

MIDI note reference:
  C4 = 60, D4 = 62, E4 = 64, F4 = 65, G4 = 67, A4 = 69, B4 = 71
"""

from __future__ import annotations

import copy
import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


# ---------------------------------------------------------------------------
# Musical constants
# ---------------------------------------------------------------------------

# Standard MIDI note names
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Scale intervals (semitones from root)
SCALES: dict[str, list[int]] = {
    # Western
    "major":             [0, 2, 4, 5, 7, 9, 11],
    "natural_minor":     [0, 2, 3, 5, 7, 8, 10],
    "harmonic_minor":    [0, 2, 3, 5, 7, 8, 11],
    "melodic_minor_asc": [0, 2, 3, 5, 7, 9, 11],
    "dorian":            [0, 2, 3, 5, 7, 9, 10],
    "mixolydian":        [0, 2, 4, 5, 7, 9, 10],
    "phrygian":          [0, 1, 3, 5, 7, 8, 10],
    "lydian":            [0, 2, 4, 6, 7, 9, 11],
    "whole_tone":        [0, 2, 4, 6, 8, 10],
    # Japanese
    "hirajoshi":         [0, 2, 3, 7, 8],         # Contemplative, otherworldly
    "in_scale":          [0, 1, 5, 7, 8],          # Dark, mysterious (Miyako-bushi)
    "yo_scale":          [0, 2, 5, 7, 9],          # Bright, folk-like
    "iwato":             [0, 1, 5, 6, 10],         # Brooding, temple bells
    "kumoi":             [0, 2, 3, 7, 9],          # Melancholy, noble
    "ryukyu":            [0, 4, 5, 7, 11],         # Okinawan, warm
    # Spirit-world blends
    "spirit_minor":      [0, 1, 3, 5, 7, 8, 11],  # Phrygian + raised 7th
    "veil_scale":        [0, 2, 3, 6, 7, 8, 11],  # Invented: liminal, unstable
    "ma_scale":          [0, 7],                    # Just the root and fifth -- space
}


class Instrument(Enum):
    """The voices of both worlds."""
    # Japanese traditional
    SHAKUHACHI = "shakuhachi"
    KOTO = "koto"
    SHAMISEN = "shamisen"
    TAIKO = "taiko"
    BIWA = "biwa"
    SHINOBUE = "shinobue"
    SUZU_BELLS = "suzu_bells"
    SHO = "sho"                   # Mouth organ -- ethereal sustained chords
    # Western orchestral
    FLUTE = "flute"
    OBOE = "oboe"
    CLARINET = "clarinet"
    VIOLIN = "violin"
    VIOLA = "viola"
    CELLO = "cello"
    CONTRABASS = "contrabass"
    PIANO = "piano"
    HARP = "harp"
    FRENCH_HORN = "french_horn"
    TIMPANI = "timpani"
    CELESTA = "celesta"
    # Modern / Ambient
    SYNTH_PAD = "synth_pad"
    MUSIC_BOX = "music_box"
    GLASS_HARMONICA = "glass_harmonica"
    # Special
    SILENCE = "silence"            # The most important instrument


class ArticulationType(Enum):
    """How a note speaks."""
    NORMAL = auto()
    LEGATO = auto()
    STACCATO = auto()
    TREMOLO = auto()
    PIZZICATO = auto()
    HARMONICS = auto()
    BEND = auto()
    GHOST = auto()       # Barely audible -- heard more with feeling than ears
    BREATH = auto()      # Shakuhachi breath tones


# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------

@dataclass
class Note:
    """
    A single musical event.

    Attributes
    ----------
    pitch : int
        MIDI note number (0 -- 127). -1 represents a rest.
    duration : float
        Length in beats (1.0 = quarter note at the current tempo).
    velocity : int
        MIDI velocity (0 -- 127). Loudness / intensity.
    instrument : Instrument
        Which voice plays this note.
    articulation : ArticulationType
        How the note is performed.
    """
    pitch: int = 60
    duration: float = 1.0
    velocity: int = 80
    instrument: Instrument = Instrument.PIANO
    articulation: ArticulationType = ArticulationType.NORMAL

    @property
    def is_rest(self) -> bool:
        return self.pitch < 0

    @staticmethod
    def rest(duration: float = 1.0) -> Note:
        """Create a rest (silence) of the given duration."""
        return Note(pitch=-1, duration=duration, velocity=0,
                    instrument=Instrument.SILENCE)

    def transpose(self, semitones: int) -> Note:
        """Return a copy transposed by the given interval."""
        if self.is_rest:
            return copy.copy(self)
        transposed = copy.copy(self)
        transposed.pitch = max(0, min(127, self.pitch + semitones))
        return transposed

    def with_velocity(self, velocity: int) -> Note:
        n = copy.copy(self)
        n.velocity = max(0, min(127, velocity))
        return n


@dataclass
class Phrase:
    """
    A short musical phrase -- a sequence of notes that form a gestural unit.
    The building block of motifs and melodies.
    """
    phrase_id: str
    notes: list[Note] = field(default_factory=list)
    name: str = ""
    tags: list[str] = field(default_factory=list)

    @property
    def total_duration(self) -> float:
        return sum(n.duration for n in self.notes)

    @property
    def note_count(self) -> int:
        return sum(1 for n in self.notes if not n.is_rest)

    def transpose(self, semitones: int) -> Phrase:
        """Return a transposed copy of the entire phrase."""
        return Phrase(
            phrase_id=f"{self.phrase_id}_t{semitones:+d}",
            notes=[n.transpose(semitones) for n in self.notes],
            name=self.name,
            tags=list(self.tags),
        )

    def with_instrument(self, instrument: Instrument) -> Phrase:
        """Return a copy with all notes assigned to a different instrument."""
        new_notes = []
        for n in self.notes:
            nc = copy.copy(n)
            if not nc.is_rest:
                nc.instrument = instrument
            new_notes.append(nc)
        return Phrase(
            phrase_id=f"{self.phrase_id}_{instrument.value}",
            notes=new_notes,
            name=self.name,
            tags=list(self.tags),
        )

    def augment(self, factor: float = 2.0) -> Phrase:
        """Return a copy with note durations multiplied (augmentation)."""
        new_notes = [copy.copy(n) for n in self.notes]
        for n in new_notes:
            n.duration *= factor
        return Phrase(
            phrase_id=f"{self.phrase_id}_aug",
            notes=new_notes,
            name=self.name,
            tags=list(self.tags),
        )

    def diminish(self, factor: float = 0.5) -> Phrase:
        """Return a copy with note durations halved (diminution)."""
        return self.augment(factor)

    def retrograde(self) -> Phrase:
        """Return the phrase in reverse order."""
        return Phrase(
            phrase_id=f"{self.phrase_id}_ret",
            notes=list(reversed(self.notes)),
            name=self.name,
            tags=list(self.tags),
        )

    def invert(self, axis_pitch: int = 60) -> Phrase:
        """Melodic inversion around an axis pitch."""
        new_notes = []
        for n in self.notes:
            if n.is_rest:
                new_notes.append(copy.copy(n))
            else:
                interval = n.pitch - axis_pitch
                nc = copy.copy(n)
                nc.pitch = max(0, min(127, axis_pitch - interval))
                new_notes.append(nc)
        return Phrase(
            phrase_id=f"{self.phrase_id}_inv",
            notes=new_notes,
            name=self.name,
            tags=list(self.tags),
        )


@dataclass
class ChordVoicing:
    """
    A chord expressed as a set of simultaneous MIDI pitches.
    """
    name: str
    pitches: list[int]
    duration: float = 4.0       # beats
    velocity: int = 60
    instrument: Instrument = Instrument.PIANO

    def as_notes(self) -> list[Note]:
        """Expand into individual Note objects (for polyphonic playback)."""
        return [
            Note(pitch=p, duration=self.duration, velocity=self.velocity,
                 instrument=self.instrument)
            for p in self.pitches
        ]


@dataclass
class ChordProgression:
    """An ordered sequence of chords with an associated key and scale."""
    progression_id: str
    key_root: int = 60           # MIDI note of the key root
    scale: str = "natural_minor"
    chords: list[ChordVoicing] = field(default_factory=list)
    name: str = ""
    tags: list[str] = field(default_factory=list)

    @property
    def total_duration(self) -> float:
        return sum(c.duration for c in self.chords)


@dataclass
class Motif:
    """
    A thematic musical idea that can be developed throughout the game.
    Consists of one or more phrases plus a harmonic context.

    A motif is the seed of a character theme, a place, or an idea.
    """
    motif_id: str
    name: str
    phrases: list[Phrase] = field(default_factory=list)
    chord_progression: Optional[ChordProgression] = None
    key_root: int = 62           # D4 by default (Aoi's key)
    scale: str = "natural_minor"
    tempo_bpm: float = 72.0
    time_signature: str = "4/4"
    primary_instrument: Instrument = Instrument.FLUTE
    tags: list[str] = field(default_factory=list)
    development_level: int = 0   # How much the motif has grown in-game

    def get_primary_phrase(self) -> Optional[Phrase]:
        return self.phrases[0] if self.phrases else None

    def transpose_to_key(self, new_root: int) -> Motif:
        """Return a copy transposed to a new key."""
        interval = new_root - self.key_root
        new_phrases = [p.transpose(interval) for p in self.phrases]
        new_prog = None
        if self.chord_progression is not None:
            new_chords = []
            for c in self.chord_progression.chords:
                nc = copy.copy(c)
                nc.pitches = [p + interval for p in c.pitches]
                new_chords.append(nc)
            new_prog = ChordProgression(
                progression_id=f"{self.chord_progression.progression_id}_t{interval:+d}",
                key_root=new_root,
                scale=self.chord_progression.scale,
                chords=new_chords,
                name=self.chord_progression.name,
                tags=self.chord_progression.tags,
            )
        return Motif(
            motif_id=f"{self.motif_id}_t{interval:+d}",
            name=self.name,
            phrases=new_phrases,
            chord_progression=new_prog,
            key_root=new_root,
            scale=self.scale,
            tempo_bpm=self.tempo_bpm,
            time_signature=self.time_signature,
            primary_instrument=self.primary_instrument,
            tags=list(self.tags),
            development_level=self.development_level,
        )


# ---------------------------------------------------------------------------
# Scale utilities
# ---------------------------------------------------------------------------

def get_scale_pitches(root: int, scale_name: str,
                      octave_range: int = 2) -> list[int]:
    """
    Generate all pitches for a scale across multiple octaves.

    Parameters
    ----------
    root : int
        MIDI note number of the root.
    scale_name : str
        Key into the SCALES dict.
    octave_range : int
        How many octaves above the root to generate.
    """
    intervals = SCALES.get(scale_name, SCALES["natural_minor"])
    pitches = []
    for octave in range(octave_range + 1):
        for interval in intervals:
            p = root + octave * 12 + interval
            if 0 <= p <= 127:
                pitches.append(p)
    return pitches


def snap_to_scale(pitch: int, scale_pitches: list[int]) -> int:
    """Snap a MIDI pitch to the nearest note in the given scale."""
    if not scale_pitches:
        return pitch
    return min(scale_pitches, key=lambda p: abs(p - pitch))


def note_name(midi_note: int) -> str:
    """Convert a MIDI note number to a human-readable name (e.g. 'D4')."""
    octave = (midi_note // 12) - 1
    name = NOTE_NAMES[midi_note % 12]
    return f"{name}{octave}"


def name_to_midi(name: str) -> int:
    """Convert a note name like 'D4' to a MIDI number."""
    # Handle sharps and flats
    if len(name) >= 3 and name[1] in ("#", "b"):
        note_part = name[:2]
        octave = int(name[2:])
    else:
        note_part = name[0]
        octave = int(name[1:])

    if note_part.endswith("b"):
        base = note_part[0]
        idx = NOTE_NAMES.index(base) - 1
        if idx < 0:
            idx = 11
    else:
        idx = NOTE_NAMES.index(note_part)

    return (octave + 1) * 12 + idx


# ---------------------------------------------------------------------------
# Composition engine
# ---------------------------------------------------------------------------

class Composer:
    """
    Procedural music composition engine for Ma no Kuni.

    Stores a library of motifs, phrases, and chord progressions, then
    combines and transforms them based on game context to produce
    continuous, adaptive musical output.

    The composer operates at a higher level than the MusicEngine:
    it decides *what* to play, while the engine handles *how* to play it.
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        self.motifs: dict[str, Motif] = {}
        self.phrases: dict[str, Phrase] = {}
        self.progressions: dict[str, ChordProgression] = {}
        self._rng = random.Random(seed)
        self._current_motif_id: Optional[str] = None
        self._current_phrase_index: int = 0
        self._beat_position: float = 0.0
        self._tempo_bpm: float = 72.0
        self._spirit_blend: float = 0.0   # 0.0 = material, 1.0 = spirit scales

    # ----- Library management ----------------------------------------------

    def register_motif(self, motif: Motif) -> None:
        self.motifs[motif.motif_id] = motif
        for phrase in motif.phrases:
            self.phrases[phrase.phrase_id] = phrase
        if motif.chord_progression is not None:
            self.progressions[motif.chord_progression.progression_id] = (
                motif.chord_progression
            )

    def register_phrase(self, phrase: Phrase) -> None:
        self.phrases[phrase.phrase_id] = phrase

    def register_progression(self, prog: ChordProgression) -> None:
        self.progressions[prog.progression_id] = prog

    def get_motif(self, motif_id: str) -> Optional[Motif]:
        return self.motifs.get(motif_id)

    def get_motifs_by_tag(self, tag: str) -> list[Motif]:
        return [m for m in self.motifs.values() if tag in m.tags]

    # ----- Scale blending --------------------------------------------------

    def set_spirit_blend(self, blend: float) -> None:
        """
        Set the material/spirit scale blend.
        0.0 = pure Western harmony, 1.0 = pure Japanese scales.
        """
        self._spirit_blend = max(0.0, min(1.0, blend))

    def get_blended_scale(self, western_scale: str,
                          japanese_scale: str) -> list[int]:
        """
        Create a hybrid scale by interpolating between two scale systems.
        At blend=0, uses only Western intervals. At blend=1, only Japanese.
        In between, pitches are drawn from both with probability weighting.
        """
        w_intervals = set(SCALES.get(western_scale, SCALES["natural_minor"]))
        j_intervals = set(SCALES.get(japanese_scale, SCALES["hirajoshi"]))

        if self._spirit_blend <= 0.0:
            return sorted(w_intervals)
        if self._spirit_blend >= 1.0:
            return sorted(j_intervals)

        # Include intervals from both scales, weighted by blend
        combined: set[int] = set()
        for interval in w_intervals:
            if self._rng.random() > self._spirit_blend * 0.7:
                combined.add(interval)
        for interval in j_intervals:
            if self._rng.random() < self._spirit_blend * 0.7 + 0.3:
                combined.add(interval)

        # Always include root and fifth for stability
        combined.add(0)
        if 7 not in combined:
            combined.add(7)

        return sorted(combined)

    # ----- Phrase generation -----------------------------------------------

    def generate_variation(self, phrase: Phrase,
                           variation_amount: float = 0.3) -> Phrase:
        """
        Create a variation of a phrase by applying controlled randomness.

        Parameters
        ----------
        phrase : Phrase
            The source phrase.
        variation_amount : float
            0.0 = exact copy, 1.0 = heavily altered.
        """
        new_notes: list[Note] = []
        for note in phrase.notes:
            n = copy.copy(note)
            if n.is_rest:
                # Sometimes shorten or lengthen rests
                if self._rng.random() < variation_amount * 0.3:
                    n.duration *= self._rng.uniform(0.5, 1.5)
                new_notes.append(n)
                continue

            # Pitch variation: step-wise motion, staying close
            if self._rng.random() < variation_amount:
                step = self._rng.choice([-2, -1, 1, 2])
                n.pitch = max(0, min(127, n.pitch + step))

            # Velocity variation: subtle dynamic shading
            if self._rng.random() < variation_amount * 0.5:
                n.velocity = max(20, min(120, n.velocity +
                                         self._rng.randint(-15, 15)))

            # Duration variation: slight rhythmic flexibility
            if self._rng.random() < variation_amount * 0.3:
                n.duration *= self._rng.uniform(0.8, 1.2)

            new_notes.append(n)

        return Phrase(
            phrase_id=f"{phrase.phrase_id}_var",
            notes=new_notes,
            name=f"{phrase.name} (variation)",
            tags=phrase.tags + ["variation"],
        )

    def generate_response_phrase(self, antecedent: Phrase,
                                 scale_name: str = "natural_minor",
                                 root: int = 62) -> Phrase:
        """
        Generate a consequent phrase that 'answers' the antecedent.
        Uses the contour of the antecedent but ends on a stable tone.
        """
        scale = get_scale_pitches(root, scale_name, octave_range=2)
        new_notes: list[Note] = []

        for i, note in enumerate(antecedent.notes):
            n = copy.copy(note)
            if n.is_rest:
                new_notes.append(n)
                continue

            # Mirror the contour
            if i > 0 and not antecedent.notes[i - 1].is_rest:
                prev_interval = note.pitch - antecedent.notes[i - 1].pitch
                target = new_notes[-1].pitch - prev_interval
                n.pitch = snap_to_scale(target, scale)
            else:
                # Start a step away from the antecedent's starting note
                offset = self._rng.choice([-2, 2, 5])
                n.pitch = snap_to_scale(note.pitch + offset, scale)

            new_notes.append(n)

        # Resolve the last note to the tonic
        if new_notes and not new_notes[-1].is_rest:
            new_notes[-1].pitch = snap_to_scale(root, scale)
            new_notes[-1].duration *= 1.5  # Lengthen for resolution

        return Phrase(
            phrase_id=f"{antecedent.phrase_id}_response",
            notes=new_notes,
            name=f"{antecedent.name} (response)",
            tags=antecedent.tags + ["response"],
        )

    def generate_ma_phrase(self, root: int = 62, length: int = 3) -> Phrase:
        """
        Generate a phrase for a ma moment -- almost silence.
        Very few notes, long durations, soft velocities, wide spaces.
        """
        ma_pitches = get_scale_pitches(root, "ma_scale", octave_range=1)
        notes: list[Note] = []

        for i in range(length):
            # Long silence before the note
            silence_dur = self._rng.uniform(3.0, 8.0)
            notes.append(Note.rest(silence_dur))

            # The note itself: soft, sustained
            pitch = self._rng.choice(ma_pitches)
            duration = self._rng.uniform(4.0, 12.0)
            velocity = self._rng.randint(15, 35)
            notes.append(Note(
                pitch=pitch,
                duration=duration,
                velocity=velocity,
                instrument=Instrument.SHAKUHACHI,
                articulation=ArticulationType.BREATH,
            ))

        # End with silence
        notes.append(Note.rest(self._rng.uniform(4.0, 10.0)))

        return Phrase(
            phrase_id="ma_generated",
            notes=notes,
            name="Ma -- the space between",
            tags=["ma", "silence", "generated"],
        )

    # ----- Motif development -----------------------------------------------

    def develop_motif(self, motif_id: str,
                      technique: str = "variation") -> Optional[Phrase]:
        """
        Apply a compositional development technique to a motif's primary
        phrase and return the result.

        Techniques: variation, retrograde, inversion, augmentation,
                    diminution, fragmentation, sequence
        """
        motif = self.motifs.get(motif_id)
        if motif is None or not motif.phrases:
            return None

        source = motif.get_primary_phrase()
        if source is None:
            return None

        if technique == "variation":
            return self.generate_variation(source, 0.4)
        elif technique == "retrograde":
            return source.retrograde()
        elif technique == "inversion":
            return source.invert(motif.key_root)
        elif technique == "augmentation":
            return source.augment(2.0)
        elif technique == "diminution":
            return source.diminish(0.5)
        elif technique == "fragmentation":
            # Take only the first half of the phrase
            half = max(1, len(source.notes) // 2)
            return Phrase(
                phrase_id=f"{source.phrase_id}_frag",
                notes=list(source.notes[:half]),
                name=f"{source.name} (fragment)",
                tags=source.tags + ["fragment"],
            )
        elif technique == "sequence":
            # Repeat the phrase transposed up a step
            return source.transpose(2)
        return None

    # ----- Chord generation ------------------------------------------------

    def build_chord(self, root: int, scale_name: str,
                    degree: int = 0, voicing_type: str = "triad",
                    instrument: Instrument = Instrument.PIANO) -> ChordVoicing:
        """
        Build a chord on a given scale degree.

        Parameters
        ----------
        root : int
            MIDI root of the key.
        scale_name : str
            Scale to derive the chord from.
        degree : int
            0-indexed scale degree (0 = tonic, 1 = supertonic, ...).
        voicing_type : str
            'triad', 'seventh', 'open', 'power'
        """
        scale_intervals = SCALES.get(scale_name, SCALES["natural_minor"])
        num_notes = len(scale_intervals)

        def scale_pitch(deg: int) -> int:
            octave_offset = deg // num_notes
            idx = deg % num_notes
            return root + octave_offset * 12 + scale_intervals[idx]

        if voicing_type == "triad":
            pitches = [scale_pitch(degree), scale_pitch(degree + 2),
                       scale_pitch(degree + 4)]
        elif voicing_type == "seventh":
            pitches = [scale_pitch(degree), scale_pitch(degree + 2),
                       scale_pitch(degree + 4), scale_pitch(degree + 6)]
        elif voicing_type == "open":
            # Root, fifth, octave-root -- spacious voicing
            pitches = [scale_pitch(degree),
                       scale_pitch(degree + 4),
                       scale_pitch(degree) + 12]
        elif voicing_type == "power":
            # Root and fifth only
            pitches = [scale_pitch(degree), scale_pitch(degree + 4)]
        else:
            pitches = [scale_pitch(degree)]

        chord_name = f"{note_name(pitches[0])}_{voicing_type}"
        return ChordVoicing(
            name=chord_name,
            pitches=pitches,
            instrument=instrument,
        )

    def generate_progression(
        self,
        key_root: int = 62,
        scale_name: str = "natural_minor",
        length: int = 4,
        style: str = "emotional",
    ) -> ChordProgression:
        """
        Generate a chord progression in the given key and style.

        Styles:
            emotional:  i - VI - III - VII  (RPG standard, sweeping)
            melancholy: i - iv - v - i      (circular sadness)
            spirit:     Open fifths moving in parallel (Debussy-like)
            tension:    Chromatic approach chords (MIRAIKAN, unease)
        """
        patterns: dict[str, list[int]] = {
            "emotional":  [0, 5, 2, 6],
            "melancholy": [0, 3, 4, 0],
            "spirit":     [0, 4, 5, 2],
            "tension":    [0, 1, 5, 6],
            "heroic":     [0, 3, 5, 4],
            "nostalgic":  [0, 2, 5, 3],
        }
        degrees = patterns.get(style, patterns["emotional"])
        if length > len(degrees):
            degrees = degrees * ((length // len(degrees)) + 1)
        degrees = degrees[:length]

        voicing = "open" if style == "spirit" else "triad"
        chords = [
            self.build_chord(key_root, scale_name, d, voicing)
            for d in degrees
        ]

        return ChordProgression(
            progression_id=f"prog_{style}_{note_name(key_root)}",
            key_root=key_root,
            scale=scale_name,
            chords=chords,
            name=f"{style.title()} in {note_name(key_root)}",
            tags=[style],
        )

    # ----- Composition selection -------------------------------------------

    def select_motif_for_context(
        self,
        game_state: str,
        location: str = "",
        spirit_permeability: float = 0.0,
        ma_level: float = 0.0,
        characters_present: Optional[list[str]] = None,
    ) -> Optional[Motif]:
        """
        Choose the most appropriate motif for the current game context.
        Returns the motif, possibly transposed or altered.
        """
        if characters_present is None:
            characters_present = []

        # Ma moments override everything
        if ma_level > 0.6:
            ma_motifs = self.get_motifs_by_tag("ma")
            if ma_motifs:
                return self._rng.choice(ma_motifs)

        # Character themes take priority if a key character is present
        character_motif_map = {
            "aoi": "aoi_theme",
            "grandmother": "grandmother_theme",
            "kuro": "spirit_world_theme",
        }
        for char in characters_present:
            motif_id = character_motif_map.get(char.lower())
            if motif_id and motif_id in self.motifs:
                motif = self.motifs[motif_id]
                # If spirit permeability is high, shift to Japanese scales
                if spirit_permeability > 0.5:
                    self.set_spirit_blend(spirit_permeability)
                return motif

        # Game-state based selection
        state_tags = {
            "combat": "battle",
            "exploration": "exploration",
            "dialogue": "character",
            "puzzle": "puzzle",
            "vignette": "contemplative",
            "spirit_vision": "spirit",
        }
        tag = state_tags.get(game_state.lower(), "exploration")
        candidates = self.get_motifs_by_tag(tag)

        # Location narrowing
        if location and candidates:
            location_matches = [
                m for m in candidates if location.lower() in
                [t.lower() for t in m.tags]
            ]
            if location_matches:
                candidates = location_matches

        if candidates:
            return self._rng.choice(candidates)

        # Fallback
        return next(iter(self.motifs.values()), None)

    # ----- Beat and tempo --------------------------------------------------

    def set_tempo(self, bpm: float) -> None:
        self._tempo_bpm = max(20.0, min(300.0, bpm))

    def beats_to_seconds(self, beats: float) -> float:
        return beats * 60.0 / self._tempo_bpm

    def seconds_to_beats(self, seconds: float) -> float:
        return seconds * self._tempo_bpm / 60.0

    # ----- Serialization helpers -------------------------------------------

    def motif_to_dict(self, motif: Motif) -> dict:
        """Serialize a motif for saving / inspection."""
        return {
            "motif_id": motif.motif_id,
            "name": motif.name,
            "key": note_name(motif.key_root),
            "scale": motif.scale,
            "tempo": motif.tempo_bpm,
            "instrument": motif.primary_instrument.value,
            "phrases": [
                {
                    "phrase_id": p.phrase_id,
                    "notes": [
                        [n.pitch, n.duration, n.velocity]
                        for n in p.notes
                    ],
                }
                for p in motif.phrases
            ],
        }

    def phrase_from_note_list(
        self,
        phrase_id: str,
        note_data: list[list],
        instrument: Instrument = Instrument.PIANO,
        name: str = "",
        tags: Optional[list[str]] = None,
    ) -> Phrase:
        """
        Create a Phrase from a list of [midi_note, duration, velocity] triples.
        A pitch of -1 denotes a rest.
        """
        notes = []
        for entry in note_data:
            pitch, dur, vel = int(entry[0]), float(entry[1]), int(entry[2])
            if pitch < 0:
                notes.append(Note.rest(dur))
            else:
                notes.append(Note(
                    pitch=pitch,
                    duration=dur,
                    velocity=vel,
                    instrument=instrument,
                ))
        return Phrase(
            phrase_id=phrase_id,
            notes=notes,
            name=name,
            tags=tags or [],
        )
