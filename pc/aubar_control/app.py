from concurrent.futures import ThreadPoolExecutor
import logging
from pathlib import Path
from queue import Empty, Queue
import tkinter as tk
from tkinter import ttk

from .protocol import DeviceError
from .session import DeviceSession, available_ports
from .audio import AudioError, MicrophoneCapture, available_inputs
from .recognition import LocalRecognizer, RecognitionError

BG = "#f5f7fc"
INK = "#3e4e65"
MUTED = "#64748b"
PINK = "#ffc2e9"


class AubarApp:
    def __init__(self, root, session=None, port_provider=available_ports,
                 capture=None, audio_provider=available_inputs, recognizer=None):
        self.root = root
        self.session = session or DeviceSession()
        self.port_provider = port_provider
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="aubar-usb")
        self.events = Queue()
        self.capture = capture or MicrophoneCapture()
        self.audio_provider = audio_provider
        self.audio_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="aubar-mic")
        self.audio_events = Queue()
        self.audio_phase = "idle"
        self.audio_scan_busy = False
        self.audio_failed = False
        self.inputs = {}
        self.last_recording = None
        self.recognizer = recognizer or LocalRecognizer()
        self.recognized_action = None
        self.recognition_text = tk.StringVar(value="Todavía no hay una frase reconocida.")
        self.recognition_message = tk.StringVar(value="Probá: «contento», «dormite» o «mirá a la izquierda».")
        self.mic_value = tk.StringVar()
        self.audio_message = tk.StringVar(value="Buscando micrófonos…")
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
        self.refresh_microphones()

    def _build(self):
        self.root.title("Aubar Bot — Panel")
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
        main.rowconfigure(1, weight=1)
        header = ttk.Frame(main)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Aubar Bot", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="Tu compañero de escritorio", style="Muted.TLabel").grid(row=1, column=0, sticky="w")
        icon = tk.Canvas(header, width=120, height=78, bg=BG, highlightthickness=0)
        icon.grid(row=0, column=1, rowspan=2, padx=(20, 0))
        icon.create_oval(10, 37, 48, 68, fill=PINK, outline=PINK)
        icon.create_oval(76, 37, 114, 68, fill=PINK, outline=PINK)
        icon.create_oval(27, 3, 98, 75, fill=PINK, outline=PINK)
        for x in (54, 72):
            icon.create_line(x, 36, x, 51, fill=INK, width=6, capstyle=tk.ROUND)

        notebook = ttk.Notebook(main)
        notebook.grid(row=1, column=0, sticky="nsew")
        device_tab = ttk.Frame(notebook, padding=16)
        microphone_tab = ttk.Frame(notebook, padding=16)
        notebook.add(device_tab, text="Dispositivo")
        notebook.add(microphone_tab, text="Micrófono")
        self._build_microphone(microphone_tab)
        main = device_tab
        main.columnconfigure(0, weight=1)
        main.rowconfigure(7, weight=1)

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

    def _build_microphone(self, panel):
        panel.columnconfigure(0, weight=1)
        ttk.Label(panel, text="Elegí tu micrófono", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 12))
        self.mic_combo = ttk.Combobox(panel, textvariable=self.mic_value, state="readonly")
        self.mic_combo.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        self.mic_combo.bind("<<ComboboxSelected>>", lambda _: self._audio_controls())
        self.mic_scan_button = ttk.Button(panel, text="Buscar micrófonos", command=self.refresh_microphones)
        self.mic_scan_button.grid(row=1, column=1)
        ttk.Label(panel, text="Mantené el botón pulsado mientras hablás. Soltalo para terminar.",
                  wraplength=650).grid(row=2, column=0, columnspan=2, sticky="w", pady=(18, 14))
        self.talk_button = tk.Button(panel, text="Mantené pulsado para hablar", bg=PINK, fg="#35263e",
                                     activebackground="#f2aedc", font=("Segoe UI", 15, "bold"),
                                     relief="flat", padx=20, pady=18, takefocus=True)
        self.talk_button.grid(row=3, column=0, columnspan=2, sticky="ew")
        self.talk_button.bind("<ButtonPress-1>", self.start_recording)
        self.talk_button.bind("<KeyPress-space>", self.start_recording)
        self.root.bind("<ButtonRelease-1>", self.stop_recording, add="+")
        self.root.bind("<KeyRelease-space>", self.stop_recording, add="+")
        self.root.bind("<FocusOut>", self._focus_out, add="+")
        self.root.bind("<Unmap>", lambda e: self.stop_recording() if e.widget is self.root else None, add="+")
        self.audio_label = tk.Label(panel, textvariable=self.audio_message, bg=BG, fg=INK,
                                    font=("Segoe UI", 11), anchor="w", wraplength=650, pady=14)
        self.audio_label.grid(row=4, column=0, columnspan=2, sticky="ew")
        self.level_bar = ttk.Progressbar(panel, maximum=100, mode="determinate")
        self.level_bar.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        ttk.Label(panel, text="Se detiene a los 10 segundos o al salir de la ventana.\n"
                  "Al soltar, la voz se reconoce en esta PC. Todavía no se envían acciones al ESP32.",
                  style="Muted.TLabel", wraplength=650).grid(row=6, column=0, columnspan=2, sticky="w")
        ttk.Label(panel, text="Lo que escuché", style="Section.TLabel").grid(row=7, column=0, columnspan=2, sticky="w", pady=(10, 8))
        tk.Label(panel, textvariable=self.recognition_text, bg="white", fg=INK,
                 font=("Segoe UI", 12), anchor="w", justify="left", wraplength=620,
                 padx=12, pady=8, height=2).grid(row=8, column=0, columnspan=2, sticky="ew")
        ttk.Label(panel, textvariable=self.recognition_message, wraplength=640).grid(row=9, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self._audio_controls()

    def _audio_controls(self):
        idle = self.audio_phase == "idle" and not self.audio_scan_busy
        self.mic_combo.configure(state="readonly" if idle else "disabled")
        self.mic_scan_button.configure(state="normal" if idle else "disabled")
        # Keep the button enabled during recording so it receives release events.
        allowed = not self.audio_scan_busy and self.mic_value.get() in self.inputs and self.audio_phase in ("idle", "starting", "warming", "recording")
        self.talk_button.configure(state="normal" if allowed else "disabled")

    def _audio_submit(self, operation, action):
        def run():
            try:
                self.audio_events.put((operation, action(), None))
            except Exception as error:
                if not isinstance(error, (AudioError, RecognitionError)):
                    logging.exception("Audio operation failed: %s", operation)
                    error = AudioError("No se pudo completar la captura. Revisá el micrófono.")
                self.capture.cancel()
                self.audio_events.put((operation, None, error))
        self.audio_executor.submit(run)

    def refresh_microphones(self):
        if self.audio_phase != "idle" or self.audio_scan_busy or self.closed:
            return
        self.audio_scan_busy = True
        self._audio_controls()
        self._audio_submit("inputs", self.audio_provider)

    def start_recording(self, event=None):
        if self.closed or self.audio_phase != "idle" or self.audio_scan_busy:
            return "break"
        device = self.inputs.get(self.mic_value.get())
        if device is None:
            return "break"
        self.talk_button.focus_set()
        self.last_recording = None
        self.recognized_action = None
        self.recognition_text.set("Esperando la captura…")
        self.recognition_message.set("")
        self.capture.arm()
        self.audio_failed = False
        self.audio_phase = "starting"
        self.audio_message.set("Preparando micrófono… Esperá a «Escuchando» para hablar.")
        self.talk_button.configure(text="Soltá para terminar")
        self._audio_controls()
        self._audio_submit("start", lambda: self.capture.start(device.index))
        return "break"

    def stop_recording(self, event=None):
        if self.closed or self.audio_phase not in ("starting", "warming", "recording"):
            return
        self.capture.cancel()
        self.audio_phase = "stopping"
        self.audio_message.set("Cerrando micrófono…")
        self._audio_controls()
        self._audio_submit("stop", self.capture.finish)

    def _focus_out(self, event):
        def check_focus():
            if not self.closed and self.root.focus_displayof() is None:
                self.stop_recording()
        self.root.after_idle(check_focus)

    def _drain_audio(self):
        try:
            while True:
                operation, result, error = self.audio_events.get_nowait()
                if error:
                    self.audio_failed = True
                    self.audio_phase = "idle"
                    self.audio_scan_busy = False
                    self.last_recording = None
                    self.recognized_action = None
                    self.recognition_text.set("—")
                    self.recognition_message.set(str(error))
                    self.audio_message.set(str(error))
                    self._log(str(error))
                elif operation == "inputs":
                    self.audio_scan_busy = False
                    previous = self.mic_value.get()
                    self.inputs = {device.label: device for device in result}
                    self.mic_combo.configure(values=list(self.inputs))
                    default = next((device.label for device in result if device.is_default), next(iter(self.inputs), ""))
                    self.mic_value.set(previous if previous in self.inputs else default)
                    self.audio_message.set("Micrófono apagado. Listo para capturar." if result else "No hay micrófonos. Conectá uno y buscá de nuevo.")
                elif operation == "start" and self.audio_phase == "starting":
                    if result and self.capture.requested.is_set():
                        self.audio_phase = "warming"
                    else:
                        self.stop_recording()
                elif operation == "stop":
                    self.audio_phase = "idle"
                    if self.audio_failed:
                        self.last_recording = None
                    elif result.duration >= 0.15:
                        self.last_recording = result
                        message = f"Micrófono apagado. Captura lista: {result.duration:.1f} s."
                        if self.capture.limit_reached:
                            message += " Se alcanzó el límite de 10 segundos."
                        if self.capture.overflow:
                            message += " Se perdieron muestras; probá otra entrada."
                        self.audio_message.set(message)
                        self.audio_phase = "recognizing"
                        self.recognition_message.set("Reconociendo la frase…")
                        self.talk_button.configure(text="Reconociendo…")
                        self.level_bar['value'] = 0
                        self._audio_submit("recognized", lambda recording=result: self.recognizer.recognize(recording))
                    else:
                        self.audio_message.set("Micrófono apagado. Captura muy corta; mantené pulsado mientras hablás.")
                        self.recognition_text.set("—")
                        self.recognition_message.set("Captura demasiado corta para reconocer.")
                    self._log(self.audio_message.get())
                elif operation == "recognized":
                    self.audio_phase = "idle"
                    self.recognized_action = result.action
                    self.recognition_text.set(result.text or "—")
                    self.recognition_message.set(result.message)
                if self.audio_phase == "idle":
                    self.talk_button.configure(text="Mantené pulsado para hablar")
                    self.level_bar['value'] = 0
                self._audio_controls()
        except Empty:
            pass
        if self.audio_phase == "warming":
            if self.capture.ready.is_set():
                self.audio_phase = "recording"
            elif self.capture.finished.is_set():
                self.stop_recording()
        if self.audio_phase == "recording":
            self.level_bar['value'] = self.capture.level*100
            self.audio_message.set(f"Escuchando… {self.capture.duration:.1f} / 10 s. Soltá para terminar.")
            if self.capture.limit_reached or self.capture.finished.is_set():
                self.stop_recording()

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
        self._drain_audio()
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
        self.capture.cancel()
        self.last_recording = None
        self.root.after_cancel(self._events_timer)
        self.root.after_cancel(self._poll_timer)
        self.executor.submit(self.session.close)
        self.executor.shutdown(wait=False, cancel_futures=False)
        self.audio_executor.submit(self.capture.finish)
        self.audio_executor.shutdown(wait=False, cancel_futures=False)
        self.root.destroy()


def main():
    log_path = Path(__file__).resolve().parents[1] / "aubar-control.log"
    logging.basicConfig(filename=log_path, encoding="utf-8", level=logging.ERROR)
    root = tk.Tk()
    AubarApp(root)
    root.mainloop()
