import os
import subprocess
import sys
import zipfile
import urllib.request
import shutil
from pathlib import Path

def check_python_version():
    print("Checking Python version...")
    if sys.version_info < (3, 6):
        print("Error: Python 3.6 or higher is required")
        return False
    print(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} detected - OK")
    return True

def install_pip_requirements():
    print("Installing Python dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        # Install UI package
        subprocess.run([sys.executable, "-m", "pip", "install", "customtkinter"], check=True)
        print("Python dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("Error installing Python dependencies")
        return False

def update_ytdlp():
    print("Updating yt-dlp to the latest version...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"], check=True)
        print("yt-dlp updated successfully")
        return True
    except subprocess.CalledProcessError:
        print("Error updating yt-dlp")
        return False

def check_ffmpeg():
    print("Checking for ffmpeg...")
    try:
        # Check if ffmpeg is installed
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=True)
        print("ffmpeg is installed. Checking codec support...")
        
        # Check if it supports libvpx
        support_check = subprocess.run(
            ["ffmpeg", "-hide_banner", "-codecs"], 
            capture_output=True, 
            text=True
        )
        
        if "libvpx" in support_check.stdout:
            print("ffmpeg supports libvpx codec - OK")
            return True
        else:
            print("ffmpeg is installed but doesn't support libvpx codec")
            return False
            
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ffmpeg not found")
        return False

def download_and_install_ffmpeg():
    print("Downloading ffmpeg for Windows...")
    
    # Updated to a reliable source with libvpx support
    ffmpeg_url = "https://github.com/GyanD/codexffmpeg/releases/download/6.1.1/ffmpeg-6.1.1-essentials_build.zip"
    zip_path = "ffmpeg.zip"
    extract_path = "ffmpeg-temp"
    
    # Create the bin directory if it doesn't exist
    bin_dir = Path(os.getcwd()) / "bin"
    bin_dir.mkdir(exist_ok=True)
    
    try:
        # Download the file
        print(f"Downloading from {ffmpeg_url}...")
        urllib.request.urlretrieve(ffmpeg_url, zip_path)
        
        # Extract the zip file
        print("Extracting zip file...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        
        # Find the ffmpeg executables inside the extracted folder
        print("Installing ffmpeg...")
        # Navigate through subdirectories to find bin folder
        for root, dirs, files in os.walk(extract_path):
            for dir_name in dirs:
                if dir_name.lower() == "bin":
                    bin_dir_source = Path(root) / dir_name
                    break
        
        if 'bin_dir_source' not in locals() or not bin_dir_source.exists():
            # Try to find executables directly
            ffmpeg_exes = []
            for root, dirs, files in os.walk(extract_path):
                for file in files:
                    if file.lower() == "ffmpeg.exe" or file.lower() == "ffprobe.exe":
                        ffmpeg_exes.append(Path(root) / file)
            
            if ffmpeg_exes:
                bin_dir_source = ffmpeg_exes[0].parent
            else:
                raise FileNotFoundError("Could not find ffmpeg executables in the extracted files")
        
        # Copy the ffmpeg and ffprobe executables to bin directory
        for exe_file in ["ffmpeg.exe", "ffprobe.exe"]:
            source_file = bin_dir_source / exe_file
            if source_file.exists():
                target_file = bin_dir / exe_file
                shutil.copy2(source_file, target_file)
                print(f"Copied {exe_file} to {bin_dir}")
            else:
                print(f"Warning: {exe_file} not found in extracted files")
        
        print(f"ffmpeg installed successfully in {bin_dir}")
        
        # Test the installed ffmpeg for libvpx support
        print("Testing ffmpeg libvpx support...")
        ffmpeg_path = bin_dir / "ffmpeg.exe"
        support_check = subprocess.run(
            [str(ffmpeg_path), "-hide_banner", "-codecs"], 
            capture_output=True, 
            text=True
        )
        
        if "libvpx" in support_check.stdout:
            print("Installed ffmpeg supports libvpx codec - OK")
        else:
            print("Warning: Installed ffmpeg doesn't appear to support libvpx codec")
            print("The application may need to use alternative conversion methods")
        
        # Clean up
        os.remove(zip_path)
        shutil.rmtree(extract_path)
        
        # Verify installation
        if not (bin_dir / "ffmpeg.exe").exists():
            raise FileNotFoundError("ffmpeg.exe was not properly installed")
        
        return True
    except Exception as e:
        print(f"Error installing ffmpeg: {e}")
        # Clean up any partial downloads/extractions
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(extract_path):
            shutil.rmtree(extract_path)
        return False

def update_batch_file():
    print("Updating batch file to include local ffmpeg...")
    batch_content = """@echo off
set PATH=%~dp0bin;%PATH%
echo Starting Clone Hero Video Downloader...
python main.py
pause
"""
    with open("run_downloader.bat", "w") as f:
        f.write(batch_content)
    print("Batch file updated")

def main():
    print("=== Clone Hero Video Downloader Setup ===")
    
    if not check_python_version():
        input("Press Enter to exit...")
        return
    
    if not install_pip_requirements():
        input("Press Enter to exit...")
        return
    
    # Update yt-dlp to the latest version
    print("Checking for yt-dlp updates...")
    update_ytdlp()
    
    if not check_ffmpeg():
        print("ffmpeg needs to be installed")
        choice = input("Do you want to download and install ffmpeg locally? (y/n): ").lower()
        
        if choice == 'y':
            if download_and_install_ffmpeg():
                update_batch_file()
            else:
                print("Failed to install ffmpeg. Please install it manually.")
                print("Download from: https://ffmpeg.org/download.html")
                input("Press Enter to exit...")
                return
        else:
            print("Please install ffmpeg manually and add it to your PATH.")
            print("Download from: https://ffmpeg.org/download.html")
            input("Press Enter to exit...")
            return
    
    print("\nSetup completed successfully!")
    print("You can now run the application using run_downloader.bat")
    input("Press Enter to exit...")

if __name__ == "__main__":
    main() 