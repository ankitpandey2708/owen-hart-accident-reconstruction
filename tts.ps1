Add-Type -AssemblyName System.Speech
$items = Get-Content "$PSScriptRoot\narration.json" -Raw | ConvertFrom-Json
foreach ($it in $items) {
  $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
  $s.SelectVoice('Microsoft David Desktop')
  $s.Rate = -1
  $s.SetOutputToWaveFile("$PSScriptRoot\audio\$($it.id).wav")
  $s.Speak($it.text)
  $s.Dispose()
}
