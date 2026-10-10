#Requires -Version 5.1
<#
.SYNOPSIS
  Recreate HC production services from production-services.json.

.DESCRIPTION
  Default mode and -DryRun only read Win32_Service, the service registry,
  listeners, and env files. They do not call nssm.exe or sc.exe, and they do
  not start, stop, or reconfigure services.

  -Apply is required before any change. If a named service already exists,
  -Apply also requires -ApproveReplace. Neither switch is used by the
  capture run on HC-PROD-VPS01.

  Secret values are never written to the output.
#>
[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$Apply,
    [switch]$ApproveReplace,
    [string]$CatalogPath = 'C:\HC\deployment\production-services.json'
)

$ErrorActionPreference = 'Stop'
$Script:MutationsAllowed = $false
$Script:NssmExe = 'C:\HC\deployment\tools\nssm\nssm.exe'
$Script:Fail = 0

$ExpectedDrift = @(
    'HC-Uploader-Public live-only DOWNSTREAM_INGEST_TOKEN',
    'HC-TKP-Public live-only GLENN_UPLOADER_INGEST_TOKEN',
    'HC-TCP-Public live-only GLENN_UPLOADER_INGEST_TOKEN',
    'HC-TCP-Public live-only TCP_V2_ADMIN_TOKEN',
    'HC-TCP-Public live-only TCP_V2_SESSION_SECRET',
    'HC-YQ-Public empty-env-entry count=1',
    'HC-AGM-Public live-only GLENN_UPLOADER_INGEST_TOKEN'
)

$ExpectedWarnings = @(
    'DOWNSTREAM_INGEST_TOKEN only-in-live-service'
)

function Write-Line {
    param([string]$Message)
    Write-Output $Message
}

function Add-Fail {
    param([string]$Message)
    $Script:Fail++
    Write-Line ("  [FAIL] {0}" -f $Message)
}

function Add-Pass {
    param([string]$Message)
    Write-Line ("  [PASS] {0}" -f $Message)
}

function Test-SecretName {
    param([string]$Name)
    return $Name -match '(?i)TOKEN|SECRET|PASSWORD|CREDENTIAL'
}

function ConvertTo-NormalizedAccount {
    param([string]$Name)
    if ($Name -in @('LocalSystem', 'NT AUTHORITY\SYSTEM')) {
        return 'LocalSystem'
    }
    return $Name
}

function ConvertTo-StartupLabel {
    param($Service)
    $startType = [string]$Service.StartType
    if ($startType -eq 'Automatic') { return 'Automatic' }
    return $startType
}

function Read-Catalog {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Catalog missing: $Path"
    }
    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    return ($raw | ConvertFrom-Json)
}

function Read-EnvFile {
    param([string]$Path)
    $map = @{}
    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path)) {
        return $map
    }
    foreach ($line in @(Get-Content -LiteralPath $Path)) {
        $text = (("" + $line) -replace "`0", '').Trim()
        if ($text.Length -eq 0 -or $text.StartsWith('#')) { continue }
        $eq = $text.IndexOf('=')
        if ($eq -lt 1) { continue }
        $key = $text.Substring(0, $eq).Trim().TrimStart([char]0xFEFF)
        $value = $text.Substring($eq + 1).Trim()
        if ($value.Length -ge 2 -and $value.StartsWith('"') -and $value.EndsWith('"')) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        $map[$key] = $value
    }
    return $map
}

function Get-LiveEnvironment {
    param([string]$ServiceName)
    $result = @{
        Map = @{}
        Blank = 0
    }
    $reg = "HKLM:\SYSTEM\CurrentControlSet\Services\$ServiceName\Parameters"
    if (-not (Test-Path -LiteralPath $reg)) {
        return $result
    }
    $raw = (Get-ItemProperty -LiteralPath $reg -Name 'AppEnvironmentExtra' -ErrorAction SilentlyContinue).AppEnvironmentExtra
    foreach ($line in @($raw)) {
        $text = (("" + $line) -replace "`0", '').Trim()
        if ($text.Length -eq 0) {
            $result.Blank++
            continue
        }
        $eq = $text.IndexOf('=')
        if ($eq -lt 1) { continue }
        $key = $text.Substring(0, $eq).Trim()
        $value = $text.Substring($eq + 1)
        $result.Map[$key] = $value
    }
    return $result
}

function Get-ObjectProperties {
    param($Object)
    $names = @()
    if ($null -eq $Object) { return $names }
    foreach ($prop in @($Object.PSObject.Properties)) {
        $names += [string]$prop.Name
    }
    return $names
}

function Get-PropertyValue {
    param($Object, [string]$Name)
    if ($null -eq $Object) { return $null }
    $prop = $Object.PSObject.Properties[$Name]
    if ($null -eq $prop) { return $null }
    return $prop.Value
}

function Test-EnvNamePresent {
    param(
        [string]$Name,
        [string]$Target
    )
    $value = [Environment]::GetEnvironmentVariable($Name, $Target)
    return -not [string]::IsNullOrWhiteSpace($value)
}

function Get-SecretFileHits {
    param([string]$Name)
    $hits = @()
    $root = 'C:\HC\secrets'
    if (-not (Test-Path -LiteralPath $root)) { return $hits }
    $files = @(Get-ChildItem -LiteralPath $root -Recurse -File -Filter '*.env' -ErrorAction SilentlyContinue)
    foreach ($file in $files) {
        $map = Read-EnvFile $file.FullName
        if ($map.ContainsKey($Name) -and -not [string]::IsNullOrWhiteSpace([string]$map[$Name])) {
            $hits += $file.FullName
        }
    }
    return $hits
}

function Assert-MutationAllowed {
    if (-not $Script:MutationsAllowed) {
        throw 'Refusing to modify this host: mutations are disabled.'
    }
}

function Invoke-NssmChecked {
    param([string[]]$NssmArgs)
    Assert-MutationAllowed
    & $Script:NssmExe @NssmArgs
    if ($LASTEXITCODE -ne 0) {
        $action = 'nssm'
        if ($NssmArgs.Count -ge 2) { $action = '{0} {1}' -f $NssmArgs[0], $NssmArgs[1] }
        throw "nssm command failed: $action"
    }
}

function Get-ApplySecretValue {
    param(
        $Service,
        [string]$Name
    )
    $designated = $null
    foreach ($source in @($Service.secret_sources)) {
        if ([string]$source.name -eq $Name -and -not [string]::IsNullOrWhiteSpace([string]$source.file)) {
            $designated = [string]$source.file
        }
    }
    if ($designated) {
        $map = Read-EnvFile $designated
        if ($map.ContainsKey($Name) -and -not [string]::IsNullOrWhiteSpace([string]$map[$Name])) {
            return [string]$map[$Name]
        }
        throw "Apply missing secret name $Name in $designated"
    }
    $hits = @(Get-SecretFileHits $Name)
    if ($hits.Count -eq 1) {
        $map = Read-EnvFile $hits[0]
        return [string]$map[$Name]
    }
    if ($hits.Count -gt 1) {
        throw "Apply found $Name in more than one secrets file and no designated file"
    }
    if (Test-EnvNamePresent $Name 'Process') {
        return [Environment]::GetEnvironmentVariable($Name, 'Process')
    }
    throw "Apply missing secret name $Name in the process environment or a secrets file"
}

function Set-NssmEnvironment {
    param(
        $Service
    )
    Assert-MutationAllowed
    $lines = New-Object System.Collections.Generic.List[string]
    foreach ($prop in @($Service.environment_non_secret.PSObject.Properties)) {
        $lines.Add(('{0}={1}' -f $prop.Name, [string]$prop.Value))
    }
    foreach ($name in @($Service.secret_variable_names)) {
        $secret = Get-ApplySecretValue -Service $Service -Name $name
        $lines.Add(('{0}={1}' -f $name, $secret))
    }
    $reg = "HKLM:\SYSTEM\CurrentControlSet\Services\$($Service.service_name)\Parameters"
    if (-not (Test-Path -LiteralPath $reg)) {
        throw "NSSM Parameters key missing for $($Service.service_name)"
    }
    New-ItemProperty -LiteralPath $reg -Name 'AppEnvironmentExtra' -PropertyType MultiString -Value $lines.ToArray() -Force | Out-Null
}

function Invoke-ApplyChanges {
    param([string]$Path)
    if ($DryRun) { throw 'DryRun is set' }
    if (-not $Apply) { throw 'Apply was not requested' }

    $catalog = Read-Catalog $Path
    $existing = @()
    foreach ($service in @($catalog.services)) {
        $found = Get-Service -Name $service.service_name -ErrorAction SilentlyContinue
        if ($found) { $existing += [string]$service.service_name }
    }
    if ($existing.Count -gt 0 -and -not $ApproveReplace) {
        throw ('Refusing to replace existing services without -ApproveReplace: ' + ($existing -join ', '))
    }

    foreach ($service in @($catalog.services)) {
        foreach ($name in @($service.secret_variable_names)) {
            [void](Get-ApplySecretValue -Service $service -Name $name)
        }
        if ($service.service_account_password_variable) {
            $passwordName = [string]$service.service_account_password_variable
            if (-not (Test-EnvNamePresent $passwordName 'Process')) {
                throw "Apply missing service-account password variable $passwordName"
            }
        }
    }

    $Script:MutationsAllowed = $true
    $Script:NssmExe = [string]$catalog.nssm_exe

    foreach ($service in @($catalog.services)) {
        $name = [string]$service.service_name
        $found = Get-Service -Name $name -ErrorAction SilentlyContinue
        if ($found) {
            Assert-MutationAllowed
            if (-not $ApproveReplace) { throw "Refusing to replace $name" }
            Stop-Service -Name $name -Force
            if ([string]$service.manager -eq 'nssm') {
                Invoke-NssmChecked @('remove', $name, 'confirm')
            } else {
                & sc.exe delete $name | Out-Null
                if ($LASTEXITCODE -ne 0) { throw "sc.exe delete failed for $name" }
            }
        }

        if ([string]$service.manager -eq 'nssm') {
            Invoke-NssmChecked @('install', $name, [string]$service.application)
            Invoke-NssmChecked @('set', $name, 'AppDirectory', [string]$service.working_directory)
            Invoke-NssmChecked @('set', $name, 'AppParameters', [string]$service.arguments)
            Invoke-NssmChecked @('set', $name, 'DisplayName', [string]$service.display_name)
            Invoke-NssmChecked @('set', $name, 'Start', 'SERVICE_AUTO_START')
            foreach ($prop in @($service.nssm.PSObject.Properties)) {
                Invoke-NssmChecked @('set', $name, [string]$prop.Name, [string]$prop.Value)
            }
            Set-NssmEnvironment -Service $service
            if ((ConvertTo-NormalizedAccount ([string]$service.service_account)) -eq 'LocalSystem') {
                Invoke-NssmChecked @('set', $name, 'ObjectName', 'LocalSystem')
            } else {
                $passwordName = [string]$service.service_account_password_variable
                $password = [Environment]::GetEnvironmentVariable($passwordName, 'Process')
                Assert-MutationAllowed
                & sc.exe config $name obj= ([string]$service.service_account) password= $password | Out-Null
                if ($LASTEXITCODE -ne 0) {
                    throw "sc.exe could not set the service account for $name"
                }
            }
            Assert-MutationAllowed
            Start-Service -Name $name
        } else {
            Assert-MutationAllowed
            $image = [string]$service.image_path
            & sc.exe create $name binPath= $image start= auto DisplayName= ([string]$service.display_name) | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "sc.exe create failed for $name" }
            $errorLabel = 'normal'
            if ([int]$service.error_control -eq 0) { $errorLabel = 'ignore' }
            & sc.exe config $name error= $errorLabel | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "sc.exe error control failed for $name" }
            & sc.exe config $name obj= LocalSystem | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "sc.exe account failed for $name" }
            Start-Service -Name $name
        }
    }
}

function Get-ServiceSnapshot {
    param($Catalog)
    $rows = @()
    foreach ($service in @($Catalog.services)) {
        $cim = Get-CimInstance Win32_Service -Filter ("Name='{0}'" -f $service.service_name) -ErrorAction SilentlyContinue
        $rows += [PSCustomObject]@{
            Name = [string]$service.service_name
            State = $(if ($cim) { [string]$cim.State } else { 'missing' })
            ProcessId = $(if ($cim) { [int]$cim.ProcessId } else { 0 })
            StartMode = $(if ($cim) { [string]$cim.StartMode } else { 'missing' })
        }
    }
    return $rows
}

function Test-SnapshotUnchanged {
    param($Before, $After)
    foreach ($left in @($Before)) {
        $right = @($After | Where-Object { $_.Name -eq $left.Name }) | Select-Object -First 1
        if (-not $right) {
            Add-Fail ("snapshot missing {0}" -f $left.Name)
            continue
        }
        $same = ($left.State -eq $right.State -and $left.ProcessId -eq $right.ProcessId -and $left.StartMode -eq $right.StartMode)
        if ($same) {
            Add-Pass ("{0} unchanged state={1} pid={2}" -f $left.Name, $left.State, $left.ProcessId)
        } else {
            Add-Fail ("{0} changed during dry-run" -f $left.Name)
        }
    }
}

function Add-PathCheck {
    param([string]$Label, [string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) {
        Add-Fail "$Label path empty"
        return
    }
    if (Test-Path -LiteralPath $Path) {
        Add-Pass "$Label $Path"
    } else {
        Add-Fail "$Label missing $Path"
    }
}

function Invoke-DryRun {
    param([string]$Path)

    $mode = 'DryRun (default)'
    if ($DryRun) { $mode = 'DryRun' }
    Write-Line '===== HC PRODUCTION SERVICE INSTALL ====='
    Write-Line ("Mode: {0}" -f $mode)
    Write-Line 'Mutations: disabled'
    Write-Line 'nssm.exe: not executed'
    Write-Line 'sc.exe: not executed'
    Write-Line ("Catalog: {0}" -f $Path)
    Write-Line ("Host: {0}" -f $env:COMPUTERNAME)
    if ($Apply -and $DryRun) {
        Write-Line 'NOTE: -Apply was not honored because -DryRun is set.'
    }
    Write-Line ''

    $catalog = Read-Catalog $Path
    $before = Get-ServiceSnapshot $catalog

    Write-Line '--- FILES ---'
    Add-PathCheck 'nssm' ([string]$catalog.nssm_exe)
    Add-PathCheck 'shared python' ([string]$catalog.python_shared_venv)
    Add-PathCheck 'uploader python' ([string]$catalog.python_uploader_venv)
    foreach ($python in @([string]$catalog.python_shared_venv, [string]$catalog.python_uploader_venv)) {
        if (Test-Path -LiteralPath $python) {
            $version = (& $python -c "import sys; print(sys.version.split()[0])").Trim()
            if ($version -eq [string]$catalog.python_version) {
                Add-Pass ("python {0} {1}" -f $version, $python)
            } else {
                Add-Fail ("python version {0} expected {1} for {2}" -f $version, $catalog.python_version, $python)
            }
        }
    }

    foreach ($service in @($catalog.services)) {
        Add-PathCheck ("{0} application" -f $service.service_name) ([string]$service.application)
        if (-not [string]::IsNullOrWhiteSpace([string]$service.working_directory)) {
            Add-PathCheck ("{0} working directory" -f $service.service_name) ([string]$service.working_directory)
        }
        if (-not [string]::IsNullOrWhiteSpace([string]$service.config_file)) {
            Add-PathCheck ("{0} config" -f $service.service_name) ([string]$service.config_file)
        }
        if (-not [string]::IsNullOrWhiteSpace([string]$service.persistent_data_path)) {
            Add-PathCheck ("{0} data" -f $service.service_name) ([string]$service.persistent_data_path)
        }
        if (-not [string]::IsNullOrWhiteSpace([string]$service.credentials_file)) {
            Add-PathCheck ("{0} credentials file" -f $service.service_name) ([string]$service.credentials_file)
        }
        foreach ($token in @(([string]$service.arguments) -split '\s+')) {
            if ($token -match '^[A-Za-z]:\\') {
                Add-PathCheck ("{0} argument" -f $service.service_name) $token
            }
        }
        foreach ($source in @($service.secret_sources)) {
            if (-not [string]::IsNullOrWhiteSpace([string]$source.file)) {
                Add-PathCheck ("{0} secret file {1}" -f $service.service_name, $source.name) ([string]$source.file)
            }
        }
        if ($service.nssm) {
            foreach ($logName in @('AppStdout', 'AppStderr')) {
                $logPath = [string](Get-PropertyValue $service.nssm $logName)
                if ($logPath) {
                    $parent = Split-Path -Parent $logPath
                    Add-PathCheck ("{0} {1} dir" -f $service.service_name, $logName) $parent
                }
            }
        }
    }

    Write-Line ''
    Write-Line '--- SECRET NAMES ---'
    $warnings = @()
    foreach ($service in @($catalog.services)) {
        $live = Get-LiveEnvironment $service.service_name
        foreach ($name in @($service.secret_variable_names)) {
            $places = @()
            if (Test-EnvNamePresent $name 'Process') { $places += 'process' }
            if (Test-EnvNamePresent $name 'Machine') { $places += 'machine' }
            if (Test-EnvNamePresent $name 'User') { $places += 'user' }
            $hits = @(Get-SecretFileHits $name)
            foreach ($hit in $hits) { $places += ('file:' + $hit) }
            $livePresent = $live.Map.ContainsKey($name) -and -not [string]::IsNullOrWhiteSpace([string]$live.Map[$name])
            if ($livePresent) { $places += 'live-service' }
            if ($places.Count -eq 0) {
                Add-Fail ("{0} {1} missing from environment, secrets files, and the live service" -f $service.service_name, $name)
            } else {
                Add-Pass ("{0} {1} present ({2})" -f $service.service_name, $name, ($places -join ', '))
            }
            $applyReady = @($places | Where-Object { $_ -ne 'live-service' })
            if ($applyReady.Count -eq 0 -and $livePresent) {
                $warnings += ("{0} only-in-live-service" -f $name)
                Write-Line ("  [WARN] {0} {1} is only in the live service environment. -Apply on a new host would refuse until it is supplied by variable name." -f $service.service_name, $name)
            }
            $designated = $null
            foreach ($source in @($service.secret_sources)) {
                if ([string]$source.name -eq $name) { $designated = [string]$source.file }
            }
            if (-not [string]::IsNullOrWhiteSpace($designated)) {
                $fileMap = Read-EnvFile $designated
                $fileValue = [string]$fileMap[$name]
                $liveValue = [string]$live.Map[$name]
                if ([string]::IsNullOrWhiteSpace($fileValue) -or [string]::IsNullOrWhiteSpace($liveValue)) {
                    Add-Fail ("{0} {1} secret name missing from designated file or live service" -f $service.service_name, $name)
                } elseif ([string]::Equals($fileValue, $liveValue, [StringComparison]::Ordinal)) {
                    Add-Pass ("{0} {1} designated file matches live service (value not shown)" -f $service.service_name, $name)
                } else {
                    Add-Fail ("{0} {1} designated file differs from live service (values not shown)" -f $service.service_name, $name)
                }
            }
        }
    }

    $uploader = Get-LiveEnvironment 'HC-Uploader-Public'
    $tkpFile = Read-EnvFile 'C:\HC\secrets\tkp-ingest.env'
    $tcpFile = Read-EnvFile 'C:\HC\secrets\tcp-ingest.env'
    $agmFile = Read-EnvFile 'C:\HC\secrets\agm-ingest.env'
    $tokenValues = @(
        [string]$uploader.Map['DOWNSTREAM_INGEST_TOKEN'],
        [string]$tkpFile['GLENN_UPLOADER_INGEST_TOKEN'],
        [string]$tcpFile['GLENN_UPLOADER_INGEST_TOKEN'],
        [string]$agmFile['GLENN_UPLOADER_INGEST_TOKEN']
    )
    $presentTokens = @($tokenValues | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    $distinctTokens = New-Object System.Collections.Generic.List[string]
    foreach ($tokenValue in $presentTokens) {
        $seen = $false
        foreach ($existingToken in $distinctTokens) {
            if ([string]::Equals($existingToken, $tokenValue, [StringComparison]::Ordinal)) {
                $seen = $true
                break
            }
        }
        if (-not $seen) { $distinctTokens.Add($tokenValue) }
    }
    if ($presentTokens.Count -eq 4 -and $distinctTokens.Count -eq 1) {
        Add-Pass 'ingest token name parity across uploader service and tkp/tcp/agm secret files (value not shown)'
    } else {
        Add-Fail ("ingest token name parity present={0} distinct={1} (values not shown)" -f $presentTokens.Count, $distinctTokens.Count)
    }

    $warningExpected = @($ExpectedWarnings | Sort-Object -Unique)
    $warningActual = @($warnings | Sort-Object -Unique)
    $warningDelta = @(Compare-Object $warningExpected $warningActual | Where-Object { $null -ne $_ })
    if ($warningDelta.Count -eq 0) {
        Add-Pass 'documented secret-location warnings match'
    } else {
        Add-Fail 'secret-location warnings differ from the documented set'
        foreach ($row in $warningDelta) {
            Write-Line ("  [WARN-DELTA] {0} {1}" -f $row.SideIndicator, $row.InputObject)
        }
    }

    Write-Line ''
    Write-Line '--- SERVICE PARITY ---'
    foreach ($service in @($catalog.services)) {
        $name = [string]$service.service_name
        $win = Get-Service -Name $name -ErrorAction SilentlyContinue
        $cim = Get-CimInstance Win32_Service -Filter ("Name='{0}'" -f $name) -ErrorAction SilentlyContinue
        if (-not $win -or -not $cim) {
            Add-Fail "$name missing"
            continue
        }
        $regRoot = Get-ItemProperty -LiteralPath ("HKLM:\SYSTEM\CurrentControlSet\Services\{0}" -f $name)
        $ok = $true
        if ([string]$cim.DisplayName -ne [string]$service.display_name) {
            $ok = $false
            Add-Fail ("{0} display name live='{1}'" -f $name, $cim.DisplayName)
        }
        $account = ConvertTo-NormalizedAccount ([string]$cim.StartName)
        $expectedAccount = ConvertTo-NormalizedAccount ([string]$service.service_account)
        if ($account -ne $expectedAccount) {
            $ok = $false
            Add-Fail ("{0} account live='{1}'" -f $name, $cim.StartName)
        }
        $startup = ConvertTo-StartupLabel $win
        if ($startup -ne [string]$service.startup_type) {
            $ok = $false
            Add-Fail ("{0} startup live='{1}'" -f $name, $startup)
        }
        if ([bool]$cim.DelayedAutoStart -ne [bool]$service.delayed_auto_start) {
            $ok = $false
            Add-Fail ("{0} delayed auto start live={1}" -f $name, $cim.DelayedAutoStart)
        }
        if ([int]$regRoot.ErrorControl -ne [int]$service.error_control) {
            $ok = $false
            Add-Fail ("{0} error control live={1}" -f $name, $regRoot.ErrorControl)
        }
        if ([int]$regRoot.Type -ne 16 -or [string]$service.service_type -ne 'Win32OwnProcess') {
            $ok = $false
            Add-Fail ("{0} service type live={1}" -f $name, $regRoot.Type)
        }

        if ([string]$service.manager -eq 'nssm') {
            $image = (("" + $cim.PathName) -replace '\s+', ' ').Trim()
            if ($image -ne [string]$catalog.nssm_exe) {
                $ok = $false
                Add-Fail ("{0} image path is not NSSM" -f $name)
            }
            $params = Get-ItemProperty -LiteralPath ("HKLM:\SYSTEM\CurrentControlSet\Services\{0}\Parameters" -f $name)
            foreach ($pair in @(
                @('Application', [string]$service.application),
                @('AppDirectory', [string]$service.working_directory),
                @('AppParameters', [string]$service.arguments)
            )) {
                $liveValue = [string](Get-PropertyValue $params $pair[0])
                if ($liveValue -ne $pair[1]) {
                    $ok = $false
                    Add-Fail ("{0} {1} mismatch" -f $name, $pair[0])
                }
            }
            $known = @('Application', 'AppDirectory', 'AppParameters', 'AppEnvironmentExtra')
            foreach ($prop in @($service.nssm.PSObject.Properties)) {
                $known += [string]$prop.Name
                $liveValue = Get-PropertyValue $params $prop.Name
                if ([string]$liveValue -ne [string]$prop.Value) {
                    $ok = $false
                    Add-Fail ("{0} {1} mismatch live='{2}'" -f $name, $prop.Name, $liveValue)
                }
            }
            foreach ($prop in @($params.PSObject.Properties)) {
                if ($prop.Name -like 'PS*') { continue }
                if ($known -notcontains [string]$prop.Name) {
                    $ok = $false
                    Add-Fail ("{0} unexpected NSSM parameter {1}" -f $name, $prop.Name)
                }
            }
            $liveEnv = Get-LiveEnvironment $name
            $expectedKeys = @()
            foreach ($prop in @($service.environment_non_secret.PSObject.Properties)) {
                $expectedKeys += [string]$prop.Name
                $liveValue = [string]$liveEnv.Map[$prop.Name]
                if ($liveValue -ne [string]$prop.Value) {
                    $ok = $false
                    Add-Fail ("{0} env {1} mismatch" -f $name, $prop.Name)
                }
            }
            foreach ($secretName in @($service.secret_variable_names)) {
                $expectedKeys += [string]$secretName
                if (-not $liveEnv.Map.ContainsKey([string]$secretName) -or [string]::IsNullOrWhiteSpace([string]$liveEnv.Map[$secretName])) {
                    $ok = $false
                    Add-Fail ("{0} env missing secret name {1}" -f $name, $secretName)
                }
            }
            foreach ($liveKey in @($liveEnv.Map.Keys)) {
                if ($expectedKeys -notcontains [string]$liveKey) {
                    $ok = $false
                    Add-Fail ("{0} unexpected live env name {1}" -f $name, $liveKey)
                }
            }
            if ([string]$service.arguments -match '--host\s+(\S+)') {
                if ($Matches[1] -ne [string]$service.bind_address) {
                    $ok = $false
                    Add-Fail ("{0} argument host is {1}" -f $name, $Matches[1])
                }
            }
            if ([string]$service.bind_address -ne '127.0.0.1') {
                $ok = $false
                Add-Fail ("{0} catalog bind address is not loopback" -f $name)
            }
            $listeners = @(Get-NetTCPConnection -LocalPort ([int]$service.port) -State Listen -ErrorAction SilentlyContinue)
            if ($listeners.Count -ne 1) {
                $ok = $false
                Add-Fail ("{0} listener count={1}" -f $name, $listeners.Count)
            } else {
                $addr = [string]$listeners[0].LocalAddress
                if ($addr -ne [string]$service.bind_address) {
                    $ok = $false
                    Add-Fail ("{0} listener address {1}" -f $name, $addr)
                }
            }
        } else {
            $image = (("" + $cim.PathName) -replace '\s+', ' ').Trim()
            $expectedImage = (("" + $service.image_path) -replace '\s+', ' ').Trim()
            if ($image -ne $expectedImage) {
                $ok = $false
                Add-Fail ("{0} image path mismatch" -f $name)
            }
            $cfg = Get-Content -LiteralPath ([string]$service.config_file) -Raw
            if ($cfg -notmatch [regex]::Escape([string]$service.tunnel_id)) {
                $ok = $false
                Add-Fail ("{0} tunnel id missing from config" -f $name)
            }
            if ($cfg -notmatch [regex]::Escape([string]$service.credentials_file)) {
                $ok = $false
                Add-Fail ("{0} credentials path missing from config" -f $name)
            }
            if ($cfg -notmatch [regex]::Escape([string]$service.ingress_default)) {
                $ok = $false
                Add-Fail ("{0} default ingress missing" -f $name)
            }
            foreach ($rule in @($service.ingress)) {
                $hostOk = $cfg -match [regex]::Escape([string]$rule.hostname)
                $destOk = $cfg -match [regex]::Escape([string]$rule.service)
                if (-not ($hostOk -and $destOk)) {
                    $ok = $false
                    Add-Fail ("{0} ingress {1}" -f $name, $rule.hostname)
                }
            }
        }

        if ($ok) { Add-Pass $name }
    }

    Write-Line ''
    Write-Line '--- CONFIG DRIFT (catalog follows the live service) ---'
    $drift = @()
    foreach ($service in @($catalog.services)) {
        if ([string]$service.manager -ne 'nssm') { continue }
        $name = [string]$service.service_name
        $fileMap = Read-EnvFile ([string]$service.config_file)
        $liveEnv = Get-LiveEnvironment $name
        foreach ($key in @($fileMap.Keys)) {
            if (-not $liveEnv.Map.ContainsKey($key)) {
                if (Test-SecretName $key) {
                    $drift += ("{0} file-only {1}" -f $name, $key)
                } else {
                    $drift += ("{0} file-only {1}={2}" -f $name, $key, [string]$fileMap[$key])
                }
            } elseif (-not (Test-SecretName $key) -and [string]$fileMap[$key] -ne [string]$liveEnv.Map[$key]) {
                $drift += ("{0} value {1} file={2} live={3}" -f $name, $key, [string]$fileMap[$key], [string]$liveEnv.Map[$key])
            }
        }
        foreach ($key in @($liveEnv.Map.Keys)) {
            if (-not $fileMap.ContainsKey($key)) {
                if (Test-SecretName $key) {
                    $drift += ("{0} live-only {1}" -f $name, $key)
                } else {
                    $drift += ("{0} live-only {1}={2}" -f $name, $key, [string]$liveEnv.Map[$key])
                }
            }
        }
        if ([int]$liveEnv.Blank -gt 0) {
            $drift += ("{0} empty-env-entry count={1}" -f $name, [int]$liveEnv.Blank)
        }
    }
    $driftExpected = @($ExpectedDrift | Sort-Object -Unique)
    $driftActual = @($drift | Sort-Object -Unique)
    $driftDelta = @(Compare-Object $driftExpected $driftActual | Where-Object { $null -ne $_ })
    if ($driftDelta.Count -eq 0) {
        foreach ($item in $driftActual) {
            Write-Line ("  [INTENTIONAL] {0}" -f $item)
        }
        Add-Pass 'config drift matches the documented set'
    } else {
        Add-Fail 'config drift does not match the documented set'
        foreach ($item in $driftActual) {
            Write-Line ("  [OBSERVED] {0}" -f $item)
        }
        foreach ($row in $driftDelta) {
            Write-Line ("  [DRIFT-DELTA] {0} {1}" -f $row.SideIndicator, $row.InputObject)
        }
    }

    Write-Line ''
    Write-Line '--- DOCUMENTED DIFFERENCES ---'
    foreach ($note in @($catalog.intentional_differences)) {
        Write-Line ("  [NOTE] {0}" -f [string]$note)
    }
    Write-Line '  [NOTE] HC_SVC_HC_TEARSHEETS_PASSWORD is an -Apply input only. Dry-run does not read it.'

    Write-Line ''
    Write-Line '--- UNCHANGED SERVICES ---'
    $after = Get-ServiceSnapshot $catalog
    Test-SnapshotUnchanged $before $after

    Write-Line ''
    if ($Script:Fail -eq 0) {
        Write-Line 'DRY-RUN RESULT: PASS'
        Write-Line 'MUTATIONS: none'
        exit 0
    }
    Write-Line ("DRY-RUN RESULT: FAIL ({0})" -f $Script:Fail)
    Write-Line 'MUTATIONS: none'
    exit 1
}

$invokeApply = $Apply.IsPresent -and -not $DryRun.IsPresent
if ($invokeApply) {
    try {
        Invoke-ApplyChanges -Path $CatalogPath
        Write-Line 'APPLY RESULT: completed'
        exit 0
    } catch {
        Write-Line ('APPLY REFUSED: ' + $_.Exception.Message)
        if ($Script:MutationsAllowed) {
            Write-Line 'MUTATIONS: apply stopped after a change may have started'
        } else {
            Write-Line 'MUTATIONS: none'
        }
        exit 2
    }
}

try {
    Invoke-DryRun -Path $CatalogPath
} catch {
    Write-Line ('DRY-RUN ERROR: ' + $_.Exception.Message)
    Write-Line 'MUTATIONS: none'
    exit 1
}
