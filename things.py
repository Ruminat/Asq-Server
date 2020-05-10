# things.py

# Let's get this party started!
import falcon
import json


class Resource(object):
  def on_post(self, req, resp, **kwargs):
    result = req.media
    print(result['ID'])
    print(result['message'])
    # do your job
    resp.body = json.dumps(result)


app = falcon.API()

app.add_route('/test', Resource())
