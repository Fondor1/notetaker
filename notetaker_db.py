import logging
import csv
import datetime as dt
from Qt import QtCore, QtGui, QtWidgets
from collections import defaultdict
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, LargeBinary, ForeignKey, create_engine, or_
from sqlalchemy.orm import sessionmaker
from passlib.hash import pbkdf2_sha256

logger = logging.getLogger('notetaker')

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    user_id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    pwhash = Column(String)

    def __repr__(self):
        return "<User(username='{}', pwhash='{}')>".format(self.username, self.pwhash)

       
class Note(Base):
    __tablename__ = 'note'
    
    # Contains only the latest edited notes for any given item 
    note_id = Column(Integer, primary_key=True)
    datetime = Column(DateTime)
    text = Column(String)
    user = Column(String, ForeignKey('user.username'))
    last_update = Column(DateTime)
    
    def __repr__(self):
        return "<Note(note_id='{}', datetime='{}', text='{}', user='{}', last_update='{}')>"\
            .format(self.note_id, self.datetime, self.text, self.user, self.last_update)

    def __getitem__(self, item):
        return (self.note_id, self.datetime, self.text, self.user, self.last_update)[item]


class Attachment(Base):
    __tablename__ = 'attachment'
    
    attach_id = Column(Integer, primary_key=True)
    # Filename or other identifier
    name = Column(String)
    data = Column(LargeBinary)
    
    def __repr__(self):
        return "<Attachment(name='{}', data='BINARY')>".format(self.name)
        

class LastUpdate(Base):
    __tablename__ = 'updatetime'
    # Single row intended to be used to keep track of the last update/edit/insertion into the database. This field can be queried by clients
    # to determine if the current view is the latest. It is currently the client's responsibility to check this value manually.
    # TODO: Add a trigger to update this value automatically when a new 
    updatetime = Column(DateTime, primary_key=True)

    def __repr__(self):
        return "<LastUpdate(updatetime='{}')>".format(self.updatetime)

        
class NoteAttachment(Base):
    __tablename__ = 'note_attachment'
    
    id = Column(Integer, primary_key=True)
    note_id = Column(Integer)
    attach_id = Column(Integer)
    
    def __repr__(self):
        return "<NoteAttachment(note_id='{}',attach_id='{}')>".format(self.note_id, self.attach_id)

class Log(Base):
    __tablename__ = 'log'
    
    # Log records every note transaction (both new and edits)
    # Does not handle attachments
    # TODO: Set up triggers to support automatic logging
    log_id = Column(Integer, primary_key=True)
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
            rowdata = {}
            for col in range(self.columnCount()):
                rowdata[self.header[col]] = self.data(self.index(row, col))
            export_list.append(rowdata)
        with open(path, 'w', newline='') as fl:
            writer = csv.DictWriter(fl, fieldnames=self.header)
            writer.writeheader()
            for line in export_list:
                writer.writerow(line)


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

        # self.dataUpdateTimer = QtCore.QTimer(self)
        # self.dataUpdateTimer.timeout.connect(self.refresh_data)
        # self.dataUpdateTimer.startTimer(update_rate)

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

    def commit_new_note(self, text, user, attachments=None):
        """
        'attachments' is expecting a list of file paths
        """
        
        logger.debug('Initiating commit of new note')
        # TODO: Check for any attachments and add if present
        # TODO: Use NIST time instead of trusting the computer time
        datetime = dt.datetime.now()
        logger.debug('Attempting to add note "{}", "{}", "{}"'.format(datetime, text, user))
        note = Note(datetime=datetime, text=text, user=user, last_update=datetime)
        self.session.add(note)
        if attachments:
            attach_list = []
            for attach in attachments:
                logger.debug('Attempting to add attachment "{}"'.format(attach))
                with open(attach, 'rb') as fl:
                    # TODO: Only keep filename/extension, not full path
                    attach_list.append(Attachment(name=attach, data=buffer(fl.read())))
        
        self.session.commit()
        logger.info('Committed note')
        self.refresh_data()
        return 'Note Committed Successfully'

    def refresh_data(self):
        # TODO: Add timer to refresh data automatically. Add option to set time in preferences dialog
        self.layoutAboutToBeChanged.emit()
        # Collect a list ir dict of all notes and the filenames for all attachments
        noteslist = self.session.query(Note).order_by(Note.datetime).all()
        attach_filename_dict = dict((a.attach_id, a.name) for a in self.session.query(Attachment.attach_id, Attachment.name).all())
        # Also generate a list holding the relationship between the notes and associated attachments
        notes_attach_list = [(item.note_id, item.attach_id) for item in self.session.query(NoteAttachment).all()]
        
        attach_dict = defaultdict(list)
        self.datatable = []
        for k,v in notes_attach_list:
            # Merge all attachments into a single list for each note_id 
            attach_dict[k].append(v)
        # Run through all notes, appending any attachments found
        for note in noteslist:
            if note.note_id in attach_dict.keys():
                self.datatable.append([note.datetime, 
                                       note.text, 
                                       note.user, 
                                       note.last_update]+
                                      ['\n'.join(attach_filename_dict[a] for a in attach_dict[note.note_id])])
            else:
                self.datatable.append([note.datetime, note.text, note.user, note.last_update] + [''])

        logger.debug('Fetched new data')
        self.layoutChanged.emit()

    def export_data(self, path):
        # Export table data to csv. Assumes path is valid and will be overwritten if exists
        with open(path, 'w', newline='') as stream:
            writer = csv.writer(stream)
            rowcount = len(self.datatable)
            colcount = len(self.datatable[0])
            writer.writerow(self.header)
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
