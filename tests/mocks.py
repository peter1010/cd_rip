"""Collection of mock objects to help with testing"""

import builtins
import urllib.request

class PatchInput:
    """A mock for input()

    This mock is a Context Manager and when used redirects the builtin
    input() method so that it takes input from a redefined list"""

    def __init__(self, inputs):
        self.inputs = inputs
        
    def mock_input(self, arg):
        """The mock input() method, take next input from list of
        inputs"""
        next = self.inputs.pop(0)
        return next

    def __enter__(self):
        self._saved_input = builtins.input
        builtins.input = self.mock_input
        return self

    def __exit__(self, e_type, e_value, e_traceback):
        builtins.input = self._saved_input
        assert(len(self.inputs) == 0)
        

class PatchUrlOpen:
    """A mock for urlopen"""
    def __init__(self, response=None, exec_cnt=0, exec_code=503):
        self.response = response
        self.exec_cnt = exec_cnt
        self.exec_code = exec_code
        if self.exec_code in [404, 503]:
            self.exec_url_error = False
        else:
            self.exec_url_error = True
        self.case = 1

    def mock_urlopen(self, url):
        if self.exec_cnt > 0:
            self.exec_cnt -= 1
            if self.exec_url_error:
                raise urllib.error.URLError(url,
                        self.exec_code)
            else:
                raise urllib.error.HTTPError(url,
                        self.exec_code, None, None, None)
        self.url = url
        return self.response

    def __enter__(self):
        self._saved_urlopen = urllib.request.urlopen
        urllib.request.urlopen = self.mock_urlopen
        return self

    def __exit__(self, e_type, e_value, e_traceback):
        urllib.request.urlopen = self._saved_urlopen
