# Local SAPI helper. The request is JSON on stdin, never executable command text.
# Speak flag 16 treats the input as plain text, including text beginning with "<".
# https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ee125223(v=vs.85)
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$aubarSpeaker = $null
$aubarErrorCode = 'SPEECH_FAILED'
try {
    $aubarRequest = [Console]::In.ReadToEnd() | ConvertFrom-Json
    if ($aubarRequest.action -notin @('voices', 'speak')) { throw 'Invalid speech action.' }
    $aubarSpeaker = New-Object -ComObject SAPI.SpVoice
    $aubarTokens = @()
    $aubarVoices = @()
    foreach ($aubarToken in $aubarSpeaker.GetVoices()) {
        foreach ($aubarLanguageCode in $aubarToken.GetAttribute('Language').Split(';')) {
            try {
                $aubarCulture = [Globalization.CultureInfo]::GetCultureInfo(
                    [Convert]::ToInt32($aubarLanguageCode, 16))
            } catch { continue }
            if ($aubarCulture.TwoLetterISOLanguageName -eq 'es') {
                $aubarTokens += $aubarToken
                $aubarVoices += @{
                    id = $aubarToken.Id
                    name = $aubarToken.GetDescription()
                    language = $aubarCulture.Name
                }
                break
            }
        }
    }
    if ($aubarVoices.Count -eq 0) {
        $aubarErrorCode = 'NO_SPANISH_VOICE'
        throw 'No Spanish SAPI voice is installed.'
    }
    if ($aubarRequest.action -eq 'voices') {
        [Console]::Out.WriteLine((@{ok=$true; voices=@($aubarVoices)} | ConvertTo-Json -Depth 4 -Compress))
    } else {
        if ($aubarRequest.text -isnot [string] -or [string]::IsNullOrWhiteSpace($aubarRequest.text) -or
            $aubarRequest.text.Length -gt 2000 -or $aubarRequest.text.Contains([char]0)) {
            throw 'Invalid speech text.'
        }
        if ($aubarRequest.volume -isnot [int] -or $aubarRequest.volume -lt 0 -or $aubarRequest.volume -gt 100 -or
            $aubarRequest.rate -isnot [int] -or $aubarRequest.rate -lt -10 -or $aubarRequest.rate -gt 10) {
            throw 'Invalid voice settings.'
        }
        $aubarSpeaker.Voice = $aubarTokens[0]
        $aubarSpeaker.Volume = $aubarRequest.volume
        $aubarSpeaker.Rate = $aubarRequest.rate
        $null = $aubarSpeaker.Speak($aubarRequest.text, 16)
        [Console]::Out.WriteLine((@{ok=$true; voice=$aubarVoices[0]} | ConvertTo-Json -Depth 4 -Compress))
    }
} catch {
    [Console]::Out.WriteLine((@{ok=$false; code=$aubarErrorCode} | ConvertTo-Json -Compress))
    exit 1
} finally {
    if ($null -ne $aubarSpeaker) {
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($aubarSpeaker)
    }
}
