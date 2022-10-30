class Selectable():
    def __init__(self,display_name,starting_letter,short_name,type):
        self.display_name = display_name
        self.starting_letter = starting_letter
        self.short_name = short_name
        self.type = type

class SelectableFilter():
    def __init__(self,display_names,short_names,type):
        self.display_names = display_names
        self.short_names = short_names
        self.type = type
