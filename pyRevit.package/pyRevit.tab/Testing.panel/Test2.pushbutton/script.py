import clr

from pyrevit.config import HOME_DIR
from pyrevit.git import git

from System import DateTime, DateTimeOffset


# r = git.Repository(HOME_DIR)
r = git.Repository(r'C:\Users\eirannejad\Desktop\pyRevit2')

print r.Head.Tip.Id.Sha
print r.Head.Tip.Message

options = git.PullOptions()
options.FetchOptions = git.FetchOptions()


def hndlr(url, uname, types):
    up = git.UsernamePasswordCredentials()
    up.Username = 'eirannejad@gmail.com'
    up.Password = 'ehsan2010'
    return up


options.FetchOptions.CredentialsProvider = git.Handlers.CredentialsHandler(hndlr)
sig = git.Signature('eirannejad', 'eirannejad@gmail.com', DateTimeOffset(DateTime.Now))

r.Network.Pull(sig, options)

print r.Head.Tip.Id.Sha
print r.Head.Tip.Message

