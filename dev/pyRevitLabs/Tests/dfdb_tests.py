# -*- coding: utf-8 -*-
#pylint: disable=C0111,E0401,C0301,C0103,C0413,W0703,W0611,W0702
"""ipy dfdb_tests.py <text_file> <userid> <number of records to test>

Example:
    ipy ./db_test.py dstorefile.txt eirannejad 20
    ipy ./db_test.py dstorefile.txt gamma 40
"""
from __future__ import print_function
import time
import sys
import os.path as op
import random

userdesktop = op.expandvars('%userprofile%\\desktop')
sys.path.append(
    op.join(userdesktop,
            r'gits\pyRevitLabs\pyRevitLabs\pyRevitLabs.DeffrelDB\bin\Debug')
    )

# import DFFDB module
import clr
from System.Collections.Generic import List
clr.AddReference('pyRevitLabs.DeffrelDB')
import pyRevitLabs.DeffrelDB as dfdb


# prepare connection ==========================================================
fstore = sys.argv[1]
requester = sys.argv[2]
MAX_RECORDS = int(sys.argv[3])

if not op.exists(fstore):
    fstore = op.join(userdesktop, fstore)

conn = dfdb.DataBase.Connect(fstore, requester, debug='--debug' in sys.argv)


ERRORS = []
ADDED_RECORDS = []

# prepare dbs =================================================================
TEST_DBS = {'db1': {'desc': "Some Description"},
            'db2': {'desc': "Some \"Complex\" Description"},
            'db3': {'desc': "Some $^$^#&^#& Description"}}

for dbkey in TEST_DBS:
    print('='*25)
    try:
        conn.ReadDB(dbkey)
        print('[  OK  ] %s read %s' % (requester, dbkey))
    except Exception as ex:
        print(ex)
        if "does not exist" not in str(ex):
            ERRORS.append(str(ex))
        dbdef = dfdb.DatabaseDefinition()
        dbdef.Description = TEST_DBS[dbkey]['desc']
        try:
            conn.CreateDB(dbkey, dbdef)
            print('[  OK  ] %s created %s' % (requester, dbkey))
        except Exception as ex:
            print(ex)
            ERRORS.append(str(ex))

# prepare dbs =================================================================
TEST_TABLES = {'table1': {'desc': "Some Description"},
               'table2': {'desc': "Some \"Complex\" Description"},
               'table3': {'desc': "Some $^$^#&^#& Description"}}

for dbkey in TEST_DBS:
    print('='*25)
    for tablekey in TEST_TABLES:
        try:
            tdef = conn.ReadTable(dbkey, dbkey + tablekey)
            print(tdef.Name)
            print(tdef.Description)
            print(tdef.Fields)
            print(tdef.Wires)
            print('[  OK  ] %s read %s:%s' % (requester, dbkey, tablekey))
        except Exception as ex:
            print(ex)
            if "does not exist" not in str(ex):
                ERRORS.append(str(ex))
            record_id = dfdb.TextField('record_id')
            record_text = dfdb.TextField('record_text')
            table_def = dfdb.TableDefinition()
            table_def.Fields = [record_id, record_text]
            table_def.Wires = [
                dfdb.Wire('record_id', 'record_id'),
                dfdb.Wire('record_id', 'cat_key')
                ]
            table_def.Description = TEST_TABLES[tablekey]['desc']
            try:
                conn.CreateTable(dbkey, dbkey + tablekey, table_def)
                print('[  OK  ] %s created %s:%s' % (requester, dbkey, tablekey))
            except Exception as ex:
                print(ex)
                ERRORS.append(str(ex))


# play with records ===========================================================
STRINGS = ['Example Keynote Text',
           'Example "Keynote" Text']

successful_records = 0
while successful_records < MAX_RECORDS:
    print('='*25)
    target_db = random.choice(TEST_DBS.keys())
    target_table = random.choice(TEST_TABLES.keys())
    rec_idx = random.randint(1, MAX_RECORDS * 4)
    table_id = target_db + target_table
    ridx = '%s_%s' % (table_id, rec_idx)
    rtext = random.choice(STRINGS)
    try:
        print('[  OK  ] %s adding %s' % (requester, ridx))
        conn.InsertRecord(target_db, table_id, ridx, {'record_text': rtext})
        successful_records += 1
        ADDED_RECORDS.append((target_db, table_id, ridx, rtext))
    except Exception as ex:
        print(ex)
        if "already exists" not in str(ex):
            ERRORS.append(str(ex))

# # batch insert
# successful_records = 0
# target_db = random.choice(TEST_DBS.keys())
# target_table = random.choice(TEST_TABLES.keys())
# table_id = target_db + target_table
# print('[  OK  ] %s is batch inserting into %s' % (requester, table_id))
# try:
#     conn.BEGIN(target_db, table_id)

#     while successful_records < MAX_RECORDS:
#         print('='*25)
#         rec_idx = random.randint(1, MAX_RECORDS * 4)
#         ridx = '%s_%s' % (table_id, rec_idx)
#         rtext = random.choice(STRINGS)
#         try:
#             print('[  OK  ] %s adding %s' % (requester, ridx))
#             conn.InsertRecord(target_db, table_id, ridx, {'record_text': rtext})
#             successful_records += 1
#             ADDED_RECORDS.append((target_db, table_id, ridx, rtext))
#         except Exception as ex:
#             print(ex)
#             if "already exists" not in str(ex):
#                 ERRORS.append(str(ex))
#     conn.END()

# except Exception as ex:
#     print(ex)
#     if "is restricted by" not in str(ex):
#         ERRORS.append(str(ex))

# # verify inserted records  ====================================================
# PASSED_INSERT_TEST = True
# for record_log in ADDED_RECORDS:
#     print('Verifying: {}'.format(record_log))
#     try:
#         rfields = conn.ReadRecord(record_log[0], record_log[1], record_log[2])
#         if not rfields:
#             ERRORS.append('Failed reading record: {}'.format(record_log[2]))
#             PASSED_INSERT_TEST = False
#         if not rfields['record_text'] == record_log[3]:
#             ERRORS.append(
#                 'Failed record text matching: {} \"{}\" != \"{}\"'
#                 .format(record_log[2], rfields['record_text'], record_log[3])
#                 )
#             PASSED_INSERT_TEST = False
#     except Exception as ex:
#         print(ex)
#         ERRORS.append(str(ex))
#         PASSED_INSERT_TEST = False

# if ERRORS:
#     print('[ FAIL ] %s has failures:' % (requester))
#     for error in ERRORS:
#         print(error)

# if PASSED_INSERT_TEST:
#     print('[  OK  ] %s passed all read tests for %s records'
#           % (requester, len(ADDED_RECORDS)))
# else:
#     print('[ FAIL ] %s failed some read tests.' % (requester))
