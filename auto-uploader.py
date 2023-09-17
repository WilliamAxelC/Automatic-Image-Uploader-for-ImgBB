import os
import time
import requests
import tkinter as tk
from tkinter import scrolledtext
import sys
from tkinter import filedialog as fd
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import json


class ConsoleRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget
    
    def write(self, text):
        self.text_widget.insert(tk.END, text)
        self.text_widget.see(tk.END)
    
    def flush(self):
        pass

def save_config(filename, config):
    with open(filename, 'w') as config_file:
        json.dump(config, config_file, indent=4)

def load_config(filename):
    try:
        with open(filename, 'r') as config_file:
            config = json.load(config_file)
    except FileNotFoundError:
        # Create a new configuration dictionary
        config = {}
        # Save the new configuration to the file
        save_config(filename, config)
    return config

imgbb_api_key = '-'
directory_to_watch = '/'
pending_uploads = []
config = load_config('config.json')
imgbb_api_key = config.get('api_key', '')  # Get the API key from the loaded config
directory_to_watch = config.get('path_to_watch', '')


class MyGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("600x1000")
        self.title("Automatic Image Uploader for ImgBB by WillAx")

        config = self.config = load_config('config.json')
        imgbb_api_key = self.config.get('api_key', '')  # Get the API key from the loaded config
        directory_to_watch = self.config.get('path_to_watch', '')
        print(f"{directory_to_watch}")  # Get the directory path from the loaded config

        api_frame = tk.Frame(self, padx=10, pady=10)
        api_frame.rowconfigure(0, weight=1)
        api_frame.rowconfigure(1, weight=1)
        api_frame.rowconfigure(2, weight=1)
        

        self.user_api_key = tk.StringVar()
        api_label = tk.Label(api_frame, text=f"Current API key: '{imgbb_api_key}'", font=("Arial", 12), padx=10, pady=10)
        self.api_label = api_label
        api_label.grid(row=0, column=0, sticky=tk.W+tk.N+tk.E)


        api_entry = tk.Entry(api_frame, textvariable=self.user_api_key, font=("Arial", 12))
        self.api_entry = api_entry
        api_entry.grid(row=1, column=0, sticky=tk.W+tk.N+tk.E)
        
        api_save_button = tk.Button(api_frame, command=self.api_save_button_commands, text='Save API Key', font=("Arial", 12), padx=10, pady=10, fg="white", bg="gray")
        api_save_button.grid(row=2, column=0, sticky=tk.N+tk.W)

        api_frame.pack(fill='x')

        self.observer = None
        self.observer_status = tk.StringVar()
        self.observer_status.set('Observer Status: Stopped')
        # self.stop_observer()
        
        observer_frame = tk.Frame(self, padx=10, pady=10)
        observer_frame.pack(fill='x')
        observer_frame.rowconfigure(0, weight=1)
        observer_frame.rowconfigure(1, weight=1)
        observer_frame.columnconfigure(0, weight=0)
        observer_frame.columnconfigure(1, weight=0)

        observer_status_label = tk.Label(observer_frame, textvariable= self.observer_status, font=("Arial", 16), padx=10, pady=10)
        observer_status_label.grid(row=0, sticky=tk.N+tk.W)

        start_observer_button = tk.Button(observer_frame, text='Start Observer',  font=("Arial", 12), padx=5, pady=10, command=self.start_observer, fg="white", bg="gray")
        start_observer_button.grid(row=1, column=0, sticky=tk.N+tk.W)

        quit_observer_button = tk.Button(observer_frame, text='Stop Observer',  font=("Arial", 12), padx=5, pady=10, command=self.quit_observer, fg="white", bg="gray")
        quit_observer_button.grid(row=2, column=0, sticky=tk.N+tk.W)

        
        dir_frame = tk.Frame(self, padx=10, pady=10)
        dir_frame.pack(fill='x')     

        self.current_dir = tk.StringVar()
        self.current_dir.set(f"Current Path: {directory_to_watch}")

        self.dir_label = tk.Label(dir_frame, textvariable=self.current_dir, font=("Arial", 12), padx=10, pady=10)
        self.dir_label.grid(row=0, column=0,sticky=tk.N+tk.W)

        browse_dir_button = tk.Button(dir_frame,text="Change Path", command=self.browse_dir, padx=5, pady=10, font=("Arial", 12), fg="white", bg="gray")
        browse_dir_button.grid(row=1, column=0,sticky=tk.N+tk.W)


        # UPLOAD
        upload_section_frame = tk.Frame(self, padx=10, pady=10)
        upload_section_frame.pack(fill='x')
        upload_section_frame.columnconfigure(0, weight=0)

        auto_upload_frame = tk.Frame(upload_section_frame, padx=10, pady=10)
        auto_upload_frame.grid(row=0, sticky=tk.W)

        self.auto_upload_var = tk.BooleanVar()
        self.auto_upload_var.set(False)

        auto_upload_label = tk.Label(auto_upload_frame, text="Auto Upload", font=("Arial", 12),padx=10, pady=10)
        auto_upload_label.grid(row=0, column=1, sticky=tk.W)

        auto_upload_checkbox = tk.Checkbutton(auto_upload_frame, variable=self.auto_upload_var,onvalue=True, offvalue=False, command=self.auto_upload_checkbox_changed)
        auto_upload_checkbox.grid(row=0, column=0, sticky=tk.W)

        recursive_frame = tk.Frame(upload_section_frame, padx=10, pady=10)
        recursive_frame.grid(row=1, sticky=tk.W)

        self.recursive_var = tk.BooleanVar()
        self.recursive_var.set(False)

        recursive_label = tk.Label(recursive_frame, text="Check Sub-directories", font=("Arial", 12),padx=10, pady=10)
        recursive_label.grid(row=0, column=1, sticky=tk.W)

        recursive_checkbox = tk.Checkbutton(recursive_frame, variable=self.recursive_var,onvalue=True, offvalue=False, command=self.recursive_checkbox_changed)
        recursive_checkbox.grid(row=0, column=0, sticky=tk.W)

        file_listbox = tk.Listbox(upload_section_frame, selectmode=tk.MULTIPLE, height=10, width=70)
        file_listbox.grid(row=2, column=0)
        self.file_listbox = file_listbox

        add_images_button = tk.Button(upload_section_frame, text="Add Images to Upload", command=self.add_images, font=("Arial", 12), padx=5, pady=10, fg="white", bg="gray")
        add_images_button.grid(row=3,column=0, sticky=tk.W)
        add_images_button.place(x = 220, y= 288)

        self.pending_count_var = tk.StringVar()
        self.pending_count_var.set(f"Upload {len(pending_uploads)} Pending Images")

        upload_pending_button = tk.Button(upload_section_frame,textvariable=self.pending_count_var, font=("Arial", 12), padx=5, pady=10, command=self.upload_pending, fg="white", bg="gray")
        upload_pending_button.grid(row=3,column=0, sticky=tk.W)

        # Create a scrolled Text widget with a fixed size
        console_text = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=10, width=100)
        console_text.pack()

        # Redirect sys.stdout to the Text widget
        console_redirector = ConsoleRedirector(console_text)
        sys.stdout = console_redirector

        print("Automatic Image Uploader for ImgBB brought to you by: https://github.com/WilliamAxelC")

        # background_color = ''
        # font_color = ''

        # self.configure(bg=background_color)
        # api_frame.configure(bg=background_color)
        # observer_frame.configure(bg=background_color)
        # recursive_frame.configure(bg=background_color)
        # auto_upload_frame.configure(bg=background_color)
        # upload_section_frame.configure(bg=background_color)

        # api_label.configure(fg=font_color, bg=background_color)

    def start_observer(self):
        event_handler = ImageHandler()
        self.observer = Observer()
        self.observer.start()
        self.observer.schedule(event_handler, path=self.config.get('path_to_watch', ''), recursive=self.recursive_var.get())
        print("Observer Started.")
        self.observer_status.set('Observer status: Running')

    def quit_observer(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None  # Set observer to None after stopping it
            print("Observer Stopped.")
            self.observer_status.set('Observer status: Stopped')

    def save_user_api_key(self):
        global imgbb_api_key
        print(f"Changed key '{imgbb_api_key}' to '{self.user_api_key.get()}'")
        imgbb_api_key = self.user_api_key.get()

        if not self.user_api_key.get():
            return

        self.config['api_key'] = imgbb_api_key
        save_config('config.json', self.config)

        self.api_label.config(text=f"Current API key: '{imgbb_api_key}'")

    def api_save_button_commands(self):
        self.save_user_api_key()
        
        self.api_entry.delete(0, tk.END)

    def upload_pending(self):
        while pending_uploads:  # Make a copy of the list to avoid modifying it while iterating
            image_path = pending_uploads.pop(0)
            upload_image(image_path)
        self.file_listbox.delete(0, tk.END)
        self.update_pending_count()

    def update_pending_count(self):
        for file_path in pending_uploads:
            file_name = os.path.basename(file_path)
            self.file_listbox.insert(tk.END, file_name)
        self.pending_count_var.set(f"Upload {len(pending_uploads)} Pending Images")
    
    def browse_dir(self):
        global directory_to_watch
        user_directory_to_watch = fd.askdirectory(initialdir = directory_to_watch, title = "Select a Path")
        if user_directory_to_watch is None:
            return

        print(f"Changing Path from '{directory_to_watch}' to '{user_directory_to_watch}'")

        directory_to_watch = user_directory_to_watch

        print(f"Changed Path to '{directory_to_watch}'")

        if self.observer and self.observer.is_alive():
        # If the observer is running, stop it before starting with the new path
            self.quit_observer()

        self.current_dir.set(f"Current Path: {directory_to_watch}")
        self.config['path_to_watch'] = directory_to_watch
        self.start_observer()
        save_config('config.json', self.config)

    def recursive_checkbox_changed(self):
        if gui.observer and gui.observer.is_alive():
            self.quit_observer()
            
        self.start_observer()
        print(f"Recursive {self.recursive_var.get()}")
    
    def auto_upload_checkbox_changed(self):
        print(f"Auto Upload: {self.auto_upload_var.get()}")
        for image_path in pending_uploads:
            upload_image(image_path)
    
    def add_images(self):
        file_paths = fd.askopenfilenames(title="Select Images to Upload", filetypes=(("Image files", "*.png *.jpg *.jpeg *.gif"), ("All files", "*.*")))

        for file_path in file_paths:
            pending_uploads.append(file_path)
            file_name = os.path.basename(file_path)
            print(f"Added {file_name} to Pending Uploads")
        self.update_pending_count()
    

class ImageHandler(FileSystemEventHandler):
    def on_created(self, event):
        print("File Detected.")
        file_name = os.path.basename(event.src_path)
        if event.is_directory:
            print("File is a directory, aborting...")
            return
        elif event.event_type == 'created':
            src_path = os.path.abspath(event.src_path)  # Normalize the path

            if src_path.lower().endswith('.tmp'):
                # This is a temporary file; wait for the actual image file to be created
                # For example, wait for a .png file with the same name
                expected_image_path = src_path[:-4] + '.png'

                # Wait for the image file to exist
                while not os.path.exists(expected_image_path):
                    time.sleep(1)  # Wait for 1 second

                image_path = expected_image_path
            elif src_path.lower().endswith('.png'):
                image_path = src_path
            else:
                # Not a valid image file; ignore it
                return

            print(f"File '{image_path}' is an image, proceeding...")

            if gui.auto_upload_var.get():
                print("Uploading Image...")
                upload_image(image_path)
            else:
                print("Added to Pending Images")
                pending_uploads.append(image_path)

            gui.update_pending_count()

def wait_for_completion(image_path):
    # Wait for a brief period (e.g., 5 seconds) to allow stable diffusion to complete the image
    max_wait_time = 5  # You can adjust this value as needed
    waited_time = 0

    while not is_image_complete(image_path) and waited_time < max_wait_time:
        time.sleep(1)  # Wait for 1 second
        waited_time += 1

def is_image_complete(image_path):
    return os.path.exists(image_path) and os.path.getsize(image_path) > 0

def upload_image(image_path):
    try:
        with open(image_path, 'rb') as file:
            response = requests.post(
                'https://api.imgbb.com/1/upload',
                params={'key': imgbb_api_key},
                files={'image': file}
            )
            if response.status_code == 200:
                print(f"Image uploaded successfully. URL: {response.json()['data']['url']}")
            else:
                print(f"Failed to upload image. Status code: {response.status_code}")
                error_message = response.json().get('error', 'No error message provided')
                print(f"Error message: {error_message}")
    except Exception as e:
        print(f"An error occurred while uploading the image: {str(e)}")

if __name__ == "__main__":
    gui = MyGUI()
    gui.mainloop()
