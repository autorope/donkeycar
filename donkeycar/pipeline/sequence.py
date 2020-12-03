from typing import Any, Callable, Generic, Iterable, Iterator, List, Sized, Tuple, TypeVar

import math
import numpy as np
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

    def batched(self, batch_size: int) -> Iterator[List[X]]:
        # Produces a batch of results
        # Ideally we should be able to return a `SizedIterator` but `mypy`
        # won't resolve this kind of recursive type
        raise NotImplemented


class TubSeqIterator(SizedIterator[TubRecord]):
    def __init__(self, records: List[TubRecord]) -> None:
        self.records = records or list()
        self.current_index = 0

    def __len__(self):
        return len(self.records)

    def __iter__(self) -> SizedIterator[TubRecord]:
        return self

    def __next__(self):
        if self.current_index >= len(self.records):
            raise StopIteration('No more records')

        record = self.records[self.current_index]
        self.current_index += 1
        return record

    next = __next__


class TfmIterator(Generic[R, XOut, YOut],  SizedIterator[Tuple[XOut, YOut]]):
    def __init__(self,
                 iterator: Iterable[R],
                 x_transform: Callable[[R], XOut],
                 y_transform: Callable[[R], YOut]) -> None:

        self.iterator = BaseTfmIterator_(
            iterator=iterator, x_transform=x_transform, y_transform=y_transform)

    def __len__(self):
        return len(self.iterator)

    def __iter__(self) -> SizedIterator[Tuple[XOut, YOut]]:
        return self

    def __next__(self):
        return next(self.iterator)

    def batched(self, batch_size=64) -> SizedIterator[List[Tuple[XOut, YOut]]]:
        return self.iterator.batched(batch_size=batch_size)


class TfmTupleIterator(Generic[X, Y, XOut, YOut],  SizedIterator[Tuple[XOut, YOut]]):
    def __init__(self,
                 iterator: Iterable[Tuple[X, Y]],
                 x_transform: Callable[[X], XOut],
                 y_transform: Callable[[Y], YOut]) -> None:

        self.iterator = BaseTfmIterator_(
            iterator=iterator, x_transform=x_transform, y_transform=y_transform)

    def __len__(self):
        return len(self.iterator)

    def __iter__(self) -> SizedIterator[Tuple[XOut, YOut]]:
        return self

    def __next__(self):
        return next(self.iterator)

    def batched(self, batch_size=64) -> SizedIterator[List[Tuple[XOut, YOut]]]:
        return self.iterator.batched(batch_size=batch_size)


class BaseTfmIterator_(Generic[XOut, YOut],  SizedIterator[Tuple[XOut, YOut]]):
    '''
    A basic transforming iterator.
    Do no use this class directly.
    '''

    def __init__(self,
                 # Losing a bit of type safety here for a common implementation
                 iterator: Iterable[Any],
                 x_transform: Callable[[R], XOut],
                 y_transform: Callable[[R], YOut]) -> None:

        self.iterator = iter(iterator)
        self.x_transform = x_transform
        self.y_transform = y_transform

    def __len__(self):
        return len(self.iterator)

    def __iter__(self) -> SizedIterator[Tuple[XOut, YOut]]:
        return self

    def __next__(self):
        record = next(self.iterator)
        if (isinstance(record, tuple) and len(record) == 2):
            x, y = record
            return self.x_transform(x), self.y_transform(y)
        else:
            return self.x_transform(record), self.y_transform(record)

    def batched(self, batch_size=64) -> SizedIterator[List[Tuple[XOut, YOut]]]:
        batched_iterator = BatchedIterator(self, batch_size=batch_size)
        return batched_iterator


class BatchedIterator(SizedIterator[List[R]]):
    def __init__(self, pipeline: SizedIterator[R], batch_size: int) -> None:
        self.pipeline = pipeline
        self.batch_size = batch_size
        self.consumed = 0

    def __len__(self):
        return math.ceil(len(self.pipeline) / self.batch_size)

    def __next__(self) -> List[R]:
        count = 0
        batch = list()
        while count < self.batch_size and self.consumed < len(self.pipeline):
            r = next(self.pipeline)
            batch.append(r)
            count += 1
            self.consumed += 1

        if len(batch) > 0:
            return batch
        else:
            raise StopIteration('No more records')

    def __iter__(self) -> Iterator[List[R]]:
        return self


class TubSequence(Iterable[TubRecord]):
    def __init__(self, records: List[TubRecord]) -> None:
        self.records = records

    def __iter__(self) -> SizedIterator[TubRecord]:
        return TubSeqIterator(self.records)

    def __len__(self):
        return len(self.records)

    def build_pipeline(self,
                       x_transform: Callable[[TubRecord], X],
                       y_transform: Callable[[TubRecord], Y]) -> SizedIterator[Tuple[X, Y]]:
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


R1 = TypeVar('R1', covariant=True)
R2 = TypeVar('R2', covariant=True)


class Reshaper(Generic[R1, R2], SizedIterator[Tuple[np.ndarray, np.ndarray]]):
    def __init__(self, batched: SizedIterator[List[Tuple[R1, R2]]]) -> None:
        self.batch = batched

    def __len__(self) -> int:
        return len(self.batch)

    def __next__(self):
        records: List[Tuple[R1, R2]] = next(self.batch)
        X: List[R1] = list()
        Y: List[R2] = list()
        for record in records:
            x, y = record
            X.append(x)
            Y.append(y)

        return np.array(X), np.array(Y)

    def __iter__(self) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
        return self

    next = __next__
