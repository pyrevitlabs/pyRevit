import requests


__context__ = 'zerodoc'
__fullframeengine__ = True


r = requests.get('http://www.x.com')

print('X.com says: {}'.format(r.text))
