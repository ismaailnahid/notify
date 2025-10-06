' run_hidden.vbs
' Purpose: run monitor.py invisibly (no CMD window)
Option Explicit

Dim WshShell
Set WshShell = CreateObject("WScript.Shell")
' Replace the path below with your Python exe and monitor.py path
WshShell.Run "python ""C:\notify\monitor_bot.py""", 0, False
Set WshShell = Nothing
' --- IGNORE ---