import unittest
import scryfall
import os
import unittest.mock

class TestCacheLayer(unittest.TestCase):
    def test_miss_then__hit(self):
        try:
            os.remove('emptyfile')
        except:
            pass
        with unittest.mock.patch.object(
                scryfall.scrython.cards,
                'Named',
                return_value = type("thing", (),
                    {'name' : lambda x: 'Opt',
                     'oracle_text' : lambda x: 'bla',
                     'mana_cost' : lambda x: '{U}',
                     'type_line' : lambda x: 'Instant',
                    })()) as p:
            with scryfall.ScrythonCacher('emptyfile') as cacher:
                ret = cacher.cardnamed('Opt')
                self.assertEqual(ret['name'], 'Opt')

        with scryfall.ScrythonCacher('emptyfile') as cacher:
            ret = cacher.cardnamed('Opt')
            self.assertEqual(ret['name'], 'Opt')

        os.remove('emptyfile')

if __name__ == '__main__':
    unittest.main()
