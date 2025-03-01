@echo off
cd /d %~dp0
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch tools/ffmpeg.exe tools/ffplay.exe tools/ffprobe.exe" --prune-empty --tag-name-filter cat -- --all
git reflog expire --expire=now --all
git gc --prune=now
git push origin --force