# -*- coding: utf-8 -*-
from pyrevit import DB
from pyrevit import script

from pyrevit.runtime.types import ScriptOutputEmojis

__context__ = 'zerodoc'


output = script.get_output()
logger = script.get_logger()

output.set_title('Output Tests')

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

output.print_md('**Testing emojify:**')
emoji_str = ''
for e in ScriptOutputEmojis.emojiDict.Keys:
    emoji_str += ' :{}:'.format(e)

print(emoji_str)

output.print_md('**Testing code block:**')
output.print_code("""
#include <iostream>
using namespace std;

int main()
{
    cout << "Hello world!" << endl;
    return 0;
}
""")

output.print_table([[1, 2, 3],
                    [1, 2, 3],
                    [1, 2, 3]],
                   columns=['Col 1', 'Col 2', 'Col 3'],
                   formats=['', '', '{}%'],
                   title='Test Table')


data = [['结构', '结构', '结构结构', 80],
        ['结构', '结构', '结构', 45],
        ['row3', 'data', 'data', 45],
        ['结构结构', 'data', '结构', 45]]

output.print_table(table_data=data,
                   title="Example Table",
                   columns=["Row Name", "Column 1", "Column 2", "Percentage"],
                   formats=['', '', '', '{}%'],
                   last_line_style='color:red;')

output.update_progress(50, 100)
output.hide_progress()
output.unhide_progress()


output.print_md('**Testing output freeze:**')
output.freeze()

for i in range(5000):
    print(i)

output.unfreeze()

output.debug_mode = True

raise Exception('Testing long error reports...')
