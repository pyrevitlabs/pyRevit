from pyrevit.forms import ProgressBar

# with ProgressBar(indeterminate=True) as pb:
with ProgressBar() as pb:
    for counter in range(0, 200):
        if pb.cancelled:
            break
        else:
            pb.update_progress(counter, 200)
