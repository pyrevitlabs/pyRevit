"""Opens the python AEC Slack team."""
from pyrevit import script


__context__ = 'zerodoc'


url = 'https://pythonaec.slack.com/'
script.open_url(url)
