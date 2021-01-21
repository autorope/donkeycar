
from typing import (Any, Callable, Generic, Iterable, Iterator, List, Sized, Tuple, TypeVar)

from donkeycar.pipeline.types import TubRecord

# Note: Be careful when re-using `TypeVar`s.
# If you are not-consistent mypy gets easily confused.

R = TypeVar('R', covariant=True)
X = TypeVar('X', covariant=True)
Y = TypeVar('Y', covariant=True)
XOut = TypeVar('XOut', covariant=True)
YOut = TypeVar('YOut', covariant=True)


class SizedIterator(Generic[X], Iterator[X], Sized):
    def __init__(self) -> None:
        # This is a protocol type without explicitly using a `Protocol`
        # Using `Protocol` requires Python 3.7
        pass


class TubSeqIterator(SizedIterator[TubRecord]):
    def __init__(self, records: List[TubRecord]) -> None:
        self.records = records or list()
        self.current_index = 0

    def __len__(self):
        return len(self.records)

    def __iter__(self) -> SizedIterator[TubRecord]:
        return TubSeqIterator(self.records)

    def __next__(self):
        if self.current_index >= len(self.records):
            raise StopIteration('No more records')

        record = self.records[self.current_index]
        self.current_index += 1
        return record

    next = __next__


class TfmIterator(Generic[R, XOut, YOut],  SizedIterator[Tuple[XOut, YOut]]):
    def __init__(self,
                 iterable: Iterable[R],
                 x_transform: Callable[[R], XOut],
                 y_transform: Callable[[R], YOut]) -> None:

        self.iterable = iterable
        self.x_transform = x_transform
        self.y_transform = y_transform
        self.iterator = BaseTfmIterator_(
            iterable=self.iterable, x_transform=self.x_transform, y_transform=self.y_transform)

    def __len__(self):
        return len(self.iterator)

    def __iter__(self) -> SizedIterator[Tuple[XOut, YOut]]:
        return BaseTfmIterator_(
            iterable=self.iterable, x_transform=self.x_transform, y_transform=self.y_transform)

    def __next__(self):
        return next(self.iterator)


class TfmTupleIterator(Generic[X, Y, XOut, YOut],  SizedIterator[Tuple[XOut, YOut]]):
    def __init__(self,
                 iterable: Iterable[Tuple[X, Y]],
                 x_transform: Callable[[X], XOut],
                 y_transform: Callable[[Y], YOut]) -> None:

        self.iterable = iterable
        self.x_transform = x_transform
        self.y_transform = y_transform
        self.iterator = BaseTfmIterator_(
            iterable=self.iterable, x_transform=self.x_transform, y_transform=self.y_transform)

    def __len__(self):
        return len(self.iterator)

    def __iter__(self) -> SizedIterator[Tuple[XOut, YOut]]:
        return BaseTfmIterator_(
            iterable=self.iterable, x_transform=self.x_transform, y_transform=self.y_transform)

    def __next__(self):
        return next(self.iterator)


class BaseTfmIterator_(Generic[XOut, YOut],  SizedIterator[Tuple[XOut, YOut]]):
    '''
    A basic transforming iterator.
    Do no use this class directly.
    '''

    def __init__(self,
                 # Losing a bit of type safety here for a common implementation
                 iterable: Iterable[Any],
                 x_transform: Callable[[R], XOut],
                 y_transform: Callable[[R], YOut]) -> None:

        self.iterable = iterable
        self.x_transform = x_transform
        self.y_transform = y_transform
        self.iterator = iter(self.iterable)

    def __len__(self):
        return len(self.iterator)

    def __iter__(self) -> SizedIterator[Tuple[XOut, YOut]]:
        return BaseTfmIterator_(self.iterable, self.x_transform, self.y_transform)

    def __next__(self):
        record = next(self.iterator)
        if (isinstance(record, tuple) and len(record) == 2):
            x, y = record
            return self.x_transform(x), self.y_transform(y)
        else:
            return self.x_transform(record), self.y_transform(record)


class TubSequence(Iterable[TubRecord]):
    def __init__(self, records: List[TubRecord]) -> None:
        self.records = records

    def __iter__(self) -> SizedIterator[TubRecord]:
        return TubSeqIterator(self.records)

    def __len__(self):
        return len(self.records)

    def build_pipeline(self,
                       x_transform: Callable[[TubRecord], X],
                       y_transform: Callable[[TubRecord], Y]) \
            -> TfmIterator:
        return TfmIterator(self, x_transform=x_transform, y_transform=y_transform)

    @classmethod
    def map_pipeline(
            cls,
            x_transform: Callable[[X], XOut],
            y_transform: Callable[[Y], YOut],
            pipeline: SizedIterator[Tuple[X, Y]]) -> SizedIterator[Tuple[XOut, YOut]]:
        return TfmTupleIterator(pipeline, x_transform=x_transform, y_transform=y_transform)

    @classmethod
    def map_pipeline_factory(
            cls,
            x_transform: Callable[[X], XOut],
            y_transform: Callable[[Y], YOut],
            factory: Callable[[], SizedIterator[Tuple[X, Y]]]) -> SizedIterator[Tuple[XOut, YOut]]:

        pipeline = factory()
        return cls.map_pipeline(pipeline=pipeline, x_transform=x_transform, y_transform=y_transform)
