from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl
import sys

class SimpleWebViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Web Engine Test")
        self.setGeometry(100, 100, 1024, 768)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)

        # Try loading a well-known website
        self.web_view.setUrl(QUrl("https://www.google.com"))

        self.web_view.page().loadFinished.connect(self.on_load_finished)

    def on_load_finished(self, ok):
        if ok:
            print("Website loaded successfully!")
        else:
            print("Failed to load website. Check internet connection or firewall.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    viewer = SimpleWebViewer()
    viewer.show()
    sys.exit(app.exec())
    