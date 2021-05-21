import os.path as op
import pprint
import yaml

import exts


class CtxParser:
    """Testing context parser from bundle.yaml file"""
    def _parse_context_list(self, context):
        context_rules = []

        str_items = [x for x in context if isinstance(x, str)]
        context_rules.append(
            exts.MDATA_COMMAND_CONTEXT_RULE.format(
                rule=exts.MDATA_COMMAND_CONTEXT_ALL_SEP.join(str_items)
                )
        )

        dict_items = [x for x in context if isinstance(x, dict)]
        for ditem in dict_items:
            context_rules.extend(self._parse_context_dict(ditem))

        return context_rules

    def _parse_context_dict(self, context):
        context_rules = []
        for ctx_key, ctx_value in context.items():
            if ctx_key == exts.MDATA_COMMAND_CONTEXT_TYPE:
                context_type = (
                    exts.MDATA_COMMAND_CONTEXT_ANY_SEP
                    if ctx_value == exts.MDATA_COMMAND_CONTEXT_ANY
                    else exts.MDATA_COMMAND_CONTEXT_ALL_SEP
                )
                continue

            if isinstance(ctx_value, str):
                ctx_value = [ctx_value]

            key = ctx_key.lower()
            condition = ""
            # all
            if key == exts.MDATA_COMMAND_CONTEXT_ALL \
                    or key == exts.MDATA_COMMAND_CONTEXT_NOTALL:
                condition = exts.MDATA_COMMAND_CONTEXT_ALL_SEP

            # any
            elif key == exts.MDATA_COMMAND_CONTEXT_ANY \
                    or key == exts.MDATA_COMMAND_CONTEXT_NOTANY:
                condition = exts.MDATA_COMMAND_CONTEXT_ANY_SEP

            # except
            elif key == exts.MDATA_COMMAND_CONTEXT_EXACT \
                    or key == exts.MDATA_COMMAND_CONTEXT_NOTEXACT:
                condition = exts.MDATA_COMMAND_CONTEXT_EXACT_SEP

            context = condition.join(
                [x for x in ctx_value if isinstance(x, str)]
                )
            formatted_rule = \
                exts.MDATA_COMMAND_CONTEXT_RULE.format(rule=context)
            if key.startswith(exts.MDATA_COMMAND_CONTEXT_NOT):
                formatted_rule = "!" + formatted_rule
            context_rules.append(formatted_rule)
        return context_rules

    def _parse_context_directives(self, context):
        context_rules = []

        if isinstance(context, str):
            context_rules.append(
                exts.MDATA_COMMAND_CONTEXT_RULE.format(rule=context)
            )
        elif isinstance(context, list):
            context_rules.extend(self._parse_context_list(context))

        elif isinstance(context, dict):
            if "rule" in context:
                return context["rule"]
            context_rules.extend(self._parse_context_dict(context))

        context_type = exts.MDATA_COMMAND_CONTEXT_ALL_SEP
        return context_type.join(context_rules)


p = CtxParser()
with open('dev/worksheets/context_parser/test_contexts.yaml', 'r') as tf:
    test_data = yaml.load(tf, Loader=yaml.FullLoader)
    for test, data in test_data.items():
        if test.startswith('context') and not test.endswith('_result'):
            # grab expected result
            if isinstance(data, list):
                for item in list(data):
                    if isinstance(item, dict) and item.get('result', None):
                        expected = item.get('result', None)
                        data.remove(item)
                        break;
            elif isinstance(data, dict):
                expected = data['result']
                data.pop('result')
            elif isinstance(data, str):
                expected = test_data[test + "_result"]

            res = p._parse_context_directives(data)
            print('-'* 60)
            if not expected == res:
                print(f'🍄 FAIL "{test}"\n'
                      f'Expected: {expected}\n'
                      f'Parsed:   {res}\n'
                       'Data:')
                pprint.pprint(data)
            else:
                print(f'🍏 PASS "{test}" --> {res}')
    print()