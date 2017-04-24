#! python3
import sys
import logging
import os.path
from Qt import QtCore, QtGui, QtWidgets
from notetaker_db import NoteTakerSortFilterProxyModel, NoteTakerTableModel

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('notetaker')


class NoteTaker(QtWidgets.QMainWindow):

    """
    NoteTaker is a multi-user note-taking application that stores notes from multiple users into a single central 
    location asynchronously. The application automatically attaches a timestamp to committed messages and updates 
    all connected clients with the latest messages. It supports plain text editing and can parse MultiMarkdown to 
    display tables and inline images. NoteTaker also supports arbitrary attachments.
    """

    version = '0.1.2'

    def __init__(self, parent=None):
        super(NoteTaker, self).__init__(parent)

        self.db_type = 'sqlite:///'

        # TODO: Support opening a db based on passed-in arguments
        self.current_user = None
        self.current_db = None

        # Build the UI
        self.setup_ui()

        # TODO: Automatically check for updates to notes

        # TODO: Allow editing or inserting new notes

        # TODO: Attachment mechanism to support one or more arbitrary file types. Support drag and drop.
        
    def setup_ui(self):
        # Set up basic dimensions and central layout
        self.program_title = 'NoteTaker'
        self.resize(850, 600)
        self.centralwidget = QtWidgets.QWidget(self)
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)

        # Define database configuration widget
        self.dbconfigFrame = QtWidgets.QFrame(self.centralwidget)
        # self.dbconfigFrame.setMaximumSize(QtCore.QSize(16777215, 55))
        self.dbconfigHorizontalLayout = QtWidgets.QHBoxLayout(self.dbconfigFrame)
        self.dbconfigHorizontalLayout.setContentsMargins(0, -1, -1, -1)
        self.dbconfigLabel = QtWidgets.QLabel(self.dbconfigFrame)
        self.dbconfigLabel.setText('Notes Database Path')
        self.dbconfigHorizontalLayout.addWidget(self.dbconfigLabel)
        self.dbconfigLineEdit = QtWidgets.QLineEdit(self.dbconfigFrame)
        self.dbconfigComboBox = QtWidgets.QComboBox(self.dbconfigFrame)
        self.dbconfigComboBox.setEditable(True)
        self.dbconfigComboBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        self.dbconfigComboBox.setLineEdit(self.dbconfigLineEdit)
        # TODO: Remember database from previous session and open automatically
        # TODO: Make this field an editable dropdown that remembers up to N previous databases
        self.dbconfigLineEdit.setText('notes.db')
        # Set up data model
        self.sourceTableModel = NoteTakerTableModel(self.db_type, self.dbconfigLineEdit.text())
        self.current_db = self.dbconfigLineEdit.text()
        self.proxyTableModel = NoteTakerSortFilterProxyModel()
        self.proxyTableModel.setSourceModel(self.sourceTableModel)
        # TODO: Add dropdown to select db type (or detect automatically)
        # self.dbconfigHorizontalLayout.addWidget(self.dbconfigLineEdit)
        self.dbconfigHorizontalLayout.addWidget(self.dbconfigComboBox)
        self.browseDatabaseButton = QtWidgets.QPushButton(self.dbconfigFrame)
        self.browseDatabaseButton.setText('Browse for database')
        self.browseDatabaseButton.clicked.connect(self.browse_db_connection)
        self.dbconfigHorizontalLayout.addWidget(self.browseDatabaseButton)
        self.loadDatabaseButton = QtWidgets.QPushButton(self.dbconfigFrame)
        self.loadDatabaseButton.setText('Load selected database')
        self.loadDatabaseButton.clicked.connect(self.load_database)
        self.dbconfigHorizontalLayout.addWidget(self.loadDatabaseButton)
        self.verticalLayout.addWidget(self.dbconfigFrame)

        # Define text filter
        self.filterFrame = QtWidgets.QFrame(self.centralwidget)
        # self.filterFrame.setMaximumSize(QtCore.QSize(16777215, 55))
        self.filterHorizontalLayout = QtWidgets.QHBoxLayout(self.filterFrame)
        self.filterHorizontalLayout.setContentsMargins(0, -1, -1, -1)
        self.filterHorizontalLabel = QtWidgets.QLabel(self.filterFrame)
        self.filterHorizontalLabel.setText('Filter')
        self.filterHorizontalLayout.addWidget(self.filterHorizontalLabel)
        self.filterLineEdit = QtWidgets.QLineEdit(self.filterFrame)
        # TODO: Implement find-as-you-type to encompass date
        self.filterLineEdit.textChanged.connect(self.filter_view)
        self.filterHorizontalLayout.addWidget(self.filterLineEdit)
        self.verticalLayout.addWidget(self.filterFrame)

        # Define View and Edit windows
        self.splitter = QtWidgets.QSplitter(self.centralwidget)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setHandleWidth(10)
        self.splitter.setChildrenCollapsible(False)
        self.tableView = QtWidgets.QTableView(self.splitter)
        self.tableView.setModel(self.proxyTableModel)
        self.tableView.setFont(QtGui.QFont('Courier New'))   # Probably not cross platform
        self.tableView.setSortingEnabled(True)
        # TODO: Fix sorting (most recent at bottom)
        self.tableView.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.tableView.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.tableView.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.noteFrame = QtWidgets.QFrame(self.splitter)
        self.noteFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.noteFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.noteFrame)
        self.horizontalLayout.setContentsMargins(0, -1, -1, -1)
        self.textEdit = PlainTextEditWithAttachments(self.noteFrame)
        self.textEdit.setFont(QtGui.QFont('Courier New'))   # Probably not cross platform
        self.textEdit.viewport().setProperty("cursor", QtGui.QCursor(QtCore.Qt.IBeamCursor))
        self.horizontalLayout.addWidget(self.textEdit)
        self.attachmentWidget = QtWidgets.QListWidget()
        self.attachmentWidget.hide()
        self.horizontalLayout.addWidget(self.attachmentWidget)
        self.commitButton = QtWidgets.QPushButton(self.noteFrame)
        self.commitButton.setText('Commit')
        self.commitButton.setStatusTip('Click or press Control+Enter to commit this message to the database')
        self.commitButton.clicked.connect(self.commit_new_note)
        QtWidgets.QShortcut(QtGui.QKeySequence('Ctrl+Return'), self, self.commit_new_note)
        QtWidgets.QShortcut(QtGui.QKeySequence('Ctrl+Enter'), self, self.commit_new_note)
        self.horizontalLayout.addWidget(self.commitButton)
        self.verticalLayout.addWidget(self.splitter)

        # Define statusbar and toolbar
        self.statusbar = QtWidgets.QStatusBar(self)
        self.setStatusBar(self.statusbar)

        # TODO: Allow user to create custom hotkey-able buttons to insert common text e.g. "Test complete. Pass"
        self.toolBar = QtWidgets.QToolBar(self)
        self.addToolBar(QtCore.Qt.TopToolBarArea, self.toolBar)

        # Define the menu
        self.menubar = QtWidgets.QMenuBar()
        self.menuFile = self.menubar.addMenu('&File')
        self.menuEdit = self.menubar.addMenu('&Edit')
        self.menuHelp = self.menubar.addMenu('&Help')
        self.setMenuBar(self.menubar)

        # File menu options
        self.actionLoad = QtWidgets.QAction(QtGui.QIcon.fromTheme("document-open"), '&Load Database', self)
        self.actionLoad.setShortcut('Ctrl+L')
        self.actionLoad.setStatusTip('Load a NoteTaker database')
        self.actionLoad.triggered.connect(self.browse_db_connection)

        self.actionExport = QtWidgets.QAction(QtGui.QIcon.fromTheme("document-save-as"), '&Export Notes', self)
        self.actionExport.setShortcut('Ctrl+S')
        self.actionExport.setStatusTip('Export notes')
        self.actionExport.triggered.connect(self.onExportClicked)

        self.actionExit = QtWidgets.QAction('&Exit', self)
        self.actionExit.setShortcut('Ctrl+Q')
        self.actionExit.setStatusTip('Exit application')
        self.actionExit.triggered.connect(self._exit)

        # Edit menu options
        self.actionPrefs = QtWidgets.QAction('&Preferences', self)
        self.actionPrefs.setShortcut('Ctrl+P')
        self.actionPrefs.setStatusTip('Edit preferences')
        # self.actioPrefs.triggered.connect(self.onPrefsClicked)

        self.userDialog = QtWidgets.QAction('&Change User', self)
        self.userDialog.setStatusTip('Change currently logged in user')
        self.userDialog.triggered.connect(self.user_dialog)

        # Help Menu options
        self.actionAbout = QtWidgets.QAction(QtGui.QIcon.fromTheme('system-help'), '&About', self)
        self.actionAbout.setStatusTip('Version and Copyright information')
        self.actionAbout.triggered.connect(self._about)

        self.menuFile.addAction(self.actionLoad)
        self.menuFile.addAction(self.actionExport)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionExit)
        self.menuHelp.addAction(self.actionAbout)
        self.menuEdit.addAction(self.actionPrefs)
        self.menuEdit.addAction(self.userDialog)
        self.menuHelp.addAction(self.actionAbout)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuEdit.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())

        self.setWindowTitle('{} - {} - {}'.format(self.program_title, self.current_user, self.current_db))
        
        self.setCentralWidget(self.centralwidget)
        

    def browse_db_connection(self):
        fl = QtWidgets.QFileDialog.getOpenFileName(caption='Open database file', directory='')
        if any(fl):
            self.dbconfigLineEdit.setText(fl[0])

    def commit_new_note(self):
        attempts = 0
        while not self.current_user and attempts < 3:
            self.user_dialog()
            attempts += 1

        if self.current_user:  # If someone is properly logged in
            result = self.sourceTableModel.commit_new_note(self.textEdit.toPlainText(), self.current_user, )
            self.textEdit.clear()
            self.statusbar.showMessage(result)
            self.tableView.resizeColumnToContents(0)
            self.tableView.resizeColumnToContents(2)
            self.tableView.resizeColumnToContents(3)
            self.tableView.resizeColumnToContents(4)
            self.tableView.resizeRowsToContents()
            self.tableView.scrollToBottom()
            
    def onExportClicked(self):
        # TODO: Pop up a window if data is filtered and ask if user would like filtered or all data exported
        if self.filterLineEdit.text() != '':
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Question)
            msg.setText('The current view is filtered. Select Yes to export only the visible data or No to export all available data.')
            msg.setWindowTitle('Export Selection?')
            msg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel)
            result = msg.exec_()
            if result == QtWidgets.QMessageBox.Yes:
                export_flag = 'filtered'
            elif result == QtWidgets.QMessageBox.No:
                export_flag = 'all'
            else:
                logger.debug('User cancelled save')
                return
        else:
            export_flag = 'all'
 
        path = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File', '', 'CSV (*.csv)')[0]
        if path != '':
            logger.debug('Found a file to save to: {}'.format(path))
            if export_flag == 'filtered':
                self.proxyTableModel.export_data_filt(path)
            elif export_flag == 'all':
                self.sourceTableModel.export_data(path)
            else:
                logger.warning('Export option "{}" not configured'.format(repr(export_flag))) 
            logger.debug('Export complete')
            self.statusbar.showMessage('Export complete! File saved as "{}"'.format(path))
        else:
            logger.debug('User cancelled save')
            

    def user_dialog(self):
        # TODO: Show currently logged in user in the GUI
        # TODO: allow config file to populate table 'user' when a new database is generated
        login = Login()
        login.exec_()
        username, pw = login.get_creds()

        if self.sourceTableModel.is_valid_user(user=username, passwd=pw):
            self.current_user = username
            self.statusbar.showMessage('Successfully logged in as "{}"'.format(self.current_user), 10000)
            self.setWindowTitle('{} - {} - {}'.format(self.program_title, self.current_user, self.current_db))
        else:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setText('Incorrect Username or Password')
            msg.setWindowTitle('Invalid Credentials')
            msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
            msg.exec_()

    def load_database(self):
        result = self.sourceTableModel.initiate_db_connection(self.db_type, self.dbconfigLineEdit.text())
        if result:
            self.current_db = result
            self.setWindowTitle('{} - {} - {}'.format(self.program_title, self.current_user, self.current_db))
            self.statusbar.showMessage('Successfully connected to "{}"'.format(self.current_db), 10000)
            self.tableView.resizeColumnToContents(0)
            self.tableView.resizeColumnToContents(2)
            self.tableView.resizeColumnToContents(3)
            self.tableView.resizeColumnToContents(4)
            self.tableView.resizeRowsToContents()
            self.tableView.scrollToBottom()
            # Ensure user logs in again when a new database is loaded
            # TODO: Determine if current database is being just reloaded or if a new database is being requested. If just reloaded, no need to re-ask for username
            self.current_user = None

    def filter_view(self):
        filter_txt = self.filterLineEdit.text()
        logger.debug('Filtering text "{}"'.format(filter_txt))
        self.proxyTableModel.update_table_view(filter_txt)

    def closeEvent(self, *args, **kwargs):
        # Catch all types of close events to handle database closing gracefully
        self._exit()

    def _exit(self):
        logger.debug('Closing database sessions')
        self.sourceTableModel.close()
        self.close()

    def _about(self):
        '''
        Opens a dialog showing information about the program
        :return: None
        '''
        QtWidgets.QMessageBox.about(self, 'About NoteTaker Tool', 'Python NoteTaker Tool'
                                                          '\nVersion {}'
                                                          '\nCopyright 2017'.format(self.version))


class PlainTextEditWithAttachments(QtWidgets.QPlainTextEdit):
    def __init__(self, parent=None):
        """
        Creates a PlainText edit box that supports arbitrary attachments
        """
        super(PlainTextEditWithAttachments, self).__init__(parent)
        self.setAcceptDrops(True)
        
    def dragEnterEvent(self, e):
        e.accept()

    def dropEvent(self, e):

        # position = e.pos()
        # self.btn.move(position)

        # e.setDropAction(QtCore.Qt.MoveAction)
        logger.debug(repr(e.mimeData))
        e.accept()
        
        if e.mimeData().hasFormat('text/uri-list'):
            files = str(e.mimeData().data('text/uri-list')).split('\r\n')
            files = [f.rstrip('\x00\r\n').replace('file:///', '') for f in files]
            logger.debug('Found the following files:')
            for f in files:
                logger.debug(repr(f))
                # if f:
                    # ext = os.path.splitext(f)[1].lower()
                    # if ext in ['.xls', '.xlsx', '.txt']:
                        # e.accept()
                        # return
                    # if ext == '.txt':
                        # e.accept()
                        # return
            # e.ignore()

class listWidget(QtWidgets.QListWidget):
    def __init__(self, parent=None):
        """
        Creates a list widget with custom key handlers
        """
        
    def keyPressEvent(self, e):
        """Overrides keyPressEvent of QListWidget.
 
        https://deptinfo-ensip.univ-poitiers.fr/ENS/pyside-docs/PySide/QtGui/QKeyEvent.html#PySide.QtGui.QKeyEvent
        Args:
            e: type QKeyEvent.
        """
        
        # TODO: Ensure this works for listWidgets. Was originally written for a QTableView
        if e.key() == QtCore.Qt.Key_Delete:
            # Get the selected cells
            selectedIndexes = self.selectedIndexes()
            # Sort the cells in reverse row order (Delete backwards from the end or we'll have trouble!)
            sortedSelection = sorted(selectedIndexes, key=lambda r: r.row(), reverse=True)
 
            # Since we are selecting full rows, we'll get a selection entry for each column!
            # Track which columns have already been deleted
            deleted_rows = []
            for s in sortedSelection:
                if not s.row() in deleted_rows:
                    deleted_rows.append(s.row())
                    self.model().removeRows(s.row(), 1)
        else:
            super(listWidget, self).keyPressEvent(e)
                                                          
                                                          
class Login(QtWidgets.QDialog):
    def __init__(self):
        """
        Creates a login dialog
        """
        super(Login, self).__init__()
        self._username = None
        self._password = None
        self.description = QtWidgets.QLabel('Please enter username and password')
        self.textName = QtWidgets.QLineEdit(self)
        self.textPass = QtWidgets.QLineEdit(self)
        self.textPass.setEchoMode(QtWidgets.QLineEdit.Password)
        self.buttonLogin = QtWidgets.QPushButton('Submit', self)
        self.buttonLogin.clicked.connect(self.handle_login)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.description)
        layout.addWidget(self.textName)
        layout.addWidget(self.textPass)
        layout.addWidget(self.buttonLogin)
        self.setWindowTitle('Credentials required')

    def handle_login(self):
        self.set_username(self.textName.text())
        self.set_password(self.textPass.text())
        self.accept()

    def get_creds(self):
        return self._username, self._password

    def get_username(self):
        return self._username

    def get_password(self):
        return self._password

    def set_password(self, pw):
        self._password = pw

    def set_username(self, un):
        self._username = un


if __name__ == '__main__':

    # Connect to an existing QApplication instance if using interactive console
    try:
        app = QtWidgets.QApplication(sys.argv)
    except RuntimeError:
        app = QtWidgets.QApplication.instance()

    f = NoteTaker()
    f.show()
    sys.exit(app.exec_())
