import gi
gi.require_version("Playerctl", "2.0")
from gi.repository import Playerctl, GLib
import requests
import shutil
import subprocess
import threading
import tempfile
import sqlite3
from PyQt5.QtWidgets import QComboBox, QLabel, QPushButton, QSlider, QFileDialog, QTableWidgetItem
from PyQt5.QtWidgets import QApplication, QMainWindow, QMenu, QAction, QTableWidget, QMessageBox
from PyQt5.QtCore import QDir, QTimer, Qt
from PyQt5.QtGui import QPainter, QIcon
import sys
import time

config = """
[general]
framerate = 60
bars = 10
[output]
method = raw
raw_target = /dev/stdout
data_format = ascii
ascii_max_range = 39
"""
event = True


class Cava:
    def __init__(self, parent):
        self.parent = parent

    def run(self):
        with tempfile.NamedTemporaryFile() as config_file:
            config_file.write(config.encode())
            config_file.flush()
            process = subprocess.Popen(["cava", "-p", config_file.name], stdout=subprocess.PIPE)
            source = process.stdout
            while True:
                data = source.readline()  # type: ignore
                sample = list(map(int, data.decode("utf-8").split(";")[:-1]))
                try:
                    self.parent.bars = sample
                    self.parent.update()
                except:
                    return


class Project(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setFixedSize(720, 400)
        self.bars = [0, 0, 0, 0, 0, 0, 0]
        self.holding = False
        self.track_saved = False
        self.menu = QMenu(self)
        self.always_on_top_action = QAction("Always on top", self)
        self.always_on_top_action.setCheckable(True)
        self.always_on_top_action.triggered.connect(self.always_on_top)
        self.menu.addAction(self.always_on_top_action)
        self.menu.addSeparator()
        self.save_art_action = QAction("Save current song art", self)
        self.save_art_action.setDisabled(True)
        self.save_art_action.triggered.connect(self.save_art)
        self.menu.addAction(self.save_art_action)
        self.copy_title_action = QAction("Copy current song title", self)
        self.copy_title_action.setDisabled(True)
        self.copy_title_action.triggered.connect(self.copy_title)
        self.menu.addAction(self.copy_title_action)
        self.copy_artists_action = QAction("Copy current song artists", self)
        self.copy_artists_action.setDisabled(True)
        self.copy_artists_action.triggered.connect(self.copy_artists)
        self.menu.addAction(self.copy_artists_action)
        self.menu.addSeparator()
        self.edit_db_action = QAction("Edit saved tracks", self)
        self.edit_db_action.triggered.connect(self.edit_db)
        self.menu.addAction(self.edit_db_action)
        self.export_db_action = QAction("Export saved tracks", self)
        self.export_db_action.triggered.connect(self.export_db)
        self.menu.addAction(self.export_db_action)
        self.opts_btn = QPushButton(self)
        icon = QIcon.fromTheme("preferences-desktop-symbolic")
        self.opts_btn.setIcon(icon)
        self.opts_btn.resize(60, 40)
        self.opts_btn.move(10, 10)
        self.opts_btn.setMenu(self.menu)
        self.opts_btn.setFocusPolicy(Qt.NoFocus)  # type: ignore
        self.all_players = QComboBox(self)
        self.all_players.resize(630, 40)
        self.all_players.move(80, 10)
        self.all_players.setFocusPolicy(Qt.NoFocus)  # type: ignore
        self.all_players.addItem("~")
        self.title = QLabel(self)
        self.title.resize(540, 40)
        self.title.move(10, 60)
        self.title.setAlignment(Qt.AlignLeft)  # type: ignore
        self.title.setStyleSheet("""
        font-size: 30px;
        font-weight: 600;
        """)
        self.artist = QLabel(self)
        self.artist.resize(540, 40)
        self.artist.move(10, 110)
        self.artist.setAlignment(Qt.AlignLeft)  # type: ignore
        self.artist.setStyleSheet("""
        font-size: 25px;
        font-weight: 500;
        """)
        self.time_now = QLabel(self)
        self.time_now.resize(50, 20)
        self.time_now.move(610, 370)
        self.time_now.setAlignment(Qt.AlignLeft)  # type: ignore
        self.time_end = QLabel(self)
        self.time_end.resize(50, 20)
        self.time_end.move(660, 370)
        self.time_end.setAlignment(Qt.AlignRight)  # type: ignore
        self.delimeter = QLabel("/", self)
        self.delimeter.resize(6, 20)
        self.delimeter.move(658, 370)
        self.delimeter.setAlignment(Qt.AlignCenter)  # type: ignore
        self.cover = QLabel(self)
        self.cover.resize(200, 200)
        self.cover.move(10, 161)
        self.cover.setStyleSheet("""
        border-radius: 6px;
        border-image: url('.cover.png') 0 0 0 0 stretch stretch;
        """)
        self.slider = QSlider(Qt.Horizontal, self)  # type: ignore
        self.slider.resize(590, 20)
        self.slider.move(10, 370)
        self.slider.sliderPressed.connect(self.slider_hold)
        self.slider.sliderReleased.connect(self.slider_release)
        self.slider.setFocusPolicy(Qt.NoFocus)  # type: ignore
        self.prev_btn = QPushButton(self)
        icon = QIcon.fromTheme("media-skip-backward")
        self.prev_btn.setIcon(icon)
        self.prev_btn.resize(40, 40)
        self.prev_btn.move(570, 60)
        self.prev_btn.clicked.connect(self.previous_track)
        self.prev_btn.setFocusPolicy(Qt.NoFocus)  # type: ignore
        self.play_pause_btn = QPushButton(self)
        self.play_pause_btn.resize(40, 40)
        self.play_pause_btn.move(620, 60)
        self.play_pause_btn.clicked.connect(self.playback_change)
        self.play_pause_btn.setFocusPolicy(Qt.NoFocus)  # type: ignore
        self.next_btn = QPushButton(self)
        self.next_btn.resize(40, 40)
        self.next_btn.move(670, 60)
        icon = QIcon.fromTheme("media-skip-forward")
        self.next_btn.setIcon(icon)
        self.next_btn.clicked.connect(self.next_track)
        self.next_btn.setFocusPolicy(Qt.NoFocus)  # type: ignore
        self.save_btn = QPushButton(self)
        icon = QIcon.fromTheme("add")
        self.save_btn.setIcon(icon)
        self.save_btn.resize(40, 40)
        self.save_btn.move(570, 110)
        self.save_btn.clicked.connect(self.save_to_db)
        self.save_btn.setFocusPolicy(Qt.NoFocus)  # type: ignore
        self.loop_btn = QPushButton(self)
        self.loop_btn.resize(40, 40)
        self.loop_btn.move(620, 110)
        self.loop_btn.clicked.connect(self.loop)
        self.loop_btn.setFocusPolicy(Qt.NoFocus)  # type: ignore
        self.shuffle_btn = QPushButton(self)
        self.shuffle_btn.resize(40, 40)
        self.shuffle_btn.move(670, 110)
        self.shuffle_btn.clicked.connect(self.shuffle)
        self.shuffle_btn.setFocusPolicy(Qt.NoFocus)  # type: ignore
        self.player = PlayerManager(self)
        player_loop = QTimer()
        player_loop.timeout.connect(self.player.run)
        player_loop.start()
        self.all_players.currentIndexChanged.connect(self.player_change)
        self.cava = Cava(self)
        cava_thread = threading.Thread(target=self.cava.run)
        cava_thread.start()

    def always_on_top(self, _):
        self.setWindowFlags(self.windowFlags() ^ Qt.WindowStaysOnTopHint)  # type: ignore
        self.show()

    def save_art(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save image", f"{QDir.homePath()}/cover.png", "Images (*.png)")
        if filename != "":
            shutil.copyfile(".art.png", filename)

    def copy_title(self):
        player = self.player.get_chosen_player()
        metadata = player.props.metadata  # type: ignore
        QApplication.clipboard().setText(metadata["xesam:title"])  # type: ignore

    def copy_artists(self):
        player = self.player.get_chosen_player()
        metadata = player.props.metadata  # type: ignore
        QApplication.clipboard().setText(", ".join(metadata["xesam:artist"]))  # type: ignore

    def edit_db(self):
        edit_widget = EditWidget(self)
        edit_widget.show()

    def export_db(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Export saved tracks", f"{QDir.homePath()}/tracks.txt", "Text files (*.txt)")
        if filename == "":
            return
        con = sqlite3.connect("saved_tracks.sqlite")
        cur = con.cursor()
        res = cur.execute("SELECT * FROM Tracks").fetchall()
        with open(filename, "w", encoding="utf8") as file:
            file.write("Your saved tracks :D\nFormat: artists - title (art_url)\n")
            for line in res:
                title = line[1]
                artists = line[2]
                art_url = line[3]
                if title == "":
                    title = "Not found :("
                if artists == "":
                    artists = "Not found :("
                if art_url == "":
                    art_url = "No cover :("
                file.write(f"{artists} - {title} ({art_url})\n")
        con.close()
    def save_to_db(self):
        player = self.player.get_chosen_player()
        metadata = player.props.metadata  # type: ignore
        title, artist, art_url = "\"\"", "\"\"", "\"\""
        if "xesam:title" in metadata.keys():
            title = f"\"{metadata['xesam:title']}\""
        if "xesam:artist" in metadata.keys():
            artist = f"\"{', '.join(metadata['xesam:artist'])}\""
        if "mpris:artUrl" in metadata.keys():
            art_url = f"\"{metadata['mpris:artUrl']}\""
        if title == "\"\"" and artist == "\"\"":
            return
        con = sqlite3.connect("saved_tracks.sqlite")
        cur = con.cursor()
        if not self.track_saved:
            que = f"INSERT INTO Tracks(title, artist, art_url) VALUES ({title}, {artist}, {art_url})"
            icon = QIcon.fromTheme("remove")
            self.track_saved = True
        else:
            que = f"DELETE FROM Tracks WHERE title = {title} AND artist = {artist}"
            icon = QIcon.fromTheme("add")
            self.track_saved = False
        cur.execute(que)
        con.commit()
        con.close()
        self.save_btn.setIcon(icon)


    def playback_change(self):
        player = self.player.get_chosen_player()
        try:
            player.play_pause()  # type: ignore
        except:
            pass

    def next_track(self):
        player = self.player.get_chosen_player()
        try:
            player.next()  # type: ignore
        except:
            pass

    def previous_track(self):
        player = self.player.get_chosen_player()
        try:
            player.previous()  # type: ignore
        except:
            pass

    def loop(self):
        player = self.player.get_chosen_player()
        player_name = player.props.player_name  # type: ignore
        status = subprocess.run(["playerctl", "-p", player_name, "loop"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        status = status.stdout.decode("utf-8").rstrip("\n")
        if status == "None":
            try:
                player.set_loop_status(1)  # type: ignore
                icon = QIcon.fromTheme("media-playlist-repeat-song-symbolic")
                self.loop_btn.setIcon(icon)
            except:
                pass
            return
        elif status == "Track":
            try:
                player.set_loop_status(2)  # type: ignore
                icon = QIcon.fromTheme("media-playlist-repeat-symbolic")
                self.loop_btn.setIcon(icon)
            except:
                pass
            return
        try:
            player.set_loop_status(0)  # type: ignore
            icon = QIcon.fromTheme("media-playlist-no-repeat-symbolic")
            self.loop_btn.setIcon(icon)
        except:
            return

    def shuffle(self):
        player = self.player.get_chosen_player()
        status = player.props.shuffle  # type: ignore
        if status:
            try:
                player.set_shuffle(0)  # type: ignore
                icon = QIcon.fromTheme("media-playlist-no-shuffle-symbolic")
                self.shuffle_btn.setIcon(icon)
            except:
                pass
            return
        try:
            player.set_shuffle(1)  # type: ignore
            icon = QIcon.fromTheme("media-playlist-shuffle-symbolic")
            self.shuffle_btn.setIcon(icon)
        except:
            pass

    def count(self, player_name):
        while True:
            global event
            if not event:
                break
            if player_name == "":
                time.sleep(0.3)
                continue
            if self.holding:
                num = self.slider.value()
                hrs = num // 3600
                used = hrs * 3600
                mins = (num - used) // 60
                used += mins * 60
                secs = num - used
                if hrs < 10:
                    hrs = f"0{hrs}"
                if mins < 10:
                    mins = f"0{mins}"
                if secs < 10:
                    secs = f"0{secs}"
                if hrs == "00" and len(self.time_end.text()) == 5:
                    self.time_now.setText(f"{mins}:{secs}")
                else:
                    self.time_now.setText(f"{hrs}:{mins}:{secs}")
                time.sleep(0.3)
                continue
            result = subprocess.run(["playerctl", "-p", player_name, "position"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = result.stdout.decode("utf-8").rstrip("\n")
            if result == "":
                self.slider.resize(542, 20)
                self.time_now.resize(70, 20)
                self.time_now.move(562, 370)
                self.time_now.setText("00:00:00")
                self.delimeter.move(633, 370)
                self.time_end.resize(70, 20)
                self.time_end.move(640, 370)
                self.time_end.setText(f"00:00:00")
            else:
                num = int(float(result))
                hrs = num // 3600
                used = hrs * 3600
                mins = (num - used) // 60
                used += mins * 60
                secs = num - used
                if hrs < 10:
                    hrs = f"0{hrs}"
                if mins < 10:
                    mins = f"0{mins}"
                if secs < 10:
                    secs = f"0{secs}"
                if hrs == "00" and len(self.time_end.text()) == 5:
                    self.time_now.setText(f"{mins}:{secs}")
                else:
                    self.time_now.setText(f"{hrs}:{mins}:{secs}")
                self.slider.setValue(num)
            time.sleep(0.5)

    def slider_hold(self):
        self.holding = True

    def slider_release(self):
        player = self.player.get_chosen_player()
        if player is None:
            self.holding = False
            return
        name, position = player.props.player_name, self.slider.value()
        subprocess.run(["playerctl", "-p", name, "position", str(position)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.holding = False

    def check_shuffle(self, player):
        status = player.props.shuffle
        if status:
            icon = QIcon.fromTheme("media-playlist-shuffle-symbolic")
            self.shuffle_btn.setIcon(icon)
            return
        icon = QIcon.fromTheme("media-playlist-no-shuffle-symbolic")
        self.shuffle_btn.setIcon(icon)

    def check_loop(self, player_name):
        status = subprocess.run(["playerctl", "-p", player_name, "loop"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        status = status.stdout.decode("utf-8").rstrip("\n")
        if status == "Track":
            icon = QIcon.fromTheme("media-playlist-repeat-song-symbolic")
            self.loop_btn.setIcon(icon)
            return
        elif status == "Playlist":
            icon = QIcon.fromTheme("media-playlist-repeat-symbolic")
            self.loop_btn.setIcon(icon)
            return
        icon = QIcon.fromTheme("media-playlist-no-repeat-symbolic")
        self.loop_btn.setIcon(icon)

    def player_change(self):
        player = self.player.get_chosen_player()
        if player is None:
            self.player.on_metadata_changed(None, None)
            return
        self.player.on_metadata_changed(player, player.props.metadata)  # type: ignore

    def paintEvent(self, _):
        p = QPainter()
        p.begin(self)
        p.setBrush(self.palette().windowText().color())
        for i, bar in enumerate(self.bars):
            p.drawRect(220 + i * 50, 360, 40, -5 + -bar * 5)
        p.end()

    def keyPressEvent(self, event):
        player = self.player.get_chosen_player()
        if player is None:
            return
        if event.key() == Qt.Key_S:  # type: ignore
            self.shuffle_btn.click()
        if event.key() == Qt.Key_R:  # type: ignore
            self.loop_btn.click()
        if event.key() == Qt.Key_Space:  # type: ignore
            self.play_pause_btn.click()
        if event.key() == Qt.Key_Greater:  # type: ignore
            self.next_btn.click()
        if event.key() == Qt.Key_Less:  # type: ignore
            self.prev_btn.click()
        if event.key() == Qt.Key_F:  # type: ignore
            self.save_btn.click()
        if event.key() == Qt.Key_Right:  # type: ignore
            subprocess.run(["playerctl", "-p", player.props.player_name, "position", "5+"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if event.key() == Qt.Key_Left:  # type: ignore
            subprocess.run(["playerctl", "-p", player.props.player_name, "position", "5-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

class EditWidget(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent  # type: ignore
        self.setFixedSize(600, 375)
        self.modified = False
        self.con = sqlite3.connect("saved_tracks.sqlite")
        self.table = QTableWidget(self)
        self.table.resize(600, 300)
        self.table.move(0, 60)
        self.table.itemChanged.connect(self.item_changed)
        self.delete_btn = QPushButton("Delete", self)
        self.delete_btn.resize(100, 40)
        self.delete_btn.move(10, 10)
        self.delete_btn.clicked.connect(self.delete_items)
        icon = QIcon.fromTheme("trash-full")
        self.delete_btn.setIcon(icon)
        self.update_btn = QPushButton("Update", self)
        self.update_btn.resize(100, 40)
        self.update_btn.move(120, 10)
        self.update_btn.clicked.connect(self.load_db)
        icon = QIcon.fromTheme("gtk-refresh")
        self.update_btn.setIcon(icon)
        self.save_btn = QPushButton("Save", self)
        self.save_btn.resize(100, 40)
        self.save_btn.move(380, 10)
        self.save_btn.clicked.connect(self.save_items)
        icon = QIcon.fromTheme("gtk-save")
        self.save_btn.setIcon(icon)
        self.exit_btn = QPushButton("Exit", self)
        self.exit_btn.resize(100, 40)
        self.exit_btn.move(490, 10)
        self.exit_btn.clicked.connect(self.close)  # type: ignore
        icon = QIcon.fromTheme("exit")
        self.exit_btn.setIcon(icon)
        self.load_db()

    def item_changed(self):
        self.modified = True

    def load_db(self):
        if self.modified:
            valid = QMessageBox.question(self, "", "Reset changed data?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if valid == QMessageBox.No:
                return
        cur = self.con.cursor()
        result = cur.execute("SELECT * FROM Tracks").fetchall()
        self.table.clear()
        self.table.setRowCount(len(result))
        self.table.setColumnCount(4)
        for i, elem in enumerate(result):
            for j, val in enumerate(elem):
                self.table.setItem(i, j, QTableWidgetItem(str(val)))
        self.modified = False

    def save_items(self):
        if not self.modified:
            self.statusBar().showMessage("Nothing changed")  # type: ignore
            return
        ids, titles, artists, art_urls = [], [], [], []
        for i in range(self.table.rowCount()):
            if not self.table.item(i, 0).text().isdigit():  # type: ignore
                self.statusBar().showMessage("Id can only be a number")  # type: ignore
                return
            ids.append(int(self.table.item(i, 0).text()))  # type: ignore
            titles.append(f"\"{self.table.item(i, 1).text()}\"")  # type: ignore
            artists.append(f"\"{self.table.item(i, 2).text()}\"")  # type: ignore
            art_urls.append(f"\"{self.table.item(i, 3).text()}\"")  # type: ignore
        tmp = []
        for i in range(self.table.rowCount()):
            tmp.append([ids[i], titles[i], artists[i], art_urls[i]])
        tmp.sort(key=lambda x: x[0])
        ids = list(map(str, ids))
        elems = []
        for i in tmp:
            elems.append(f"({i[0]}, {i[1]}, {i[2]}, {i[3]})")
        valid = QMessageBox.question(self, "", "Overwrite existing data?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if valid == QMessageBox.No:
            return
        cur = self.con.cursor()
        que = f"DELETE FROM Tracks WHERE id IN ({', '.join(ids)})"
        cur.execute(que)
        que = f"INSERT INTO Tracks VALUES {', '.join(elems)}"
        cur.execute(que)
        self.con.commit()
        self.statusBar().showMessage("")  # type: ignore
        self.modified = False
        player = self.parent.player.get_chosen_player()
        if player is not None:
            self.parent.player.on_metadata_changed(player, player.props.metadata)

    def delete_items(self):
        rows = list(set([i.row() for i in self.table.selectedItems()]))
        if not rows:
            self.statusBar().showMessage("Nothing to delete")  # type: ignore
            return
        self.load_db()
        ids = [self.table.item(i, 0).text() for i in rows]  # type: ignore
        if len(ids) == 1:
            msg = f"Delete element with id {ids[0]}?"
        else:
            msg = f"Delete elements with id {', '.join(ids)}?"
        valid = QMessageBox.question(self, "", msg,
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if valid == QMessageBox.No:
            return
        cur = self.con.cursor()
        que = f"DELETE FROM Tracks WHERE id IN ({', '.join(ids)})"
        cur.execute(que)
        self.con.commit()
        self.statusBar().showMessage("")  # type: ignore
        player = self.parent.player.get_chosen_player()
        if player is not None:
            self.parent.player.on_metadata_changed(player, player.props.metadata)

    def closeEvent(self, event):
        if not self.modified:
            event.accept()
        else:
            valid = QMessageBox.question(self, "", "Exit without saving?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if valid == QMessageBox.Yes:
                self.modified = False
                event.accept()
            else:
                event.ignore()


class PlayerManager:
    def __init__(self, parent):
        self.manager = Playerctl.PlayerManager()
        self.loop = GLib.MainLoop()
        self.manager.connect("name-appeared", lambda *args: self.on_player_appeared(*args))
        self.manager.connect("player-vanished", lambda *args: self.on_player_vanished(*args))
        self.parent = parent
        self.dum = threading.Thread(target=self.parent.count, args=("",))
        self.dum.start()
        self.prev = [None, "", ""]
        self.init_players()

    def init_players(self):
        for player in self.manager.props.player_names:
            self.init_player(player)

    def init_player(self, player):
        self.parent.all_players.addItem(player.name)
        player = Playerctl.Player.new_from_name(player)
        player.connect("metadata", self.on_metadata_changed, None)
        player.connect("playback-status", self.on_playback_status_changed, None)
        self.manager.manage_player(player)
        self.on_metadata_changed(player, player.props.metadata)

    def get_players(self):
        return self.manager.props.players

    def get_chosen_player(self):
        players = self.get_players()
        chosen_name = self.parent.all_players.currentText()
        for player in players:
            if player.props.player_name == chosen_name:
                return player
        return None

    def write_output(self, title, artists, art):
        if art[0]:
            try:
                response = requests.get(art[1])
                open(".art.png", "wb").write(response.content)
                self.parent.cover.setStyleSheet("""
                border-radius: 6px;
                border-image: url('.art.png') 0 0 0 0 stretch stretch;
                """)
            except:
                self.parent.cover.setStyleSheet("""
                border-radius: 6px;
                border-image: url('.cover.png') 0 0 0 0 stretch stretch;
                """)
                self.parent.save_art_action.setDisabled(True)
        else:
            self.parent.cover.setStyleSheet("""
            border-radius: 6px;
            border-image: url('.cover.png') 0 0 0 0 stretch stretch;
            """)
        self.parent.title.setText(title)
        self.parent.artist.setText(artists)

    def on_playback_status_changed(self, player, status, _=None):
        current_playing = self.get_chosen_player()
        if current_playing is None:
            return
        if current_playing.props.player_name != player.props.player_name:  # type: ignore
            return
        if status == Playerctl.PlaybackStatus(1):
            icon = QIcon.fromTheme("media-play")
        else:
            icon = QIcon.fromTheme("media-pause")
        self.parent.play_pause_btn.setIcon(icon)

    def on_metadata_changed(self, player, metadata, _=None):
        global event
        self.parent.setFixedSize(720, 400)
        current_playing = self.get_chosen_player()
        if current_playing is None:
            artists = ""
            title = ""
            art = [False, ""]
            self.parent.save_art_action.setDisabled(True)
            self.parent.copy_title_action.setDisabled(True)
            self.parent.copy_artists_action.setDisabled(True)
            self.prev = [None, title, artists]
            event = False
            self.write_output(title, artists, art)
            self.parent.setFixedSize(720, 60)
            return
        elif current_playing.props.player_name != player.props.player_name:  # type: ignore
            return
        artists = "Not found :("
        title = "Not found :("
        if "xesam:artist" in metadata.keys():
            tmp = metadata["xesam:artist"]
            if len(tmp) > 0 and tmp != [""]:
                artists = ", ".join(tmp)
        if "xesam:title" in metadata.keys():
            tmp = metadata["xesam:title"]
            if len(tmp) > 0 and tmp != [""]:
                title = tmp
        if [player, title, artists] == self.prev:
            tmp_title = f"\"{title}\""
            tmp_artists = f"\"{artists}\""
            con = sqlite3.connect("saved_tracks.sqlite")
            cur = con.cursor()
            que = f"SELECT * FROM Tracks WHERE title = {tmp_title} AND artist = {tmp_artists}"
            res = cur.execute(que).fetchone()
            if res:
                self.parent.track_saved = True
                icon = QIcon.fromTheme("remove")
            else:
                self.parent.track_saved = False
                icon = QIcon.fromTheme("add")
            con.close()
            self.parent.save_btn.setIcon(icon)
            return
        self.parent.save_art_action.setDisabled(True)
        self.parent.copy_title_action.setDisabled(True)
        self.parent.copy_artists_action.setDisabled(True)
        if "mpris:artUrl" in metadata.keys():
            art = [True, metadata["mpris:artUrl"]]
            self.parent.save_art_action.setEnabled(True)
        else:
            art = [False, ""]
        if title != "Not found :(":
            self.parent.copy_title_action.setEnabled(True)
        if artists != "Not found :(":
            self.parent.copy_artists_action.setEnabled(True)
        status = player.props.playback_status
        self.on_playback_status_changed(player, status)
        self.parent.check_shuffle(player)
        self.parent.check_loop(player.props.player_name)
        self.write_output(title, artists, art)
        tmp_title = f"\"{title}\""
        tmp_artists = f"\"{artists}\""
        con = sqlite3.connect("saved_tracks.sqlite")
        cur = con.cursor()
        que = f"SELECT * FROM Tracks WHERE title = {tmp_title} AND artist = {tmp_artists}"
        res = cur.execute(que).fetchone()
        if res:
            self.parent.track_saved = True
            icon = QIcon.fromTheme("remove")
        else:
            self.parent.track_saved = False
            icon = QIcon.fromTheme("add")
        con.close()
        self.parent.save_btn.setIcon(icon)
        if player != self.prev[0]:
            event = False
            self.dum.join()
            event = True
            self.dum = threading.Thread(target=self.parent.count, args=(player.props.player_name,))
            self.dum.start()
        if "mpris:length" in metadata.keys():
            lenght = int(str(metadata["mpris:length"])[:-6])
            hrs = lenght // 3600
            used = hrs * 3600
            mins = (lenght - used) // 60
            used += mins * 60
            secs = lenght - used
            if hrs < 10:
                hrs = f"0{hrs}"
            if mins < 10:
                mins = f"0{mins}"
            if secs < 10:
                secs = f"0{secs}"
            if hrs == "00":
                self.parent.slider.resize(590, 20)
                self.parent.time_now.resize(50, 20)
                self.parent.time_now.move(610, 370)
                self.parent.delimeter.move(658, 370)
                self.parent.time_end.resize(50, 20)
                self.parent.time_end.move(660, 370)
                self.parent.time_end.setText(f"{mins}:{secs}")
            else:
                self.parent.slider.resize(542, 20)
                self.parent.time_now.resize(70, 20)
                self.parent.time_now.move(562, 370)
                self.parent.delimeter.move(633, 370)
                self.parent.time_end.resize(70, 20)
                self.parent.time_end.move(640, 370)
                self.parent.time_end.setText(f"{hrs}:{mins}:{secs}")
        else:
            lenght = 0
        self.parent.slider.setRange(0, lenght)
        self.prev = [player, title, artists]

    def on_player_appeared(self, _, player):
        self.init_player(player)

    def on_player_vanished(self, _, player):
        current_name = self.parent.all_players.currentText()
        name = player.props.player_name
        for ind in range(self.parent.all_players.count()):
            if self.parent.all_players.itemText(ind) == name:
                self.parent.all_players.removeItem(ind)
                if name == current_name:
                    self.parent.all_players.setCurrentText("~")
                return

    def run(self):
        self.loop.run()


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


def main():
    global event
    app = QApplication(sys.argv)
    ex = Project()
    ex.show()
    sys.excepthook = except_hook
    app.exec()
    event = False
    sys.exit()


if __name__ == "__main__":
    main()
