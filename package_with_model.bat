@echo off

echo ---------------
echo Building backend executable
pyinstaller back2/server.py --clean --noconfirm --onefile --distpath ./backend --collect-all easyocr --collect-all torch --collect-all torchvision --collect-all docling --collect-all docling_core --collect-all docling_parse --collect-all docling_ibm_models --collect-all pymupdf --collect-all tokenizers --add-data "back2/tokenizer.json;back2" --add-data "back2/config.json;back2"

echo ---------------
echo Copying model files...
xcopy "model" "backend\model" /E /I /Y
echo ---------------

cd front
echo ---------------
npx electron-forge package --platform=win32 --arch=x64
echo ---------------
cd ..

echo Copying backend files...
xcopy "backend" "front\out\EasyForm-win32-x64\backend" /E /I /Y
echo ---------------
echo Package MSIX
echo Copying logo and AppxManifest.xml

echo ---------------
xcopy "logo.jpg" "front\out\EasyForm-win32-x64\" /Y /R /Q
xcopy "AppxManifest.xml" "front\out\EasyForm-win32-x64\" /Y /R /Q

echo ---------------
MakeAppx.exe pack /overwrite /d .\front\out\EasyForm-win32-x64 /p EasyForm.msix

echo ---------------
echo Build complete!

