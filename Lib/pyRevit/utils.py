import os
import sys
import os.path as op

def find_loader_directory():
    """Return the __init__ full directory address"""
    folder = op.dirname(op.dirname(op.dirname(__file__)))  # three steps back for /__init__/Lib/pyRevit
    return folder


def find_home_directory():
    """Return the pyRevit home directory address. This is the
       directory that contains the portable git, __init__, pyRevit, and other packages"""
    folder = op.dirname(find_loader_directory())
    return folder


def find_user_temp_directory():
    """Return the user temp directory %temp%"""
    return os.getenv('Temp')


def get_username():
    """Return the username from Revit API (Application.Username)"""
    uname = __revit__.Application.Username
    uname = uname.split('@')[0]         # if username is email
    uname = uname.replace('.','')       # removing dots since username will be used in file naming
    return uname


# import pickle
# import re
# import fnmatch
# import zipfile
# import hashlib
# import os
# from os import path
# import time
# from System.Diagnostics import Process

# from loader.logger import logger
# from loader.config import TEMPDIR, SCRIPTS_DLL_BASENAME, CACHE_FILE
# from loader.config import SCRIPTS_DIR


# def dump_session(session_data=None):
    # """ This can eventually be used to load/dump cache data"""
    # dump_filename = path.join(TEMPDIR, CACHE_FILE)
    # session = {}
    # session['hash'] = get_hash_from_dir(SCRIPTS_DIR)
    # session['data'] = session_data
    # try:
        # with open(dump_filename, 'w') as fp:
            # pickle.dump(session, fp)
        # logger.info('Parsed Session Dumped [{}]'.format(session['hash']))
    # except IOError as errmsg:
        # logger.error('Failed to dump_tabs from pickle: {}'.format(errmsg))


# def load_session():
    # """ This can eventually be used to load/dump cache data"""
    # dump_filename = path.join(TEMPDIR, CACHE_FILE)
    # try:
        # with open(dump_filename, 'r') as fp:
            # session = pickle.load(fp)
        # logger.info('Session Reloaded')
    # except IOError as errmsg:
        # logger.info('No pickled session found.')
        # return {'hash': None, 'data': None}
    # else:
        # return session['hash'], session['data']

# def get_hash_from_dir(script_dir):
    # """Creates a unique # to represent state of directory.
    # Zip and Hash worked well, but took ~1sec.
    # This method is very efficient and cheap.
    # It adds the last mod time (epoch time) of all files and folders."""
    # logger.info('Generating Hash of directory')
    # pat = r'(\.pkg)|(\.panel)|(\.tab)|(\.png)|(loader)'
    # hash_sum = 0
    # for root, dirs, files in os.walk(script_dir):
        # if re.search(pat, root, flags=re.IGNORECASE):
            # hash_sum += os.path.getmtime(root)
            # for filename in files:
                # modtime = path.getmtime(path.join(root, filename))
                # hash_sum += modtime
    # logger.debug('Session Hash: {}'.format(hash_sum))
    # return hash_sum

# def purge_unused_dlls(dll_filename):
    # """Deletes DLL files created by previous runs.
    # dll_name arg is used to prevent funciton from deleting dll used by session
    # """
    # revit_processes = Process.GetProcessesByName('Revit')
    # if len(revit_processes) > 1:
        # logger.info('More than 1 session Opened. Skipping DLL Cleanup.')
    # else:
        # tempfiles = os.listdir(TEMPDIR)
        # matching_files = fnmatch.filter(tempfiles, '*{}*'.format(
                                                         # SCRIPTS_DLL_BASENAME))
        # for filename in matching_files:
            # # Keep Tab Dump, delete DLLs
            # if CACHE_FILE not in filename and dll_filename not in filename:
                # try:
                    # os.remove(path.join(TEMPDIR, filename))
                # except Exception as errmsg:
                    # logger.warning('Could not remove some temporary files.')
        # logger.debug('DLL Clean up completed.')

# import os
# import clr
# import json
# import subprocess
# import shutil
# from pprint import pprint

# from Autodesk.Revit.UI import TaskDialog

# from .config import ROOT_DIR, PYREVIT_DIR, GIT_EXE, BREAKLINE, CWD
# from .config import PKGSJSON_FILEPATH, PKGSJSON_WEB
# from .logger import logger

# clr.AddReference('System.Net')
# clr.AddReference('System.IO')
# from System.Net import HttpWebRequest
# from System.Net import WebClient
# from System.IO import StreamReader

# def get_local_folders():
    # """ Return list of name of folders in pyrevit root dir.
    # ['pyrevitplus' ,'smartalign', 'etc']
    # """
    # folders = []
    # for filename in os.listdir(ROOT_DIR):
        # abs_filepath = op.join(ROOT_DIR, filename)
        # if op.isdir(abs_filepath):
            # folders.append(filename)
    # logger.debug('Local Folders: {}'.format(folders))
    # return folders


# def load_pgks_from_file():
    # """ Reads packages.json from file
    # packages.json should be formatted like this:

    # [
        # {   "name": "locker",
            # "version": "1.0",
            # "description": "Test Repo for clonning",
            # "url": "http://www.github.com/gtalarico/locker/"
        # },
        # ...
    # ]

    # """
    # logger.info('Getting Local Package list...')
    # logger.debug('PkgsJSON: {}'.format(PKGSJSON_FILEPATH))

    # try:
        # with open(PKGSJSON_FILEPATH, 'r') as fp:
            # packages_json = json.load(fp)
    # except IOError as errmsg:
        # logger.error('Failed opening packages.json')
        # logger.error(errmsg)
        # raise
    # except ValueError as errmsg:
        # logger.error('Failed to decode packages.json')
        # logger.error(errmsg)
        # raise
    # try:
        # packages = packages_json['packages']
    # except Exception as errmsg:
        # logger.error('Packages is not properly formatted.')
        # logger.error(errmsg)
        # raise

    # logger.debug('Got Local Packages:')
    # # logger.debug(pprint(packages))
    # return packages


# def load_pgks_from_origin():
    # """ Alternative for loading from remote repo. """
    # logger.info('Getting Remote Package list...')
    # try:
        # json_response = WebClient().DownloadString(PKGSJSON_WEB)
    # except ValueError as errmsg:
        # logger.error('Failed to decode packages.json')
        # logger.error(errmsg)
    # except Exception as errmsg:
        # logger.error('Unkown Error while getting remote packages.json')
        # logger.error(errmsg)
    # else:
        # packages_json = json.loads(json_response)
        # try:
            # packages = packages_json['packages']
        # except Exception as errmsg:
            # logger.error('Packages is not properly formatted.')
            # logger.error(errmsg)
        # else:
            # logger.debug('Got Remote Packages:')
            # # logger.debug(pprint(packages))
            # return packages


# def subprocess_cmd(command):
    # """ Helper function to call subprocess.Popen consistently without having
    # to repeat keyword settings"""
    # logger.debug('CMD: ' + command)
    # process = subprocess.Popen(command, stdout=subprocess.PIPE,
                               # stderr=subprocess.PIPE, shell=True)
    # proc_stdout, errmsg = process.communicate()
    # # print(BREAKLINE)
    # # print('SUBPROCESS OUTPUT')
    # logger.debug(proc_stdout)
    # if errmsg:
        # logger.warning(errmsg)
    # # print(BREAKLINE)
    # return process, proc_stdout, errmsg


# def get_local_pgk_version(package_name):
    # raise NotImplemented
    # # logger.debug('Getting local version for  {}'.format(package_name))
    # # version_file = op.join(package_name, 'version')
    # # with open(version_file) as fp:
    # #     version = fp.read()
    # # logger.info('Local Version is: {}'.format(version))
    # # return version


# def get_remote_pgk_version(url):
    # """git ls-remote --tags https://github.com/gtalarico/pyrevitplus.git
       # f97d7c9768e2ef9e55d93c351a1acda7e39fd736        refs/tags/0.1.0
       # 72cc9355f3299a5d075adc335699bad8d961c9f8        refs/tags/0.3.0
       # 0d4046cf7930621a9fbcdca26cbb3b4945890129        refs/tags/0.4.0
    # """
    # raise NotImplemented
    # # logger.debug('Getting latest tag for url {}'.format(url))
    # # process, out, errmsg = subprocess_cmd(
    # #     '"{GIT}" ls-remote --tags {url}'\
    # #                             .format(GIT=GIT_EXE,url=url))
    # #
    # # failed = process.returncode
    # # if not failed:
    # #     output_lines = out.strip().split('\n')
    # #     ref = output_lines[-1].split('/')[-1]
    # #     logger.info('Remote TAG is: {}'.format(ref))
    # #     return ref


# def get_local_pkg_ref(package_name):
    # """git -C pyrevitplus rev-parse HEAD
       # 86773e09869e5e0071ae3fe50f51a9e1c23657b6
    # """
    # logger.info('Getting REF for local package: {}'.format(package_name))
    # process, out, errmsg = subprocess_cmd(
        # '"{GIT}" -C "{package_name}" rev-parse HEAD'.format(GIT=GIT_EXE,
                                                            # package_name=package_name))

    # failed = process.returncode
    # if not failed:
        # ref = out
        # logger.info('Local ref is: {}'.format(ref))
        # return ref.strip()[:7]


# def get_remote_pkg_ref(url):
    # """git ls-remote https://github.com/gtalarico/pyrevitplus.git refs/heads/master
    # d282c4e6a4590db210431da60091afd69890fc55        refs/heads/master
    # """
    # logger.debug('Getting REF for remote package: {}'.format(url))
    # process, out, errmsg = subprocess_cmd(
        # '"{GIT}" ls-remote {url} refs/heads/master'.format(GIT=GIT_EXE, url=url))

    # failed = process.returncode
    # if not failed:
        # ref = out.split()[0]
        # logger.debug('Remote ref is: {}'.format(ref))
        # return ref.strip()[:7]


# def clone_pkg_from_remote(package_name, package_url):
    # package_exists = op.exists(package_name)
    # logger.debug('Trying to clone: %s', package_name)
    # logger.debug('Cloning CWD is: %s', os.getcwd())
    # logger.debug('Exists: %s', package_exists)

    # if not package_exists:
        # logger.debug('Package does not exists. Will Clone.')
        # logger.info('Clonning Package from Repository...')
        # process, out, errmsg = subprocess_cmd(
            # '"{GIT}" clone --progress --depth=1 {url}'.format(GIT=GIT_EXE, url=package_url))

    # else:
        # # If directory exists but git folder is not there, will fail.
        # logger.debug('Package Exists. Will merge')
        # logger.info('Updating Package from Repository...')

        # process, out, errmsg = subprocess_cmd(
            # '"{GIT}" -C "{name}" pull -f origin'.format(GIT=GIT_EXE,
                                                             # name=package_name))


    # failed = process.returncode
    # # returncode is zero if completed, 1 if failed.
    # if not failed:
        # logger.info('Package Installed.')
        # toggle_tab(package_name, True)
        # return package_name


# def remove_local_pkg(package_name):
    # """Doc """

    # def handleRemoveReadonly(func, path, exc):
        # """ Handles locked git files as per discussion:
        # http://stackoverflow.com/questions/1213706/what-user-do-python-scripts-run-as-in-windows
        # """
        # import errno, stat
        # excvalue = exc[1]
        # if func in (os.rmdir, os.remove) and excvalue.errno == errno.EACCES:
            # os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 0777
            # func(path)
        # else:
            # raise

    # logger.info('Deletting Package...')
    # try:
        # shutil.rmtree(package_name, ignore_errors=False,
          # onerror=handleRemoveReadonly)
        # # shutil.rmtree(submodule_path, ignore_errors=False,
                    # #   onerror=handleRemoveReadonly)
    # except Exception as errmsg:
        # logger.error('Clould not Delete package: %s', package_name)
        # logger.error(errmsg)
        # TaskDialog.Show('Package Maanger', 'Could not Delete Package.'\
                        # 'Please manually delete:\n{}'.format(
                         # op.join(CWD, package_name)))
    # else:
        # logger.info('Package Deleted: %s', package_name)
        # toggle_tab(package_name, False)
        # return package_name


# def toggle_tab(package_name, state):
    # """ Needs AdWindows.dll"""
    # try:
        # clr.AddReference('AdWindows')
        # from Autodesk.Windows import ComponentManager
    # except Exception as errmsg:
        # logger.warning('Could not access required DLL to hide/show tabs.')
    # else:
        # ribbon = ComponentManager.Ribbon
        # for tab in ribbon.Tabs:
            # if tab.Title == package_name:
                # tab.IsVisible = state
