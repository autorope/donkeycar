from typing import Any, Callable, Generic, Iterable, Iterator, List, Sized, \
    Tuple, TypeVar, Union

from donkeycar.pipeline.types import TubRecord

# Note: Be careful when re-using `TypeVar`s.
# If you are not-consistent mypy gets easily confused.

X = TypeVar('X', covariant=True)
Y = TypeVar('Y', covariant=True)
XOut = TypeVar('XOut', covariant=True)
YOut = TypeVar('YOut', covariant=True)


# This is a protocol type without explicitly using a `Protocol`
# Using `Protocol` requires Python 3.7
class SizedIterable(Generic[X], Iterable[X], Sized):
    def __init__(self) -> None:
        pass

    def __len__(self) -> int:
        pass

    def __iter__(self) -> Iterator[X]:
        pass


class _BaseTfmIterator(Generic[X, Y, XOut, YOut], Iterator[Tuple[XOut, YOut]]):
    """
    A basic transforming iterator. Do no use this class directly.
    """
    def __init__(self,
                 iterable: 'TfmShallowList') -> None:
        self.iterable = iterable
        self.iterator: Iterator[Union[TubRecord, Tuple[X, Y]]] \
            = iter(self.iterable.iterable)

    def __iter__(self) -> '_BaseTfmIterator[X, Y, XOut, YOut]':
        return self

    def __next__(self) -> Tuple[XOut, YOut]:
        r: Union[TubRecord, Tuple[X, Y]] = next(self.iterator)
        return self.iterable.transform_item(r)


class TfmShallowList(Generic[XOut, YOut], SizedIterable[Tuple[XOut, YOut]]):
    def __init__(self,
                 iterable: Union[List[TubRecord],
                                 'TfmShallowList[XOut, YOut]'],
                 x_transform: Callable[[Any], XOut],
                 y_transform: Callable[[Any], YOut]) -> None:
        self.iterable = iterable
        self.x_transform = x_transform
        self.y_transform = y_transform

    def __len__(self) -> int:
        return len(self.iterable)

    def __iter__(self) -> _BaseTfmIterator[X, Y, XOut, YOut]:
        return _BaseTfmIterator(self)

    def transform_item(self, r: Union[TubRecord, Tuple[X, Y]]) \
            -> Tuple[XOut, YOut]:
        if isinstance(r, tuple) and len(r) == 2:
            x, y = r
            return self.x_transform(x), self.y_transform(y)
        else:
            return self.x_transform(r), self.y_transform(r)


class Pipeline(Generic[X, Y, XOut, YOut], SizedIterable[Tuple[XOut, YOut]]):
    def __init__(self,
                 iterable: Union['Pipeline', List[TubRecord]],
                 x_transform: Callable[[Any], XOut],
                 y_transform: Callable[[Any], YOut]) -> None:
        self.iterable = iterable
        self.x_transform = x_transform
        self.y_transform = y_transform

    def __iter__(self) -> Iterator[Tuple[XOut, YOut]]:
        for record in self.iterable:
            if isinstance(record, tuple):
                x, y = record
                yield self.x_transform(x), self.y_transform(y)
            else:
                yield self.x_transform(record), self.y_transform(record)

    def __len__(self) -> int:
        return len(self.iterable)

