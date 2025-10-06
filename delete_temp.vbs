' run_hidden.vbs
' Place this VBS in the same folder as delete_temp.py or update the paths below.

Option Explicit
Dim sh, pythonPath, scriptPath, args, cmd

Set sh = CreateObject("WScript.Shell")

' Path to python executable. If Python is in PATH, you can use "python"
pythonPath = "python"
' Full path to the delete_temp.py script (change if needed)
scriptPath = CreateObject("Scripting.FileSystemObject").GetAbsolutePathName("delete_temp.py")

' Arguments. Use --yes for silent permanent delete (dangerous). Omit it for interactive confirmation.
args = "--yes"

' Build command
cmd = pythonPath & " " & Chr(34) & scriptPath & Chr(34) & " " & args

' 0 = hidden, True = wait for completion
sh.Run cmd, 0, True
