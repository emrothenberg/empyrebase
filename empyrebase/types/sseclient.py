import re
import threading
import time
import warnings

import requests


# Technically, we should support streams that mix line endings.  This regex,
# however, assumes that a system will provide consistent line endings.
end_of_field = re.compile(r'\r\n\r\n|\r\r|\n\n')

class SSEClient(object):
    def __init__(self, url, token_refreshable, token_refresher, session, build_headers, max_retries, last_id=None, retry=3000, **kwargs):
        self.url = url
        self.last_id = last_id
        self.retry = retry
        self.running = True
        # Optional support for passing in a requests.Session()
        self.session = session
        # function for building auth header when token expires
        self.build_headers = build_headers
        self.start_time = None
        # Any extra kwargs will be fed into the requests.get call later.
        self.requests_kwargs = kwargs
        self.token_refresher = token_refresher
        self.token_refreshable = token_refreshable
        self._new_iterator = True
        self.max_retries = max_retries
        
        if token_refreshable:
            reauth = threading.Thread(target=self._reauthorize_worker)
            reauth.start()

        # The SSE spec requires making requests with Cache-Control: nocache
        if 'headers' not in self.requests_kwargs:
            self.requests_kwargs['headers'] = {}
        self.requests_kwargs['headers']['Cache-Control'] = 'no-cache'

        # The 'Accept' header is not required, but explicit > implicit
        self.requests_kwargs['headers']['Accept'] = 'text/event-stream'

        # Keep data here as it streams in
        self.buf = u''

        self._connect()
        
    def __refresh_token(self):
        try:
            token = self.url.split("auth=")[1].split("&")[0]
        except IndexError:
            raise ValueError("Could not find token in URL. Please make sure you provided an auth token.")
        new_token = self.token_refresher()
        url = self.url.replace(token, new_token)
        self.url = url
        
    def _reauthorize_worker(self, interval=15):
        while True:
            time.sleep(interval)
            self.__refresh_token()

    def _connect(self):
        retries = 0
        while retries < self.max_retries:
            retries += 1
            if self.last_id:
                self.requests_kwargs['headers']['Last-Event-ID'] = self.last_id
            headers = self.build_headers()
            self.requests_kwargs['headers'].update(headers)
            # Use session if set.  Otherwise fall back to requests module.
            self.requester = self.session or requests
            self.resp = self.requester.get(self.url, stream=True, **self.requests_kwargs)
            self._new_iterator = True
            self.resp_iterator = self.resp.iter_content(decode_unicode=True)

            # TODO: Ensure we're handling redirects.  Might also stick the 'origin'
            # attribute on Events like the Javascript spec requires.
            if self.resp.status_code == 401 and self.token_refreshable: # Unauthorized with a chance for authorization.
                print(f"Failed to start streaming, trying again ({retries}/{self.max_retries})...")
                old_url = self.url
                self.__refresh_token()
                if self.url != old_url:
                    continue
            else: # No need to retry
                retries = self.max_retries
        
        self.resp.raise_for_status()
        retries = 0

    def _event_complete(self):
        complete = re.search(end_of_field, self.buf)
        # print(complete)
        return complete is not None

    def __iter__(self):
        return self

    def __next__(self):
        while not self._event_complete():
            try:
                if self._new_iterator and self.resp_iterator:
                    self._new_iterator = False  # Reset flag
                    self.resp_iterator = self.resp.iter_content(decode_unicode=True)  # Ensure reset

                nextchar = next(self.resp_iterator)
                self.buf += nextchar
            except (StopIteration, requests.RequestException):
                time.sleep(self.retry / 1000.0)
                self._connect()

                # The SSE spec only supports resuming from a whole message, so
                # if we have half a message we should throw it out.
                head, sep, tail = self.buf.rpartition('\n')
                self.buf = head + sep
                self._new_iterator = True
                continue

        split = re.split(end_of_field, self.buf)
        head = split[0]
        tail = "".join(split[1:])

        self.buf = tail
        msg = Event.parse(head)

        if msg.data == "credential is no longer valid":
            self._connect()
            return None

        if msg.data == 'null':
            return None

        # If the server requests a specific retry delay, we need to honor it.
        if msg.retry:
            self.retry = msg.retry

        # last_id should only be set if included in the message.  It's not
        # forgotten if a message omits it.
        if msg.id:
            self.last_id = msg.id

        return msg


class Event(object):

    sse_line_pattern = re.compile('(?P<name>[^:]*):?( ?(?P<value>.*))?')

    def __init__(self, data='', event='message', id=None, retry=None):
        self.data = data
        self.event = event
        self.id = id
        self.retry = retry

    def dump(self):
        lines = []
        if self.id:
            lines.append('id: %s' % self.id)

        # Only include an event line if it's not the default already.
        if self.event != 'message':
            lines.append('event: %s' % self.event)

        if self.retry:
            lines.append('retry: %s' % self.retry)

        lines.extend('data: %s' % d for d in self.data.split('\n'))
        return '\n'.join(lines) + '\n\n'

    @classmethod
    def parse(cls, raw):
        """
        Given a possibly-multiline string representing an SSE message, parse it
        and return a Event object.
        """
        msg = cls()
        for line in raw.split('\n'):
            m = cls.sse_line_pattern.match(line)
            if m is None:
                # Malformed line.  Discard but warn.
                warnings.warn('Invalid SSE line: "%s"' % line, SyntaxWarning)
                continue

            name = m.groupdict()['name']
            value = m.groupdict()['value']
            if name == '':
                # line began with a ":", so is a comment.  Ignore
                continue

            if name == 'data':
                # If we already have some data, then join to it with a newline.
                # Else this is it.
                if msg.data:
                    msg.data = '%s\n%s' % (msg.data, value)
                else:
                    msg.data = value
            elif name == 'event':
                msg.event = value
            elif name == 'id':
                msg.id = value
            elif name == 'retry':
                msg.retry = int(value)

        return msg

    def __str__(self):
        return self.data
