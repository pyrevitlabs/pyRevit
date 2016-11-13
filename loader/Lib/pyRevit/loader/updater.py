
# fixme rewrite update mechanism to use this to update all(?) extensions

import sys
import clr
from System import DateTime, DateTimeOffset

sys.path.append(r'C:\pyRevitv4\loader\pyRevitLoader')
clr.AddReference('LibGit2Sharp')

import LibGit2Sharp as git

r = git.Repository(r'C:\pyRevitv4')

print r.Head.Tip.Id.Sha
print r.Head.Tip.Message

# options = git.PullOptions()
# options.FetchOptions = git.FetchOptions()

options = git.FetchOptions()

up = git.UsernamePasswordCredentials()
up.Username = 'eirannejad'
up.Password = 'ehsan2010'


def hndlr(url, uname, types):
    return up


options.FetchOptions.CredentialsProvider = git.Handlers.CredentialsHandler(hndlr)
sig = git.Signature('eirannejad', 'eirannejad@gmail.com', DateTimeOffset(DateTime.Now))

r.Network.Pull(sig, options)


from pyrevit.git import git
r = git.Repository(r'C:\pyRevitv4')
