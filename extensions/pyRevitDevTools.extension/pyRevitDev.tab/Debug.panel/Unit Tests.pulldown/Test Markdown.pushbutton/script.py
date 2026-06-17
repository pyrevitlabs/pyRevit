# -*- coding: utf-8 -*-
from pyrevit import script


output = script.get_output()
output.set_title('Markdown Tests')

output.print_md('# Heading 1')
output.print_md('## Heading 2')
output.print_md('### Heading 3')

output.print_md('**Testing inline styles:**')
output.print_md('Normal text, **bold text**, __also bold__, '
                '*italic text*, _also italic_, and `inline code`.')

output.print_md('**Testing list:**')
output.print_md('- first item\n- second *italic* item\n- third **bold** item')

output.print_md('**Testing divider:**')
output.print_md('-----')

output.print_md('**Testing markdown table with alignment:**')
output.print_md(
    '| Left | Center | Right |\n'
    '| :--- | :----: | ----: |\n'
    '| a | *b* | **c** |\n'
    '| d | e | f |'
    )

output.print_md('**Testing print_table (headers left-aligned):**')
output.print_table([['1589784', 'Family1 (*Category*: Generic Models)']],
                   columns=['Id', 'Name'],
                   title='Count Faces')
