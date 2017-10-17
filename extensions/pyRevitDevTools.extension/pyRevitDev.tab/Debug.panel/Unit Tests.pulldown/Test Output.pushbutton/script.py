# -*- coding: utf-8 -*-
import clr
import sys
import scriptutils as su

from Autodesk.Revit.DB import ElementId


__context__ = 'zerodoc'


su.this_script.output.print_md('**Testing log levels:**')
su.logger.critical('Test Log Level')
su.logger.warning('Test Log Level')
su.logger.info('Test Log Level :ok_hand_sign:')
su.logger.debug('Test Log Level')

su.this_script.output.print_md('**Testing large buffer output (>1023 chars):**')
su.this_script.output.print_html('<div style="background:green">{}</div>'.format('Test '*256))

su.this_script.output.print_md('**Testing linkify:**')
print('Clickable element id: {}'.format(su.this_script.output.linkify(ElementId(1557))))
