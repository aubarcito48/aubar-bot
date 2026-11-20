"""Aubar's Qt workspace: two docks, conversation and a movable portrait."""
import html
import time

from PySide6.QtCore import Qt, QTimer, QSettings, Signal, QPoint
from PySide6.QtGui import QAction, QColor, QFont, QImage, QPainter, QPixmap, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QDockWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QToolButton, QComboBox, QCheckBox, QSlider, QTextBrowser,
    QPlainTextEdit, QMenu, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsItem, QFrame, QSizePolicy, QToolBar, QScrollArea,
)

from ...models.avatar.catalog import EXPRESSIONS, ANIMATIONS
from ...models.avatar.portrait import PortraitPlayer
from ...services.recognition.voice_commands import VoiceAction
from ...services.desktop.runtime import DesktopRuntime


STYLE = """
QMainWindow, QWidget#workspace { background: #101925; color: #e8edf3; }
QWidget { color: #e8edf3; font-family: 'Segoe UI'; font-size: 13px; }
QDockWidget { color: #bbc9d8; font-weight: 600; }
QDockWidget::title { background: #192536; padding: 10px; border-bottom: 1px solid #304054; }
QWidget#dockBody { background: #162131; }
QLabel#section { color: #edf3f7; font-weight: 600; margin-top: 15px; }
QLabel#muted { color: #a7b7ca; }
QLabel#brand { font-size: 24px; font-weight: 700; color: #edf3f7; padding: 8px; }
QLabel#state { color: #73dccb; padding: 8px; }
QToolBar { background: #142030; border: 0; border-bottom: 1px solid #304054; spacing: 7px; padding: 8px; }
QToolButton, QPushButton { background: #233247; border: 1px solid #3b5069; border-radius: 7px; padding: 8px 11px; }
QToolButton:hover, QPushButton:hover { background: #30465c; border-color: #73dccb; }
QPushButton#primary { background: #69d6c4; color: #10232b; font-weight: 600; border-color: #69d6c4; }
QPushButton:disabled { color: #91a1b3; background: #1b2736; border-color: #28394b; }
QComboBox, QPlainTextEdit, QTextBrowser { background: #101b29; border: 1px solid #3b5069; border-radius: 7px; padding: 8px; selection-background-color: #386b76; }
QComboBox { min-height: 23px; }
QComboBox QAbstractItemView { background: #1c2a3d; selection-background-color: #386b76; }
QCheckBox { spacing: 8px; padding-top: 8px; padding-bottom: 8px; }
QCheckBox::indicator { width: 16px; height: 16px; }
QSlider::groove:horizontal { height: 4px; background: #354961; border-radius: 2px; }
QSlider::handle:horizontal { background: #73dccb; width: 14px; margin: -5px 0; border-radius: 7px; }
QScrollArea { border: 0; background: #162131; }
QScrollBar:vertical { background: #142030; width: 10px; }
QScrollBar::handle:vertical { background: #425b73; min-height: 24px; border-radius: 4px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QMainWindow::separator { background: #304054; width: 3px; height: 3px; }
QStatusBar { background: #142030; color: #a7b7ca; }
QMenu { background: #1b293b; border: 1px solid #425b73; padding: 6px; }
QMenu::item { padding: 8px 20px; }
QMenu::item:selected { background: #30465c; }
QPushButton:focus, QToolButton:focus, QComboBox:focus, QPlainTextEdit:focus { border-color: #73dccb; }
"""


class Composer(QPlainTextEdit):
    sendRequested = Signal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            if not event.isAutoRepeat():
                self.sendRequested.emit()
            return
        super().keyPressEvent(event)


class AvatarView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('avatarView')
        scene = QGraphicsScene(self)
        self.setScene(scene)
        self.item = QGraphicsPixmapItem()
        self.item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        scene.addItem(self.item)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet('background: transparent; border: none;')
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._centered = False
        self.item.setScale(1.2)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.setSceneRect(0, 0, max(1, self.viewport().width()), max(1, self.viewport().height()))
        if not self._centered:
            self.center_avatar()

    def center_avatar(self):
        bounds = self.item.boundingRect()
        self.item.setPos(max(0, (self.viewport().width()-bounds.width()*self.item.scale())/2),
                         max(0, (self.viewport().height()-bounds.height()*self.item.scale())/2))

    def set_image(self, image):
        self.item.setPixmap(QPixmap.fromImage(image))
        if not self._centered:
            self.center_avatar()
            self._centered = True


class MascotWindow(QWidget):
    restoreRequested = Signal()
    listeningRequested = Signal(bool)
    stopVoiceRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle('Aubar · Mascota')
        self.setToolTip('Arrastrá para mover · clic derecho para volver al panel')
        self.resize(258, 480)
        self.image = QImage()
        self.drag_offset = None
        self.listening_enabled = False
        self.status_until = 0.0
        self.status_label = QLabel(self)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.status_label.setStyleSheet('background: #162131; color: #73dccb; border: 1px solid #3b5069; border-radius: 7px; padding: 5px; font-size: 12px;')
        self.set_status('Micrófono desactivado')

    def set_status(self, text, *, hold=0):
        if hold:
            self.status_until = time.monotonic()+hold
        self.status_label.setText(text)
        self.setToolTip(text+'\nArrastrá para mover · clic derecho para ver opciones')
        self.status_label.setGeometry(6, 6, max(1, self.width()-12), 58)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.status_label.setGeometry(6, 6, max(1, self.width()-12), 58)

    def paintEvent(self, event):
        if not self.image.isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawImage(self.rect(), self.image)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = event.globalPosition().toPoint()-self.pos()

    def mouseMoveEvent(self, event):
        if self.drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint()-self.drag_offset)

    def mouseReleaseEvent(self, event):
        self.drag_offset = None

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction('Volver al espacio de trabajo', self.restoreRequested.emit)
        listening = menu.addAction('Escucha automática')
        listening.setCheckable(True)
        listening.setChecked(self.listening_enabled)
        listening.triggered.connect(self.listeningRequested.emit)
        menu.addAction('Detener voz', self.stopVoiceRequested.emit)
        menu.addSeparator()
        menu.addAction('Más pequeño', lambda: self.resize(172, 320))
        menu.addAction('Más grande', lambda: self.resize(344, 640))
        menu.exec(event.globalPos())

    def closeEvent(self, event):
        self.restoreRequested.emit()
        event.accept()


class AubarWindow(QMainWindow):
    def __init__(self, runtime=None, *, scan=True, settings=None):
        super().__init__()
        self.runtime = runtime or DesktopRuntime()
        self.settings = settings or QSettings('Aubar', 'Desktop')
        self.player = None
        self.current_image = QImage()
        self.last_error = ''
        self.closed = False
        self.setObjectName('aubarDesktop')
        self.setWindowTitle('Aubar · Tu asistente personal')
        self.resize(1280, 860)
        self.setMinimumSize(820, 650)
        self.setDockOptions(QMainWindow.DockOption.AnimatedDocks | QMainWindow.DockOption.AllowNestedDocks)
        self.setStyleSheet(STYLE)
        self._build_workspace()
        self._build_connections()
        self._build_devices()
        self._build_chat()
        self._build_toolbar()
        self.mascot = MascotWindow()
        self.mascot.restoreRequested.connect(self.restore_workspace)
        self.mascot.listeningRequested.connect(self.auto.setChecked)
        self.mascot.stopVoiceRequested.connect(self.runtime.stop_voice)
        self.statusBar().showMessage('Tus mensajes se conservan solo durante esta sesión.')
        self._restore_layout()
        try:
            self.player = PortraitPlayer()
        except (OSError, ValueError, KeyError, IndexError) as error:
            self.avatar_hint.setText('No se pudo cargar el retrato. Revisá el banco de imágenes del firmware.')
            self.last_error = str(error)
        self.timer = QTimer(self)
        self.timer.setInterval(42)
        self.timer.timeout.connect(self.tick)
        self.timer.start()
        if scan:
            self.runtime.scan()

    def label(self, text, section=False):
        label = QLabel(text)
        label.setObjectName('section' if section else 'muted')
        label.setWordWrap(True)
        return label

    def button(self, text, callback, primary=False):
        button = QPushButton(text)
        if primary:
            button.setObjectName('primary')
        button.clicked.connect(callback)
        return button

    def dock(self, name, key, area):
        dock = QDockWidget(name, self)
        dock.setObjectName(key)
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable |
                         QDockWidget.DockWidgetFeature.DockWidgetMovable |
                         QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        body = QWidget()
        body.setObjectName('dockBody')
        layout = QVBoxLayout(body)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)
        dock.setWidget(body)
        self.addDockWidget(area, dock)
        return dock, body, layout

    def _build_workspace(self):
        workspace = QWidget()
        workspace.setObjectName('workspace')
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(24, 12, 24, 12)
        row = QHBoxLayout()
        self.state = QLabel('Listo para conversar')
        self.state.setObjectName('state')
        row.addWidget(self.state)
        row.addStretch()
        row.addWidget(self.button('Centrar avatar', lambda: self.avatar.center_avatar()))
        layout.addLayout(row)
        self.avatar = AvatarView()
        layout.addWidget(self.avatar, 1)
        self.avatar_hint = self.label('Arrastrá a Aubar para moverlo. Plegá los paneles para darle más espacio.')
        self.avatar_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.avatar_hint)
        self.setCentralWidget(workspace)

    def _build_connections(self):
        self.connections_dock, body, layout = self.dock('Conexiones', 'connectionsDock', Qt.DockWidgetArea.LeftDockWidgetArea)
        body.setMinimumWidth(210)
        body.setMaximumWidth(420)
        layout.addWidget(self.label('Conversación e información', True))
        self.config_label = self.label('Leyendo configuración local…')
        layout.addWidget(self.config_label)
        layout.addWidget(self.button('Recargar configuración', self.reload))
        layout.addWidget(self.label('Portfolio', True))
        layout.addWidget(self.label('Consultá los proyectos y la experiencia publicados.'))
        layout.addWidget(self.button('Consultar portfolio', lambda: self.prompt('¿Qué proyectos tiene Nahuel en su portfolio?')))
        layout.addWidget(self.label('WhatsApp', True))
        self.whatsapp_state = self.label('Control local sin configurar')
        layout.addWidget(self.whatsapp_state)
        self.inbox = QTextBrowser()
        self.inbox.setObjectName('whatsappInbox')
        self.inbox.setMaximumHeight(130)
        self.inbox.setPlaceholderText('Los mensajes nuevos de contactos autorizados aparecerán acá.')
        self.inbox.setOpenExternalLinks(False)
        layout.addWidget(self.inbox)
        layout.addWidget(self.button('Consultar mensajes', lambda: self.prompt('¿Qué mensajes recientes tengo en WhatsApp?')))
        self.read_notices = QCheckBox('Leer notificaciones en voz alta')
        layout.addWidget(self.read_notices)
        layout.addWidget(self.label('YouTube', True))
        layout.addWidget(self.button('Buscar un video', lambda: self.prompt('Buscá en YouTube ')))
        layout.addStretch()
        layout.addWidget(self.label('Próximamente: correo y cámara. Sus conexiones todavía no están implementadas.'))

    def _build_devices(self):
        self.devices_dock, body, layout = self.dock('Dispositivos y actuación', 'devicesDock', Qt.DockWidgetArea.RightDockWidgetArea)
        body.setMinimumWidth(220)
        body.setMaximumWidth(420)
        layout.addWidget(self.label('ESP32 · opcional', True))
        self.ports = QComboBox()
        self.ports.setAccessibleName('Puerto del ESP32')
        layout.addWidget(self.ports)
        row = QHBoxLayout()
        self.connect_button = self.button('Conectar', self.connect_device)
        self.disconnect_button = self.button('Desconectar', self.runtime.disconnect)
        row.addWidget(self.connect_button)
        row.addWidget(self.disconnect_button)
        layout.addLayout(row)
        self.device_state = self.label('Usando el avatar de la PC')
        layout.addWidget(self.device_state)
        layout.addWidget(self.label('Micrófono', True))
        self.inputs = QComboBox()
        self.inputs.setAccessibleName('Micrófono de entrada')
        layout.addWidget(self.inputs)
        self.auto = QCheckBox('Escucha automática')
        self.auto.toggled.connect(self.toggle_auto)
        layout.addWidget(self.auto)
        self.record = self.button('Hablar', self.toggle_record)
        layout.addWidget(self.record)
        self.mic_level = self.label('Micrófono desactivado')
        layout.addWidget(self.mic_level)
        layout.addWidget(self.button('Buscar dispositivos', self.runtime.scan))
        layout.addWidget(self.label('Voz · Kokoro / Onyx', True))
        self.voice = QCheckBox('Escuchar las respuestas')
        self.voice.setChecked(True)
        self.voice.toggled.connect(self.set_voice)
        layout.addWidget(self.voice)
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(80)
        self.volume.setAccessibleName('Volumen de Aubar')
        self.volume.valueChanged.connect(lambda value: setattr(self.runtime, 'volume', value))
        layout.addWidget(self.volume)
        layout.addWidget(self.label('Salida: dispositivo de audio predeterminado de Windows.'))
        layout.addWidget(self.button('Detener voz', self.runtime.stop_voice))
        layout.addWidget(self.label('Actuación', True))
        self.expressions = QComboBox()
        self.expressions.setAccessibleName('Expresión o animación de Aubar')
        for kind, catalog in (('EXPRESSION', EXPRESSIONS), ('ANIMATION', ANIMATIONS)):
            for identifier, label in catalog.items():
                self.expressions.addItem(('Cara · ' if kind == 'EXPRESSION' else 'Gesto · ')+label, (kind, identifier, label))
        layout.addWidget(self.expressions)
        layout.addWidget(self.button('Mostrar gesto', self.select_expression))
        self.zoom = QSlider(Qt.Orientation.Horizontal)
        self.zoom.setRange(60, 220)
        self.zoom.setValue(120)
        self.zoom.setAccessibleName('Tamaño del avatar')
        self.zoom.valueChanged.connect(lambda value: self.avatar.item.setScale(value/100))
        layout.addWidget(self.zoom)
        layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        self.devices_dock.setWidget(scroll)

    def _build_chat(self):
        self.chat_dock, body, layout = self.dock('Conversación', 'chatDock', Qt.DockWidgetArea.BottomDockWidgetArea)
        self.chat = QTextBrowser()
        self.chat.setObjectName('conversationHistory')
        self.chat.setAccessibleName('Conversación con Aubar')
        self.chat.setOpenLinks(False)
        self.chat.setMinimumHeight(70)
        layout.addWidget(self.chat, 1)
        row = QHBoxLayout()
        self.composer = Composer()
        self.composer.setObjectName('messageComposer')
        self.composer.setAccessibleName('Mensaje para Aubar')
        self.composer.setPlaceholderText('Escribile a Aubar… Enter para enviar · Shift+Enter para otra línea')
        self.composer.setMaximumHeight(70)
        self.composer.sendRequested.connect(self.send)
        row.addWidget(self.composer, 1)
        self.send_button = self.button('Enviar', self.send, True)
        self.send_button.setObjectName('primary')
        row.addWidget(self.send_button)
        row.addWidget(self.button('Cancelar', self.runtime.cancel))
        self.actions_button = QToolButton()
        self.actions_button.setText('Acciones')
        self.actions_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self.actions_button)
        menu.addAction('Nueva conversación', self.runtime.reset)
        menu.addAction('Escuchar última respuesta', lambda: self.runtime.speak())
        menu.addAction('Consultar portfolio', lambda: self.prompt('¿Qué proyectos tiene Nahuel en su portfolio?'))
        menu.addAction('Consultar WhatsApp', lambda: self.prompt('¿Qué mensajes recientes tengo en WhatsApp?'))
        menu.addSeparator()
        menu.addAction('Detener voz', self.runtime.stop_voice)
        self.actions_button.setMenu(menu)
        row.addWidget(self.actions_button)
        layout.addLayout(row)
        self.append('Aubar', 'Hola, Nahuel. Podés escribirme o activar el micrófono. Mis conexiones se configuran en el panel izquierdo.')

    def _build_toolbar(self):
        toolbar = QToolBar('Espacio de trabajo', self)
        toolbar.setObjectName('workspaceToolbar')
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        brand = QLabel('Aubar')
        brand.setObjectName('brand')
        toolbar.addWidget(brand)
        for dock in (self.connections_dock, self.devices_dock, self.chat_dock):
            toolbar.addAction(dock.toggleViewAction())
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        toolbar.addAction('Restaurar diseño', self.reset_layout)
        toolbar.addAction('Modo mascota', self.show_mascot)

    def _restore_layout(self):
        geometry = self.settings.value('geometry')
        state = self.settings.value('layout')
        if geometry:
            self.restoreGeometry(geometry)
        if state:
            self.restoreState(state)
        else:
            self.resizeDocks([self.connections_dock, self.devices_dock], [245, 265], Qt.Orientation.Horizontal)
            self.resizeDocks([self.chat_dock], [245], Qt.Orientation.Vertical)

    def reset_layout(self):
        for dock, area in ((self.connections_dock, Qt.DockWidgetArea.LeftDockWidgetArea),
                           (self.devices_dock, Qt.DockWidgetArea.RightDockWidgetArea),
                           (self.chat_dock, Qt.DockWidgetArea.BottomDockWidgetArea)):
            dock.setFloating(False)
            self.addDockWidget(area, dock)
            dock.show()
        self.resizeDocks([self.connections_dock, self.devices_dock], [245, 265], Qt.Orientation.Horizontal)
        self.resizeDocks([self.chat_dock], [245], Qt.Orientation.Vertical)
        self.avatar.center_avatar()

    def show_mascot(self):
        if self.player is None:
            self.state.setText('El retrato no está disponible. Revisá sus archivos antes de usar la miniatura.')
            return
        screen = self.screen().availableGeometry()
        self.mascot.move(screen.right()-self.mascot.width()-24, screen.bottom()-self.mascot.height()-24)
        self.mascot.image = self.current_image
        self._update_mascot_status()
        self.mascot.show()
        self.hide()

    def restore_workspace(self):
        self.mascot.hide()
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def append(self, author, text):
        color = '#73dccb' if author == 'Aubar' else '#b9c9e0'
        safe = html.escape(text).replace('\n', '<br>')
        self.chat.append(f'<p style="margin:8px 0"><b style="color:{color}">{html.escape(author)}</b><br>{safe}</p>')
        self.chat.moveCursor(QTextCursor.MoveOperation.End)

    def prompt(self, text):
        self.chat_dock.show()
        self.composer.setPlainText(text)
        self.composer.setFocus()
        self.composer.moveCursor(QTextCursor.MoveOperation.End)

    def send(self):
        if self.runtime.send(self.composer.toPlainText()):
            self.composer.clear()

    def reload(self):
        self.runtime.reload()

    def connect_device(self):
        port = self.ports.currentData()
        if port:
            self.runtime.connect(port)

    def toggle_auto(self, enabled):
        self.runtime.set_auto(enabled, self.inputs.currentData())

    def toggle_record(self):
        if self.runtime.recording:
            self.runtime.finish_recording()
        else:
            self.runtime.start_recording(self.inputs.currentData())

    def set_voice(self, enabled):
        self.runtime.voice = enabled
        if not enabled:
            self.runtime.stop_voice()

    def select_expression(self):
        kind, identifier, label = self.expressions.currentData()
        self.runtime.select(VoiceAction(kind, identifier, label))

    def _event(self, kind, value):
        if kind in ('user', 'assistant'):
            self.append('Vos' if kind == 'user' else 'Aubar', value)
        elif kind == 'clear':
            self.chat.clear()
        elif kind in ('status', 'error'):
            self.state.setText(value)
            self.mascot.set_status(value, hold=8 if kind == 'error' else 3)
            if kind == 'error':
                self.last_error = value
                self.append('Aviso', value)
        elif kind == 'config':
            self.config_label.setText('Groq · texto / Director local · actuación\n'+value)
            config = self.runtime.config
            self.whatsapp_state.setText('Puente configurado · comprobando conexión' if config and config.whatsapp_control_url else 'Control local sin configurar')
        elif kind == 'visual':
            if self.player:
                self.player.select(value)
        elif kind == 'speaking':
            if self.player:
                self.player.set_speaking(value)
        elif kind == 'recognized':
            self.statusBar().showMessage('Reconocido: '+value, 12000)
        elif kind == 'voice_rejected':
            text, message = value
            self.append('Micrófono', 'Frase reconocida: '+text+'\n'+message)
        elif kind == 'device':
            self.device_state.setText('ESP32 conectado · PC y placa' if value else 'Usando el avatar de la PC')
        elif kind in ('ports', 'inputs'):
            combo = self.ports if kind == 'ports' else self.inputs
            selected = combo.currentData()
            combo.clear()
            for item in value:
                combo.addItem(item.label, item.device if kind == 'ports' else item.index)
            index = combo.findData(selected)
            if index < 0 and kind == 'inputs':
                index = next((i for i, item in enumerate(value) if item.is_default), 0)
            combo.setCurrentIndex(max(0, index))
        elif kind == 'whatsapp':
            status, events, missed = value
            self.whatsapp_state.setText('Puente conectado' if status == 'connected' else 'Puente no disponible · reintentando')
            for event in events:
                name = event['name'] or 'Contacto …'+event['sender'][-4:]
                self.inbox.append(html.escape(name+': '+event['text']).replace('\n', '<br>'))
                if self.read_notices.isChecked() and self.runtime.voice and not self.runtime.busy and not self.runtime.speech.busy:
                    from ...models.avatar.ai_avatar import normalize_reply
                    self.runtime.speak(normalize_reply(('Mensaje de '+name+': '+event['text'])[:1800]))
            if missed:
                self.inbox.append('Hay mensajes anteriores fuera de la ventana del puente. Revisá WhatsApp.')

    def _update_mascot_status(self):
        runtime = self.runtime
        self.mascot.listening_enabled = runtime.auto
        if time.monotonic() < self.mascot.status_until:
            return
        if runtime.speech.articulating:
            text = 'Hablando…'
        elif runtime.speech.busy:
            text = 'Preparando la voz…'
        elif runtime.busy:
            text = self.state.text()
        elif runtime.recording:
            text = 'Grabando una frase…'
        elif runtime.auto_starting:
            text = 'Preparando micrófono…'
        elif runtime.auto_ready and runtime.automatic.listening.is_set():
            text = ('Calibrando micrófono…' if runtime.automatic.calibrating else
                    'Te escucho…' if runtime.automatic.speaking else 'Escuchando · podés hablar')
        elif runtime.auto:
            text = 'Escucha en pausa · esperando audio'
        else:
            text = 'Micrófono desactivado · clic derecho'
        self.mascot.set_status(text)

    def tick(self):
        for kind, value in self.runtime.tick():
            self._event(kind, value)
        self.send_button.setEnabled(not self.runtime.busy)
        self.connect_button.setEnabled(not self.runtime.connected and self.ports.count() > 0)
        self.disconnect_button.setEnabled(self.runtime.connected)
        self.record.setText('Terminar' if self.runtime.recording else 'Hablar')
        self.record.setEnabled(self.inputs.count() > 0 and (self.runtime.recording or not self.runtime.busy and not self.runtime.auto))
        self.inputs.setEnabled(not self.runtime.recording and not self.runtime.auto)
        if self.auto.isChecked() != self.runtime.auto:
            self.auto.blockSignals(True)
            self.auto.setChecked(self.runtime.auto)
            self.auto.blockSignals(False)
        self.mic_level.setText('Escucha automática activa' if self.runtime.auto else 'Grabando…' if self.runtime.recording else 'Micrófono desactivado')
        self._update_mascot_status()
        if self.player:
            try:
                data = self.player.render()
                if data is not None:
                    bank = self.player.bank
                    self.current_image = QImage(data, bank.width, bank.height, bank.width*4, QImage.Format.Format_RGBA8888).copy()
                    self.avatar.set_image(self.current_image)
                    if self.mascot.isVisible():
                        self.mascot.image = self.current_image
                        self.mascot.update()
            except (ValueError, IndexError, KeyError):
                self.state.setText('No se pudo reproducir el retrato. Revisá el banco de imágenes.')
                self.player = None

    def closeEvent(self, event):
        if not self.closed:
            self.closed = True
            self.timer.stop()
            self.settings.setValue('geometry', self.saveGeometry())
            self.settings.setValue('layout', self.saveState())
            self.mascot.hide()
            self.mascot.deleteLater()
            self.runtime.close()
        event.accept()


def main():
    app = QApplication.instance() or QApplication([])
    app.setApplicationName('Aubar Desktop')
    app.setOrganizationName('Aubar')
    app.setFont(QFont('Segoe UI', 10))
    window = AubarWindow()
    window.show()
    return app.exec()
