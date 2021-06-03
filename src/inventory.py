
import yaml

with open('data/items.yaml') as item_data:
    s_item_data = yaml.safe_load(item_data)

class Inventory:
    def __init__(self, entity=False):
        self.items = []
        self.size = 9

        self.entity = entity

    def has_item_type(self, item_type):
        for i in range(len(self.items)):
            if self.items[i].item_type == item_type:
                return i
        return False

    def add_item(self, item):
        item_index = self.has_item_type(item.item_type)
        if item_index is not False and is_stackable(item.item_type):
            self.items[item_index].quantity += item.quantity
        else:
            self.items.append(item)

    def remove_item(self, item_index, drop):
        if drop and self.entity:
            self.entity.drop_item(self.items[item_index])
        now = self.items[:item_index]
        if item_index < len(self.items) - 1:
            now += self.items[item_index+1:]
        self.items = now

    def reduce_item(self, item_index, amount = 1):
        if self.items[item_index].quantity <= amount:
            self.remove_item(item_index, False)
            return

        self.items[item_index].quantity -= amount


    def use_item(self, item_index):
        item = self.items[item_index]
        data = s_item_data[item.item_type]
        if 'usage' not in data:
            self.remove_item(item_index, True) # Drop it
            return

        if data['usage'] == 'equip':
            item.equipped = not item.equipped
            if self.entity:
                self.entity.equipment_update()
        elif data['usage'] == 'consumable':
            if self.entity:
                for effect in data['effects']:
                    self.entity.instant_effect(effect)
            self.reduce_item(item_index)

    def get_all_equipped(self):
        equipped = []
        for i in self.items:
            if not i.equipped:
                continue
            equipped.append(i)
        return equipped

class Item:
    def __init__(self, item_type='generic', quantity=1, icon='no_img'):
        self.item_type = item_type
        self.quantity = quantity
        self.icon = icon
        if item_type in s_item_data:
            if 'icon' in s_item_data[item_type]:
                self.icon = s_item_data[item_type]['icon']
        self.equipped = False

def item_from_pickup(pickup):
    img_name = pickup.img_name
    subtype = pickup.subtype
    if pickup.subtype == 'moni_pile':
        subtype = 'moni'
        img_name = 'moni'

    quantity = 1
    if hasattr(pickup, 'quantity'):
        quantity = pickup.quantity

    return Item(subtype, quantity, subtype)

def is_stackable(item_type):
    return s_item_data[item_type]['stackable']

def get_item_data(item_type):
    if item_type not in s_item_data:
        print("No item data for " + str(item_type))
        return False
    return s_item_data[item_type]
