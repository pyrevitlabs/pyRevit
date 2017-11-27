from pyrevit.forms import ProgressBar

# with ProgressBar(indeterminate=True) as pb:
# with ProgressBar(title='Test Title', indeterminate=True) as pb:
with ProgressBar() as pb:
    for counter in range(0, 300):
        if pb.cancelled:
            break
        else:
            pb.update_progress(counter, 600)

    pb.indeterminate = True
    pb.title = 'Indeterminate Process... ({value}/{max_value})'
    for counter in range(300, 600):
        if pb.cancelled:
            break
        else:
            pb.update_progress(counter, 600)
