import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import time

def epoch_to_pacific_time(time):
    """Method to convert from epoch (UTC, number of seconds since Jan 1, 1970) to a datetime format
    in the Pacific timezone

    Args:
        time (array_like): Anything that can be converted into a np array, e.g a list of epoch times

    Returns:
        t_pacific (DateTimeIndex): Datetime object in pacific time
    """
    time = np.array(time)
    # Convert to datetime, specifying that it's in seconds
    t_datetime = pd.to_datetime(time, unit='s')
    # Current timezone is UTC
    t_utc = t_datetime.tz_localize('utc')
    # New timezone is pacific
    t_pacific = t_utc.tz_convert('America/Los_Angeles')

    # t_pacific = datetime(t_pacific)
    
    # print(t_pacific)
    # print(type(t_pacific))
    # t_pacific = float(np.array(t_pacific))

    # print(t_pacific)

    return t_pacific

y = []
x = []
for i in range(10):
    t = time.time()
    t_pdt = epoch_to_pacific_time(t)
    x.append(t_pdt)
    y.append(i*2)
    time.sleep(0.5)

fig, ax = plt.subplots()

ax.plot(x, y)

plt.show()
