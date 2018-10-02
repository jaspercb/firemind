# /usr/bin/python

"""
TODO:
    * Spell targeting
    * Refactor permanent objects, or at the very least display them
    * Add more neat-o interactions
    * Add mana tracking (plus electromancer)
        * Smart mana spending?
    * Build in resolution effects of more spells

"""

import scrython
import re
import math
import copy
import curses

CMD_ADDMANA = "addmana"
CMD_CAST = "cast"
CMD_ENEMYCAST = "enemycast"
CMD_COPY = "copy"
CMD_EFFECT = "effect"
CMD_DRAW = "draw"
CMD_DISCARD = "discard"
CMD_PUTINLIBRARY = "putinlibrary"
CMD_MINDMOIL = "mindmoil"
CMD_ECHO = "echo"
CMD_PASSPRIORITY = "passpriority"
CMD_PASSUNTILCLEAR = "passuntilclear"

OWNER_YOU = "You"
OWNER_OTHER = "Someone else"

class Permanent(object):
    def __init__(self, game):
        self.game = game

    def oncast(self, cast_obj):
        pass

    def ondraw(self):
        pass

class ThousandYearStorm(Permanent):
    def oncast(self, spell):
        if spell.owner == OWNER_YOU and spell.typ in ("Instant", "Sorcery"):
            prior_instants = [spell for spell in self.game.prior_casts if spell.owner == OWNER_YOU and
                spell.typ in ("Instant", "Sorcery")]
            for i in range(len(prior_instants)):
                self.game.copy_stackobject(spell)

class Mindmoil(Permanent):
    def oncast(self, cast_obj):
        self.game.make_stackobject("Mindmoil trigger", description="Put your hand on the bottom of your library, then draw that many cards", typ="Triggered Ability", on_resolution=["mindmoil"])

class NivMizzetParun(Permanent):
    def oncast(self, cast_obj):
        if cast_obj.typ in ("Instant", "Sorcery"):
            self.game.make_stackobject("Draw a card (Niv Mizzet)", typ="Triggered Ability", on_resolution=["draw 1"])

    def ondraw(self):
        self.game.make_stackobject("Deal 1 damage to any target (Niv-Mizzet, Parun)", typ="Triggered Ability")

PermanentAbilities = {
    "Thousand-Year Storm" : ThousandYearStorm,
    "Mindmoil" : Mindmoil,
    "Arjun, the Shifting Flame" : Mindmoil,
    "Niv-Mizzet, Parun" : NivMizzetParun
}

SpellEffects = {
    "Opt" : ["draw 1"],
    "Brainstorm" : ["draw 3", "putinlibrary 2"],
    "Pyretic Ritual" : ["addmana 0 3 0"],
    "Frantic Search" : ["draw 2", "discard 2"], # TODO: untap 3 lands
}

class Game(object):
    def __init__(self):
        self.prior_casts = set() # set of StackObjects that were cast
        self.mana = [0, 0, 0] # colorless, blue, red
        self.stack = []
        self.stackobjects = {}
        self.permanents = set()
        self.cards_in_hand = 0
        self.cards_in_library = 100

    def __Counter():
        i = 0
        while True:
            yield i
            i += 1

    IdGenerator = __Counter()

    class StackObject(object):
        def __init__(self, id, name, owner=OWNER_YOU, description="", typ="Instant", scryfall=False, is_copy=False, on_resolution=[]):
            if scryfall:
                try:
                    card = scrython.cards.Named(fuzzy=name)
                except:
                    card = None
            else:
                card = None

            if not card:
                self.name = name
                self.typ = typ
                self.description = description
                self.manacost = None
            else:
                self.name = card.name().encode('ascii', 'ignore').decode('ascii')
                self.typ = card.type_line().encode('ascii', 'ignore').decode('ascii')
                self.description = card.oracle_text().encode('ascii', 'ignore').decode('ascii')
                self.manacost = card.mana_cost()

            self.on_resolution = SpellEffects.get(self.name, []) + on_resolution
            self.owner = owner
            self.is_copy = is_copy
            self.id = id

        def __repr__(self):
            return "{0} {1} {2}{3}".format(
                    self.id,
                    self.name,
                    self.typ,
                    '*' if self.is_copy else '')

    def make_stackobject(self, *args, **kwargs):
        id = next(self.IdGenerator)
        obj = self.StackObject(id, *args, **kwargs)
        self.stackobjects[id] = obj
        self.stack.append(obj)
        return obj
    
    def log(self, message):
        for listener in self.listeners:
            listener.send(message)

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
                    self.log("I DON'T KNOW WHAT YOU JUST TRIED TO COPY")
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
        self.log("{0} resolves. ({1})".format(effect.name, effect.description))
        for on_resolution in effect.on_resolution:
            self.process_instruction(on_resolution)
        if effect.name in PermanentAbilities:
            self.permanents.add(PermanentAbilities[effect.name](self))

    def draw(self, ncards):
        self.cards_in_hand += ncards
        self.cards_in_library -= ncards
        for listener in self.permanents:
            for i in range(ncards):
                listener.ondraw()


    def process_instruction(self, instruction):
        if ' ' in instruction:
            cmd, other = instruction.split(maxsplit=1)
        else:
            cmd = instruction
            other = None

        if cmd.lower() == CMD_ADDMANA:
            self.mana = list(map(sum, zip(self.mana, map(int, other.split()))))
        elif cmd.lower() == CMD_CAST:
            name = other
            stackobj = self.make_stackobject(name, scryfall=True, owner=OWNER_YOU)
            # spend mana: satisfy color requirements, then spend colorless, then spend what we have more of
            if stackobj.manacost:
                redreq = stackobj.manacost.count('{R}')
                bluereq = stackobj.manacost.count('{U}')
                otherre = re.match("\{[0-9]\}", stackobj.manacost)

                self.mana[1] -= redreq
                self.mana[2] -= bluereq
                if otherre:
                    for i in range(int(otherre.group()[1:-1])):
                        if self.mana[0] > 0:
                            self.mana[0] -= 1
                        elif self.mana[1] > self.mana[2]:
                            self.mana[1] -= 1
                        else:
                            self.mana[2] -= 1
                
            for listener in self.permanents:
                listener.oncast(stackobj)
            self.prior_casts.add(stackobj)
        elif cmd.lower() == CMD_ENEMYCAST:
            name = other
            stackobj = self.make_stackobject(name, scryfall=True, owner=OWNER_OTHER)
            for listener in self.permanents:
                listener.oncast(stackobj)
            self.prior_casts.add(stackobj)
        elif cmd.lower() == CMD_COPY:
            id = other
            self.copy_stackobject(id)
        elif cmd.lower() == CMD_EFFECT:
            self.make_stackobject(other, typ="Effect")
        elif cmd.lower() == CMD_DRAW:
            ncards = int(other)
            self.draw(ncards)
        elif cmd.lower() == CMD_PUTINLIBRARY:
            ncards = int(other)
            self.cards_in_hand -= ncards
            self.cards_in_library += ncards
        elif cmd.lower() == CMD_DISCARD:
            ncards = int(other)
            self.cards_in_hand -= ncards
        elif cmd.lower() == CMD_MINDMOIL:
            ncards = self.cards_in_hand
            self.cards_in_hand -= ncards
            self.cards_in_library += ncards
            self.draw(ncards)
        elif cmd.lower() == CMD_ECHO:
            self.log(other)
        elif cmd.lower() == CMD_PASSPRIORITY:
            self.resolve()
        elif cmd.lower() == CMD_PASSUNTILCLEAR:
            while self.stack:
                self.resolve()

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


class GameDisplay():
    def __init__(self, stdscr, game):
        self.eventlog = []
        self.game = game
        game.listeners = [self]

        # screen setup
        self.screen = stdscr
        y, x = self.screen.getbegyx()
        h, w = self.screen.getmaxyx()
        halfw = int(w/2)

        self.inputscreen = curses.newwin(1, w, y, x)
        self.statusline = curses.newwin(1, w, y+1, x)
        self.stackscreenborder = curses.newwin(h, halfw, y+2, x)
        self.stackscreenborder.border()
        self.stackscreenborder.noutrefresh()
        self.stackscreen = curses.newwin(h-2, halfw-2, y + 3, x+1)

        self.logscreenborder = curses.newwin(h, w-halfw, y + 2, x + halfw - 1)
        self.logscreenborder.border()
        self.logscreenborder.noutrefresh()
        self.logscreen = curses.newwin(h - 2, w-halfw - 2, y + 3, x + halfw)

    def send(self, message):
        if message:
            self.eventlog.append(message)

    def render_stack(self):
        self.stackscreen.clear()
        for i, stackelement in enumerate(self.game.stack):
            self.stackscreen.addstr(i, 0, str(stackelement))
        self.stackscreen.noutrefresh()

    def render_event_log(self):
        self.logscreen.clear()
        lineno = 0
        maxnlines, linewidth = self.logscreen.getmaxyx()
        for logmsg in reversed(self.eventlog):
            nlines = math.ceil(len(str(logmsg))/linewidth)
            for i in range(nlines):
                if lineno + i + 1 < maxnlines:
                    self.logscreen.addstr(lineno + i, 0, str(logmsg[linewidth*i:linewidth*(i+1)]))
            if lineno + nlines + 1 < maxnlines:
                self.logscreen.addstr(lineno + nlines, 0, '-'*linewidth)
            lineno += nlines + 1
        self.logscreen.noutrefresh()

    def render_statusline(self):
        self.statusline.clear()
        self.statusline.addstr(0, 0, "Mana: ")
        self.statusline.addstr(0, 7, "{0}".format(self.game.mana[0]))
        self.statusline.addstr(0, 11, "R{0}".format(self.game.mana[1]), curses.color_pair(1))
        self.statusline.addstr(0, 15, "B{0}".format(self.game.mana[2]), curses.color_pair(2))
        self.statusline.addstr(0, 20, "{ncards} cards in hand".format(ncards=self.game.cards_in_hand))
        self.statusline.noutrefresh()

    def run(self):
        runner = self.game.run()
        runner.send(None) # start consuming generator
        runner.send("addmana 4 2 2")
        runner.send("cast Thousand-Year Storm")
        runner.send(CMD_PASSUNTILCLEAR)
        runner.send("cast Opt")
        runner.send("cast Lightning Bolt")
        try:
            while True:
                self.render_stack()
                self.render_event_log()
                self.render_statusline()
                cmd = self.inputscreen.getstr(0, 0).decode() # b"" -> ""
                self.inputscreen.clear()
                self.inputscreen.noutrefresh()
                curses.doupdate()
                runner.send(str(cmd))
        except StopIteration:
            pass

def main(stdscr):
    curses.echo()
    curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_BLUE, curses.COLOR_BLACK)
    g = Game()
    gDisplay = GameDisplay(stdscr, g)
    gDisplay.run()

curses.wrapper(main)
