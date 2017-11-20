from time import sleep
from pyrevit.forms import ProgressBar

with ProgressBar() as pb:
	for counter in range(0, 100, 10):
		pb.update_progress(counter, 100)
		sleep(0.5)
