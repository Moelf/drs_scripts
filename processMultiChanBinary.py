#! /usr/bin/env python

## take a binary file output from DRS scope
## create a ROOT file with time and voltage arrays
##
## note that time values are different for every event since
## DRS binning is uneven, and the trigger can occur in any bin

import sys
import struct
import datetime as dt
import json
import numpy as np
import ROOT as r

def getStr(fid, length):
    data = fid.read(length)
    if len(data)==0:
        return None
    res = struct.unpack("c"*length, data)
    return "".join(res)

def getShort(fid, num=1):
    data = fid.read(2*num)
    if len(data)==0:
        return None
    res = struct.unpack("H"*num, data)
    return res[0] if num==1 else res

def getFloat(fid, num=1):
    data = fid.read(4*num)
    if len(data)==0:
        return None
    res = struct.unpack("f"*num, data)
    return res[0] if num==1 else res

def getInt(fid, num=1):
    data = fid.read(4*num)
    if len(data)==0:
        return None
    res = struct.unpack("I"*num, data)
    return res[0] if num==1 else res

def processMultiChanBinary(name, N_EVTS):
    print "processing data"
    
    indir =  "/homes/sheplock/Timing/drs_scope/data/unprocessed/"
    outdir = "/homes/sheplock/Timing/drs_scope/data/processed/"

    N_BINS = 1024 # number of timing bins per channel

    fin = indir+"/{0}.dat".format(name)
    fout = r.TFile(outdir+"/{0}.root".format(name), "RECREATE")
    ts1 = np.zeros(1024, dtype='float')
    vs1 = np.zeros(1024, dtype='float')
    ts2 = np.zeros(1024, dtype='float')
    vs2 = np.zeros(1024, dtype='float')
    ts3 = np.zeros(1024, dtype='float')
    vs3 = np.zeros(1024, dtype='float')
    ts4 = np.zeros(1024, dtype='float')
    vs4 = np.zeros(1024, dtype='float')
    t = r.TTree("Events","Events")
    t1 = t.Branch("times_CH1", ts1, 'times[1024]/D')
    v1 = t.Branch("voltages_CH1", vs1, 'voltages[1024]/D')
    t2 = t.Branch("times_CH2", ts2, 'times[1024]/D')
    v2 = t.Branch("voltages_CH2", vs2, 'voltages[1024]/D')
    t3 = t.Branch("times_CH3", ts3, 'times[1024]/D')
    v3 = t.Branch("voltages_CH3", vs3, 'voltages[1024]/D')
    t4 = t.Branch("times_CH4", ts4, 'times[1024]/D')
    v4 = t.Branch("voltages_CH4", vs4, 'voltages[1024]/D')
    
    t.SetEntries(N_EVTS)
    
    fid = open(fin,'rb')

    # make sure file header is correct
    fhdr = getStr(fid, 4)
    if fhdr != "DRS2":
        print "ERROR: unrecognized header "+fhdr
        exit(1)
        
    # make sure timing header is correct
    thdr = getStr(fid, 4)
    if thdr != "TIME":
        print "ERROR: unrecognized time header "+thdr
        exit(1)

    # get the boards in file
    n_boards = 0
    channels = []
    board_ids = []
    bin_widths = []
    while True:
        bhdr = getStr(fid, 2)
        if bhdr != "B#":
            fid.seek(-2, 1)
            break
        board_ids.append( getShort(fid) )
        n_boards += 1
        bin_widths.append([])
        print "Found Board #"+str(board_ids[-1])

        while True:
            chdr = getStr(fid, 3)
            if chdr != "C00":
                fid.seek(-3, 1)
                break
            cnum = int(getStr(fid, 1))
            print "  Found channel #"+str(cnum)
            channels.append(cnum)
            bin_widths[n_boards-1].append(getFloat(fid, N_BINS))

        if len(bin_widths[n_boards-1])==0:
            print "ERROR: Board #{0} doesn't have any channels!".format(board_ids[-1])

    if n_boards==0:
        print "ERROR: didn't find any valid boards!"
        exit(1)

    if n_boards > 1:
        print "ERROR: only support one board. Found {0} in file.".format(n_boards)
        exit(1)

    bin_widths = bin_widths[0]
    n_chan = len(bin_widths)
    rates = []

    n_evt = 0
    while True:
        ehdr = getStr(fid, 4)
        if ehdr == None:
            break
        if ehdr != "EHDR":
            raise Exception("Bad event header!")

        n_evt += 1
        # print "Found Event #"+str(n_evt)
        serial = getInt(fid)
        # print "  Serial #"+str(serial)
        date = getShort(fid, 7)
        date = dt.datetime(*date[:6], microsecond=1000*date[6])
        if n_evt == 1:
            t_start = date
        elif n_evt == N_EVTS:
            t_end = date
        # print "  Date: "+str(date)
        rangeCtr = getShort(fid)
        # print "  Range Center: "+str(rangeCtr)
        getStr(fid, 2)
        b_num = getShort(fid)
        getStr(fid, 2)
        trig_cell = getShort(fid)
        # print "  Trigger Cell: "+str(trig_cell)

        for ichn in range(n_chan):
            chdr = getStr(fid, 4)
            if chdr != "C00"+str(channels[ichn]):
                print "ERROR: bad event data!"
                exit(1)

            scaler = getInt(fid)
            voltages = np.array(getShort(fid, N_BINS))
            #if READ_CHN != channels[ichn]:
            #    continue
            voltages = voltages/65535. * 1000 - 500 + rangeCtr
            times = np.roll(np.array(bin_widths[ichn]), N_BINS-trig_cell)
            times = np.cumsum(times)
            times = np.append([0], times[:-1])
            rates.append((times[-1]-times[0])/(times.size-1))
            if ichn==0:
                np.copyto(ts1, times)
                np.copyto(vs1, voltages)
                t1.Fill()
                v1.Fill()
            elif ichn==1:
                np.copyto(ts2, times)
                np.copyto(vs2, voltages)
                t2.Fill()
                v2.Fill()
            elif ichn==2:
                np.copyto(ts3, times)
                np.copyto(vs3, voltages)
                t3.Fill()
                v3.Fill()
            elif ichn==3:
                np.copyto(ts4, times)
                np.copyto(vs4, voltages)
                t4.Fill()
                v4.Fill()
            else:
                print "ERROR: Channel out of range! "+str(ichn)
                exit(1)

    t_tot = t_end - t_start
    t_sec = t_tot.total_seconds()
        
    print "Measured sampling rate: {0:.2f} GHz".format(1.0/np.mean(rates))
    print "Total time of run = " + str(t_tot) + " which is " + str(t_sec) + " seconds."
    print "Event rate = " +str(N_EVTS/t_sec) + " Hz"
    t.Write()
    fout.Close()
    
if __name__ == "__main__":
    args = sys.argv[1:]
    for filename in args:
        folder, name = filename.rsplit('/',1)
        name, ext = name.rsplit('.',1)
        pre, evt = name.rsplit('_',1)
        nevts, vts = evt.rsplit('e',1)
        N_EVTS = int(nevts)
        processMultiChanBinary(name,N_EVTS)