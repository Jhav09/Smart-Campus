from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, QObject, Signal, Slot
import os
import json # To pass Python data to JavaScript

# For Python-JavaScript communication, you'll need this:
from PySide6.QtWebChannel import QWebChannel

class CampusMapWidget(QWidget):
    # Signal to emit when a marker is clicked (for Python-JS communication)
    marker_clicked_signal = Signal(str, str) # Emits (id, title)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.web_view = QWebEngineView()
        self.layout.addWidget(self.web_view)

        # Build the path to your HTML map file
        # This path assumes map_assets is a sibling to the ui folder
        current_dir = os.path.dirname(os.path.abspath(__file__))
        map_html_path = os.path.join(current_dir, '..', 'map_assets', 'campus_map.html')
        
        # Check if the file exists
        if not os.path.exists(map_html_path):
            print(f"Error: Map HTML file not found at {map_html_path}")
            # You might want to display an error in the UI here
            return

        # Load the local HTML file
        self.web_view.setUrl(QUrl.fromLocalFile(map_html_path))

        # --- Setup Python-JavaScript communication (QWebChannel) ---
        # This allows JavaScript to call Python methods
        self.channel = QWebChannel(self.web_view.page())
        
        # Create a Python object to expose to JavaScript
        self.python_bridge = PythonMapBridge()
        self.python_bridge.marker_clicked_signal.connect(self._handle_marker_click)
        
        # Expose the Python object under the name 'pythonBridge' in JavaScript
        self.channel.registerObject("pythonBridge", self.python_bridge)
        self.web_view.page().setWebChannel(self.channel)

        # Connect to load finished signal to inject data after map is ready
        self.web_view.page().loadFinished.connect(self.on_load_finished)

    def on_load_finished(self, ok):
        if ok:
            print("Map loaded successfully!")
            # Example: Add some dummy buildings/rooms after the map loads
            # In a real scenario, you'd fetch this data from your MySQL database
            dummy_locations = [
                {"id": "bldg_eng", "name": "Engineering Building", "latitude": 24.4530, "longitude": 54.3760},
                {"id": "room_a101", "name": "Lecture Hall A101", "latitude": 24.4550, "longitude": 54.3780},
                {"id": "sports_center", "name": "Sports Center", "latitude": 24.4510, "longitude": 54.3790},
                {"id": "lib_main", "name": "Main Library", "latitude": 24.4545, "longitude": 54.3770},
            ]
            self.add_locations_to_map(dummy_locations)
        else:
            print("Failed to load map.")

    def add_locations_to_map(self, locations):
        """
        Adds a list of locations (buildings/rooms) to the map.
        Locations should be a list of dicts with 'id', 'name', 'latitude', 'longitude'.
        """
        if locations:
            # Convert the Python list of dicts to a JSON string for JavaScript
            json_locations = json.dumps(locations)
            # Call the JavaScript function 'addMarkers' in the HTML
            self.web_view.page().runJavaScript(f"addMarkers({json_locations});")
            print(f"Injected {len(locations)} locations into map.")

    @Slot(str, str)
    def _handle_marker_click(self, marker_id, marker_title):
        """Internal slot to handle marker clicks from JavaScript."""
        print(f"Python received marker click: ID={marker_id}, Title={marker_title}")
        # Emit a public signal that other parts of your app can connect to
        self.marker_clicked_signal.emit(marker_id, marker_title)


class PythonMapBridge(QObject):
    """
    This class acts as a bridge to allow JavaScript to call Python methods.
    Methods decorated with @Slot are exposed to JavaScript.
    """
    marker_clicked_signal = Signal(str, str) # Signal to pass data to CampusMapWidget

    @Slot(str, str)
    def markerClicked(self, marker_id, marker_title):
        """Called from JavaScript when a map marker is clicked."""
        print(f"PythonMapBridge received click: ID={marker_id}, Title={marker_title}")
        self.marker_clicked_signal.emit(marker_id, marker_title)

# --- Example of how to use this widget in a simple main window ---
if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication, QMainWindow
    import sys

    app = QApplication(sys.argv)
    
    main_window = QMainWindow()
    main_window.setWindowTitle("Campus Map Demo")
    main_window.setGeometry(100, 100, 800, 600)

    map_widget = CampusMapWidget()
    main_window.setCentralWidget(map_widget)

    # Example of how to connect to the signal from outside the map widget
    # This signal will be emitted when a marker is clicked on the map
    map_widget.marker_clicked_signal.connect(lambda id, title: print(f"App received click: {title} ({id})"))

    main_window.show()
    sys.exit(app.exec())
    