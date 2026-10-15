$ErrorActionPreference = "Stop"
kubectl apply --dry-run=client -f k8s/namespace.yaml
foreach ($dir in @("lms-portal","food-portal","hospital-portal")) {
  kubectl apply --dry-run=client -f "$dir/deployment.yaml"
  kubectl apply --dry-run=client -f "$dir/service.yaml"
  Write-Host "$dir manifests validated"
}
