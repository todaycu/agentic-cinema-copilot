<#!
.SYNOPSIS
Starts Prometheus to scrape the local, instrumented render-farm demo and remote-write to Grafana Cloud.

.DESCRIPTION
The generated runtime config is ignored by Git because it contains the remote-write token.
Run the FastAPI backend first so http://host.docker.internal:8000/metrics is available to Docker.
#>

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $root '.env'
$templatePath = Join-Path $PSScriptRoot 'prometheus.template.yml'
$runtimePath = Join-Path $PSScriptRoot 'prometheus.runtime.yml'

if (-not (Test-Path $envPath)) { throw '.env was not found.' }

$values = @{}
Get-Content $envPath | ForEach-Object {
    if ($_ -match '^\s*([^#=\s]+)\s*=\s*(.*?)\s*$') { $values[$Matches[1]] = $Matches[2] }
}

foreach ($required in 'GRAFANA_PROMETHEUS_REMOTE_WRITE_URL', 'GRAFANA_PROMETHEUS_USERNAME', 'GRAFANA_PROMETHEUS_TOKEN') {
    if ([string]::IsNullOrWhiteSpace($values[$required])) { throw "$required is missing from .env." }
}

$config = Get-Content $templatePath -Raw
$config = $config.Replace('__GRAFANA_REMOTE_WRITE_URL__', $values['GRAFANA_PROMETHEUS_REMOTE_WRITE_URL'])
$config = $config.Replace('__GRAFANA_REMOTE_WRITE_USERNAME__', $values['GRAFANA_PROMETHEUS_USERNAME'])
$config = $config.Replace('__GRAFANA_REMOTE_WRITE_TOKEN__', $values['GRAFANA_PROMETHEUS_TOKEN'])
Set-Content -LiteralPath $runtimePath -Value $config -NoNewline

$existingContainer = docker ps -aq --filter "name=^/agentic-cinema-prometheus$"
if ($existingContainer) {
  docker rm -f agentic-cinema-prometheus | Out-Null
}
docker run --name agentic-cinema-prometheus --rm -p 9090:9090 `
  -v "${runtimePath}:/etc/prometheus/prometheus.yml:ro" `
  prom/prometheus:v3.5.0
