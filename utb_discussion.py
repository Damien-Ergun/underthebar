import sys
import json
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QScrollArea, QWidget, QLabel, QLineEdit, QPushButton
from PySide6.QtCore import Qt, QPoint, QThread, Signal, Slot
import time
import json
import random
from datetime import datetime
from PySide6.QtCore import QThread, Signal
from pathlib import Path
import os
from datetime import datetime
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QPixmap, QPainter, QColor, QPainterPath
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QPushButton

import time
from PySide6.QtCore import QThread, Signal, Slot

import hevy_api

class OnlineLikeWorker(QThread):
    """Background worker that simulates a 5-second network request to like a comment."""
    # Custom signal that emits: (success_status_bool, row_widget_reference)
    finished_liking = Signal(bool, object)

    def __init__(self, comment_id, row_widget):
        super().__init__()
        self.comment_id = comment_id
        self.row_widget = row_widget

    def run(self):
        #time.sleep(5)  # Simulate 5-second network delay
        
        status = hevy_api.like_comment(str(self.comment_id))
        
        
        # Simulate a successful online post request. 
        # Change this to False to test the fallback automatic error reversion!
        request_successful = True 
        
        if status != 200:
            request_successful = False
        
        self.finished_liking.emit(request_successful, self.row_widget)

def format_relative_time(timestamp_str):
    if not timestamp_str:
        return "now"
    try:
        clean_str = timestamp_str.replace("Z", "+00:00")
        created_time = datetime.fromisoformat(clean_str)
        now = datetime.now(created_time.tzinfo)
        diff = now - created_time
        seconds = int(diff.total_seconds())

        if seconds < 60: return "now"
        minutes = seconds // 60
        if minutes < 60: return f"{minutes}m"
        hours = minutes // 60
        if hours < 24: return f"{hours}h"
        return f"{hours // 24}d"
    except Exception:
        return "now"

from PySide6.QtWidgets import QDialog, QGridLayout, QToolButton

class EmojiPickerPopup(QDialog):
    """A clean, frameless grid pop-up displaying popular emojis."""
    def __init__(self, target_input_field, parent=None):
        super().__init__(parent)
        self.target_input = target_input_field
        
        # Set frameless popup style parameters
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: rgb(53, 53, 53); border: 1px solid rgb(75, 75, 75); border-radius: 8px;")
        self.setFixedSize(220, 160)

        layout = QGridLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # A selection of popular canonical emojis
        emojis = [
            "😀", "😂", "🤣", "😊", "🔥", "💯",
            "👍", "🙏", "❤️", "👀", "💪", "🏋️",
            "🥵", "😏", "😅", "👏", "💥", "👊",
            "😎", "🎉", "✨", "🚀", "🤔", "😮"
        ]

        # Arrange emojis into a 4x6 grid layout
        rows, cols = 4, 6
        for idx, emoji in enumerate(emojis):
            btn = QToolButton()
            btn.setText(emoji)
            btn.setFixedSize(30, 30)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                """
                QToolButton { border: none; font-size: 16px; background: transparent; border-radius: 4px; }
                QToolButton::hover { background-color: rgb(75, 75, 75); }
                """
            )
            # Inject character on click and close popup context safely
            btn.clicked.connect(lambda checked=False, char=emoji: self.insert_emoji(char))
            
            r = idx // cols
            c = idx % cols
            layout.addWidget(btn, r, c)

    def insert_emoji(self, char):
        """Appends the emoji directly where the user cursor is blinking."""
        current_text = self.target_input.text()
        cursor_pos = self.target_input.cursorPosition()
        
        # Split and rebuild string to handle inline insertion properly
        new_text = current_text[:cursor_pos] + char + current_text[cursor_pos:]
        self.target_input.setText(new_text)
        
        # Move focus back and reposition cursor pipe ahead of the new emoji character
        self.target_input.setFocus()
        self.input_field = self.target_input # temporary placeholder
        self.target_input.setCursorPosition(cursor_pos + len(char))
        self.close()


# Define a persistent local cache directory path
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".chat_cache")
CACHE_DIR = str(Path.home())+"/.underthebar/temp/"

class NetworkAvatar(QLabel):
    """Loads profile pictures, checking local disk cache via url filenames before network downloads."""
    def __init__(self, image_url_str, size=38):
        super().__init__()
        self.size = size
        self.setFixedSize(size, size)

        # 1. Instantly draw a dark grey fallback background placeholder
        self.fallback_pixmap = QPixmap(size, size)
        self.fallback_pixmap.fill(QColor(53, 53, 53))
        self.setPixmap(self.fallback_pixmap)

        if not image_url_str:
            return

        # 2. Ensure our directory structure path safely exists on the user's drive
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)

        # 3. Strip everything except the raw filename from the end of the URL path string
        # e.g., "https://cloudfront.net" -> "gaeabb-thumbnail.jpg"
        parsed_url = QUrl(image_url_str)
        filename = parsed_url.fileName()

        # If a URL ends without a filename pattern, fallback to a clean standardized fallback name
        if not filename or filename.strip() == "":
            filename = "fallback_profile.png"

        # Handle and strip potential trailing URL parameter string artifacts (like "?s=120" from Google URLs)
        if "?" in filename:
            filename = filename.split("?")[0]

        self.local_cache_path = os.path.join(CACHE_DIR, filename)

        # 4. Check if the image filename already exists locally on disk
        if os.path.exists(self.local_cache_path):
            self.load_and_apply_avatar(self.local_cache_path)
        else:
            # Cache miss: Trigger background network download request
            self.manager = QNetworkAccessManager(self)
            self.manager.finished.connect(self.on_download_complete)
            self.manager.get(QNetworkRequest(QUrl(image_url_str)))

    def on_download_complete(self, reply):
        """Executes when the network thread successfully completes."""
        if reply.error() == QNetworkReply.NoError:
            raw_data = reply.readAll()
            
            # Save raw bytes to our local disk asset cache file path immediately
            try:
                with open(self.local_cache_path, "wb") as f:
                    f.write(raw_data.data())
                
                # Apply the newly cached file asset directly onto the screen layout
                self.load_and_apply_avatar(self.local_cache_path)
            except Exception as e:
                print(f"Failed writing image data cache asset: {e}")
                
        reply.deleteLater()

    def load_and_apply_avatar(self, file_path):
        """Loads a local file path target, applies a circle clip path, and repaints the label."""
        src_pixmap = QPixmap(file_path)
        if src_pixmap.isNull():
            return

        target_pixmap = QPixmap(self.size, self.size)
        target_pixmap.fill(Qt.transparent)

        scaled = src_pixmap.scaled(
            self.size, self.size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
        )

        painter = QPainter(target_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        path = QPainterPath()
        path.addEllipse(0, 0, self.size, self.size)
        painter.setClipPath(path)
        
        painter.drawPixmap(0, 0, scaled)
        painter.end()

        self.setPixmap(target_pixmap)

class MessageRow(QWidget):
    def __init__(self, comment_id, username, text, profile_pic_url, created_at, initial_likes, is_liked, dialog_parent, is_reply=False):
        super().__init__()
        self.comment_id, self.username, self.dialog_parent, self.is_reply = comment_id, username, dialog_parent, is_reply
        self.like_count, self.is_liked = initial_likes or 0, bool(is_liked)

        layout = QHBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(52 if is_reply else 16, 6 if is_reply else 8, 12, 6 if is_reply else 8)

        self.avatar = NetworkAvatar(profile_pic_url)
        layout.addWidget(self.avatar, alignment=Qt.AlignTop)

        content_layout = QVBoxLayout()
        content_layout.setSpacing(3)

        header_layout = QHBoxLayout()
        name_label = QLabel(username)
        name_label.setStyleSheet("font-weight: bold; color: #F3F4F6; font-size: 13px;")
        header_layout.addWidget(name_label)

        time_label = QLabel(format_relative_time(created_at))
        time_label.setStyleSheet("color: #8E8E93; font-size: 12px;")
        header_layout.addWidget(time_label)
        header_layout.addStretch()
        content_layout.addLayout(header_layout)

        self.body_label = QLabel(text)
        self.body_label.setWordWrap(True)
        self.body_label.setStyleSheet("color: #E5E7EB; font-size: 13px; line-height: 1.4;")
        content_layout.addWidget(self.body_label)

        action_layout = QHBoxLayout()
        action_layout.setSpacing(12)

        self.reply_btn = QPushButton("Reply")
        self.reply_btn.setCursor(Qt.PointingHandCursor)
        self.reply_btn.setStyleSheet("QPushButton { border: none; color: #3B82F6; font-size: 11px; font-weight: bold; background: transparent; padding: 0px; } QPushButton:hover { color: #60A5FA; text-decoration: underline; }")
        self.reply_btn.clicked.connect(self.trigger_reply_target)
        action_layout.addWidget(self.reply_btn)

        self.like_btn = QPushButton()
        self.like_btn.setCursor(Qt.PointingHandCursor)
        self.like_btn.setFocusPolicy(Qt.NoFocus)
        self.like_btn.clicked.connect(self.toggle_like)
        action_layout.addWidget(self.like_btn)

        self.like_counter_label = QLabel()
        self.like_counter_label.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        action_layout.addWidget(self.like_counter_label)
        action_layout.addStretch()
        content_layout.addLayout(action_layout)

        layout.addLayout(content_layout, stretch=1)
        self.update_like_ui_state()
        
        self.active_like_workers = []

    def trigger_reply_target(self):
        self.dialog_parent.set_reply_target(self)

    def toggle_like(self):
        if self.is_liked:
            return

        # 1. Optimistic UI update: Instantly update only the button's visual state to "Liked"
        self.like_btn.setText("Liked")
        self.like_btn.setStyleSheet("QPushButton { border: none; color: #EF4444; font-size: 11px; font-weight: bold; background: transparent; padding: 0px; }")
        self.like_btn.setCursor(Qt.ArrowCursor)
        self.like_btn.setEnabled(False) # Temporarily lock out additional clicks

        # 2. Fire background thread (passing our comment ID and a self reference)
        worker = OnlineLikeWorker(self.comment_id, self)
        worker.finished_liking.connect(self.on_like_request_completed)
        
        self.active_like_workers.append(worker) # Prevent garbage collection
        worker.start()
        
    @Slot(bool, object)
    def on_like_request_completed(self, success, row_widget):
        """Runs back on the UI thread when the 5 seconds complete."""
        sender_thread = self.sender()
        if sender_thread in self.active_like_workers:
            self.active_like_workers.remove(sender_thread)

        if success:
            # 3. Request succeeded: Formally increment counter data metrics and print to console
            self.is_liked = True
            self.like_count += 1
            #print(f"Liked comment: {self.comment_id}")
            self.update_like_ui_state()
        else:
            # 4. Request failed fallback: Completely revert button back to clickable original state
            print(f"Network error liking comment {self.comment_id}. Reverting state...")
            self.is_liked = False
            self.update_like_ui_state()

    def update_like_ui_state(self):
        """Standardized UI drawing controller based on formal boolean states."""
        if self.is_liked:
            self.like_btn.setText("Liked")
            self.like_btn.setStyleSheet("QPushButton { border: none; color: #EF4444; font-size: 11px; font-weight: bold; background: transparent; padding: 0px; }")
            self.like_btn.setCursor(Qt.ArrowCursor)
            self.like_btn.setEnabled(False) 
        else:
            self.like_btn.setText("Like")
            self.like_btn.setStyleSheet("QPushButton { border: none; color: #A0A0A5; font-size: 11px; font-weight: bold; background: transparent; padding: 0px; } QPushButton:hover { color: #D1D5DB; }")
            self.like_btn.setCursor(Qt.PointingHandCursor)
            self.like_btn.setEnabled(True)

        # Counter text metrics label only becomes visible if actual saved numbers exist
        self.like_counter_label.setText(f"•  ❤️ {self.like_count}" if self.like_count > 0 else "")
        self.like_counter_label.setVisible(self.like_count > 0)



class OnlineSendWorker(QThread):
    """Background worker that simulates a 5-second network call returning a dictionary object."""
    # Custom signal that emits: (returned_json_dict, local_row_widget_reference)
    finished_sending = Signal(list, object)

    def __init__(self, workout_id, text, reply_target=None, reply_to_id=None):
        super().__init__()
        self.workout_id = workout_id
        self.text = text
        self.reply_target = reply_target
        self.reply_to_id = reply_to_id

    def run(self):
        # Simulate network latency
        #time.sleep(5)
        
        hevy_api.post_comment(self.workout_id, self.text, self.reply_to_id)
        the_data = hevy_api.get_comments(self.workout_id)

        # Mock an updated dataset structure matching your required schema format
        mock_response = [
            {
                "id": 13499999,
                "comment": "It is broken sorry.",
                "username": "Under the Bar",
                "verified": False,
                "full_name": "Your Account Name",
                "created_at": datetime.now().isoformat() + "Z",
                "like_count": 0,
                "profile_pic": "",
                "is_liked_by_user": False
            }
        ]
        #with open("workout.json", "r", encoding="utf-8") as file:
        #    mock_response = json.load(file)
        
        # Safely emit the dictionary directly across thread channels
        if isinstance(the_data, list):
            self.finished_sending.emit(the_data, self.reply_target)
        else:
            self.finished_sending.emit(mock_response, self.reply_target)
        
class OnlineFetchWorker(QThread):
    """Background worker that fetches discussion JSON"""
    # Custom signal that emits: (returned_json_dict, local_row_widget_reference)
    finished_fetching = Signal(list)

    def __init__(self, workout_id=None):
        super().__init__()
        self.workout_id = workout_id

    def run(self):
        # Simulate network latency
        #time.sleep(5)
        the_data = hevy_api.get_comments(self.workout_id)

        # Mock an updated dataset structure matching your required schema format
        mock_response = {
            "comments": [
                {
                    "id": 13499999,
                    "comment": "It is broken sorry.",
                    "username": "Under the Bar",
                    "verified": False,
                    "full_name": "Your Account Name",
                    "created_at": datetime.now().isoformat() + "Z",
                    "like_count": 0,
                    "profile_pic": "",
                    "is_liked_by_user": False
                }
            ]
        }
        #with open("workout.json", "r", encoding="utf-8") as file:
        #    mock_response = json.load(file)
        
        # Safely emit the dictionary directly across thread channels
        if isinstance(the_data, list):
            print("Received valid comment list")
            self.finished_fetching.emit(the_data)
        else:
            self.finished_fetching.emit(mock_response)


class UTBDiscussion(QDialog):
    def __init__(self, workout_id=None):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.resize(462, 582)
        
        # Combined styles to apply the rgb themes, text coloring, and clean custom scrollbars
        self.setStyleSheet(
            """
            QDialog {
                background-color: rgb(0, 0, 0);
                color: #F3F4F6;
            }
            
            /* Custom ScrollBar Theme Configuration */
            QScrollBar:vertical {
                border: none;
                background-color: rgb(25, 25, 25);
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background-color: rgb(53, 53, 53);
                min-height: 30px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgb(75, 75, 75);
            }
            QScrollBar::handle:vertical:pressed {
                background-color: rgb(45, 45, 45);
            }
            QScrollBar::sub-line:vertical, QScrollBar::add-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                border: none;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            """
        )

        self.current_reply_target = None
        self.widget_map = {}
        self.drag_position = QPoint()

        # Master border constraint layout
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(1, 1, 1, 1)
        outer_layout.setSpacing(0)

        # Central canvas box area
        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: rgb(25, 25, 25);")
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        outer_layout.addWidget(central_widget)

        # Title Bar
        self.title_bar = QWidget()
        self.title_bar.setStyleSheet("background-color: rgb(53, 53, 53); border-bottom: 1px solid rgb(40, 40, 40);")
        self.title_bar.setFixedHeight(40)
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(16, 0, 10, 0)

        title_label = QLabel("Comments")
        title_label.setStyleSheet("font-weight: bold; color: #F3F4F6; font-size: 13px; background: transparent;")
        
        close_button = QPushButton("✕")
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.setFixedSize(28, 28)
        close_button.setStyleSheet(
            """
            QPushButton {
                border: none; color: #9CA3AF; font-size: 14px; font-weight: bold; background: transparent; border-radius: 4px;
            }
            QPushButton:hover { background-color: rgb(75, 75, 75); color: #FFFFFF; }
            QPushButton:pressed { background-color: rgb(60, 60, 60); }
            """
        )
        close_button.clicked.connect(self.close)

        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(close_button)
        main_layout.addWidget(self.title_bar)

        # Scroll Feed
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none; background-color: rgb(25, 25, 25);")

        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background-color: rgb(25, 25, 25);")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(0, 12, 0, 12)
        self.chat_layout.setSpacing(4)
        #self.chat_layout.addStretch()

        self.scroll_area.setWidget(self.chat_container)
        main_layout.addWidget(self.scroll_area)

        # Active Context bar
        self.context_bar = QWidget()
        self.context_bar.setVisible(False)
        self.context_bar.setStyleSheet("background-color: rgb(53, 53, 53); border-top: 1px solid rgb(70, 70, 70);")
        context_layout = QHBoxLayout(self.context_bar)
        context_layout.setContentsMargins(16, 8, 16, 8)

        self.context_label = QLabel()
        self.context_label.setStyleSheet("color: #D1D5DB; font-size: 12px; background: transparent;")

        cancel_reply_btn = QPushButton("✕")
        cancel_reply_btn.setFixedSize(16, 16)
        cancel_reply_btn.setStyleSheet("border: none; color: #9CA3AF; font-weight: bold; background: transparent;")
        cancel_reply_btn.clicked.connect(self.clear_reply_target)

        context_layout.addWidget(self.context_label)
        context_layout.addStretch()
        context_layout.addWidget(cancel_reply_btn)
        main_layout.addWidget(self.context_bar)

        # Input panel bar layout configuration
        input_panel = QWidget()
        input_panel.setStyleSheet("background-color: rgb(25, 25, 25); border-top: 1px solid rgb(45, 45, 45);")
        input_layout = QHBoxLayout(input_panel)
        input_layout.setContentsMargins(14, 14, 14, 14)
        input_layout.setSpacing(10)

        # Container to overlay the emoji action layout cleanly inside the line entry bar boundary
        input_container = QWidget()
        input_container.setStyleSheet("background-color: rgb(53, 53, 53); border: 1px solid rgb(75, 75, 75); border-radius: 20px;")
        container_layout = QHBoxLayout(input_container)
        container_layout.setContentsMargins(4, 0, 12, 0)
        container_layout.setSpacing(0)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Message thread...")
        self.input_field.returnPressed.connect(self.submit_message)
        self.input_field.setStyleSheet("QLineEdit { padding: 10px 12px; border: none; background: transparent; color: #F9FAFB; font-size: 13px; }")

        # Subtle smiling icon button acting as the trigger link anchor
        self.emoji_btn = QPushButton("💪")
        self.emoji_btn.setCursor(Qt.PointingHandCursor)
        self.emoji_btn.setFixedSize(28, 28)
        self.emoji_btn.setStyleSheet(
            """
            QPushButton { border: none; font-size: 15px; background: transparent; border-radius: 14px; }
            QPushButton::hover { background-color: rgb(75, 75, 75); }
            """
        )
        self.emoji_btn.clicked.connect(self.show_emoji_picker)

        container_layout.addWidget(self.input_field)
        container_layout.addWidget(self.emoji_btn)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.submit_message)
        self.send_button.setFixedSize(74, 37)
        self.send_button.setStyleSheet("QPushButton { background-color: rgb(53, 53, 53); color: #F3F4F6; border: 1px solid rgb(75, 75, 75); border-radius: 18px; font-weight: bold; font-size: 13px; } QPushButton:hover { background-color: rgb(68, 68, 68); border-color: rgb(90, 90, 90); } QPushButton:disabled { background-color: rgb(35, 35, 35); color: rgb(100, 100, 100); border-color: rgb(50, 50, 50); }")

        input_layout.addWidget(input_container) # Pack container layout line in instead of standalone input
        input_layout.addWidget(self.send_button)
        main_layout.addWidget(input_panel)
        
        # Locate this inside your __init__ setup to track running threads
        # Add it anywhere among the variables:
        self.active_workers = []
        
        # LOAD THE WORKOUT
        self.workout_id = workout_id
        if self.workout_id != None:
            # 4. Fire background thread (loading the workout)
            worker = OnlineFetchWorker(self.workout_id)
            worker.finished_fetching.connect(self.on_fetch_complete)
            
            self.active_workers.append(worker)
            worker.start()

    def show_emoji_picker(self):
        """Calculates popup coordinates dynamically and displays the picker panel."""
        picker = EmojiPickerPopup(self.input_field, self)
        
        # Calculate screen coordinates directly above the emoji trigger icon button
        button_pos = self.emoji_btn.mapToGlobal(QPoint(0, 0))
        popup_x = button_pos.x() - picker.width() + self.emoji_btn.width()
        popup_y = button_pos.y() - picker.height() - 8  # 8px floating padding clearance gap
        
        picker.move(popup_x, popup_y)
        picker.exec()
        
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self.input_field.hasFocus():
                self.submit_message()
            event.accept()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.title_bar.rect().contains(self.title_bar.mapFrom(self, event.position().toPoint())):
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self.drag_position.isNull():
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_position = QPoint()

    def load_comments_json(self, json_data):
        
        if isinstance(json_data, dict):
            comments_list = json_data.get("comments", [])
        elif isinstance(json_data, list):
            comments_list = json_data

        parents, children = [], []
        for c in comments_list:
            if "parent_comment_id" in c and c["parent_comment_id"] is not None:
                children.append(c)
            else:
                parents.append(c)

        for p in parents:
            self.append_new_row(p.get("id"), p.get("username", "anonymous"), p.get("comment", ""), p.get("profile_pic", ""), p.get("created_at", ""), p.get("like_count", 0), p.get("is_liked_by_user", False))
        for c in children:
            parent_id = c["parent_comment_id"]
            if parent_id in self.widget_map:
                self.insert_reply_row(self.widget_map[parent_id], c.get("id"), c.get("username", "anonymous"), c.get("comment", ""), c.get("profile_pic", ""), c.get("created_at", ""), c.get("like_count", 0), c.get("is_liked_by_user", False))

    def set_reply_target(self, message_widget):
        self.current_reply_target = message_widget
        text_preview = message_widget.body_label.text()
        clipped = f"{text_preview[:25]}..." if len(text_preview) > 25 else text_preview
        self.context_label.setText(f"Replying to <b style='color:#F3F4F6;'>@{message_widget.username}</b>: \"<i>{clipped}</i>\"")
        self.context_bar.setVisible(True)
        
        self.input_field.setText(f"@{message_widget.username} ")
        self.input_field.setFocus()
        self.input_field.setCursorPosition(len(self.input_field.text()))

    def clear_reply_target(self):
        self.current_reply_target = None
        self.context_bar.setVisible(False)
        self.input_field.clear()

    def append_new_row(self, comment_id, username, text, avatar_url, created_at="", like_count=0, is_liked=False):
        row = MessageRow(comment_id, username, text, avatar_url, created_at, like_count, is_liked, self, is_reply=False)
        self.widget_map[comment_id] = row
        
        # 1. Safely find the position of the last row widget, ignoring any trailing spacer items
        target_idx = 0
        for idx in range(self.chat_layout.count()):
            item = self.chat_layout.itemAt(idx)
            if item and item.widget():
                target_idx = idx + 1
                
        # 2. Injects the new parent row cleanly below all existing content blocks
        self.chat_layout.insertWidget(target_idx, row)
        return row

    def insert_reply_row(self, parent_widget, comment_id, username, text, avatar_url, created_at="", like_count=0, is_liked=False):
        row = MessageRow(comment_id, username, text, avatar_url, created_at, like_count, is_liked, self, is_reply=True)
        self.widget_map[comment_id] = row
        
        v_scroll = self.scroll_area.verticalScrollBar()
        current_scroll_val = v_scroll.value()
        
        idx = self.chat_layout.indexOf(parent_widget)
        target_idx = idx + 1
        while target_idx < self.chat_layout.count():
            item = self.chat_layout.itemAt(target_idx)
            # Break if we hit a spacer item or another top-level parent row widget
            if not item or not item.widget() or not item.widget().is_reply: 
                break
            target_idx += 1
            
        self.chat_layout.insertWidget(target_idx, row)
        
        QApplication.processEvents()
        v_scroll.setValue(current_scroll_val)
        return row

    def submit_message(self):
        """Inserts the message locally immediately, then locks input for 5 seconds."""
        text = self.input_field.text().strip()
        if not text: return

        # 1. Generate local IDs and timestamps immediately
        generated_id = random.randint(20000000, 99900000)
        now_iso = datetime.now().isoformat() + "Z"
        inserted_row_widget = None

        # 2. Add to UI right away depending on context
        reply_to_id = None
        if self.current_reply_target:
            #print(f"reply to id: {self.current_reply_target.comment_id} -> text: {text}")
            reply_to_id = self.current_reply_target.comment_id
            inserted_row_widget = self.insert_reply_row(
                self.current_reply_target, generated_id, "You", text, "", created_at=now_iso
            )
            self.clear_reply_target()
        else:
            #print(f"new comment: {text}")
            
            # Use range connection to snap the view down to the new parent post
            v_scrollbar = self.scroll_area.verticalScrollBar()
            def handle_new_bottom(min_val, max_val):
                v_scrollbar.setValue(max_val)
                v_scrollbar.rangeChanged.disconnect(handle_new_bottom)
            v_scrollbar.rangeChanged.connect(handle_new_bottom)
            
            inserted_row_widget = self.append_new_row(
                generated_id, "You", text, "", created_at=now_iso
            )
            self.input_field.clear()

        # 3. Freeze controls immediately so user can't send another one yet
        self.send_button.setEnabled(False)
        self.input_field.setEnabled(False)

        # 4. Fire background thread (passing our text and row reference)
        worker = OnlineSendWorker(self.workout_id, text, inserted_row_widget, reply_to_id)
        worker.finished_sending.connect(self.on_message_successfully_sent)
        
        self.active_workers.append(worker)
        worker.start()

    @Slot(list)
    def on_fetch_complete(self, returned_list):
        """Freezes layout painting, saves scroll position, reloads dictionary data, and restores scroll offset."""
        fetcher_thread = self.sender()
        if fetcher_thread in self.active_workers:
            self.active_workers.remove(fetcher_thread)
        
        # Freeze the display painting engine to completely block flickering
        self.setUpdatesEnabled(False)
        
        self.load_comments_json(returned_list)
        self.chat_layout.addStretch()
        QApplication.processEvents()
        
        self.setUpdatesEnabled(True)
        self.update()
        

    @Slot(list, None)
    def on_message_successfully_sent(self, returned_dict, row_widget):
        """Freezes layout painting, saves scroll position, reloads dictionary data, and restores scroll offset."""
        print("running: ", "on_message_successfully_sent")
        sender_thread = self.sender()
        if sender_thread in self.active_workers:
            self.active_workers.remove(sender_thread)

        # Capture the exact vertical scrollbar offset value right now
        v_scrollbar = self.scroll_area.verticalScrollBar()
        saved_scroll_val = v_scrollbar.value()

        # Freeze the display painting engine to completely block flickering
        self.setUpdatesEnabled(False)

        try:
            # Completely flush the existing text layout tracking dictionary
            self.widget_map.clear()
            
            for idx in reversed(range(self.chat_layout.count())):
                item = self.chat_layout.itemAt(idx)
                if item and item.widget():
                    widget_to_drop = item.widget()
                    self.chat_layout.removeWidget(widget_to_drop)
                    widget_to_drop.deleteLater()
                elif item: # This wipes out the old standalone stretch spacer items
                    self.chat_layout.removeItem(item)

            # 1. Feed the fresh dictionary into your loader logic first
            self.load_comments_json(returned_dict)

            # 2. Add the stretch spacer at the absolute BOTTOM of the stack.
            # This acts as a spring, pushing all your messages up to the top!
            self.chat_layout.addStretch()

            # Flush event tasks to ensure Qt handles row math before re-scrolling
            QApplication.processEvents()

            # Re-apply the stored pixel offset value back to the vertical slider bounds
            v_scrollbar.setValue(saved_scroll_val)
        
        except:
            print("on_message_successfully_sent: ", "something broke")

        finally:
            # Unfreeze the display and re-enable global screen painting processes
            self.setUpdatesEnabled(True)
            self.update()

        # Re-enable user interaction fields smoothly
        self.input_field.setEnabled(True)
        self.send_button.setEnabled(True)
        self.input_field.setFocus()
            
    def scroll_to_bottom(self):
        # Kept as an explicit manual backup utility loop if needed
        pass
        
    def showEvent(self, event):
        """Triggers automatically when the dialog window is displayed on screen."""
        super().showEvent(event)
        
        # Explicitly focus the input line edit widget
        self.input_field.setFocus()
        
        # Ensure the cursor text pipe line is active and blinking immediately
        self.input_field.activateWindow()

if __name__ == "__main__":
    SAMPLE_JSON = """{
        "comments": [
            {
                "id": 13487871,
                "comment": "Cali park beats the shit out of ours. You need to pack it into your suitcases.",
                "username": "kennyboyo",
                "created_at": "2026-07-29T16:16:42.795Z",
                "like_count": 1,
                "profile_pic": "https://cloudfront.net",
                "is_liked_by_user": false
            },
            {
                "id": 13493170,
                "comment": "@gercingetorix hahaha you can always scroll through the comments of your Hevy posts to restore your confidence 🤣🤣",
                "username": "kennyboyo",
                "created_at": "2026-07-29T20:03:32.221Z",
                "like_count": 2,
                "profile_pic": "https://cloudfront.net",
                "parent_comment_id": 13487871,
                "is_liked_by_user": true
            },
            {
                "id": 13494202,
                "comment": "Looks great fun, cali stuff looks alright too 😏😅😂",
                "username": "mattplifts",
                "created_at": "2026-07-29T20:48:53.544Z",
                "like_count": 0,
                "profile_pic": "https://cloudfront.net",
                "is_liked_by_user": false
            }
        ]
    }"""

    with open("workout.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    app = QApplication(sys.argv)
    #dialog = UTBDiscussion("f2c78551-2179-4f3b-b527-94c4722748a2")
    dialog = UTBDiscussion("1ca5a454-0865-4f07-bd81-fb7a41886a6d") # Workout Tues July 21st 2026 with no comments on it.
    #dialog.load_comments_json(data)
    dialog.exec()