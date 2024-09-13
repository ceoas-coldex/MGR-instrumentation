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
- Alt+q is the hotkey to kill the GUI, cleanly shuts down sensors and stops data collection

## Data Management

## Modification Instructions
### To add a new sensor
- sensor_comms.yaml
- sensor_data.yaml
- executor._set_gui_buttons
- sensor -> new method for initializing, querying, shutting down, etc



