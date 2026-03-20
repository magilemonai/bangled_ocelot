"""
Ma no Kuni - Ambient Soundscape Manager

Two Tokyos occupy the same space:
  - The material city: trains, crosswalks, rain, vending machines, crowds
  - The spirit city: wind chimes without wind, distant bells, whispered names

This system blends them according to spirit permeability, location,
season, and time of day. The result is a living, breathing acoustic
world where the ordinary and the otherworldly coexist.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SoundDomain(Enum):
    """Which world a sound belongs to."""
    MATERIAL = "material"
    SPIRIT = "spirit"
    SHARED = "shared"    # Some sounds exist in both (wind, rain, heartbeats)


class SoundCategory(Enum):
    """Broad classification for ambient sounds."""
    WEATHER = "weather"
    URBAN = "urban"
    NATURE = "nature"
    HUMAN = "human"
    MECHANICAL = "mechanical"
    SPIRITUAL = "spiritual"
    TEMPORAL = "temporal"     # Sounds that mark the passage of time


class SeasonalVariant(Enum):
    """Season-specific ambient variants."""
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"
    ALL = "all"


class TimeVariant(Enum):
    """Time-of-day variants for ambient sounds."""
    DAWN = "dawn"
    MORNING = "morning"
    MIDDAY = "midday"
    AFTERNOON = "afternoon"
    DUSK = "dusk"
    EVENING = "evening"
    MIDNIGHT = "midnight"
    WITCHING = "witching"
    ALL = "all"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class AmbientSound:
    """
    A single ambient sound element that can be layered into a soundscape.
    """
    sound_id: str
    name: str
    asset_path: str = ""
    domain: SoundDomain = SoundDomain.MATERIAL
    category: SoundCategory = SoundCategory.URBAN
    volume: float = 0.5
    volume_range: tuple[float, float] = (0.3, 0.7)
    pan: float = 0.0               # -1 = left, 1 = right
    pan_range: tuple[float, float] = (-0.5, 0.5)
    loop: bool = True
    min_interval: float = 0.0      # For non-looping: min seconds between plays
    max_interval: float = 0.0      # For non-looping: max seconds between plays
    fade_in: float = 1.0
    fade_out: float = 1.0
    pitch_variation: float = 0.0   # Random pitch shift range in semitones
    reverb_send: float = 0.0
    low_pass: float = 20000.0
    seasons: list[SeasonalVariant] = field(
        default_factory=lambda: [SeasonalVariant.ALL]
    )
    times: list[TimeVariant] = field(
        default_factory=lambda: [TimeVariant.ALL]
    )
    districts: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    description: str = ""

    def is_active_for_season(self, season: str) -> bool:
        if SeasonalVariant.ALL in self.seasons:
            return True
        try:
            return SeasonalVariant(season.lower()) in self.seasons
        except ValueError:
            return True

    def is_active_for_time(self, time_of_day: str) -> bool:
        if TimeVariant.ALL in self.times:
            return True
        try:
            return TimeVariant(time_of_day.lower()) in self.times
        except ValueError:
            return True

    def is_active_for_district(self, district: str) -> bool:
        if not self.districts:
            return True  # No restriction
        return district.lower() in [d.lower() for d in self.districts]


@dataclass
class SoundInstance:
    """
    A runtime instance of an ambient sound currently playing.
    """
    sound: AmbientSound
    current_volume: float = 0.0
    target_volume: float = 0.0
    current_pan: float = 0.0
    playing: bool = False
    fade_progress: float = 1.0     # 0.0 = start of fade, 1.0 = complete
    fade_duration: float = 1.0
    fade_direction: str = "none"   # "in", "out", "none"
    next_trigger_time: float = 0.0 # For intermittent sounds
    time_until_trigger: float = 0.0

    def start_fade_in(self, duration: float = 1.0) -> None:
        self.fade_direction = "in"
        self.fade_progress = 0.0
        self.fade_duration = max(0.01, duration)
        self.playing = True

    def start_fade_out(self, duration: float = 1.0) -> None:
        self.fade_direction = "out"
        self.fade_progress = 0.0
        self.fade_duration = max(0.01, duration)

    def update(self, delta: float) -> None:
        if self.fade_direction != "none":
            self.fade_progress += delta / self.fade_duration
            if self.fade_progress >= 1.0:
                self.fade_progress = 1.0
                if self.fade_direction == "out":
                    self.playing = False
                    self.current_volume = 0.0
                elif self.fade_direction == "in":
                    self.current_volume = self.target_volume
                self.fade_direction = "none"
            else:
                t = self.fade_progress
                # Smooth ease curve
                curved = t * t * (3.0 - 2.0 * t)
                if self.fade_direction == "in":
                    self.current_volume = self.target_volume * curved
                else:
                    self.current_volume = self.target_volume * (1.0 - curved)


@dataclass
class DistrictSoundProfile:
    """
    The acoustic personality of a Tokyo district.
    Each district has a distinct blend of material and spirit sounds.
    """
    district_id: str
    name: str
    material_sounds: list[str] = field(default_factory=list)
    spirit_sounds: list[str] = field(default_factory=list)
    shared_sounds: list[str] = field(default_factory=list)
    base_spirit_resonance: float = 0.0   # How easily spirits bleed through here
    material_volume_modifier: float = 1.0
    spirit_volume_modifier: float = 1.0
    reverb_character: float = 0.3        # 0.0 = dry/open, 1.0 = cavernous
    description: str = ""


@dataclass
class WeatherState:
    """Current weather conditions affecting the soundscape."""
    rain_intensity: float = 0.0       # 0 = none, 1 = downpour
    wind_strength: float = 0.0       # 0 = calm, 1 = storm
    thunder: bool = False
    snow: bool = False
    fog: bool = False                 # Fog muffles material sounds, amplifies spirit
    humidity: float = 0.5            # Affects reverb character


# ---------------------------------------------------------------------------
# Soundscape Manager
# ---------------------------------------------------------------------------

class SoundscapeManager:
    """
    Manages the ambient audio environment of Ma no Kuni.

    The soundscape is a living mix of material and spirit world sounds.
    As spirit permeability changes, the spirit sounds fade in and
    material sounds may become muffled, distant, or distorted.

    Each district has its own acoustic profile. Shibuya is loud and
    dense; Yanaka is quiet, with birdsong. The spirit overlay differs
    too: Asakusa's spirit sounds are temple bells and chanting;
    Akihabara's are the hum of restless digital yokai.
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        self.sounds: dict[str, AmbientSound] = {}
        self.districts: dict[str, DistrictSoundProfile] = {}
        self.active_instances: dict[str, SoundInstance] = {}
        self.master_volume: float = 0.7
        self.material_mix: float = 1.0    # Overall material layer volume
        self.spirit_mix: float = 0.0      # Overall spirit layer volume
        self._current_district: Optional[str] = None
        self._current_season: str = "spring"
        self._current_time: str = "morning"
        self._spirit_permeability: float = 0.0
        self._weather: WeatherState = WeatherState()
        self._rng = random.Random(seed)
        self._transition_duration: float = 3.0

    # ----- Registration ----------------------------------------------------

    def register_sound(self, sound: AmbientSound) -> None:
        self.sounds[sound.sound_id] = sound

    def register_district(self, profile: DistrictSoundProfile) -> None:
        self.districts[profile.district_id] = profile

    # ----- District transitions --------------------------------------------

    def enter_district(self, district_id: str,
                       transition_time: float = 3.0) -> None:
        """
        Move to a new district. Fades out sounds that do not belong
        to the new district and fades in the new ones.
        """
        if district_id == self._current_district:
            return

        old_district = self._current_district
        self._current_district = district_id
        self._transition_duration = transition_time

        profile = self.districts.get(district_id)
        if profile is None:
            return

        # Determine which sounds should be active
        target_sounds = set()
        target_sounds.update(profile.material_sounds)
        target_sounds.update(profile.shared_sounds)
        # Spirit sounds gated by permeability
        if self._spirit_permeability > 0.1:
            target_sounds.update(profile.spirit_sounds)

        # Fade out sounds not in the new set
        for sound_id, instance in list(self.active_instances.items()):
            if sound_id not in target_sounds:
                instance.start_fade_out(transition_time)

        # Fade in new sounds
        for sound_id in target_sounds:
            if sound_id in self.active_instances:
                continue  # Already playing
            sound = self.sounds.get(sound_id)
            if sound is None:
                continue
            if not self._is_sound_eligible(sound):
                continue
            self._activate_sound(sound, transition_time)

    def _is_sound_eligible(self, sound: AmbientSound) -> bool:
        """Check season, time-of-day, and district filters."""
        if not sound.is_active_for_season(self._current_season):
            return False
        if not sound.is_active_for_time(self._current_time):
            return False
        return True

    def _activate_sound(self, sound: AmbientSound,
                        fade_time: float = 1.0) -> None:
        """Start playing an ambient sound."""
        volume = self._calculate_sound_volume(sound)
        pan = self._rng.uniform(*sound.pan_range) if sound.pan == 0.0 else sound.pan

        instance = SoundInstance(
            sound=sound,
            target_volume=volume,
            current_pan=pan,
        )
        instance.start_fade_in(max(fade_time, sound.fade_in))

        if not sound.loop:
            instance.time_until_trigger = self._rng.uniform(
                sound.min_interval, max(sound.min_interval, sound.max_interval)
            )

        self.active_instances[sound.sound_id] = instance

    def _calculate_sound_volume(self, sound: AmbientSound) -> float:
        """Calculate the effective volume for a sound given all modifiers."""
        base = self._rng.uniform(*sound.volume_range)
        profile = self.districts.get(self._current_district or "")

        # Domain mixing
        if sound.domain == SoundDomain.MATERIAL:
            base *= self.material_mix
            if profile:
                base *= profile.material_volume_modifier
            # Fog muffles material sounds
            if self._weather.fog:
                base *= 0.6
        elif sound.domain == SoundDomain.SPIRIT:
            base *= self.spirit_mix
            if profile:
                base *= profile.spirit_volume_modifier
            # Fog amplifies spirit sounds
            if self._weather.fog:
                base *= 1.3
        # SHARED sounds get the average of both mixes
        else:
            base *= (self.material_mix + self.spirit_mix) / 2.0

        # Rain reduces outdoor ambient sounds, adds its own
        if self._weather.rain_intensity > 0.3:
            if sound.category in (SoundCategory.NATURE, SoundCategory.HUMAN):
                rain_duck = 1.0 - self._weather.rain_intensity * 0.5
                base *= rain_duck

        return max(0.0, min(1.0, base))

    # ----- Permeability ----------------------------------------------------

    def set_spirit_permeability(self, value: float) -> None:
        """
        Update spirit permeability. This is the master control for how
        much the spirit soundscape bleeds into the material one.
        """
        old = self._spirit_permeability
        self._spirit_permeability = max(0.0, min(1.0, value))

        # Calculate mix levels
        self.spirit_mix = self._spirit_permeability
        # Material sounds get slightly muffled as spirit world takes over
        self.material_mix = 1.0 - self._spirit_permeability * 0.3

        profile = self.districts.get(self._current_district or "")
        if profile is None:
            return

        # Activate spirit sounds if permeability crossed threshold
        if old < 0.1 <= self._spirit_permeability:
            for sound_id in profile.spirit_sounds:
                if sound_id not in self.active_instances:
                    sound = self.sounds.get(sound_id)
                    if sound and self._is_sound_eligible(sound):
                        self._activate_sound(sound, 4.0)

        # Deactivate spirit sounds if permeability dropped
        if self._spirit_permeability < 0.1 <= old:
            for sound_id in profile.spirit_sounds:
                if sound_id in self.active_instances:
                    self.active_instances[sound_id].start_fade_out(3.0)

        # Update volumes for all active spirit sounds
        for sound_id, instance in self.active_instances.items():
            if instance.sound.domain == SoundDomain.SPIRIT:
                instance.target_volume = self._calculate_sound_volume(
                    instance.sound
                )

    # ----- Time and season -------------------------------------------------

    def set_time_of_day(self, time_of_day: str) -> None:
        """
        Change time of day. Fades in/out sounds that are time-specific.
        Dawn brings birdsong. Midnight brings silence and spirits.
        """
        if time_of_day == self._current_time:
            return
        self._current_time = time_of_day
        self._refresh_active_sounds()

    def set_season(self, season: str) -> None:
        """
        Change the season. Spring has cherry blossom rustle, summer has
        cicadas, autumn has dry leaves, winter has cold wind.
        """
        if season == self._current_season:
            return
        self._current_season = season
        self._refresh_active_sounds()

    def set_weather(self, weather: WeatherState) -> None:
        """Update weather conditions."""
        self._weather = weather
        self._refresh_active_sounds()

    def _refresh_active_sounds(self) -> None:
        """Re-evaluate which sounds should be active after a context change."""
        profile = self.districts.get(self._current_district or "")
        if profile is None:
            return

        all_district_sounds = set()
        all_district_sounds.update(profile.material_sounds)
        all_district_sounds.update(profile.shared_sounds)
        if self._spirit_permeability > 0.1:
            all_district_sounds.update(profile.spirit_sounds)

        for sound_id in all_district_sounds:
            sound = self.sounds.get(sound_id)
            if sound is None:
                continue

            eligible = self._is_sound_eligible(sound)
            currently_playing = (
                sound_id in self.active_instances
                and self.active_instances[sound_id].playing
            )

            if eligible and not currently_playing:
                self._activate_sound(sound, 2.0)
            elif not eligible and currently_playing:
                self.active_instances[sound_id].start_fade_out(2.0)
            elif eligible and currently_playing:
                # Update volume in case modifiers changed
                self.active_instances[sound_id].target_volume = (
                    self._calculate_sound_volume(sound)
                )

    # ----- Main update -----------------------------------------------------

    def update(self, delta: float) -> None:
        """
        Advance all active sound instances. Call once per frame.
        """
        to_remove: list[str] = []

        for sound_id, instance in self.active_instances.items():
            instance.update(delta)

            # Handle intermittent (non-looping) sounds
            if not instance.sound.loop and instance.playing:
                instance.time_until_trigger -= delta
                if instance.time_until_trigger <= 0.0:
                    # Trigger the sound, schedule next occurrence
                    instance.time_until_trigger = self._rng.uniform(
                        instance.sound.min_interval,
                        max(instance.sound.min_interval,
                            instance.sound.max_interval),
                    )
                    # Randomize pan for spatial variety
                    instance.current_pan = self._rng.uniform(
                        *instance.sound.pan_range
                    )

            # Clean up stopped instances
            if not instance.playing and instance.fade_direction == "none":
                to_remove.append(sound_id)

        for sound_id in to_remove:
            del self.active_instances[sound_id]

    # ----- Queries ---------------------------------------------------------

    def get_active_sounds(self) -> list[dict]:
        """Return info on all currently playing sounds."""
        return [
            {
                "sound_id": sid,
                "name": inst.sound.name,
                "domain": inst.sound.domain.value,
                "category": inst.sound.category.value,
                "volume": round(inst.current_volume * self.master_volume, 3),
                "pan": round(inst.current_pan, 2),
                "playing": inst.playing,
            }
            for sid, inst in self.active_instances.items()
            if inst.playing
        ]

    def get_mix_state(self) -> dict:
        """Return the current mix balance."""
        return {
            "master_volume": self.master_volume,
            "material_mix": round(self.material_mix, 3),
            "spirit_mix": round(self.spirit_mix, 3),
            "permeability": round(self._spirit_permeability, 3),
            "district": self._current_district,
            "season": self._current_season,
            "time": self._current_time,
            "weather": {
                "rain": self._weather.rain_intensity,
                "wind": self._weather.wind_strength,
                "fog": self._weather.fog,
            },
            "active_sound_count": sum(
                1 for i in self.active_instances.values() if i.playing
            ),
        }


# ---------------------------------------------------------------------------
# Pre-defined ambient sound library
# ---------------------------------------------------------------------------

def create_tokyo_sounds() -> list[AmbientSound]:
    """
    Factory function returning the core set of material-world Tokyo sounds.
    """
    return [
        # -- Urban --
        AmbientSound(
            sound_id="train_passing",
            name="Train passing",
            domain=SoundDomain.MATERIAL,
            category=SoundCategory.URBAN,
            volume=0.5,
            volume_range=(0.4, 0.7),
            loop=False,
            min_interval=20.0,
            max_interval=60.0,
            pan_range=(-1.0, 1.0),
            fade_in=1.5,
            fade_out=2.0,
            description="The approaching rumble, doppler shift, receding clatter",
        ),
        AmbientSound(
            sound_id="crosswalk_signal",
            name="Crosswalk signal",
            domain=SoundDomain.MATERIAL,
            category=SoundCategory.URBAN,
            volume=0.3,
            volume_range=(0.2, 0.4),
            loop=False,
            min_interval=30.0,
            max_interval=90.0,
            pan_range=(-0.3, 0.3),
            description="The tori no uta melody that guides you across",
        ),
        AmbientSound(
            sound_id="vending_machine_hum",
            name="Vending machine hum",
            domain=SoundDomain.MATERIAL,
            category=SoundCategory.MECHANICAL,
            volume=0.15,
            volume_range=(0.1, 0.2),
            loop=True,
            pan_range=(0.2, 0.6),
            low_pass=4000.0,
            description="The constant drone of illuminated drink machines",
        ),
        AmbientSound(
            sound_id="crowd_murmur",
            name="Crowd murmur",
            domain=SoundDomain.MATERIAL,
            category=SoundCategory.HUMAN,
            volume=0.4,
            volume_range=(0.2, 0.6),
            loop=True,
            low_pass=6000.0,
            times=[TimeVariant.MORNING, TimeVariant.MIDDAY,
                   TimeVariant.AFTERNOON, TimeVariant.EVENING],
            description="The hum of thousands of lives, indistinct but warm",
        ),
        AmbientSound(
            sound_id="footsteps_pavement",
            name="Footsteps on pavement",
            domain=SoundDomain.MATERIAL,
            category=SoundCategory.HUMAN,
            volume=0.25,
            volume_range=(0.15, 0.35),
            loop=False,
            min_interval=2.0,
            max_interval=8.0,
            pan_range=(-0.8, 0.8),
            description="Individual footsteps clicking past on concrete",
        ),
        AmbientSound(
            sound_id="bicycle_bell",
            name="Bicycle bell",
            domain=SoundDomain.MATERIAL,
            category=SoundCategory.URBAN,
            volume=0.3,
            volume_range=(0.2, 0.4),
            loop=False,
            min_interval=40.0,
            max_interval=120.0,
            pan_range=(-0.8, 0.8),
            pitch_variation=2.0,
            description="A bright ring as a cyclist passes",
        ),
        AmbientSound(
            sound_id="convenience_store_chime",
            name="Konbini door chime",
            domain=SoundDomain.MATERIAL,
            category=SoundCategory.URBAN,
            volume=0.2,
            volume_range=(0.15, 0.3),
            loop=False,
            min_interval=15.0,
            max_interval=45.0,
            pan_range=(-0.4, 0.4),
            reverb_send=0.2,
            description="The cheerful electronic jingle of a convenience store",
        ),
        AmbientSound(
            sound_id="distant_sirens",
            name="Distant sirens",
            domain=SoundDomain.MATERIAL,
            category=SoundCategory.URBAN,
            volume=0.2,
            volume_range=(0.1, 0.3),
            loop=False,
            min_interval=60.0,
            max_interval=180.0,
            pan_range=(-1.0, 1.0),
            low_pass=3000.0,
            reverb_send=0.4,
            times=[TimeVariant.EVENING, TimeVariant.MIDNIGHT, TimeVariant.WITCHING],
            description="Emergency vehicles wailing somewhere across the city",
        ),
        # -- Weather --
        AmbientSound(
            sound_id="rain_light",
            name="Light rain",
            domain=SoundDomain.SHARED,
            category=SoundCategory.WEATHER,
            volume=0.4,
            volume_range=(0.3, 0.5),
            loop=True,
            reverb_send=0.3,
            description="Gentle rain on streets and rooftops",
        ),
        AmbientSound(
            sound_id="rain_heavy",
            name="Heavy rain",
            domain=SoundDomain.SHARED,
            category=SoundCategory.WEATHER,
            volume=0.7,
            volume_range=(0.6, 0.8),
            loop=True,
            reverb_send=0.5,
            low_pass=8000.0,
            description="Torrential downpour washing the city clean",
        ),
        AmbientSound(
            sound_id="thunder_distant",
            name="Distant thunder",
            domain=SoundDomain.SHARED,
            category=SoundCategory.WEATHER,
            volume=0.5,
            volume_range=(0.3, 0.7),
            loop=False,
            min_interval=15.0,
            max_interval=60.0,
            reverb_send=0.8,
            low_pass=2000.0,
            description="Thunder rolling across the city, felt as much as heard",
        ),
        AmbientSound(
            sound_id="wind_gentle",
            name="Gentle wind",
            domain=SoundDomain.SHARED,
            category=SoundCategory.WEATHER,
            volume=0.2,
            volume_range=(0.1, 0.3),
            loop=True,
            description="Soft breeze through the streets",
        ),
        # -- Nature --
        AmbientSound(
            sound_id="morning_birds",
            name="Morning birdsong",
            domain=SoundDomain.MATERIAL,
            category=SoundCategory.NATURE,
            volume=0.3,
            volume_range=(0.2, 0.4),
            loop=True,
            times=[TimeVariant.DAWN, TimeVariant.MORNING],
            seasons=[SeasonalVariant.SPRING, SeasonalVariant.SUMMER],
            pan_range=(-0.6, 0.6),
            description="Sparrows and crows greeting the day",
        ),
        AmbientSound(
            sound_id="evening_crickets",
            name="Evening crickets",
            domain=SoundDomain.MATERIAL,
            category=SoundCategory.NATURE,
            volume=0.25,
            volume_range=(0.15, 0.35),
            loop=True,
            times=[TimeVariant.EVENING, TimeVariant.MIDNIGHT],
            seasons=[SeasonalVariant.SUMMER, SeasonalVariant.AUTUMN],
            description="Suzumushi singing in the darkening gardens",
        ),
        AmbientSound(
            sound_id="cicadas",
            name="Cicadas",
            domain=SoundDomain.MATERIAL,
            category=SoundCategory.NATURE,
            volume=0.5,
            volume_range=(0.4, 0.7),
            loop=True,
            times=[TimeVariant.MIDDAY, TimeVariant.AFTERNOON],
            seasons=[SeasonalVariant.SUMMER],
            description="The overwhelming drone of summer, a wall of sound",
        ),
        AmbientSound(
            sound_id="cherry_blossom_rustle",
            name="Cherry blossom petals",
            domain=SoundDomain.SHARED,
            category=SoundCategory.NATURE,
            volume=0.15,
            volume_range=(0.1, 0.2),
            loop=True,
            seasons=[SeasonalVariant.SPRING],
            reverb_send=0.3,
            description="Petals drifting -- they carry messages between worlds",
        ),
        AmbientSound(
            sound_id="autumn_leaves",
            name="Dry leaves skittering",
            domain=SoundDomain.MATERIAL,
            category=SoundCategory.NATURE,
            volume=0.2,
            volume_range=(0.1, 0.3),
            loop=False,
            min_interval=5.0,
            max_interval=20.0,
            seasons=[SeasonalVariant.AUTUMN],
            pan_range=(-0.7, 0.7),
            description="Dead leaves scraping across pavement in the wind",
        ),
        AmbientSound(
            sound_id="cold_wind",
            name="Cold winter wind",
            domain=SoundDomain.SHARED,
            category=SoundCategory.WEATHER,
            volume=0.35,
            volume_range=(0.2, 0.5),
            loop=True,
            seasons=[SeasonalVariant.WINTER],
            low_pass=5000.0,
            description="A bitter wind that makes the veil between worlds brittle",
        ),
    ]


def create_spirit_sounds() -> list[AmbientSound]:
    """
    Factory function returning spirit-world ambient sounds.
    These are the sounds of the other Tokyo -- the one you hear
    when the veil is thin.
    """
    return [
        AmbientSound(
            sound_id="wind_chimes_no_wind",
            name="Wind chimes without wind",
            domain=SoundDomain.SPIRIT,
            category=SoundCategory.SPIRITUAL,
            volume=0.3,
            volume_range=(0.15, 0.4),
            loop=False,
            min_interval=10.0,
            max_interval=30.0,
            reverb_send=0.7,
            pan_range=(-0.5, 0.5),
            pitch_variation=3.0,
            description="Furin chimes ring on still air -- something is passing",
        ),
        AmbientSound(
            sound_id="distant_bells",
            name="Distant temple bells",
            domain=SoundDomain.SPIRIT,
            category=SoundCategory.SPIRITUAL,
            volume=0.25,
            volume_range=(0.15, 0.35),
            loop=False,
            min_interval=20.0,
            max_interval=60.0,
            reverb_send=0.9,
            low_pass=4000.0,
            pan_range=(-0.3, 0.3),
            description="A temple bell tolling in a world that shares your space",
        ),
        AmbientSound(
            sound_id="whispered_names",
            name="Whispered names",
            domain=SoundDomain.SPIRIT,
            category=SoundCategory.SPIRITUAL,
            volume=0.15,
            volume_range=(0.08, 0.2),
            loop=False,
            min_interval=30.0,
            max_interval=90.0,
            reverb_send=0.6,
            low_pass=3000.0,
            pan_range=(-0.8, 0.8),
            description="Someone -- something -- calling a name just below hearing",
        ),
        AmbientSound(
            sound_id="breathing_spaces",
            name="Breathing spaces",
            domain=SoundDomain.SPIRIT,
            category=SoundCategory.SPIRITUAL,
            volume=0.1,
            volume_range=(0.05, 0.15),
            loop=True,
            reverb_send=0.5,
            low_pass=2000.0,
            description="The slow, deep breathing of spaces that are alive",
        ),
        AmbientSound(
            sound_id="spirit_footsteps",
            name="Unseen footsteps",
            domain=SoundDomain.SPIRIT,
            category=SoundCategory.SPIRITUAL,
            volume=0.2,
            volume_range=(0.1, 0.3),
            loop=False,
            min_interval=15.0,
            max_interval=45.0,
            pan_range=(-1.0, 1.0),
            reverb_send=0.4,
            description="Footsteps with no body, passing close",
        ),
        AmbientSound(
            sound_id="spirit_water",
            name="Spirit water",
            domain=SoundDomain.SPIRIT,
            category=SoundCategory.SPIRITUAL,
            volume=0.2,
            volume_range=(0.1, 0.25),
            loop=True,
            reverb_send=0.8,
            low_pass=5000.0,
            description="Water flowing somewhere impossibly close and far",
        ),
        AmbientSound(
            sound_id="veil_hum",
            name="The hum of the veil",
            domain=SoundDomain.SPIRIT,
            category=SoundCategory.SPIRITUAL,
            volume=0.1,
            volume_range=(0.05, 0.15),
            loop=True,
            low_pass=1500.0,
            description="A sub-bass presence, like standing near a power line in another dimension",
        ),
        AmbientSound(
            sound_id="spirit_laughter",
            name="Distant spirit laughter",
            domain=SoundDomain.SPIRIT,
            category=SoundCategory.SPIRITUAL,
            volume=0.12,
            volume_range=(0.06, 0.18),
            loop=False,
            min_interval=45.0,
            max_interval=120.0,
            reverb_send=0.7,
            pan_range=(-0.6, 0.6),
            low_pass=4000.0,
            times=[TimeVariant.DUSK, TimeVariant.EVENING,
                   TimeVariant.MIDNIGHT, TimeVariant.WITCHING],
            description="Children laughing? No -- older, stranger",
        ),
        AmbientSound(
            sound_id="koto_fragment",
            name="Koto fragment",
            domain=SoundDomain.SPIRIT,
            category=SoundCategory.SPIRITUAL,
            volume=0.2,
            volume_range=(0.1, 0.25),
            loop=False,
            min_interval=30.0,
            max_interval=90.0,
            reverb_send=0.6,
            pan_range=(-0.4, 0.4),
            pitch_variation=2.0,
            description="A few notes of koto from a room that does not exist",
        ),
        AmbientSound(
            sound_id="spirit_static",
            name="Spirit static",
            domain=SoundDomain.SPIRIT,
            category=SoundCategory.SPIRITUAL,
            volume=0.1,
            volume_range=(0.05, 0.15),
            loop=True,
            low_pass=8000.0,
            description="Like radio static, but organic -- the noise between worlds",
        ),
        AmbientSound(
            sound_id="paper_rustle",
            name="Ofuda rustling",
            domain=SoundDomain.SPIRIT,
            category=SoundCategory.SPIRITUAL,
            volume=0.12,
            volume_range=(0.08, 0.18),
            loop=False,
            min_interval=20.0,
            max_interval=50.0,
            pan_range=(-0.5, 0.5),
            description="Spirit wards flutter as something passes near",
        ),
        AmbientSound(
            sound_id="midnight_silence",
            name="Midnight silence",
            domain=SoundDomain.SPIRIT,
            category=SoundCategory.TEMPORAL,
            volume=0.05,
            volume_range=(0.02, 0.08),
            loop=True,
            times=[TimeVariant.MIDNIGHT, TimeVariant.WITCHING],
            low_pass=2000.0,
            reverb_send=0.9,
            description="The deepest silence has its own sound -- a held breath",
        ),
    ]


def create_district_profiles() -> list[DistrictSoundProfile]:
    """
    Factory function returning acoustic profiles for Tokyo's districts.
    """
    return [
        DistrictSoundProfile(
            district_id="shibuya",
            name="Shibuya",
            material_sounds=[
                "train_passing", "crosswalk_signal", "crowd_murmur",
                "footsteps_pavement", "vending_machine_hum",
                "convenience_store_chime",
            ],
            spirit_sounds=[
                "wind_chimes_no_wind", "whispered_names",
                "spirit_footsteps", "spirit_static",
            ],
            shared_sounds=["rain_light", "rain_heavy", "wind_gentle"],
            base_spirit_resonance=0.15,
            material_volume_modifier=1.2,
            spirit_volume_modifier=0.8,
            reverb_character=0.2,
            description="The crossing, the crowds, the neon -- spirits drown in noise",
        ),
        DistrictSoundProfile(
            district_id="asakusa",
            name="Asakusa",
            material_sounds=[
                "crowd_murmur", "footsteps_pavement", "bicycle_bell",
                "vending_machine_hum",
            ],
            spirit_sounds=[
                "distant_bells", "wind_chimes_no_wind", "breathing_spaces",
                "koto_fragment", "paper_rustle",
            ],
            shared_sounds=[
                "rain_light", "rain_heavy", "wind_gentle",
                "cherry_blossom_rustle",
            ],
            base_spirit_resonance=0.4,
            material_volume_modifier=0.8,
            spirit_volume_modifier=1.3,
            reverb_character=0.5,
            description="Ancient temple grounds; the spirit world is close here",
        ),
        DistrictSoundProfile(
            district_id="yanaka",
            name="Yanaka",
            material_sounds=[
                "footsteps_pavement", "bicycle_bell", "morning_birds",
                "evening_crickets",
            ],
            spirit_sounds=[
                "wind_chimes_no_wind", "distant_bells",
                "breathing_spaces", "whispered_names", "spirit_water",
                "midnight_silence",
            ],
            shared_sounds=[
                "rain_light", "wind_gentle", "cherry_blossom_rustle",
                "autumn_leaves", "cold_wind",
            ],
            base_spirit_resonance=0.5,
            material_volume_modifier=0.6,
            spirit_volume_modifier=1.4,
            reverb_character=0.4,
            description="The old cemetery neighborhood. Grandmother lives here. The quiet is deep.",
        ),
        DistrictSoundProfile(
            district_id="akihabara",
            name="Akihabara",
            material_sounds=[
                "crowd_murmur", "vending_machine_hum",
                "convenience_store_chime", "footsteps_pavement",
                "train_passing",
            ],
            spirit_sounds=[
                "spirit_static", "veil_hum", "spirit_laughter",
                "whispered_names",
            ],
            shared_sounds=["rain_light", "rain_heavy", "wind_gentle"],
            base_spirit_resonance=0.2,
            material_volume_modifier=1.1,
            spirit_volume_modifier=0.9,
            reverb_character=0.3,
            description="Electronic buzz and digital yokai -- new spirits born of current",
        ),
        DistrictSoundProfile(
            district_id="ueno_park",
            name="Ueno Park",
            material_sounds=[
                "morning_birds", "evening_crickets", "cicadas",
                "footsteps_pavement", "bicycle_bell",
            ],
            spirit_sounds=[
                "wind_chimes_no_wind", "spirit_water",
                "breathing_spaces", "spirit_footsteps", "koto_fragment",
            ],
            shared_sounds=[
                "rain_light", "rain_heavy", "wind_gentle",
                "cherry_blossom_rustle", "autumn_leaves", "cold_wind",
            ],
            base_spirit_resonance=0.35,
            material_volume_modifier=0.7,
            spirit_volume_modifier=1.2,
            reverb_character=0.4,
            description="Nature in the city -- a green pause where both worlds breathe",
        ),
        DistrictSoundProfile(
            district_id="miraikan_tower",
            name="MIRAIKAN Corporate Tower",
            material_sounds=[
                "vending_machine_hum",
            ],
            spirit_sounds=[
                "veil_hum", "spirit_static", "breathing_spaces",
            ],
            shared_sounds=["wind_gentle"],
            base_spirit_resonance=0.1,
            material_volume_modifier=0.4,
            spirit_volume_modifier=0.5,
            reverb_character=0.7,
            description="Sterile silence. The hum of machines that harvest spirit energy.",
        ),
        DistrictSoundProfile(
            district_id="spirit_crossing",
            name="Spirit Crossing",
            material_sounds=[],
            spirit_sounds=[
                "wind_chimes_no_wind", "distant_bells", "whispered_names",
                "breathing_spaces", "spirit_footsteps", "spirit_water",
                "veil_hum", "spirit_laughter", "koto_fragment",
                "paper_rustle", "midnight_silence",
            ],
            shared_sounds=["wind_gentle"],
            base_spirit_resonance=1.0,
            material_volume_modifier=0.0,
            spirit_volume_modifier=1.5,
            reverb_character=0.9,
            description="The other side. No material sounds at all. Only spirit.",
        ),
    ]
