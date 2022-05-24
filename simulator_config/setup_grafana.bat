@ECHO OFF 

ECHO Setting up Grafana...
copy defaults.ini "C:\Program Files\GrafanaLabs\grafana\conf\"
cd "C:\Program Files\GrafanaLabs\grafana\bin"
grafana-cli.exe plugins install agenty-flowcharting-panel
ECHO Grafana plugins installed successfully...
ECHO Restarting Grafana...
powershell -command "Restart-Service Grafana"
cd /D "%~dp0"
