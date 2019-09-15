from pyrevit.forms import ProgressBar


__context__ = 'zero-doc'


# with ProgressBar(indeterminate=True) as pb:
# with ProgressBar(title='Test Title', indeterminate=True) as pb:
cancelcount = 0
cancelcounttimeout = 50
max_value = 1000
with ProgressBar(cancellable=True, step=10) as pb:
    for counter in range(0, max_value):
        if pb.cancelled:
            break
        else:
            pb.update_progress(counter, max_value)

    for counter in range(0, max_value):
        pb.step = (max_value - counter) / 10
        if pb.cancelled:
            break
        else:
            pb.update_progress(counter, max_value)

    pb.indeterminate = True
    pb.title = 'Indeterminate Process... ({value} of {max_value})'
    for counter in range(0, max_value/4):
        if pb.cancelled:
            cancelcount += 1
            if cancelcount >= cancelcounttimeout:
                break

        pb.update_progress(counter, max_value/4)
