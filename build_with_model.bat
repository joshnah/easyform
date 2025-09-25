@echo off

echo ---------------
echo Building backend executable
pyinstaller back/server.py --clean --noconfirm --onefile --distpath ./backend --collect-all easyocr --collect-all torch --collect-all torchvision --collect-all docling --collect-all docling_core --collect-all docling_parse --collect-all docling_ibm_models

echo ---------------
echo Copying model files...
xcopy "model" "backend\model" /E /I /Y
echo ---------------
echo Package electron app in out/EasyForm-win32-arm64 (can vary based on your system architecture)

cd front
echo ---------------
npm run package
echo ---------------
cd ..

echo Copying backend files...
xcopy "backend" "front\out\EasyForm-win32-arm64\backend" /E /I /Y
echo ---------------
echo Package MSIX
echo Copying logo and AppxManifest.xml

echo ---------------
xcopy "logo.jpg" "front\out\EasyForm-win32-arm64"  
xcopy "AppxManifest.xml" "front\out\EasyForm-win32-arm64"

echo ---------------
MakeAppx.exe pack /overwrite /d .\front\out\EasyForm-win32-arm64 /p EasyForm.msix

echo ---------------
echo Build complete!

