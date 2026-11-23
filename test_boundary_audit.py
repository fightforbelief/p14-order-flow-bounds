from fractions import Fraction
from itertools import product
from math import comb
import unittest

from boundary_audit import audit_size, reversal_radius
from full_days import audit_hour


class BoundaryTests(unittest.TestCase):
    def test_witness_by_enumeration(self):
        for dw, dl, sw, sl, cap in product(range(1,9),range(1,9),range(1,9),range(1,9),range(5)):
            if sw > dw or sl > dl or sw*dl > sl*dw:
                continue
            possible = [i+j for i in range(dw-sw+1) for j in range(cap+1)
                        if sw*(dl+j) >= sl*(dw-i)]
            self.assertEqual(reversal_radius(dw,sw,dl,sl,cap), min(possible))

    def test_cost_exact(self):
        for total in range(1,48):
            for radius in range(1,total+1):
                n = next(k for k in range(total+1)
                         if Fraction(comb(total-radius,k),comb(total,k)) <= Fraction(1,20))
                self.assertEqual(audit_size(total,radius), n)

    def test_labelled_hour(self):
        def msg(i,p,t,oid):
            return dict(trade_id=i, side="sell", price=str(p),time=f"2025-03-01T00:00:{t}Z",taker_order_id=oid)
        rows = [msg(1,1,"00","a"),msg(2,1,"00","a"),msg(3,2,"00","b"),msg(4,3,"02","b"),msg(6,4,"02","b")]
        c = audit_hour([*rows,rows[2]],"2025-03-01",0)
        self.assertEqual([c[k] for k in ("fills","duplicates","records","segments","orders",
                                            "native_eligible","native_false_join","native_missed_join")],
                         [5,1,4,2,3,1,1,1])
