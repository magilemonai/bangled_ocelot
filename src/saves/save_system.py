"""
Ma no Kuni - Save System

Saving is an act of crystallization. The world pauses, takes a breath,
and a memory crystal forms containing everything that has happened.

Save points are found at places of spiritual significance:
shrines, grandmother's house, spirit nexuses, places of deep ma.
"""

import json
import os
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class SaveMetadata:
    """Information about a save file, visible before loading."""
    slot: int
    save_name: str
    timestamp: str
    play_time_seconds: float
    chapter: int
    chapter_name: str
    location: str
    district: str
    level: int
    spirit_bonds: int
    day: int
    season: str
    time_of_day: str
    screenshot_data: Optional[str] = None  # Base64 encoded thumbnail
    ma_total: float = 0.0
    completion_percent: float = 0.0

    @property
    def play_time_formatted(self) -> str:
        hours = int(self.play_time_seconds // 3600)
        minutes = int((self.play_time_seconds % 3600) // 60)
        return f"{hours}:{minutes:02d}"


@dataclass
class SaveData:
    """Complete save state - a crystallized moment."""
    metadata: SaveMetadata
    version: str = "0.1.0"

    # Player state
    player: Dict[str, Any] = field(default_factory=dict)
    inventory: List[Dict] = field(default_factory=list)
    equipment: Dict[str, Any] = field(default_factory=dict)

    # World state
    clock: Dict[str, Any] = field(default_factory=dict)
    spirit_tide: Dict[str, Any] = field(default_factory=dict)
    ma_state: Dict[str, Any] = field(default_factory=dict)
    district_states: Dict[str, Any] = field(default_factory=dict)

    # Story state
    flags: Dict[str, Any] = field(default_factory=dict)
    active_quests: List[Dict] = field(default_factory=list)
    completed_quests: List[str] = field(default_factory=list)
    failed_quests: List[str] = field(default_factory=list)

    # Relationships
    relationships: Dict[str, Dict] = field(default_factory=dict)
    spirit_bonds: Dict[str, Dict] = field(default_factory=dict)

    # Bestiary
    bestiary_entries: Dict[str, Dict] = field(default_factory=dict)

    # Discoveries
    discoveries: List[str] = field(default_factory=list)
    visited_locations: List[str] = field(default_factory=list)

    # Crafting
    known_recipes: List[str] = field(default_factory=list)

    # Statistics
    statistics: Dict[str, Any] = field(default_factory=dict)

    # Vignettes witnessed
    vignettes_seen: List[str] = field(default_factory=list)

    # Checksum for integrity
    checksum: str = ""


class SaveSystem:
    """
    Manages save files. Each save is a memory crystal.
    The game supports 9 save slots + 1 autosave.
    """

    MAX_SLOTS = 9
    AUTOSAVE_SLOT = 0
    SAVE_DIR = "saves"

    def __init__(self, base_path: str = "."):
        self.base_path = base_path
        self.save_path = os.path.join(base_path, self.SAVE_DIR)
        self._ensure_save_directory()

    def _ensure_save_directory(self) -> None:
        os.makedirs(self.save_path, exist_ok=True)

    def _slot_filename(self, slot: int) -> str:
        if slot == self.AUTOSAVE_SLOT:
            return os.path.join(self.save_path, "autosave.json")
        return os.path.join(self.save_path, f"save_{slot:02d}.json")

    def _calculate_checksum(self, data: dict) -> str:
        """Calculate integrity checksum for save data."""
        data_copy = {k: v for k, v in data.items() if k != "checksum"}
        raw = json.dumps(data_copy, sort_keys=True).encode()
        return hashlib.sha256(raw).hexdigest()[:16]

    def save(self, slot: int, save_data: SaveData) -> bool:
        """
        Crystallize the current moment into a save file.
        Returns True on success.
        """
        if not (0 <= slot <= self.MAX_SLOTS):
            return False

        save_data.metadata.slot = slot
        save_data.metadata.timestamp = datetime.now().isoformat()

        data_dict = asdict(save_data)
        data_dict["checksum"] = self._calculate_checksum(data_dict)

        filepath = self._slot_filename(slot)
        try:
            # Write to temp file first, then rename for atomicity
            temp_path = filepath + ".tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data_dict, f, ensure_ascii=False, indent=2)
            os.replace(temp_path, filepath)
            return True
        except (IOError, OSError):
            return False

    def load(self, slot: int) -> Optional[SaveData]:
        """
        Dissolve a memory crystal and restore the world state.
        Returns None if the save is missing or corrupted.
        """
        filepath = self._slot_filename(slot)
        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data_dict = json.load(f)

            # Verify checksum
            stored_checksum = data_dict.get("checksum", "")
            computed_checksum = self._calculate_checksum(data_dict)
            if stored_checksum != computed_checksum:
                return None  # Corrupted save

            metadata = SaveMetadata(**data_dict.pop("metadata"))
            data_dict.pop("checksum", None)
            return SaveData(metadata=metadata, **data_dict)

        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    def delete(self, slot: int) -> bool:
        """Delete a save file. Careful - memories lost cannot be recovered."""
        filepath = self._slot_filename(slot)
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False

    def get_all_metadata(self) -> Dict[int, Optional[SaveMetadata]]:
        """Get metadata for all save slots without loading full data."""
        metadata = {}
        for slot in range(self.MAX_SLOTS + 1):
            filepath = self._slot_filename(slot)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    metadata[slot] = SaveMetadata(**data["metadata"])
                except (json.JSONDecodeError, KeyError, TypeError):
                    metadata[slot] = None
            else:
                metadata[slot] = None
        return metadata

    def slot_exists(self, slot: int) -> bool:
        return os.path.exists(self._slot_filename(slot))

    def any_saves_exist(self) -> bool:
        return any(self.slot_exists(slot) for slot in range(self.MAX_SLOTS + 1))

    def autosave(self, save_data: SaveData) -> bool:
        """Quick save to the autosave slot."""
        save_data.metadata.save_name = "Autosave"
        return self.save(self.AUTOSAVE_SLOT, save_data)
