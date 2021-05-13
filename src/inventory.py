

class Inventory:
    def __init__(self):
        self.items = {}
        self.size = 9

        self.sorted = []

    def add_item(self, item):
        if item.item_type not in self.items:
            self.items[item.item_type] = item
            self.sorted.append(item.item_type)
        else:
            self.items[item.item_type].quantity += item.quantity

class Item:
    def __init__(self, item_type='generic', quantity=1, icon='no_img'):
        self.item_type = item_type
        self.quantity = quantity
        self.icon = icon
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

