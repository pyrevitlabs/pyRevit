## Limits

The plain-text fallback applies only when the WebView2 Runtime is missing.
It preserves script text, table rows and columns, Copy All Text, keyboard selection and copying, and Freeze/Unfreeze buffering; it does not render HTML styling, charts, links, or injected JavaScript.
Copy All Text reads the visible fallback text rather than the unavailable browser; the original fallback's empty-copy behavior is fixed.
Save Contents, Open in Browser, and Print still require WebView2 and do not export or print the fallback text.
A WebView2 initialization failure with the runtime installed is a separate path: the first output now shows the window before initialization is checked, but no plain-text fallback is created, and a failed initialization can leave a blank window with discarded output reported once in the renderer log.
Install or repair WebView2 and reopen the output window to restore browser-backed features.
