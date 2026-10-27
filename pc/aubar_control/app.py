from concurrent.futures import ThreadPoolExecutor
import logging
from pathlib import Path
from queue import Empty, Queue
import tkinter as tk
from tkinter import ttk

from .protocol import DeviceError
from .session import DeviceSession, available_ports

BG = "#f5f7fc"
INK = "#3e4e65"
MUTED = "#64748b"
PINK = "#ffc2e9"


class AubarApp:
    def __init__(self, root, session=None, port_provider=available_ports):
        self.root = root
        self.session = session or DeviceSession()
        self.port_provider = port_provider
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="aubar-usb")
        self.events = Queue()
        self.connected = False
        self.busy = False
        self.closed = False
        self.ports = {}
        self.active_port = None
        self.port_value = tk.StringVar()
        self.banner_value = tk.StringVar(value="Buscando puertos…")
        self.values = {key: tk.StringVar(value="—") for key in ("expression", "mode", "look")}
        self._build()
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._events_timer = root.after(80, self._drain)
        self._poll_timer = root.after(1500, self._poll)
        self.refresh_ports()

    def _build(self):
        self.root.title("Aubar Bot — Conexión")
        height = max(650, min(740, self.root.winfo_screenheight()-120))
        self.root.geometry(f"820x{height}")
        self.root.minsize(760, 650)
        self.root.configure(bg=BG)
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=INK, font=("Segoe UI", 11))
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("Title.TLabel", font=("Segoe UI", 28, "bold"))
        style.configure("Section.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("TButton", padding=(14, 9), font=("Segoe UI", 10), foreground=INK)
        style.configure("Primary.TButton", background=PINK, foreground="#35263e", borderwidth=0)
        style.map("Primary.TButton", background=[("active", "#f2aedc"), ("disabled", "#e8eaf0")])
        style.configure("TCombobox", padding=8, font=("Segoe UI", 10))
        style.configure("Value.TLabel", background="white", font=("Segoe UI", 18, "bold"))
        style.configure("Caption.TLabel", background="white", foreground=MUTED)

        main = ttk.Frame(self.root, padding=30)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(7, weight=1)
        header = ttk.Frame(main)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Aubar Bot", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="Panel de conexión", style="Muted.TLabel").grid(row=1, column=0, sticky="w")
        icon = tk.Canvas(header, width=120, height=78, bg=BG, highlightthickness=0)
        icon.grid(row=0, column=1, rowspan=2, padx=(20, 0))
        icon.create_oval(10, 37, 48, 68, fill=PINK, outline=PINK)
        icon.create_oval(76, 37, 114, 68, fill=PINK, outline=PINK)
        icon.create_oval(27, 3, 98, 75, fill=PINK, outline=PINK)
        for x in (54, 72):
            icon.create_line(x, 36, x, 51, fill=INK, width=6, capstyle=tk.ROUND)

        connection = ttk.Frame(main)
        connection.grid(row=1, column=0, sticky="ew")
        connection.columnconfigure(0, weight=1)
        ttk.Label(connection, text="Puerto USB", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.port_combo = ttk.Combobox(connection, textvariable=self.port_value, state="readonly")
        self.port_combo.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        self.port_combo.bind("<<ComboboxSelected>>", lambda _: self._controls())
        self.scan_button = ttk.Button(connection, text="Buscar puertos", command=self.refresh_ports)
        self.scan_button.grid(row=1, column=1)
        buttons = ttk.Frame(main)
        buttons.grid(row=2, column=0, sticky="ew", pady=(12, 12))
        self.connect_button = ttk.Button(buttons, text="Conectar", style="Primary.TButton", command=self.connect)
        self.connect_button.pack(side="left", padx=(0, 8))
        self.disconnect_button = ttk.Button(buttons, text="Desconectar", command=self.disconnect)
        self.disconnect_button.pack(side="left")
        self.status_button = ttk.Button(buttons, text="Consultar estado", command=self.refresh_status)
        self.status_button.pack(side="right")
        self.banner = tk.Label(main, textvariable=self.banner_value, bg="#e8eef8", fg=INK,
                               anchor="w", padx=14, pady=12, font=("Segoe UI", 10), wraplength=680)
        self.banner.grid(row=3, column=0, sticky="ew", pady=(0, 20))

        ttk.Label(main, text="En la pantalla", style="Section.TLabel").grid(row=4, column=0, sticky="w", pady=(0, 8))
        state = tk.Frame(main, bg="white", highlightbackground="#dfe5ef", highlightthickness=1)
        state.grid(row=5, column=0, sticky="ew")
        for column, (key, title) in enumerate((("expression", "Expresión"), ("mode", "Modo"), ("look", "Mirada"))):
            state.columnconfigure(column, weight=1, uniform="status")
            ttk.Label(state, text=title, style="Caption.TLabel").grid(row=0, column=column, sticky="w", padx=18, pady=(14, 3))
            ttk.Label(state, textvariable=self.values[key], style="Value.TLabel").grid(row=1, column=column, sticky="w", padx=18, pady=(0, 16))

        ttk.Label(main, text="Actividad", style="Section.TLabel").grid(row=6, column=0, sticky="w", pady=(20, 8))
        self.activity = tk.Text(main, height=5, state="disabled", bg="white", fg=INK,
                                font=("Segoe UI", 10), relief="flat", padx=12, pady=10,
                                wrap="word", highlightthickness=1, highlightbackground="#dfe5ef")
        self.activity.grid(row=7, column=0, sticky="nsew")
        ttk.Label(main, text="Cerrá el monitor serie de Arduino antes de conectar.", style="Muted.TLabel").grid(row=8, column=0, sticky="w", pady=(12, 0))
        self._controls()

    def _controls(self):
        def enable(widget, allowed):
            widget.configure(state="normal" if allowed else "disabled")
        enable(self.connect_button, not self.busy and not self.connected and self.port_value.get() in self.ports)
        enable(self.disconnect_button, not self.busy and self.connected)
        enable(self.status_button, not self.busy and self.connected)
        enable(self.scan_button, not self.busy and not self.connected)
        self.port_combo.configure(state="readonly" if not self.busy and not self.connected else "disabled")

    def _message(self, text, error=False):
        self.banner_value.set(text)
        self.banner.configure(bg="#fbe8ed" if error else "#e8eef8", fg="#942b45" if error else INK)

    def _log(self, text):
        self.activity.configure(state="normal")
        self.activity.insert("end", text+"\n")
        if int(self.activity.index("end-1c").split(".")[0]) > 80:
            self.activity.delete("1.0", "2.0")
        self.activity.see("end")
        self.activity.configure(state="disabled")

    def _submit(self, operation, action):
        if self.busy or self.closed:
            return
        self.busy = True
        self._controls()
        def run():
            try:
                self.events.put((operation, action(), None))
            except Exception as error:
                self.session.close()
                if not isinstance(error, DeviceError):
                    logging.exception("Desktop operation failed: %s", operation)
                    error = DeviceError("No se pudo completar la operación. Volvé a conectar el dispositivo.")
                self.events.put((operation, None, error))
        self.executor.submit(run)

    def refresh_ports(self):
        self._submit("ports", self.port_provider)

    def connect(self):
        port = self.ports.get(self.port_value.get())
        if port:
            self._message(f"Conectando con {port.device}…")
            self._submit("connect", lambda: (port.device, self.session.connect(port.device)))

    def disconnect(self):
        self._submit("disconnect", self.session.close)

    def refresh_status(self):
        self._submit("status", self.session.status)

    def _clear_state(self):
        for value in self.values.values():
            value.set("—")

    def _apply_status(self, status):
        self.values["expression"].set(status.expression.capitalize())
        self.values["mode"].set("Automático" if status.mode == "auto" else "Manual")
        self.values["look"].set(status.look.capitalize())

    def _drain(self):
        try:
            while True:
                operation, result, error = self.events.get_nowait()
                self.busy = False
                if error:
                    self.connected = False
                    self.active_port = None
                    self._clear_state()
                    self._message(str(error), error=True)
                    self._log(str(error))
                elif operation == "ports":
                    previous = self.port_value.get()
                    self.ports = {port.label: port for port in result}
                    self.port_combo.configure(values=list(self.ports))
                    selected = next((port.label for port in result if port.is_esp32), next(iter(self.ports), ""))
                    self.port_value.set(previous if previous in self.ports else selected)
                    self._message("Elegí el puerto y conectá tu ESP32." if result else "No hay puertos. Conectá el cable USB y buscá de nuevo.")
                elif operation == "connect":
                    self.active_port, status = result
                    self.connected = True
                    self._apply_status(status)
                    self._message(f"Conectado a {self.active_port}. El estado se actualiza automáticamente.")
                    self._log(f"Conexión confirmada con Aubar Bot en {self.active_port}.")
                elif operation in ("status", "poll"):
                    self._apply_status(result)
                    if operation == "status":
                        self._log("Estado del dispositivo actualizado.")
                elif operation == "disconnect":
                    self.connected = False
                    self.active_port = None
                    self._clear_state()
                    self._message("Sin conexión. Podés seleccionar un puerto y volver a conectar.")
                    self._log("Puerto liberado. La placa mantiene su modo de funcionamiento.")
                self._controls()
        except Empty:
            pass
        if not self.closed:
            self._events_timer = self.root.after(80, self._drain)

    def _poll(self):
        if self.connected and not self.busy:
            self._submit("poll", self.session.status)
        if not self.closed:
            self._poll_timer = self.root.after(1500, self._poll)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.root.after_cancel(self._events_timer)
        self.root.after_cancel(self._poll_timer)
        self.executor.submit(self.session.close)
        self.executor.shutdown(wait=False, cancel_futures=False)
        self.root.destroy()


def main():
    log_path = Path(__file__).resolve().parents[1] / "aubar-control.log"
    logging.basicConfig(filename=log_path, encoding="utf-8", level=logging.ERROR)
    root = tk.Tk()
    AubarApp(root)
    root.mainloop()
