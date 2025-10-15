Param(
  [string]$EnvFile = "$(Split-Path $PSCommandPath -Parent)\containerapp.env"
)

if (-not (Test-Path $EnvFile)) {
  Write-Error "Copy azure/containerapp.env.sample to azure/containerapp.env and fill values."; exit 1
}

Get-Content $EnvFile | ForEach-Object {
  if ($_ -match "^\s*#") { return }
  if ($_ -match "^\s*$") { return }
  $k,$v = $_.Split('=',2)
  Set-Variable -Name $k -Value $v -Scope Script
}

az group create -n $RESOURCE_GROUP -l $LOCATION
az acr create -n $ACR_NAME -g $RESOURCE_GROUP --sku Basic
$ACR_LOGIN_SERVER = az acr show -n $ACR_NAME -g $RESOURCE_GROUP --query loginServer -o tsv

Push-Location (Split-Path $PSScriptRoot -Parent)
az acr build -t "$ACR_LOGIN_SERVER/$IMAGE_TAG" -r $ACR_NAME .
Pop-Location

az extension add --name containerapp --upgrade
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights

az containerapp env create -n $ENV_NAME -g $RESOURCE_GROUP -l $LOCATION

$FQDN = az containerapp create `
  -n $CONTAINERAPP_NAME -g $RESOURCE_GROUP `
  --environment $ENV_NAME `
  --image "$ACR_LOGIN_SERVER/$IMAGE_TAG" `
  --target-port 8000 --ingress external `
  --registry-server $ACR_LOGIN_SERVER `
  --env-vars APP_MODE=http KB_DIR=/app/knowledge-base FIXED_DIR=/data/dummy-project/fixed OPENAI_API_KEY=$OPENAI_API_KEY `
  --query properties.configuration.ingress.fqdn -o tsv

Write-Host "Container App URL: https://$FQDN"
Write-Host "Health:            https://$FQDN/health"
Write-Host "POST JSON:         https://$FQDN/api/v1/fix/json"
Write-Host "POST ZIP:          https://$FQDN/api/v1/fix/zip"
