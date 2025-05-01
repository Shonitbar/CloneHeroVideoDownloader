# Clone Hero Video Background Downloader

A Windows desktop application that automatically downloads background videos for Clone Hero songs from YouTube and converts them to the required `.webm` format with VP8 codec.

![Clone Hero Video Downloader](https://raw.githubusercontent.com/wiki/DragonForce/CloneHeroVideoDownloader/screenshot.png)

## Features

- Modern UI with light/dark theme support
- Select your Clone Hero Songs folder
- Auto-detects song folders without video.webm files
- Searches YouTube for each song using the folder name
- Shows top 3 video results for each song with option to choose
- Allows custom YouTube URL input for full control
- Downloads the video and converts to WebM format with VP8 codec (required by Clone Hero)
- Option to select video quality (360p, 480p, 720p, 1080p)
- Auto-fetch mode to automatically select the first result
- Skip or overwrite existing videos, with "Skip All" option
- No console windows appear during execution

## Requirements

- Windows
- Python 3.6 or higher (for running from source)
- yt-dlp (for YouTube downloads)
- ffmpeg (for video conversion)
- customtkinter (for modern UI)

## Quick Installation

For an easy setup, simply run the included setup script:

1. Download or clone this repository
2. Double-click `setup.bat` to run the setup script
3. The script will:
   - Check your Python version
   - Install required Python packages
   - Download and install ffmpeg locally if needed
   - Prepare the run_downloader.bat file

After setup completes, you can run the application using `run_downloader.bat`.

## Using the Standalone Executable (No Python Required)

For users without Python installed:

1. Download the latest release from the [Releases](https://github.com/yourusername/CloneHeroVideoDownloader/releases) page
2. Extract the ZIP file
3. Run `CloneHeroVideoDownloader.exe`

The executable is completely standalone and includes all necessary dependencies including ffmpeg - no external software needed.

## Building the Standalone Executable

To build the standalone executable yourself:

1. Make sure you have Python installed
2. Run `build_standalone.bat`
3. The script will:
   - Download and embed ffmpeg
   - Install necessary dependencies
   - Build a standalone executable with PyInstaller
   - The executable will be placed in the `dist` folder

## Manual Installation

If you prefer to install dependencies manually:

1. Install Python from [python.org](https://www.python.org/downloads/) if you don't have it
2. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```
3. Install ffmpeg:
   - Download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - Extract the files
   - Add the bin directory to your system PATH

## Usage

1. Run the application
2. Click "Browse Folder" and select your Clone Hero Songs folder
3. Choose your preferred video quality
4. Enable "Auto-fetch Mode" if you want to automatically use the first result
5. Click "Start Processing"
6. The app will:
   - Check each song folder for an existing video.webm file
   - If no video exists, search YouTube, download, and convert
   - If a video already exists, ask if you want to skip or overwrite
7. Monitor progress in the log window

## Notes

- The app uses the song folder name as the YouTube search query
- Downloaded videos are automatically converted to WebM with VP8 codec
- Temporary files are cleaned up after processing
- The standalone executable hides all console windows for a cleaner experience

## Troubleshooting

- If you get a "Missing dependencies" message, run the setup.bat file again
- Make sure ffmpeg is properly installed for video conversion
- Check the log for detailed error messages

## License

Released under MIT License. See LICENSE file for details. 