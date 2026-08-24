# -*- coding: utf-8 -*-
# netrequests.py
#
# Minimal requests-compatible shim for IronPython / pyRevit using .NET HttpClient.
#
# Supports:
# - requests.get(...)
# - requests.post(...)
# - requests.put(...)
# - requests.patch(...)
# - requests.delete(...)
# - params={}
# - json={}
# - data=
# - headers={}
# - timeout=
# - stream=True
# - response.status_code
# - response.ok
# - response.text
# - response.content
# - response.json()
# - response.iter_lines()
# - response.close()
# - requests.RequestException
# - requests.exceptions.RequestException

import clr

try:
    clr.AddReference("System.Net.Http")
except Exception as ex:
    raise Exception(
        "Failed to load System.Net.Http: {}".format(ex)
    )

from System import TimeSpan 
from System.Net.Http import ( 
    HttpClient,
    HttpRequestMessage,
    HttpMethod,
    StringContent,
    HttpCompletionOption
)

from System.IO import StreamReader 

try:
    from System.Text import Encoding
except Exception:
    Encoding = None

__version__ = "0.2.0"

_PATCH = HttpMethod("PATCH")

_shared_client = HttpClient()


class RequestException(Exception):
    pass

class Timeout(RequestException):
    pass

class _Exceptions(object):
    RequestException = RequestException
    Timeout = Timeout

exceptions = _Exceptions()

def _urlencode(params):
    """
    IronPython / CPython compatible urlencode helper.
    """
    if not params:
        return ""

    try:
        from urllib.parse import urlencode
        return urlencode(params)
    except Exception:
        pass

    try:
        from urllib import urlencode
        return urlencode(params)
    except Exception:
        pass


    pairs = ("{}={}".format(str(k), str(v)) for k, v in params.items())

    return "&".join(pairs)


def _apply_params(url, params):
    if not params:
        return url

    query = _urlencode(params)

    if not query:
        return url

    if "?" in url:
        return "{}&{}".format(url, query)

    return "{}?{}".format(url, query)


def _get_exception_message(ex):
    try:
        if ex.InnerException:
            return "{} | Inner: {}".format(
                ex,
                ex.InnerException
            )
    except Exception:
        pass

    return str(ex)


class Response(object):

    def __init__(self, dotnet_response, stream=False, client=None):
        self._response = dotnet_response
        self._stream = stream
        self._client = client
        self._reader = None

        try:
            self.status_code = int(
                dotnet_response.StatusCode
            )
        except Exception:
            self.status_code = 0

        try:
            self.reason = str(
                dotnet_response.ReasonPhrase
            )
        except Exception:
            self.reason = ""

        self.headers = {}

        try:
            for h in dotnet_response.Headers:
                try:
                    values = [str(x) for x in h.Value]
                    self.headers[str(h.Key)] = ",".join(values)
                except Exception:
                    pass
        except Exception:
            pass

        self._content = b""
        self._text = ""

        try:
            if dotnet_response.Content:

                try:
                    for h in dotnet_response.Content.Headers:
                        try:
                            values = [str(x) for x in h.Value]
                            self.headers[str(h.Key)] = ",".join(values)
                        except Exception:
                            pass
                except Exception:
                    pass

                # Important:
                # If this is a streaming response, do NOT read the full content here.
                # SSE endpoints may never complete, so ReadAsStringAsync().Result
                # would block forever.
                if not stream:
                    try:
                        self._content = (
                            dotnet_response.Content
                            .ReadAsByteArrayAsync()
                            .Result
                        )
                    except Exception:
                        self._content = b""

                    try:
                        self._text = (
                            dotnet_response.Content
                            .ReadAsStringAsync()
                            .Result
                        )
                    except Exception:
                        self._text = ""

        except Exception:
            pass

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    @property
    def text(self):
        return self._text

    @property
    def content(self):
        return self._content

    @property
    def raw(self):
        return self._response

    def json(self):
        import json

        if self._stream:
            raise RequestException(
                "Cannot parse streamed response as JSON."
            )

        if not self._text:
            return {}

        try:
            return json.loads(self._text)

        except Exception as ex:
            raise RequestException(
                "Invalid JSON: {}".format(ex)
            )

    def raise_for_status(self):
        if not self.ok:
            raise RequestException(
                "HTTP {} {}".format(
                    self.status_code,
                    self.reason
                )
            )

    def iter_lines(self):
        """
        Minimal implementation for requests.Response.iter_lines().

        Intended for SSE-style responses:

            for raw_line in response.iter_lines():
                ...

        Returns strings in IronPython/.NET rather than bytes.
        Your existing code already handles both.
        """

        try:
            if not self._response:
                return

            if not self._response.Content:
                return

            stream = (
                self._response.Content
                .ReadAsStreamAsync()
                .Result
            )

            self._reader = StreamReader(stream)

            while True:
                try:
                    line = self._reader.ReadLine()
                except Exception:
                    break

                if line is None:
                    break

                yield line

        except Exception:
            return

    def close(self):
        try:
            if self._reader:
                self._reader.Close()
        except Exception:
            pass

        try:
            if self._response:
                self._response.Dispose()
        except Exception:
            pass

        try:
            if self._client:
                self._client.Dispose()
        except Exception:
            pass


def _create_request(
        method,
        url,
        headers=None,
        data=None,
        json_data=None):

    method_map = {
        "GET": HttpMethod.Get,
        "POST": HttpMethod.Post,
        "PUT": HttpMethod.Put,
        "DELETE": HttpMethod.Delete,
        "PATCH": _PATCH,
        "HEAD": HttpMethod.Head
    }

    method_upper = method.upper()

    if method_upper not in method_map:
        raise RequestException(
            "Unsupported HTTP method: {}".format(method)
        )

    try:
        request = HttpRequestMessage(
            method_map[method_upper],
            url
        )

    except Exception as ex:
        raise RequestException(
            "Failed creating request: {}".format(
                _get_exception_message(ex)
            )
        )

    if headers:
        for k, v in headers.items():
            try:
                request.Headers.TryAddWithoutValidation(
                    str(k),
                    str(v)
                )
            except Exception:
                # Some headers are content headers and cannot be added here.
                # Content-Type is handled below when creating StringContent.
                pass

    try:
        if json_data is not None:

            import json

            payload = json.dumps(json_data)

            if Encoding:
                request.Content = StringContent(
                    payload,
                    Encoding.UTF8,
                    "application/json"
                )
            else:
                request.Content = StringContent(
                    payload
                )

        elif data is not None:

            if not isinstance(data, str):
                data = str(data)

            request.Content = StringContent(data)

    except Exception as ex:
        raise RequestException(
            "Failed creating content: {}".format(
                _get_exception_message(ex)
            )
        )

    return request


def request(
        method,
        url,
        headers=None,
        params=None,
        data=None,
        json=None,
        stream=False,
        timeout=None,
        verify=None,
        allow_redirects=True,
        **kwargs):

    if verify is False:
        raise NotImplementedError("verify=False is not supported")

    if allow_redirects is False:
        raise NotImplementedError("allow_redirects=False is not supported")

    client = _shared_client
    temporary_client = False
    req = None

    try:
        url = _apply_params(url, params)

        if timeout is not None:
            try:
                client = HttpClient()
                client.Timeout = TimeSpan.FromSeconds(
                    float(timeout)
                )
                temporary_client = True
            except Exception:
                client = _shared_client
                temporary_client = False

        req = _create_request(
            method,
            url,
            headers=headers,
            data=data,
            json_data=json
        )

        try:
            if stream:
                resp = client.SendAsync(
                    req,
                    HttpCompletionOption.ResponseHeadersRead
                ).Result
            else:
                resp = client.SendAsync(req).Result

        except Exception as ex:
            raise RequestException(
                "HTTP request failed: {}".format(
                    _get_exception_message(ex)
                )
            )

        finally:
            try:
                if req:
                    req.Dispose()
            except Exception:
                pass

        if resp is None:
            raise RequestException(
                "No response received"
            )

        # If streaming, keep the temporary client alive until response.close().
        if stream and temporary_client:
            return Response(
                resp,
                stream=True,
                client=client
            )

        response = Response(
            resp,
            stream=stream,
            client=None
        )

        return response

    except RequestException:
        raise

    except Exception as ex:
        import traceback

        raise RequestException(
            "{}\n\n{}".format(
                _get_exception_message(ex),
                traceback.format_exc()
            )
        )

    finally:
        # For non-streaming temporary clients, safe to dispose here because
        # response body has already been read into memory.
        if temporary_client and not stream:
            try:
                client.Dispose()
            except Exception:
                pass


def get(
        url,
        headers=None,
        params=None,
        stream=False,
        timeout=None,
        verify=None,
        allow_redirects=True,
        **kwargs):

    return request(
        "GET",
        url,
        headers=headers,
        params=params,
        stream=stream,
        timeout=timeout,
        verify=verify,
        allow_redirects=allow_redirects,
        **kwargs
    )


def post(
        url,
        headers=None,
        params=None,
        data=None,
        json=None,
        stream=False,
        timeout=None,
        verify=None,
        allow_redirects=True,
        **kwargs):

    return request(
        "POST",
        url,
        headers=headers,
        params=params,
        data=data,
        json=json,
        stream=stream,
        timeout=timeout,
        verify=verify,
        allow_redirects=allow_redirects,
        **kwargs
    )


def put(
        url,
        headers=None,
        params=None,
        data=None,
        json=None,
        stream=False,
        timeout=None,
        verify=None,
        allow_redirects=True,
        **kwargs):

    return request(
        "PUT",
        url,
        headers=headers,
        params=params,
        data=data,
        json=json,
        stream=stream,
        timeout=timeout,
        verify=verify,
        allow_redirects=allow_redirects,
        **kwargs
    )


def patch(
        url,
        headers=None,
        params=None,
        data=None,
        json=None,
        stream=False,
        timeout=None,
        verify=None,
        allow_redirects=True,
        **kwargs):

    return request(
        "PATCH",
        url,
        headers=headers,
        params=params,
        data=data,
        json=json,
        stream=stream,
        timeout=timeout,
        verify=verify,
        allow_redirects=allow_redirects,
        **kwargs
    )


def delete(
        url,
        headers=None,
        params=None,
        timeout=None,
        verify=None,
        allow_redirects=True,
        **kwargs):

    return request(
        "DELETE",
        url,
        headers=headers,
        params=params,
        timeout=timeout,
        verify=verify,
        allow_redirects=allow_redirects,
        **kwargs
    )


def head(
        url,
        headers=None,
        params=None,
        timeout=None,
        verify=None,
        allow_redirects=True,
        **kwargs):

    return request(
        "HEAD",
        url,
        headers=headers,
        params=params,
        timeout=timeout,
        verify=verify,
        allow_redirects=allow_redirects,
        **kwargs
    )