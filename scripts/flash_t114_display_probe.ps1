[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ZipName = 'KoalaByte-Blue-T114-display-probe-72ed1c8.zip'
$ExpectedZipHash = '5792938C7C43E0266E0397DD6EBD6046FFFDB27277B243EDD47607C276380F5E'
$Uf2Name = 'koalabyte-t114-display-probe-relocated-239a-usb-led-st7789-ht-n5262.uf2'
$ExpectedUf2Hash = 'B58425668AC5BD5523EA4AA788BCE1855F142CA13A8AFF21B708F5B17C5473FF'

Write-Output 'T114_DISPLAY_PROBE_FLASH_BEGIN'

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

$Stage = Join-Path $env:TEMP ('koalabyte-t114-display-probe-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Force -Path $Stage | Out-Null
Expand-Archive -LiteralPath $Zip.FullName -DestinationPath $Stage -Force

$Uf2 = Get-ChildItem $Stage -Recurse -File -Filter $Uf2Name |
    Select-Object -First 1

if ($null -eq $Uf2) {
    throw "T114 display-probe UF2 was not found: $Uf2Name"
}

$ActualUf2Hash = (Get-FileHash $Uf2.FullName -Algorithm SHA256).Hash
if ($ActualUf2Hash -ne $ExpectedUf2Hash) {
    throw "UF2 hash mismatch: $ActualUf2Hash"
}

$BeforePorts = @(
    Get-CimInstance Win32_SerialPort |
        Where-Object { $_.PNPDeviceID -notlike 'BTHENUM*' } |
        Select-Object -ExpandProperty DeviceID
)

$BootVolume = Get-Volume |
    Where-Object { $_.FileSystemLabel -eq 'HT-n5262' -and $_.DriveLetter } |
    Select-Object -First 1

if ($null -eq $BootVolume) {
    throw 'HT-n5262 is not mounted. Double-press Reset and rerun the command.'
}

$Destination = "$($BootVolume.DriveLetter):\t114-display-probe.uf2"
Copy-Item -LiteralPath $Uf2.FullName -Destination $Destination

Write-Output "Zip=$($Zip.FullName)"
Write-Output "ZipSHA256=$ActualZipHash"
Write-Output "Copied=$Destination"
Write-Output "UF2SHA256=$ActualUf2Hash"
Write-Output 'WAITING_FOR_RUNTIME=15_SECONDS'

Start-Sleep -Seconds 15

$StillMounted = Get-Volume |
    Where-Object { $_.FileSystemLabel -eq 'HT-n5262' -and $_.DriveLetter }

$RuntimeDevices = @(
    Get-CimInstance Win32_SerialPort |
        Where-Object { $_.PNPDeviceID -notlike 'BTHENUM*' }
)

$AfterPorts = @($RuntimeDevices | Select-Object -ExpandProperty DeviceID)
$NewPorts = @($AfterPorts | Where-Object { $_ -notin $BeforePorts })
$ProbeRuntimePorts = @(
    $RuntimeDevices |
        Where-Object {
            $_.PNPDeviceID -match 'VID_2FE3&PID_0100' -or
            $_.DeviceID -in $NewPorts
        } |
        Select-Object -ExpandProperty DeviceID
)

Write-Output "BootloaderStillMounted=$([bool]$StillMounted)"
Write-Output "NewPorts=$($NewPorts -join ',')"
Write-Output "ProbeRuntimePorts=$($ProbeRuntimePorts -join ',')"

if ($ProbeRuntimePorts.Count -gt 0) {
    Write-Output 'Result=DISPLAY_PROBE_RUNTIME_DETECTED'
} else {
    Write-Output 'Result=NO_DISPLAY_PROBE_RUNTIME'
}

$RuntimeDevices |
    Format-Table DeviceID, Name, PNPDeviceID -AutoSize -Wrap

Write-Output 'T114_DISPLAY_PROBE_FLASH_END'
