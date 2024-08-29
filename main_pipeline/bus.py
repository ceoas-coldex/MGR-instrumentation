# -------------
# The bus!
# -------------

from readerwriterlock import rwlock

class Bus():
    """Class that sets up a bus to pass information around with read/write locking"""
    def __init__(self):
        self.message = None
        self.lock = rwlock.RWLockWriteD() # sets up a lock to prevent simultanous reading and writing

    def write(self, message):
        with self.lock.gen_wlock():
            self.message = message

    def read(self):
        with self.lock.gen_rlock():
            message = self.message
        return message