"""
WebSocket Close Code Number Registry, for code readability.
See RFC 6455 - https://tools.ietf.org/html/rfc6455#section-11.7
And RFC 6455 - https://tools.ietf.org/html/rfc6455
And https://www.iana.org/assignments/websocket/websocket.xhtml#close-code-number
And https://developer.mozilla.org/en-US/docs/Web/API/CloseEvent/code
"""


def is_standard(code):
    return 1000 <= code <= 2999
  
def is_unassigned(code):
    return 3001 <= code <= 3999
  
def is_private(code):
    return 4000 <= code <= 4999


CODE_1000_NORMAL_CLOSURE = 1000
CODE_1001_GOING_AWAY = 1001
CODE_1002_PROTOCOL_ERROR = 1002
CODE_1003_UNSUPPORTED_DATA = 1003
CODE_1004_RESERVED = 1004
CODE_1005_NO_STATUS_RECEIVED = 1005
CODE_1006_ABNORMAL_CLOSURE = 1006
CODE_1007_INVALID_FRAME_PAYLOAD_DATA = 1007
CODE_1008_POLICY_VIOLATION = 1008
CODE_1009_MESSAGE_TOO_BIG = 1009
CODE_1010_MANDATORY_EXIT = 1010
CODE_1011_INTERNAL_SERVER_ERROR = 1011
CODE_1012_SERVICE_RESTART = 1012
CODE_1013_TRY_AGAIN_LATER = 1013
CODE_1014_BAD_GATEWAY = 1014
CODE_1015_TLS_HANDSHAKE = 1015
CODE_3000_UNAUTHORIZED = 3000
