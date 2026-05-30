Add-Type -AssemblyName System.Drawing

$outDir = Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..\..\ReportLatex")) ""

function New-Canvas([int]$w, [int]$h) {
    $bmp = New-Object System.Drawing.Bitmap($w, $h)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
    $g.Clear([System.Drawing.Color]::White)
    return @($bmp, $g)
}

function New-Font([float]$size, [string]$style = "Regular") {
    $fontStyle = [System.Drawing.FontStyle]::Regular
    if ($style -eq "Bold") { $fontStyle = [System.Drawing.FontStyle]::Bold }
    return New-Object System.Drawing.Font("Segoe UI", $size, $fontStyle)
}

function Draw-Box($g, [int]$x, [int]$y, [int]$w, [int]$h, [string]$title, [string[]]$lines, $fill, $border) {
    $rect = New-Object System.Drawing.Rectangle($x, $y, $w, $h)
    $brush = New-Object System.Drawing.SolidBrush($fill)
    $pen = New-Object System.Drawing.Pen($border, 3)
    $g.FillRectangle($brush, $rect)
    $g.DrawRectangle($pen, $rect)
    $titleFont = New-Font 19 "Bold"
    $bodyFont = New-Font 15
    $textBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(28, 34, 44))
    $sf = New-Object System.Drawing.StringFormat
    $sf.Alignment = [System.Drawing.StringAlignment]::Center
    $sf.LineAlignment = [System.Drawing.StringAlignment]::Near
    $g.DrawString($title, $titleFont, $textBrush, (New-Object System.Drawing.RectangleF($x, ($y + 8), $w, 30)), $sf)
    $body = [string]::Join("`n", $lines)
    $g.DrawString($body, $bodyFont, $textBrush, (New-Object System.Drawing.RectangleF(($x + 10), ($y + 43), ($w - 20), ($h - 48))), $sf)
    $brush.Dispose(); $pen.Dispose(); $titleFont.Dispose(); $bodyFont.Dispose(); $textBrush.Dispose(); $sf.Dispose()
}

function Draw-Label($g, [string]$text, [int]$x, [int]$y, [int]$w, [int]$h, [float]$size = 15, [bool]$bold = $false) {
    $style = "Regular"
    if ($bold) { $style = "Bold" }
    $font = New-Font $size $style
    $brush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(28, 34, 44))
    $sf = New-Object System.Drawing.StringFormat
    $sf.Alignment = [System.Drawing.StringAlignment]::Center
    $sf.LineAlignment = [System.Drawing.StringAlignment]::Center
    $g.DrawString($text, $font, $brush, (New-Object System.Drawing.RectangleF($x, $y, $w, $h)), $sf)
    $font.Dispose(); $brush.Dispose(); $sf.Dispose()
}

function Draw-Arrow($g, [int]$x1, [int]$y1, [int]$x2, [int]$y2, [string]$label = "") {
    $pen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(45, 68, 93), 4)
    $cap = New-Object System.Drawing.Drawing2D.AdjustableArrowCap(6, 7)
    $pen.CustomEndCap = $cap
    $g.DrawLine($pen, $x1, $y1, $x2, $y2)
    if ($label.Length -gt 0) {
        $mx = [int](($x1 + $x2) / 2 - 105)
        $my = [int](($y1 + $y2) / 2 - 24)
        $bg = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(245, 248, 251))
        $g.FillRectangle($bg, $mx, $my, 210, 42)
        Draw-Label $g $label $mx $my 210 42 13 $false
        $bg.Dispose()
    }
    $pen.Dispose(); $cap.Dispose()
}

function Draw-PolylineArrow($g, [int[]]$points, [string]$label = "", [int]$lx = 0, [int]$ly = 0) {
    $pen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(45, 68, 93), 4)
    $plainPen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(45, 68, 93), 4)
    $cap = New-Object System.Drawing.Drawing2D.AdjustableArrowCap(6, 7)
    $pen.CustomEndCap = $cap
    for ($i = 0; $i -lt ($points.Length / 2 - 1); $i++) {
        $x1 = $points[$i * 2]
        $y1 = $points[$i * 2 + 1]
        $x2 = $points[$i * 2 + 2]
        $y2 = $points[$i * 2 + 3]
        if ($i -lt ($points.Length / 2 - 2)) {
            $g.DrawLine($plainPen, $x1, $y1, $x2, $y2)
        } else {
            $g.DrawLine($pen, $x1, $y1, $x2, $y2)
        }
    }
    if ($label.Length -gt 0) {
        $bg = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(248, 250, 252))
        $g.FillRectangle($bg, $lx, $ly, 220, 44)
        Draw-Label $g $label $lx $ly 220 44 13 $false
        $bg.Dispose()
    }
    $pen.Dispose(); $plainPen.Dispose(); $cap.Dispose()
}

function Save-Png($bmp, $g, [string]$name) {
    $path = Join-Path $outDir $name
    $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose()
    $bmp.Dispose()
    Write-Host "wrote $path"
}

function Draw-Architecture {
    $pair = New-Canvas 1800 980
    $bmp = $pair[0]; $g = $pair[1]
    Draw-Label $g "Portal Turret System Architecture" 0 22 1800 44 26 $true
    $piFill = [System.Drawing.Color]::FromArgb(229, 244, 250)
    $piBorder = [System.Drawing.Color]::FromArgb(44, 126, 160)
    $mcuFill = [System.Drawing.Color]::FromArgb(236, 243, 232)
    $mcuBorder = [System.Drawing.Color]::FromArgb(86, 137, 76)
    $actFill = [System.Drawing.Color]::FromArgb(252, 244, 226)
    $actBorder = [System.Drawing.Color]::FromArgb(176, 127, 40)
    $audFill = [System.Drawing.Color]::FromArgb(246, 235, 245)
    $audBorder = [System.Drawing.Color]::FromArgb(142, 92, 145)

    Draw-Box $g 80 110 520 700 "Raspberry Pi 5" @(
        "CSI Camera: picamera2 640x480",
        "YOLO11n ONNX person detector",
        "State machine: main.py",
        "Controller: pixel -> degrees",
        "SerialLink: 30 Hz max",
        "SoundPlayer: HTTP phone audio"
    ) $piFill $piBorder

    Draw-Box $g 730 110 520 700 "Arduino Uno R4" @(
        "USB serial parser: 115200 baud",
        "Clamp safe servo limits",
        "Slew limiter: 3 deg / 15 ms",
        "Failsafe: 500 ms",
        "4x Servo PWM",
        "Laser GPIO and barrel LEDs"
    ) $mcuFill $mcuBorder

    Draw-Box $g 1390 140 310 135 "Pan Servo" @("MG996R", "pin 9") $actFill $actBorder
    Draw-Box $g 1390 310 310 135 "Tilt Servo" @("MG996R", "pin 10") $actFill $actBorder
    Draw-Box $g 1390 480 310 135 "Eye Servos" @("2x SG90 class", "pins 5, 6") $actFill $actBorder
    Draw-Box $g 1390 650 310 135 "Laser + LEDs" @("laser pin 7", "LED pins 2,3,12,13") $actFill $actBorder
    Draw-Box $g 210 835 410 95 "Phone Speakers" @("WiFi HTTP :8765", "Portal WAV playback") $audFill $audBorder

    Draw-Arrow $g 600 420 730 420 "USB UART`nT,pan,tilt,eyeX,eyeY,laser"
    Draw-Arrow $g 1250 205 1390 205 "PWM"
    Draw-Arrow $g 1250 375 1390 375 "PWM"
    Draw-Arrow $g 1250 545 1390 545 "PWM"
    Draw-Arrow $g 1250 715 1390 715 "GPIO"
    Draw-Arrow $g 420 810 420 835 "HTTP audio"
    Draw-Label $g "Pi performs perception and behavior; Arduino enforces actuation timing and local safety." 650 845 690 55 16 $false
    Save-Png $bmp $g "fig_architecture.png"
}

function Draw-Fsm {
    $pair = New-Canvas 1500 980
    $bmp = $pair[0]; $g = $pair[1]
    Draw-Label $g "Turret State Machine" 0 28 1500 46 27 $true
    $fill = [System.Drawing.Color]::FromArgb(232, 241, 248)
    $border = [System.Drawing.Color]::FromArgb(53, 101, 146)
    $noteFill = [System.Drawing.Color]::FromArgb(252, 244, 226)
    $noteBorder = [System.Drawing.Color]::FromArgb(176, 127, 40)

    Draw-Box $g 130 180 310 145 "SEARCHING" @("No target", "center or idle scan") $fill $border
    Draw-Box $g 610 180 310 145 "TARGET_ACQUIRED" @("person detected", "wait found_ms = 1000 ms") $fill $border
    Draw-Box $g 610 600 310 145 "TRACKING" @("continuous aim", "fire rule enabled") $fill $border
    Draw-Box $g 1080 600 310 145 "TARGET_LOST" @("target disappeared", "wait lost_ms = 1000 ms") $fill $border

    Draw-Arrow $g 440 285 610 285
    Draw-Label $g "person seen" 470 292 120 34 13 $false
    Draw-Arrow $g 610 220 440 220
    Draw-Label $g "lost before found_ms" 440 178 170 34 13 $false
    Draw-Arrow $g 765 325 765 600
    Draw-Label $g "stable target`n>= found_ms" 655 440 220 48 13 $false
    Draw-Arrow $g 920 705 1080 705
    Draw-Label $g "lost" 985 712 80 30 13 $false
    Draw-Arrow $g 1080 635 920 635
    Draw-Label $g "person seen`nreacquire" 935 585 150 52 13 $false
    Draw-PolylineArrow $g @(1235,745,1235,860,285,860,285,325) "lost >= lost_ms" 790 830

    Draw-Box $g 120 610 330 160 "Fire side effect" @(
        "TRACKING only",
        "bbox area >= 0.40",
        "lock sound + F command",
        "cooldown = 4000 ms"
    ) $noteFill $noteBorder
    Draw-Arrow $g 610 682 450 682 "close target"
    Save-Png $bmp $g "fig_fsm.png"
}

function Draw-Serial {
    $pair = New-Canvas 1700 1000
    $bmp = $pair[0]; $g = $pair[1]
    Draw-Label $g "Serial Packet Timeline and Firmware Safety" 0 26 1700 46 27 $true
    $linePen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(80, 92, 110), 3)
    $dashPen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(160, 170, 180), 2)
    $dashPen.DashStyle = [System.Drawing.Drawing2D.DashStyle]::Dash
    $xs = @(260, 850, 1440)
    $names = @("Raspberry Pi", "USB CDC Serial", "Arduino Uno R4")
    for ($i = 0; $i -lt 3; $i++) {
        Draw-Label $g $names[$i] ($xs[$i] - 150) 110 300 42 19 $true
        $g.DrawLine($dashPen, $xs[$i], 160, $xs[$i], 830)
    }

    Draw-Arrow $g 260 230 850 230 "T,90,88,95,35,1\n"
    Draw-Arrow $g 850 300 1440 300 "line delivered"
    Draw-Box $g 1240 342 400 100 "Parse and clamp" @("safe servo ranges", "ignore invalid fields") ([System.Drawing.Color]::FromArgb(236, 243, 232)) ([System.Drawing.Color]::FromArgb(86, 137, 76))
    Draw-Arrow $g 1440 470 850 470 "OK\n"
    Draw-Arrow $g 850 540 260 540 "ack flushed`nnon-blocking"
    Draw-Box $g 1230 585 420 105 "Every 15 ms" @("slew current angles", "toward parsed targets") ([System.Drawing.Color]::FromArgb(232, 241, 248)) ([System.Drawing.Color]::FromArgb(53, 101, 146))
    Draw-Arrow $g 260 735 1440 735 "F\n or L,1\n auxiliary command"
    Draw-Box $g 80 805 470 115 "Host limit" @("commands capped at 30 Hz", "reconnect retry = 2 s") ([System.Drawing.Color]::FromArgb(246, 235, 245)) ([System.Drawing.Color]::FromArgb(142, 92, 145))
    Draw-Box $g 1160 805 470 115 "Firmware failsafe" @("no valid command for 500 ms", "center servos + laser off") ([System.Drawing.Color]::FromArgb(252, 244, 226)) ([System.Drawing.Color]::FromArgb(176, 127, 40))
    $linePen.Dispose(); $dashPen.Dispose()
    Save-Png $bmp $g "fig_serial.png"
}

Draw-Architecture
Draw-Fsm
Draw-Serial
