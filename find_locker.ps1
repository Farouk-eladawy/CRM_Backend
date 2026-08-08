$file = "C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\.git\index.lock"
Write-Host "Looking for processes locking: $file"
$procs = Get-Process | Where-Object { $_.ProcessName -match 'git|python|code|notepad|explorer' }
foreach ($p in $procs) {
    try {
        $modules = $p.Modules
        foreach ($m in $modules) {
            if ($m.FileName -like "*index*") {
                Write-Host "PID $($p.Id) : $($p.ProcessName) - $($m.FileName)"
            }
        }
    } catch {}
}
# Check using handle tool if available
if (Get-Command handle.exe -ErrorAction SilentlyContinue) {
    handle.exe -accepteula -a "$file"
}
Write-Host "Done"
