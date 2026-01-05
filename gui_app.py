import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import sys
import os
import json
import logging
from io import StringIO

# Import logic from existing modules
# We wrap imports in try-except to handle potential missing dependencies or errors in those files
try:
    import app as data_collector
    from conversor_csv_a_xlsx import ConversorCSVaXLSX
    from unificador_proyectos import UnificadorProyectos
except ImportError as e:
    print(f"Error importing modules: {e}")

# Configuration for CustomTkinter
ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class TextRedirector(object):
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, str):
        self.widget.configure(state="normal")
        self.widget.insert("end", str, (self.tag,))
        self.widget.see("end")
        self.widget.configure(state="disabled")
        
    def flush(self):
        pass

class SensorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window setup
        self.title("Sensor Data Manager")
        self.geometry("900x600")

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Sensor Manager", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.sidebar_button_1 = ctk.CTkButton(self.sidebar_frame, text="Dashboard", command=self.show_dashboard)
        self.sidebar_button_1.grid(row=1, column=0, padx=20, pady=10)
        
        self.sidebar_button_2 = ctk.CTkButton(self.sidebar_frame, text="Collector", command=self.show_collector)
        self.sidebar_button_2.grid(row=2, column=0, padx=20, pady=10)
        
        self.sidebar_button_3 = ctk.CTkButton(self.sidebar_frame, text="Tools", command=self.show_tools)
        self.sidebar_button_3.grid(row=3, column=0, padx=20, pady=10)

        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"],
                                                                       command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 20))

        # Main Content Area
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        # Initialize Frames
        self.create_dashboard()
        self.create_collector()
        self.create_tools()

        # Default View
        self.show_dashboard()

    def create_dashboard(self):
        self.dashboard_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        
        label = ctk.CTkLabel(self.dashboard_frame, text="Welcome to Sensor Data Manager", font=ctk.CTkFont(size=24))
        label.pack(pady=20)
        
        info = ctk.CTkLabel(self.dashboard_frame, text="Select an option from the sidebar to begin.\n\n"
                                                       "Collector: Download data from API and upload to OneDrive.\n"
                                                       "Tools: Convert to Excel or Unify Projects.",
                                                       font=ctk.CTkFont(size=14))
        info.pack(pady=20)
        
        # Could add summary stats here later reading from logs or config

    def create_collector(self):
        self.collector_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.collector_frame.grid_columnconfigure(0, weight=1)
        
        # Buttons
        btn_frame = ctk.CTkFrame(self.collector_frame)
        btn_frame.pack(fill="x", pady=10)
        
        self.btn_download = ctk.CTkButton(btn_frame, text="Download Data from API", command=self.run_download)
        self.btn_download.pack(side="left", padx=10, pady=10)
        
        self.btn_upload = ctk.CTkButton(btn_frame, text="Upload to OneDrive", command=self.run_upload)
        self.btn_upload.pack(side="left", padx=10, pady=10)
        
        # Log Area
        log_label = ctk.CTkLabel(self.collector_frame, text="Activity Log:")
        log_label.pack(anchor="w", pady=(10, 0))
        
        self.log_textbox = ctk.CTkTextbox(self.collector_frame, width=600, height=400)
        self.log_textbox.pack(fill="both", expand=True, pady=10)
        self.log_textbox.configure(state="disabled")

    def create_tools(self):
        self.tools_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        
        # CSV to Excel
        frame_csv = ctk.CTkFrame(self.tools_frame)
        frame_csv.pack(fill="x", pady=10)
        
        lbl_csv = ctk.CTkLabel(frame_csv, text="CSV to Excel Converter", font=ctk.CTkFont(size=16, weight="bold"))
        lbl_csv.pack(pady=5)
        
        btn_csv = ctk.CTkButton(frame_csv, text="Convert All CSVs in 'datos_unificados'", command=self.run_csv_conversion)
        btn_csv.pack(pady=10)

        # Unify Projects
        frame_unify = ctk.CTkFrame(self.tools_frame)
        frame_unify.pack(fill="x", pady=10)
        
        lbl_unify = ctk.CTkLabel(frame_unify, text="Unify Projects", font=ctk.CTkFont(size=16, weight="bold"))
        lbl_unify.pack(pady=5)
        
        btn_unify = ctk.CTkButton(frame_unify, text="Unify All Project Data", command=self.run_unify)
        btn_unify.pack(pady=10)

    # --- Navigation ---
    def hide_all_frames(self):
        self.dashboard_frame.pack_forget()
        self.collector_frame.pack_forget()
        self.tools_frame.pack_forget()

    def show_dashboard(self):
        self.hide_all_frames()
        self.dashboard_frame.pack(fill="both", expand=True)

    def show_collector(self):
        self.hide_all_frames()
        self.collector_frame.pack(fill="both", expand=True)

    def show_tools(self):
        self.hide_all_frames()
        self.tools_frame.pack(fill="both", expand=True)

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    # --- Logic ---
    def redirect_output(self):
        # Redirect stdout/stderr to the textbox
        sys.stdout = TextRedirector(self.log_textbox, "stdout")
        sys.stderr = TextRedirector(self.log_textbox, "stderr")

    def reset_output(self):
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    def run_download(self):
        self.btn_download.configure(state="disabled")
        threading.Thread(target=self._download_thread).start()

    def _download_thread(self):
        self.redirect_output()
        print("\n--- Starting Data Download ---\n")
        try:
            data_collector.obtener_datos_desde_api()
        except Exception as e:
            print(f"Error: {e}")
        finally:
            print("\n--- Download Finished ---\n")
            self.reset_output()
            self.btn_download.configure(state="normal")

    def run_upload(self):
        self.btn_upload.configure(state="disabled")
        threading.Thread(target=self._upload_thread).start()

    def _upload_thread(self):
        self.redirect_output()
        print("\n--- Starting OneDrive Upload ---\n")
        try:
            data_collector.subir_archivos_a_onedrive()
        except Exception as e:
            print(f"Error: {e}")
        finally:
            print("\n--- Upload Finished ---\n")
            self.reset_output()
            self.btn_upload.configure(state="normal")

    def run_csv_conversion(self):
        threading.Thread(target=self._csv_thread).start()

    def _csv_thread(self):
        # We need a way to show output for this too, maybe a separate log window or popup
        # For now let's just use print and hope the user looks at the console if running via terminal, 
        # OR we can add a log area to the Tools tab too. 
        # Better yet, popup message when done.
        
        # Because we want to see progress, let's redirect to the collector log for now or create a popup log
        pass 
        # Actually, let's just make the "Tools" run in the background and pop up a message
        try:
            conversor = ConversorCSVaXLSX()
            conversor.convertir_todos()
            self.after(0, lambda: messagebox.showinfo("Success", "Conversion Completed!"))
        except Exception as e:
             self.after(0, lambda: messagebox.showerror("Error", str(e)))

    def run_unify(self):
        threading.Thread(target=self._unify_thread).start()

    def _unify_thread(self):
        try:
            unificador = UnificadorProyectos()
            unificador.ejecutar_unificacion()
            self.after(0, lambda: messagebox.showinfo("Success", "Unification Completed!"))
        except Exception as e:
             self.after(0, lambda: messagebox.showerror("Error", str(e)))

if __name__ == "__main__":
    app = SensorApp()
    app.mainloop()
