$globalStartTime = Get-Date
Write-Host "Start compression: $globalStartTime" -ForegroundColor Cyan
Write-Host "--------------------------------------------------"

$pt_combinations = @(
    @{P=1; T=24}, @{P=2; T=12}, @{P=3; T=8}, @{P=4; T=6},
    @{P=6; T=4},  @{P=8; T=3},  @{P=12; T=2}, @{P=24; T=1}
)

$bc_codecs = @("bc1", "bc3", "bc7")
Write-Host "`n[TEST] BC formats starting..." -ForegroundColor Green

foreach ($codec in $bc_codecs) {
    foreach ($pt in $pt_combinations) {
        $p = $pt.P
        $t = $pt.T
        $out_folder = "${codec}_output_P${p}_T${t}"
        
        Write-Host "Running $codec | Process: $p | Thread: $t" -ForegroundColor DarkGray
        python tool.py --codec $codec --nProcesses $p --nThreads $t --data_path dataset --output_path $out_folder
        if (Test-Path $out_folder) 
        {
            Remove-Item -Path $out_folder -Recurse -Force
        }   
    }
}

Write-Host "`n[TEST] ETC formats starting..." -ForegroundColor Green

foreach ($pt in $pt_combinations) {
    $p = $pt.P
    $t = $pt.T
    $out_folder = "etc1_output_P${p}_T${t}"
    
    Write-Host "Running etc1 | Process: $p | Thread: $t" -ForegroundColor DarkGray
    python tool.py --codec etc1 --nProcesses $p --nThreads $t --data_path dataset --output_path $out_folder
    if (Test-Path $out_folder) 
    {
        Remove-Item -Path $out_folder -Recurse -Force
    }
}

$etc2_codecs = @("etc2")
foreach ($codec in $etc2_codecs) {
    
    foreach ($pt in $pt_combinations) {
        $p = $pt.P
        $t = $pt.T
        $out_folder = "${codec}_output_P${p}_T${t}"
        
        Write-Host "Running $codec (Standard) | Process: $p | Thread: $t" -ForegroundColor DarkGray
        python tool.py --codec $codec --nProcesses $p --nThreads $t --data_path dataset --output_path $out_folder
        if (Test-Path $out_folder) 
        {
            Remove-Item -Path $out_folder -Recurse -Force
        }
    }
    
    foreach ($pt in $pt_combinations) {
        $p = $pt.P
        $t = $pt.T
        $out_folder = "${codec}_hq_output_P${p}_T${t}" # hq 폴더명 분리
        
        Write-Host "Running $codec (HQ) | Process: $p | Thread: $t" -ForegroundColor Yellow
        python tool.py --codec $codec --etc2_hq --nProcesses $p --nThreads $t --data_path dataset --output_path $out_folder
        if (Test-Path $out_folder) 
        {
            Remove-Item -Path $out_folder -Recurse -Force
        }
    }
}

Write-Host "`n[TEST] ASTC format starting..." -ForegroundColor Green

$astc_qualities = @("fastest", "fast", "medium", "thorough", "verythorough", "exhaustive")
# $astc_qualities = @("fastest", "fast", "medium")
$astc_blocks = @("4x4", "5x4", "5x5", "6x5", "6x6", "8x5", "8x6", "3x3x3", "4x3x3", "4x4x3", "4x4x4", "5x4x4")

foreach ($q in $astc_qualities) {
    foreach ($b in $astc_blocks) {
        foreach ($pt in $pt_combinations) {
            $p = $pt.P
            $t = $pt.T
            $out_folder = "astc_output_Q$($q)_B$($b)_P$($p)_T$($t)"
            
            Write-Host "Running ASTC | Quality: $q | Block: $b | Process: $p | Thread: $t" -ForegroundColor DarkGray
            python tool.py --codec astc --astc_quality $q --astc_block_size $b --nProcesses $p --nThreads $t --data_path dataset --output_path $out_folder

            if (Test-Path $out_folder) 
            {
                Remove-Item -Path $out_folder -Recurse -Force
            }
        }
    }
}

$globalEndTime = Get-Date
$elapsedTime = $globalEndTime - $globalStartTime

Write-Host "`n--------------------------------------------------"
Write-Host "Done!" -ForegroundColor Magenta
Write-Host "End Time: $globalEndTime"
Write-Host "Total comrpession time: $($elapsedTime.Hours) H $($elapsedTime.Minutes) M $($elapsedTime.Seconds) S" -ForegroundColor Green