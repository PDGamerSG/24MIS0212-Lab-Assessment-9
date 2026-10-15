param(
  [Parameter(Mandatory=$true)][string]$Deployment,
  [string]$Namespace = "assessment9",
  [string]$BrokenImage = "nginx:does-not-exist-assessment9"
)
$ErrorActionPreference = "Continue"
Write-Host "Deploying deliberately faulty image: $BrokenImage"
kubectl -n $Namespace set image deployment/$Deployment "$Deployment=$BrokenImage"
$rolloutOutput = kubectl -n $Namespace rollout status deployment/$Deployment --timeout=25s 2>&1
$rolloutExit = $LASTEXITCODE
$rolloutOutput | ForEach-Object { Write-Host $_ }
if ($rolloutExit -eq 0) {
  throw "The faulty rollout unexpectedly succeeded."
}
Write-Host "Failed rollout detected (kubectl exit code $rolloutExit)."
Write-Host "Rolling back to the last stable revision..."
kubectl -n $Namespace rollout undo deployment/$Deployment
kubectl -n $Namespace rollout status deployment/$Deployment --timeout=120s
Write-Host "Stable revision restored."
kubectl -n $Namespace get pods -l app=$Deployment
