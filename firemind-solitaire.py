# /usr/bin/python

"""
TODO:
    * Thousand-Year Storm
    Arbitrary instants and sorceries

"""

import scrython
import copy

CMD_ADD = "add"
CMD_CAST = "cast"
CMD_COPY = "copy"

class Permanent(object):
    def __init__(self, game):
        self.game = game

    def oncast(self, cast_obj):
        pass

    def ondraw(self):
        pass

class ThousandYearStorm(Permanent):
    def oncast(self, cast_obj):
        prior_instants = [spell for spell in self.game.prior_casts if
                (spell.typ == "Instant" or spell.typ == "Sorcery")] # TODO: and you cast it
        for i in range(len(prior_instants)):
            self.game.copy_stackobject(cast_obj)

class Mindmoil(Permanent):
    def oncast(self, cast_obj):
        self.game.make_stackobject("Put your hand on the bottom of your library, then draw that many cards", typ="Triggered Ability")

def NivMizzetParun(Permanent):
    def ondraw(self):
        self.game.make_stackobject("Deal 1 damage to any target")

PermanentAbilities = {
    "Thousand-Year Storm" : ThousandYearStorm,
    "Mindmoil" : Mindmoil,
    "Arjun, the Shifting Flame" : Mindmoil,
    "Niv-Mizzet, Parun" : NivMizzetParun
}

class Game(object):
    def __init__(self):
        self.prior_casts = set() # set of StackObjects that were cast
        self.mana = 0
        self.stack = []
        self.stackobjects = {}
        self.permanents = set()

    def __Counter():
        i = 0
        while True:
            yield i
            i += 1

    IdGenerator = __Counter()

    class StackObject(object):
        def __init__(self, id, name, typ="Instant", is_copy=False, on_resolution=[]):
            try:
                card = scrython.cards.Named(fuzzy=name)
            except:
                card = None

            if not card:
                self.name = name
                self.typ = typ
                self.on_resolution = on_resolution
            else:
                self.name = card.name()
                self.typ = card.type_line()
                self.on_resolution = on_resolution + [card.oracle_text()]
            self.is_copy = is_copy
            self.id = id

        def __repr__(self):
            return "{0} {1} {2}{3}".format(
                    self.id,
                    self.name,
                    self.typ,
                    '*' if self.is_copy else '')

    def render(self):
        if self.stack:
            print("CURRENT STACK:")
            for i in self.stack:
                print('\t', i)
        else:
            print("THE STACK IS EMPTY")
        print("MANA REMAINING:", self.mana)

    def make_stackobject(self, *args, **kwargs):
        id = next(self.IdGenerator)
        obj = self.StackObject(id, *args, **kwargs)
        self.stackobjects[id] = obj
        self.stack.append(obj)
        return obj

    def copy_stackobject(self, id):
        newId = next(self.IdGenerator)
        try:
            template = self.stackobjects[id]
        except:
            if isinstance(id, self.StackObject):
                template = id
            else:
                # if it uniquely specifies a name, that's OK I guess
                matches = [obj for obj in self.stack if obj.name.lower() == id.lower()]
                if len(matches):
                    template = matches[0]
                else:
                    print("I DON'T KNOW WHAT YOU JUST TRIED TO COPY")
                    return
        assert isinstance(template, self.StackObject)
        obj = copy.deepcopy(template)
        obj.id = newId
        obj.is_copy = True
        self.stackobjects[newId] = obj
        self.stack.append(obj)
        return obj

    def resolve(self):
        effect = self.stack[-1]
        self.stack.pop()
        print("RESOLVES: {0}".format(effect))
        for on_resolution in effect.on_resolution:
            print('\t', on_resolution)
        if effect.name in PermanentAbilities:
            self.permanents.add(PermanentAbilities[effect.name](self))

    def process_instruction(self, instruction):
        cmd, other = instruction.split(maxsplit=1)
        if cmd == "add":
            self.mana += int(other)
        elif cmd == "cast":
            name = other
            stackobj = self.make_stackobject(name)
            for listener in self.permanents:
                listener.oncast(stackobj)
            self.prior_casts.add(stackobj)
        elif cmd == "copy":
            id = other
            self.copy_stackobject(id)
        elif cmd == "effect":
            self.make_stackobject(other, typ="Effect")
        elif cmd == "draw":
            for listener in self.permanents:
                for i in range(int(other)):
                    listener.ondraw()

    def run(self):
        while True:
            inp = (yield)
            if not inp:
                # resolve spell
                if self.stack:
                    self.resolve()
                else:
                    return
            else:
                self.process_instruction(inp)
            self.render()

g = Game()
runner = g.run()
runner.send(None)

try:
    while True:
        inp = input('>>> ')
        runner.send(inp)
except StopIteration:
    pass

