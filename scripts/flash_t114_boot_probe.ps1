$ErrorActionPreference = 'Stop'

$ZipName = 'KoalaByte-Blue-T114-relocated-boot-probe-eb4a949.zip'
$ExpectedZipHash = 'A6430C82CFE8B5A4058E6ED52CE67E0139DD67AB09E8C1CBFBD45B3BAB2E49F6'
$Uf2Name = 'koalabyte-t114-boot-probe-relocated-239a-usb-led-ht-n5262.uf2'
$ExpectedUf2Hash = 'CA8E47643939CDC447365241A82C9C525A5238E426D789E9B1AF95D58C804238'

Write-Host 'BOOT_PROBE_FLASH_BEGIN'

$SearchRoots = @(
    (Join-Path $env:USERPROFILE 'Downloads'),
    (Join-Path $env:USERPROFILE 'Documents'),
    (Get-Location).Path
) | Where-Object { Test-Path $_ }

$Zip = Get-ChildItem $SearchRoots -Recurse -File -Filter $ZipName -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if ($null -eq $Zip) {
    throw "Download not found: $ZipName"
}

$ActualZipHash = (Get-FileHash $Zip.FullName -Algorithm SHA256).Hash
if ($ActualZipHash -ne $ExpectedZipHash) {
    throw "ZIP hash mismatch: $ActualZipHash"
}

$Stage = Join-Path $env:TEMP ('koalabyte-t114-boot-probe-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Force -Path $Stage | Out-Null
Expand-Archive -LiteralPath $Zip.FullName -DestinationPath $Stage -Force

$Uf2 = Get-ChildItem $Stage -Recurse -File -Filter $Uf2Name | Select-Object -First 1
if ($null -eq $Uf2) {
    throw "UF2 not found: $Uf2Name"
}

$ActualUf2Hash = (Get-FileHash $Uf2.FullName -Algorithm SHA256).Hash
if ($ActualUf2Hash -ne $ExpectedUf2Hash) {
    throw "UF2 hash mismatch: $ActualUf2Hash"
}

$BeforePorts = @(Get-CimInstance Win32_SerialPort)
$BootVolume = Get-Volume |
    Where-Object { $_.FileSystemLabel -eq 'HT-n5262' -and $_.DriveLetter } |
    Select-Object -First 1

if ($null -eq $BootVolume) {
    throw 'HT-n5262 is not mounted. Double-press Reset and run this script again.'
}

$Destination = "$($BootVolume.DriveLetter):\boot-probe.uf2"
Copy-Item -LiteralPath $Uf2.FullName -Destination $Destination

Write-Host "Copied=$Destination"
Write-Host "UF2SHA256=$ActualUf2Hash"
Write-Host 'WAITING_FOR_RUNTIME=15_SECONDS'
Start-Sleep -Seconds 15

$AfterPorts = @(Get-CimInstance Win32_SerialPort)
$BeforeIds = @($BeforePorts | Select-Object -ExpandProperty PNPDeviceID)
$NewPorts = @($AfterPorts | Where-Object { $_.PNPDeviceID -notin $BeforeIds })
$RuntimePorts = @($AfterPorts | Where-Object { $_.PNPDeviceID -match 'VID_2FE3' })
$StillMounted = Get-Volume |
    Where-Object { $_.FileSystemLabel -eq 'HT-n5262' -and $_.DriveLetter }

Write-Host "BootloaderStillMounted=$([bool]$StillMounted)"
Write-Host "NewPorts=$($NewPorts.DeviceID -join ',')"
Write-Host "ProbeRuntimePorts=$($RuntimePorts.DeviceID -join ',')"

if ($RuntimePorts.Count -gt 0) {
    Write-Host 'Result=PROBE_RUNTIME_DETECTED'
} else {
    Write-Host 'Result=NO_PROBE_RUNTIME'
}

$AfterPorts |
    Select-Object DeviceID, Name, PNPDeviceID |
    Format-Table -AutoSize -Wrap

Write-Host 'BOOT_PROBE_FLASH_END'
