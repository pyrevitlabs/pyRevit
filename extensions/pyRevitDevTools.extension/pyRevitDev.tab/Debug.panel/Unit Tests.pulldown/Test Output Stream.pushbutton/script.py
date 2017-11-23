# -*- coding: utf-8 -*-
from pyrevit import DB
from pyrevit import script


__context__ = 'zerodoc'


output = script.get_output()
logger = script.get_logger()


output.print_md('**Testing log levels:**')
logger.critical('Test Log Level')
logger.warning('Test Log Level')
logger.info('Test Log Level :ok_hand_sign:')
logger.debug('Test Log Level')

output.print_md('**Testing large buffer output (>1023 chars):**')
output.print_html('<div style="background:green">{}</div>'.format('Test '*256))

output.print_md('**Testing linkify:**')
print('Clickable element id: {}'
      .format(output.linkify(DB.ElementId(1557))))

output.print_md('**Testing code block:**')
output.print_code(
"""
#include <iostream>
using namespace std;

int main()
{
    cout << "Hello world!" << endl;
    return 0;
}
"""
)
