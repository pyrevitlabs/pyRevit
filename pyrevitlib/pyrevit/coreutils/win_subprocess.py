# -*- coding: utf-8 -*-
"""Copyright (C) 2021 Valentin Lab

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

1. Redistributions of source code must retain the above copyright
notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above
copyright notice, this list of conditions and the following
disclaimer in the documentation and/or other materials provided
with the distribution.

3. Neither the name of the copyright holder nor the names of its
contributors may be used to endorse or promote products derived
from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
OF THE POSSIBILITY OF SUCH DAMAGE.
"""

# issue: https://bugs.python.org/issue19264

import ctypes
import subprocess
import _subprocess
from ctypes import byref, windll, c_char_p, c_wchar_p, c_void_p, \
     Structure, sizeof, c_wchar, WinError
from ctypes.wintypes import BYTE, WORD, LPWSTR, BOOL, DWORD, LPVOID, \
     HANDLE


# region Types

CREATE_UNICODE_ENVIRONMENT = 0x00000400
LPCTSTR = c_char_p
LPTSTR = c_wchar_p
LPSECURITY_ATTRIBUTES = c_void_p
LPBYTE  = ctypes.POINTER(BYTE)

class STARTUPINFOW(Structure):
    _fields_ = [
        ("cb",              DWORD),  ("lpReserved",    LPWSTR),
        ("lpDesktop",       LPWSTR), ("lpTitle",       LPWSTR),
        ("dwX",             DWORD),  ("dwY",           DWORD),
        ("dwXSize",         DWORD),  ("dwYSize",       DWORD),
        ("dwXCountChars",   DWORD),  ("dwYCountChars", DWORD),
        ("dwFillAtrribute", DWORD),  ("dwFlags",       DWORD),
        ("wShowWindow",     WORD),   ("cbReserved2",   WORD),
        ("lpReserved2",     LPBYTE), ("hStdInput",     HANDLE),
        ("hStdOutput",      HANDLE), ("hStdError",     HANDLE),
    ]

LPSTARTUPINFOW = ctypes.POINTER(STARTUPINFOW)


class PROCESS_INFORMATION(Structure):
    _fields_ = [
        ("hProcess",         HANDLE), ("hThread",          HANDLE),
        ("dwProcessId",      DWORD),  ("dwThreadId",       DWORD),
    ]

LPPROCESS_INFORMATION = ctypes.POINTER(PROCESS_INFORMATION)


class DUMMY_HANDLE(ctypes.c_void_p):

    def __init__(self, *a, **kw):
        super(DUMMY_HANDLE, self).__init__(*a, **kw)
        self.closed = False

    def Close(self):
        if not self.closed:
            windll.kernel32.CloseHandle(self)
            self.closed = True

    def __int__(self):
        return self.value


CreateProcessW = windll.kernel32.CreateProcessW
CreateProcessW.argtypes = [
    LPCTSTR, LPTSTR, LPSECURITY_ATTRIBUTES,
    LPSECURITY_ATTRIBUTES, BOOL, DWORD, LPVOID, LPCTSTR,
    LPSTARTUPINFOW, LPPROCESS_INFORMATION,
]
CreateProcessW.restype = BOOL
# endregion

# region Patched functions/classes

def CreateProcess(executable, args, _p_attr, _t_attr,
                  inherit_handles, creation_flags, env, cwd,
                  startup_info):
    """Create a process supporting unicode executable and args for win32

    Python implementation of CreateProcess using CreateProcessW for Win32

    """

    si = STARTUPINFOW(
        dwFlags=startup_info.dwFlags,
        wShowWindow=startup_info.wShowWindow,
        cb=sizeof(STARTUPINFOW),
        ## XXXvlab: not sure of the casting here to ints.
        hStdInput=int(startup_info.hStdInput),
        hStdOutput=int(startup_info.hStdOutput),
        hStdError=int(startup_info.hStdError),
    )

    wenv = None
    if env is not None:
        ## LPCWSTR seems to be c_wchar_p, so let's say CWSTR is c_wchar
        env = (unicode("").join([
            unicode("%s=%s\0") % (k, v)
            for k, v in env.items()])) + unicode("\0")
        wenv = (c_wchar * len(env))()
        wenv.value = env

    pi = PROCESS_INFORMATION()
    creation_flags |= CREATE_UNICODE_ENVIRONMENT

    if CreateProcessW(executable, args, None, None,
                      inherit_handles, creation_flags,
                      wenv, cwd, byref(si), byref(pi)):
        return (DUMMY_HANDLE(pi.hProcess), DUMMY_HANDLE(pi.hThread),
                pi.dwProcessId, pi.dwThreadId)
    raise WinError()


class Popen(subprocess.Popen):
    """This superseeds Popen and corrects a bug in cPython 2.7 implem"""

    def _execute_child(self, args, executable, preexec_fn, close_fds,
                       cwd, env, universal_newlines,
                       startupinfo, creationflags, shell, to_close,
                       p2cread, p2cwrite,
                       c2pread, c2pwrite,
                       errread, errwrite):
        """Code from part of _execute_child from Python 2.7 (9fbb65e)

        There are only 2 little changes concerning the construction of
        the the final string in shell mode: we preempt the creation of
        the command string when shell is True, because original function
        will try to encode unicode args which we want to avoid to be able to
        sending it as-is to ``CreateProcess``.

        """
        if not isinstance(args, subprocess.types.StringTypes):
            args = subprocess.list2cmdline(args)

        if startupinfo is None:
            startupinfo = subprocess.STARTUPINFO()
        if shell:
            startupinfo.dwFlags |= _subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = _subprocess.SW_HIDE
            comspec = os.environ.get("COMSPEC", unicode("cmd.exe"))
            args = unicode('{} /c "{}"').format(comspec, args)
            if (_subprocess.GetVersion() >= 0x80000000 or
                    os.path.basename(comspec).lower() == "command.com"):
                w9xpopen = self._find_w9xpopen()
                args = unicode('"%s" %s') % (w9xpopen, args)
                creationflags |= _subprocess.CREATE_NEW_CONSOLE

        super(Popen, self)._execute_child(args, executable,
            preexec_fn, close_fds, cwd, env, universal_newlines,
            startupinfo, creationflags, False, to_close, p2cread,
            p2cwrite, c2pread, c2pwrite, errread, errwrite)

# endregion

_subprocess.CreateProcess = CreateProcess
