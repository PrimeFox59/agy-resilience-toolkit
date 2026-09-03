Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
userProfile = WshShell.ExpandEnvironmentStrings("%USERPROFILE%")

nodeExe = "node.exe"
If fso.FileExists("C:\Program Files\nodejs\node.exe") Then
    nodeExe = "C:\Program Files\nodejs\node.exe"
End If

scriptPath = userProfile & "\scripts\hermes-memory-sync.js"
WshShell.Run """" & nodeExe & """ """ & scriptPath & """", 0, False
