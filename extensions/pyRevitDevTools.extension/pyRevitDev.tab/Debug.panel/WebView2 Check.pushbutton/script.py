# -*- coding: utf-8 -*-
"""Validate that the output window renders with WebView2 (Chromium).

Runs a battery of checks against the live output document: renderer engine
identity and runtime version, Chromium user agent, html/script/style
injection (including proof that injected scripts actually execute), markdown
link conversion, progress bar dom, revit:// deep-link anchors, the removed
legacy renderer property, and the WebView2 user-data folder. Results print
as a pass/fail table.
"""
import os

from pyrevit import script

output = script.get_output()
output.set_title('WebView2 Output Check')

WV2_USERDATA = os.path.join(
    os.environ.get('LOCALAPPDATA', ''), 'pyRevit', 'WebView2'
)

results = []


def check(name, func):
    """Run one check, capturing exceptions as a failure with the detail."""
    try:
        ok, detail = func()
    except Exception as ex:
        ok, detail = False, '{}: {}'.format(type(ex).__name__, ex)
    results.append((name, bool(ok), detail))


def t_engine():
    """Renderer must identify as WebView2/Chromium."""
    eng = output.renderer_engine
    return (eng == 'WebView2/Chromium', eng)


def t_version():
    """Runtime major version must be Chromium-era (>= 86), not IE (<= 11)."""
    ver = output.window.RendererVersion
    return (ver.Major >= 86, str(ver))


def t_user_agent():
    """Live user agent must be Chromium and carry no IE markers."""
    ua = output.evaluate_js('navigator.userAgent')
    ok = 'Chrome' in ua and 'Trident' not in ua and 'MSIE' not in ua
    return (ok, ua)


def t_head_meta():
    """Initial head must carry the WebView2 rendererversion meta, no IE meta."""
    head = output.get_head_html()
    ok = 'rendererversion' in head and 'X-UA-Compatible' not in head
    return (ok, 'rendererversion meta present, no IE meta')


def t_inject_head():
    """inject_to_head must land a style tag in the live head."""
    output.inject_to_head(
        'style',
        '#wv2check{color:purple;}',
        {'id': 'wv2check-style'}
    )
    return ('wv2check-style' in output.get_head_html(), 'style tag present in head')


def t_inject_body():
    """inject_to_body must land a queryable div in the live body."""
    output.inject_to_body('div', 'wv2 marker', {'id': 'wv2check-body'})
    r = output.evaluate_js('!!document.getElementById("wv2check-body")')
    return (str(r).lower() == 'true', 'marker div present in body')


def t_inject_script():
    """inject_script must create a script element that actually executes."""
    output.inject_script('window.__wv2checkValue = 42;')
    r = output.evaluate_js('window.__wv2checkValue')
    return (str(r) == '42', 'injected script executed, value={}'.format(r))


def t_add_style():
    """add_style must append a style tag to the head."""
    output.add_style('.wv2check-entry{letter-spacing:0.5px;}',
                     {'id': 'wv2check-style2'})
    return ('wv2check-style2' in output.get_head_html(), 'add_style tag present')


def t_markdown_link():
    """print_md must convert [text](url) into a real anchor."""
    output.print_md(
        'Markdown link check: '
        '[pyRevit Repo](https://github.com/pyrevitlabs/pyRevit)'
    )
    r = output.evaluate_js(
        '!!document.querySelector('
        '"a[href=\'https://github.com/pyrevitlabs/pyRevit\']")'
    )
    return (str(r).lower() == 'true', 'markdown link syntax rendered as anchor')


def t_revit_deeplink():
    """revit:// outputhelpers anchors must be present for click interception."""
    output.print_html(
        '<a href="revit://outputhelpers?command=print&amp;'
        'message=wv2check-deeplink">revit deep-link check</a>'
    )
    r = output.evaluate_js('!!document.querySelector("a[href^=\'revit://\']")')
    return (str(r).lower() == 'true', 'revit:// anchor present')


def t_progress_dom():
    """The html progress bar must respond to UpdateProgressBar."""
    output.window.UpdateProgressBar(1, 4)
    r = output.evaluate_js(
        '(document.getElementById("pbar") || {style: {}}).style.width'
    )
    return (str(r) == '25%', 'pbar width = {}'.format(r))


def t_legacy_renderer_removed():
    """output.renderer must raise, per the clean-break policy."""
    try:
        output.renderer
        return (False, 'output.renderer still returns an object')
    except NotImplementedError:
        return (True, 'output.renderer raises as designed')
    except Exception as ex:
        return (True, 'output.renderer raises ({})'.format(type(ex).__name__))


def t_userdata_folder():
    """The WebView2 user-data folder must exist under LocalAppData."""
    return (os.path.isdir(WV2_USERDATA), WV2_USERDATA)


def t_emoji_unicode():
    """Literal unicode emoji must survive into the live dom for Chromium."""
    output.print_html('<div id="wv2check-uni">✅ ❌ ⚠️ 🎯</div>')
    r = output.evaluate_js(
        'document.getElementById("wv2check-uni")'
        '.innerText.indexOf("✅") >= 0'
    )
    return (str(r).lower() == 'true', 'unicode emoji present in dom text')


def t_emoji_segoe():
    """Segoe UI Emoji must be the computed font of an emoji span."""
    output.print_html(
        '<span id="wv2check-segoe" '
        'style="font-family:\'Segoe UI Emoji\'">✅</span>'
    )
    r = output.evaluate_js(
        'getComputedStyle(document.getElementById("wv2check-segoe"))'
        '.fontFamily.indexOf("Segoe UI Emoji") >= 0'
    )
    return (str(r).lower() == 'true', 'computed font is Segoe UI Emoji')


def t_emoji_dll_pipeline():
    """Shortcodes printed through the pipeline must become img.emoji nodes."""
    output.print_html(
        '<div id="wv2check-dll">'
        ':heavy_check_mark: :cross_mark: :warning:</div>'
    )
    count = output.evaluate_js('document.querySelectorAll("img.emoji").length')
    literal = output.evaluate_js(
        'document.getElementById("wv2check-dll")'
        '.innerText.indexOf(":heavy_check_mark:") >= 0'
    )
    detail = 'img.emoji count={}, literal shortcode present={}'.format(
        count, str(literal).lower()
    )
    ok = str(count) not in ('0', 'null') and str(literal).lower() == 'false'
    return (ok, detail)


def t_emoji_dll_direct():
    """Direct Emojize call must produce an img span (dll-level diagnosis)."""
    try:
        from pyRevitLabs.Emojis import Emojis as DotNetEmojis
    except ImportError:
        import clr
        clr.AddReference('pyRevitLabs.Emojis')
        from pyRevitLabs.Emojis import Emojis as DotNetEmojis
    converted = DotNetEmojis.Emojize(':heavy_check_mark:')
    return (
        converted.startswith('<span><img'),
        converted[:60] + '...' if len(converted) > 60 else converted
    )


check('Renderer engine is WebView2', t_engine)
check('Runtime version is Chromium', t_version)
check('User agent is Chromium', t_user_agent)
check('Document head is WebView2-generated', t_head_meta)
check('inject_to_head works', t_inject_head)
check('inject_to_body works', t_inject_body)
check('inject_script executes', t_inject_script)
check('add_style works', t_add_style)
check('Markdown links convert', t_markdown_link)
check('revit:// deep-link anchors', t_revit_deeplink)
check('Progress bar dom', t_progress_dom)
check('Legacy renderer removed', t_legacy_renderer_removed)
check('WebView2 user-data folder', t_userdata_folder)
check('Emoji rendering: unicode (Chromium)', t_emoji_unicode)
check('Emoji rendering: Segoe UI Emoji font', t_emoji_segoe)
check('Emoji rendering: dll shortcodes', t_emoji_dll_pipeline)
check('Emoji conversion: direct Emojize call', t_emoji_dll_direct)

output.print_md('### WebView2 Output Validation')
output.print_md(
    'Engine: `{}` / Runtime: `{}`'.format(
        output.renderer_engine, output.renderer_version
    )
)
output.print_md('User agent: `{}`'.format(output.evaluate_js('navigator.userAgent')))

rows = []
for name, ok, detail in results:
    mark = '✅' if ok else '❌'
    rows.append(['{} {}'.format(mark, name), str(detail)])

output.print_table(rows, columns=['Check', 'Result'])

passed = len([r for r in results if r[1]])
output.print_md('**{} / {} checks passed**'.format(passed, len(results)))
if passed != len(results):
    output.mark_error()
