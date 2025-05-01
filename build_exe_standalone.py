import PyInstaller.__main__
import os
import shutil
import zipfile
import urllib.request
import subprocess
import sys

print("Building standalone Clone Hero Video Downloader...")

# Check if we need to download ffmpeg
bin_dir = os.path.join(os.getcwd(), "bin")
os.makedirs(bin_dir, exist_ok=True)
ffmpeg_exe = os.path.join(bin_dir, "ffmpeg.exe")
ffprobe_exe = os.path.join(bin_dir, "ffprobe.exe")

# Download ffmpeg if needed
if not (os.path.exists(ffmpeg_exe) and os.path.exists(ffprobe_exe)):
    print("Downloading ffmpeg (this may take a while)...")
    ffmpeg_url = "https://github.com/GyanD/codexffmpeg/releases/download/6.1.1/ffmpeg-6.1.1-essentials_build.zip"
    zip_path = os.path.join(os.getcwd(), "ffmpeg.zip")
    extract_path = os.path.join(os.getcwd(), "ffmpeg-temp")
    
    # Download the file
    urllib.request.urlretrieve(ffmpeg_url, zip_path)
    
    # Extract the zip file
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)
    
    # Find the ffmpeg executables inside the extracted folder
    for root, dirs, files in os.walk(extract_path):
        for dir_name in dirs:
            if dir_name.lower() == "bin":
                bin_dir_source = os.path.join(root, dir_name)
                
                # Copy the ffmpeg and ffprobe executables to bin directory
                for exe_file in ["ffmpeg.exe", "ffprobe.exe"]:
                    source_file = os.path.join(bin_dir_source, exe_file)
                    if os.path.exists(source_file):
                        shutil.copy2(source_file, os.path.join(bin_dir, exe_file))
                break

    # Clean up
    if os.path.exists(zip_path):
        os.remove(zip_path)
    if os.path.exists(extract_path):
        shutil.rmtree(extract_path)
    
    print("ffmpeg downloaded and installed.")

# Create a file that will check for and use the bundled ffmpeg
with open("bundled_ffmpeg.py", "w") as f:
    f.write("""
import os
import sys

def get_ffmpeg_path():
    \"\"\"Return the path to the ffmpeg executable\"\"\"
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        ffmpeg_exe = os.path.join(bundle_dir, "ffmpeg.exe")
        return ffmpeg_exe
    else:
        # Running in development environment
        bin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")
        ffmpeg_exe = os.path.join(bin_dir, "ffmpeg.exe")
        if os.path.exists(ffmpeg_exe):
            return ffmpeg_exe
        return "ffmpeg"

def get_ffprobe_path():
    \"\"\"Return the path to the ffprobe executable\"\"\"
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        ffprobe_exe = os.path.join(bundle_dir, "ffprobe.exe")
        return ffprobe_exe
    else:
        # Running in development environment
        bin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")
        ffprobe_exe = os.path.join(bin_dir, "ffprobe.exe")
        if os.path.exists(ffprobe_exe):
            return ffprobe_exe
        return "ffprobe"
""")

# Modify main.py to use the bundled_ffmpeg.py
# First, read the main.py file
with open("main.py", "r") as f:
    main_content = f.read()

# Create a temporary modified version for building
with open("main_temp.py", "w") as f:
    # Add import for bundled_ffmpeg at the top after other imports
    import_section_end = main_content.find("# Set customtkinter appearance")
    f.write(main_content[:import_section_end])
    f.write("import bundled_ffmpeg\n\n")
    f.write(main_content[import_section_end:])

# Install PyInstaller if needed
try:
    import PyInstaller
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

# Install yt-dlp if needed
try:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
except:
    print("Warning: Could not install yt-dlp. The executable may not work correctly.")

# Install customtkinter if needed
try:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "customtkinter"])
except:
    print("Warning: Could not install customtkinter. The executable may not work correctly.")

# Command line arguments for PyInstaller
pyinstaller_args = [
    '--name=CloneHeroVideoDownloader',
    '--onefile',
    '--noconsole',
    '--icon=icon.ico',
    '--add-data=icon.ico;.',
    # Add ffmpeg and ffprobe as binary data
    f'--add-binary={os.path.join(bin_dir, "ffmpeg.exe")};.',
    f'--add-binary={os.path.join(bin_dir, "ffprobe.exe")};.',
    # Add hidden imports for customtkinter
    '--hidden-import=customtkinter',
    '--hidden-import=PIL',
    '--hidden-import=darkdetect',
    '--hidden-import=yt_dlp',
    # Exclude unnecessary packages to reduce size
    '--exclude-module=matplotlib',
    '--exclude-module=numpy',
    '--exclude-module=pandas',
    '--exclude-module=scipy',
    # Main script (use our temporary version)
    'main_temp.py'
]

# Run PyInstaller with the arguments
PyInstaller.__main__.run(pyinstaller_args)

# Clean up temporary files
if os.path.exists("main_temp.py"):
    os.remove("main_temp.py")
if os.path.exists("bundled_ffmpeg.py"):
    os.remove("bundled_ffmpeg.py")

print("Build complete! The standalone executable is located at:")
print(os.path.join(os.getcwd(), "dist", "CloneHeroVideoDownloader.exe")) 