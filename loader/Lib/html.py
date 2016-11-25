# -*- encoding: utf8 -*-
#
# $Id: html.py 5409 2011-06-29 07:07:25Z rjones $
# $HeadURL: svn+ssh://svn/svn/trunk/api/eklib/html.py $
#
'''Simple, elegant HTML, XHTML and XML generation.

Constructing your HTML
----------------------

To construct HTML start with an instance of ``html.HTML()``. Add
tags by accessing the tag's attribute on that object. For example:

>>> from html import HTML
>>> h = HTML()
>>> h.p('Hello, world!')
>>> print h                          # or print(h) in python 3+
<p>Hello, world!</p>

You may supply a tag name and some text contents when creating a HTML
instance:

>>> h = HTML('html', 'text')
>>> print h
<html>text</html>

You may also append text content later using the tag's ``.text()`` method
or using augmented addition ``+=``. Any HTML-specific characters (``<>&"``)
in the text will be escaped for HTML safety as appropriate unless
``escape=False`` is passed. Each of the following examples uses a new
``HTML`` instance:

>>> p = h.p('hello world!\\n')
>>> p.br
>>> p.text('more &rarr; text', escape=False)
>>> p += ' ... augmented'
>>> h.p
>>> print h
<p>hello, world!<br>more &rarr; text ... augmented</p>
<p>

Note also that the top-level ``HTML`` object adds newlines between tags by
default. Finally in the above you'll see an empty paragraph tag - tags with
no contents get no closing tag.

If the tag should have sub-tags you have two options. You may either add
the sub-tags directly on the tag:

>>> l = h.ol
>>> l.li('item 1')
>>> l.li.b('item 2 > 1')
>>> print h
<ol>
<li>item 1</li>
<li><b>item 2 &gt; 1</b></li>
</ol>

Note that the default behavior with lists (and tables) is to add newlines
between sub-tags to generate a nicer output. You can also see in that
example the chaining of tags in ``l.li.b``.

Tag attributes may be passed in as well:

>>> t = h.table(border='1')
>>> for i in range(2):
>>>   r = t.tr
>>>   r.td('column 1')
>>>   r.td('column 2')
>>> print t
<table border="1">
<tr><td>column 1</td><td>column 2</td></tr>
<tr><td>column 1</td><td>column 2</td></tr>
</table>

A variation on the above is to use a tag as a context variable. The
following is functionally identical to the first list construction but
with a slightly different sytax emphasising the HTML structure:

>>> with h.ol as l:
...   l.li('item 1')
...   l.li.b('item 2 > 1')

You may turn off/on adding newlines by passing ``newlines=False`` or
``True`` to the tag (or ``HTML`` instance) at creation time:

>>> l = h.ol(newlines=False)
>>> l.li('item 1')
>>> l.li('item 2')
>>> print h
<ol><li>item 1</li><li>item 2</li></ol>

Since we can't use ``class`` as a keyword, the library recognises ``klass``
as a substitute:

>>> print h.p(content, klass="styled")
<p class="styled">content</p>


Unicode
-------

``HTML`` will work with either regular strings **or** unicode strings, but
not **both at the same time**.

Obtain the final unicode string by calling ``unicode()`` on the ``HTML``
instance:

>>> h = HTML()
>>> h.p(u'Some Euro: €1.14')
>>> unicode(h)
u'<p>Some Euro: €1.14</p>'

If (under Python 2.x) you add non-unicode strings or attempt to get the
resultant HTML source through any means other than ``unicode()`` then you
will most likely get one of the following errors raised:

UnicodeDecodeError
   Probably means you've added non-unicode strings to your HTML.
UnicodeEncodeError
   Probably means you're trying to get the resultant HTML using ``print``
   or ``str()`` (or ``%s``).


How generation works
--------------------

The HTML document is generated when the ``HTML`` instance is "stringified".
This could be done either by invoking ``str()`` on it, or just printing it.
It may also be returned directly as the "iterable content" from a WSGI app
function.

You may also render any tag or sub-tag at any time by stringifying it.

Tags with no contents (either text or sub-tags) will have no closing tag.
There is no "special list" of tags that must always have closing tags, so
if you need to force a closing tag you'll need to provide some content,
even if it's just a single space character.

Rendering doesn't affect the HTML document's state, so you can add to or
otherwise manipulate the HTML after you've stringified it.


Creating XHTML
--------------

To construct XHTML start with an instance of ``html.XHTML()`` and use it
as you would an ``HTML`` instance. Empty elements will now be rendered
with the appropriate XHTML minimized tag syntax. For example:

>>> from html import XHTML
>>> h = XHTML()
>>> h.p
>>> h.br
>>> print h
<p></p>
<br />


Creating XML
------------

A slight tweak to the ``html.XHTML()`` implementation allows us to generate
arbitrary XML using ``html.XML()``:

>>> from html import XML
>>> h = XML('xml')
>>> h.p
>>> h.br('hi there')
>>> print h
<xml>
<p />
<br>hi there</br>
</xml>


Tags with difficult names
-------------------------

If your tag name isn't a valid Python identifier name, or if it's called
"text" or "raw_text" you can add your tag slightly more manually:

>>> from html import XML
>>> h = XML('xml')
>>> h += XML('some-tag', 'some text')
>>> h += XML('text', 'some text')
>>> print h
<xml>
<some-tag>some text</some-tag>
<text>some text</text>
</xml>


Version History (in Brief)
--------------------------

- 1.16 detect and raise a more useful error when some WSGI frameworks
  attempt to call HTML.read(). Also added ability to add new content using
  the += operator.
- 1.15 fix Python 3 compatibility (unit tests)
- 1.14 added plain XML support
- 1.13 allow adding (X)HTML instances (tags) as new document content
- 1.12 fix handling of XHTML empty tags when generating unicode
  output (thanks Carsten Eggers)
- 1.11 remove setuptools dependency
- 1.10 support plain ol' distutils again
- 1.9 added unicode support for Python 2.x
- 1.8 added Python 3 compatibility
- 1.7 added Python 2.5 compatibility and escape argument to tag
  construction
- 1.6 added .raw_text() and and WSGI compatibility
- 1.5 added XHTML support
- 1.3 added more documentation, more tests
- 1.2 added special-case klass / class attribute
- 1.1 added escaping control
- 1.0 was the initial release

----

I would be interested to know whether this module is useful - if you use it
please indicate so at https://www.ohloh.net/p/pyhtml

This code is copyright 2009-2011 eKit.com Inc (http://www.ekit.com/)
See the end of the source file for the license of use.
XHTML support was contributed by Michael Haubenwallner.
'''
from __future__ import with_statement
__version__ = '1.16'

import sys
import cgi
import unittest


class HTML(object):
    '''Easily generate HTML.

    >>> print HTML('html', 'some text')
    <html>some text</html>
    >>> print HTML('html').p('some text')
    <html><p>some text</p></html>

    If a name is not passed in then the instance becomes a container for
    other tags that itself generates no tag:

    >>> h = HTML()
    >>> h.p('text')
    >>> h.p('text')
    print h
    <p>some text</p>
    <p>some text</p>

    '''
    newline_default_on = set('table ol ul dl'.split())

    def __init__(self, name=None, text=None, stack=None, newlines=True,
            escape=True):
        self._name = name
        self._content = []
        self._attrs = {}
        # insert newlines between content?
        if stack is None:
            stack = [self]
            self._top = True
            self._newlines = newlines
        else:
            self._top = False
            self._newlines = name in self.newline_default_on
        self._stack = stack
        if text is not None:
            self.text(text, escape)

    def __getattr__(self, name):
        # adding a new tag or newline
        if name == 'newline':
            e = '\n'
        else:
            e = self.__class__(name, stack=self._stack)
        if self._top:
            self._stack[-1]._content.append(e)
        else:
            self._content.append(e)
        return e

    def __iadd__(self, other):
        if self._top:
            self._stack[-1]._content.append(other)
        else:
            self._content.append(other)
        return self

    def text(self, text, escape=True):
        '''Add text to the document. If "escape" is True any characters
        special to HTML will be escaped.
        '''
        if escape:
            text = cgi.escape(text)
        # adding text
        if self._top:
            self._stack[-1]._content.append(text)
        else:
            self._content.append(text)

    def raw_text(self, text):
        '''Add raw, unescaped text to the document. This is useful for
        explicitly adding HTML code or entities.
        '''
        return self.text(text, escape=False)

    def __call__(self, *content, **kw):
        if self._name == 'read':
            if len(content) == 1 and isinstance(content[0], int):
                raise TypeError('you appear to be calling read(%d) on '
                    'a HTML instance' % content)
            elif len(content) == 0:
                raise TypeError('you appear to be calling read() on a '
                    'HTML instance')

        # customising a tag with content or attributes
        escape = kw.pop('escape', True)
        if content:
            if escape:
                self._content = list(map(cgi.escape, content))
            else:
                self._content = content
        if 'newlines' in kw:
            # special-case to allow control over newlines
            self._newlines = kw.pop('newlines')
        for k in kw:
            if k == 'klass':
                self._attrs['class'] = cgi.escape(kw[k], True)
            else:
                self._attrs[k] = cgi.escape(kw[k], True)
        return self

    def __enter__(self):
        # we're now adding tags to me!
        self._stack.append(self)
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        # we're done adding tags to me!
        self._stack.pop()

    def __repr__(self):
        return '<HTML %s 0x%x>' % (self._name, id(self))

    def _stringify(self, str_type):
        # turn me and my content into text
        join = '\n' if self._newlines else ''
        if self._name is None:
            return join.join(map(str_type, self._content))
        a = ['%s="%s"' % i for i in self._attrs.items()]
        l = [self._name] + a
        s = '<%s>%s' % (' '.join(l), join)
        if self._content:
            s += join.join(map(str_type, self._content))
            s += join + '</%s>' % self._name
        return s

    def __str__(self):
        return self._stringify(str)

    def __unicode__(self):
        return self._stringify(unicode)

    def __iter__(self):
        return iter([str(self)])


class XHTML(HTML):
    '''Easily generate XHTML.
    '''
    empty_elements = set('base meta link hr br param img area input col \
        colgroup basefont isindex frame'.split())

    def _stringify(self, str_type):
        # turn me and my content into text
        # honor empty and non-empty elements
        join = '\n' if self._newlines else ''
        if self._name is None:
            return join.join(map(str_type, self._content))
        a = ['%s="%s"' % i for i in self._attrs.items()]
        l = [self._name] + a
        s = '<%s>%s' % (' '.join(l), join)
        if self._content or not(self._name.lower() in self.empty_elements):
            s += join.join(map(str_type, self._content))
            s += join + '</%s>' % self._name
        else:
            s = '<%s />%s' % (' '.join(l), join)
        return s


class XML(XHTML):
    '''Easily generate XML.

    All tags with no contents are reduced to self-terminating tags.
    '''
    newline_default_on = set()          # no tags are special

    def _stringify(self, str_type):
        # turn me and my content into text
        # honor empty and non-empty elements
        join = '\n' if self._newlines else ''
        if self._name is None:
            return join.join(map(str_type, self._content))
        a = ['%s="%s"' % i for i in self._attrs.items()]
        l = [self._name] + a
        s = '<%s>%s' % (' '.join(l), join)
        if self._content:
            s += join.join(map(str_type, self._content))
            s += join + '</%s>' % self._name
        else:
            s = '<%s />%s' % (' '.join(l), join)
        return s


class TestCase(unittest.TestCase):
    def test_empty_tag(self):
        'generation of an empty HTML tag'
        self.assertEquals(str(HTML().br), '<br>')

    def test_empty_tag_xml(self):
        'generation of an empty XHTML tag'
        self.assertEquals(str(XHTML().br), '<br />')

    def test_tag_add(self):
        'test top-level tag creation'
        self.assertEquals(str(HTML('html', 'text')), '<html>\ntext\n</html>')

    def test_tag_add_no_newline(self):
        'test top-level tag creation'
        self.assertEquals(str(HTML('html', 'text', newlines=False)),
            '<html>text</html>')

    def test_iadd_tag(self):
        "test iadd'ing a tag"
        h = XML('xml')
        h += XML('some-tag', 'spam', newlines=False)
        h += XML('text', 'spam', newlines=False)
        self.assertEquals(str(h),
            '<xml>\n<some-tag>spam</some-tag>\n<text>spam</text>\n</xml>')

    def test_iadd_text(self):
        "test iadd'ing text"
        h = HTML('html', newlines=False)
        h += 'text'
        h += 'text'
        self.assertEquals(str(h), '<html>texttext</html>')

    def test_xhtml_match_tag(self):
        'check forced generation of matching tag when empty'
        self.assertEquals(str(XHTML().p), '<p></p>')

    if sys.version_info[0] == 2:
        def test_empty_tag_unicode(self):
            'generation of an empty HTML tag'
            self.assertEquals(unicode(HTML().br), unicode('<br>'))

        def test_empty_tag_xml_unicode(self):
            'generation of an empty XHTML tag'
            self.assertEquals(unicode(XHTML().br), unicode('<br />'))

        def test_xhtml_match_tag_unicode(self):
            'check forced generation of matching tag when empty'
            self.assertEquals(unicode(XHTML().p), unicode('<p></p>'))

    def test_just_tag(self):
        'generate HTML for just one tag'
        self.assertEquals(str(HTML().br), '<br>')

    def test_just_tag_xhtml(self):
        'generate XHTML for just one tag'
        self.assertEquals(str(XHTML().br), '<br />')

    def test_xml(self):
        'generate XML'
        self.assertEquals(str(XML().br), '<br />')
        self.assertEquals(str(XML().p), '<p />')
        self.assertEquals(str(XML().br('text')), '<br>text</br>')

    def test_para_tag(self):
        'generation of a tag with contents'
        h = HTML()
        h.p('hello')
        self.assertEquals(str(h), '<p>hello</p>')

    def test_escape(self):
        'escaping of special HTML characters in text'
        h = HTML()
        h.text('<>&')
        self.assertEquals(str(h), '&lt;&gt;&amp;')

    def test_no_escape(self):
        'no escaping of special HTML characters in text'
        h = HTML()
        h.text('<>&', False)
        self.assertEquals(str(h), '<>&')

    def test_escape_attr(self):
        'escaping of special HTML characters in attributes'
        h = HTML()
        h.br(id='<>&"')
        self.assertEquals(str(h), '<br id="&lt;&gt;&amp;&quot;">')

    def test_subtag_context(self):
        'generation of sub-tags using "with" context'
        h = HTML()
        with h.ol:
            h.li('foo')
            h.li('bar')
        self.assertEquals(str(h), '<ol>\n<li>foo</li>\n<li>bar</li>\n</ol>')

    def test_subtag_direct(self):
        'generation of sub-tags directly on the parent tag'
        h = HTML()
        l = h.ol
        l.li('foo')
        l.li.b('bar')
        self.assertEquals(str(h),
            '<ol>\n<li>foo</li>\n<li><b>bar</b></li>\n</ol>')

    def test_subtag_direct_context(self):
        'generation of sub-tags directly on the parent tag in "with" context'
        h = HTML()
        with h.ol as l:
            l.li('foo')
            l.li.b('bar')
        self.assertEquals(str(h),
            '<ol>\n<li>foo</li>\n<li><b>bar</b></li>\n</ol>')

    def test_subtag_no_newlines(self):
        'prevent generation of newlines against default'
        h = HTML()
        l = h.ol(newlines=False)
        l.li('foo')
        l.li('bar')
        self.assertEquals(str(h), '<ol><li>foo</li><li>bar</li></ol>')

    def test_add_text(self):
        'add text to a tag'
        h = HTML()
        p = h.p('hello, world!\n')
        p.text('more text')
        self.assertEquals(str(h), '<p>hello, world!\nmore text</p>')

    def test_add_text_newlines(self):
        'add text to a tag with newlines for prettiness'
        h = HTML()
        p = h.p('hello, world!', newlines=True)
        p.text('more text')
        self.assertEquals(str(h), '<p>\nhello, world!\nmore text\n</p>')

    def test_doc_newlines(self):
        'default document adding newlines between tags'
        h = HTML()
        h.br
        h.br
        self.assertEquals(str(h), '<br>\n<br>')

    def test_doc_no_newlines(self):
        'prevent document adding newlines between tags'
        h = HTML(newlines=False)
        h.br
        h.br
        self.assertEquals(str(h), '<br><br>')

    def test_unicode(self):
        'make sure unicode input works and results in unicode output'
        h = HTML(newlines=False)
        # Python 3 compat
        try:
            unicode = unicode
            TEST = 'euro \xe2\x82\xac'.decode('utf8')
        except:
            unicode = str
            TEST = 'euro €'
        h.p(TEST)
        self.assertEquals(unicode(h), '<p>%s</p>' % TEST)

    def test_table(self):
        'multiple "with" context blocks'
        h = HTML()
        with h.table(border='1'):
            for i in range(2):
                with h.tr:
                    h.td('column 1')
                    h.td('column 2')
        self.assertEquals(str(h), '''<table border="1">
<tr><td>column 1</td><td>column 2</td></tr>
<tr><td>column 1</td><td>column 2</td></tr>
</table>''')

if __name__ == '__main__':
    unittest.main()


# Copyright (c) 2009 eKit.com Inc (http://www.ekit.com/)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# vim: set filetype=python ts=4 sw=4 et si
