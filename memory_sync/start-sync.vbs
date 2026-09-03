Set WshShell = CreateObject("WScript.Shell")
userProfile = WshShell.ExpandEnvironmentStrings("%USERPROFILE%")
WshShell.Run "node """ & userProfile & "\scripts\hermes-memory-sync.js""", 0, False
