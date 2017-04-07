#! python3
import sys
import datetime
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

        # TODO: Create database connection
        engine = create_engine('notes.db', echo=True)
        
        Session = sessionmaker(bind=engine)

        # TODO: Allow for editing or inserting new notes

        # TODO: Attachment mechanism to support one or more arbitrary file types. Support drag and drop.
        
    def setup_ui(self):
        # TODO: Create a "find as you type" field to filter notes
    
        # Set up basic dimensions and central layout
        self.setObjectName("NoteTaker")
        self.resize(850, 600)
        self.centralwidget = QtWidgets.QWidget(self)
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.frame = QtWidgets.QFrame(self.centralwidget)
        self.frame.setMaximumSize(QtCore.QSize(16777215, 45))
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)

        # Define database configuration widget
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.frame)
        self.horizontalLayout_2.setContentsMargins(0, -1, -1, -1)
        self.label = QtWidgets.QLabel(self.frame)
        self.label.setText('Notes Database Path')
        self.horizontalLayout_2.addWidget(self.label)
        self.lineEdit = QtWidgets.QLineEdit(self.frame)
        self.horizontalLayout_2.addWidget(self.lineEdit)
        self.loadDatabaseButton = QtWidgets.QPushButton(self.frame)
        self.loadDatabaseButton.setText('Load database')
        self.horizontalLayout_2.addWidget(self.loadDatabaseButton)

        # Define View and Edit windows
        self.verticalLayout.addWidget(self.frame)
        self.splitter = QtWidgets.QSplitter(self.centralwidget)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setHandleWidth(10)
        self.splitter.setChildrenCollapsible(False)
        self.tableWidget = QtWidgets.QTableWidget(self.splitter)
        self.tableWidget.setColumnCount(0)
        self.tableWidget.setRowCount(0)
        self.frame = QtWidgets.QFrame(self.splitter)
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.frame)
        self.horizontalLayout.setContentsMargins(0, -1, -1, -1)
        self.textEdit = QtWidgets.QPlainTextEdit(self.frame)
        # TODO: Set textEdit as a monospace typeface
        self.textEdit.viewport().setProperty("cursor", QtGui.QCursor(QtCore.Qt.IBeamCursor))
        self.horizontalLayout.addWidget(self.textEdit)
        self.commitButton = QtWidgets.QPushButton(self.frame)
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
