"""
project1.py
Griffin Melnick, melnig@rpi.edu
Peter Straub, straup@rpi.edu

    CPU scheduling simulation. Performs each of the first-come, first-served 
    (FCFS), shortest remaining time (SRT), and round robin (RR) algorithms and 
    prints significant events in processes thorughout duration of simulation. 
    Writes simulation results summary to an output file. The program is run by 
    calling

        bash$ python3 project1.py <input-file> <stats-output-file> [<rr-add>]

    where <input-file> is the file with formatted process information, 
    <stats-output-file> is the file to which to write simulation results summary,
    and the optional <rr-add> determines whether processes are added to the 
    beginning or end of the ready queue in the RR algorithm. 
"""

from __future__ import print_function
from collections import defaultdict as ddict
from collections import deque
import copy
import os
import sys

DEBUG = False

n = 0
t_cs = 8
t_slice = 80
rr_add = 0

"""
Process helper class to store process details from input file.
"""
class Process:
    """
    Default constructor.
    """
    def __init__( self, pid, arrival, burst, num, io ):
        # Helper details. #
        self._start = 0                         # most recent start time #
        self._readied = 0                       # most recent ready time #
        self._last_arrival = arrival            # most recent arrival time #
        self._remaining = burst                 # remaining time for burst #

        # Details taken from input file. #
        self._pid = pid
        self._arrival = arrival
        self._burst = burst
        self._num = num
        self._io = io

    # ------------------------------------------------------------------------ #
    # Overidden methods #

    """
    Repr representation.
    :return:    raw representation of all data in Process object.
    """
    def __repr__( self ):
        repr_rep = "Process(_pid = {}, _arrival = {}, ".format( \
                self._pid, self._arrival )
        repr_rep += "_burst = {}, _num = {}, _io = {})".format( \
                self._burst, self._num, self._io )
        return repr_rep


    """
    String representation of Process.
    :return:    string detailing with Process pid and arrival time.
    """
    def __str__( self ):
        return "proc. {} @ {}ms ".format( self._pid, self._arrival )


"""
CPU helper class to better keep track of processes throughout scheduling.
"""
class CPU:
    """
    Default constructor.
    """
    def __init__( self, procs ):
        self._procs = procs                     # processes found in input file #

        # Helper details. #
        self._total_turnaround = float( 0 )     # total turnaround time #
        self._total_wait = float( 0 )           # total wait time #
        self._total_num = float( sum( [proc._num for proc in self._procs] ) )

        # Simple output details. #
        self._avg_burst = ( sum( [(proc._burst * proc._num) for proc in self._procs] )\
                 / self._total_num )
        self._avg_wait = 0
        self._avg_turnaround = 0
        self._context = 0
        self._preempt = 0

        # Process scheduling details. #
        self._ticker = 0                        # time ticker #
        self._curr = None                       # running process #
        self._ready = deque()                   # ready queue for processes #
        self._finished = ddict( int )           # maps PID to final burst finish #
        self._io = ddict( int )                 # maps PID to I/O finish #

    # ------------------------------------------------------------------------ #
    # Accessors #
    
    """
    String representation of CPU ready queue.
    :return:    string in the format of '[Q *contents of _ready*]
    """
    def get_queue( self ):
        contents = "[Q"
        for proc in self._ready:
            contents += ' ' + proc._pid
        contents += ']'
        if ( contents == "[Q]" ):
            contents = "[Q <empty>]"

        return contents

    # ------------------------------------------------------------------------ #
    # Modifiers #

    """
    Adds new process.
    :param:     proc, new process.
    """
    def add( self, proc ):
        proc._start = self._ticker
        self._total_wait += ( self._ticker - proc._readied )
        
        # Add new process. #
        self._ticker += ( t_cs // 2 )
        self._curr = proc
        self._context += 1


    """
    Adds process to ready queue.
    :param:     proc, readying process.
    """
    def ready( self, proc ):
        proc._readied = self._ticker
        proc._last_arrival = self._ticker
        (self._ready).append( proc )

    
    """
    Removes running process.
    """
    def remove( self ):
        # Remove running process. #
        self._ticker += ( t_cs // 2 )
        self._total_turnaround += ( self._ticker - (self._curr)._last_arrival )
        self._curr = None


    """
    Preempts running process with new process.
    :param:     proc, preempting process
    """
    def preempt( self, proc ):
        # Remove running process and adds to _ready. #
        self._ticker += ( t_cs // 2 )
        (self._curr)._readied = self._ticker
        (self._ready).appendleft( self._curr )
        self._curr = None

        # Add new process. #
        self._ticker += ( t_cs // 2 )
        self._curr = proc
        (self._curr)._remaining -= 1

        self._context += 1
        self._preempt += 1

    # ------------------------------------------------------------------------ #
    # Overridden methods #
    
    """
    Repr representation.
    :return:    raw representation of all data in CPU object.
    """
    def __repr__( self ):
        repr_rep = "CPU(_ticker = {}, _curr = {}, _ready = deque([".format( \
                self._ticker, (self._curr)._pid )
        for proc in self._ready:
            repr_rep += "{}, ".format( proc._pid )

        return repr_rep[ :-2 ] + "]))"


    """
    String representation of CPU.
    :return:    string with time, current process, and string rep of ready queue.
    """
    def __str__( self ):
        return "{}ms: running {}, ready {}".format( self._ticker, self._curr._id, \
                self.get_queue() )

# ---------------------------------------------------------------------------- #

"""
Helper method to print to stderr.
:param:     *args, all non-keyworded arguments.
            **kwargs, all keyworded arguments.
"""
def err( *args, **kwargs ):
    print( *args, file=sys.stderr, **kwargs )


"""
Helper method to read in file input.
:param:     f_name, file name to find in directory and read.
:return:    ddict of process id mapped to tuple of details, if successful
            os.EX_IOERR, if file fails, ex.EX_DATAERR, if file is not formatted
"""
def read_file( f_name ):
    pwd = os.path.dirname( __file__ )
    path = os.path.join( pwd, f_name )

    try:
        f = open( path, 'r' )
    except:
        return os.EX_IOERR

    procs = []
    for line in f:
        if ( (line[0] != '#') and (line[0] != '\n') ):
            line = line.strip().split('|')
            try:
                tmp = [ int(line[i]) for i in range(1, 5) ]
                procs.append( Process(line[0], tmp[0], tmp[1], tmp[2], tmp[3]) )
            except:
                f.close()
                return os.EX_DATAERR

    f.close()
    return procs


"""
Builds simple output file list.
:param:     lines, list with existing lines
            res, results from process scheduling
:return:    list with lines of output related to 'res' appended to end.
"""
def build_simple( lines, res ):
    lines.append( "-- average CPU burst time: {0:.2f} ms\n".format(res[0]) )
    lines.append( "-- average wait time: {0:.2f} ms\n".format(res[1]) )
    lines.append( "-- average turnaround time: {0:.2f} ms\n".format(res[2]) )
    lines.append( "-- total number of context switches: {}\n".format(res[3]) )
    lines.append( "-- total number of preemptions: {}\n".format(res[4]) )

    return lines


"""
First come, first serve simulation.
:param:     procs, list of Process objects to simulate.
:return:    five-tuple with simple output tracking variables.
"""
def run_fcfs( procs ):
    cpu = CPU( copy.deepcopy(procs) )
    print( "time {}ms: Simulator started for FCFS {}".format(cpu._ticker, \
            cpu.get_queue()) )

    while 1:
        removed = False
        if ( cpu._curr != None ):
            # Check for finished process. #
            if ( (cpu._curr)._remaining <= 0 ):
                (cpu._curr)._num -= 1
                if ( (cpu._curr)._num > 0 ):
                    print( "time {}ms: Process {} completed a CPU burst; {} burst{} to go {}".format( \
                            cpu._ticker, (cpu._curr)._pid, (cpu._curr)._num, \
                            ('s' if (cpu._curr)._num != 1 else ''), cpu.get_queue() ) )

                    cpu._io[cpu._curr] = ( cpu._ticker + (cpu._curr)._io + (t_cs // 2) )
                    print( "time {}ms: Process {} switching out of CPU; will block on I/O until time {}ms {}".format( \
                            cpu._ticker, (cpu._curr)._pid, cpu._io[cpu._curr], \
                            cpu.get_queue() ) )

                else:
                    # (cpu._curr)._num <= 0 #
                    print( "time {}ms: Process {} terminated {}".format(cpu._ticker, \
                            (cpu._curr)._pid, cpu.get_queue()) )
                    cpu._finished[cpu._curr] = cpu._ticker

                removed = True

            else:
                # (cpu._curr)._remaining > 0 #
                (cpu._curr)._remaining -= 1

        io_done = sorted( [ proc for proc, tick in (cpu._io).items() if tick == cpu._ticker ],
                key = lambda obj : obj._pid )
        for proc in io_done:
            cpu.ready( proc )
            del cpu._io[proc]
            print( "time {}ms: Process {} completed I/O; added to ready queue {}".format(\
                    cpu._ticker, proc._pid, cpu.get_queue()) )

        for proc in cpu._procs:
            if ( proc._arrival == cpu._ticker ):
                proc._last_arrival = cpu._ticker
                cpu.ready( proc )
                print( "time {}ms: Process {} arrived and added to ready queue {}".format(\
                        cpu._ticker, proc._pid, cpu.get_queue()) )

        if ( removed ):
            cpu.remove()

        if ( cpu._curr == None ):
            if ( cpu._ready ):
                cpu.add( (cpu._ready).popleft() )
                (cpu._curr)._remaining = ( (cpu._curr)._burst - 1 )
                print( "time {}ms: Process {} started using the CPU {}".format(\
                        cpu._ticker, (cpu._curr)._pid, cpu.get_queue()) )

        if ( len(cpu._finished) == n ):
            break
        
        cpu._ticker += 1

    print( "time {}ms: Simulator ended for FCFS\n".format(cpu._ticker) )
    cpu._avg_wait = cpu._total_wait / cpu._total_num
    cpu._avg_turnaround = cpu._total_turnaround / cpu._total_num
    return ( cpu._avg_burst, cpu._avg_wait, cpu._avg_turnaround, \
            cpu._context, cpu._preempt )


"""
Shortest remaining time simulation.
:param:     procs, list of Process objects to simulate.
:return:    five-tuple with simple output tracking variables.
"""
def run_srt( procs ):
    cpu = CPU( copy.deepcopy(procs) )
    print( "time {}ms: Simulator started for SRT {}".format(cpu._ticker, cpu.get_queue()) )

    while 1:
        removed = False
        if ( cpu._curr != None ):
            # Check for finished process. #
            if ( (cpu._curr)._remaining <= 0 ):
                (cpu._curr)._num -= 1
                if ( (cpu._curr)._num > 0 ):
                    print( "time {}ms: Process {} completed a CPU burst; {} burst{} to go {}".format( \
                            cpu._ticker, (cpu._curr)._pid, (cpu._curr)._num, \
                            ('s' if (cpu._curr)._num != 1 else ''), cpu.get_queue() ) )

                    (cpu._curr)._remaining = (cpu._curr)._burst
                    cpu._io[cpu._curr] = ( cpu._ticker + (cpu._curr)._io + (t_cs // 2) )
                    print( "time {}ms: Process {} switching out of CPU; will block on I/O until time {}ms {}".format( \
                            cpu._ticker, (cpu._curr)._pid, cpu._io[cpu._curr], \
                            cpu.get_queue() ) )

                else:
                    # (cpu._curr)._num <= 0 #
                    print( "time {}ms: Process {} terminated {}".format(cpu._ticker, \
                            (cpu._curr)._pid, cpu.get_queue()) )
                    cpu._finished[cpu._curr] = cpu._ticker

                removed = True

            else:
                # (cpu._curr)._remaining > 0 #
                (cpu._curr)._remaining -= 1

        io_done = sorted( [ proc for proc, tick in (cpu._io).items() if tick == cpu._ticker ],
                key = lambda obj : (obj._remaining, obj._pid) )
        if ( io_done ):
            if ( (cpu._curr) and (not removed) ):
                if ( io_done[0]._remaining < (cpu._curr)._remaining ):
                    print( "time {}ms: Process {} completed I/O and will preempt {} {}".format(\
                            cpu._ticker, io_done[0]._pid, (cpu._curr)._pid, \
                            cpu.get_queue()) )
                    cpu.preempt( io_done[0] )
                    print( "time {}ms: Process {} started using the CPU {}".format(\
                            cpu._ticker, (cpu._curr)._pid, cpu.get_queue()) )
                    del io_done[0]

            for proc in io_done:
                cpu.ready( proc )
                cpu._ready = deque( sorted( cpu._ready, 
                        key = lambda obj : (obj._remaining, obj._pid) ) )
                print( "time {}ms: Process {} completed I/O; added to ready queue {}".format(\
                        cpu._ticker, proc._pid, cpu.get_queue()) )

        arrived = sorted( [ proc for proc in cpu._procs if proc._arrival == cpu._ticker ],
                key = lambda obj : (obj._remaining, obj._pid) )
        if ( arrived ):
            if ( (cpu._curr) and (not removed) ):
                if ( arrived[0]._remaining < (cpu._curr)._remaining ):
                    print( "time {}ms: Process {} arrived and will preempt {} {}".format(\
                            cpu._ticker, arrived[0]._pid, (cpu._curr)._pid, \
                            cpu.get_queue()) )
                    cpu.preempt( arrived[0] )
                    print( "time {}ms: Process {} started using the CPU {}".format(\
                            cpu._ticker, (cpu._curr)._pid, cpu.get_queue()) )
                    del arrived[0]

            for proc in arrived:
                cpu.ready( proc )
                cpu._ready = deque( sorted( cpu._ready, 
                        key = lambda obj : (obj._remaining, obj._pid) ) )
                print( "time {}ms: Process {} arrived and added to ready queue {}".format(\
                        cpu._ticker, proc._pid, cpu.get_queue()) )
            
        if ( removed ):
            cpu.remove()

        if ( cpu._curr == None ):
            if ( cpu._ready ):
                cpu.add( (cpu._ready).popleft() )
                (cpu._curr)._start = ( cpu._ticker - (t_cs // 2) )
                if ( (cpu._curr)._remaining == (cpu._curr)._burst ):
                    (cpu._curr)._remaining = ( (cpu._curr)._burst - 1 )
                    print( "time {}ms: Process {} started using the CPU {}".format(\
                            cpu._ticker, (cpu._curr)._pid, cpu.get_queue()) )

                else:
                    # (cpu._curr)._remaining != (cpu._curr)._burst #
                    print( "time {}ms: Process {} started using the CPU with {}ms remaining {}".format( \
                            cpu._ticker, (cpu._curr)._pid, ((cpu._curr)._remaining + 1),
                            cpu.get_queue() ) )

        if ( len(cpu._finished) == n ):
            break
        
        cpu._ticker += 1
    
    print( "time {}ms: Simulator ended for SRT\n".format(cpu._ticker) )
    cpu._avg_wait = cpu._total_wait / cpu._total_num
    cpu._avg_turnaround = cpu._total_turnaround / cpu._total_num
    return ( cpu._avg_burst, cpu._avg_wait, cpu._avg_turnaround, \
            cpu._context, cpu._preempt )


"""
Round robin simulation.
:param:     procs, list of Process objects to simulate.
:return:    five-tuple with simple output tracking variables.
"""
def run_rr( procs ):
    cpu = CPU( copy.deepcopy(procs) )
    print( "time {}ms: Simulator started for RR {}".format(cpu._ticker, cpu.get_queue()) )
    
    print( "time {}ms: Simulator ended for RR".format(cpu._ticker) )
    cpu._avg_turnaround = cpu._total_turnaround / cpu._total_num
    cpu._avg_wait = cpu._total_wait / cpu._total_num
    return ( cpu._avg_burst, cpu._avg_wait, cpu._avg_turnaround, \
            cpu._context, cpu._preempt )

# ---------------------------------------------------------------------------- #

if ( __name__ == "__main__" ):
    if ( ( len(sys.argv) == 3 ) or ( len(sys.argv) == 4 ) ):
        # Check to make sure that optional argument 3 is valid. #
        if ( len(sys.argv) == 4 ):
            if ( sys.argv[3] == "BEGINNING" ):
                rr_add = 1

            elif ( sys.argv[3] != "END" ):
                err( "ERROR: Invalid arguments" )
                sys.exit( "USAGE: ./a.out <input-file> <stats-output-file> [<rr-add>]" )

        # Open write-to file to make sure file is valid. #
        pwd = os.path.dirname( __file__ )
        path = os.path.join( pwd, sys.argv[2] )
        try:
            f = open( path, 'w' )
        except:
            sys.exit( "ERROR: Invalid output file" )

        procs = read_file( sys.argv[1] )
        if ( isinstance(procs, list) ):
            n = len( procs )
            if DEBUG:
                print( "{} processes...".format(n) )
                for proc in procs:
                    print( "  " + str(proc) )

            fcfs_res = run_fcfs( procs )
            srt_res = run_srt( procs )
            # rr_res = run_rr( procs )

            simple_out = []

            # Add FCFS results. #
            simple_out.append( "Algorithm FCFS\n" )
            simple_out = build_simple( simple_out, fcfs_res )
            # Add SRT results. #
            simple_out.append( "Algorithm SRT\n" )
            simple_out = build_simple( simple_out, srt_res )
            # Add RR results. #
            # simple_out.append( "Algorithm RR\n" )
            # simple_out = build_simple( simple_out, rr_res )

            f.writelines( simple_out )
            f.close()

            sys.exit()

        else:
            f.close()
            sys.exit( "ERROR: Invalid input file format" )

    else:
        err( "ERROR: Invalid arguments" )
        sys.exit( "USAGE: ./a.out <input-file> <stats-output-file> [<rr-add>]" )
