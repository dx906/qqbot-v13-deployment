' ===========================================================================
'  V1.3 production stack launcher  --  idempotent, console-free, ordered
'
'  Why VBScript: every service must survive the death of whatever launched it.
'  Services launched from a bash/pwsh session inherit that console group and
'  get Ctrl+C on session teardown (we lost embed/OV/persona that way on
'  2026-10-27 03:20 -- the persona log literally ends with "^C").
'  wscript.exe has no console, and Run(...,0,...) gives every child a hidden
'  window, so nothing in the chain is attached to a shell.
'
'  Order matters: embed -> OpenViking -> persona -> AstrBot -> SnowLuma.
'  Each step probes its port first, so double-clicking twice is harmless.
'
'  PURE ASCII on purpose. Keep CRLF. No BOM.
' ===========================================================================
Option Explicit

Dim sh, fso, root, logf, failures, warnings
Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root    = "D:\AI\QQBot-v13"
logf    = root & "\logs\stack.log"
failures = 0
warnings = 0

SubLog "===== stack start requested ====="

' ---------------- helpers ----------------------------------------------
Sub SubLog(msg)
  Dim f
  On Error Resume Next
  Set f = fso.OpenTextFile(logf, 8, True)
  If Err.Number = 0 Then
    f.WriteLine Now & "  " & msg
    f.Close
  End If
  On Error GoTo 0
End Sub

Function PortListening(port)
  Dim exec, out
  PortListening = False
  On Error Resume Next
  Set exec = sh.Exec("%comspec% /c netstat -ano -p TCP | findstr """ & port & " "" | findstr LISTENING")
  If Err.Number <> 0 Then Exit Function
  out = exec.StdOut.ReadAll()
  On Error GoTo 0
  If InStr(out, "LISTENING") > 0 Then PortListening = True
End Function

Function WaitPort(port, seconds, label)
  Dim i
  WaitPort = False
  For i = 1 To seconds
    If PortListening(port) Then
      SubLog "  " & label & " ready on " & port & " (" & i & "s)"
      WaitPort = True
      Exit Function
    End If
    WScript.Sleep 1000
  Next
  SubLog "  !! TIMEOUT " & label & " port " & port & " after " & seconds & "s"
  failures = failures + 1
End Function

' start a hidden cmd that owns the child process; returns True when launched
Function LaunchHidden(cmdline)
  Dim rc
  LaunchHidden = False
  On Error Resume Next
  ' 0 = hidden window, False = do not wait
  rc = sh.Run(cmdline, 0, False)
  If Err.Number <> 0 Then
    SubLog "  !! launch failed: " & cmdline & " err=" & Err.Description
    failures = failures + 1
    Exit Function
  End If
  On Error GoTo 0
  LaunchHidden = True
End Function

Sub SetEnv(name, value)
  sh.Environment("PROCESS")(name) = value
End Sub

' ---------------- 1. embed 8329 ----------------------------------------
If PortListening(8329) Then
  SubLog "[1/5] embed 8329 already up"
Else
  SubLog "[1/5] starting embed 8329"
  SetEnv "PYTHONIOENCODING", "utf-8"
  SetEnv "PYTHONUNBUFFERED", "1"
  SetEnv "HF_HUB_OFFLINE", "1"
  SetEnv "TRANSFORMERS_OFFLINE", "1"
  SetEnv "TOKENIZERS_PARALLELISM", "false"
  SetEnv "OMP_NUM_THREADS", "4"
  sh.CurrentDirectory = root & "\persona-base\_embed"
  Call LaunchHidden("%comspec% /c """"" & "D:\AI\persona-base\.venv-embed\Scripts\python.exe" & """" & " embed_server.py --port 8329 --warm """ & "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2" & """ >> """ & root & "\logs\embed-v13.log"" 2>&1""")
  Call WaitPort(8329, 90, "embed")
End If

' ---------------- 2. OpenViking 1936 -----------------------------------
If PortListening(1936) Then
  SubLog "[2/5] openviking 1936 already up"
Else
  SubLog "[2/5] starting openviking 1936"
  sh.CurrentDirectory = root
  ' VikingBot child process needs UTF-8 output; rich emoji crashes on a GBK handle
  SetEnv "PYTHONUTF8", "1"
  SetEnv "PYTHONIOENCODING", "utf-8"
  SetEnv "PATH", sh.ExpandEnvironmentStrings("%USERPROFILE%") & "\.local\bin;" & sh.ExpandEnvironmentStrings("%PATH%")
  ' --with-bot enables Agent chat (/bot/v1 proxy); --bot-port 18791 avoids 18790 used by the main 1933 instance
  Call LaunchHidden("%comspec% /c """"" & sh.ExpandEnvironmentStrings("%USERPROFILE%") & "\.local\bin\openviking-server.exe" & """ --config """ & root & "\ov-v13\ov.conf"" --port 1936 --with-bot --bot-port 18791 >> """ & root & "\logs\ov-v13.log"" 2>&1""")
  Call WaitPort(1936, 120, "openviking")
End If

' ---------------- 3. persona 8127 --------------------------------------
If PortListening(8127) Then
  SubLog "[3/5] persona 8127 already up"
Else
  SubLog "[3/5] starting persona 8127"
  SetEnv "PYTHONIOENCODING", "utf-8"
  SetEnv "PYTHONUTF8", "1"
  SetEnv "PERSONA_EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
  SetEnv "PERSONA_EMBED_BASE_URL", "http://127.0.0.1:8329/v1"
  SetEnv "PERSONA_EMBED_DIM", "384"
  SetEnv "PERSONA_BACKUP", "0"
  sh.CurrentDirectory = root & "\persona-base"
  Call LaunchHidden("%comspec% /c """"" & root & "\venv\Scripts\python.exe"" serve.py --port 8127 --no-backup >> """ & root & "\logs\persona-svc-v13.log"" 2>&1""")
  Call WaitPort(8127, 90, "persona")
End If

' ---------------- 4. AstrBot 6381/6382 ---------------------------------
If PortListening(6381) Then
  SubLog "[4/5] astrbot 6381 already up"
Else
  SubLog "[4/5] starting astrbot 6381"
  SetEnv "PYTHONIOENCODING", "utf-8"
  sh.CurrentDirectory = root
  Call LaunchHidden("%comspec% /c """"" & root & "\venv\Scripts\python.exe"" -c ""from astrbot.cli.__main__ import cli; cli()"" run -p 6381 >> """ & root & "\logs\astrbot-v13-console.log"" 2>&1""")
  Call WaitPort(6381, 180, "astrbot")
End If

' ---------------- 5. SnowLuma 5199 -------------------------------------
If PortListening(5199) Then
  SubLog "[5/5] snowluma 5199 already up"
Else
  SubLog "[5/5] starting snowluma 5199"
  sh.CurrentDirectory = root & "\SnowLuma"
  Call LaunchHidden("%comspec% /c """"" & root & "\SnowLuma\node.exe"" index.mjs >> """ & root & "\logs\snowluma.log"" 2>&1""")
  Call WaitPort(5199, 60, "snowluma")
End If

' ---------------- summary ----------------------------------------------
If failures = 0 Then
  SubLog "===== stack UP (all 5 services reachable) ====="
Else
  SubLog "===== stack INCOMPLETE, failures=" & failures & " -- see logs ====="
End If
WScript.Quit failures