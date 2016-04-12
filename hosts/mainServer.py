#!/usr/bin/python

import sqlite3
import json
import socket
import sys
import threading
import traceback
import signal


PORT = 3128
HOST = socket.gethostname()


class CollectReading(threading.Thread):
    """Collect Reading from concentrators"""
    s = socket.socket()
    runFlag = True
    readings = []

    def __init__(self):
        super(CollectReading, self).__init__()
        self.listenerThread = threading.Thread(target=self.listen)
        self.dataThread = threading.Thread(target=self.updateDB)
        self.dataSignal = threading.Event()
        self.listenSignal = threading.Event()
        self.reader_lock = threading.Lock()

        self.conn = sqlite3.connect("readings.db",check_same_thread=False)
        self.c = self.conn.cursor()
        self.c.execute('''CREATE TABLE IF NOT EXISTS readings
                    (id, kwh, lastread, PRIMARY KEY (id, kwh))''')
        self.conn.commit()
        self.listenerThread.start()
        self.dataThread.start()

    def listen(self):
        """Listen to concentrators on different Area"""
        print "Listen"
        try:
            self.s.bind((HOST, PORT))
            self.s.listen(10)
            print "Listening on port %d" % PORT
        except socket.error:
            print "exception: "
            traceback.print_exc()
        while self.runFlag:
            c, addr = self.s.accept()
            temp_buffer = c.recv(2048)
            print "Got connection from ", addr
            if not self.runFlag:
                continue
            try:
                self.readings.append = json.loads(temp_buffer)
                if len(self.readings) == 3:
                    status = self.updateDB()
                    self.listenSignal.wait()
                    if status:
                        print "changes written to DB"

            except ValueError:
                print "Error in decoding json"
                traceback.print_exc()
            finally:
                self.listenSignal.set()
            c.send("SER_ACK")
            c.close()
        return

    def updateDB(self):
        try:
            print "Data received"
            rdstmt = []
            for reading in self.readings:
                print reading['id']
                row = (reading['id'], reading['reading'], reading['ts'])
                rdstmt.append(row)
                print "....."
            self.c.executemany("INSERT INTO readings VALUES (?,?,?)", rdstmt)
            self.conn.commit()
            self.readings = []

        except self.c.error:
            traceback.print_exc()
        finally:
            self.listenSignal.set()
        return True

    def stopListening(self):
        """ Stop listener thread """
        print "killing listener"
        self.runFlag = False
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((socket.gethostname(), PORT))
        self.conn.close()
        # self.dataSignal.clear()
        self.listenerThread.join()
        self.dataThread.join()

    def showData(self, meter_id):
        """Show Data per meterID"""
        cur = self.c.execute("SELECT * FROM readings WHERE id=? ORDER BY lastread", meter_id)
        for row in cur:
            print row


def signalHandler(signal, frame):
    # print "ctrl-c pressed"
    reader.stopListening()
    sys.exit(0)


def validID(meterid):
    try:
        if 0 < int(meterid) < 255:
            return True
        else:
            return False
    except ValueError:
        return False

if __name__ == '__main__':
    reader = CollectReading()
    # reader.updateDB()
    choice = ''
    # print "Enter Meter ID to see readings \n press S to exit this mode \n Press X to exit program"

    # while True:
    #    choice = raw_input("> ")
    #     if choice == 's' or choice == 'S':
    #         break
    #     elif choice == 'x' or choice == 'X':
    #         reader.stopListening()
    #         sys.exit(0)
    #     elif validID(choice):
    #         reader.showData(choice)
    #     else:
    #         continue

    signal.signal(signal.SIGINT, signalHandler)
    signal.pause()
