#!/usr/bin/env python3

#from numpy import set_printoptions, array, zeros, asarray, amax, int, dtype, fabs, fromfile, prod, size, reshape, nan, array2string
import numpy as np
import re
import os
import utils

try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree

np.set_printoptions(precision=5)

# *************************************************************************** #
# *************************** class definition ****************************** #
# *************************************************************************** #

class BrukerData:
    """
Class to store and process data of a Bruker MRI Experiment
    """
    def __init__(self, path="", ExpNum=0, ExpName = ""):
        self.method = {}
        self.acqp = {}
        self.visu = {}
        self.d3proc = {}

        #ImtenseData 3d matrix [x][y][z/(number of images)]
        self.IntenseData = np.array([])

        #Dimension[1] -> x dimension
        #Dimension[2] -> y dimension
        #Dimension[0] -> number of images
        self.Dimension = np.zeros(3, dtype=np.int)

        self.ROI = np.array([])

        self.path = path
        self.ExpNum = ExpNum
        self.ExpName = ExpName
        
    
    def Resolution(self):
        if self.method and ("PVM_SpatResol" in self.method) \
                       and len(list(self.method["PVM_SpatResol"]))>=2:

            SpatResolX = float(self.method["PVM_SpatResol"][0])
            SpatResolY = float(self.method["PVM_SpatResol"][1])
        else:
            SpatResolX = float(self.ROI[0]) / (self.Dimension[1] - 1)
            SpatResolY = float(self.ROI[1]) / (self.Dimension[2] - 1)

        return np.asarray([SpatResolX, SpatResolY])

    def SliceDistance(self):
        try:
            if self.method and ("PVM_SpatResol" in self.method) \
                           and len(list(self.method["PVM_SpatResol"]))==3:

                return float(self.method["PVM_SpatResol"][2])

            elif not self.visu:
                raise Exception("There is no 'visu_pars' data in {0}/{1}".format(self.ExpName, self.ExpNum))

            elif not ("PVM_SPackArrSliceDistance" in self.method) \
                 or type(self.method["PVM_SPackArrSliceDistance"]) != float:

                raise Exception("Uncorrect SliceDistance parameter in the " +\
                                "\'method\' data in {0}/{1}".format(self.ExpName, self.ExpNum))

            else:
                return float(self.method["PVM_SPackArrSliceDistance"])

        except Exception as err:
            utils.logger.warning(err)
            return None

    def ImageWordType(self):

        #visuType = [BIT, SGN/UNSGN, TYPE]

        _, [img_bit, img_sgn, img_type]= ImageBitType(self.visu, self.d3proc)
        if img_sgn:
            return "{0} {1} {2}".format(img_bit,
                                        "signed" if img_sgn == "sgn" else "unsigned",
                                        img_type)
        else:
            return "{0} {1}".format(img_bit,
                                    img_type)

    def LeftTopCoordinates(self):
        if self.visu:
            return np.asarray(self.visu["VisuCorePosition"])
        else:
            return np.array([])

    def SliceOrientation(self):
        if self.visu:
            return self.visu["VisuCoreOrientation"]
        else:
            return np.array([])

# *************************************************************************** #
# ****************************** Functions ********************************** #
# *************************************************************************** #

def check_dict(AllFiles):
    """
Find uncorrect data in AllFiles and remove it
    """
    import collections

    for exp_name in list(AllFiles.keys()):

        for exp_num in list(AllFiles[exp_name].keys()):
            if not AllFiles[exp_name][exp_num]:
                utils.logger.warning("There is no '2dseq' data in {0}\{1}".format(exp_name, exp_num))
                del AllFiles[exp_name][exp_num]

        AllFiles[exp_name] = utils.sort_dict(AllFiles[exp_name])

        if not AllFiles[exp_name]:
            utils.logger.warning("There is no any experiments with '2dseq' data in {}".format(exp_name))
            del AllFiles[exp_name]

    return AllFiles

def CorrectBrukerData(data):
    _, [img_bit, _, _] = ImageBitType(data.visu, data.d3proc)
    dim = 2**(img_bit)
    return np.where(data.IntenseData < 0, data.IntenseData + dim, data.IntenseData)

def get_parser():
    """ 
Get parser object for script bruker.py
    """
    from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
    parser = ArgumentParser(description=__doc__,
                            formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument("-i", "--ifile",
                        dest="InputFile",
                        type=lambda x: is_valid_file(parser, x),
                        help="read data from FILE",
                        metavar="INPUTFILE")
    parser.add_argument("-o", "--ofile",
                        dest="OutputFile",
                        type=str,
                        help="write data to text OUTPUT_FILE",
                        metavar="OUTPUT_FILE")
    parser.add_argument("-x", "--oxmlfile",
                        dest="OutputXMLFile",
                        type=str,
                        help="write data to XML OUTPUT_XML_FILE",
                        metavar="OUTPUT_XML_FILE")
    parser.add_argument("-d", "--idir",
                        dest="InputDir",
                        type=lambda x: is_valid_dir(parser, x),
                        help="get files from INPUT_DIR",
                        metavar="INPUT_DIR")
    parser.add_argument("--outdir",
                        dest="OutputDir",
                        help="write data to OUTPUT_DIR with filenames\
                              corresponding to the experiment name",
                        metavar="OUTPUT_DIR")
    parser.add_argument("--expname", 
                        dest="ExpName",
                        type=str,
                        help="Choose certain name of the experiment",
                        metavar="EXP_NAME")
    parser.add_argument("--expnum", 
                        dest="ExpNum",
                        type=int,
                        help="Choose certain number of the experiment",
                        metavar="EXP_NUM")
    # parser.add_argument("-n",
    #                     dest="n",
    #                     type=int,
    #                     help="number of output images")
    return parser

def HeaderForTextFile(file, data):

    file.write("Dimension == {0}\n".format(data.Dimension))
    file.write("Resolution == {0}\n".format(data.Resolution()))
    file.write("SliceDistance == {0}\n".format(data.SliceDistance()))
    file.write("LeftTopCoordinates == {0}\n".format(data.LeftTopCoordinates()))
    file.write("SliceOrientation == \n{0}\n".format(data.SliceOrientation()))
    file.write("ImageWordType == {0}\n".format(data.ImageWordType()))
    file.write("IntenseData == \n")

def ImageBitType(visu, d3proc):
    """
Return bitness of the image in the format as "intBIT"(for example "int16")
    """
    # Return list of the values from VisuCoreWordType:
    # visuType = [(numBIT, SGN/UNSGN, TYPE)]
    img_bit = 16
    img_sgn = "sgn"
    img_type = "int"

    if visu:
        visuType = re.findall('[^_]+', visu["VisuCoreWordType"])
        img_bit = int(visuType[0].replace("BIT", ""))

        if len(visuType) == 3:
            img_sgn = visuType[1].lower()
            img_type = visuType[2].lower()
        else: # if no SGN is specified
            img_type = visuType[1].lower()
            img_sgn = None

    elif d3proc:
        # get size of the '2dseq' file in byte
        dseq_path = d3proc["path_to_file"].replace("d3proc","2dseq")
        dseq_size = os.stat(dseq_path).st_size

        img_bit = int(dseq_size * 8 / (d3proc['IM_SIX'] * d3proc['IM_SIY'] * d3proc['IM_SIZ']))

    if img_type == "int":
        numpy_type = '{0}{1}'.format(img_type if img_sgn == "sgn" else 'uint', img_bit)
    else:
        numpy_type = '{0}{1}'.format(img_type, img_bit)

    return np.dtype(numpy_type), [img_bit, img_sgn, img_type]

def is_valid_file(parser, arg):
    """
Check if arg is a valid file that already exists on the file system.

Parameters
----------
parser : argparse object
arg : str

Returns
-------
arg
    """
    arg = os.path.abspath(arg)
    if not os.path.exists(arg):
        parser.error("The file %s does not exist!" % arg)
    else:
        return arg

def is_valid_dir(parser, arg):
    """
Check if arg is a valid directory that already exists on the file system.

Parameters
----------
parser : argparse object
arg : str

Returns
-------
arg
    """
    arg = os.path.abspath(arg)
    if not os.path.isdir(arg):
        parser.error("The file %s is not a directory!" % arg)
    elif not os.path.exists(arg):
        parser.error("The directory %s does not exist!" % arg)
    else:
        return arg

def ParseArray(current_file, line):

    # extract the arraysize and convert it to numpy
    line = line[1:-2].replace(" ", "").split(",")
    arraysize = np.array([int(x) for x in line])

    # then extract the next line
    vallist = current_file.readline().split()

    # if the line was a string, then return it directly
    try:
        float(vallist[0])
    except ValueError:
        return " ".join(vallist)

    # include potentially multiple lines
    while len(vallist) != np.prod(arraysize):
        vallist = vallist + current_file.readline().split()

    # try converting to int, if error, then to float
    
    try:
        vallist = [int(x) for x in vallist]
    except ValueError:
        vallist = [float(x) for x in vallist]

    # convert to numpy array
    if len(vallist) > 1:
        if np.size(arraysize) > 1 and arraysize[1] == 9:
            arraysize = np.array([arraysize[0], 3, 3])

        return np.reshape(np.array(vallist),
                          arraysize[1:] if arraysize[0] == 1 else arraysize)
    # or to plain number
    else:
        return vallist[0]

def ParseSingleValue(val):

    try: # check if int
        result = int(val)
    except ValueError:
        try: # then check if float
            result = float(val)
        except ValueError:
            # if not, should  be string. Remove  newline character.
            result = val.rstrip('\n')

    return result

def PathToFile(files_dict, filename = "", ExpNum = 0, ExpName = ""):
    """
Find path to "filename" in the "files_dict".

"ExpNum" indicates the certain number of experiment, if no number is specified, 
then the first number in the dictionary is selected.

"ExpName" indicates the certain name of experiment, if no name is specified, 
then the first name in the dictionary is selected.
    """
    if not ExpName:
        ExpName = list(files_dict.keys())[0]

    elif ExpName not in list(files_dict.keys()):
        try:
            raise ValueError
        except ValueError:
            utils.logger.warning("No such name of the experiment")

    if not ExpNum:
        ExpNum = list(files_dict[ExpName].keys())[0]

    elif str(ExpNum) not in list(files_dict[ExpName].keys()):
        try:
            raise ValueError
        except ValueError:
            utils.logger.warning("No such number corresponding to the experiment")

    files = files_dict[ExpName][str(ExpNum)]
    try:
        for file in files:
            if file.find(filename) != -1:
                return file
        raise FileNotFoundError

    except FileNotFoundError:
        utils.logger.warning("Can't find such file '{0}' in {1}/{2}".format(filename, ExpName, ExpNum))
        return ''

def ReadDirectory(fpath):
    """
Reading directory according to the fpath and return a dictionary of files:

AllFiles{EXPNAME1 : {EXPNUM1 : [list of files], EXPNUM2 : [list of files], ..., 
                                                OTHER : [list of files]},
         EXPNAME2 : {EXPNUM1 : [list of files], EXPNUM2 : [list of files], ..., 
                                                OTHER : [list of files]},
         ...}

    """
    AllFiles = {}
    files_list = []
    expname = ""
    exp_number = ""
    common_files = {}
    end = 0
    inpdata = 0
    makesubnum = 0
    for path_to_file, subdirs, files in os.walk(fpath):

        if makesubnum:
            subnum = re.findall(r"pdata\\(\d+)$", path_to_file)
            if subnum:                
                exp_number = expnum + "." + subnum[-1]
                end = 1

        # if there is more then 1 data files in exp_num
        if inpdata:
            makesubnum = len(subdirs) > 1
            if not makesubnum:
                exp_number = expnum                
                end = 1
            else:
                common_files = files_list[:]
            inpdata = 0

        if "pdata" in subdirs:
            exp_tuple = re.findall(r'([^\\]+) \\ (\d+) $',
                                   path_to_file, re.X)[0]
            expname = exp_tuple[0]
            expnum = exp_tuple[1]
            if expname not in AllFiles.keys():
                AllFiles[expname] = {}

            inpdata = 1

        for name in files:
            if not set(["acqp", "2dseq"]).isdisjoint(files):
                files_list.append(os.path.join(path_to_file, name))

        if "2dseq" in files and end:
            end = 0
            if not set(common_files).issubset(files_list):
                files_list += common_files
            AllFiles[expname][exp_number] = files_list
            files_list = []
    return check_dict(AllFiles)

def ReadExperiment(files_dict, ExpNum, ExpName = ""):
    """
Read in a Bruker MRI Experiment. Returns raw data, processed data, 
and method, acqp and visu_pars parameters in a dictionary.

    """ 
    try:
        data = BrukerData(os.path, ExpNum, ExpName)
        # parameter files as dictionaries
        data.method = \
                ReadParamFile(PathToFile(files_dict, "method", ExpNum, ExpName))
        data.acqp = \
                ReadParamFile(PathToFile(files_dict, "acqp", ExpNum, ExpName))
        data.visu = \
                ReadParamFile(PathToFile(files_dict, "visu_pars", ExpNum, ExpName))

        data.d3proc = \
                ReadParamFile(PathToFile(files_dict, "d3proc", ExpNum, ExpName))

        # processed data
        data.IntenseData = \
                ReadProcessedData(PathToFile(files_dict, "2dseq", ExpNum, ExpName),
                                  data.visu, data.d3proc,
                                  data.acqp, ExpNum, ExpName)

        data.max_val = np.amax(data.IntenseData)
        data.min_val = np.amin(data.IntenseData)
        data.Dimension = np.asarray(data.IntenseData.shape)

        data.ROI = data.visu["VisuCoreExtent"]

        data.path = os.path
        data.ExpNum = ExpNum

        return data

    except Exception as err:
        utils.logger.warning(err)
        #utils.logger.exception(err)
        return None

def ReadParamFile(filepath):
    """
Read a Bruker MRI experiment's method or acqp file to a dictionary.
    """
    param_dict = {}
    if os.path.exists(filepath):
        with open(filepath, "r") as file:
            for line in file:

                # when line contains parameter
                if line.startswith('##$'):

                    (param_name, current_line) = line[3:].split('=') # split at "="

                    # if current entry (current_line) is arraysize
                    if current_line[0:2] == "( " and current_line[-3:-1] == " )":
                        value = ParseArray(file, current_line)

                    # if current entry (current_line) is struct/list
                    elif current_line[0] == "(" and current_line[-3:-1] != " )":

                        # if neccessary read in multiple lines
                        while current_line[-2] != ")":
                            current_line = current_line[0:-1] + file.readline()

                        # parse the values to a list
                        value = [ParseSingleValue(x)
                                 for x in current_line[1:-2].split(', ')]

                    # otherwise current entry must be single string or number
                    else:
                        value = ParseSingleValue(current_line)

                    # save parsed value to dict
                    param_dict[param_name] = value
        param_dict["path_to_file"] = filepath
    return param_dict

def ReadProcessedData(filepath, visu, d3proc, acqp, ExpNum, ExpName):
    """
Read the data of images from file "2dseq"
    """
    with open(filepath, "r") as f:
        
        np_type, [img_bit,_,_] = ImageBitType(visu, d3proc)
        data = np.fromfile(f, dtype=np_type)

        mn = np.amin(data)
        if mn < 0:
            utils.logger.info("There is a negative minimal value = '{0}' in {1}/{2}".format(mn, ExpName, ExpNum))

        if visu:
            if visu["VisuCoreDim"] == 1:
                raise Exception("\"VisuCoreDim\" is equal 1 in the \'visu_pars\' data in {0}/{1}".format(ExpName, ExpNum))

            data = data.reshape(-1, visu["VisuCoreSize"][0], visu["VisuCoreSize"][1])
        elif d3proc:
            data = data.reshape(-1, d3proc['IM_SIX'], d3proc['IM_SIY'])
        return data

def ShellForXMLWrite(data):
    root = etree.Element('data')

    dim = etree.SubElement(root, "tag", name="Dimension")
    etree.SubElement(dim, "x").text = str(data.Dimension[1])
    etree.SubElement(dim, "y").text = str(data.Dimension[2])
    etree.SubElement(dim, "z").text = str(data.Dimension[0])

    if data.Resolution().any():
        res = etree.SubElement(root, "tag", name="Resolution")
        etree.SubElement(res, "x").text = str(data.Resolution()[0])
        etree.SubElement(res, "y").text = str(data.Resolution()[1])

    if data.SliceDistance():
        etree.SubElement(root, "tag", name="SliceDistance").text = str(data.SliceDistance())

    if data.LeftTopCoordinates().any():
        ltc = etree.SubElement(root, "tag", name="LeftTopCoordinates")
        etree.SubElement(ltc, "x").text = str(data.LeftTopCoordinates()[0])
        etree.SubElement(ltc, "y").text = str(data.LeftTopCoordinates()[1])
        etree.SubElement(ltc, "z").text = str(data.LeftTopCoordinates()[2])

    if data.SliceOrientation().any():
        orient = etree.SubElement(root, "tag", name="SliceOrientation")
        etree.SubElement(orient, "v1").text = str(data.SliceOrientation()[0])
        etree.SubElement(orient, "v2").text = str(data.SliceOrientation()[1])
        etree.SubElement(orient, "v3").text = str(data.SliceOrientation()[2])

    etree.SubElement(root, "tag", name="ImageWordType").text = str(data.ImageWordType())

    return root

def SingleWriteToTextFile(fname, data = None, index = 0, create = False):
    """
Write the index number of the Image from data in a text file with FNAME nam
    """
    np.set_printoptions(threshold=np.nan)
    if create:
        file = open(fname, "w")
        HeaderForTextFile(file, data)        
    else:
        file = open(fname, "a")

    file.write('\n# Image = {0}\n'.format(index+1))
    file.write(np.array2string(data.IntenseData[index,:,:]))

    file.close()

def SingleWriteToXMLFile(fname, data = None, index = 0, create = False,):
    """
Write the index number of the Image from data in a XML file with FNAME name
    """
    np.set_printoptions(threshold=np.nan)

    if create:
        root = ShellForXMLWrite(data)

        img_data = etree.SubElement(root, "tag", name="IntenseData")
        
        elem = etree.SubElement(img_data, "image")
        elem.set("number", str(index + 1))
        elem.text = np.array2string(data.IntenseData[index,:,:])

        tree = etree.ElementTree(root)
    else:
        # add new Images in the old xml file

        tree = etree.parse(fname)
        xmlRoot = tree.getroot()
        elem = etree.SubElement(xmlRoot[-1], "image")
        elem.text = np.array2string(data.IntenseData[index,:,:])
        elem.set("number", str(index + 1))

    tree.write(fname)

def WriteToTextFile(fname, data):
    """
Write all Images from data in a text file with FNAME name
    """
    file = open(fname, "w")
    HeaderForTextFile(file, data)
    for i in range(data.Dimension[0]):
        file.write('\n# Image = {0}\n'.format(i+1))
        np.set_printoptions(threshold=np.nan)
        file.write(np.array2string(data.IntenseData[i,:,:]))
    file.close()

def WriteToXMLFile(fname, data):
    """
Write all Images from data in a XML file with FNAME name
    """
    root = ShellForXMLWrite(data)

    img_data = etree.SubElement(root, "tag", name="IntenseData")

    np.set_printoptions(threshold=np.nan)
    for i in range(data.Dimension[0]):
        etree.SubElement(img_data, "image{}".format(i)).text = np.array2string(data.IntenseData[i,:,:])

    brukerdata = etree.ElementTree(root)
    brukerdata.write(fname)

# *************************************************************************** #
# --------------------------------------------------------------------------- #
# *************************************************************************** #

if __name__ == "__main__":
    args = get_parser().parse_args()

    inputFile = args.InputFile
    inputDir = args.InputDir
    outputFile = args.OutputFile
    outputXMLFile = args.OutputXMLFile
    outputDir = args.OutputDir
    expName = args.ExpName
    expNum = args.ExpNum

    if inputDir:
        files_dict = ReadDirectory(inputDir)

    if outputFile:
        if not expName:
            expName = list(files_dict.keys())[0]

        if not expNum:
            for num in list(files_dict[expName].keys()):
                experiment = ReadExperiment(files_dict, num, expName)
                file = open("{0}_{1}".format(num, outputFile), "w")
                WriteToFile(file, experiment)
                file.close()

        else:
            experiment = ReadExperiment(files_dict, expNum, expName)
            WriteToFile(outputFile, experiment)

    if outputXMLFile:
        if not expName:
            expName = list(files_dict.keys())[0]

        if not expNum:
            for num in list(files_dict[expName].keys()):
                experiment = ReadExperiment(files_dict, num, expName)
                fname = "{0}_{1}".format(num, outputXMLFile)
                WriteToXMLFile(fname, experiment)

        else:
            experiment = ReadExperiment(files_dict, expNum, expName)
            WriteToXMLFile(outputXMLFile, experiment)

    if outputDir:
        if not expName:
            expName = list(files_dict.keys())[0]

        if not expNum:
            for num in list(files_dict[expName].keys()):
                experiment = ReadExperiment(files_dict, num, expName)
                f_path = os.path.join(outputDir, "{0}_{1}".format(num,expName))
                WriteToFile(f_path, experiment)

        else:
            experiment = ReadExperiment(files_dict, expNum, expName)
            WriteToFile(outputDir, experiment)
            