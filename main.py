import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QFileDialog, QListWidget, QLabel, QProgressBar, 
    QMessageBox, QFrame, QMenu
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint, QSize
from PyQt6.QtGui import QFont, QAction, QColor, QPalette
from engine import VideoEngine

class ProcessorThread(QThread):
    progress = pyqtSignal(int, str)
    log_signal = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, intros, body, output_dir):
        super().__init__()
        self.intros = intros
        self.body = body
        self.output_dir = output_dir

    def run(self):
        total_files = len(self.intros)
        engine = VideoEngine()
        
        self.log_signal.emit("Iniciando...")
        
        for i, intro_path in enumerate(self.intros):
            file_name = os.path.basename(intro_path)
            output_name = f"final_{file_name}"
            output_path = os.path.join(self.output_dir, output_name)
            
            def engine_callback(percent, line):
                self.progress.emit(percent, f"Processando {i+1}/{total_files}: {file_name}")

            success, msg = engine.merge_videos(intro_path, self.body, output_path, progress_callback=engine_callback)
            
            if not success:
                self.finished.emit(False, f"Erro em {file_name}: {msg}")
                return
            
        self.finished.emit(True, "Processamento finalizado!")

class VideoMergerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.intro_videos = []
        self.body_video = None
        self.output_directory = ""
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Video Merger Pro")
        self.setMinimumSize(1000, 700)
        
        # Paleta de cores moderna (Zinc/Slate)
        self.setStyleSheet("""
            QMainWindow { background-color: #09090b; }
            QLabel { color: #fafafa; font-family: 'Inter', 'Segoe UI'; }
            
            /* Botões Gerais */
            QPushButton { 
                background-color: #27272a; color: #ffffff; border-radius: 8px; 
                padding: 12px; border: 1px solid #3f3f46; font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #3f3f46; border-color: #52525b; }
            
            /* Botão Principal (Ação) */
            QPushButton#primaryBtn { 
                background-color: #fafafa; color: #09090b; border: none; 
                font-size: 15px; font-weight: 700;
            }
            QPushButton#primaryBtn:hover { background-color: #e4e4e7; }
            QPushButton#primaryBtn:disabled { background-color: #27272a; color: #71717a; }
            
            /* Botão de Risco */
            QPushButton#dangerBtn { 
                background-color: transparent; color: #f87171; border: 1px solid #450a0a;
                padding: 6px 12px; font-size: 11px; font-weight: 500;
            }
            QPushButton#dangerBtn:hover { background-color: #450a0a; }
            
            /* Lista de Vídeos */
            QListWidget { 
                background-color: #09090b; color: #e4e4e7; border-radius: 12px; 
                border: 1px solid #27272a; padding: 10px; font-size: 14px;
                outline: none;
            }
            QListWidget::item { 
                padding: 12px; margin-bottom: 4px; background-color: #18181b;
                border-radius: 8px; border: 1px solid #27272a;
            }
            QListWidget::item:selected { background-color: #27272a; color: white; border-color: #3f3f46; }
            QListWidget::item:hover { background-color: #27272a; }
            
            /* Barra de Progresso */
            QProgressBar { 
                border: none; border-radius: 6px; text-align: center; 
                color: transparent; background-color: #18181b; height: 12px;
            }
            QProgressBar::chunk { background-color: #fafafa; border-radius: 6px; }
            
            /* Containers (Cards) */
            QFrame#sidebar { 
                background-color: #18181b; border-right: 1px solid #27272a;
                min-width: 320px;
            }
            QFrame#main_content { background-color: #09090b; }
            
            QFrame#config_box {
                background-color: #09090b; border-radius: 12px; 
                border: 1px solid #27272a; padding: 15px;
            }
            
            QMenu { background-color: #18181b; color: white; border: 1px solid #27272a; padding: 5px; }
            QMenu::item { padding: 8px 25px; border-radius: 4px; }
            QMenu::item:selected { background-color: #27272a; }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- SIDEBAR (Configurações) ---
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(25, 40, 25, 40)
        sidebar_layout.setSpacing(25)

        title = QLabel("Video Merger")
        title.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        sidebar_layout.addWidget(title)

        # Seção Vídeo de Corpo
        sidebar_layout.addWidget(QLabel("CONFIGURAÇÃO BASE"))
        
        self.body_card = QFrame()
        self.body_card.setObjectName("config_box")
        bc_layout = QVBoxLayout(self.body_card)
        
        self.body_label = QLabel("Nenhum vídeo de corpo")
        self.body_label.setStyleSheet("color: #71717a; font-size: 13px;")
        self.body_label.setWordWrap(True)
        
        btn_select_body = QPushButton("Selecionar Corpo")
        btn_select_body.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_select_body.clicked.connect(self.select_body_video)
        
        bc_layout.addWidget(self.body_label)
        bc_layout.addWidget(btn_select_body)
        sidebar_layout.addWidget(self.body_card)

        # Seção Destino
        sidebar_layout.addWidget(QLabel("DESTINO"))
        
        self.dest_card = QFrame()
        self.dest_card.setObjectName("config_box")
        dc_layout = QVBoxLayout(self.dest_card)
        
        self.dest_label = QLabel("Pasta não selecionada")
        self.dest_label.setStyleSheet("color: #71717a; font-size: 13px;")
        
        btn_select_dest = QPushButton("Escolher Pasta")
        btn_select_dest.clicked.connect(self.select_output_dir)
        
        dc_layout.addWidget(self.dest_label)
        dc_layout.addWidget(btn_select_dest)
        sidebar_layout.addWidget(self.dest_card)

        sidebar_layout.addStretch()
        
        # Info Badge
        info_badge = QLabel("v2.0 Beta • FFmpeg Engine")
        info_badge.setStyleSheet("color: #3f3f46; font-size: 10px;")
        sidebar_layout.addWidget(info_badge)

        layout.addWidget(sidebar)

        # --- MAIN CONTENT (Fila de Vídeos) ---
        main_content = QFrame()
        main_content.setObjectName("main_content")
        main_layout = QVBoxLayout(main_content)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)

        queue_header = QHBoxLayout()
        queue_title = QLabel("Fila de Processamento")
        queue_title.setFont(QFont("Inter", 18, QFont.Weight.DemiBold))
        queue_header.addWidget(queue_title)
        
        self.btn_clear = QPushButton("Limpar Tudo")
        self.btn_clear.setObjectName("dangerBtn")
        self.btn_clear.clicked.connect(self.clear_intro_list)
        queue_header.addWidget(self.btn_clear)
        
        main_layout.addLayout(queue_header)

        self.intro_list = QListWidget()
        self.intro_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.intro_list.customContextMenuRequested.connect(self.show_context_menu)
        
        btn_add = QPushButton("+ Adicionar Vídeos Iniciais")
        btn_add.setObjectName("primaryBtn")
        btn_add.setFixedHeight(55)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.clicked.connect(self.select_intro_videos)
        
        main_layout.addWidget(self.intro_list)
        main_layout.addWidget(btn_add)

        # Footer (Progresso)
        footer = QVBoxLayout()
        footer.setSpacing(10)
        
        self.progress_bar = QProgressBar()
        self.status_label = QLabel("Aguardando arquivos...")
        self.status_label.setStyleSheet("color: #71717a; font-size: 12px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        footer.addWidget(self.progress_bar)
        footer.addWidget(self.status_label)
        
        self.btn_run = QPushButton("🚀 INICIAR PROCESSAMENTO")
        self.btn_run.setObjectName("primaryBtn")
        self.btn_run.setFixedHeight(60)
        self.btn_run.clicked.connect(self.start_processing)
        
        main_layout.addLayout(footer)
        main_layout.addWidget(self.btn_run)

        layout.addWidget(main_content)

    def show_context_menu(self, position: QPoint):
        item = self.intro_list.itemAt(position)
        if item:
            menu = QMenu()
            remove_action = QAction("Remover arquivo", self)
            remove_action.triggered.connect(lambda: self.remove_intro_by_item(item))
            menu.addAction(remove_action)
            menu.exec(self.intro_list.mapToGlobal(position))

    def select_body_video(self):
        file, _ = QFileDialog.getOpenFileName(self, "Vídeo de Corpo", "", "Video Files (*.mp4 *.mkv *.mov *.avi)")
        if file:
            self.body_video = file
            self.body_label.setText(f"✓ {os.path.basename(file)}")
            self.body_label.setStyleSheet("color: #fafafa; font-weight: 500;")

    def select_intro_videos(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Vídeos Iniciais", "", "Video Files (*.mp4 *.mkv *.mov *.avi)")
        if files:
            for f in files:
                if f not in self.intro_videos:
                    self.intro_videos.append(f)
                    info = VideoEngine.get_video_info(f)
                    res = f"{info['width']}x{info['height']}" if info else "???"
                    self.intro_list.addItem(f"{os.path.basename(f)}  •  {res}")
            self.update_ui_state()

    def remove_intro_by_item(self, item):
        index = self.intro_list.row(item)
        self.intro_list.takeItem(index)
        self.intro_videos.pop(index)
        self.update_ui_state()

    def clear_intro_list(self):
        if self.intro_videos:
            self.intro_list.clear()
            self.intro_videos = []
            self.update_ui_state()

    def select_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Pasta de Destino")
        if directory:
            self.output_directory = directory
            self.dest_label.setText(f"✓ {os.path.basename(directory) or directory}")
            self.dest_label.setStyleSheet("color: #fafafa; font-weight: 500;")

    def update_ui_state(self):
        count = len(self.intro_videos)
        if count > 0:
            self.status_label.setText(f"{count} vídeo(s) na fila")
        else:
            self.status_label.setText("Aguardando arquivos...")

    def start_processing(self):
        if not self.body_video or not self.intro_videos or not self.output_directory:
            QMessageBox.warning(self, "Faltam informações", "Selecione o vídeo de corpo, os intros e o destino.")
            return

        self.btn_run.setEnabled(False)
        self.thread = ProcessorThread(self.intro_videos, self.body_video, self.output_directory)
        self.thread.progress.connect(self.update_progress)
        self.thread.finished.connect(self.processing_finished)
        self.thread.start()

    def update_progress(self, val, msg):
        self.progress_bar.setValue(val)
        self.status_label.setText(msg)
        self.status_label.setStyleSheet("color: #fafafa; font-weight: 600;")

    def processing_finished(self, success, msg):
        self.btn_run.setEnabled(True)
        if success:
            QMessageBox.information(self, "Sucesso", "Processamento concluído com êxito!")
            self.clear_all()
        else:
            QMessageBox.critical(self, "Erro", msg)

    def clear_all(self):
        self.intro_videos = []
        self.body_video = None
        self.output_directory = ""
        self.intro_list.clear()
        self.body_label.setText("Nenhum vídeo de corpo")
        self.body_label.setStyleSheet("color: #71717a;")
        self.dest_label.setText("Pasta não selecionada")
        self.dest_label.setStyleSheet("color: #71717a;")
        self.progress_bar.setValue(0)
        self.update_ui_state()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VideoMergerApp()
    window.show()
    sys.exit(app.exec())
