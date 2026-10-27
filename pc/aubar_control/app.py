from concurrent.futures import ThreadPoolExecutor, CancelledError
import logging
import time
from pathlib import Path
from queue import Empty, Queue
import tkinter as tk
from tkinter import ttk

from .protocol import DeviceError
from .session import DeviceSession, available_ports
from .audio import AudioError, MicrophoneCapture, available_inputs
from .recognition import LocalRecognizer, RecognitionError
from .catalog import EXPRESSIONS, ANIMATIONS
from .voice_commands import VoiceAction
from .automatic_audio import AutomaticCapture
from .speech import SpeechEngine, SpeechError, SpeechCancelled
from .responses import confirmation_text

BG = "#f5f7fc"
INK = "#3e4e65"
MUTED = "#64748b"
PINK = "#ffc2e9"


class AubarApp:
    def __init__(self, root, session=None, port_provider=available_ports,
                 capture=None, audio_provider=available_inputs, recognizer=None, automatic_capture=None, speech=None,
                 reply_provider=confirmation_text):
        self.root = root
        self.session = session or DeviceSession()
        self.port_provider = port_provider
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="aubar-usb")
        self.events = Queue()
        self.capture = capture or MicrophoneCapture()
        self.automatic_capture = automatic_capture or AutomaticCapture(self.capture.backend)
        self.speech = speech or SpeechEngine()
        self.speech_enabled = tk.BooleanVar(value=True)
        self.speech_volume = tk.DoubleVar(value=80)
        self.speech_volume_label = tk.StringVar(value="80 %")
        self.speech_message = tk.StringVar(value="Lista para probar la voz en español.")
        self.speech_voice = tk.StringVar(value="Se usará la voz en español de Windows.")
        self._speech_future = None
        self._speech_stop_requested = False
        self._speech_is_test = False
        self.reply_provider = reply_provider
        self._pending_reply = None
        self._speech_response_token = None
        self._speech_was_automatic = False
        self._speech_resume_at = 0
        self.auto_enabled = tk.BooleanVar(value=False)
        self.auto_generation = 0
        self.auto_running = False
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
        self.recognition_message = tk.StringVar(value="Probá «enojado derecha» o «celebrar izquierda». En automática, empezá con «Aubar».")
        self.mic_value = tk.StringVar()
        self.audio_message = tk.StringVar(value="Buscando micrófonos…")
        self.connected = False
        self.busy = False
        self.closed = False
        self.ports = {}
        self.active_port = None
        self.connection_token = 0
        self.capture_connection_token = None
        self.pending_action = None
        self.voice_inflight = False
        self.port_value = tk.StringVar()
        self.banner_value = tk.StringVar(value="Buscando puertos…")
        self.values = {key: tk.StringVar(value="—") for key in ("expression", "mode", "look")}
        self.animation_value = tk.StringVar(value="Animación: —")
        self.catalog_message = tk.StringVar(value="Conectá el ESP32 para elegir una expresión o una animación.")
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
        speech_tab = ttk.Frame(notebook, padding=16)
        notebook.add(speech_tab, text="Voz")
        self._build_speech(speech_tab)
        catalog_tab = ttk.Frame(notebook, padding=16)
        notebook.add(catalog_tab, text="Catálogo")
        self._build_catalog(catalog_tab)
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
            ttk.Label(state, textvariable=self.values[key], style="Value.TLabel", wraplength=200).grid(row=1, column=column, sticky="w", padx=18, pady=(0, 16))
        ttk.Label(state, textvariable=self.animation_value, style="Caption.TLabel").grid(row=2, column=0, columnspan=3, sticky="w", padx=18, pady=(0, 12))

        ttk.Label(main, text="Actividad", style="Section.TLabel").grid(row=6, column=0, sticky="w", pady=(20, 8))
        self.activity = tk.Text(main, height=5, state="disabled", bg="white", fg=INK,
                                font=("Segoe UI", 10), relief="flat", padx=12, pady=10,
                                wrap="word", highlightthickness=1, highlightbackground="#dfe5ef")
        self.activity.grid(row=7, column=0, sticky="nsew")
        ttk.Label(main, text="Cerrá el monitor serie de Arduino antes de conectar.", style="Muted.TLabel").grid(row=8, column=0, sticky="w", pady=(12, 0))
        self._controls()

    def _build_speech(self, panel):
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(4, weight=1)
        heading = ttk.Frame(panel)
        heading.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        heading.columnconfigure(0, weight=1)
        ttk.Label(heading, text="La voz de Aubar", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(heading, textvariable=self.speech_voice, style="Muted.TLabel",
                  wraplength=540).grid(row=1, column=0, sticky="w", pady=(6, 0))
        icon=tk.Canvas(heading,width=70,height=60,bg=BG,highlightthickness=0)
        icon.grid(row=0,column=1,rowspan=2,padx=(16,0))
        icon.create_oval(3,3,57,57,fill=PINK,outline=PINK)
        icon.create_polygon(15,25,23,25,33,17,33,43,23,35,15,35,fill=INK)
        icon.create_arc(28,18,48,42,start=-60,extent=120,style="arc",outline=INK,width=3)
        self.speech_check=ttk.Checkbutton(panel,text="Activar voz",variable=self.speech_enabled,
                                         command=self.toggle_speech)
        self.speech_check.grid(row=1,column=0,sticky="w",pady=(0,10))
        volume=ttk.Frame(panel)
        volume.grid(row=2,column=0,sticky="ew",pady=(0,12))
        volume.columnconfigure(0,weight=1)
        ttk.Label(volume,text="Volumen").grid(row=0,column=0,sticky="w")
        ttk.Label(volume,textvariable=self.speech_volume_label).grid(row=0,column=1,sticky="e")
        self.speech_volume_scale=ttk.Scale(volume,from_=0,to=100,variable=self.speech_volume,
                                           command=self._speech_volume_changed)
        self.speech_volume_scale.grid(row=1,column=0,columnspan=2,sticky="ew",pady=(8,0))
        ttk.Label(panel,text="Texto para probar").grid(row=3,column=0,sticky="w",pady=(0,8))
        self.speech_text=tk.Text(panel,height=3,wrap="word",font=("Segoe UI",12),fg=INK,
                                 bg="white",padx=12,pady=10,relief="flat",
                                 highlightthickness=1,highlightbackground="#dfe5ef")
        self.speech_text.insert("1.0","Hola, soy Aubar. Esta es mi voz en español. Podés ajustar el volumen y detener esta prueba desde el panel.")
        self.speech_text.grid(row=4,column=0,sticky="nsew")
        buttons=ttk.Frame(panel)
        buttons.grid(row=5,column=0,sticky="ew",pady=(10,10))
        self.speech_test_button=ttk.Button(buttons,text="Probar voz",style="Primary.TButton",
                                          command=self.test_speech)
        self.speech_test_button.pack(side="left",padx=(0,10))
        self.speech_stop_button=ttk.Button(buttons,text="Detener",command=self.stop_speech)
        self.speech_stop_button.pack(side="left")
        self.speech_status=tk.Label(panel,textvariable=self.speech_message,bg="#e8eef8",fg=INK,
                                    anchor="w",justify="left",font=("Segoe UI",11),
                                    padx=14,pady=8,wraplength=650)
        self.speech_status.grid(row=6,column=0,sticky="ew")
        self.speech_hint=ttk.Label(panel,text="La prueba usa la salida de audio predeterminada de Windows.",
                                   style="Muted.TLabel",wraplength=650)
        self.speech_hint.grid(row=7,column=0,sticky="w",pady=(8,0))
        self._speech_controls()

    def _speech_volume_changed(self, value=None):
        self.speech_volume_label.set(f"{round(self.speech_volume.get())} %")

    def _speech_controls(self):
        active=self._speech_future is not None or self.speech.busy
        enabled=self.speech_enabled.get()
        microphone_busy=self.auto_enabled.get() or self.audio_phase!='idle'
        self.speech_test_button.configure(state="normal" if enabled and not active and not microphone_busy else "disabled")
        self.speech_stop_button.configure(state="normal" if active and not self._speech_stop_requested else "disabled")
        self.speech_volume_scale.configure(state="normal" if enabled and not active else "disabled")
        self.speech_text.configure(state="normal" if enabled and not active else "disabled")
        if microphone_busy:
            self.speech_hint.configure(text="Apagá la escucha automática o terminá la captura para probar la voz.")
        else:
            self.speech_hint.configure(text="La prueba usa la salida de audio predeterminada de Windows.")

    def _speech_message(self, text, error=False):
        self.speech_message.set(text)
        self.speech_status.configure(bg="#fbe8ed" if error else "#e8eef8",fg="#942b45" if error else INK)

    def test_speech(self):
        if not self.closed:
            self.speak_text(self.speech_text.get("1.0","end-1c"),is_test=True)

    def speak_text(self, text, *, is_test=False, allow_automatic=False):
        if self.closed or not self.speech_enabled.get() or self._speech_future is not None or self.speech.busy:
            return False
        if (self.auto_enabled.get() and not allow_automatic) or self.audio_phase!='idle':
            self._speech_message("Apagá la escucha automática o terminá la captura antes de probar la voz.")
            return False
        self._speech_was_automatic=self.auto_enabled.get() and self.auto_running
        if self._speech_was_automatic:
            self.automatic_capture.pause()
        try:
            self._speech_future=self.speech.speak(text,volume=round(self.speech_volume.get()))
        except SpeechError as error:
            self._speech_was_automatic=False
            self._speech_message(str(error),error=True)
            return False
        self._speech_is_test=is_test
        self._speech_stop_requested=False
        self._speech_message("Hablando…" if is_test else "Hablando: "+text)
        self._audio_controls()
        return True

    def stop_speech(self):
        self._pending_reply=None
        if self.closed or not self.speech.busy and self._speech_future is None:
            return
        self._speech_stop_requested=True
        self.speech.stop()
        self._speech_message("Deteniendo la voz…")
        self._speech_controls()

    def toggle_speech(self):
        if not self.speech_enabled.get():
            self._pending_reply=None
            self.stop_speech()
            if self._speech_future is None and not self.speech.busy:
                self._speech_message("Voz desactivada.")
        elif self._speech_future is None:
            self._speech_message("Lista para probar la voz en español.")
        self._speech_controls()

    def _drain_speech(self):
        future=self._speech_future
        if future is None or not future.done():
            return
        self._speech_future=None
        try:
            voice=future.result()
        except (CancelledError,SpeechCancelled):
            self._speech_message("Voz desactivada." if not self.speech_enabled.get() else "Reproducción detenida.")
        except Exception as error:
            if self._speech_stop_requested:
                self._speech_message("Voz desactivada." if not self.speech_enabled.get() else "Reproducción detenida.")
            else:
                if not isinstance(error,SpeechError):
                    logging.exception("Speech playback failed")
                self._speech_message(str(error) if isinstance(error,SpeechError) else
                                     "No se pudo reproducir la voz. Revisá la salida de audio.",error=True)
        else:
            self.speech_voice.set(f"Voz: {voice.name} ({voice.language})")
            self._speech_message(("Prueba de voz finalizada." if self._speech_is_test else "Reproducción finalizada.") if not self._speech_stop_requested else
                                 "Voz desactivada." if not self.speech_enabled.get() else "Reproducción detenida.")
        self._speech_stop_requested=False
        self._speech_response_token=None
        if self._speech_was_automatic:
            self._speech_resume_at=time.monotonic()+.35
        self._speech_was_automatic=False
        self._audio_controls()

    def _queue_confirmed_reply(self, action, token):
        if self.closed or not self.speech_enabled.get() or not self.connected or token!=self.connection_token:
            return
        try:
            text=self.reply_provider(action)
        except Exception:
            logging.exception("Could not build confirmed speech response")
            self._speech_message("La acción se confirmó, pero no se pudo preparar su respuesta hablada.",error=True)
            return
        if isinstance(text,str) and text.strip():
            self._pending_reply=(token,text)

    def _drain_reply(self):
        if self._pending_reply is None:
            return
        token,text=self._pending_reply
        if self.closed or not self.speech_enabled.get() or not self.connected or token!=self.connection_token:
            self._pending_reply=None
            return
        if self.audio_phase!='idle' or self._speech_future is not None or self.speech.busy:
            return
        self._pending_reply=None
        if self.speak_text(text,allow_automatic=True):
            self._speech_response_token=token
            self._log('Aubar: '+text)

    def _build_catalog(self, panel):
        panel.columnconfigure(0, weight=1)
        ttk.Label(panel, text="El avatar completo", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Label(panel, text="28 expresiones · 23 animaciones", style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(0, 20))
        self.catalog_buttons = []
        self.catalog_choices = {}
        for row, (kind, title, catalog) in enumerate((
            ('EXPRESSION', 'Expresión fija', EXPRESSIONS),
            ('ANIMATION', 'Animación en bucle', ANIMATIONS))):
            base=2+row*3
            ttk.Label(panel, text=title).grid(row=base, column=0, sticky="w", pady=(0, 6))
            selected=tk.StringVar(value=next(iter(catalog.values())))
            choices={label: identifier for identifier, label in catalog.items()}
            self.catalog_choices[kind]=(selected, choices)
            ttk.Combobox(panel, textvariable=selected, values=list(choices), state="readonly").grid(row=base+1, column=0, sticky="ew", padx=(0, 12))
            button=ttk.Button(panel, text="Mostrar" if row==0 else "Reproducir",
                command=lambda k=kind: self.apply_catalog(k), style="Primary.TButton")
            button.grid(row=base+1, column=1, pady=(0, 20))
            self.catalog_buttons.append(button)
        demo=ttk.Button(panel, text="Recorrer todas las animaciones", command=lambda: self.apply_catalog('MODE'))
        demo.grid(row=8, column=0, sticky="w", pady=(4, 16))
        self.catalog_buttons.append(demo)
        ttk.Label(panel, textvariable=self.catalog_message, wraplength=650).grid(row=9, column=0, columnspan=2, sticky="w")
        ttk.Label(panel, text="Voz: «pensar», «reír», «celebrar», «dormir»…\n"
                  "También: «Aubar, enojado derecha» o «Aubar, celebrar izquierda».\n"
                  "Para una pose fija: «expresión tímido» o «expresión cejas enojadas».\n"
                  "BOOT adelanta la animación; en una expresión fija, pasa a la siguiente.",
                  style="Muted.TLabel", wraplength=650).grid(row=10, column=0, columnspan=2, sticky="w", pady=(20, 0))

    def apply_catalog(self, kind):
        if self.closed or self.busy or self.speech.busy or self._pending_reply is not None or not self.connected or self.audio_phase!='idle':
            return
        if kind=='MODE':
            action=VoiceAction('MODE', 'auto', 'Todas las animaciones')
        else:
            selected, choices=self.catalog_choices[kind]
            identifier=choices.get(selected.get())
            if identifier is None:
                return
            action=VoiceAction(kind, identifier, selected.get())
        token=self.connection_token
        self.catalog_message.set('Enviando al ESP32…')
        self._submit('catalog', lambda: (token, action, self.session.apply_action(action)))

    def _build_microphone(self, panel):
        panel.columnconfigure(0, weight=1)
        ttk.Label(panel, text="Elegí tu micrófono", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 12))
        self.mic_combo = ttk.Combobox(panel, textvariable=self.mic_value, state="readonly")
        self.mic_combo.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        self.mic_combo.bind("<<ComboboxSelected>>", lambda _: self._audio_controls())
        self.mic_scan_button = ttk.Button(panel, text="Buscar micrófonos", command=self.refresh_microphones)
        self.mic_scan_button.grid(row=1, column=1)
        modes = ttk.Frame(panel)
        modes.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 8))
        self.auto_check = ttk.Checkbutton(modes, text="Escucha automática · «Aubar» + comando",
            variable=self.auto_enabled, command=self.toggle_automatic)
        self.auto_check.pack(anchor="w")
        ttk.Label(modes, text="Automática: hablá y hacé una pausa. Manual: mantené pulsado el botón.",
                  style="Muted.TLabel", wraplength=650).pack(anchor="w", pady=(6, 0))
        self.talk_button = tk.Button(panel, text="Mantené pulsado para hablar", bg=PINK, fg="#35263e",
                                     activebackground="#f2aedc", font=("Segoe UI", 13, "bold"),
                                     relief="flat", padx=20, pady=12, takefocus=True)
        self.talk_button.grid(row=3, column=0, columnspan=2, sticky="ew")
        self.talk_button.bind("<ButtonPress-1>", self.start_recording)
        self.talk_button.bind("<KeyPress-space>", self.start_recording)
        self.root.bind("<ButtonRelease-1>", self.stop_recording, add="+")
        self.root.bind("<KeyRelease-space>", self.stop_recording, add="+")
        self.root.bind("<FocusOut>", self._focus_out, add="+")
        self.root.bind("<Unmap>", lambda e: self.stop_recording() if e.widget is self.root else None, add="+")
        self.audio_label = tk.Label(panel, textvariable=self.audio_message, bg=BG, fg=INK,
                                    font=("Segoe UI", 11), anchor="w", wraplength=650, pady=8)
        self.audio_label.grid(row=4, column=0, columnspan=2, sticky="ew")
        self.level_bar = ttk.Progressbar(panel, maximum=100, mode="determinate")
        self.level_bar.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        ttk.Label(panel, text="Automática sigue al minimizar; apagá la casilla para cerrar el micrófono.\n"
                  "Una pausa de 0,8 s termina la frase. Manual se detiene al soltar o salir.",
                  style="Muted.TLabel", wraplength=650).grid(row=6, column=0, columnspan=2, sticky="w")
        ttk.Label(panel, text="Lo que escuché", style="Section.TLabel").grid(row=7, column=0, columnspan=2, sticky="w", pady=(10, 8))
        tk.Label(panel, textvariable=self.recognition_text, bg="white", fg=INK,
                 font=("Segoe UI", 12), anchor="w", justify="left", wraplength=620,
                 padx=12, pady=8, height=2).grid(row=8, column=0, columnspan=2, sticky="ew")
        ttk.Label(panel, textvariable=self.recognition_message, wraplength=640).grid(row=9, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self._audio_controls()

    def _audio_controls(self):
        idle = self.audio_phase == "idle" and not self.audio_scan_busy and not self.auto_enabled.get()
        self.mic_combo.configure(state="readonly" if idle else "disabled")
        self.mic_scan_button.configure(state="normal" if idle else "disabled")
        # Keep the button enabled during recording so it receives release events.
        allowed = not self.speech.busy and not self.auto_enabled.get() and not self.voice_inflight and not self.audio_scan_busy and self.mic_value.get() in self.inputs and self.audio_phase in ("idle", "starting", "warming", "recording")
        self.talk_button.configure(state="normal" if allowed else "disabled")
        auto_allowed = self.auto_enabled.get() or (idle and not self.speech.busy and not self.voice_inflight and self.connected and self.mic_value.get() in self.inputs)
        self.auto_check.configure(state="normal" if auto_allowed else "disabled")
        if hasattr(self, 'catalog_buttons'):
            for button in self.catalog_buttons:
                button.configure(state="normal" if self.connected and not self.busy and not self.speech.busy and self._pending_reply is None and self.audio_phase=="idle" else "disabled")
        self._speech_controls()

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
        if self.auto_enabled.get() or self.audio_phase != "idle" or self.audio_scan_busy or self.closed:
            return
        self.audio_scan_busy = True
        self._audio_controls()
        self._audio_submit("inputs", self.audio_provider)

    def start_recording(self, event=None):
        if self.speech.busy or self.voice_inflight or self.auto_enabled.get() or self.closed or self.audio_phase != "idle" or self.audio_scan_busy:
            return "break"
        device = self.inputs.get(self.mic_value.get())
        if device is None:
            return "break"
        self.talk_button.focus_set()
        self.last_recording = None
        self.capture_connection_token = self.connection_token if self.connected else None
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
                if operation.startswith('auto_'):
                    self._handle_automatic_event(operation, result, error)
                    self._audio_controls()
                    continue
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
                    if result.action is not None:
                        if self.connected and self.capture_connection_token == self.connection_token:
                            self.pending_action = (self.connection_token, result.action)
                            self.audio_phase = 'sending'
                            self.recognition_message.set('Enviando la orden al ESP32…')
                            self.talk_button.configure(text='Esperando confirmación…')
                        else:
                            self.recognition_message.set('Acción no enviada. Conectá el ESP32 y repetí la frase.')
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

    def toggle_automatic(self):
        if not self.auto_enabled.get():
            self.stop_automatic()
            return
        device = self.inputs.get(self.mic_value.get())
        if self.speech.busy or self.voice_inflight or self.closed or not self.connected or device is None or self.audio_phase!='idle':
            self.auto_enabled.set(False)
            self._audio_controls()
            return
        self.auto_generation += 1
        generation = self.auto_generation
        self.automatic_capture.arm()
        self.audio_phase = 'auto_starting'
        self.audio_message.set('Preparando escucha automática…')
        self.recognition_message.set('Decí «Aubar, enojado derecha» o «Aubar, celebrar izquierda» cuando esté lista.')
        self._audio_controls()
        self._audio_submit('auto_start', lambda: (generation, self.automatic_capture.start(device.index)))

    def stop_automatic(self, message='Escucha automática apagada. Micrófono cerrado.'):
        self.auto_enabled.set(False)
        self.auto_generation += 1
        generation = self.auto_generation
        self.auto_running = False
        self.automatic_capture.cancel()
        self.automatic_capture.pause()
        self.capture_connection_token = None
        self.pending_action = None
        self.audio_phase = 'auto_stopping'
        self.audio_message.set('Cerrando escucha automática…')
        self._audio_controls()
        def finish():
            self.automatic_capture.finish()
            return generation, message
        self._audio_submit('auto_stop', finish)

    def _handle_automatic_event(self, operation, result, error):
        if error is not None:
            if operation=='auto_stop':
                self.auto_enabled.set(False)
                self.auto_running = False
                self.audio_phase = 'idle'
                self.audio_message.set(str(error))
            else:
                self.stop_automatic(str(error))
            self._log(str(error))
            return
        generation, value = result
        if generation!=self.auto_generation:
            return
        if operation=='auto_stop':
            self.audio_phase = 'idle'
            self.audio_message.set(value)
            self.level_bar['value'] = 0
            return
        if not self.auto_enabled.get():
            return
        if operation=='auto_start':
            if not value:
                self.stop_automatic('No se pudo iniciar la escucha automática.')
                return
            self.auto_running = True
            self.audio_phase = 'idle'
        elif operation=='auto_recognized':
            # The existing sender still checks the live connection token and
            # waits for the device acknowledgment. Nothing is retried.
            self.audio_events.put(('recognized', value, None))

    def _tick_automatic(self):
        if not self.auto_enabled.get() or not self.auto_running or self.closed:
            return
        capture = self.automatic_capture
        if capture.finished.is_set() or not capture.requested.is_set():
            self.stop_automatic('El micrófono se desconectó. Revisá la entrada y activá la escucha de nuevo.')
            return
        if self._speech_future is not None or self.speech.busy or self._pending_reply is not None or time.monotonic()<self._speech_resume_at:
            capture.pause()
            self.level_bar['value']=0
            self.audio_message.set('Escucha en pausa mientras Aubar responde…')
            return
        try:
            recording = capture.utterances.get_nowait()
        except Empty:
            recording = None
        if isinstance(recording, AudioError):
            self.stop_automatic(str(recording))
            return
        if recording is not None:
            generation = self.auto_generation
            self.capture_connection_token = self.connection_token
            self.last_recording = None  # No continuous audio retained by the UI.
            self.recognized_action = None
            self.audio_phase = 'auto_recognizing'
            self.audio_message.set('Frase terminada. Reconociendo…')
            self.level_bar['value'] = 0
            self.recognition_text.set('Procesando la voz…')
            self.recognition_message.set('Comprobando «Aubar» y el comando…')
            self._audio_controls()
            self._audio_submit('auto_recognized', lambda: (
                generation, self.recognizer.recognize_automatic(recording)))
            return
        if self.audio_phase=='idle' and not self.busy and self.pending_action is None:
            if not capture.ready.is_set():
                self.audio_message.set('Preparando micrófono…')
                return
            capture.resume()
            self.level_bar['value'] = capture.level*100
            self.audio_message.set('Calibrando ruido ambiente… Esperá un instante sin hablar.' if capture.calibrating else
                                   'Voz detectada. Hacé una pausa al terminar…' if capture.speaking else
                                   'Escucha automática activa. Decí «Aubar» seguido de un comando.')

    def _controls(self):
        def enable(widget, allowed):
            widget.configure(state="normal" if allowed else "disabled")
        enable(self.connect_button, not self.busy and not self.connected and self.port_value.get() in self.ports)
        enable(self.disconnect_button, not self.busy and self.connected)
        enable(self.status_button, not self.busy and self.connected)
        enable(self.scan_button, not self.busy and not self.connected)
        self.port_combo.configure(state="readonly" if not self.busy and not self.connected else "disabled")
        for button in self.catalog_buttons:
            enable(button, self.connected and not self.busy and not self.speech.busy and self._pending_reply is None and self.audio_phase=="idle")
        self._audio_controls()

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
        if port and not self.busy:
            self._invalidate_connection()
            self._message(f"Conectando con {port.device}…")
            self._submit("connect", lambda: (port.device, self.session.connect(port.device)))

    def disconnect(self):
        if self.busy:
            return
        self._invalidate_connection()
        self._submit("disconnect", self.session.close)

    def _invalidate_connection(self):
        self.connection_token += 1
        self._pending_reply=None
        if self._speech_response_token is not None:
            self.stop_speech()
        if self.pending_action is not None or self.audio_phase == 'sending':
            self.recognition_message.set('Orden descartada por desconexión. Reconectá y repetí la frase.')
            self.audio_phase = 'idle'
            self.talk_button.configure(text='Mantené pulsado para hablar')
        self.pending_action = None
        if self.auto_enabled.get() or self.auto_running:
            self.stop_automatic('Escucha apagada por desconexión. Reconectá y activala de nuevo.')
        self._audio_controls()

    def _dispatch_voice(self):
        if self.pending_action is None or self.busy or self.closed:
            return
        token, action = self.pending_action
        self.pending_action = None
        if not self.connected or token != self.connection_token:
            self.audio_phase = 'idle'
            self.recognition_message.set('Acción no enviada. Reconectá y repetí la frase.')
            self.talk_button.configure(text='Mantené pulsado para hablar')
            self._audio_controls()
            return
        self.voice_inflight = True
        self._submit('voice', lambda: (token, action, self.session.apply_action(action)))

    def refresh_status(self):
        self._submit("status", self.session.status)

    def _clear_state(self):
        self.animation_value.set("Animación: —")
        for value in self.values.values():
            value.set("—")

    def _apply_status(self, status):
        self.values["expression"].set(EXPRESSIONS.get(status.expression, status.expression.capitalize()))
        self.animation_value.set("Animación: "+ANIMATIONS.get(status.animation, "Ninguna"))
        self.values["mode"].set("Automático" if status.mode == "auto" else "Manual")
        self.values["look"].set(status.look.capitalize())

    def _drain(self):
        try:
            while True:
                operation, result, error = self.events.get_nowait()
                self.busy = False
                if operation=='voice':
                    self.voice_inflight = False
                if error:
                    self._invalidate_connection()
                    self.connected = False
                    self.active_port = None
                    self._clear_state()
                    self._message(str(error), error=True)
                    self._log(str(error))
                    if operation == 'voice':
                        self.recognition_message.set(str(error))
                    if operation == 'catalog':
                        self.catalog_message.set(str(error))
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
                elif operation in ('voice', 'catalog'):
                    token, action, status = result
                    confirmed=token == self.connection_token and self.connected
                    if confirmed:
                        self._apply_status(status)
                        if operation=='catalog':
                            self.catalog_message.set(f'{action.label}. Confirmado por el ESP32.')
                        else:
                            self.recognition_message.set(f'{action.label}. Confirmado por el ESP32.')
                        self._log(f'{action.label}. Confirmado por el ESP32.')
                    if operation=='voice':
                        if self.audio_phase=='sending':
                            self.audio_phase = 'idle'
                        self.talk_button.configure(text='Mantené pulsado para hablar')
                    if confirmed:
                        self._queue_confirmed_reply(action,token)
                    self._audio_controls()
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
        self._drain_speech()
        self._drain_reply()
        self._tick_automatic()
        self._dispatch_voice()
        if not self.closed:
            self._events_timer = self.root.after(80, self._drain)

    def _poll(self):
        if self.connected and not self.busy and self.pending_action is None:
            self._submit("poll", self.session.status)
        if not self.closed:
            self._poll_timer = self.root.after(1500, self._poll)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self._pending_reply=None
        self.speech.close()
        self.auto_enabled.set(False)
        self.auto_generation += 1
        self.automatic_capture.cancel()
        self.pending_action = None
        self.capture.cancel()
        self.last_recording = None
        self.root.after_cancel(self._events_timer)
        self.root.after_cancel(self._poll_timer)
        self.executor.submit(self.session.close)
        self.executor.shutdown(wait=False, cancel_futures=False)
        self.audio_executor.submit(self.capture.finish)
        self.audio_executor.submit(self.automatic_capture.finish)
        self.audio_executor.shutdown(wait=False, cancel_futures=False)
        self.root.destroy()


def main():
    log_path = Path(__file__).resolve().parents[1] / "aubar-control.log"
    logging.basicConfig(filename=log_path, encoding="utf-8", level=logging.ERROR)
    root = tk.Tk()
    AubarApp(root)
    root.mainloop()
