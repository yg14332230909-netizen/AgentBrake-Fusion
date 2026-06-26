param(
  [string]$Model = $(if ($env:MODEL) { $env:MODEL } else { "deepseek-chat" }),
  [string]$Attack = $(if ($env:ATTACK_NAME) { $env:ATTACK_NAME } else { "important_instructions" }),
  [string]$GatewayPort = $(if ($env:GATEWAY_PORT) { $env:GATEWAY_PORT } else { "8765" }),
  [string]$GatewayApiKey = $(if ($env:AGENTBRAKE_GATEWAY_API_KEY) { $env:AGENTBRAKE_GATEWAY_API_KEY } else { "agentbrake-fusion-local" }),
  [string]$UpstreamBaseUrl = $(if ($env:OPENAI_BASE_URL) { $env:OPENAI_BASE_URL } else { "https://api.deepseek.com/v1" }),
  [string]$UpstreamApiKey = $(if ($env:OPENAI_API_KEY) { $env:OPENAI_API_KEY } else { "" })
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $scriptDir))
Set-Location $repoRoot

$env:AGENTBRAKE_EVAL_FAST_MODE = "1"
$env:AGENTBRAKE_DISABLE_STUDIO_EVENTS = "1"
$env:AGENTBRAKE_AUDIT_BUFFERED = "1"
$env:AGENTBRAKE_EVIDENCE_GRAPH_MODE = "summary"
$env:AGENTBRAKE_POLICY_TRACE_MODE = "summary"
$env:AGENTBRAKE_DISABLE_PREFLIGHT = "1"
$env:AGENTBRAKE_SESSION_CACHE = "1"
$env:AGENTBRAKE_OPENAI_COMPAT_SYSTEM_ROLE = "1"

$logRoot = Join-Path $repoRoot "experiments/agentdojo_toolgate/logs"
$reportRoot = Join-Path $repoRoot "experiments/agentdojo_toolgate/reports"
$runReportDir = Join-Path $reportRoot "runs"
New-Item -ItemType Directory -Force -Path $logRoot, $reportRoot, $runReportDir | Out-Null

$suites = @("banking", "slack", "workspace", "travel")

function Write-ErrorReport {
  param(
    [string]$Step,
    [string]$Message
  )
  $path = Join-Path $reportRoot "error_${Step}.md"
  @"
# Step Failed

- step: $Step
- message: $Message
"@ | Set-Content -Path $path -Encoding UTF8
}

function Invoke-Run {
  param(
    [string]$Step,
    [string[]]$CommandArgs,
    [string]$StdoutPath
  )
  Write-Host "==> $Step"
  $stdoutTarget = $StdoutPath
  $stderrTarget = if ($StdoutPath) { [System.IO.Path]::ChangeExtension($StdoutPath, ".stderr.log") } else { $null }
  if ($stdoutTarget) {
    $parent = Split-Path -Parent $stdoutTarget
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    if ($stderrTarget) {
      $stderrParent = Split-Path -Parent $stderrTarget
      if ($stderrParent) { New-Item -ItemType Directory -Force -Path $stderrParent | Out-Null }
    }
    $filteredArgs = @($CommandArgs | Where-Object { $_ -ne $null -and $_ -ne "" })
    $proc = Start-Process -FilePath "python" -ArgumentList $filteredArgs -Wait -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdoutTarget -RedirectStandardError $stderrTarget
    if ($proc.ExitCode -ne 0) {
      throw "Step $Step failed with exit code $($proc.ExitCode)"
    }
  } else {
    $filteredArgs = @($CommandArgs | Where-Object { $_ -ne $null -and $_ -ne "" })
    $proc = Start-Process -FilePath "python" -ArgumentList $filteredArgs -Wait -PassThru -WindowStyle Hidden
    if ($proc.ExitCode -ne 0) {
      throw "Step $Step failed with exit code $($proc.ExitCode)"
    }
  }
}

function Invoke-EvalRun {
  param(
    [string]$Step,
    [string]$RunName,
    [string[]]$CommandArgs,
    [string]$StdoutPath
  )
  $resultPath = Join-Path $runReportDir "${RunName}.json"
  if (Test-Path $resultPath) {
    Write-Host "==> $Step (skip existing $RunName)"
    return
  }
  Invoke-Run -Step $Step -CommandArgs $CommandArgs -StdoutPath $StdoutPath
}

function Set-DirectUpstreamEnv {
  $env:OPENAI_BASE_URL = $UpstreamBaseUrl
  $env:OPENAI_API_KEY = $UpstreamApiKey
}

function Set-GatewayEnv {
  $env:OPENAI_BASE_URL = "http://127.0.0.1:$GatewayPort/v1"
  $env:OPENAI_API_KEY = $GatewayApiKey
}

function Start-Gateway {
  $gatewayLogDir = Join-Path $logRoot "agentbrake_gateway_only"
  New-Item -ItemType Directory -Force -Path $gatewayLogDir | Out-Null
  $gatewayPidPath = Join-Path $gatewayLogDir "gateway.pid"
  if (Test-Path $gatewayPidPath) {
    $existingGatewayProcessId = Get-Content $gatewayPidPath | Select-Object -First 1
    if ($existingGatewayProcessId) {
      $existingGateway = Get-Process -Id ([int]$existingGatewayProcessId) -ErrorAction SilentlyContinue
      if ($existingGateway) {
        Write-Host "==> gateway already running (pid $existingGatewayProcessId)"
        return
      }
    }
  }
  $audit = Join-Path $gatewayLogDir "gateway_audit.jsonl"
  $stdout = Join-Path $gatewayLogDir "gateway.stdout.log"
  $stderr = Join-Path $gatewayLogDir "gateway.stderr.log"
  $args = @(
    "-m", "agentbrake.cli", "gateway-start",
    "--repo", $repoRoot,
    "--host", "127.0.0.1",
    "--port", $GatewayPort,
    "--audit", $audit,
    "--policy-mode", "enforce",
    "--upstream-base-url", $UpstreamBaseUrl,
    "--gateway-api-key", $GatewayApiKey,
    "--release-mode", "gateway_only"
  )
  $proc = Start-Process -FilePath "python" -ArgumentList $args -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr
  Set-Content -Path $gatewayPidPath -Value $proc.Id -Encoding ASCII
  Start-Sleep -Seconds 3
}

function Stop-Gateway {
  $gatewayPidPath = Join-Path $logRoot "agentbrake_gateway_only/gateway.pid"
  if (Test-Path $gatewayPidPath) {
    $gatewayProcessId = Get-Content $gatewayPidPath | Select-Object -First 1
    if ($gatewayProcessId) {
      try { Stop-Process -Id [int]$gatewayProcessId -Force -ErrorAction Stop } catch {}
    }
  }
  Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -match 'agentbrake\.cli gateway-start' -and $_.CommandLine -match [regex]::Escape($repoRoot) } |
    ForEach-Object {
      try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop } catch {}
    }
  if (Test-Path $gatewayPidPath) {
    Remove-Item -Path $gatewayPidPath -Force -ErrorAction SilentlyContinue
  }
}

function Restart-Gateway {
  Stop-Gateway
  Start-Sleep -Seconds 5
  Start-Gateway
}

function Test-TransientGatewayFailure {
  param(
    [string]$Step,
    [string]$StdoutPath
  )
  $stderrPath = if ($StdoutPath) { [System.IO.Path]::ChangeExtension($StdoutPath, ".stderr.log") } else { Join-Path $reportRoot "$Step.stderr.log" }
  if (-not (Test-Path $stderrPath)) {
    return $false
  }
  $content = Get-Content $stderrPath -ErrorAction SilentlyContinue | Out-String
  return ($content -match '502|503|504|BadGateway|InternalServerError')
}

function Invoke-EvalRunWithRecovery {
  param(
    [string]$Step,
    [string]$RunName,
    [string[]]$CommandArgs,
    [string]$StdoutPath,
    [switch]$MayRestartGateway
  )
  try {
    Invoke-EvalRun -Step $Step -RunName $RunName -CommandArgs $CommandArgs -StdoutPath $StdoutPath
  } catch {
    if ($MayRestartGateway -and (Test-TransientGatewayFailure -Step $Step -StdoutPath $StdoutPath)) {
      Write-Host "==> $Step transient failure detected; restarting gateway and retrying once"
      Restart-Gateway
      Invoke-EvalRun -Step $Step -RunName $RunName -CommandArgs $CommandArgs -StdoutPath $StdoutPath
      return
    }
    throw
  }
}

function Invoke-EvalRunOptional {
  param(
    [string]$Step,
    [string]$RunName,
    [string[]]$CommandArgs,
    [string]$StdoutPath,
    [switch]$MayRestartGateway
  )
  try {
    Invoke-EvalRunWithRecovery -Step $Step -RunName $RunName -CommandArgs $CommandArgs -StdoutPath $StdoutPath -MayRestartGateway:$MayRestartGateway
  } catch {
    $failurePath = Join-Path $reportRoot "failed_${Step}.md"
    @"
# Optional Step Failed

- step: $Step
- run_name: $RunName
- message: $($_.Exception.Message)
- stdout: $StdoutPath
- stderr: $([System.IO.Path]::ChangeExtension($StdoutPath, ".stderr.log"))

This optional comparison step failed after retry. The full run continues so ToolGate results can still be produced.
"@ | Set-Content -Path $failurePath -Encoding UTF8
    Write-Host "==> $Step failed after retry; continuing"
  }
}

try {
  if (-not $UpstreamApiKey) {
    throw "Missing upstream API key. Set OPENAI_API_KEY before starting the full eval."
  }
  Set-DirectUpstreamEnv
  Invoke-Run -Step "dump_tools" -CommandArgs @(
    (Join-Path $scriptDir "01_dump_agentdojo_tools.py")
  ) -StdoutPath (Join-Path $reportRoot "dump_tools.stdout.log")

  foreach ($suite in $suites) {
    $suiteLogRoot = Join-Path $logRoot $suite
    New-Item -ItemType Directory -Force -Path $suiteLogRoot | Out-Null

    Invoke-EvalRun -Step "${suite}_no_defense" -RunName "${suite}_no_defense_attack" -CommandArgs @(
      "-m", "agentbrake.eval.agentdojo.run_toolgate_eval",
      "--suite", $suite,
      "--model", $Model,
      "--defense", "none",
      "--attack", $Attack,
      "--run-name", "${suite}_no_defense_attack",
      "--logdir", (Join-Path $suiteLogRoot "no_defense"),
      "--report-dir", $runReportDir
    ) -StdoutPath (Join-Path $suiteLogRoot "no_defense.stdout.log")

    Invoke-EvalRun -Step "${suite}_tool_filter" -RunName "${suite}_tool_filter_attack" -CommandArgs @(
      "-m", "agentbrake.eval.agentdojo.run_toolgate_eval",
      "--suite", $suite,
      "--model", $Model,
      "--defense", "tool_filter",
      "--attack", $Attack,
      "--run-name", "${suite}_tool_filter_attack",
      "--logdir", (Join-Path $suiteLogRoot "tool_filter"),
      "--report-dir", $runReportDir
    ) -StdoutPath (Join-Path $suiteLogRoot "tool_filter.stdout.log")
  }

  Start-Gateway

  foreach ($suite in $suites) {
    $suiteLogRoot = Join-Path $logRoot $suite

    Set-GatewayEnv
    Invoke-EvalRunOptional -Step "${suite}_gateway_only" -RunName "${suite}_agentbrake_gateway_only_attack" -CommandArgs @(
      "-m", "agentbrake.eval.agentdojo.run_toolgate_eval",
      "--suite", $suite,
      "--model", $Model,
      "--defense", "none",
      "--attack", $Attack,
      "--run-name", "${suite}_agentbrake_gateway_only_attack",
      "--logdir", (Join-Path $suiteLogRoot "agentbrake_gateway_only"),
      "--report-dir", $runReportDir
    ) -StdoutPath (Join-Path $suiteLogRoot "gateway_only.stdout.log") -MayRestartGateway

    Set-DirectUpstreamEnv
    Invoke-EvalRunWithRecovery -Step "${suite}_toolgate" -RunName "${suite}_agentbrake_toolgate_attack" -CommandArgs @(
      "-m", "agentbrake.eval.agentdojo.run_toolgate_eval",
      "--suite", $suite,
      "--model", $Model,
      "--defense", "agentbrake_toolgate",
      "--attack", $Attack,
      "--run-name", "${suite}_agentbrake_toolgate_attack",
      "--logdir", (Join-Path $suiteLogRoot "agentbrake_toolgate"),
      "--report-dir", $runReportDir
    ) -StdoutPath (Join-Path $suiteLogRoot "toolgate.stdout.log") -MayRestartGateway

    Invoke-EvalRunWithRecovery -Step "${suite}_toolgate_benign" -RunName "${suite}_agentbrake_toolgate_benign" -CommandArgs @(
      "-m", "agentbrake.eval.agentdojo.run_toolgate_eval",
      "--suite", $suite,
      "--model", $Model,
      "--defense", "agentbrake_toolgate",
      "--attack", "none",
      "--run-name", "${suite}_agentbrake_toolgate_benign",
      "--logdir", (Join-Path $suiteLogRoot "agentbrake_toolgate_benign"),
      "--report-dir", $runReportDir
    ) -StdoutPath (Join-Path $suiteLogRoot "toolgate_benign.stdout.log") -MayRestartGateway

    Invoke-EvalRunWithRecovery -Step "${suite}_toolgate_no_taxonomy" -RunName "${suite}_agentbrake_toolgate_no_taxonomy_attack" -CommandArgs @(
      "-m", "agentbrake.eval.agentdojo.run_toolgate_eval",
      "--suite", $suite,
      "--model", $Model,
      "--defense", "agentbrake_toolgate",
      "--attack", $Attack,
      "--run-name", "${suite}_agentbrake_toolgate_no_taxonomy_attack",
      "--disable-taxonomy",
      "--logdir", (Join-Path $suiteLogRoot "agentbrake_toolgate_no_taxonomy"),
      "--report-dir", $runReportDir
    ) -StdoutPath (Join-Path $suiteLogRoot "toolgate_no_taxonomy.stdout.log") -MayRestartGateway

    Invoke-EvalRunWithRecovery -Step "${suite}_toolgate_no_state_tracker" -RunName "${suite}_agentbrake_toolgate_no_state_tracker_attack" -CommandArgs @(
      "-m", "agentbrake.eval.agentdojo.run_toolgate_eval",
      "--suite", $suite,
      "--model", $Model,
      "--defense", "agentbrake_toolgate",
      "--attack", $Attack,
      "--run-name", "${suite}_agentbrake_toolgate_no_state_tracker_attack",
      "--disable-state-tracker",
      "--logdir", (Join-Path $suiteLogRoot "agentbrake_toolgate_no_state_tracker"),
      "--report-dir", $runReportDir
    ) -StdoutPath (Join-Path $suiteLogRoot "toolgate_no_state_tracker.stdout.log") -MayRestartGateway

    Invoke-EvalRunWithRecovery -Step "${suite}_toolgate_no_invariants" -RunName "${suite}_agentbrake_toolgate_no_invariants_attack" -CommandArgs @(
      "-m", "agentbrake.eval.agentdojo.run_toolgate_eval",
      "--suite", $suite,
      "--model", $Model,
      "--defense", "agentbrake_toolgate",
      "--attack", $Attack,
      "--run-name", "${suite}_agentbrake_toolgate_no_invariants_attack",
      "--disable-invariants",
      "--logdir", (Join-Path $suiteLogRoot "agentbrake_toolgate_no_invariants"),
      "--report-dir", $runReportDir
    ) -StdoutPath (Join-Path $suiteLogRoot "toolgate_no_invariants.stdout.log") -MayRestartGateway

    Invoke-EvalRunWithRecovery -Step "${suite}_full_fast" -RunName "${suite}_full_agentbrake_fast_attack" -CommandArgs @(
      "-m", "agentbrake.eval.agentdojo.run_toolgate_eval",
      "--suite", $suite,
      "--model", $Model,
      "--defense", "agentbrake_toolgate",
      "--attack", $Attack,
      "--run-name", "${suite}_full_agentbrake_fast_attack",
      "--logdir", (Join-Path $suiteLogRoot "full_agentbrake_fast"),
      "--report-dir", $runReportDir
    ) -StdoutPath (Join-Path $suiteLogRoot "full_fast.stdout.log") -MayRestartGateway
  }

  Set-DirectUpstreamEnv
  Invoke-Run -Step "collect_results" -CommandArgs @(
    (Join-Path $scriptDir "08_collect_results.py")
  ) -StdoutPath (Join-Path $reportRoot "collect_results.stdout.log")
  Invoke-Run -Step "profile_latency" -CommandArgs @(
    (Join-Path $scriptDir "09_profile_latency.py")
  ) -StdoutPath (Join-Path $reportRoot "profile_latency.stdout.log")
}
catch {
  Write-ErrorReport -Step "run_full_eval" -Message $_.Exception.Message
  throw
}
finally {
  Stop-Gateway
}
