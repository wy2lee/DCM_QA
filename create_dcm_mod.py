#!/usr/bin/python

# Creates a dcm_mod file for fix_dcm.py based on some input information
#     Semi-hacky, designed to quickly populate SubjectID, SubjectName, SeriesDescription
#          Also includes a bunch of predefined modifications (ie. wipe)
#           Contains logic to determine scan type from input directory name

# Based on calls to dcmmodify

#    File Name:  create_dcm_mod.py
#
#    NOTES - WL - 17/07/22 - Initial Creation
#
#   AUTHOR - Wayne Lee, 
#   Created - 2015/07/22
#   REVISIONS 

#       A - 2015-07-22 - WL - Original Creation, loose class and function definitions

from optparse import OptionParser, Option, OptionValueError
import datetime
import string
import glob
import os, shlex, subprocess
import numpy

program_name = 'create_dcm_mod.py'

#*************************************************************************************
# BASIC MOD VALUES

lut_basic_mod = '0010,0030 : 19900101\n' + \
    '0010,0040 : 0\n' + \
    '0010,1010 : 0\n' + \
    '0010,1020 : 0\n' + \
    '0010,1030 : 0\n' + \
    '0010,2154 : 0\n'



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

def load_lut_scan_type(fname_lut_scan_type):
#   Loads lut for scan_types
    lut_scan_type={}
    if not os.path.exists(fname_lut_scan_type):
        raise SystemExit, 'ERROR - Parameter File - File not found: %s' % (fname_subj_list,) 
        
    file_lut_scan_type = open(fname_lut_scan_type,'r')
    for line_file in file_lut_scan_type:
        lut_scan_type[line_file.split(':')[0].strip(' ')] = line_file.split(':')[1].strip(' \n')
    return lut_scan_type
        
        
def load_dcm_list(fname_dcm_list, lut_dcm_hdrs):
#   Loads list of dicom headers to change, and their new value
    if not os.path.exists(fname_dcm_list):
        raise SystemExit, 'ERROR - Parameter File - File not found: %s' % (fname_subj_list,) 
        
    file_dcm_list = open(fname_dcm_list,'r')
    for line_dcm in file_dcm_list:
        lut_dcm_hdrs[line_dcm.split(':')[0].strip(' ')] = line_dcm.split(':')[1].strip(' ')
    return lut_dcm_hdrs

def check_scan_type(dir_curr_scan_clean, scan_type):
# Function to check if current scan needs to be prepped
    list_ignore = ['_ADC','_TRACEW','_FA','_ColFA']   # processed DTI scans to ignore

    QA_THIS_SCAN = 1
    list_scan_type = scan_type.split(',')
    # make sure all keywords present in directory name
    for scan_keywords in list_scan_type:
        if dir_curr_scan_clean.find(scan_keywords)<0:
            QA_THIS_SCAN = 0
            
    # make sure all ignore words are absent in directory name
    for ignore_keywords in list_ignore:
        if dir_curr_scan_clean.find(ignore_keywords)>-1:
            QA_THIS_SCAN = 0
            
    return QA_THIS_SCAN

#**********************************************************************
    
def main():
    usage = "Usage: "+program_name+" <options> targetDir subjectID sessionSuffix \n" + \
            "   or  "+program_name+" --help";
    parser = OptionParser(usage)
    parser.add_option("--lut_ST", type="string", dest="fname_lut_scan_type",
                        default="lut_scan_type.cfg", help="Lut to convert default Scan Description into defined ScanType [default = lut_scan_type.cfg]")
    parser.add_option("--fname_output", type="string", dest="fname_output",
                        default="dcm_mod_temp.txt", help="Output dcm_mod filename [default = dcm_mod_temp.txt]")
    parser.add_option("-c","--clobber", action="store_true", dest="clobber",
                        default=0, help="overwrite output file")
    parser.add_option("-v","--verbose", action="store_true", dest="verbose",
                        default=0, help="Verbose output")
    parser.add_option("-d","--debug", action="store_true", dest="debug",
                        default=0, help="Run in debug mode")

    options, args = parser.parse_args()


    lut_scan_type = {}
    if len(args) == 3:
        targetDir, subjectID, sessionSuffix = args
    else:
        parser.error("incorrect number of arguments")

    lut_scan_type = load_lut_scan_type(options.fname_lut_scan_type)    
    dir_target_clean = targetDir.replace('-','_')   # remove variability of - or _

    # Check if targetDir is one that requires modifications    
    for scan_type in lut_scan_type:
        QA_THIS_SCAN = check_scan_type(dir_target_clean, scan_type) 
        if QA_THIS_SCAN:
            new_scanType = lut_scan_type[scan_type]
            new_subjectID = subjectID
            new_sessionName = '%s_%s' % (subjectID,sessionSuffix)
            print targetDir, new_subjectID, new_sessionName, new_scanType
    
    
if __name__ == '__main__' :
    main()


    