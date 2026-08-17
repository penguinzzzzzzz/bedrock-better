name: Build Android APK

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build with Buildozer
        uses: Artemis-ce/buildozer-action@v1
        with:
          command: buildozer android debug
          subfolder: .
      - name: Upload APK
        uses: actions/upload-artifact@v3
        with:
          name: bedrock-better-apk
          path: bin/*.apk