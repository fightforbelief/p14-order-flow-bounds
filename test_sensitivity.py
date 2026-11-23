import itertools
import unittest
from fractions import Fraction
from summarize import join_asymmetry


class SensitivityTest(unittest.TestCase):
    def test_against_all_pairs(self):
        cases = [(d, s, a) for d in range(2, 8) for s in range(1, d)
                 for a in range(1, d-s+1)]
        for (dw, sw, aw), (dl, sl, al) in itertools.product(cases, repeat=2):
            if sw * dl > sl * dw:
                continue
            def counts(d, s, a):
                return dict(records=d+1, segments=1, switches=s, native_buy=d+1-a, native_sell=0)
            val, jw, jl = join_asymmetry(counts(dw,sw,aw), counts(dl,sl,al), "native")
            choices = [max(0, Fraction(i, aw)-Fraction(j, al))
                       for i in range(aw+1) for j in range(al+1)
                       if sw*(dl-j) >= sl*(dw-i)]
            self.assertEqual(val, float(min(choices)) if choices else None)
            if val is not None:
                self.assertGreaterEqual(sw*(dl-jl), sl*(dw-jw))
