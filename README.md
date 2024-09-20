# MGR-instrumentation
Codebase and documentation for unified data collection of the OSU COLDEX MGR lab instrumentation

## Overview

## Getting Started

### Dependencies
- imports in the virtual environment requirements.txt

### Abakus
- Just plugged straight into my (windows10) laptop, it set up the device properly

### Sensirion flow meters
- just plugged in, took the data validation and processing from Abby's stuff

### Dimetrix laser
- just plugged in

## GUI
- ctrl-tab walks you around the different widgets

## Data Management

## Modification Instructions
### To add a new sensor
- sensor_comms.yaml
- sensor_data.yaml
- sensor_interfaces\my_new_sensor_name.py -> make a class with methods for initializing, querying, shutting down, etc
- sim_interfaces -> make a shell of those ^ methods. Can have as many or as few cababilities as you'd like, but this allows the entire pipeline to run even when a sensor is unplugged
- sensor.py -> tie into those new methods and write a my_new_sensor_producer() method to publish sensor data to a bus
- interpretor.py -> new methods for processing, which get called by main_consumer_producer. Make sure the dictionary keys match
- 



