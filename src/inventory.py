

class Inventory():
    def __init__(self):
        self.items = {}

    def add_item(item):
        if item.item_type not in self.items:
            self.items[item.item_type] = item
        else:
            self.items[item.item_type].quantity += item.quantity

class Item():
    def __init__(self, item_type, quantity):
        self.item_type = item_type
        self.quantity = quantity

