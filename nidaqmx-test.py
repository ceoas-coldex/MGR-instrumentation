from daqmx import NIDAQmxInstrument

daq = NIDAQmxInstrument(device_name='cDAQ1', serial_number="0130C856")

print(f"value: {daq.ai0.value:.3f}V")