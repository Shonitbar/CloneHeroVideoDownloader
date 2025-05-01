import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import re
import time
import shutil
import customtkinter as ctk
import sys

# Add Windows-specific imports for hiding console windows
if sys.platform == 'win32':
    import ctypes
    from subprocess import STARTUPINFO, STARTF_USESHOWWINDOW, SW_HIDE

# Function to create a subprocess with hidden console window
def create_hidden_process(cmd, **kwargs):
    """Create a subprocess with hidden console window on Windows"""
    if sys.platform == 'win32':
        startupinfo = STARTUPINFO()
        startupinfo.dwFlags |= STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = SW_HIDE
        
        # Add startupinfo to kwargs
        kwargs['startupinfo'] = startupinfo
        
        # Make sure we're not trying to show any window
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    
    return subprocess.Popen(cmd, **kwargs)

# Set customtkinter appearance
ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class CloneHeroVideoDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Clone Hero Video Downloader")
        self.root.geometry("800x600")
        self.root.minsize(650, 500)
        
        self.songs_folder = ""
        self.video_quality = "720"
        self.song_folders = []
        self.current_song_index = 0
        self.processing = False
        self.skip_all_existing = False  # Flag to skip all existing videos
        self.dialog_active = False  # Flag to track if a dialog is currently open
        self.auto_fetch = False  # Flag for auto-fetch mode
        self.skip_conversion = False  # Flag to skip current conversion
        
        # Create a flag for ffmpeg path
        self.ffmpeg_path = "ffmpeg"  # default to system path
        
        # Check if we have ffmpeg in the local bin directory or bundled (for frozen executable)
        try:
            if 'bundled_ffmpeg' in sys.modules:
                # Use bundled ffmpeg if available (when running as executable)
                self.ffmpeg_path = sys.modules['bundled_ffmpeg'].get_ffmpeg_path()
            else:
                # Use local ffmpeg if available (when running from source)
                local_ffmpeg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", "ffmpeg.exe")
                if os.path.exists(local_ffmpeg):
                    self.ffmpeg_path = local_ffmpeg
        except Exception as e:
            print(f"Warning: Could not set ffmpeg path: {e}")
        
        self.setup_ui()
        
    def setup_ui(self):
        # Configure grid layout (4x4)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Create sidebar frame with widgets
        self.sidebar_frame = ctk.CTkFrame(self.root, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        
        # App logo/title
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Clone Hero\nVideo Downloader", 
                                      font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Browse button in sidebar
        self.browse_button = ctk.CTkButton(self.sidebar_frame, text="Browse Folder", 
                                         command=self.select_folder)
        self.browse_button.grid(row=1, column=0, padx=20, pady=10)
        
        # Quality selection in sidebar
        self.quality_label = ctk.CTkLabel(self.sidebar_frame, text="Video Quality:")
        self.quality_label.grid(row=2, column=0, padx=20, pady=(10, 0))
        
        self.quality_combobox = ctk.CTkComboBox(self.sidebar_frame, values=["360p", "480p", "720p", "1080p"])
        self.quality_combobox.grid(row=3, column=0, padx=20, pady=(5, 10))
        self.quality_combobox.set("720p")  # default value
        
        # Auto-fetch checkbox
        self.auto_fetch_var = ctk.BooleanVar(value=False)
        self.auto_fetch_cb = ctk.CTkCheckBox(self.sidebar_frame, text="Auto-fetch Mode", 
                                           variable=self.auto_fetch_var,
                                           command=self.toggle_auto_fetch,
                                           onvalue=True, offvalue=False)
        self.auto_fetch_cb.grid(row=4, column=0, padx=20, pady=10, sticky="n")
        
        # Appearance mode switcher
        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Appearance Mode:")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        
        self.appearance_mode_menu = ctk.CTkOptionMenu(self.sidebar_frame, 
                                                 values=["System", "Light", "Dark"],
                                                 command=self.change_appearance_mode)
        self.appearance_mode_menu.grid(row=6, column=0, padx=20, pady=(5, 10))
        
        # Create main frame
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.grid(row=0, column=1, rowspan=3, padx=(20, 20), pady=(20, 0), sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        
        # Selected folder display
        self.folder_frame = ctk.CTkFrame(self.main_frame)
        self.folder_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.folder_frame.grid_columnconfigure(0, weight=1)
        
        self.folder_path_var = tk.StringVar()
        self.folder_label = ctk.CTkLabel(self.folder_frame, text="Selected Songs Folder:")
        self.folder_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.folder_path_entry = ctk.CTkEntry(self.folder_frame, textvariable=self.folder_path_var, width=400)
        self.folder_path_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        
        # Log display
        self.log_frame = ctk.CTkFrame(self.main_frame)
        self.log_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.log_frame.grid_rowconfigure(0, weight=1)
        self.log_frame.grid_columnconfigure(0, weight=1)
        
        self.log_text = ctk.CTkTextbox(self.log_frame, height=300, width=600, font=("Consolas", 12))
        self.log_text.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Progress frame and bar
        self.progress_frame = ctk.CTkFrame(self.main_frame)
        self.progress_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        self.progress_frame.grid_columnconfigure(1, weight=1)
        
        self.progress_label = ctk.CTkLabel(self.progress_frame, text="Overall Progress:")
        self.progress_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        self.progress_bar.set(0)
        
        # Control buttons
        self.controls_frame = ctk.CTkFrame(self.root)
        self.controls_frame.grid(row=3, column=1, padx=20, pady=20, sticky="ew")
        self.controls_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.start_btn = ctk.CTkButton(self.controls_frame, text="Start Processing", 
                                     command=self.start_processing)
        self.start_btn.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        self.stop_btn = ctk.CTkButton(self.controls_frame, text="Stop", 
                                    command=self.stop_processing, 
                                    state="disabled", 
                                    fg_color="gray50", hover_color="gray30")
        self.stop_btn.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        self.skip_btn = ctk.CTkButton(self.controls_frame, text="Skip Current", 
                                    command=self.skip_current_conversion, 
                                    state="disabled", 
                                    fg_color="gray50", hover_color="gray30")
        self.skip_btn.grid(row=0, column=2, padx=10, pady=10, sticky="ew")
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ctk.CTkLabel(self.root, textvariable=self.status_var, corner_radius=8)
        self.status_bar.grid(row=4, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="ew")
        
    def change_appearance_mode(self, new_appearance_mode):
        ctk.set_appearance_mode(new_appearance_mode)
        
    def select_folder(self):
        folder = filedialog.askdirectory(title="Select Clone Hero Songs Folder")
        if folder:
            self.songs_folder = folder
            self.folder_path_var.set(folder)
            self.log(f"Selected folder: {folder}")
    
    def log(self, message, verbose=True):
        """Log a message to the UI log and console"""
        if verbose:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", message + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        print(message)
    
    def update_status(self, message):
        self.status_var.set(message)
        self.root.update_idletasks()
    
    def start_processing(self):
        if not self.songs_folder:
            self.show_error_dialog("Please select the Songs folder first.")
            return
        
        if not os.path.exists(self.songs_folder):
            self.show_error_dialog("Selected folder does not exist.")
            return
        
        # Get selected video quality (strip "p" from the end)
        self.video_quality = self.quality_combobox.get().replace("p", "")
        self.auto_fetch = self.auto_fetch_var.get()
        
        # Reset progress
        self.current_song_index = 0
        self.progress_bar.set(0)
        self.skip_all_existing = False
        self.dialog_active = False
        self.skip_conversion = False
        
        # Get all song folders
        self.song_folders = [f for f in os.listdir(self.songs_folder) 
                            if os.path.isdir(os.path.join(self.songs_folder, f))]
        
        if not self.song_folders:
            self.show_info_dialog("No song folders found in the selected directory.")
            return
        
        # Start processing in a separate thread
        self.processing = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal", fg_color=("#DB3E39", "#821D1A"), hover_color=("#B33731", "#611715"))
        self.skip_btn.configure(state="normal", fg_color=("#1F6AA5", "#144870"), hover_color=("#144870", "#0A2E4A"))
        
        self.log(f"Found {len(self.song_folders)} song folders. Starting processing...")
        self.log(f"Auto-fetch mode: {'Enabled' if self.auto_fetch else 'Disabled'}")
        self.update_status("Processing...")
        
        self.process_thread = threading.Thread(target=self.process_songs)
        self.process_thread.daemon = True
        self.process_thread.start()
    
    def stop_processing(self):
        self.processing = False
        self.update_status("Stopping...")
        self.log("Stopping processing...")
    
    def skip_current_conversion(self):
        self.skip_conversion = True
        self.update_status("Skipping current conversion...")
        self.log("User requested to skip current conversion")
    
    def show_error_dialog(self, message):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Error")
        dialog.geometry("400x150")
        dialog.transient(self.root)
        dialog.lift()
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(0, weight=1)
        
        frame = ctk.CTkFrame(dialog)
        frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        
        label = ctk.CTkLabel(frame, text=message, font=("Helvetica", 14))
        label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        ok_button = ctk.CTkButton(frame, text="OK", command=dialog.destroy)
        ok_button.grid(row=1, column=0, padx=20, pady=10)
        
        dialog.focus_set()
        dialog.grab_set()
        
    def show_info_dialog(self, message):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Information")
        dialog.geometry("400x150")
        dialog.transient(self.root)
        dialog.lift()
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(0, weight=1)
        
        frame = ctk.CTkFrame(dialog)
        frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        
        label = ctk.CTkLabel(frame, text=message, font=("Helvetica", 14))
        label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        ok_button = ctk.CTkButton(frame, text="OK", command=dialog.destroy)
        ok_button.grid(row=1, column=0, padx=20, pady=10)
        
        dialog.focus_set()
        dialog.grab_set()
    
    def process_songs(self):
        total_songs = len(self.song_folders)
        i = 0
        
        while i < total_songs and self.processing:
            song_folder = self.song_folders[i]
            self.current_song_index = i
            song_path = os.path.join(self.songs_folder, song_folder)
            video_file = os.path.join(song_path, "video.webm")
            
            self.update_status(f"Processing {i+1}/{total_songs}: {song_folder}")
            self.progress_bar.set((i / total_songs))
            self.root.update_idletasks()
            
            # Check if video already exists
            if os.path.exists(video_file):
                # If skip_all_existing is set, don't ask and just skip
                if self.skip_all_existing:
                    self.log(f"Skipping {song_folder} (video already exists - Skip All active)")
                    i += 1
                    continue
                
                # Ensure we're not showing multiple dialogs
                if self.dialog_active:
                    # Wait for existing dialog to complete
                    while self.dialog_active and self.processing:
                        time.sleep(0.1)
                    if not self.processing:
                        break
                
                # Ask user what to do in the main thread
                self.dialog_active = True
                response = self.ask_overwrite(song_folder)
                
                # Dialog has been handled
                self.dialog_active = False
                
                if response == "skip":
                    self.log(f"Skipping {song_folder} (video already exists)")
                    i += 1
                    continue
                elif response == "skip_all":
                    self.log(f"Skipping {song_folder} and all remaining songs with existing videos")
                    self.skip_all_existing = True
                    i += 1
                    continue
                elif response == "stop":
                    self.log("Process stopped by user")
                    break
            
            self.log(f"Processing: {song_folder}")
            
            try:
                # Download video from YouTube
                success = self.download_video(song_folder, song_path)
                if not success:
                    self.log(f"Failed to process {song_folder}. Moving to next song.")
            except Exception as e:
                self.log(f"Error processing {song_folder}: {str(e)}")
            
            # Move to next song regardless of success or failure
            i += 1
        
        # Update UI when done
        self.root.after(0, self.processing_finished)
    
    def ask_overwrite(self, song_name):
        # This function will be called from the processing thread
        # We'll use a synchronization mechanism to block until the user responds
        
        self.dialog_active = True
        response = {"action": None}  # Use a dict so it can be modified in the nested function
        
        def show_dialog():
            # Create a custom dialog with "Replace", "Skip", "Skip All", and "Cancel" buttons
            dialog = ctk.CTkToplevel(self.root)
            dialog.title("Video Already Exists")
            dialog.geometry("400x200")
            dialog.transient(self.root)
            dialog.lift()  # Bring to front
            dialog.grid_columnconfigure(0, weight=1)
            dialog.grid_rowconfigure(0, weight=1)
            
            # Set dialog to be modal
            dialog.grab_set()
            
            # Create a frame for the content
            content_frame = ctk.CTkFrame(dialog)
            content_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
            content_frame.grid_columnconfigure(0, weight=1)
            
            # Message
            msg = ctk.CTkLabel(content_frame, 
                              text=f"'{song_name}' already has a video.webm file.\nWhat would you like to do?", 
                              font=ctk.CTkFont(size=12),
                              wraplength=350)
            msg.grid(row=0, column=0, padx=20, pady=(20, 30))
            
            # Button frame
            btn_frame = ctk.CTkFrame(content_frame)
            btn_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
            btn_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
            
            def on_replace():
                response["action"] = "replace"
                dialog.destroy()
            
            def on_skip():
                response["action"] = "skip"
                dialog.destroy()
            
            def on_skip_all():
                response["action"] = "skipall"
                dialog.destroy()
            
            def on_cancel():
                response["action"] = "cancel"
                dialog.destroy()
            
            def on_dialog_close():
                # If the dialog is closed by the X button
                if not response["action"]:
                    response["action"] = "cancel"
                dialog.destroy()
            
            # Configure buttons with consistent sizes
            btn_width = 100
            btn_height = 30
            
            replace_btn = ctk.CTkButton(btn_frame, text="Replace", command=on_replace, 
                                      fg_color=("#1F6AA5", "#144870"), 
                                      width=btn_width, height=btn_height)
            replace_btn.grid(row=0, column=0, padx=5, pady=5)
            
            skip_btn = ctk.CTkButton(btn_frame, text="Skip", command=on_skip,
                                   width=btn_width, height=btn_height)
            skip_btn.grid(row=0, column=1, padx=5, pady=5)
            
            skip_all_btn = ctk.CTkButton(btn_frame, text="Skip All", command=on_skip_all,
                                       width=btn_width, height=btn_height)
            skip_all_btn.grid(row=0, column=2, padx=5, pady=5)
            
            cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", command=on_cancel,
                                     fg_color=("#DB3E39", "#821D1A"), 
                                     width=btn_width, height=btn_height)
            cancel_btn.grid(row=0, column=3, padx=5, pady=5)
            
            dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)
            dialog.focus_set()
            
            # Wait for the dialog to be closed before returning
            self.root.wait_window(dialog)
        
        # Schedule the dialog to be shown from the main thread
        self.root.after(0, show_dialog)
        
        # Wait for the dialog to complete
        while self.dialog_active and response["action"] is None:
            time.sleep(0.1)
            
        self.dialog_active = False
        
        # If the user chose "Skip All", set the flag to skip all future videos
        if response["action"] == "skipall":
            self.skip_all_existing = True
            return "skip"
        
        return response["action"]
    
    def sanitize_song_name(self, song_name):
        """Clean up song name for better YouTube search results"""
        # Remove bracketed content like [Chart by...]
        cleaned = re.sub(r'\[.*?\]', '', song_name)
        # Remove parenthesized content
        cleaned = re.sub(r'\(.*?\)', '', cleaned)
        # Remove special characters often used in file naming
        cleaned = re.sub(r'[-_+]', ' ', cleaned)
        # Remove extra spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Just return the cleaned folder name without adding any keywords
        return cleaned
    
    def download_video(self, song_name, song_path):
        self.log(f"Processing: {song_name}")
        
        # Sanitize song name for better search results
        search_term = self.sanitize_song_name(song_name)
        self.log(f"Search query: {search_term}")
        
        # Create temporary download directory
        temp_dir = os.path.join(song_path, "temp_download")
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # Get top 3 results from YouTube instead of just one
            search_query = f"ytsearch3:{search_term}"
            
            # Try alternative formats if the first one fails
            format_options = [
                # First try: Specific format for quality control
                f"bestvideo[height<={self.video_quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={self.video_quality}]",
                # Second try: Any video format with desired height
                f"bestvideo[height<={self.video_quality}]+bestaudio/best[height<={self.video_quality}]",
                # Third try: Just get the best quality available
                "bestvideo+bestaudio/best" 
            ]
            
            # Get search results first
            video_results = self.get_search_results(search_query)
            
            if not video_results:
                self.log(f"No videos found for {song_name}")
                return False
            
            # Show results to user if not in auto-fetch mode
            if not self.auto_fetch and len(video_results) > 1:
                selected_video = self.show_video_selection(video_results, song_name)
                if not selected_video:
                    self.log("Video selection canceled by user")
                    return False
            else:
                # In auto-fetch mode, just use the first result
                selected_video = video_results[0]
                self.log(f"Auto-fetch mode: Selected first result - {selected_video['title']}")
            
            # Download the selected video
            downloaded_file = self.download_selected_video(selected_video, temp_dir, format_options)
            
            if not downloaded_file:
                self.log(f"Failed to download video for {song_name}")
                return False
            
            # Convert to WebM with VP8 codec
            self.log("Converting to WebM with VP8 codec...")
            output_file = os.path.join(song_path, "video.webm")
            
            # Reset skip flag before starting conversions
            self.skip_conversion = False
            
            # Define conversion options to try
            conversion_options = [
                # Option 1: Fast conversion with reasonable quality - using stderr for progress
                [
                    self.ffmpeg_path, "-y", "-i", downloaded_file,
                    "-c:v", "libvpx", "-c:a", "libvorbis",
                    "-b:v", "1M", "-b:a", "128k",
                    "-deadline", "good", "-cpu-used", "4",  # Increased CPU usage for speed
                    output_file
                ],
                # Option 2: More compatible settings with lower quality
                [
                    self.ffmpeg_path, "-y", "-i", downloaded_file,
                    "-c:v", "libvpx", "-c:a", "libvorbis",
                    "-b:v", "800k", "-b:a", "128k",
                    "-deadline", "realtime", "-cpu-used", "8",  # Fastest settings
                    "-vf", "scale=640:360",  # Lower resolution for faster encoding
                    "-threads", "4",
                    output_file
                ],
                # Option 3: Alternative codec approach
                [
                    self.ffmpeg_path, "-y", "-i", downloaded_file,
                    "-c:v", "vp8", "-c:a", "libvorbis",  # Try vp8 instead of libvpx
                    "-b:v", "500k", "-b:a", "96k",
                    "-vf", "scale=640:360",
                    output_file
                ]
            ]
            
            conversion_success = False
            for i, cmd in enumerate(conversion_options):
                self.log(f"Trying conversion method {i+1}...")
                
                try:
                    # Set a timeout for the conversion process
                    max_duration_minutes = 5  # Reduced from 10 minutes
                    self.log(f"Setting timeout of {max_duration_minutes} minutes for conversion")
                    
                    # Get file info first
                    probe_cmd = [
                        self.ffmpeg_path, "-i", downloaded_file
                    ]
                    try:
                        if sys.platform == 'win32':
                            # Use hidden subprocess on Windows
                            startupinfo = STARTUPINFO()
                            startupinfo.dwFlags |= STARTF_USESHOWWINDOW
                            startupinfo.wShowWindow = SW_HIDE
                            probe_result = subprocess.run(probe_cmd, 
                                                        capture_output=True, 
                                                        text=True,
                                                        startupinfo=startupinfo,
                                                        creationflags=subprocess.CREATE_NO_WINDOW)
                        else:
                            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
                        self.log(f"Input file info: {probe_result.stderr[:200]}...")
                    except:
                        self.log("Couldn't get file info")
                    
                    # Run ffmpeg with progress tracking through stderr instead of pipe:1
                    if sys.platform == 'win32':
                        process = create_hidden_process(
                            cmd, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE,
                            universal_newlines=True,
                            bufsize=1  # Line buffered
                        )
                    else:
                        process = subprocess.Popen(
                            cmd, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE,
                            universal_newlines=True,
                            bufsize=1  # Line buffered
                        )
                    
                    # Track time and progress
                    start_time = time.time()
                    last_update_time = start_time
                    frame_pattern = re.compile(r'frame=\s*(\d+)')
                    fps_pattern = re.compile(r'fps=\s*(\d+)')
                    timeout_seconds = max_duration_minutes * 60
                    
                    # Create a non-blocking stderr reader
                    def read_stderr():
                        while True:
                            line = process.stderr.readline()
                            if not line:
                                break
                            yield line
                    
                    stderr_reader = read_stderr()
                    last_frame = 0
                    frames_stuck_count = 0
                    
                    # Process stderr in real-time to get progress
                    check_interval = 0.5  # Check every half second
                    while process.poll() is None:
                        # Check if processing was stopped by user
                        if not self.processing:
                            process.terminate()
                            self.log("Conversion terminated by user")
                            return False
                        
                        # Check if user requested to skip this conversion
                        if self.skip_conversion:
                            process.terminate()
                            self.log("Conversion skipped by user")
                            self.skip_conversion = False  # Reset flag
                            break  # Try next method
                        
                        # Check for timeout
                        current_time = time.time()
                        elapsed_seconds = current_time - start_time
                        if elapsed_seconds > timeout_seconds:
                            process.terminate()
                            self.log(f"Conversion timed out after {max_duration_minutes} minutes")
                            break  # Try next method
                        
                        # Process any new stderr lines
                        progress_updated = False
                        frame_count = None
                        fps = None
                        
                        # Try to read a few lines without blocking
                        for _ in range(10):  # Try to read up to 10 lines
                            try:
                                # Non-blocking read from stderr
                                line = next(stderr_reader, None)
                                if line is None:
                                    break
                                    
                                # Look for frame and fps info
                                frame_match = frame_pattern.search(line)
                                if frame_match:
                                    frame_count = int(frame_match.group(1))
                                    progress_updated = True
                                    
                                fps_match = fps_pattern.search(line)
                                if fps_match:
                                    fps = fps_match.group(1)
                            except:
                                break
                        
                        # Check if frames are advancing
                        if frame_count is not None:
                            if frame_count == last_frame:
                                frames_stuck_count += 1
                            else:
                                frames_stuck_count = 0
                                last_frame = frame_count
                        
                        # If frames are stuck for too long, terminate and try next method
                        if frames_stuck_count > 20:  # Stuck for 10 seconds (20 * 0.5s)
                            self.log(f"Conversion appears stuck at frame {last_frame}. Trying next method...")
                            process.terminate()
                            break
                        
                        # Update status if we got new information or if it's been a while
                        if progress_updated or (current_time - last_update_time) > 3:
                            if frame_count is not None:
                                elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_seconds))
                                fps_str = fps if fps else "unknown"
                                progress_msg = f"Converting: frame {frame_count}, time {elapsed_str}, fps={fps_str}"
                                self.update_status(progress_msg)
                                self.log(progress_msg, verbose=False)
                                last_update_time = current_time
                        
                        # Sleep a bit to avoid CPU hogging
                        time.sleep(check_interval)
                    
                    # Get final output
                    try:
                        stdout, stderr = process.communicate(timeout=5)  # 5 second timeout for final output
                    except subprocess.TimeoutExpired:
                        process.terminate()
                        stdout, stderr = "", "Communication timeout"
                    
                    if process.returncode == 0:
                        self.log("Conversion successful!")
                        conversion_success = True
                        break
                    else:
                        error_msg = stderr if stderr else "Unknown error"
                        self.log(f"Conversion attempt {i+1} failed. Error details:")
                        self.log(f"First 200 chars of error: {error_msg[:200]}")
                        
                        # Check for specific errors
                        if "Unknown encoder 'libvpx'" in error_msg:
                            self.log("The ffmpeg installation doesn't support libvpx codec. Trying with a different codec...")
                            # Try a different codec for VP8
                            alt_cmd = [
                                self.ffmpeg_path, "-y", "-i", downloaded_file,
                                "-c:v", "vp8", "-c:a", "libvorbis",  # Try vp8 instead of libvpx
                                "-b:v", "800k", "-b:a", "128k",
                                "-deadline", "good",
                                "-vf", "scale=640:360",
                                output_file
                            ]
                            self.log("Trying alternative codec conversion...")
                            alt_process = subprocess.run(alt_cmd, capture_output=True, text=True)
                            if alt_process.returncode == 0:
                                self.log("Alternative codec conversion successful!")
                                conversion_success = True
                                break
                
                except subprocess.TimeoutExpired:
                    self.log(f"Conversion attempt {i+1} timed out during final communication")
                    process.terminate()
                except Exception as e:
                    self.log(f"Error during conversion: {str(e)}")
                    import traceback
                    self.log(f"Error traceback: {traceback.format_exc()}")
                    try:
                        process.terminate()
                    except:
                        pass
            
            # If all conversion methods failed, try one last desperate approach with minimal operations
            if not conversion_success:
                self.log("All standard conversion methods failed. Trying minimal conversion as last resort...")
                try:
                    # Try a simple copy with minimal encoding
                    final_cmd = [
                        self.ffmpeg_path, "-y", "-i", downloaded_file,
                        "-c:v", "libvpx", "-c:a", "libvorbis",
                        "-vf", "scale=640:360",  # Low resolution
                        "-b:v", "500k", "-b:a", "96k",  # Low bitrate
                        "-deadline", "realtime", "-cpu-used", "16",  # Fastest possible encoding
                        "-threads", "4", 
                        "-quality", "worst",  # Use worst quality for speed
                        "-tile-columns", "6", "-frame-parallel", "1",  # Parallel processing
                        output_file
                    ]
                    
                    self.log("Running last resort conversion...")
                    if sys.platform == 'win32':
                        # Use hidden subprocess on Windows
                        startupinfo = STARTUPINFO()
                        startupinfo.dwFlags |= STARTF_USESHOWWINDOW
                        startupinfo.wShowWindow = SW_HIDE
                        result = subprocess.run(final_cmd, 
                                             capture_output=True, 
                                             text=True, 
                                             timeout=300,  # 5 minute timeout
                                             startupinfo=startupinfo,
                                             creationflags=subprocess.CREATE_NO_WINDOW)
                    else:
                        result = subprocess.run(final_cmd, capture_output=True, text=True, timeout=300)  # 5 minute timeout
                    
                    if result.returncode == 0:
                        self.log("Last resort conversion successful!")
                        conversion_success = True
                    else:
                        self.log(f"Last resort conversion failed: {result.stderr[:200]}")
                except Exception as e:
                    self.log(f"Last resort conversion error: {str(e)}")
            
            if not conversion_success:
                self.log(f"All conversion attempts failed for {song_name}")
                return False
            
            self.log(f"Successfully created video.webm for {song_name}")
            
            return True
            
        except Exception as e:
            self.log(f"Unexpected error: {str(e)}")
            import traceback
            self.log(f"Error details: {traceback.format_exc()}")
            return False
        finally:
            # Clean up temp files
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    self.log(f"Warning: Could not clean up temp directory: {str(e)}")
    
    def get_search_results(self, search_query):
        """Get search results from YouTube"""
        self.log(f"Searching YouTube for top results...")
        
        cmd = [
            "yt-dlp", "--no-download", 
            "--print", "title",
            "--print", "id",
            "--print", "duration",
            "--print", "view_count",
            search_query
        ]
        
        try:
            if sys.platform == 'win32':
                # Use hidden subprocess on Windows
                startupinfo = STARTUPINFO()
                startupinfo.dwFlags |= STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = SW_HIDE
                result = subprocess.run(cmd, 
                                      capture_output=True, 
                                      text=True,
                                      startupinfo=startupinfo,
                                      creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                result = subprocess.run(cmd, capture_output=True, text=True)
                
            output = result.stdout.strip()
            
            if not output:
                self.log("No search results found")
                return []
            
            # Parse the results
            lines = output.split('\n')
            videos = []
            
            # Log the raw output for debugging
            self.log(f"Raw yt-dlp output: {lines[:8]}")  # Show just first 2 videos worth of lines
            
            # Process the output in chunks of 4 lines (or as many as available)
            i = 0
            while i + 3 < len(lines):  # Make sure we have at least 4 lines
                title = lines[i]
                video_id = lines[i+1]
                duration = lines[i+2]
                view_count = lines[i+3]
                
                # Format the data
                video = {
                    'title': title,
                    'id': video_id,
                    'duration': duration,
                    'view_count': view_count,
                    'url': f"https://www.youtube.com/watch?v={video_id}"
                }
                
                videos.append(video)
                self.log(f"Found: {title} (Duration: {duration}, Views: {view_count})")
                
                # Move to the next group of 4 lines
                i += 4
            
            if not videos:
                self.log("No videos could be parsed from the output")
            
            return videos
        except Exception as e:
            self.log(f"Error getting search results: {str(e)}")
            import traceback
            self.log(f"Error details: {traceback.format_exc()}")
            return []

    def show_video_selection(self, videos, song_name):
        self.dialog_active = True
        result = {"video": None}
        
        def show_dialog():
            dialog = ctk.CTkToplevel(self.root)
            dialog.title(f"Select Video for {song_name}")
            dialog.geometry("700x500")
            dialog.transient(self.root)
            dialog.grab_set()
            dialog.grid_columnconfigure(0, weight=1)
            dialog.grid_rowconfigure(0, weight=1)
            
            # Main content frame
            content_frame = ctk.CTkFrame(dialog)
            content_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
            content_frame.grid_columnconfigure(0, weight=1)
            content_frame.grid_rowconfigure(1, weight=1)
            
            # Title and instruction
            title_label = ctk.CTkLabel(content_frame, 
                                    text=f"Select a video for '{song_name}'", 
                                    font=ctk.CTkFont(size=16, weight="bold"))
            title_label.grid(row=0, column=0, padx=20, pady=(10, 20), sticky="w")
            
            # Create a scrollable frame for video options
            scrollable_frame = ctk.CTkScrollableFrame(content_frame, height=250, width=650)
            scrollable_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
            scrollable_frame.grid_columnconfigure(0, weight=1)
            
            # Function to select a video
            def select_video(video):
                result["video"] = video
                dialog.destroy()
            
            # Function to open URL in browser
            def open_url(url):
                try:
                    import webbrowser
                    webbrowser.open(url)
                except Exception as e:
                    self.log(f"Error opening URL: {e}")
            
            # Function to handle dialog close
            def on_dialog_close():
                if result["video"] is None:
                    result["video"] = "cancel" 
                dialog.destroy()
            
            # Function to validate and use custom URL
            def use_custom_url():
                url = url_var.get().strip()
                if not url:
                    messagebox.showerror("Error", "Please enter a valid YouTube URL")
                    return
                
                # Extract video ID from different YouTube URL formats
                video_id = extract_video_id(url)
                if not video_id:
                    messagebox.showerror("Error", "Invalid YouTube URL format")
                    return
                
                # Create a custom video object
                custom_video = {
                    'title': 'Custom URL',
                    'id': video_id,
                    'url': f'https://www.youtube.com/watch?v={video_id}',
                    'duration': 0,  # Unknown duration
                    'view_count': 0,     # Unknown views
                    'custom': True
                }
                
                select_video(custom_video)
                
            # Extract video ID from different YouTube URL formats
            def extract_video_id(url):
                import re
                # Regular YouTube URL: https://www.youtube.com/watch?v=VIDEO_ID
                match = re.search(r'youtube\.com/watch\?v=([a-zA-Z0-9_-]+)', url)
                if match:
                    return match.group(1)
                
                # Shortened URL: https://youtu.be/VIDEO_ID
                match = re.search(r'youtu\.be/([a-zA-Z0-9_-]+)', url)
                if match:
                    return match.group(1)
                
                # Embed URL: https://www.youtube.com/embed/VIDEO_ID
                match = re.search(r'youtube\.com/embed/([a-zA-Z0-9_-]+)', url)
                if match:
                    return match.group(1)
                
                return None
            
            # Create a card for each video option
            for i, video in enumerate(videos):
                # Create a frame for each video with a nice card-like appearance
                video_frame = ctk.CTkFrame(scrollable_frame)
                video_frame.grid(row=i, column=0, padx=10, pady=10, sticky="ew")
                video_frame.grid_columnconfigure(1, weight=1)
                
                # Format duration to be more readable
                duration_secs = video.get('duration', 0)
                if duration_secs:
                    try:
                        duration_secs = int(duration_secs)
                        minutes = duration_secs // 60
                        seconds = duration_secs % 60
                        duration_str = f"{minutes}:{seconds:02d}"
                    except (ValueError, TypeError):
                        # If conversion fails, use it as is
                        duration_str = str(duration_secs)
                else:
                    duration_str = "Unknown duration"
                
                # Format view count
                view_count = video.get('view_count', video.get('views', 0))
                if view_count:
                    try:
                        view_count = int(view_count)
                        if view_count >= 1000000:
                            view_count_str = f"{view_count/1000000:.1f}M views"
                        elif view_count >= 1000:
                            view_count_str = f"{view_count/1000:.1f}K views"
                        else:
                            view_count_str = f"{view_count} views"
                    except (ValueError, TypeError):
                        # If conversion fails, use it as is
                        view_count_str = f"{view_count} views"
                else:
                    view_count_str = "Unknown views"
                
                # Option number
                option_label = ctk.CTkLabel(video_frame, text=f"Option {i+1}", 
                                         font=ctk.CTkFont(size=14, weight="bold"),
                                         width=80)
                option_label.grid(row=0, column=0, rowspan=2, padx=10, pady=10)
                
                # Video title
                title_label = ctk.CTkLabel(video_frame, 
                                        text=video['title'],
                                        font=ctk.CTkFont(size=13),
                                        wraplength=400, 
                                        justify="left",
                                        anchor="w")
                title_label.grid(row=0, column=1, padx=10, pady=(10, 2), sticky="w")
                
                # Video details
                details_label = ctk.CTkLabel(video_frame,
                                          text=f"Duration: {duration_str} | {view_count_str}",
                                          font=ctk.CTkFont(size=11),
                                          anchor="w")
                details_label.grid(row=1, column=1, padx=10, pady=(0, 10), sticky="w")
                
                # Button frame
                btn_frame = ctk.CTkFrame(video_frame)
                btn_frame.grid(row=0, column=2, rowspan=2, padx=10, pady=10)
                
                # Select button
                select_btn = ctk.CTkButton(btn_frame,
                                        text="Select",
                                        command=lambda v=video: select_video(v),
                                        width=80,
                                        height=30)
                select_btn.grid(row=0, column=0, padx=5, pady=5)
                
                # Open URL button
                url_btn = ctk.CTkButton(btn_frame,
                                      text="Preview",
                                      command=lambda url=video['url']: open_url(url),
                                      width=80,
                                      height=30,
                                      fg_color=("#6c757d", "#495057"))
                url_btn.grid(row=1, column=0, padx=5, pady=5)
            
            # Separator
            separator = ctk.CTkFrame(content_frame, height=2, fg_color=("gray70", "gray30"))
            separator.grid(row=2, column=0, padx=20, pady=15, sticky="ew")
            
            # Custom URL section
            custom_frame = ctk.CTkFrame(content_frame)
            custom_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
            custom_frame.grid_columnconfigure(1, weight=1)
            
            custom_label = ctk.CTkLabel(custom_frame, 
                                      text="Custom YouTube URL:",
                                      font=ctk.CTkFont(size=12))
            custom_label.grid(row=0, column=0, padx=10, pady=10)
            
            url_var = tk.StringVar()
            url_entry = ctk.CTkEntry(custom_frame, 
                                   textvariable=url_var, 
                                   width=350,
                                   placeholder_text="https://www.youtube.com/watch?v=...")
            url_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
            
            custom_btn = ctk.CTkButton(custom_frame, 
                                     text="Use Custom URL", 
                                     command=use_custom_url)
            custom_btn.grid(row=0, column=2, padx=10, pady=10)
            
            # Cancel button
            cancel_btn = ctk.CTkButton(content_frame, 
                                     text="Cancel", 
                                     command=lambda: select_video("cancel"),
                                     fg_color=("#DB3E39", "#821D1A"))
            cancel_btn.grid(row=4, column=0, padx=20, pady=15)
            
            dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)
            dialog.focus_set()
            
            # Wait for the dialog to close
            self.root.wait_window(dialog)
        
        # Show dialog from the main thread
        self.root.after(0, show_dialog)
        
        # Wait for the dialog to complete
        while self.dialog_active and result["video"] is None:
            time.sleep(0.1)
        
        self.dialog_active = False
        return result["video"]

    def download_selected_video(self, video, temp_dir, format_options):
        """Download the selected video"""
        self.log(f"Downloading selected video: {video['title']}")
        
        video_url = video['url']
        output_template = os.path.join(temp_dir, "%(title)s.%(ext)s")
        
        # For custom URLs, validate the URL format
        if video['title'].startswith("Custom video:"):
            self.log("Processing custom URL...")
            # Check if the URL can be extracted properly by yt-dlp
            try:
                # First verify the video exists and is downloadable
                verify_cmd = [
                    "yt-dlp", "--no-download", "--print", "title", 
                    video_url
                ]
                if sys.platform == 'win32':
                    # Use hidden subprocess on Windows
                    startupinfo = STARTUPINFO()
                    startupinfo.dwFlags |= STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = SW_HIDE
                    result = subprocess.run(verify_cmd, 
                                         capture_output=True, 
                                         text=True,
                                         startupinfo=startupinfo,
                                         creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    result = subprocess.run(verify_cmd, capture_output=True, text=True)
                if not result.stdout.strip():
                    self.log(f"Error: The custom URL could not be verified or is not a valid YouTube video: {video_url}")
                    return None
                    
                self.log(f"Custom URL verified. Found video: {result.stdout.strip()}")
            except Exception as e:
                self.log(f"Error verifying custom URL: {str(e)}")
                return None
        
        # Try each format option
        for format_index, format_option in enumerate(format_options):
            self.log(f"Download attempt {format_index+1}: Using format '{format_option}'")
            
            # Build the download command
            cmd = [
                "yt-dlp", 
                "-f", format_option,
                "--merge-output-format", "mp4",  # Target MP4 for initial download
                "--no-playlist",
                "--geo-bypass",
                "--max-filesize", "100M",  # Limit file size to avoid huge downloads
                "-o", output_template,
                video_url
            ]
            
            # Run the download process
            self.log(f"Downloading video at {self.video_quality}p...")
            if sys.platform == 'win32':
                process = create_hidden_process(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    bufsize=1  # Line buffered
                )
            else:
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    bufsize=1  # Line buffered
                )
            
            # Collect output for error reporting
            download_output = []
            
            # Process output in real-time
            for line in process.stdout:
                download_output.append(line)
                if not self.processing:
                    process.terminate()
                    self.log("Process terminated by user")
                    return None
                
                if "[download]" in line and "%" in line:
                    self.update_status(line.strip())
                elif "ERROR:" in line:
                    self.log(f"Download error: {line.strip()}")
            
            process.wait()
            
            # Check if the download was successful
            if process.returncode != 0:
                self.log(f"Download failed with exit code {process.returncode}")
                error_info = "\n".join(download_output[-5:]) if download_output else "No output captured"
                self.log(f"Download error details (last 5 lines):\n{error_info}")
                continue
            
            # Find the downloaded video file
            video_files = [f for f in os.listdir(temp_dir) 
                           if os.path.isfile(os.path.join(temp_dir, f)) and 
                           f.endswith(('.mp4', '.webm', '.mkv', '.avi'))]
            
            if not video_files:
                self.log("No video files found after download")
                continue
            
            # Get the most recently modified file
            video_files.sort(key=lambda f: os.path.getmtime(os.path.join(temp_dir, f)), reverse=True)
            downloaded_file = os.path.join(temp_dir, video_files[0])
            self.log(f"Successfully downloaded: {os.path.basename(downloaded_file)}")
            return downloaded_file
        
        # If all format options failed
        self.log("All download formats failed")
        return None
    
    def processing_finished(self):
        self.processing = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.skip_btn.configure(state="disabled")
        self.progress_bar.set(100)
        self.update_status("Finished")
        self.log("Processing completed!")

    def toggle_auto_fetch(self):
        self.auto_fetch = self.auto_fetch_var.get()
        self.log(f"Auto-fetch mode {'enabled' if self.auto_fetch else 'disabled'}")

def check_dependencies():
    """Check if required dependencies are installed"""
    missing = []
    
    # Check if running as a frozen executable
    if getattr(sys, 'frozen', False):
        # When running as an executable, we've already bundled everything
        return True
    
    # Check for yt-dlp
    try:
        if sys.platform == 'win32':
            # Use hidden subprocess on Windows
            startupinfo = STARTUPINFO()
            startupinfo.dwFlags |= STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = SW_HIDE
            subprocess.run(["yt-dlp", "--version"], 
                        capture_output=True,
                        check=True,
                        startupinfo=startupinfo,
                        creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            # Standard approach for other platforms
            subprocess.run(["yt-dlp", "--version"], 
                        capture_output=True, 
                        check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        missing.append("yt-dlp")
    
    # Check for ffmpeg
    try:
        if sys.platform == 'win32':
            # Use hidden subprocess on Windows
            startupinfo = STARTUPINFO()
            startupinfo.dwFlags |= STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = SW_HIDE
            subprocess.run(["ffmpeg", "-version"], 
                        capture_output=True, 
                        check=True,
                        startupinfo=startupinfo,
                        creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            # Standard approach for other platforms
            subprocess.run(["ffmpeg", "-version"], 
                        capture_output=True, 
                        check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Try checking for ffmpeg in the bin directory
        local_ffmpeg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", "ffmpeg.exe")
        if not os.path.exists(local_ffmpeg):
            missing.append("ffmpeg")
    
    return len(missing) == 0  # Return True if no missing dependencies

def main():
    # Check dependencies first
    if not check_dependencies():
        messagebox.showerror("Missing Dependencies", 
                           "The application requires yt-dlp and ffmpeg.\n"
                           "Please run setup.bat to install the required dependencies.")
        return
    
    root = ctk.CTk()
    app = CloneHeroVideoDownloader(root)
    
    # Set application icon if available
    try:
        # First try to use a bundled icon (for PyInstaller)
        import sys
        import os
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            bundle_dir = sys._MEIPASS
            icon_path = os.path.join(bundle_dir, 'icon.ico')
        else:
            # Running in development environment
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
            
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except Exception:
        # If icon setting fails, just continue without an icon
        pass
    
    # Center the window on screen
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    root.mainloop()

if __name__ == "__main__":
    main() 