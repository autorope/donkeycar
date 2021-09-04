import unittest
import pytest

from donkeycar.utilities.circular_buffer import CircularBuffer

class TestCircularBuffer(unittest.TestCase):

    def test_circular_buffer_queue(self):
        """
        enqueue items to head
        dequeue items from tail
        """
        queue:CircularBuffer = CircularBuffer(3, defaultValue="out-of-range")
        self.assertEqual(3, queue.capacity)
        self.assertEqual(0, queue.count)

        queue.enqueue(0)
        self.assertEqual(1, queue.count)
        self.assertEqual(0, queue.head())
        self.assertEqual(0, queue.tail())

        queue.enqueue(1)
        self.assertEqual(2, queue.count)
        self.assertEqual(1, queue.head())
        self.assertEqual(0, queue.tail())

        queue.enqueue(2)
        self.assertEqual(3, queue.count)
        self.assertEqual(2, queue.head())
        self.assertEqual(0, queue.tail())

        queue.enqueue(3)
        self.assertEqual(3, queue.count)
        self.assertEqual(3, queue.head())
        self.assertEqual(1, queue.tail())

        self.assertEqual(1, queue.dequeue())
        self.assertEqual(2, queue.count)
        self.assertEqual(3, queue.head())
        self.assertEqual(2, queue.tail())

        self.assertEqual(2, queue.dequeue())
        self.assertEqual(1, queue.count)
        self.assertEqual(3, queue.head())
        self.assertEqual(3, queue.tail())

        self.assertEqual(3, queue.dequeue())
        self.assertEqual(0, queue.count)
        self.assertEqual("out-of-range", queue.head())
        self.assertEqual("out-of-range", queue.tail())

        self.assertEqual("out-of-range", queue.dequeue())

    def test_circular_buffer_stack(self):
        """
        push items to head
        pop items from head
        """
        stack:CircularBuffer = CircularBuffer(2, defaultValue="out-of-range")
        self.assertEqual(2, stack.capacity)
        self.assertEqual(0, stack.count)
        self.assertEqual("out-of-range", stack.pop())

        stack.push(0)
        self.assertEqual(1, stack.count)
        self.assertEqual(0, stack.head())
        self.assertEqual(0, stack.tail())

        stack.push(1)
        self.assertEqual(2, stack.count)
        self.assertEqual(1, stack.head())
        self.assertEqual(0, stack.tail())

        # pushing onto a full stack raises exception
        try:
            stack.push(2)
            self.fail("should have thrown exception")
        except IndexError:
            # nothing should have changed
            self.assertEqual(2, stack.count)
            self.assertEqual(1, stack.head())
            self.assertEqual(0, stack.tail())

        self.assertEqual(1, stack.pop())
        self.assertEqual(1, stack.count)
        self.assertEqual(0, stack.head())
        self.assertEqual(0, stack.tail())

        self.assertEqual(0, stack.pop())
        self.assertEqual(0, stack.count)
        self.assertEqual("out-of-range", stack.head())
        self.assertEqual("out-of-range", stack.tail())

        # popping from empty stack returns default
        self.assertEqual("out-of-range", stack.pop())

    def test_circular_buffer_array(self):
        """
        append items to tail
        set/get items by index
        """
        array:CircularBuffer = CircularBuffer(2, defaultValue="out-of-range")
        self.assertEqual(2, array.capacity)
        self.assertEqual(0, array.count)
        self.assertEqual("out-of-range", array.get(0))

        array.append(0)
        self.assertEqual(1, array.count)
        self.assertEqual(0, array.head())
        self.assertEqual(0, array.tail())
        self.assertEqual(0, array.get(0))
        self.assertEqual("out-of-range", array.get(1))

        array.append(1)
        self.assertEqual(2, array.count)
        self.assertEqual(0, array.head())
        self.assertEqual(1, array.tail())
        self.assertEqual(0, array.get(0))
        self.assertEqual(1, array.get(1))
        self.assertEqual("out-of-range", array.get(2))

        for i in range(array.count):
            array.set(i, array.count-i)
            self.assertEqual(array.count-i, array.get(i))
