#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU Lesser General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (LGPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of LGPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/lgpl-2.0.txt.
#
# Jeff Ortel <jortel@redhat.com>
#

"""
PAM module for python
"""
from ctypes import CDLL, POINTER, Structure, CFUNCTYPE, cast, byref, sizeof
from ctypes import c_void_p, c_uint, c_char_p, c_char, c_int
from ctypes.util import find_library
from logging import getLogger

SERVICE = 'passwd'
PROMPT_ECHO_OFF = 1
PROMPT_ECHO_ON = 2
ERROR_MSG = 3
TEXT_INFO = 4
REINITIALIZE_CRED = 0x0008

log = getLogger(__name__)


class Lib(object):
    """
    Represents external libs.
    """

    libc = None
    libpam = None
    calloc = None
    strdup = None
    pam_start = None
    pam_authenticate = None
    pam_setcred = None
    pam_end = None
    loaded = False

    @staticmethod
    def load():
        """
        Load and initialize both libc and libpam.
        The libs are only loaded and initialized once so this method
        can safely be called multiple times.
        """
        if Lib.loaded:
            return

        Lib.libc = CDLL(find_library('c'))
        Lib.libpam = CDLL(find_library('pam'))

        Lib.calloc = Lib.libc.calloc
        Lib.calloc.restype = c_void_p
        Lib.calloc.argtypes = [c_uint, c_uint]

        Lib.strdup = Lib.libc.strdup
        Lib.strdup.argstypes = [c_char_p]
        Lib.strdup.restype = POINTER(c_char)

        Lib.pam_start = Lib.libpam.pam_start
        Lib.pam_start.restype = c_int
        Lib.pam_start.argtypes = [
            c_char_p,
            c_char_p,
            POINTER(PamConversation),
            POINTER(PamHandle)
        ]

        Lib.pam_authenticate = Lib.libpam.pam_authenticate
        Lib.pam_authenticate.restype = c_int
        Lib.pam_authenticate.argtypes = [PamHandle, c_int]

        Lib.pam_setcred = Lib.libpam.pam_setcred
        Lib.pam_setcred.restype = c_int
        Lib.pam_setcred.argtypes = [PamHandle, c_int]

        Lib.pam_end = Lib.libpam.pam_end
        Lib.pam_end.restype = c_int
        Lib.pam_end.argtypes = [PamHandle, c_int]

        Lib.loaded = True


class PamHandle(Structure):
    _fields_ = [
        ('ptr', c_void_p)
    ]

    def __init__(self):
        Structure.__init__(self)
        self.handle = 0


class PamMessage(Structure):
    _fields_ = [
        ('style', c_int),
        ('message', c_char_p),
    ]


class PamResponse(Structure):
    _fields_ = [
        ('reply', c_char_p),
        ('retval', c_int),
    ]


CONVERSATION = \
    CFUNCTYPE(
        c_int,
        c_int,
        POINTER(POINTER(PamMessage)),
        POINTER(POINTER(PamResponse)),
        c_void_p)


class PamConversation(Structure):
    _fields_ = [
        ('function', CONVERSATION),
        ('ptr', c_void_p)
    ]


def authenticate(user, password, service=None):
    """
    Authenticate using PAM.
    :param user: The username to authenticate.
    :type user: str
    :param password: The password to authenticate.
    :type password: str
    :param service: The PAM service to authenticate against (default: passwd)
    :return: True if authentication succeeds.
    :rtype: bool
    """
    try:
        return _authenticate(user, password, service or SERVICE)
    except Exception:
        log.exception('PAM authentication failed')
        return False


def _authenticate(user, password, service):
    @CONVERSATION
    def dialog(n_messages, messages, p_response, data):
        ptr = Lib.calloc(n_messages, sizeof(PamResponse))
        p_response[0] = cast(ptr, POINTER(PamResponse))
        for i in range(n_messages):
            if messages[i].contents.style == PROMPT_ECHO_OFF:
                p_response.contents[i].reply = cast(Lib.strdup(password), c_char_p)
                p_response.contents[i].retval = 0
        return 0

    Lib.load()
    handle = PamHandle()
    conversation = PamConversation(dialog, 0)
    retval = Lib.pam_start(service, user, byref(conversation), byref(handle))
    if retval != 0:
        # PAM start failed
        return False
    retval = Lib.pam_authenticate(handle, 0)
    authenticated = (retval == 0)
    if authenticated:
        retval = Lib.pam_setcred(handle, REINITIALIZE_CRED)
    Lib.pam_end(handle, retval)
    return authenticated
