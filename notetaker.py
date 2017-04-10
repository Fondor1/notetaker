#! python3
import sys
import datetime as dt
import logging
import faulthandler
from passlib.hash import pbkdf2_sha256
from PyQt5 import QtCore, QtGui, QtWidgets
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, LargeBinary, ForeignKey, create_engine, or_
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('notetaker')

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String)
    pwhash = Column(String)

    def __repr__(self):
        return "<User(username='{}', pwhash='{}')>".format(self.username, self.pwhash)

       
class Note(Base):
    __tablename__ = 'note'
    
    # Contains only the latest edited notes for any given item 
    id = Column(Integer, primary_key=True)
    datetime = Column(DateTime)
    text = Column(String)
    user = Column(String, ForeignKey('user.username'))
    last_update = Column(DateTime)
    
    def __repr__(self):
        return "<Note(datetime='{}', text='{}', user='{}', last_update='{}')>"\
            .format(self.datetime, self.text, self.user, self.last_update)

    def __getitem__(self, item):
        return (self.datetime, self.text, self.user, self.last_update)[item]


class Attachment(Base):
    __tablename__ = 'attachment'
    
    id = Column(Integer, primary_key=True)
    # Filename or other identifier
    name = Column(String)
    data = Column(LargeBinary)
    # note_id is the id of the note with which this attachment is associated
    note_id = Column(Integer)
    
    def __repr__(self):
        return "<Attachment(name='{}', data='BINARY', note_id='{}')>".format(self.name, self.note_id)


class Log(Base):
    __tablename__ = 'log'
    
    # Log records every note transaction (both new and edits)
    # Does not handle attachments
    # TODO: Set up triggers to support automatic logging
    id = Column(Integer, primary_key=True)
    # timestamp when the insertion/edit was made
    timestamp = Column(DateTime)
    # text is the 
    text = Column(String)

    def __repr__(self):
        return "<Log(timestamp='{}', text='{}')>".format(self.timestamp, self.text)


class NoteTaker(QtWidgets.QMainWindow):

    """
    NoteTaker is a multi-user note-taking application that stores notes from multiple users into a single central 
    location asynchronously. The application automatically attaches a timestamp to committed messages and updates 
    all connected clients with the latest messages. It supports plain text editing and can parse MultiMarkdown to 
    display tables and inline images. NoteTaker also supports arbitrary attachments.
    """

    version = '0.1.0'

    def __init__(self, parent=None):
        super(NoteTaker, self).__init__(parent)

        self.db_type = 'sqlite:///'

        # TODO: Create dialog or other username/pw combo entry. Validate user info with user table
        self.current_user = None

        # Build the UI
        self.setup_ui()

        # String that is prepended to the database address listed in the dbconfig text entry

        # TODO: Automatically check for updates to notes

        # TODO: Allow editing or inserting new notes

        # TODO: Attachment mechanism to support one or more arbitrary file types. Support drag and drop.
        
    def setup_ui(self):
        # Set up basic dimensions and central layout
        self.setWindowTitle("NoteTaker")
        self.resize(850, 600)
        self.centralwidget = QtWidgets.QWidget(self)
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)

        # Define database configuration widget
        self.dbconfigFrame = QtWidgets.QFrame(self.centralwidget)
        self.dbconfigFrame.setMaximumSize(QtCore.QSize(16777215, 45))
        self.dbconfigHorizontalLayout = QtWidgets.QHBoxLayout(self.dbconfigFrame)
        self.dbconfigHorizontalLayout.setContentsMargins(0, -1, -1, -1)
        self.dbconfigLabel = QtWidgets.QLabel(self.dbconfigFrame)
        self.dbconfigLabel.setText('Notes Database Path')
        self.dbconfigHorizontalLayout.addWidget(self.dbconfigLabel)
        self.dbconfigLineEdit = QtWidgets.QLineEdit(self.dbconfigFrame)
        # TODO: Remember database from previous session and open automatically
        # TODO: Make this field an editable dropdown that remembers up to N previous databases
        self.dbconfigLineEdit.setText('notes.db')
        # Set up data model
        self.sourceTableModel = NoteTakerTableModel(self.db_type, self.dbconfigLineEdit.text())
        self.proxyTableModel = NoteTakerSortFilterProxyModel()
        self.proxyTableModel.setSourceModel(self.sourceTableModel)
        # TODO: Add dropdown to select db type (or detect automatically)
        self.dbconfigHorizontalLayout.addWidget(self.dbconfigLineEdit)
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
        self.filterFrame.setMaximumSize(QtCore.QSize(16777215, 45))
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
        self.tableView.resizeColumnsToContents()
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
        self.textEdit = QtWidgets.QPlainTextEdit(self.noteFrame)
        self.textEdit.setFont(QtGui.QFont('Courier New'))   # Probably not cross platform
        self.textEdit.viewport().setProperty("cursor", QtGui.QCursor(QtCore.Qt.IBeamCursor))
        self.horizontalLayout.addWidget(self.textEdit)
        self.commitButton = QtWidgets.QPushButton(self.noteFrame)
        self.commitButton.setText('Commit')
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
        self.actionLoad = QtWidgets.QAction(QtGui.QIcon.fromTheme("document-open"), '&Load Config', self)
        self.actionLoad.setShortcut('Ctrl+L')
        self.actionLoad.setStatusTip('Load a NoteTaker database')
        # self.actionLoad.triggered.connect(self.onLoadClicked)

        self.actionExport = QtWidgets.QAction(QtGui.QIcon.fromTheme("document-save-as"), '&Export Notes', self)
        self.actionExport.setShortcut('Ctrl+S')
        self.actionExport.setStatusTip('Export notes')
        # self.actionSave.triggered.connect(self.onExportClicked)

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

        if self.current_user:
            result = self.sourceTableModel.commit_new_note(self.textEdit.toPlainText(), self.current_user)
            self.textEdit.clear()
            self.statusbar.showMessage(result)
            self.tableView.scrollToBottom()
            self.tableView.resizeColumnToContents(2)
            self.tableView.resizeRowsToContents()

    def user_dialog(self):
        # TODO: Show currently logged in user in the GUI
        login = Login()
        login.exec_()
        username, pw = login.get_creds()

        if self.sourceTableModel.is_valid_user(user=username, passwd=pw):
            self.current_user = username
        else:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setText('Incorrect Username or Password')
            msg.setWindowTitle('Invalid Credentials')
            msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
            msg.exec_()

    def load_database(self):
        result = self.sourceTableModel.initiate_db_connection(self.db_type, self.dbconfigLineEdit.text())
        self.statusbar.showMessage(result)
        self.tableView.scrollToBottom()

    def filter_view(self):
        filter_txt = self.filterLineEdit.text()
        logger.debug(filter_txt)
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


class NoteTakerSortFilterProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self, parent=None):
        super(NoteTakerSortFilterProxyModel, self).__init__(parent)
        # Currently passes everything through without filtering.

    def update_table_view(self, filter_txt):
        search = QtCore.QRegExp(filter_txt, QtCore.Qt.CaseInsensitive, QtCore.QRegExp.Wildcard)
        self.setFilterRegExp(search)
        self.setFilterKeyColumn(1)


class NoteTakerTableModel(QtCore.QAbstractTableModel):
    # http://pyqt.sourceforge.net/Docs/PyQt4/qabstracttablemodel.html

    def __init__(self, db_type, db, update_rate=2000, parent=None):
        super(NoteTakerTableModel, self).__init__(parent)
        self.session = None
        self.datatable = None
        self.header = ('Creation Date', 'Text', 'User', 'Last Modified')

        self.initiate_db_connection(db_type, db)

        self.dataUpdateTimer = QtCore.QTimer(self)
        self.dataUpdateTimer.timeout.connect(self.refresh_data)
        self.dataUpdateTimer.startTimer(update_rate)

    def initiate_db_connection(self, db_type, db):
        # Connect to the database specified
        # TODO: Check for existence of db, if not present ask user if they wish to create
        if self.session:
            self.session.close()
        try:
            engine = create_engine(db_type + db, echo=True)
            Base.metadata.create_all(engine)
            dbSession = sessionmaker(bind=engine)
            self.session = dbSession()
        except:
            # Not sure yet what error types we might encounter, so raise everything for now
            raise
        else:
            # TODO: Update GUI with db connection status
            # self.setWindowTitle('{} - {}'.format('NoteTaker', db))
            # self.update_table_view()
            self.refresh_data()
            logger.debug('Completed db connection')
            return 'Successfully connected to "{}"'.format(db)

    def commit_new_note(self, text, user):
        logger.debug('Initiating commit of new note')
        # TODO: Check for any attachments and add if present
        datetime = dt.datetime.now()
        logger.debug('Trying to add note "{}", "{}", "{}"'.format(datetime, text, user))
        note = Note(datetime=datetime, text=text, user=user, last_update=datetime)
        try:
            self.session.add(note)
            self.session.commit()
        except Exception as e:
            logger.error('Failed to commit: {}'.format(repr(e)))
            raise
        else:
            logger.info('Committed note')
            self.refresh_data()
            return 'Note Committed Successfully'

    def update_table_view(self):
        # self.statusbar.showMessage('Updating table view', 1000)
        # Query the database for notes
        # filter_text = self.filterLineEdit.text()
        # if filter_text:
        #     # If user typed text for filtering, filter based on all available parameters
        #     rowlist = [r for r in self.session.query(Note).\
        #         filter(or_(Note.text.ilike('%{}%'.format(filter_text)),
        #                    Note.user.ilike('%{}%'.format(filter_text)),
        #                    Note.datetime.ilike('%{}%'.format(filter_text)),
        #                    Note.last_update.ilike('%{}%'.format(filter_text)))).\
        #         order_by(Note.datetime)]
        # else:
        #     rowlist = [r for r in self.session.query(Note).order_by(Note.datetime)]
        # for r in rowlist:
        #     print(repr(r))
        pass

    def refresh_data(self):
        # TODO: Add timer to refresh data automatically. Add option to set time in preferences dialog
        try:
            self.layoutAboutToBeChanged.emit()
            self.datatable = [d for d in self.session.query(Note).order_by(Note.datetime).all()]
        except AttributeError:
            raise
        else:
            logger.debug('Fetched new data')
            self.layoutChanged.emit()

    def rowCount(self, parent=QtCore.QModelIndex(), *args, **kwargs):
        try:
            # count = self.session.query(Note).count()
            count = len(self.datatable)
        except AttributeError:
            return 0
        else:
            return count

    def columnCount(self, parent=QtCore.QModelIndex(), *args, **kwargs):
        return len(self.header)

    def headerData(self, p_int, orientation=QtCore.Qt.Horizontal, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return self.header[p_int]

    def data(self, QModelIndex, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            i = QModelIndex.row()
            j = QModelIndex.column()
            return '{}'.format(self.datatable[i][j])
        else:
            return QtCore.QVariant()

    def flags(self, QModelIndex):
        # TODO: Allow copying
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    def close(self):
        self.session.close()

    def is_valid_user(self, user, passwd):
        for un, pwhash in self.session.query(User.username, User.pwhash).filter(User.username == user):
            logger.debug('Found user in database. {}'.format(un))
            # TODO: Fix static value
            # return True
            return pbkdf2_sha256.verify(passwd, pwhash)


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

    logfile = open('faulthandler.log', 'a')
    fh = faulthandler.enable(logfile)

    # Connect to an existing QApplication instance if using interactive console
    try:
        app = QtWidgets.QApplication(sys.argv)
    except RuntimeError:
        app = QtWidgets.QApplication.instance()

    f = NoteTaker()
    f.show()
    sys.exit(app.exec_())
