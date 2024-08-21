import numpy as np
import time
import concurrent.futures
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
    
class DummySensor():
    """Class that mimics a sensor by generating random integers. This would be the place to read from the different 
    sensors and publish that data over busses"""
    def __init__(self) -> None:
        pass

    def sensor_producer(self, sensor_bus:Bus, delay):
        data = self.read_sensor()
        sensor_bus.write(data)
        time.sleep(delay)

    def read_sensor(self):
        data = np.random.randint(-5, 6)
        return data

class DummyInterpretor():
    """Class that reads data from the sensor bus, does some processing, and republishes on an interpretor bus.
    Currently just takes in the random integer from DummySensor and doubles it"""
    def __init__(self) -> None:
        pass

    def doubler_consumer_producer(self, sensor_bus:Bus, doubler_bus:Bus, delay):
        data = sensor_bus.read()
        interp = self.doubler(data)
        doubler_bus.write(interp)
        time.sleep(delay)

    def doubler(self, data):
        doubled = data*2
        return doubled

class DummyDisplay():
    """Class that reads the interpreted data and displays it. Will eventually be on the GUI, for now it 
    reads the interpretor bus and prints the data"""
    def __init__(self) -> None:
        pass

    def display_consumer(self, interpretor_bus:Bus, delay):
        interp_data = interpretor_bus.read()
        print(interp_data)

class DummyExecutor():
    """Class that handles passing the data around on all the busses. Still needs a clean shutdown."""
    def __init__(self) -> None:
        # Initialize the classes
        self.sensor = DummySensor()
        self.interpretor = DummyInterpretor()
        self.display = DummyDisplay()

        # Initialize the busses
        self.sensor_bus = Bus()
        self.interpretor_bus = Bus()

        # Set the delay times (sec)
        self.sensor_delay = 0.1
        self.interp_delay = 0.1
        self.display_delay = 0.1
        
    def execute(self):
        """Method to execute the sensor, interpretor, and display classes with threading. Calls the appropriate methods within
        those classes and passes them the correct busses and delay times."""
        while True:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                eSensor = executor.submit(self.sensor.sensor_producer, self.sensor_bus, self.sensor_delay)
                eInterpreter = executor.submit(self.interpretor.doubler_consumer_producer, self.sensor_bus, 
                                                self.interpretor_bus, self.interp_delay)
                eDisplay = executor.submit(self.display.display_consumer, self.interpretor_bus, self.display_delay)

            eSensor.result()
            eInterpreter.result()
            eDisplay.result()

if __name__ == "__main__":
    my_executor = DummyExecutor()
    my_executor.execute()