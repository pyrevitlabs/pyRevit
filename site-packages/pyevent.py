#####################################################################################
#
#  Copyright (c) Microsoft Corporation. All rights reserved.
#
# This source code is subject to terms and conditions of the Apache License, Version 2.0. A 
# copy of the license can be found in the License.html file at the root of this distribution. If 
# you cannot locate the  Apache License, Version 2.0, please send an email to 
# ironpy@microsoft.com. By using this source code in any fashion, you are agreeing to be bound 
# by the terms of the Apache License, Version 2.0.
#
# You must not remove this notice, or any other, from this software.
#
#
#####################################################################################

class event(object):
    """Provides CLR event-like functionality for Python.  This is a public
    event helper that allows adding and removing handlers."""
    __slots__ = ['handlers']
        
    def __init__(self):
        self.handlers = []
    
    def __iadd__(self, other):
        if isinstance(other, event):
            self.handlers.extend(other.handlers)
        elif isinstance(other, event_caller):
            self.handlers.extend(other.event.handlers)
        else:
            if not callable(other):
                raise TypeError, "cannot assign to event unless value is callable"
            self.handlers.append(other)
        return self
        
    def __isub__(self, other):
        if isinstance(other, event):
            newEv = []
            for x in self.handlers:
                if not other.handlers.contains(x):
                    newEv.append(x)
            self.handlers = newEv
        elif isinstance(other, event_caller):
            newEv = []
            for x in self.handlers:
                if not other.event.handlers.contains(x):
                    newEv.append(x)
            self.handlers = newEv
        else:
            if other in self.handlers:
                self.handlers.remove(other)
        return self

    def make_caller(self):
        return event_caller(self)

class event_caller(object):
    """Provides CLR event-like functionality for Python.  This is the
    protected event caller that allows the owner to raise the event"""
    __slots__ = ['event']
    
    def __init__(self, event):
        self.event = event
            
    def __call__(self, *args):
        for ev in self.event.handlers:
            ev(*args)

    def __set__(self, val):
        raise ValueError, "cannot assign to an event, can only add or remove handlers"
    
    def __delete__(self, val):
        raise ValueError, "cannot delete an event, can only add or remove handlers"

    def __get__(self, instance, owner):
        return self


def make_event():
    """Creates an event object tuple.  The first value in the tuple can be
    exposed to allow external code to hook and unhook from the event.  The
    second value can be used to raise the event and can be stored in a
    private variable."""
    res = event()
    
    return (res, res.make_caller())
