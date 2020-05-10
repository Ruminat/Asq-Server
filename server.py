"""
  server.py
  The main server file.
  Run the following command to start it on windows (you need waitress for that):
  waitress-serve --port=8000 server:app
  And this one on UNIX (you need gunicorn for that):
  gunicorn server:app
"""

import falcon
import json

class Asq(object):
  def on_post(self, req, resp):
    result = req.media
    print(result)
    resp.body = json.dumps(result)

app = falcon.API()

app.add_route('/asq', Asq())
