$ErrorActionPreference = "Continue"
$PY = "D:\6_code\13_python\1_python3.11.0\python.exe"
$out = "D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\意象训练与筋膜感知调研\原始数据\YouTube"
$proxy = "http://127.0.0.1:7892"

$vids = @(
  @{id="dXcg4NLPC_Y"; slug="01_wilke_force_transmission"},
  @{id="fOwhjE0VgXA"; slug="02_schleip_orchestration"},
  @{id="aboOT94CaR8"; slug="03_spindle_vs_gto"},
  @{id="lvqoQQBoLc4"; slug="04_autogenic_inhibition"},
  @{id="rq1X5nwmfSQ"; slug="05_calgary_mind_strength"},
  @{id="2ZkJtIouKzE"; slug="06_huberman_brainbody"},
  @{id="R5Z6caL6SUw"; slug="07_optimal_theory"},
  @{id="F0dKzQ3bB88"; slug="08_attentional_focus"},
  @{id="dvRiIxr3CAw"; slug="09_differential_learning"},
  @{id="9egMuLqjEgA"; slug="10_aphantasia_motor_simulation"},
  @{id="Y8iEsi4Mr5U"; slug="11_imagery_strength_study"},
  @{id="9N7g6IXqmy8"; slug="12_myofascial_trains_hype"},
  @{id="OK6DlVBqACY"; slug="13_schleip_podcast"}
)

$report = @()
foreach ($v in $vids) {
  $id = $v.id; $slug = $v.slug
  $base = Join-Path $out $slug
  $url = "https://www.youtube.com/watch?v=$id"
  $status = "none"
  # pass 1: manual subs
  & $PY -m yt_dlp --no-update --proxy $proxy --write-subs --sub-langs "en" --skip-download --sleep-subtitles 2 --output $base $url 2>&1 | Out-Null
  Start-Sleep -Seconds 2
  if (Test-Path "$base.en.vtt") { $status = "manual" }
  else {
    # pass 2: auto subs
    & $PY -m yt_dlp --no-update --proxy $proxy --write-auto-subs --sub-langs "en" --skip-download --sleep-subtitles 2 --output $base $url 2>&1 | Out-Null
    Start-Sleep -Seconds 2
    if (Test-Path "$base.en.vtt") { $status = "auto" }
  }
  $size = 0
  if (Test-Path "$base.en.vtt") { $size = (Get-Item "$base.en.vtt").Length }
  $line = "$slug | $id | $status | ${size}B"
  Write-Output $line
  $report += $line
}
$report | Out-File -FilePath "$out\_subtitle_fetch_report.txt" -Encoding utf8
Write-Output "=== DONE ==="
