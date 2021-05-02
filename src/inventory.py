

class Inventory():
    def __init__(self):
        self.items = {}

    def add_item(self, item):
        if item.item_type not in self.items:
            self.items[item.item_type] = item
        else:
            self.items[item.item_type].quantity += item.quantity

class Item():
    def __init__(self, item_type='generic', quantity=1, icon='no_img'):
        self.item_type = item_type
        self.quantity = quantity
        self.icon = icon

def item_from_pickup(pickup):
    item = Item(pickup.subtype, 1, pickup.img_name)
    if hasattr(pickup, 'quantity'):
        item.quantity = pickup.quantity

    return item

