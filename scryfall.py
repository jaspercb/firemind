"""
A caching layer around Scrython to avoid duplicate calls.
Cache persists over execution by storing state in a json structure.
"""

import scrython
import json

class ScrythonCacher:
    def __init__(self, filename="cachefile.json"):
        self.filename = filename

    def __enter__(self):
        try:
            with open(self.filename, 'r') as f:
                self.jsondata = json.loads(f.read())
        except OSError:
            self.jsondata = {
                'fuzzynames' : {},
                'cardsbyname' : {},
            }
        return self

    def cardnamed(self, cardname):
        """ Returns a JSON object with data associated with that card """
        if cardname in self.jsondata['fuzzynames']:
            cardname = self.jsondata['fuzzynames'][cardname]

        if cardname not in self.jsondata['cardsbyname']:
            card = scrython.cards.Named(fuzzy=cardname)
            self.jsondata['fuzzynames'][cardname] = card.name()
            self.jsondata['cardsbyname'][card.name()] = {
                'name' : card.name(),
                'mana_cost' : card.mana_cost(),
                'oracle_text' : card.oracle_text(),
                'type_line' : card.type_line(),
            }
        return self.jsondata['cardsbyname'][self.jsondata['fuzzynames'][cardname]]

    def __exit__(self, exception_type, exception_value, traceback):
        with open(self.filename, 'w') as f:
            f.write(json.dumps(self.jsondata))

