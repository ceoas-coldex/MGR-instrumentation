# MGR Instrumentation
Codebase and documentation for unified data collection of the OSU COLDEX MGR lab instrumentation

## Overview

purpose of this repo is 

current sensors integrated are

This README describes installation/setup procedures, how to use the codebase, elements of the GUI, and data management. More documentation exists in each package:

- [Sensor Interfaces README](sensor_interfaces/README.md): documentation of the **sensors**, including user manuals, interfaces, simulated hardware, and steps for adding a new sensor
- [Data Pipeline README](main_pipeline/README.md): crunchier documentation of the **data processing pipeline**, such as how data gets passed from sensing → interpreting → saving.

## Getting Started

This section goes over installation and setup of this repository. If you're reading this README from the MGR lab computer, this has already been taken care of - you can start [using the codebase](#running).

### Installation

This project can be installed from GitHub with

    git clone https://github.com/ali-clara/MGR-instrumentation.git

Or by using [GitHub desktop](https://github.com/apps/desktop), which I recommend for Windows and for folks who aren't too familiar with `git`.

### Dependencies
I highly recommend setting up a virtual environment to hold and store this codebase, especially for lab computers with multiple users. This allows you to run Python locally in the environment, instead of globally on your machine, which gets rid of a lot of import/path headaches. A good IDE can make this really easy ([here's a walkthrough for VSCode](https://code.visualstudio.com/docs/python/environments#_creating-environments)). Once you have your environment, you can import all the dependencies needed for this repository by running the following from the main directory:

    pip install -r requirements.text

If you don't want to use a virtual environment, you'll need to import the following:

- [numpy](https://pypi.org/project/numpy/)
- [pandas](https://pypi.org/project/pandas/)
- [pyserial](https://pypi.org/project/pyserial/)
- [matplotlib](https://pypi.org/project/matplotlib/)
- [logdecorator](https://pypi.org/project/logdecorator/)
- [PyYAML](https://pypi.org/project/pyyaml/)
- [readerwriterlock](https://pypi.org/project/readerwriterlock/)
- [PyQt5](https://pypi.org/project/PyQt5/)

### Configuration Files

To make this codebase easier to modify, it uses a set of YAML files to configure internal parameters, such as the sensors we display on the live-plotting screens, the directories we save data to, and the sensor communication ports. These files and their functions are described here, as well as what elements to configure upon setup.

- *sensor_comms.yaml* - Sets the sensor communication parameters, such as serial port and baud rate.

    - <mark>**Configure upon setup**:</mark> Set the correct serial port for each sensor. You can find this information by plugging in the sensors one at a time and noting what ports become active, either in the Windows Device Manager (under COM & LPT) or through the command line.

- *data_saving.yaml* - Sets the directories where sensor data and logged notes get stored.
    
    - <mark>**Configure upon setup**:</mark> Set the directories to a valid location on your device

- *sensor_data.yaml* - Sets up internal data management. You can comment out lines or entire sensor blocks to prevent that data from being plotted and saved.

    - **Configure upon setup**: Nothing required

- *log_entries.yaml* - Sets the text entries that pop up on the Logging & Notetaking GUI panel.

    - **Configure upon setup**: Nothing required

- *main_page_plots.yaml* - Sets what sensors and what data channels of those sensors get plotted on the main data-streaming page.

    - **Configure upon setup**: Nothing required

## Running

## GUI 
- tab walks you around the different widgets

## Data Management
