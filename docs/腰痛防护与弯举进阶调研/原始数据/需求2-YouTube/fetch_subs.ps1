$py = "D:\6_code\13_python\1_python3.11.0\python.exe"
$outDir = "D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\腰痛防护与弯举进阶调研\原始数据\需求2-YouTube"
$logFile = Join-Path $outDir "fetch_log.txt"
"=== Fetch started $(Get-Date -Format o) ===" | Out-File -Encoding utf8 $logFile

# Priority list: id | short_name
$ids = @(
  @("GNO4OtYoCYk","JeffNippard_BestWorstBiceps_EMG"),
  @("q8jjwZbhBas","RP_5RulesOfBicepTraining"),
  @("20ibpB635Rw","JeremyEthier_DumbbellBiceps"),
  @("i1YgFZB6alI","JeffNippard_HowToBuildHugeBiceps"),
  @("gS-xsC48xTs","HouseOfHypertrophy_InclineVsPreacher"),
  @("dBZC24qvK8k","musclemonsters_ProgressIsolationLifts"),
  @("MBjezf-qinM","AlexLeonidas_MicroloadingIsntWorthIt"),
  @("cEEyH6JtCqQ","SeanNalewanyj_DynamicDoubleProgression"),
  @("mYf7QhCRYFw","ScottHerman_BarbellVsCableCurl"),
  @("qia2yOo6VJo","ScottHerman_DBCurlVsHammer"),
  @("Je3tL6M5B54","RippedBody_AutoregDoubleProgression"),
  @("KIxPOMNbnFs","JasonBlaha_MicroloadingFractionalPlates"),
  @("aYKsmKP5kd4","StartingStrength_Microloading"),
  @("p7k9LFQTzpU","ATHLEANX_BarbellVsDBVsCable"),
  @("lzQLqfbY0dA","BenYanes_AreHammerCurlsStupid"),
  @("jjnJHhzZUUM","JeremyEthier_STOPDoingBicepCurls"),
  @("iL0AsMX4-hA","NaturalHypertrophy_13YearsCheatCurls"),
  @("9e2EgsKo_qU","JeremyEthier_MoreGainsHalfTime")
)

foreach ($pair in $ids) {
  $id = $pair[0]; $name = $pair[1]
  $outTpl = Join-Path $outDir "${name}__${id}"
  $url = "https://www.youtube.com/watch?v=$id"
  $msg = "[$(Get-Date -Format HH:mm:ss)] === $id $name ==="
  Write-Host $msg
  Add-Content -Path $logFile -Value $msg -Encoding utf8

  # Try manual subs first
  & $py -m yt_dlp --no-update --proxy "http://127.0.0.1:7892" `
    --extractor-args "youtube:player_client=android" `
    --write-subs --sub-langs "en.*" --skip-download `
    --sleep-subtitles 2 `
    --output $outTpl $url 2>&1 | Tee-Object -FilePath $logFile -Append | Out-Null

  # Check if any .vtt produced
  $vtt = Get-ChildItem -Path $outDir -Filter "${name}__${id}*.vtt" -ErrorAction SilentlyContinue
  if (-not $vtt) {
    # Fall back to auto subs
    $msg2 = "  -> no manual subs, trying auto"
    Write-Host $msg2
    Add-Content -Path $logFile -Value $msg2 -Encoding utf8
    & $py -m yt_dlp --no-update --proxy "http://127.0.0.1:7892" `
      --extractor-args "youtube:player_client=android" `
      --write-auto-subs --sub-langs "en.*" --skip-download `
      --sleep-subtitles 2 `
      --output $outTpl $url 2>&1 | Tee-Object -FilePath $logFile -Append | Out-Null
  }

  Start-Sleep -Seconds 3
}
"=== Fetch done $(Get-Date -Format o) ===" | Add-Content -Path $logFile -Encoding utf8
Write-Host "ALL DONE"
