"""
server_test.py

Purpose:
    Script that verifies the expected behavior of two Nginx server blocks.

verifies that:
  - Port 8080 returns custom HTML (status EXPECTED_8080_STATUS) and contains META+H1 markers.
  - Port 8081 returns error HTML (status EXPECTED_8081_STATUS) and contains META+H1 markers.

Environment variables:
  - NGINX_HOST (default: localhost)
  - EXPECTED_8080_STATUS (default: 200)
  - EXPECTED_8081_STATUS (default: 501)

Exit codes:
  - 0  success
  - 10 connectivity failure
  - 20 wrong status code
  - 30 wrong body content
  - 40 unexpected script error
"""

import http.client
import os

EXPECTED_8080_STATUS = os.environ.get("EXPECTED_8080_STATUS", "200")  # if unset: defaults to 200
EXPECTED_8081_STATUS = os.environ.get("EXPECTED_8081_STATUS", "501")  # # if unset: defaults to 501

# exit codes mapping
EXIT_CONNECT = 10
EXIT_STATUS = 20 
EXIT_BODY = 30
EXIT_UNEXPECTED = 40

def http_req(host: str, port: int, timeout: float, method: str):
    """
    Send one HTTP request and returns a tuple (status_code, body)
    
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
        return response.status, body
    finally:
        conn.close()

# checks if respons contains give strings.
def analyze_response(source: str, body: str, status: str, meta: str, h1: str ):
    """
    checks the status of a response, searches for a meta tag and h1 element in the body.
    
    :param (str) source: name of souce to keep track of errors 
    :param (str) body: body of the response 
    :param (str) status: status code of the response 
    :param (str) meta: meta tag to search in the body
    :param (str) h1: h1 tag to search in the body
    """
    if(source == "8080"):
        if int(status) != int(EXPECTED_8080_STATUS):
            return (EXIT_STATUS, f"FAIL {source}: status {status}, expected {EXPECTED_8080_STATUS}")
    elif(source == "8081"):
        if int(status) != int(EXPECTED_8081_STATUS):
            return (EXIT_STATUS, f"FAIL {source}: status {status}, expected {EXPECTED_8081_STATUS}")
    
    if (meta not in body):
        return (EXIT_BODY, f"FAIL {source}: missing meta tag")
    if (h1 not in body):
        return (EXIT_BODY, f"FAIL {source}: missing h1")
    
    return (0, f"OK {source}")

def main() -> int:
    host = os.environ.get("NGINX_HOST", "localhost")
    total_codes = []
    total_msgs = []

    try:
        # testing server block listening on 8080
        print("testing 8080")
        try:
            status, body = http_req(host, 8080, 3.0, "GET")
        except (OSError, TimeoutError) as e:
            total_codes.append(EXIT_CONNECT)
            total_msgs.append(f"FAIL 8080: connect error: {e}")
        else:    
            response_code, response_msg = analyze_response("8080", body, status, 
                                                        "<meta name=\"description\" content=\"Dino Chrome\">",
                                                        "<h1>Surprise! Hope you have some fun!</h1>")
            total_codes.append(response_code)
            total_msgs.append(response_msg)

        # testing server block listening on 8080
        print("testing 8081")
        try:
            status, body = http_req(host, 8081, 3.0, "GET")
        except (OSError, TimeoutError) as e:
            total_codes.append(EXIT_CONNECT)
            total_msgs.append(f"FAIL 8081: connect error: {e}")
        else:    
            response_code, response_msg = analyze_response("8081", body, status,
                                "<meta name=\"description\" content=\"custom 501 error\">",
                                "<h1>501 Not Implemented</h1>")
            total_codes.append(response_code)
            total_msgs.append(response_msg)

    except Exception as e:
        total_codes.append(EXIT_UNEXPECTED)
        total_msgs.append(str(e))

    #
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