@echo off
setlocal

echo [INFO] Searching for vcpkg.exe in the system...

:: 1. Find the full path of vcpkg.exe using the 'where' command
for /f "delims=" %%F in ('where vcpkg 2^>nul') do (
    set "VCPKG_EXE_PATH=%%F"
    goto :found_vcpkg
)

:: Error handling if vcpkg is not found
echo [ERROR] Could not find vcpkg.exe. 
echo Please ensure that the vcpkg directory is added to your system PATH environment variable.
pause
exit /b 1

:found_vcpkg
:: 2. Extract the directory path from the executable path (includes trailing \)
for %%D in ("%VCPKG_EXE_PATH%") do set "VCPKG_ROOT_DIR=%%~dpD"

:: 3. Construct the toolchain file path
set "VCPKG_TOOLCHAIN_FILE_PATH=%VCPKG_ROOT_DIR%scripts\buildsystems\vcpkg.cmake"

echo [INFO] Found vcpkg root at: %VCPKG_ROOT_DIR%
echo [INFO] Applying toolchain file: %VCPKG_TOOLCHAIN_FILE_PATH%

:: 4. Verify if the toolchain file actually exists
if not exist "%VCPKG_TOOLCHAIN_FILE_PATH%" (
    echo [ERROR] Toolchain file not found at: %VCPKG_TOOLCHAIN_FILE_PATH%
    pause
    exit /b 1
)

:: 5. Navigate to the etcpak directory and run CMake
cd vender\etcpak
echo [INFO] Starting CMake configuration...
cmake . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_TOOLCHAIN_FILE="%VCPKG_TOOLCHAIN_FILE_PATH%"
echo [INFO] Configuration completed successfully!

echo [INFO] Start build of etcpak 2.0...
cmake --build build --config Release
echo [INFO] Build of etcpak 2.0 completed successfully!

cd ../../
if not exist "encoders\etcpak" mkdir "encoders\etcpak"
xcopy /E /Y /I "vender\etcpak\build\Release" "encoders\etcpak"

if not exist "encoders\astcenc" mkdir "encoders\astcenc"

cd vender/astc-encoder
cmake . -B build -DCMAKE_BUILD_TYPE=Release
echo [INFO] Configuration completed successfully!
echo [INFO] Start build of astcenc...
cmake --build build --config Release
echo [INFO] Build of astcenc completed successfully!

endlocal
pause