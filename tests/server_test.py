"""
server_test.py

Purpose:
    Script that verifies the expected behavior of two Nginx server endpoints.

Exit codes:
  - 0  success
  - 10 connectivity failure
  - 20 wrong status code
  - 30 wrong body content
  - 40 unexpected script error
"""

import http.client
import os
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed

ALLOWED_STATUS_CODES = {200,501}
LIMITED_STATUS = 429 

# exit codes mapping
EXIT_CONNECT = 10
EXIT_STATUS = 20
EXIT_HEADERS = 30
EXIT_BODY = 40
EXIT_UNEXPECTED = 50

# will be used to set tests.
class Test:
    """
    Defines expectations for one endpoint test.

    Attributes:
        status: Expected HTTP status code.
        headers: Required response headers (key -> expected substring in value).
        body: List of required substrings that must appear in the response body.
    """
    def __init__(self, status: int, headers: dict, body: list[str]):
        self.status = status
        self.headers = headers
        self.body = body

def http_req(host: str, port: int, timeout: float, method: str):
    """
    Send one HTTP request and returns a tuple ((int)status_code, (dict)headers, (str)body)
    
    :param (str) host: hostname
    :param (int) port: port
    :param (float) timeout: timeout for connection
    :param (str) method: method of http requset
    """
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    try: 
        conn.request(method, "/", headers={"Connection": "close", "User-Agent": "server_test.py"})
        response = conn.getresponse()
        body = response.read().decode("utf-8", errors="replace")
        headers = dict(response.getheaders())
        return response.status, body
    finally:
        conn.close()

def https_req(host: str, port: int, timeout: float, method: str):
    """
    Send one HTTPS request and returns a tuple ((int)status_code, (dict)headers, (str)body)
    
    :param (str) host: hostname
    :param (int) port: port
    :param (float) timeout: timeout for connection
    :param (str) method: method of http requset
    """
    ctx = ssl._create_unverified_context()
    conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=ctx)
    try: 
        conn.request(method, "/", headers={"Connection": "close", "User-Agent": "server_test.py"})
        response = conn.getresponse()
        body = response.read().decode("utf-8", errors="replace")
        headers = dict(response.getheaders())
        return response.status, body
    finally:
        conn.close()


def req(host: str, port: int, proto: str, timeout: float, method: str):
    """
    Send one HTTP or HTTPS request and returns a tuple ((int)status_code, (dict)headers, (str)body)
    
    :param (str) host: hostname
    :param (int) port: port
    :param (float) timeout: timeout for connection
    :param (str) method: method of http requset
    """
    if proto == "https":
        ctx = ssl._create_unverified_context()
        conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=ctx)
    else:
        conn = http.client.HTTPConnection(host, port, timeout=timeout)

    try: 
        conn.request(method, "/", headers={"Connection": "close", "User-Agent": "server_test.py"})
        response = conn.getresponse()
        body = response.read().decode("utf-8", errors="replace")
        headers = dict(response.getheaders())
        return response.status, headers, body
    finally:
        conn.close()

def response_test(source: str, status: int, headers: dict, body: str, test: Test):
    """
    verifies a response of an endpoint.
    
    :param (str) source: name of source to keep track of errors
    :param (str) status: response status code
    :param (dict) headers: response headers
    :param (str) body: response body of
    :param (Test) test: the desired status code, header and content of body
    """
    proto, host, port = source.split(":")

    # check the status code
    if test.status is not None:
        if test.status != status:
            return (EXIT_STATUS, f"FAIL {proto}://{host}:{port} status: expected {test.status} got {status}")
    # check that all required headers are present 
    if test.headers is not None:
        for key, value in test.headers.items():
            #check if headers has key - save "" if no.
            actual = headers.get(key, "")
            if value not in actual:
                return (EXIT_HEADERS, f"FAIL {proto}://{host}:{port} header {key}: expected contains {value!r} got {actual!r}")
   # check that all required strings are present in the body 
    if test.body is not None:
        for str in test.body:
            if str not in body:
                return (EXIT_BODY, f"FAIL {proto}://{host}:{port} body: missing {str!r}")

    return (0, f"OK {proto}://{host}:{port} response is valid")

def limit_test(dest: str):
    """
    Test rate limit feature of endpoints
    
    :param (str) source: Source and destination of the test (format - protocol:hostname:port)
    """
    proto, host, port = dest.split(":")
    
    total = 40
    workers = 10
    limited = 0
    ok = 0

    def one_test():
        status, headers, body = req(host, port, proto, 2.0, "GET")
        # headers and body not neccessery here
        return status
    
    # burst: send many requests quickly in parallel
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(one_test) for _ in range(total)]
        for future in as_completed(futures):
            status_code = future.result()
            if status_code in ALLOWED_STATUS_CODES:
                ok += 1
            elif status_code == LIMITED_STATUS:
                limited += 1

    if limited == 0:
        return (EXIT_STATUS, f"FAIL {proto}://{host}:{port} rate-limit: not triggered (no 503/429). ok={ok}/{total}")

    return (0, f"OK {proto}://{host}:{port} rate-limit triggered. ok={ok}/{total} limited={limited}/{total}")

def main() -> int:
    host = os.environ.get("NGINX_HOST", "localhost")
    total_codes = []
    total_msgs = []

    # define the list of tergets to test - each terget MUST have:
    #   "dest"     - (str) destination ip
    #   "port"     - (int) port to access
    #   "protocol" - (str) portocol to be used (limitied to http or https)
    #   "method"   - (str) method to be used
    targets = [
        {"dest": host, "port": 8080, "protocol": "http", "method": "GET"},
        {"dest": host, "port": 8081, "protocol": "http", "method": "GET"},
        {"dest": host, "port": 8443, "protocol": "https", "method": "GET"}
    ]

    # define the list of tests to preform.
    # note that order of test MUST align with the order of the tergets!!!
    # stracture of a test:
    #   - int: desired status code
    #   - dict: headers to verify headers - {"header-name": "header-content", "header-name": "header-content", ...}
    #   - list[str]: list of strings to look for in the body
    # if you don't want to test a parameter use None.
    tests = [
        Test(200,
             {"Content-Type": "text/html"},
             ["<meta name=\"description\" content=\"Dino Chrome\">",
              "<h1>Surprise! Hope you have some fun!</h1>"]),
        Test(501,
             {"Content-Type": "text/html"},
             ["<meta name=\"description\" content=\"custom 501 error\">",
              "<h1>501 Not Implemented</h1>"]),
        Test(200,
             {"Content-Type": "text/html"},
             ["<meta name=\"description\" content=\"Dino Chrome\">",
              "<h1>Surprise! Hope you have some fun!</h1>"]),
    ]

    for target, test in zip(targets, tests):
        dest = target["dest"]
        port = int(target["port"])
        protocol = target["protocol"]
        method = target["method"]

        try:
            status, headers, body = req(dest, port, protocol, 3.0, method)
        except (OSError, TimeoutError) as e:
            total_codes.append(EXIT_CONNECT)
            total_msgs.append(f"FAIL {protocol}://{dest}:{port} connect error: {e}")
        else:
            source = f"{protocol}:{dest}:{port}"
            result_code, result_msg = response_test(source, status, headers, body, test)
            total_codes.append(result_code)
            total_msgs.append(result_msg)
            result_code, result_msg = limit_test(source)
            total_codes.append(result_code)
            total_msgs.append(result_msg)

    status = 0
    for i in range(len(total_codes)):
        if(total_codes[i] != 0): # if any failures exist
            status = 1
    for msg in total_msgs: # print all messages.
        print(msg)
    if status != 0: # if tests failed find min code that is not 0
        return min(code for code in total_codes if code != 0)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())