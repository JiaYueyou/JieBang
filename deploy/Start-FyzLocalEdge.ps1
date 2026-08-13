param(
    [int]$HttpPort = 18080
)

$ErrorActionPreference = "Stop"
$containerName = "jiebang-fyz-nginx-local"
$composeContainerName = "jiebang-fyz-nginx-1"
$networkName = "jiebang-fyz_backend"
$imageName = "jiebang-fyz-web:local"

if (-not (docker network inspect $networkName 2>$null)) {
    throw "Docker network '$networkName' does not exist. Start deploy/compose.yml first."
}

# The Compose-managed Nginx is stateless. Stop it before starting the local
# fallback so both containers cannot compete for the same published port.
$composeContainer = docker ps -a --filter "name=^/$composeContainerName$" --format '{{.Names}}'
if ($composeContainer) {
    docker stop $composeContainerName | Out-Null
}

$existingContainer = docker ps -a --filter "name=^/$containerName$" --format '{{.Names}}'
if ($existingContainer) {
    docker rm -f $containerName | Out-Null
}

docker run -d `
    --name $containerName `
    --restart unless-stopped `
    --network $networkName `
    --publish "${HttpPort}:80" `
    $imageName | Out-Null

Write-Host "FYZ local Nginx is available at http://localhost:$HttpPort"
