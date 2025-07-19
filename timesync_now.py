# NOTE: If you want to run in cmd as administrator
# w32tm /config /syncfromflags:manual /manualpeerlist:"th.pool.ntp.org 3.th.pool.ntp.org 0.asia.pool.ntp.org 2.asia.pool.ntp.org"
# w32tm /config /update
# w32tm /resync
# net stop w32time
# net start w32time

# complete...

# if not successful run this command
# w32tm /unregister
# w32tm /register
# and re-do all step again

# OR USE THIS SCRIPT
import win32com.shell.shell as shell 
import win32con
import os


commands = 'w32tm /unregister'
shell.ShellExecuteEx(lpVerb='runas', lpFile='cmd.exe', lpParameters='/c '+commands, nShow=win32con.SW_SHOWDEFAULT)
commands = 'w32tm /register'
shell.ShellExecuteEx(lpVerb='runas', lpFile='cmd.exe', lpParameters='/c '+commands)
commands = 'net start w32time'
shell.ShellExecuteEx(lpVerb='runas', lpFile='cmd.exe', lpParameters='/c '+commands)

# For 1st run please use this command
commands = 'w32tm /config /syncfromflags:manual /manualpeerlist:"th.pool.ntp.org ' \
           '3.th.pool.ntp.org 0.asia.pool.ntp.org 2.asia.pool.ntp.org"'
shell.ShellExecuteEx(lpVerb='runas', lpFile='cmd.exe', lpParameters='/c '+commands)
commands = 'w32tm /config /update'
shell.ShellExecuteEx(lpVerb='runas', lpFile='cmd.exe', lpParameters='/c '+commands, nShow=win32con.SW_SHOWDEFAULT)
commands = 'w32tm /resync'
shell.ShellExecuteEx(lpVerb='runas', lpFile='cmd.exe', lpParameters='/c '+commands)
# commands = 'net stop w32time'
# shell.ShellExecuteEx(lpVerb='runas', lpFile='cmd.exe', lpParameters='/c '+commands)
commands = 'net start w32time'
shell.ShellExecuteEx(lpVerb='runas', lpFile='cmd.exe', lpParameters='/c '+commands)

# Next time, you can just run this command to resync.
commands = 'w32tm /resync'
shell.ShellExecuteEx(lpVerb='runas', lpFile='cmd.exe', lpParameters='/c '+commands)

# Show time sync status
os.system('w32tm /query /status')