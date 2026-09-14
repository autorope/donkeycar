#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
import pytest
from donkeycar.memory import Memory

class TestMemory(unittest.TestCase):

    def test_setitem_single_item(self):
        mem = Memory()
        mem['myitem'] = 999
        assert mem['myitem'] == 999

    def test_setitem_multi_items(self):
        mem = Memory()
        mem[('myitem1', 'myitem2')] = [888, '999']
        assert mem[('myitem1', 'myitem2')] == [888, '999']

    def test_put_single_item(self):
        mem = Memory()
        mem.put(['myitem'], 999)
        assert mem['myitem'] == 999

    def test_put_single_item_as_tuple(self):
        mem = Memory()
        mem.put(('myitem',), 999)
        assert mem['myitem'] == 999

    def test_put_multi_item(self):
        mem = Memory()
        mem.put(['my1stitem','my2nditem'], [777, '999'])
        assert mem['my1stitem'] == 777
        assert mem['my2nditem'] == '999'

    def test_put_multi_item_as_tuple(self):
        mem = Memory()
        mem.put(('my1stitem','my2nditem'), (777, '999'))
        assert mem['my1stitem'] == 777
        assert mem['my2nditem'] == '999'

    def test_get_multi_item(self):
        mem = Memory()
        mem.put(['my1stitem','my2nditem'], [777, '999'])
        assert mem.get(['my1stitem','my2nditem']) == [777, '999']

    def test_update_item(self):
        mem = Memory()
        mem.put(['myitem'], 888)
        assert mem['myitem'] == 888

        mem.update({'myitem': '111'})
        assert mem['myitem'] == '111'

    def test_get_keys(self):
        mem = Memory()
        mem.put(['myitem'], 888)
        assert list(mem.keys()) == ['myitem']

    def test_get_values(self):
        mem = Memory()
        mem.put(['myitem'], 888)
        assert list(mem.values()) == [888]

    def test_get_iter(self):
        mem = Memory()
        mem.put(['myitem'], 888)

        assert dict(mem.items()) == {'myitem': 888}

    def test_setitem_multi_items_as_list_key(self):
        # a non-tuple sequence of keys must still take its values from the
        # value, not from the keys
        mem = Memory()
        mem[['myitem1', 'myitem2']] = [888, '999']
        assert mem['myitem1'] == 888
        assert mem['myitem2'] == '999'

    def test_remove_item(self):
        mem = Memory()
        mem.put(['myitem'], 888)
        mem.remove(['myitem'])
        assert list(mem.keys()) == []

    def test_remove_multi_items(self):
        mem = Memory()
        mem.put(['my1stitem', 'my2nditem'], [777, '999'])
        mem.remove(['my1stitem', 'my2nditem'])
        assert list(mem.keys()) == []

    def test_remove_leaves_other_items(self):
        mem = Memory()
        mem.put(['my1stitem', 'my2nditem'], [777, '999'])
        mem.remove(['my1stitem'])
        assert list(mem.keys()) == ['my2nditem']

    def test_remove_missing_item_does_not_raise(self):
        # one-shot events are removed by the part that emitted them, but
        # another part may have removed the key first
        mem = Memory()
        mem.remove(['nosuchitem'])
        assert list(mem.keys()) == []

    def test_remove_mixed_present_and_missing_items(self):
        mem = Memory()
        mem.put(['myitem'], 888)
        mem.remove(['nosuchitem', 'myitem'])
        assert list(mem.keys()) == []

    def test_remove_nothing(self):
        mem = Memory()
        mem.put(['myitem'], 888)
        mem.remove([])
        assert list(mem.keys()) == ['myitem']
