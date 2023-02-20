
class CircularBuffer:
    """
    Fixed capacity circular buffer that can be used as
    a queue, stack or array
    """
    def __init__(self, capacity:int, defaultValue=None) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be greater than zero")
        self.defaultValue = defaultValue
        self.buffer:list = [None] * capacity
        self.capacity:int = capacity
        self.count:int = 0
        self.tailIndex:int = 0

    def head(self):
        """
        Non-destructive get of the entry at the head (index count-1)
        return: if list is not empty, the head (most recently pushed/enqueued) entry.
                if list is empty, the default value provided in the constructor                
        """
        if self.count > 0:
            return self.buffer[(self.tailIndex + self.count - 1) % self.capacity]
        return self.defaultValue

    def tail(self):
        """
        Non-destructive get of the entry at the tail (index 0)
        return: if list is not empty, the tail (least recently pushed/enqueued) entry.
                if list is empty, the default value provided in the constructor
        """
        if self.count > 0:
            return self.buffer[self.tailIndex]
        return self.defaultValue

    def enqueue(self, value):
        """
        Push a value onto the head of the buffer.  
        If the buffer is full, then the value 
        at the tail is dropped to make room.
        """
        if self.count < self.capacity:
            self.count += 1
        else:
            # drop entry at the tail
            self.tailIndex = (self.tailIndex + 1) % self.capacity

        # write value at head
        self.buffer[(self.tailIndex + self.count - 1) % self.capacity] = value    

    def dequeue(self):
        """
        Remove value at tail of list and return it
        return: if list not empty, value at tail
                if list empty, the default value
        """
        theValue = self.tail()
        if self.count > 0:
            self.count -= 1
            self.tailIndex = (self.tailIndex + 1) % self.capacity
        return theValue

    def push(self, value):
        """
        Push a value onto the head of the buffer.  
        If the buffer is full, then a IndexError
        is raised.
        """
        if self.count >= self.capacity:
            raise IndexError("Attempt to push to a full buffer")

        self.enqueue(value)

    def pop(self):
        """
        Remove value at head of list and return it
        return: if list not empty, the value at head 
                if list empty, the default value
        """
        theValue = self.head()
        if self.count > 0:
            self.count -= 1
        return theValue

    def append(self, value):
        """
        append a value to the tail (index count-1) of the buffer.
        If the buffer is at capacity, then this
        will raise an IndexError.
        """
        if self.count >= self.capacity:
            raise IndexError("Attempt to append to a full buffer")

        # make space a tail for the value
        self.count += 1
        self.tailIndex = (self.tailIndex - 1) % self.capacity
        self.buffer[self.tailIndex] = value


    def get(self, i:int):
        """
        Get value at given index where
        head is index 0 and tail is is index count-1;
        i: index from 0 to count-1 (head is zero)
        return: value at index
                or the default value if index is out of range
        """
        if (i >= 0) and (i < self.count):
            return self.buffer[(self.tailIndex + (self.count + i - 1)) % self.capacity]

        return self.defaultValue

    def set(self, i:int, value):
        """
        Set value at given index where
        head is index 0 and tail is is index count-1;
        """
        if (i >= 0) and (i < self.count):
            self.buffer[(self.tailIndex + (self.count + i - 1)) % self.capacity] = value
            return
        raise IndexError("buffer index is out of range")

    def truncateTo(self, count):
        """
        Truncate the list to the given number of values.
        If the given number is greater than or equal to
        the current count(), then nothing is changed.
        If the given number is less than the 
        current count(), then elements are dropped
        from the tail to resize to the given number.
        The capactity of the queue is not changed.

        So to drop all entries except the head:
         truncateTo(1)        

        count: the desired number of elements to
               leave in the queue (maximum)
        """
        if count < 0 or count > self.capacity:
            raise ValueError("count is out of range")
        self.count = count
        self.tailIndex = (self.tailIndex + count) % self.capacity

