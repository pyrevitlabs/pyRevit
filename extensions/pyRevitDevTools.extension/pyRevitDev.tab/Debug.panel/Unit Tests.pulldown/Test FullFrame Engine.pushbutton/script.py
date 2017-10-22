__fullframeengine__ = True

import requests

r = requests.get('http://www.x.com')

print('X.com says: {}'.format(r.text))
