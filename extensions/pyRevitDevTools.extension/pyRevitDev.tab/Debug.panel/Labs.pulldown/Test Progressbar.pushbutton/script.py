from pyrevit.forms import ProgressBar

with ProgressBar() as pb:
	for counter in range(0, 1000):
		pb.update_progress(counter, 1000)
