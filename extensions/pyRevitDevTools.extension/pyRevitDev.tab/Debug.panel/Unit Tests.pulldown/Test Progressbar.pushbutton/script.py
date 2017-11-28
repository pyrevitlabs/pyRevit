from pyrevit.forms import ProgressBar


__context__ = 'zerodoc'


# with ProgressBar(indeterminate=True) as pb:
# with ProgressBar(title='Test Title', indeterminate=True) as pb:
cancelcount = 0
cancelcounttimeout = 50
with ProgressBar() as pb:
    for counter in range(0, 300):
        if pb.cancelled:
            break
        else:
            pb.update_progress(counter, 300)

    pb.indeterminate = True
    pb.title = 'Indeterminate Process... ({value}/{max_value})'
    for counter in range(0, 300):
        if pb.cancelled:
            cancelcount += 1
            if cancelcount >= cancelcounttimeout:
                break

        pb.update_progress(counter, 300)
