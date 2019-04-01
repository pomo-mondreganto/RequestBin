from flask import Flask, request, redirect, url_for, render_template, abort, make_response
import secrets
from redis import StrictRedis
from werkzeug.routing import Rule
import re
import json
from datetime import datetime
from functools import wraps


class ReverseProxied(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)


app = Flask(__name__)
app.config['APPLICATION_ROOT'] = '/request_bin'
app.wsgi_app = ReverseProxied(app.wsgi_app)

app.url_map.add(Rule('/bin/<bin_id>', endpoint='bin'))

redis = StrictRedis(host='shared_redis', port=6379, db=0)


@app.route('/')
def hello_world():
    return render_template('index.html')


@app.route('/new_bin', methods=['GET'])
def new_bin():
    bin_id = secrets.token_hex(5)
    return redirect(url_for('bin_stats', bin_id=bin_id))


@app.endpoint('bin')
def view_bin(bin_id):
    if not re.match('^[0-9a-f]{10}$', bin_id):
        abort(404)

    pipe = redis.pipeline(transaction=True)
    exists = pipe.exists(f"bin-existence-{bin_id}").execute()[0]
    if not exists:
        abort(404)

    maybe_json = request.get_json(silent=True, cache=False)
    if maybe_json:
        thejson = json.dumps(maybe_json)
    else:
        thejson = "no json"

    obj = {
        'method': request.method,
        'url': request.url,
        'headers': list(request.headers),
        'form': list(request.form.items()),
        'args': list(request.args.items()),
        'json': thejson,
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }

    result = json.dumps(obj)

    pipe = redis.pipeline(transaction=True)
    pipe.lpush(f'bin-{bin_id}', result)
    pipe.execute()
    return 'OK'


@app.route('/stats/<bin_id>')
def bin_stats(bin_id):
    if not re.match('^[0-9a-f]{10}$', bin_id):
        abort(404)

    pipe = redis.pipeline(transaction=True)
    pipe.lrange(name=f'bin-{bin_id}', start=0, end=10)
    pipe.set(name=f'bin-existence-{bin_id}', value=1)
    pipe.expire(name=f'bin-existence-{bin_id}', time=300)

    result = pipe.execute()
    requests = result[0]

    try:
        requests = [json.loads(x.decode()) for x in requests]
    except UnicodeDecodeError or json.decoder.JSONDecodeError:
        requests = []

    return render_template('bin_stats.html', requests=requests, bin_id=bin_id)


if __name__ == '__main__':
    app.run()
