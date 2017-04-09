#! python3
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, LargeBinary, create_engine
from sqlalchemy.orm import sessionmaker

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
    user = Column(String)
    
    def __repr__(self):
        return "<Note(dateime='{}', text='{}', user='{}')>".format(self.dateime, self.text, self.user)


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

    '''
    NoteTaker is a multi-user note-taking application that stores notes from multiple users into a single central location asynchronously. The application automatically attaches a timestamp to committed messages and updates all connected clients with the latest messages. It supports plain text editing and can parse MultiMarkdown to display tables and inline images NoteTaker also supports arbitrary attachments.
    '''

    version = '0.0.1'

    def __init__(self, parent=None):
        super(NoteTaker, self).__init__(parent)

        # Build the UI
        self.setup_ui()

        # String that is prepended to the database address listed in the dbconfig text entry
        self.db_type = 'sqlite:///'

        try:
            engine = create_engine(self.db_type + self.dbconfigLineEdit.text(), echo=True)
        except:
            raise
        else:
            self.dbSession = sessionmaker(bind=engine)

        # TODO: Allow for editing or inserting new notes

        # TODO: Attachment mechanism to support one or more arbitrary file types. Support drag and drop.
        
    def setup_ui(self):
        # TODO: Create a "find as you type" field to filter notes
    
        # Set up basic dimensions and central layout
        self.setObjectName("NoteTaker")
        self.resize(850, 600)
        self.centralwidget = QtWidgets.QWidget(self)
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)

        # Define database configuration widget
        self.dbconfigFrame = QtWidgets.QFrame(self.centralwidget)
        self.dbconfigFrame.setMaximumSize(QtCore.QSize(16777215, 45))
        # self.dbconfigFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        # self.dbconfigFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.dbconfigHorizontalLayout = QtWidgets.QHBoxLayout(self.dbconfigFrame)
        self.dbconfigHorizontalLayout.setContentsMargins(0, -1, -1, -1)
        self.dbconfigLabel = QtWidgets.QLabel(self.dbconfigFrame)
        self.dbconfigLabel.setText('Notes Database Path')
        self.dbconfigHorizontalLayout.addWidget(self.dbconfigLabel)
        self.dbconfigLineEdit = QtWidgets.QLineEdit(self.dbconfigFrame)
        # TODO: Remember database from previous session and open automatically
        self.dbconfigLineEdit.setText('notes.db')
        # TODO: Add dropdown to select db type (or detect automatically)
        self.dbconfigHorizontalLayout.addWidget(self.dbconfigLineEdit)
        self.loadDatabaseButton = QtWidgets.QPushButton(self.dbconfigFrame)
        self.loadDatabaseButton.setText('Load database')
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
        self.filterLineEdit.textChanged.connect(self.updateTableView)
        self.filterHorizontalLayout.addWidget(self.filterLineEdit)
        self.verticalLayout.addWidget(self.filterFrame)

        # Define View and Edit windows
        self.splitter = QtWidgets.QSplitter(self.centralwidget)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setHandleWidth(10)
        self.splitter.setChildrenCollapsible(False)
        self.tableWidget = QtWidgets.QTableWidget(self.splitter)
        self.tableWidget.setColumnCount(0)
        self.tableWidget.setRowCount(0)
        self.dbconfigFrame = QtWidgets.QFrame(self.splitter)
        self.dbconfigFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.dbconfigFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.dbconfigFrame)
        self.horizontalLayout.setContentsMargins(0, -1, -1, -1)
        self.textEdit = QtWidgets.QPlainTextEdit(self.dbconfigFrame)
        # TODO: Set textEdit as a monospace typeface
        self.textEdit.viewport().setProperty("cursor", QtGui.QCursor(QtCore.Qt.IBeamCursor))
        self.horizontalLayout.addWidget(self.textEdit)
        self.commitButton = QtWidgets.QPushButton(self.dbconfigFrame)
        self.commitButton.setText('Commit')
        self.horizontalLayout.addWidget(self.commitButton)
        self.verticalLayout.addWidget(self.splitter)

        # Define statusbar and toolbar
        self.statusbar = QtWidgets.QStatusBar(self)
        self.setStatusBar(self.statusbar)

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
        self.actionExit.triggered.connect(self.close)

        # Edit menu options
        self.actionPrefs = QtWidgets.QAction('&Preferences', self)
        self.actionPrefs.setShortcut('Ctrl+P')
        self.actionPrefs.setStatusTip('Edit preferences')
        self.actionPrefs.setStatusTip('Edit preferences')
        # self.actioPrefs.triggered.connect(self.onPrefsClicked)

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
        self.menuHelp.addAction(self.actionAbout)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuEdit.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())

        self.setCentralWidget(self.centralwidget)

    def updateTableView(self):
        self.statusbar.showMessage('Entered text "{}"'.format(self.filterLineEdit.text()), 2000)

    def _about(self):
        '''
        Opens a dialog showing information about the program
        :return: None
        '''
        QtWidgets.QMessageBox.about(self, 'About NoteTaker Tool', 'Python NoteTaker Tool'
                                                          '\nVersion {}'
                                                          '\nCopyright 2017'.format(self.version))
                                                          
if __name__ == '__main__':

    # Connect to an existing QApplication instance if using interactive console
    try:
        app = QtWidgets.QApplication(sys.argv)
    except RuntimeError:
        app = QtWidgets.QApplication.instance()

    f = NoteTaker()
    f.show()
    sys.exit(app.exec_())
