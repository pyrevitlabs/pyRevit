"""Opens the python AEC Slack team."""
from pyrevit import coreutils


__context__ = 'zerodoc'


url = 'https://pythonaec.slack.com/'
coreutils.open_url(url)
