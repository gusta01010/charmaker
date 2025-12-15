import tkinter as tk
from tkinter import filedialog

def open_image_dialog():
    """Opens a file dialog to select a common image file."""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    filepath = filedialog.askopenfilename(
        title="Select an Image",
        filetypes=(
            ("Image Files", "*.png *.jpg *.jpeg *.webp"),
            ("All files", "*.*")
        )
    )
    return filepath

def open_images_dialog():
    """Opens a file dialog to select multiple image files."""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    filepaths = filedialog.askopenfilenames(
        title="Select Images",
        filetypes=(
            ("Image Files", "*.png *.jpg *.jpeg *.webp"),
            ("All files", "*.*")
        )
    )
    return filepaths

def open_folder_dialog(initial_dir="."):
    """Opens a folder selection dialog."""
    root = tk.Tk()
    root.withdraw() # Hides the main window
    folder_path = filedialog.askdirectory(
        title="Select a Folder to Save Characters",
        initialdir=initial_dir
    )
    return folder_path