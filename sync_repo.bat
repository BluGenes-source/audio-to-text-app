@echo off
cd /d %~dp0
git rm -r --cached . 
git add .
git commit -m "Reset tracking and update gitignore"
git push