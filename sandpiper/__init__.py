# -*- coding: utf-8 -*-

import mimetypes
import os
import re
import tempfile
import urllib
import uuid

from mako import exceptions
from mako.lookup import TemplateLookup

_app_config = {}
_mako_template_lookup = None

_DEFAULT_CONFIG = {
    'mongo_db': 'CHANGE_ME',
    'mongo_host': 'CHANGE_ME',
    'mongo_port': 'CHANGE_ME',
    'public_path': 'CHANGE_ME',
    'template_path': 'CHANGE_ME'
}


def _get_config(key):
    if key in _app_config:
        return _app_config[key]
    else:
        return _DEFAULT_CONFIG.get(key)


_STATUS_CODES = {
    100: 'CONTINUE',
    101: 'SWITCHING PROTOCOLS',
    102: 'PROCESSING',
    200: 'OK',
    201: 'CREATED',
    202: 'ACCEPTED',
    203: 'NON-AUTHORITATIVE INFORMATION',
    204: 'NO CONTENT',
    205: 'RESET CONTENT',
    206: 'PARTIAL CONTENT',
    207: 'MULTI-STATUS',
    208: 'ALREADY REPORTED',
    226: 'IM USED',
    300: 'MULTIPLE CHOICES',
    301: 'MOVED PERMANENTLY',
    302: 'FOUND',
    303: 'SEE OTHER',
    304: 'NOT MODIFIED',
    305: 'USE PROXY',
    306: 'RESERVED',
    307: 'TEMPORARY REDIRECT',
    400: 'BAD REQUEST',
    401: 'UNAUTHORIZED',
    402: 'PAYMENT REQUIRED',
    403: 'FORBIDDEN',
    404: 'NOT FOUND',
    405: 'METHOD NOT ALLOWED',
    406: 'NOT ACCEPTABLE',
    407: 'PROXY AUTHENTICATION REQUIRED',
    408: 'REQUEST TIMEOUT',
    409: 'CONFLICT',
    410: 'GONE',
    411: 'LENGTH REQUIRED',
    412: 'PRECONDITION FAILED',
    413: 'REQUEST ENTITY TOO LARGE',
    414: 'REQUEST-URI TOO LONG',
    415: 'UNSUPPORTED MEDIA TYPE',
    416: 'REQUESTED RANGE NOT SATISFIABLE',
    417: 'EXPECTATION FAILED',
    422: 'UNPROCESSABLE ENTITY',
    423: 'LOCKED',
    424: 'FAILED DEPENDENCY',
    426: 'UPGRADE REQUIRED',
    500: 'INTERNAL SERVER ERROR',
    501: 'NOT IMPLEMENTED',
    502: 'BAD GATEWAY',
    503: 'SERVICE UNAVAILABLE',
    504: 'GATEWAY TIMEOUT',
    505: 'HTTP VERSION NOT SUPPORTED',
    506: 'VARIANT ALSO NEGOTIATES',
    507: 'INSUFFICIENT STORAGE',
    508: 'LOOP DETECTED',
    510: 'NOT EXTENDED',
}


_SESSION_STORE = {}


class HttpRequest(object):
    '''
    Object representing an HTTP request.
    '''
    def __init__(self, environ):
        self.environ = environ
        self.method = environ['REQUEST_METHOD']
        self.get = {}
        self.post = {}

        if len(self.environ['QUERY_STRING']) > 0:
            for get_piece in self.environ['QUERY_STRING'].split('&'):
                key, val = get_piece.split('=')
                self.get[urllib.unquote(key)] = urllib.unquote_plus(val)
        if self.method == 'POST':
            post_data = self.environ['wsgi.input'].read()
            for post_piece in post_data.split('&'):
                key, val = post_piece.split('=')
                self.post[urllib.unquote(key)] = urllib.unquote_plus(val)

        # Set up session
        cookies = self.cookies
        self.session = {}
        if 'sandpiper_session' in cookies:
            self.session_key = cookies['sandpiper_session']
            self.session = _SESSION_STORE.get(self.session_key, {})
        else:
            self.session_key = str(uuid.uuid4())

    @property
    def cookies(self):
        cookie_data = {}
        if 'HTTP_COOKIE' in self.environ:
            for cookie_def in self.environ['HTTP_COOKIE'].split('; '):
                cookie_name, cookie_value = cookie_def.split('=')
                cookie_data[cookie_name] = cookie_value
        return cookie_data


class HttpResponse(object):
    '''
    Object representing an HTTP response.
    '''
    def __init__(self, data, status_code=200, content_type='text/plain', headers={}, cookies={}):
        '''
        Create an HttpResponse. `data` may be an iterable or a string.
        `status_code` should be an integer. `content_type` should be a valid
        mime type. `headers` should be a dictionary with header names and
        values. `cookies` should be a dictionary with cookie names and values.
        '''
        self.defined_headers = headers
        if isinstance(data, str) or isinstance(data, unicode):
            self.data = [data]
            self.defined_headers['Content-Length'] = str(len(data))
        else:
            self.data = data
        self.status_code = status_code
        self.content_type = content_type
        self.cookies = cookies

    @property
    def status_text(self):
        return str(self.status_code) + ' ' + _STATUS_CODES[self.status_code]

    @property
    def headers(self):
        all_headers = [(key, self.defined_headers[key]) for key in self.defined_headers]
        # Add cookies
        cookies = self.cookies
        for cookie in cookies:
            all_headers.append(('Set-Cookie', cookie + '=' + cookies[cookie] + '; Path=/'))
        return all_headers


class HttpTemplateResponse(HttpResponse):
    '''
    Object representing an HTTP response using an HTML template.
    '''
    def __init__(self, template, context_dict, status_code=200, content_type='text/html', headers={}, cookies={}):
        '''
        Create an HttpResponse. `template` should be a relative reference to a
        template file in the app/views/templates folder. `context_dict` should
        be a dict used to untemplate the template from `template`.
        `status_code` should be an integer. `content_type` should be a valid
        mime type. `headers` should be a dictionary with header names and
        values. `cookies` should be a dictionary with cookie names and values.
        '''
        rendered_template = _mako_template_lookup.get_template(template).render(**context_dict)
        HttpResponse.__init__(self,
            rendered_template,
            status_code=status_code,
            content_type=content_type,
            headers=headers,
            cookies=cookies)


class HttpRedirectResponse(HttpResponse):
    '''
    Convenience object representing an HTTP response that redirects to another URL.
    '''
    def __init__(self, location, status_code=302, headers={}, cookies={}):
        '''
        Create an HTTPReponse that redirects to another URL.
        '''
        headers['Location'] = location
        HttpResponse.__init__(self,
            '',
            status_code=status_code,
            headers=headers,
            cookies=cookies)


class HttpException(Exception):
    '''
    Raise this to have Sandpiper render the 404/500/etc. view.
    '''
    def __init__(self, message, status_code=500):
        '''
        Do all the normal exception init stuff and also save the special
        information required to render the response.
        '''
        self.status_code = status_code
        Exception.__init__(self, message)


def get_wsgi_app(app_config, routes):
    global _app_config, _mako_template_lookup
    _app_config = app_config

    # Parse routes
    routing_list = []
    for path, handler in routes:
        if isinstance(handler, str) or isinstance(handler, unicode):
            handler_parts = handler.split('.')
            handler_module_name = '.'.join(handler_parts[:-1])
            handler_function_name = handler_parts[-1]
            module_import = __import__(handler_module_name)
            for part in handler_module_name.split('.')[1:]:
                module_import = getattr(module_import, part)
            handler_function = getattr(module_import, handler_function_name)
            routing_list.append((re.compile(path), handler_function))
        elif hasattr(handler, '__call__'):
            routing_list.append((re.compile(path), handler))
        else:
            raise Exception('Routes should either reference handlers by string or be a callable.')

    # Set up template lookup
    module_directory = tempfile.mkdtemp()
    _mako_template_lookup = TemplateLookup(directories=_get_config('template_path'), module_directory=module_directory)

    def _wsgi_app(environ, start_response):
        path_info = environ['PATH_INFO']
        try:
            for path_re, handler in routing_list:
                re_match = path_re.match(path_info)
                if re_match:
                    request = HttpRequest(environ)
                    args = (request,) + re_match.groups()
                    response = handler(*args)
                    if isinstance(response, HttpResponse):
                        _SESSION_STORE[request.session_key] = request.session
                        response.cookies['sandpiper_session'] = request.session_key
                        headers = [('Content-Type', response.content_type)] + response.headers
                        start_response(response.status_text, headers)
                        print path_info, response.status_text
                        return response.data
                    elif isinstance(response, str) or isinstance(response, unicode):
                        start_response('200 OK', [])
                        print path_info, '200 OK'
                        return [response]
            filename = os.path.abspath(_get_config('public_path') + path_info)
            if filename.startswith(_get_config('public_path')) and os.path.isfile(filename):
                with open(filename, 'rb') as f:
                    data = f.read()
                content_type, encoding = mimetypes.guess_type(os.path.basename(filename))
                headers = [('Content-Length', str(len(data)))]
                if content_type:
                    headers.append(('Content-Type', content_type))
                start_response('200 OK', headers)
                print path_info, '200 OK'
                return [data]
            else:
                raise HttpException('Not found', status_code=404)
        except HttpException as he:
            status_text = str(he.status_code) + ' ' + _STATUS_CODES[he.status_code]
            start_response(status_text, [])
            print path_info, status_text
            return [status_text + '?!? (╯°□°）╯︵ ┻━┻']
    return _wsgi_app
