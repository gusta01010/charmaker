import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import threading
import sys
import os
import requests
import io
from PIL import Image, ImageTk

# Add the src directory to sys.path if not running from there
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from image_handler import ImageHandler
from api_handler import APIHandler
from scraper import scrape_with_selenium, scrape_with_crawl4ai
from character_card import save_character_card
import config_manager
from main import parse_ai_response


class CharMakerTkinterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("✨ CharMaker AI Interface")
        self.root.geometry("1020x720")
        self.root.minsize(760, 640)

        self.compact_breakpoint = 980
        self.is_compact_layout = False
        
        self.config = config_manager.load_config()
        self.is_dark_mode = self.config.get('dark_mode', False)
        self.thumb_image = None
        self.preview_timer = None
        
        self.setup_styles()
        self.setup_ui()
        self.queue_preview_update()
        
    def setup_styles(self):
        style = ttk.Style(self.root)
        if 'clam' in style.theme_names():
            style.theme_use('clam')
            
        if self.is_dark_mode:
            self.bg_color = "#1e1e1e"
            self.card_bg = "#2d2d30"
            self.primary = "#4a90e2"
            self.text_color = "#f0f0f0"
            self.text_widget_bg = "#1e1e1e"
            self.text_widget_fg = "#f0f0f0"
            self.header_color = "#ffffff"
            self.entry_bg = "#333333"
            self.entry_fg = "#ffffff"
        else:
            self.bg_color = "#f0f3f5"
            self.card_bg = "#ffffff"
            self.primary = "#2b579a"
            self.text_color = "#202124"
            self.text_widget_bg = "#f9fafd"
            self.text_widget_fg = "#333333"
            self.header_color = "#1a1a1a"
            self.entry_bg = "#ffffff"
            self.entry_fg = "#000000"
            
        self.root.configure(bg=self.bg_color)
        
        style.configure('.', background=self.bg_color, foreground=self.text_color, font=('Segoe UI', 10))
        style.configure('TFrame', background=self.bg_color)
        style.configure('Card.TFrame', background=self.card_bg)
        
        style.configure('TLabelframe', background=self.card_bg, borderwidth=1, bordercolor="#e1e1e1" if not self.is_dark_mode else "#444", relief="flat")
        style.configure('TLabelframe.Label', background=self.card_bg, font=('Segoe UI', 11, 'bold'), foreground=self.primary)
        
        style.configure('TLabel', background=self.card_bg, foreground=self.text_color, font=('Segoe UI', 10))
        style.configure('Header.TLabel', background=self.bg_color, font=('Segoe UI', 20, 'bold'), foreground=self.header_color)
        style.configure('SubHeader.TLabel', background=self.bg_color, font=('Segoe UI', 10), foreground="#888" if self.is_dark_mode else "#5f6368")
        style.configure('Status.TLabel', background=self.bg_color, font=('Segoe UI', 10, 'italic'), foreground="#888" if self.is_dark_mode else "#5f6368")
        
        style.configure('TCombobox', fieldbackground=self.entry_bg, background=btn_bg if 'btn_bg' in locals() else ("#444" if self.is_dark_mode else "#e1dfdd"), foreground=self.entry_fg, padding=4)
        style.map('TCombobox', fieldbackground=[('readonly', self.entry_bg)], selectbackground=[('readonly', self.primary)], selectforeground=[('readonly', 'white')])

        style.configure('TEntry', fieldbackground=self.entry_bg, foreground=self.entry_fg, padding=4)
        style.map('TEntry', fieldbackground=[('disabled', '#222' if self.is_dark_mode else '#f0f0f0')])
        style.configure('TCheckbutton', background=self.card_bg, foreground=self.text_color, font=('Segoe UI', 10))
        style.map('TCheckbutton', background=[('active', self.card_bg)])
        style.configure('TRadiobutton', background=self.card_bg, foreground=self.text_color)
        
        btn_bg = "#444" if self.is_dark_mode else "#e1dfdd"
        btn_fg = "#f0f0f0" if self.is_dark_mode else "#000"
        
        # We define TCombobox styles referencing btn_bg, so we update it here
        style.configure('TCombobox', fieldbackground=self.entry_bg, background=btn_bg, foreground=self.entry_fg, padding=4)
        style.map('TCombobox', fieldbackground=[('readonly', self.entry_bg)], selectbackground=[('readonly', self.primary)], selectforeground=[('readonly', 'white')])

        style.configure('TButton', font=('Segoe UI', 10), background=btn_bg, foreground=btn_fg, borderwidth=0, padding=6)
        style.map('TButton', background=[('active', '#555' if self.is_dark_mode else '#d0d0d0'), ('disabled', '#333' if self.is_dark_mode else '#f3f2f1')])
        
        style.configure('Theme.TButton', font=('Segoe UI Emoji', 14), background=self.bg_color, foreground=self.text_color, borderwidth=0, padding=2, anchor='center')
        style.map('Theme.TButton', background=[('active', '#333' if self.is_dark_mode else '#e0e0e0')])
        
        style.configure('Action.TButton', font=('Segoe UI', 12, 'bold'), foreground='white', background=self.primary, padding=10)
        style.map('Action.TButton', 
                  background=[('active', '#357abd' if self.is_dark_mode else '#1e3e6d'), ('disabled', '#555' if self.is_dark_mode else '#a5b5c9')], 
                  foreground=[('disabled', '#888' if self.is_dark_mode else '#f0f0f0')])
                  
        style.configure('Horizontal.TProgressbar', background=self.primary, troughcolor=btn_bg, borderwidth=0, thickness=4)
        
        style.configure('TNotebook', background=self.bg_color, borderwidth=0)
        style.configure('TNotebook.Tab', background=btn_bg, foreground=btn_fg, padding=[10, 5], font=('Segoe UI', 10))
        style.map('TNotebook.Tab', 
                  background=[('selected', self.card_bg), ('active', '#555' if self.is_dark_mode else '#d0d0d0')], 
                  foreground=[('selected', self.primary)])

        if hasattr(self, 'urls_text'):
            self.urls_text.configure(bg=self.text_widget_bg, fg=self.text_widget_fg, insertbackground=self.text_color, highlightbackground="#444" if self.is_dark_mode else "#d1d5db")
            self.instructions_text.configure(bg=self.text_widget_bg, fg=self.text_widget_fg, insertbackground=self.text_color, highlightbackground="#444" if self.is_dark_mode else "#d1d5db")

    def toggle_dark_mode(self):
        self.is_dark_mode = not self.is_dark_mode
        self.dark_mode_btn.config(text="☀️" if self.is_dark_mode else "🌒")
        self.config['dark_mode'] = self.is_dark_mode
        config_manager.save_config(self.config)
        self.setup_styles()

    def setup_ui(self):
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill="x", padx=14, pady=(8, 4))
        
        self.dark_mode_btn = ttk.Button(header_frame, text="☀️" if self.is_dark_mode else "🌒", style='Theme.TButton', command=self.toggle_dark_mode, width=3)
        self.dark_mode_btn.pack(side="right", anchor="n", padx=(0, 6))
        
        titles_frame = ttk.Frame(header_frame)
        titles_frame.pack(side="left", fill="x", expand=True)
        ttk.Label(titles_frame, text="CharMaker AI Generation", style='Header.TLabel').pack(anchor="w")
        ttk.Label(titles_frame, text="Provide URLs and parameters to fully construct and generate character cards automatically.", style='SubHeader.TLabel').pack(anchor="w")

        self.main_paned = ttk.Frame(self.root)
        self.main_paned.pack(fill="both", expand=True, padx=14, pady=4)
        self.main_paned.columnconfigure(0, weight=1, uniform="col")
        self.main_paned.columnconfigure(1, weight=1, uniform="col")
        self.main_paned.rowconfigure(0, weight=1)
        self.main_paned.rowconfigure(1, weight=1)

        self.left_frame = ttk.Frame(self.main_paned)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        
        content_frame = ttk.LabelFrame(self.left_frame, text="Content Sources", padding=10)
        content_frame.pack(fill="both", expand=True, pady=(0, 8))
        
        ttk.Label(content_frame, text="Target URLs / Images (one per line):", font=('Segoe UI', 9, 'bold')).pack(anchor="w", pady=(0, 5))
        self.urls_text = tk.Text(content_frame, height=6, font=('Consolas', 10), relief="flat", padx=8, pady=7, spacing1=5, spacing3=5, highlightthickness=1)
        self.urls_text.pack(fill="both", expand=True, pady=(0, 8))
        
        ttk.Label(content_frame, text="Additional Custom Instructions (Prompt):", font=('Segoe UI', 9, 'bold')).pack(anchor="w", pady=(0, 5))
        self.instructions_text = tk.Text(content_frame, height=4, font=('Segoe UI', 10), relief="flat", padx=8, pady=7, spacing1=2, spacing3=2, highlightthickness=1)
        self.instructions_text.pack(fill="both", expand=True)

        self.urls_text.configure(bg=self.text_widget_bg, fg=self.text_widget_fg, insertbackground=self.text_color, highlightbackground="#d1d5db")
        self.instructions_text.configure(bg=self.text_widget_bg, fg=self.text_widget_fg, insertbackground=self.text_color, highlightbackground="#d1d5db")

        self.right_frame = ttk.Frame(self.main_paned)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        # Split AI configuration into two tabs
        self.config_notebook = ttk.Notebook(self.right_frame)
        self.config_notebook.pack(fill="x", pady=(0, 8))

        api_frame = ttk.Frame(self.config_notebook, padding=10)
        self.config_notebook.add(api_frame, text="AI Configuration")
        
        ttk.Label(api_frame, text="Platform Provider:").grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        provider_box_frame = ttk.Frame(api_frame)
        provider_box_frame.grid(row=0, column=1, sticky="w", padx=10, pady=(0, 10))
        
        self.provider_var = tk.StringVar(value=self.config.get('api_provider', 'groq'))
        self.provider_cb = ttk.Combobox(provider_box_frame, textvariable=self.provider_var, values=["groq", "openrouter", "gemini"], state="readonly", width=18)
        self.provider_cb.pack(side="left")
        self.provider_cb.bind("<<ComboboxSelected>>", self.on_provider_change)

        self.gemini_grounding_var = tk.BooleanVar(value=self.config.get('gemini_grounding', False))
        self.gemini_grounding_chk = ttk.Checkbutton(provider_box_frame, text="Google Grounding", variable=self.gemini_grounding_var, command=self.on_grounding_toggle)
        if self.provider_var.get() == "gemini":
            self.gemini_grounding_chk.pack(side="left", padx=(10, 0))
        
        ttk.Label(api_frame, text="API Key:").grid(row=1, column=0, sticky="w", pady=(0, 10))
        self.api_key_var = tk.StringVar(value=self.config.get(f"{self.provider_var.get()}_api_key", ""))
        self.api_key_var.trace_add("write", self.on_api_key_change)
        self.api_key_entry = ttk.Entry(api_frame, textvariable=self.api_key_var, width=28, show="*")
        self.api_key_entry.grid(row=1, column=1, sticky="w", padx=10, pady=(0, 10))
        
        ttk.Label(api_frame, text="LLM Model:").grid(row=2, column=0, sticky="w", pady=(0, 10))
        self.model_var = tk.StringVar(value=config_manager.get_current_model(self.config))
        self.model_var.trace_add("write", self.on_model_change)
        self.model_entry = ttk.Entry(api_frame, textvariable=self.model_var, width=28)
        self.model_entry.grid(row=2, column=1, sticky="w", padx=10, pady=(0, 10))
        
        ttk.Label(api_frame, text="Preset:").grid(row=3, column=0, sticky="w", pady=(0, 10))
        preset_frame = ttk.Frame(api_frame)
        preset_frame.grid(row=3, column=1, sticky="w", padx=10, pady=(0, 10))
        self.preset_var = tk.StringVar(value=self.config.get('preset', 'Preset 3'))
        self.preset_cb = ttk.Combobox(preset_frame, textvariable=self.preset_var, values=["Preset 1", "Preset 2", "Preset 3"], state="readonly", width=19)
        self.preset_cb.pack(side="left")
        self.preset_cb.bind("<<ComboboxSelected>>", self.on_preset_change)
        self.preset_help_btn = ttk.Button(preset_frame, text="❓", width=3, command=self.show_preset_help)
        self.preset_help_btn.pack(side="left", padx=(5, 0))
        
        self.sep_sys_msg_var = tk.BooleanVar(value=self.config.get('separate_system_messages', False))
        ttk.Checkbutton(api_frame, text="Separate System Messages", variable=self.sep_sys_msg_var, command=self.on_sys_msg_toggle).grid(row=4, column=0, columnspan=2, sticky="w")
        
        self.check_tokens_var = tk.BooleanVar(value=self.config.get('check_token_count', True))
        ttk.Checkbutton(api_frame, text="Check token count before generation", variable=self.check_tokens_var, command=self.on_check_tokens_toggle).grid(row=5, column=0, columnspan=2, sticky="w", pady=(5, 0))

        scraping_frame = ttk.Frame(self.config_notebook, padding=10)
        self.config_notebook.add(scraping_frame, text="Scraping Settings")

        ttk.Label(scraping_frame, text="Scraper Engine:").grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.scraper_engine_var = tk.StringVar(value=self.config.get('scraper_engine', 'legacy'))
        
        self.scraper_engine_cb = ttk.Combobox(scraping_frame, textvariable=self.scraper_engine_var, values=["legacy (scraper.py)", "crawl4ai"], state="readonly", width=18)
        self.scraper_engine_cb.grid(row=0, column=1, sticky="w", padx=10, pady=(0, 10))
        self.scraper_engine_cb.bind("<<ComboboxSelected>>", self.on_scraper_engine_change)

        self.crawl4ai_headless_var = tk.BooleanVar(value=self.config.get('crawl4ai_headless', True))
        self.crawl4ai_headless_chk = ttk.Checkbutton(scraping_frame, text="Use Headless Mode (recommended: off)", variable=self.crawl4ai_headless_var, command=self.on_headless_mode_toggle)

        self.update_scraper_options()

        img_frame = ttk.LabelFrame(self.right_frame, text="Image Settings", padding=10)
        img_frame.pack(fill="x", pady=(0, 8))
        
        ttk.Label(img_frame, text="Final Avatar Image Source:", font=('Segoe UI', 9)).pack(anchor="w", pady=(0, 5))
        
        img_opt_frame = ttk.Frame(img_frame, style='Card.TFrame')
        img_opt_frame.pack(fill="x")
        
        self.final_img_type_var = tk.StringVar(value="default")
        self.final_img_cb = ttk.Combobox(img_opt_frame, textvariable=self.final_img_type_var, 
                                         values=["default", "local", "url"], state="readonly", width=12)
        self.final_img_cb.pack(side="left", padx=(0, 10))
        self.final_img_cb.bind("<<ComboboxSelected>>", self.on_final_img_opt_change)
        
        self.final_img_val_var = tk.StringVar()
        self.final_img_val_var.trace_add("write", self.queue_preview_update)
        
        self.final_img_entry = ttk.Entry(img_opt_frame, textvariable=self.final_img_val_var)
        self.final_img_entry.pack(side="left", fill="x", expand=True)
        self.final_img_entry.config(state="disabled")
        
        self.final_img_btn = ttk.Button(img_opt_frame, text="Browse", width=8, command=self.browse_image)

        self.preview_frame = ttk.Frame(img_frame, style='Card.TFrame', height=98)
        self.preview_frame.pack(fill="x", pady=(8, 0))
        self.preview_frame.pack_propagate(False)

        self.thumb_label = ttk.Label(self.preview_frame, text="No Preview", style='Status.TLabel', anchor="center")
        self.thumb_label.pack(fill="both", expand=True)

        out_frame = ttk.LabelFrame(self.right_frame, text="Output Directory", padding=10)
        out_frame.pack(fill="x")
        
        out_inner = ttk.Frame(out_frame, style='Card.TFrame')
        out_inner.pack(fill="x")
        
        ttk.Label(out_inner, text="Path:", font=('Segoe UI', 9)).pack(side="left", padx=(0, 5))
        self.save_loc_var = tk.StringVar(value=self.config.get('save_location', 'saved_characters'))
        ttk.Entry(out_inner, textvariable=self.save_loc_var, state="readonly").pack(side="left", fill="x", expand=True)
        ttk.Button(out_inner, text="Change...", width=10, command=self.change_save_location).pack(side="left", padx=(10, 0))

        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(fill="x", side="bottom", padx=14, pady=(0, 10))
        
        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(bottom_frame, mode='indeterminate', variable=self.progress_var, style="Horizontal.TProgressbar")
        
        self.start_btn = ttk.Button(bottom_frame, text="🚀 START GENERATION", style='Action.TButton', command=self.on_start)
        self.start_btn.pack(fill="x", pady=(0, 10))
        
        self.status_var = tk.StringVar(value="Ready and waiting.")
        ttk.Label(bottom_frame, textvariable=self.status_var, style='Status.TLabel', anchor="center").pack(fill="x")

        self.root.bind("<Configure>", self.on_window_resize)
        self.root.after(50, self.apply_responsive_layout)

    def apply_responsive_layout(self):
        width = self.root.winfo_width()
        compact = width < self.compact_breakpoint

        if compact == self.is_compact_layout:
            return

        self.is_compact_layout = compact

        self.left_frame.grid_forget()
        self.right_frame.grid_forget()

        if compact:
            self.left_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 6))
            self.right_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=(0, 0))
            self.main_paned.columnconfigure(1, weight=0)
        else:
            self.left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)
            self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=0)
            self.main_paned.columnconfigure(1, weight=1, uniform="col")

    def on_window_resize(self, event):
        if event.widget is self.root:
            self.apply_responsive_layout()

    def queue_preview_update(self, *args):
        if self.preview_timer:
            self.root.after_cancel(self.preview_timer)
        self.preview_timer = self.root.after(800, self.update_thumbnail_preview)

    def update_thumbnail_preview(self):
        path = self.get_final_image_path()
        if not path:
            self.thumb_label.config(text="No Preview", image="")
            self.thumb_image = None
            return
        
        def load_img():
            try:
                if path.startswith("http"):
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    resp = requests.get(path, headers=headers, stream=True, timeout=5)
                    resp.raise_for_status()
                    img = Image.open(io.BytesIO(resp.content))
                else:
                    if not os.path.exists(path):
                        raise Exception("File not found")
                    img = Image.open(path)
                    
                img.thumbnail((90, 90))
                photo = ImageTk.PhotoImage(img)
                
                def set_img():
                    self.thumb_image = photo
                    self.thumb_label.config(image=photo, text="")
                    
                self.root.after(0, set_img)
            except Exception as e:
                def set_err():
                    self.thumb_label.config(text="Preview Unavailable", image="")
                    self.thumb_image = None
                self.root.after(0, set_err)
        
        self.thumb_label.config(text="Loading preview...", image="")
        threading.Thread(target=load_img, daemon=True).start()

    def on_api_key_change(self, *args):
        provider = self.provider_var.get()
        self.config[f'{provider}_api_key'] = self.api_key_var.get()
        config_manager.save_config(self.config)

    def on_model_change(self, *args):
        provider = self.provider_var.get()
        config_manager.set_provider_model(self.config, provider, self.model_var.get())

    def on_preset_change(self, event=None):
        self.config['preset'] = self.preset_var.get()
        config_manager.save_config(self.config) 

    def show_preset_help(self):
        help_text = (
            "Presets control how the AI formats and styles the characters.\n\n"
            "• Preset 1: Experimental,  great results.\n"
            "• Preset 2: Tends to write shorter descriptions (1300 - 2100).\n"
            "• Preset 3: Tends to write longer descriptions (2000 - 3500).\n\n"
            """Scorecard (Accuracy + Roleplaying quality):
            Description	      Greeting	Combined
Preset 1    88.3	         88.0	     88.2
Preset 2    78.0	         84.3	     81.2
Preset 3    82.0	         78.0	     80.0

-Average analyzed with internet sources from the models:
anthropic/claude-opus-4.6-search
google/gemini-3.1-pro-grounding,
gpt-5.2-search
    
using same 3 URLS + 1 image and gemini-3-flash-preview to generate.\n\n"""
            "You can customize these by editing the 'presets.py' file."
        )
        messagebox.showinfo("Preset Information", help_text)

    def on_sys_msg_toggle(self, event=None):
        self.config['separate_system_messages'] = self.sep_sys_msg_var.get()
        config_manager.save_config(self.config)

    def on_check_tokens_toggle(self, event=None):
        self.config['check_token_count'] = self.check_tokens_var.get()
        config_manager.save_config(self.config)

    def on_final_img_opt_change(self, event=None):
        opt = self.final_img_type_var.get()
        self.final_img_btn.pack_forget()
        self.final_img_entry.pack_forget()
        
        if opt == "default":
            self.final_img_entry.pack(side="left", fill="x", expand=True)
            self.final_img_entry.delete(0, tk.END)
            self.final_img_entry.config(state="disabled")
        elif opt == "local":
            self.final_img_entry.pack(side="left", fill="x", expand=True)
            self.final_img_entry.config(state="normal")
            self.final_img_btn.pack(side="left", padx=(10,0))
        elif opt == "url":
            self.final_img_entry.pack(side="left", fill="x", expand=True)
            self.final_img_entry.config(state="normal")
            
        self.queue_preview_update()
            
    def browse_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp")])
        if path:
            self.final_img_val_var.set(path)

    def on_scraper_engine_change(self, event=None):
        engine = self.scraper_engine_var.get()
        if engine == "crawl4ai":
            try:
                import crawl4ai
            except ImportError:
                messagebox.showwarning("Missing Library", "crawl4ai is not installed. Please install it using 'pip install crawl4ai'. Falling back to legacy scraper.")
                self.scraper_engine_var.set("legacy (scraper.py)")
                engine = "legacy (scraper.py)"
        
        self.config['scraper_engine'] = engine
        config_manager.save_config(self.config)
        self.update_scraper_options()

    def on_headless_mode_toggle(self, event=None):
        self.config['crawl4ai_headless'] = self.crawl4ai_headless_var.get()
        config_manager.save_config(self.config)

    def update_scraper_options(self):
        if self.scraper_engine_var.get() == "crawl4ai":
            self.crawl4ai_headless_chk.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 10))
        else:
            self.crawl4ai_headless_chk.grid_forget()

    def on_provider_change(self, event=None):
        provider = self.provider_var.get()
        self.config['api_provider'] = provider

        if provider == 'groq':
            messagebox.showwarning(
                "⚠️ Groq API Warning",
                "**WARNING!**\n\nRecently groq began to restrict multiple accounts due to violation of their terms of service, be very careful using this service because it can get your organization restricted."
            )

        model = config_manager.get_current_model(self.config)
        self.model_var.set(model)

        api_key = self.config.get(f"{provider}_api_key", "")
        self.api_key_var.set(api_key)

        if provider == "gemini":
            self.gemini_grounding_chk.pack(side="left", padx=(10, 0))
        else:
            self.gemini_grounding_chk.pack_forget()

        config_manager.save_config(self.config)

    def on_grounding_toggle(self, event=None):
        self.config['gemini_grounding'] = self.gemini_grounding_var.get()
        config_manager.save_config(self.config)

    def change_save_location(self):
        new_loc = filedialog.askdirectory(initialdir=self.save_loc_var.get())
        if new_loc:
            self.save_loc_var.set(new_loc)
            
    def update_status(self, text):
        self.status_var.set(text)
        self.root.update_idletasks()
        
    def on_start(self):
        self.start_btn.config(state="disabled", text="GENERATING...")
        self.progress_bar.pack(fill="x", pady=(0, 10), before=self.start_btn)
        self.progress_bar.start(15)
        threading.Thread(target=self.run_generation_workflow, daemon=True).start()
        
    def end_loading(self):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.start_btn.config(state="normal", text="🚀 START GENERATION")

    def run_generation_workflow(self):
        try:
            provider = self.provider_var.get()
            self.config['api_provider'] = provider
            config_manager.set_provider_model(self.config, provider, self.model_var.get())
            self.config['separate_system_messages'] = self.sep_sys_msg_var.get()
            self.config['save_location'] = self.save_loc_var.get()
            
            # Apply the selected preset
            try:
                from presets import PRESET1, PRESET2, PRESET3
                preset_map = {"Preset 1": PRESET1, "Preset 2": PRESET2, "Preset 3": PRESET3}
                APIHandler.INSTRUCTIONS = preset_map.get(self.preset_var.get(), PRESET3)
            except Exception as e:
                print(f"Warning: Could not load presets directly ({e})")
            
            raw_urls = [line.strip() for line in self.urls_text.get("1.0", tk.END).split('\n') if line.strip()]
            instructions = self.instructions_text.get("1.0", tk.END).strip()
            
            urls_to_scrape = []
            gen_image_objects = []
            
            for url in raw_urls:
                if ImageHandler.is_image_url(url):
                    self.update_status("Loading generation visual references...")
                    loaded_img = ImageHandler.load_image(url)
                    if loaded_img:
                        gen_image_objects.append(loaded_img)
                    else:
                        self.update_status("Failed to load one visual reference... proceeding anyway.")
                else:
                    urls_to_scrape.append(url)
            
            scraped_content = ""
            if urls_to_scrape:
                self.update_status(f"Scraping URLs (fetching web content from {len(urls_to_scrape)} sources)...")
                engine = self.config.get('scraper_engine', 'legacy (scraper.py)')
                if engine == 'crawl4ai':
                    headless = self.config.get('crawl4ai_headless', True)
                    scraped_content = scrape_with_crawl4ai(urls_to_scrape, headless=headless)
                    if scraped_content is None:
                        # Fallback
                        scraped_content = scrape_with_selenium(urls_to_scrape)
                else:
                    scraped_content = scrape_with_selenium(urls_to_scrape)

            if not scraped_content and not gen_image_objects:
                self.end_loading()
                self.update_status("Aborted: No valid content or image provided.")
                messagebox.showerror("Validation Error", "No valid content or image was provided to generate the character from. Please provide a URL or an Image Reference.")
                return

            if gen_image_objects:
                self.update_status(f"Loaded {len(gen_image_objects)} image(s) + text content. Ready for generation.")
                
            if self.check_tokens_var.get():
                try:
                    import tiktoken
                    system_text = APIHandler.INSTRUCTIONS
                    full_text = f"{system_text}\n\n{scraped_content}\n\n{instructions}"
                    enc = tiktoken.get_encoding("cl100k_base")
                    token_count = len(enc.encode(full_text))
                    
                    if gen_image_objects:
                        token_count += 350 * len(gen_image_objects) # rough estimate per image input
                        
                    k_tokens = token_count / 1000.0
                    
                    proceed = messagebox.askyesno(
                        "Token Count Estimation",
                        f"The total content is approximately {k_tokens:.1f}K tokens.\n\nDo you want to proceed with generation?"
                    )
                    if not proceed:
                        self.update_status("Cancelled by user after token check.")
                        return
                except ImportError:
                    print("tiktoken not installed, skipping accurate token count check.")
                
            self.update_status(f"Generating character format via {provider.title()} API...")
            response_text = APIHandler.generate_character(
                self.config,
                scraped_content,
                gen_image_objects,
                instructions
            )
            
            character_details = parse_ai_response(response_text)
            if not character_details or not character_details.get("NAME"):
                raise ValueError("No character schema data found in the response. AI output format might be incorrect.")
                
            self.update_status("Processing final character avatar...")
            final_img_path = self.get_final_image_path()
            if not final_img_path or not os.path.exists(final_img_path):
                self.update_status("Final image missing/invalid. Waiting for user selection...")
                final_img_path = self.prompt_for_final_image_choice()
                if not final_img_path or not os.path.exists(final_img_path):
                    self.update_status("Warning: Final image not valid. Falling back to default template.png.")
                    final_img_path = "./template.png"
                
            self.update_status("Saving character dataset locally...")
            os.makedirs(self.config['save_location'], exist_ok=True)
            save_character_card(character_details, final_img_path, self.config['save_location'])
            ImageHandler.cleanup_temp_file(final_img_path)
            
            name = character_details.get('NAME', 'Unknown')
            self.update_status(f"✅ Success! Character '{name}' created and saved in '{self.config['save_location']}'.")
            messagebox.showinfo("Creation Complete", f"Character '{name}' was generated and saved successfully!")
            
        except Exception as e:
            self.update_status(f"❌ Error during generation: {e}")
            messagebox.showerror("Error", str(e))
        finally:
            self.root.after(0, self.end_loading)

    def get_final_image_path(self):
        choice = self.final_img_type_var.get()
        if choice == "default":
            return "./template.png"
        elif choice == "local":
            local_path = self.final_img_val_var.get().strip()
            return local_path if local_path else None
        elif choice == "url":
            url = self.final_img_val_var.get().strip()
            if url:
                return self.download_image_to_temp(url)
        return None

    def download_image_to_temp(self, url):
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, stream=True, timeout=10)
            response.raise_for_status()
            return ImageHandler.save_temp_image(response.content)
        except Exception:
            return None

    def prompt_for_final_image_choice(self):
        """Ask user how to recover when final image is missing/invalid."""
        while True:
            action = messagebox.askyesnocancel(
                "Final Image Required",
                "No valid final character image is set.\n\n"
                "Yes = Enter image URL\n"
                "No = Choose local file\n"
                "Cancel = Use default template image"
            )

            if action is True:
                url = simpledialog.askstring("Image URL", "Enter image URL for the character:", parent=self.root)
                if not url:
                    continue
                img_path = self.download_image_to_temp(url.strip())
                if img_path and os.path.exists(img_path):
                    return img_path
                messagebox.showerror("Invalid URL", "Could not download an image from that URL.")

            elif action is False:
                local_path = filedialog.askopenfilename(
                    title="Choose character image",
                    filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp *.gif *.bmp")]
                )
                if local_path and os.path.exists(local_path):
                    return local_path
                if local_path:
                    messagebox.showerror("Invalid File", "Selected file path is not valid.")

            else:
                return "./template.png"

if __name__ == "__main__":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
        
    root = tk.Tk()
    app = CharMakerTkinterApp(root)
    root.mainloop()