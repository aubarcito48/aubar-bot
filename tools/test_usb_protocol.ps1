param([string]$Port = 'COM3')

$ErrorActionPreference = 'Stop'
$kirbyPort = [System.IO.Ports.SerialPort]::new($Port, 115200)
$kirbyPort.ReadTimeout = 3000
$kirbyPort.WriteTimeout = 3000
$kirbyPort.DtrEnable = $true
$kirbyChecks = 0

function Assert-KirbyResponse([string]$Expected) {
    try { $actual = $kirbyPort.ReadLine().TrimEnd([char[]]"`r`n") }
    catch [System.TimeoutException] { throw "Timeout waiting for '$Expected' after $script:kirbyChecks successful checks." }
    if ($actual -ne $Expected) { throw "Expected '$Expected', received '$actual'." }
    $script:kirbyChecks++
}

try {
    $kirbyPort.Open()
    $kirbyPort.DiscardInBuffer()
    # End any incomplete line left by a previous client before starting checks.
    $kirbyPort.Write("`nPING`n")
    $synchronized = $false
    for ($attempt = 0; $attempt -lt 8; $attempt++) {
        if ($kirbyPort.ReadLine().TrimEnd([char[]]"`r`n") -eq 'OK PONG 3') {
            $synchronized = $true
            break
        }
    }
    if (-not $synchronized) { throw 'Could not synchronize the USB protocol.' }
    $cases = @(
        @('PING', 'OK PONG 3'),
        @('EXPRESSION neutral', 'OK APPLIED EXPRESSION neutral'),
        @('EXPRESSION contento', 'OK APPLIED EXPRESSION contento'),
        @('EXPRESSION sorprendido', 'OK APPLIED EXPRESSION sorprendido'),
        @('EXPRESSION dormido', 'OK APPLIED EXPRESSION dormido'),
        @('EXPRESSION enojado', 'OK APPLIED EXPRESSION enojado'),
        @('LOOK izquierda', 'OK APPLIED LOOK izquierda'),
        @('LOOK centro', 'OK APPLIED LOOK centro'),
        @('LOOK derecha', 'OK APPLIED LOOK derecha'),
        @('MODE manual', 'OK APPLIED MODE manual'),
        @('MODE auto', 'OK APPLIED MODE auto'),
        @('LOOK arriba', 'ERR INVALID_ARGUMENT'),
        @('EXPRESSION', 'ERR INVALID_ARGUMENT'),
        @('PING extra', 'ERR INVALID_ARGUMENT'),
        @('LOOK  centro', 'ERR INVALID_ARGUMENT'),
        @('MODE auto extra', 'ERR INVALID_ARGUMENT'),
        @('HELLO', 'ERR UNKNOWN_COMMAND'),
        @('', 'ERR EMPTY')
    )
    foreach ($case in $cases) {
        $kirbyPort.Write($case[0] + "`n")
        Assert-KirbyResponse $case[1]
    }

    # A partial line must not produce a response before LF.
    $kirbyPort.Write('EXPRE')
    $kirbyPort.ReadTimeout = 150
    $incompleteReplied = $false
    try { $null = $kirbyPort.ReadLine(); $incompleteReplied = $true }
    catch [System.TimeoutException] { }
    if ($incompleteReplied) { throw 'Incomplete line produced a response.' }
    $kirbyChecks++
    $kirbyPort.ReadTimeout = 3000
    $kirbyPort.Write("SSION neutral`r`n")
    Assert-KirbyResponse 'OK APPLIED EXPRESSION neutral'

    $binary = [byte[]](80, 73, 78, 71, 0, 10)
    $kirbyPort.Write($binary, 0, $binary.Length)
    Assert-KirbyResponse 'ERR INVALID_CHARACTER'

    $kirbyPort.Write(('X' * 64) + "`n")
    Assert-KirbyResponse 'ERR UNKNOWN_COMMAND'
    $kirbyPort.Write(('X' * 65) + "`n")
    Assert-KirbyResponse 'ERR LINE_TOO_LONG'
    $kirbyPort.Write(('X' * 1000) + "PING`nPING`n")
    Assert-KirbyResponse 'ERR LINE_TOO_LONG'
    Assert-KirbyResponse 'OK PONG 3'

    # Check recovery repeatedly while the production animation loop runs.
    for ($index = 0; $index -lt 20; $index++) {
        $kirbyPort.Write("LOOK arriba`n")
        Assert-KirbyResponse 'ERR INVALID_ARGUMENT'
        $kirbyPort.Write("PING`n")
        Assert-KirbyResponse 'OK PONG 3'
    }
    Write-Output "TK15 USB PASS: $kirbyChecks checks on $Port."
}
finally {
    if ($kirbyPort.IsOpen) { $kirbyPort.Close() }
    $kirbyPort.Dispose()
}
