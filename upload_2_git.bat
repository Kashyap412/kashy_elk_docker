for /f "tokens=1-3 delims=/ " %%a in ("%date%") do set _date=%%a/%%b/%%c
for /f "tokens=1-3 delims=:." %%a in ("%time: =0%") do set _time=%%a:%%b:%%c
git add .
git commit -m "Initial ELK stack setup %_date% %_time%"
git push -u origin main