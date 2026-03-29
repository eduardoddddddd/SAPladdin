@echo off
setlocal

cd /d "%~dp0\.."

git status --short --branch
git remote -v

echo [INFO] If origin is missing, run:
echo git remote add origin https://github.com/eduardoddddddd/SAPladdin.git
echo.
echo [INFO] To publish current branch:
echo git push -u origin main

endlocal
