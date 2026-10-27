param([string]$Port = 'COM3')

$ErrorActionPreference = 'Stop'
$kirbyPort = [System.IO.Ports.SerialPort]::new($Port, 115200)
$kirbyPort.ReadTimeout = 3000
$kirbyPort.WriteTimeout = 3000
$kirbyPort.DtrEnable = $true
$kirbyChecks = 0

function Send-KirbyControl([string]$Command, [string]$Expected) {
    $kirbyPort.Write($Command + "`n")
    $actual = $kirbyPort.ReadLine().TrimEnd([char[]]"`r`n")
    if ($actual -ne $Expected) { throw "$Command expected '$Expected', received '$actual'." }
    $script:kirbyChecks++
}

try {
    $kirbyPort.Open()
    $kirbyPort.DiscardInBuffer()
    $kirbyPort.Write("`nPING`n")
    $synchronized = $false
    for ($attempt = 0; $attempt -lt 8; $attempt++) {
        if ($kirbyPort.ReadLine().TrimEnd([char[]]"`r`n") -eq 'OK PONG 4') {
            $synchronized = $true
            break
        }
    }
    if (-not $synchronized) { throw 'Could not synchronize protocol v4.' }

    Send-KirbyControl 'MODE auto' 'OK APPLIED MODE auto'
    Send-KirbyControl 'STATUS' 'OK STATUS mode=auto expression=neutral look=centro animation=none'
    Send-KirbyControl 'EXPRESSION enojado' 'OK APPLIED EXPRESSION enojado'
    Send-KirbyControl 'LOOK izquierda' 'OK APPLIED LOOK izquierda'
    Send-KirbyControl 'STATUS' 'OK STATUS mode=manual expression=enojado look=izquierda animation=none'
    Write-Output 'Checking that manual selection survives the automatic deadline (13 seconds)...'
    Start-Sleep -Seconds 13
    Send-KirbyControl 'STATUS' 'OK STATUS mode=manual expression=enojado look=izquierda animation=none'

    Send-KirbyControl 'LOOK arriba' 'ERR INVALID_ARGUMENT'
    Send-KirbyControl 'MODE falso' 'ERR INVALID_ARGUMENT'
    Send-KirbyControl 'STATUS' 'OK STATUS mode=manual expression=enojado look=izquierda animation=none'
    foreach ($direction in @('centro', 'derecha', 'izquierda')) {
        Send-KirbyControl "LOOK $direction" "OK APPLIED LOOK $direction"
        Send-KirbyControl 'STATUS' "OK STATUS mode=manual expression=enojado look=$direction animation=none"
    }
    Send-KirbyControl 'EXPRESSION dormido' 'OK APPLIED EXPRESSION dormido'
    Send-KirbyControl 'STATUS' 'OK STATUS mode=manual expression=dormido look=izquierda animation=none'
    Send-KirbyControl 'EXPRESSION contento' 'OK APPLIED EXPRESSION contento'
    Send-KirbyControl 'STATUS' 'OK STATUS mode=manual expression=contento look=izquierda animation=none'
    Send-KirbyControl 'MODE manual' 'OK APPLIED MODE manual'
    Send-KirbyControl 'STATUS' 'OK STATUS mode=manual expression=contento look=izquierda animation=none'

    Send-KirbyControl 'MODE auto' 'OK APPLIED MODE auto'
    Send-KirbyControl 'STATUS' 'OK STATUS mode=auto expression=neutral look=centro animation=none'
    Write-Output 'Checking that automatic playback resumes (13 seconds)...'
    Start-Sleep -Seconds 13
    $kirbyPort.Write("STATUS`n")
    $autoState = $kirbyPort.ReadLine().TrimEnd([char[]]"`r`n")
    if (-not $autoState.StartsWith('OK STATUS mode=auto ') -or $autoState.EndsWith('animation=none')) {
        throw "Demo did not resume: $autoState"
    }
    $kirbyChecks++
    Send-KirbyControl 'EXPRESSION enojado' 'OK APPLIED EXPRESSION enojado'
    Send-KirbyControl 'LOOK izquierda' 'OK APPLIED LOOK izquierda'
    Send-KirbyControl 'STATUS' 'OK STATUS mode=manual expression=enojado look=izquierda animation=none'
    Write-Output "TK16 USB PASS: $kirbyChecks checks on $Port. Left manual angry/left for visual verification."
}
finally {
    if ($kirbyPort.IsOpen) { $kirbyPort.Close() }
    $kirbyPort.Dispose()
}
