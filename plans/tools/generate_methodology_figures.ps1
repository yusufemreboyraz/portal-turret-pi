Add-Type -AssemblyName System.Drawing

$outDir = Resolve-Path (Join-Path $PSScriptRoot "..\..\ReportLatex")

function New-Canvas([int]$w, [int]$h) {
    $bmp = New-Object System.Drawing.Bitmap($w, $h)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
    $g.Clear([System.Drawing.Color]::White)
    return @($bmp, $g)
}

function New-Font([float]$size, [bool]$bold = $false) {
    $style = [System.Drawing.FontStyle]::Regular
    if ($bold) { $style = [System.Drawing.FontStyle]::Bold }
    return New-Object System.Drawing.Font("Segoe UI", $size, $style)
}

function Draw-Text($g, [string]$text, [int]$x, [int]$y, [int]$w, [int]$h, [float]$size, [bool]$bold = $false) {
    $font = New-Font $size $bold
    $brush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(28, 34, 44))
    $sf = New-Object System.Drawing.StringFormat
    $sf.Alignment = [System.Drawing.StringAlignment]::Center
    $sf.LineAlignment = [System.Drawing.StringAlignment]::Center
    $g.DrawString($text, $font, $brush, (New-Object System.Drawing.RectangleF($x, $y, $w, $h)), $sf)
    $font.Dispose(); $brush.Dispose(); $sf.Dispose()
}

function Draw-Box($g, [int]$x, [int]$y, [int]$w, [int]$h, [string]$title, [string[]]$lines, $fill, $border) {
    $rect = New-Object System.Drawing.Rectangle($x, $y, $w, $h)
    $brush = New-Object System.Drawing.SolidBrush($fill)
    $pen = New-Object System.Drawing.Pen($border, 3)
    $g.FillRectangle($brush, $rect)
    $g.DrawRectangle($pen, $rect)
    Draw-Text $g $title $x ($y + 8) $w 30 16 $true
    Draw-Text $g ([string]::Join("`n", $lines)) ($x + 8) ($y + 44) ($w - 16) ($h - 52) 12 $false
    $brush.Dispose(); $pen.Dispose()
}

function Draw-Arrow($g, [int]$x1, [int]$y1, [int]$x2, [int]$y2, [string]$label = "") {
    $pen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(45, 68, 93), 4)
    $cap = New-Object System.Drawing.Drawing2D.AdjustableArrowCap(6, 7)
    $pen.CustomEndCap = $cap
    $g.DrawLine($pen, $x1, $y1, $x2, $y2)
    if ($label.Length -gt 0) {
        $mx = [int](($x1 + $x2) / 2 - 70)
        $my = [int](($y1 + $y2) / 2 - 22)
        $bg = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(248, 250, 252))
        $g.FillRectangle($bg, $mx, $my, 140, 36)
        Draw-Text $g $label $mx $my 140 36 11 $false
        $bg.Dispose()
    }
    $pen.Dispose(); $cap.Dispose()
}

function Save-Png($bmp, $g, [string]$name) {
    $path = Join-Path $outDir $name
    $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bmp.Dispose()
    Write-Host "wrote $path"
}

function Draw-OnnxPipeline {
    $pair = New-Canvas 1650 520
    $bmp = $pair[0]; $g = $pair[1]
    Draw-Text $g "YOLO11n to ONNX Edge-AI Deployment Pipeline" 0 24 1650 44 24 $true

    $fillA = [System.Drawing.Color]::FromArgb(232, 241, 248)
    $borderA = [System.Drawing.Color]::FromArgb(53, 101, 146)
    $fillB = [System.Drawing.Color]::FromArgb(236, 243, 232)
    $borderB = [System.Drawing.Color]::FromArgb(86, 137, 76)
    $fillC = [System.Drawing.Color]::FromArgb(252, 244, 226)
    $borderC = [System.Drawing.Color]::FromArgb(176, 127, 40)

    $y = 160
    Draw-Box $g 70 $y 250 135 "YOLO11n" @("pretrained detector", "COCO person class") $fillA $borderA
    Draw-Box $g 380 $y 250 135 "Export" @("ONNX graph", "single deploy file") $fillB $borderB
    Draw-Box $g 690 $y 250 135 "Optimize" @("graph export", "quantization-oriented") $fillC $borderC
    Draw-Box $g 1000 $y 250 135 "Pi 5 Runtime" @("ONNX Runtime CPU", "640x640 letterbox") $fillB $borderB
    Draw-Box $g 1310 $y 250 135 "Closed Loop" @("person bbox", "FSM + servo command") $fillA $borderA

    Draw-Arrow $g 320 228 380 228
    Draw-Arrow $g 630 228 690 228
    Draw-Arrow $g 940 228 1000 228
    Draw-Arrow $g 1250 228 1310 228
    Draw-Text $g "No on-device PyTorch training, analytics dashboard, or cloud dependency is required on the embedded host." 170 360 1310 54 15 $false
    Save-Png $bmp $g "fig_onnx_pipeline.png"
}

function Draw-AudioNetwork {
    $pair = New-Canvas 1500 560
    $bmp = $pair[0]; $g = $pair[1]
    Draw-Text $g "Network Audio Subsystem" 0 24 1500 44 24 $true

    $fillPi = [System.Drawing.Color]::FromArgb(232, 241, 248)
    $borderPi = [System.Drawing.Color]::FromArgb(53, 101, 146)
    $fillHttp = [System.Drawing.Color]::FromArgb(236, 243, 232)
    $borderHttp = [System.Drawing.Color]::FromArgb(86, 137, 76)
    $fillPhone = [System.Drawing.Color]::FromArgb(246, 235, 245)
    $borderPhone = [System.Drawing.Color]::FromArgb(142, 92, 145)

    Draw-Box $g 80 165 285 145 "FSM Event" @("found / lock / lost", "non-blocking trigger") $fillPi $borderPi
    Draw-Box $g 450 165 285 145 "SoundPlayer" @("select WAV file", "TargetFound / TargetLost") $fillPi $borderPi
    Draw-Box $g 820 165 285 145 "HTTP Streamer" @("ThreadingHTTPServer", "port 8765") $fillHttp $borderHttp
    Draw-Box $g 1190 165 235 145 "Smartphone" @("browser client", "HTML5 audio") $fillPhone $borderPhone

    Draw-Arrow $g 365 238 450 238 "play()"
    Draw-Arrow $g 735 238 820 238 "serve"
    Draw-Arrow $g 1105 238 1190 238 "WiFi"
    Draw-Text $g "Audio is offloaded to phones after local speaker drivers failed; servo and vision timing remain unaffected." 170 390 1160 54 15 $false
    Save-Png $bmp $g "fig_audio_network.png"
}

Draw-OnnxPipeline
Draw-AudioNetwork
