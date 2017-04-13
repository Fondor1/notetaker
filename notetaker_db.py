import logging
import csv
import datetime as dt
from Qt import QtCore, QtGui, QtWidgets
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, LargeBinary, ForeignKey, create_engine, or_
from sqlalchemy.orm import sessionmaker
from passlib.hash import pbkdf2_sha256

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

        
class NoteTakerSortFilterProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self, parent=None):
        """
        Model used to filter the NoteTakerTableModel based on user entries
        """
        super(NoteTakerSortFilterProxyModel, self).__init__(parent)
        self.header = ('Creation Date', 'Text', 'User', 'Last Modified', 'Attachments')

    def update_table_view(self, filter_txt):
        search = QtCore.QRegExp(filter_txt, QtCore.Qt.CaseInsensitive, QtCore.QRegExp.Wildcard)
        self.setFilterRegExp(search)
        self.setFilterKeyColumn(1)
        
    def export_data_filt(self, path):
        export_list = []
        for row in range(self.rowCount()):
            logger.debug(row)
            rowdata = {}
            for col in range(self.columnCount()):
                rowdata[self.header[col]] = self.data(self.createIndex(row, col))
            export_list.append(rowdata)
        with open(path, 'w') as fl:
            writer = csv.DictWriter(fl, fieldnames=self.header)
            writer.writeHeader()
            for line in rowdata:
                writer.writeline(line)                


class NoteTakerTableModel(QtCore.QAbstractTableModel):
    def __init__(self, db_type, db, update_rate=2000, parent=None):
        """
        Model used to interact with the database via sqlalchemy
        """
        super(NoteTakerTableModel, self).__init__(parent)
        self.session = None
        self.datatable = [[]]
        self.header = ('Creation Date', 'Text', 'User', 'Last Modified', 'Attachments')

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
            self.refresh_data()
            logger.debug('Completed db connection to "{}"'.format(db))
            return '{}'.format(db)

    def commit_new_note(self, text, user, attach=None):
        logger.debug('Initiating commit of new note')
        # TODO: Check for any attachments and add if present
        datetime = dt.datetime.now()
        logger.debug('Trying to add note "{}", "{}", "{}"'.format(datetime, text, user))
        note = Note(datetime=datetime, text=text, user=user, last_update=datetime)
        self.session.add(note)
        self.session.commit()
        logger.info('Committed note')
        self.refresh_data()
        return 'Note Committed Successfully'

    def refresh_data(self):
        # TODO: Add timer to refresh data automatically. Add option to set time in preferences dialog
        self.layoutAboutToBeChanged.emit()
        self.datatable = [d for d in self.session.query(Note).order_by(Note.datetime).all()]
        logger.debug('Fetched new data')
        self.layoutChanged.emit()

    def export_data(self, path):
        # Export table data to csv. Assumes path is valid and will be overwritten if exists
        with open(path, 'wb') as stream:
            writer = csv.writer(stream)
            rowcount = len(self.datatable)
            colcount = len(self.datatable[0])
            for row in range(rowcount):
                rowdata = []
                for column in range(colcount):
                    item = self.datatable[row][column]
                    rowdata.append(item)
                writer.writerow(rowdata)
            
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
            return None

    def flags(self, QModelIndex):
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    def close(self):
        self.session.close()

    def is_valid_user(self, user, passwd):
        for un, pwhash in self.session.query(User.username, User.pwhash).filter(User.username == user):
            logger.debug('Found user in database. {}'.format(un))
            return pbkdf2_sha256.verify(passwd, pwhash)
