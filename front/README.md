# How to use

## Run in dev mode

```bash
npm install
npm start
```

## Package + run the app in production

```bash
npm run package
# Start for MacOS (hot take : I don't like other OS :)))
open ./out/EasyForm-darwin-arm64/EasyForm.app
```

## Build python script
```bash
cd src/scripts
chmod +x build.sh
./build.sh # this will take all python files in src/scripts and compile them
# The built binaries will reside in assets/python
```
