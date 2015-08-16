__window__.Close()
import _winreg as wr
k = wr.OpenKey(wr.HKEY_CURRENT_USER,r'Software\Bluebeam Software\Brewery\V45\Printer Driver',0,wr.KEY_WRITE)
wr.SetValueEx(k,r'PromptForFileName',0,wr.REG_SZ,'1')
#wr.QueryValueEx(k,r'PromptForFileName')
wr.FlushKey(k)
k.Close()
print('Done...Bluebeam Ask for Filename Dialog Enabled...')