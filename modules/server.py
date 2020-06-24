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
from Asq import parse, translate
from db import SELECT, SELECT2Data

# The only rout of the server (/asq), translates the passed query and returns the result from DB.
class Asq(object):
  def on_post(self, req, resp):
    requestData = req.media
    query = requestData['query']

    parsed = parse(requestData['query'])
    if (parsed['status'] == 'error'):
      resp.body = json.dumps(parsed)
      return

    translated = translate(parsed)
    if (translated['status'] == 'error'):
      resp.body = json.dumps(translated)
      return

    try:
      result = SELECT(translated['result'], SELECT2Data)
      resp.body = json.dumps({
        'status': 'success',
        'result': result
      })
    except Exception:
      resp.body = json.dumps({
        'status': 'error',
        'message': 'Database error!'
      })
      return

app = falcon.API()

app.add_route('/asq', Asq())
