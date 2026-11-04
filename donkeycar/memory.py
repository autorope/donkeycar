#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jun 25 11:07:48 2017

@author: wroscoe
"""

from collections.abc import ItemsView, Iterable, KeysView, Sequence, ValuesView
from typing import Any


class Memory:
    """
    A convenience class to save key/value pairs.
    """

    def __init__(self, *args: Any, **kw: Any) -> None:
        self.d: dict[str, Any] = {}

    def __setitem__(self, key: str | Sequence[str], value: Any) -> None:
        if isinstance(key, str):
            self.d[key] = value
        else:
            for i, k in enumerate(key):
                self.d[k] = value[i]

    def __getitem__(self, key: str | tuple[str, ...]) -> Any:
        if isinstance(key, tuple):
            return [self.d[k] for k in key]
        return self.d[key]

    def update(self, new_d: dict[str, Any]) -> None:
        '''
        update memory with values from a dictionary
        '''
        self.d.update(new_d)

    def put(self, keys: Sequence[str], inputs: Any) -> None:
        if len(keys) > 1:
            for i, key in enumerate(keys):
                try:
                    self.d[key] = inputs[i]
                except IndexError as e:
                    error = str(e) + ' issue with keys: ' + str(key)
                    raise IndexError(error)

        else:
            self.d[keys[0]] = inputs

    def get(self, keys: Sequence[str]) -> list[Any]:
        result = [self.d.get(k) for k in keys]
        return result

    def remove(self, keys: Iterable[str]) -> None:
        '''
        Remove all the keys in the given list.
        Keys that are not in memory are ignored, so it is safe to remove
        a key that another part has already removed.
        '''
        for key in keys:
            self.d.pop(key, None)

    def keys(self) -> KeysView[str]:
        return self.d.keys()

    def values(self) -> ValuesView[Any]:
        return self.d.values()

    def items(self) -> ItemsView[str, Any]:
        return self.d.items()
