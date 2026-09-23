"""
Advance Path Editor V1.0.1
--------------------------
Modern asset path editor and validator for Autodesk Maya and Chaos V-Ray.
Supports dynamic Qt bindings across PySide2 (Maya 2018–2024) and PySide6 (Maya 2025–2026+).

Version: 1.0.1
Author: Rahul Vilas Gambhir
GitHub: https://github.com/thecodemaster21
License: MIT
"""

import os
import maya.cmds as cmds

# Dynamic Qt binding resolution (PySide2 for Maya <= 2024, PySide6 for Maya >= 2025)
try:
    from PySide2 import QtWidgets, QtCore, QtGui
except ImportError:
    try:
        from PySide6 import QtWidgets, QtCore, QtGui
    except ImportError:
        raise ImportError("Neither PySide2 nor PySide6 could be resolved in this Maya environment.")

__version__ = "1.0.1"
__author__ = "Rahul Vilas Gambhir"


class AdvancePathEditor(QtWidgets.QDialog):
    """Modern dark-themed file path manager for Maya native and V-Ray nodes."""

    def __init__(self, parent=None):
        super(AdvancePathEditor, self).__init__(parent)
        self.setWindowTitle("Advance Path Editor V1.0.1")
        self.resize(920, 600)
        self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint)

        self._ensure_vray_loaded()
        self._setup_ui()
        self._apply_stylesheet()
        self.refresh_paths()

    def _ensure_vray_loaded(self):
        """Loads vrayformaya if installed but currently inactive."""
        plugin_name = "vrayformaya"
        if not cmds.pluginInfo(plugin_name, query=True, loaded=True):
            try:
                cmds.loadPlugin(plugin_name, quiet=True)
            except Exception:
                pass

    def _setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Header Bar
        header = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("ADVANCE PATH EDITOR")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #4DEEEA; letter-spacing: 1px;")

        ver_label = QtWidgets.QLabel("v1.0.1")
        ver_label.setStyleSheet("font-size: 11px; color: #777777; font-weight: bold;")

        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Filter by node name, type, or path...")
        self.search_input.textChanged.connect(self.filter_paths)

        refresh_btn = QtWidgets.QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_paths)

        header.addWidget(title)
        header.addWidget(ver_label)
        header.addSpacing(15)
        header.addWidget(self.search_input)
        header.addWidget(refresh_btn)
        main_layout.addLayout(header)

        # Asset Table
        self.table = QtWidgets.QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Status", "Node Name", "Type", "Attribute", "Resolved File Path"])
        self.table.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        main_layout.addWidget(self.table)

        # Operations Group
        actions_group = QtWidgets.QGroupBox("Batch Operations")
        actions_layout = QtWidgets.QVBoxLayout(actions_group)

        # String Replace Row
        replace_layout = QtWidgets.QHBoxLayout()
        self.find_input = QtWidgets.QLineEdit()
        self.find_input.setPlaceholderText("Find string...")
        self.replace_input = QtWidgets.QLineEdit()
        self.replace_input.setPlaceholderText("Replace with...")
        replace_btn = QtWidgets.QPushButton("Replace Selected")
        replace_btn.clicked.connect(self.replace_string)

        replace_layout.addWidget(self.find_input)
        replace_layout.addWidget(self.replace_input)
        replace_layout.addWidget(replace_btn)
        actions_layout.addLayout(replace_layout)

        # Directory Repath Row
        repath_layout = QtWidgets.QHBoxLayout()
        self.dir_input = QtWidgets.QLineEdit()
        self.dir_input.setPlaceholderText("Target folder directory...")
        browse_btn = QtWidgets.QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_folder)
        repath_btn = QtWidgets.QPushButton("Repath Selected")
        repath_btn.clicked.connect(self.repath_selected)

        repath_layout.addWidget(self.dir_input)
        repath_layout.addWidget(browse_btn)
        repath_layout.addWidget(repath_btn)
        actions_layout.addLayout(repath_layout)

        main_layout.addWidget(actions_group)

    def _apply_stylesheet(self):
        style = (
            "QDialog { background-color: #1E1E1E; color: #E0E0E0; font-family: 'Segoe UI', sans-serif; }\n"
            "QLabel { color: #CCCCCC; }\n"
            "QLineEdit { background-color: #121212; border: 1px solid #333333; border-radius: 4px; padding: 6px; color: #FFFFFF; }\n"
            "QLineEdit:focus { border: 1px solid #4DEEEA; }\n"
            "QPushButton { background-color: #2D2D2D; border: 1px solid #3A3A3A; border-radius: 4px; padding: 6px 14px; color: #FFFFFF; font-weight: bold; }\n"
            "QPushButton:hover { background-color: #3D3D3D; border-color: #4DEEEA; }\n"
            "QPushButton:pressed { background-color: #4DEEEA; color: #000000; }\n"
            "QTableWidget { background-color: #121212; alternate-background-color: #181818; border: 1px solid #333333; gridline-color: #252525; color: #E0E0E0; }\n"
            "QHeaderView::section { background-color: #252525; color: #999999; padding: 6px; border: none; font-weight: bold; }\n"
            "QGroupBox { border: 1px solid #333333; border-radius: 6px; margin-top: 10px; font-weight: bold; color: #777777; }\n"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }"
        )
        self.setStyleSheet(style)

    def get_file_nodes(self):
        """Returns tuples of (node, node_type, attribute) for all tracked scene assets."""
        node_mappings = {
            "file": ["fileTextureName"],
            "aiImage": ["filename"],
            "AlembicNode": ["abc_File"],
            "VRayPlaceEnvTex": ["fileName"],
            "VRayMesh": ["filePath"],
            "VRayVolumeGrid": ["fileName"],
            "VRayLightIESShape": ["iesFile"],
            "VRayVRmat": ["filename"],
            "VRayPtex": ["ptexFilePath"],
            "VRayOSL": ["oslFilePath"]
        }

        nodes = []
        for n_type, attrs in node_mappings.items():
            found_nodes = cmds.ls(type=n_type) or []
            for node in found_nodes:
                for attr in attrs:
                    if cmds.attributeQuery(attr, node=node, exists=True):
                        nodes.append((node, n_type, attr))
        return nodes

    def refresh_paths(self):
        """Scans scene files and refreshes path status indicators."""
        self.table.setRowCount(0)
        file_nodes = self.get_file_nodes()

        for row, (node, n_type, attr) in enumerate(file_nodes):
            path = cmds.getAttr("{}.{}".format(node, attr)) or ""
            exists = os.path.exists(path) if path else False

            self.table.insertRow(row)

            status_item = QtWidgets.QTableWidgetItem(" OK " if exists else " MISSING ")
            status_item.setForeground(QtGui.QColor("#00E676" if exists else "#FF5252"))
            status_item.setTextAlignment(QtCore.Qt.AlignCenter)

            self.table.setItem(row, 0, status_item)
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(node))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(n_type))
            self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(attr))
            self.table.setItem(row, 4, QtWidgets.QTableWidgetItem(path))

    def filter_paths(self, text):
        """Filters visible rows against node name, type, and path."""
        text = text.lower()
        for row in range(self.table.rowCount()):
            node_name = self.table.item(row, 1).text().lower()
            node_type = self.table.item(row, 2).text().lower()
            path_name = self.table.item(row, 4).text().lower()
            show = (text in node_name) or (text in node_type) or (text in path_name)
            self.table.setRowHidden(row, not show)

    def replace_string(self):
        """Executes search-and-replace across selected table rows."""
        find_str = self.find_input.text()
        replace_str = self.replace_input.text()
        if not find_str:
            return

        selected_rows = set(item.row() for item in self.table.selectedItems())
        for row in selected_rows:
            node = self.table.item(row, 1).text()
            attr = self.table.item(row, 3).text()
            old_path = self.table.item(row, 4).text()

            if find_str in old_path:
                new_path = old_path.replace(find_str, replace_str)
                cmds.setAttr("{}.{}".format(node, attr), new_path, type="string")

        self.refresh_paths()

    def browse_folder(self):
        """Opens a folder selection dialog."""
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Target Folder")
        if folder:
            self.dir_input.setText(folder)

    def repath_selected(self):
        """Repaths selected assets to target folder keeping original filenames."""
        target_dir = self.dir_input.text()
        if not target_dir or not os.path.exists(target_dir):
            return

        selected_rows = set(item.row() for item in self.table.selectedItems())
        for row in selected_rows:
            node = self.table.item(row, 1).text()
            attr = self.table.item(row, 3).text()
            current_path = self.table.item(row, 4).text()

            filename = os.path.basename(current_path)
            new_path = os.path.join(target_dir, filename).replace("\\", "/")

            cmds.setAttr("{}.{}".format(node, attr), new_path, type="string")

        self.refresh_paths()


def show_ui():
    """Initializes and displays the Advance Path Editor window."""
    global _advance_path_editor_dialog
    try:
        _advance_path_editor_dialog.close()
        _advance_path_editor_dialog.deleteLater()
    except Exception:
        pass

    _advance_path_editor_dialog = AdvancePathEditor()
    _advance_path_editor_dialog.show()


if __name__ == "__main__":
    show_ui()