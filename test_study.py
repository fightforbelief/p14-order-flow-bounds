import itertools
import unittest
from study import SETTINGS, compatible


class BoundsTest(unittest.TestCase):
    def test_all_partitions(self):
        # Every tape over two directions and two prices including repeated
        # stamps, across-bucket edges and a chain longer than the allowed span.
        times = [0, 0, 999, 1000, 13000, 21000]
        for tape in itertools.product(itertools.product((-1, 1), (4, 5)), repeat=len(times)):
            rows = [(*r, t) for r, t in zip(tape, times)]
            switches = sum(a[0] != b[0] for a, b in zip(rows, rows[1:]))
            for kind in SETTINGS:
                start = 0
                anchors = [0]
                for i in range(1, len(rows)):
                    if not compatible(kind, times[start], rows[i-1], rows[i]):
                        anchors.append(i)
                        start = i
                lower = [sum(rows[i][0] == s for i in anchors) for s in (-1, 1)]
                upper = [sum(r[0] == s for r in rows) for s in (-1, 1)]
                seen = set()
                for bits in itertools.product((0, 1), repeat=len(rows)-1):
                    cuts = [0] + [i+1 for i, b in enumerate(bits) if b] + [len(rows)]
                    valid = True
                    for a, b in zip(cuts, cuts[1:]):
                        block = rows[a:b]
                        if kind == "span20ms":
                            valid &= block[-1][2]-block[0][2] <= 20000
                        else:
                            scale = 1 if kind == "native" else 1000
                            valid &= block[-1][2]//scale == block[0][2]//scale
                        for (s,p,t),(v,q,u) in zip(block,block[1:]):
                            valid &= s == v and ((q-p)*s > 0 or (kind == "span20ms" and q == p and u != t))
                    if valid:
                        signs = [rows[i][0] for i in cuts[:-1]]
                        self.assertEqual(sum(a != b for a,b in zip(signs,signs[1:])), switches)
                        seen.add((signs.count(-1), signs.count(1)))
                self.assertEqual(seen, set(itertools.product(*(range(a,b+1) for a,b in zip(lower,upper)))))


if __name__ == "__main__":
    unittest.main()
