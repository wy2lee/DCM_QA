#!/usr/bin/python

# Based on an input text file, modifies all dicoms in a given directory 
# Two usage modes
#           A - Single field - Command line call changes one field only
#           B - Multi-field - Pass a file containing a list of all headers to change and their new values

# Based on calls to dcmmodify

#    File Name:  fix_dcm.py
#
#    NOTES - WL - 13/10/21 - Initial Creation
#
#   AUTHOR - Wayne Lee, 
#   Created - 2013/10/21
#   REVISIONS 

#       A - 2013-07-04 - WL - Original Creation, loose class and function definitions
#       B - 2015-03-19 - WL - GitHub'd

from optparse import OptionParser, Option, OptionValueError
import datetime
import string
import glob
import os, shlex, subprocess
import numpy

program_name = 'fix_dcm.py'

#*************************************************************************************
# FUNCTIONS

# General utility function to call system commands
def run_cmd(sys_cmd, debug, verbose):
# one line call to output system command and control debug state
    if verbose:
        print sys_cmd
    if not debug:
        p = subprocess.Popen(sys_cmd, stdout = subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        output, errors = p.communicate()
        if verbose:
            print output, errors
        return output, errors
    else:
        return '','' 

def load_dcm_list(fname_dcm_list, lut_dcm_hdrs):
#   Loads list of dicom headers to change, and their new value
    if not os.path.exists(fname_dcm_list):
        raise SystemExit, 'ERROR - Parameter File - File not found: %s' % (fname_subj_list,) 
        
    file_dcm_list = open(fname_dcm_list,'r')
    for line_dcm in file_dcm_list:
        lut_dcm_hdrs[line_dcm.split(':')[0].strip(' ')] = line_dcm.split(':')[1].strip(' ')
    return lut_dcm_hdrs
    
#**********************************************************************
    
def main():
    usage = "Usage: [SINGLE FIELD MODE] "+program_name+" <options> dcm_hdr new_dcm_value dir_dcm_in dir_dcm_out \n" + \
            "   or  [BATCH MODE] "+program_name+" <options> fname_dcm_list dir_dcm_in dir_dcm_out \n" + \
            "   or  "+program_name+" --help";
    parser = OptionParser(usage)
    parser.add_option("-c","--clobber", action="store_true", dest="clobber",
                        default=0, help="overwrite output file")
    parser.add_option("-v","--verbose", action="store_true", dest="verbose",
                        default=0, help="Verbose output")
    parser.add_option("-d","--debug", action="store_true", dest="debug",
                        default=0, help="Run in debug mode")

    options, args = parser.parse_args()

    lut_dcm_hdrs = {}
    if len(args) == 3:
        fname_dcm_list, dir_dcm_in, dir_dcm_out = args
        lut_dcm_hdrs = load_dcm_list(fname_dcm_list, lut_dcm_hdrs)
    elif len(args) == 4:
        dcm_hdr, dcm_new_value, dir_dcm_in, dir_dcm_out = args
        lut_dcm_hdrs[dcm_hdr] = dcm_new_value
    else:
        parser.error("incorrect number of arguments")

    # Check for base output directory, create if needed
    if not os.path.exists(dir_dcm_out):
        run_cmd('mkdir ' + dir_dcm_out, options.debug, options.verbose)

    dir_series_name = dir_dcm_in.split('/')[-1]
    # Check for specific output directory, exit if not clobber
    if  os.path.exists( '%s/%s' % (dir_dcm_out, dir_series_name)) and not options.clobber:
        raise SystemExit, '* ERROR - Output directory already exists, turn on CLOBBER to overwrite: %s/%s' % \
            ((dir_dcm_out, dir_series_name)) 
    else:
        cmd_duplicate = ('cp -rf %s %s/') % \
            (dir_dcm_in, dir_dcm_out)
        
        
    run_cmd(cmd_duplicate, options.debug, options.verbose)
    
    list_dcm_files = os.listdir(dir_dcm_in)

    for fname_scan in list_dcm_files:
        # print fname_scan
        for curr_dcm_hdr_index in lut_dcm_hdrs:
            curr_dcm_hdr_value = lut_dcm_hdrs[curr_dcm_hdr_index].strip('\n')
            cmd_dcmodify = 'dcmodify -ma "(%s)"=%s %s/%s/%s' % \
                (curr_dcm_hdr_index, curr_dcm_hdr_value, dir_dcm_out, dir_series_name, fname_scan)
            run_cmd(cmd_dcmodify, options.debug, options.verbose)
            
            cmd_rmbak = 'rm -f %s/%s/%s.bak' % (dir_dcm_out, dir_series_name, fname_scan)
            run_cmd(cmd_rmbak, options.debug, options.verbose)
            
if __name__ == '__main__' :
    main()


    
