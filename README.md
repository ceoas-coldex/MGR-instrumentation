# MGR-instrumentation
Codebase and documentation for unified data collection of the OSU COLDEX MGR lab instrumentation

## GUI
- ctrl-tab walks you around the different widgets

## Dependencies
- imports in the virtual environment requirements.txt

### Abakus
- Just plugged straight into my (windows10) laptop, it set up the device properly

### Sensirion flow meters
- just plugged in, took the data validation and processing from Abby's stuff

### Dimetrix laser
- just plugged in

## Running
- Alt+q is the hotkey to stop data collection

## To add a new sensor
- sensor_comms.yaml
- sensor_data.yaml
- executor._set_gui_buttons
- sensor -> new method for initializing, querying, shutting down, etc

