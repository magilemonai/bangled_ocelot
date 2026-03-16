"""
Ma no Kuni - Inventory System

Everything Aoi carries has weight - not just physical weight,
but spiritual resonance. A grandmother's hairpin might weigh nothing
in grams but carry the weight of decades of love.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict


class ItemCategory(Enum):
    """Categories of items that exist in both worlds."""
    MATERIAL = auto()          # Basic crafting materials
    CONSUMABLE = auto()        # Tea blends, healing items
    KEY_ITEM = auto()          # Story-critical items
    EQUIPMENT = auto()         # Wearable items
    SPIRIT_ITEM = auto()       # Items from the spirit world
    OFUDA = auto()             # Spirit talismans
    CHARM = auto()             # Spirit charms and accessories
    GIFT = auto()              # Items for relationship building
    MEMORY = auto()            # Crystallized memories
    CURIOUS = auto()           # Products of failed/experimental crafting
    LORE = auto()              # Lore fragments, readable items


class ItemRarity(Enum):
    """How rare an item is, also reflects spiritual significance."""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    PRECIOUS = "precious"     # Not 'legendary' - things are precious because of meaning
    SINGULAR = "singular"      # One of a kind


class ElementAffinity(Enum):
    """Elemental affinities tied to Japanese concepts."""
    NONE = "none"
    FIRE = "fire"             # 火
    WATER = "water"           # 水
    WIND = "wind"             # 風
    EARTH = "earth"           # 土
    LIGHT = "light"           # 光
    SHADOW = "shadow"         # 影
    MEMORY = "memory"         # 記憶
    SILENCE = "silence"       # 静寂


@dataclass
class Item:
    """A single item in the world."""
    id: str
    name: str
    description: str
    category: ItemCategory
    rarity: ItemRarity = ItemRarity.COMMON
    element: ElementAffinity = ElementAffinity.NONE
    spirit_resonance: float = 0.0    # 0-1, how spirit-touched
    stack_size: int = 99
    value: int = 0                    # Base trade value
    usable: bool = False
    equippable: bool = False
    giftable: bool = True
    lore_text: str = ""              # Extended lore, revealed over time
    spirit_description: str = ""      # How the item looks in spirit vision
    icon: str = ""

    # Effects when used
    use_effects: Dict = field(default_factory=dict)

    # Crafting properties
    craft_tags: List[str] = field(default_factory=list)


@dataclass
class InventorySlot:
    """A slot in the inventory holding items."""
    item: Item
    quantity: int = 1
    is_new: bool = True  # Highlight newly acquired items
    is_favorite: bool = False

    @property
    def can_add(self) -> bool:
        return self.quantity < self.item.stack_size


@dataclass
class Equipment:
    """Aoi's equipment loadout."""
    # Equipment slots
    accessory_1: Optional[Item] = None   # Spirit charms
    accessory_2: Optional[Item] = None
    ofuda: Optional[Item] = None         # Active talisman
    keepsake: Optional[Item] = None      # A personal item that grows with Aoi

    def get_all_equipped(self) -> List[Item]:
        return [
            item for item in [
                self.accessory_1, self.accessory_2,
                self.ofuda, self.keepsake
            ] if item is not None
        ]

    def total_spirit_resonance(self) -> float:
        return sum(item.spirit_resonance for item in self.get_all_equipped())


class Inventory:
    """
    Aoi's bag. A simple canvas tote that grandmother gave them.
    It shouldn't hold as much as it does. Perhaps the bag
    has a small spirit of its own.
    """

    def __init__(self, max_slots: int = 99):
        self.slots: Dict[str, InventorySlot] = {}
        self.max_slots = max_slots
        self.equipment = Equipment()
        self.money: int = 500  # Starting yen
        self.key_items: List[Item] = []  # Key items stored separately

    def add_item(self, item: Item, quantity: int = 1) -> bool:
        """
        Add an item to inventory. Returns True if successful.
        """
        if item.category == ItemCategory.KEY_ITEM:
            self.key_items.append(item)
            return True

        if item.id in self.slots:
            slot = self.slots[item.id]
            can_add = min(quantity, slot.item.stack_size - slot.quantity)
            slot.quantity += can_add
            slot.is_new = True
            return can_add == quantity

        if len(self.slots) >= self.max_slots:
            return False

        self.slots[item.id] = InventorySlot(item=item, quantity=quantity)
        return True

    def remove_item(self, item_id: str, quantity: int = 1) -> bool:
        """Remove items. Returns True if successful."""
        if item_id not in self.slots:
            return False

        slot = self.slots[item_id]
        if slot.quantity < quantity:
            return False

        slot.quantity -= quantity
        if slot.quantity <= 0:
            del self.slots[item_id]
        return True

    def has_item(self, item_id: str, quantity: int = 1) -> bool:
        """Check if we have enough of an item."""
        if item_id in self.slots:
            return self.slots[item_id].quantity >= quantity
        return any(ki.id == item_id for ki in self.key_items)

    def get_items_by_category(self, category: ItemCategory) -> List[InventorySlot]:
        """Get all items of a category."""
        return [
            slot for slot in self.slots.values()
            if slot.item.category == category
        ]

    def get_giftable_items(self) -> List[InventorySlot]:
        """Get items that can be given as gifts."""
        return [
            slot for slot in self.slots.values()
            if slot.item.giftable and slot.item.category != ItemCategory.KEY_ITEM
        ]

    def get_spirit_resonance_items(self, min_resonance: float = 0.5) -> List[InventorySlot]:
        """Get items with high spirit resonance."""
        return [
            slot for slot in self.slots.values()
            if slot.item.spirit_resonance >= min_resonance
        ]

    def mark_all_seen(self) -> None:
        """Mark all items as no longer new."""
        for slot in self.slots.values():
            slot.is_new = False

    @property
    def total_items(self) -> int:
        return sum(slot.quantity for slot in self.slots.values())

    @property
    def slots_used(self) -> int:
        return len(self.slots)

    @property
    def is_full(self) -> bool:
        return self.slots_used >= self.max_slots

    def equip(self, item_id: str, slot_name: str) -> Optional[Item]:
        """
        Equip an item. Returns the previously equipped item, if any.
        """
        if item_id not in self.slots:
            return None

        item = self.slots[item_id].item
        if not item.equippable:
            return None

        old_item = getattr(self.equipment, slot_name, None)
        setattr(self.equipment, slot_name, item)
        self.remove_item(item_id, 1)

        if old_item:
            self.add_item(old_item, 1)

        return old_item
