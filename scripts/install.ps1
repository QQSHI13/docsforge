# Usage: irm https://is.gd/docsforge_vsix_ps1 | iex
$r = Invoke-RestMethod https://api.github.com/repos/QQSHI13/docsforge/releases/latest
$u = $r.assets | Where-Object { $_.name -like "*.vsix" } | Select-Object -First 1
if ($u) { Invoke-WebRequest $u.browser_download_url -OutFile "$env:TEMP\docsforge.vsix"; code.cmd --install-extension "$env:TEMP\docsforge.vsix" --force; Remove-Item "$env:TEMP\docsforge.vsix"; Write-Host "Installed!" } else { Write-Host "Failed" }
