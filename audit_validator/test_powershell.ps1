# Test PowerShell script for UI collection
Write-Host "Testing UI collection commands..."

try {
    # Test basic commands
    Write-Host "1. Testing Get-WinUserLanguageList..."
    $langList = Get-WinUserLanguageList -ErrorAction SilentlyContinue
    Write-Host "Result: $langList"
    
    Write-Host "2. Testing Get-WinSystemLocale..."
    $systemLocale = Get-WinSystemLocale -ErrorAction SilentlyContinue
    Write-Host "Result: $systemLocale"
    
    Write-Host "3. Testing CurrentUICulture..."
    $currentUICulture = [System.Globalization.CultureInfo]::CurrentUICulture
    Write-Host "Result: $currentUICulture"
    
    Write-Host "4. Testing CurrentCulture..."
    $currentCulture = [System.Globalization.CultureInfo]::CurrentCulture
    Write-Host "Result: $currentCulture"
    
    Write-Host "5. Testing keyboard layout..."
    $kl = (Get-ItemProperty -Path 'HKCU:\Keyboard Layout\Preload' -ErrorAction SilentlyContinue)."1"
    Write-Host "Result: $kl"
    
    Write-Host "6. Testing displays..."
    $screens = [System.Windows.Forms.Screen]::AllScreens
    Write-Host "Result: $screens"
    
} catch {
    Write-Host "Error: $_"
}
