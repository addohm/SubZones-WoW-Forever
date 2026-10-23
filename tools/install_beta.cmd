@echo off
rem Update this repo from GitHub and copy the addon into the WoW: Forever beta client.
rem Run it from anywhere (or double-click it), then restart the client, or /reload if SUBZONES
rem was already loaded. It only pulls what's on GitHub: push your commits first.
setlocal
rem The repo is the folder above this script, wherever it's cloned.
for %%i in ("%~dp0..") do set "REPO=%%~fi"
set "ADDON=C:\Program Files (x86)\World of Warcraft\_classic_beta_\Interface\AddOns\SUBZONES"

git -C "%REPO%" pull --ff-only
if errorlevel 1 (
  echo git pull failed, so nothing was copied.
  set "RESULT=1"
  goto done
)

rem /MIR makes the installed folder an exact copy (files no longer in the repo are deleted).
rem Zips are your own packaging, not part of the addon.
robocopy "%REPO%\SUBZONES" "%ADDON%" /MIR /IS /IT /XF *.zip
rem robocopy exit codes below 8 mean success.
if errorlevel 8 (
  echo Copy failed. Is the WoW folder writable, and the path above right?
  set "RESULT=1"
  goto done
)
rem Stamp the installed copy with the commit, so /subzones debug shows which build is running.
for /f %%h in ('git -C "%REPO%" rev-parse --short HEAD') do set "BUILD=%%h"
> "%ADDON%\Build.lua" (
  echo local _, ns = ...
  echo ns.Build = "%BUILD%"
)
echo Installed SUBZONES build %BUILD% into %ADDON%
echo In game: /reload, then /subzones debug should say build %BUILD%.
set "RESULT=0"

:done
rem Keep the window open when started by double-click.
echo %cmdcmdline% | find /i "%~nx0" >nul && pause
exit /b %RESULT%
