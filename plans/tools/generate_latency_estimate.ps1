Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Globalization

$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$csvPath = Join-Path $repo "plans\data\latency_estimate.csv"
$outPath = Join-Path $repo "ReportLatex\fig_latency_estimate.png"

$rows = Import-Csv $csvPath
$values = @($rows | ForEach-Object { [double]$_.latency_ms })
$mean = ($values | Measure-Object -Average).Average
$min = ($values | Measure-Object -Minimum).Minimum
$max = ($values | Measure-Object -Maximum).Maximum
$sumSq = 0.0
foreach ($v in $values) {
    $sumSq += [Math]::Pow($v - $mean, 2)
}
$std = [Math]::Sqrt($sumSq / [Math]::Max(1, $values.Count - 1))

$w = 1500
$h = 900
$bmp = New-Object System.Drawing.Bitmap($w, $h)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
$g.Clear([System.Drawing.Color]::White)

function Font([float]$size, [string]$style = "Regular") {
    $fs = [System.Drawing.FontStyle]::Regular
    if ($style -eq "Bold") { $fs = [System.Drawing.FontStyle]::Bold }
    return New-Object System.Drawing.Font("Segoe UI", $size, $fs)
}

function DrawText([string]$text, [int]$x, [int]$y, [int]$ww, [int]$hh, [float]$size, [bool]$bold = $false) {
    $style = "Regular"
    if ($bold) { $style = "Bold" }
    $font = Font $size $style
    $brush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(28, 34, 44))
    $sf = New-Object System.Drawing.StringFormat
    $sf.Alignment = [System.Drawing.StringAlignment]::Center
    $sf.LineAlignment = [System.Drawing.StringAlignment]::Center
    $g.DrawString($text, $font, $brush, (New-Object System.Drawing.RectangleF($x, $y, $ww, $hh)), $sf)
    $font.Dispose(); $brush.Dispose(); $sf.Dispose()
}

DrawText "Preliminary Latency Estimate" 0 25 $w 48 28 $true
$meanText = $mean.ToString("F1", [System.Globalization.CultureInfo]::InvariantCulture)
$stdText = $std.ToString("F1", [System.Globalization.CultureInfo]::InvariantCulture)
DrawText ("N={0}, mean={1} ms, std={2} ms" -f $values.Count, $meanText, $stdText) 0 75 $w 34 17 $false

$left = 110
$top = 145
$plotW = 1260
$plotH = 580
$axisPen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(45, 68, 93), 3)
$gridPen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(220, 226, 232), 1)
$barBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(76, 135, 173))
$meanPen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(176, 87, 54), 4)
$textBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(28, 34, 44))
$fontSmall = Font 13

$yMin = 0
$yMax = 180
for ($tick = 0; $tick -le $yMax; $tick += 30) {
    $y = $top + $plotH - (($tick - $yMin) / ($yMax - $yMin)) * $plotH
    $g.DrawLine($gridPen, $left, [int]$y, $left + $plotW, [int]$y)
    $g.DrawString([string]$tick, $fontSmall, $textBrush, 35, [int]($y - 11))
}

$g.DrawLine($axisPen, $left, $top, $left, $top + $plotH)
$g.DrawLine($axisPen, $left, $top + $plotH, $left + $plotW, $top + $plotH)

$barGap = 8
$barW = [Math]::Floor(($plotW - (($values.Count + 1) * $barGap)) / $values.Count)
for ($i = 0; $i -lt $values.Count; $i++) {
    $v = $values[$i]
    $barH = (($v - $yMin) / ($yMax - $yMin)) * $plotH
    $x = $left + $barGap + $i * ($barW + $barGap)
    $y = $top + $plotH - $barH
    $g.FillRectangle($barBrush, [int]$x, [int]$y, [int]$barW, [int]$barH)
    if ((($i + 1) % 2) -eq 0) {
        $g.DrawString([string]($i + 1), $fontSmall, $textBrush, [int]($x + $barW / 2 - 8), $top + $plotH + 14)
    }
}

$meanY = $top + $plotH - (($mean - $yMin) / ($yMax - $yMin)) * $plotH
$g.DrawLine($meanPen, $left, [int]$meanY, $left + $plotW, [int]$meanY)
DrawText "Trial" ($left + 500) ($top + $plotH + 52) 260 34 16 $false
DrawText "Latency (ms)" 0 ($top - 42) 180 34 15 $false
DrawText "Estimated, not measured; replace with Raspberry Pi bench data when available." 0 800 $w 36 15 $false

$bmp.Save($outPath, [System.Drawing.Imaging.ImageFormat]::Png)
$fontSmall.Dispose(); $textBrush.Dispose(); $meanPen.Dispose(); $barBrush.Dispose(); $gridPen.Dispose(); $axisPen.Dispose()
$g.Dispose(); $bmp.Dispose()
Write-Host "wrote $outPath"
