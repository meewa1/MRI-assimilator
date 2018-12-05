#!/usr/bin/env python3

import numpy as np
import utils

import brukerWriter as bw

class BrukerData():
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
        import brukerReader as br
        _, [img_bit, img_sgn, img_type] = br.ImageBitType(self.visu, self.d3proc)
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

if __name__ == "__main__":
    args = get_parser().parse_args()

    import brukerReader as br
    
    inputFile = args.InputFile
    inputDir = args.InputDir
    outputFile = args.OutputFile
    outputXMLFile = args.OutputXMLFile
    outputDir = args.OutputDir
    expName = args.ExpName
    expNum = args.ExpNum

    if inputDir:
        files_dict = br.ReadDirectory(inputDir)

    if outputFile:
        if not expName:
            expName = list(files_dict.keys())[0]

        if not expNum:
            for num in list(files_dict[expName].keys()):
                experiment = br.ReadExperiment(files_dict, num, expName)
                file = open("{0}_{1}".format(num, outputFile), "w")
                bw.WriteToTextFile(file, experiment)
                file.close()

        else:
            experiment = br.ReadExperiment(files_dict, expNum, expName)
            bw.WriteToTextFile(outputFile, experiment)

    if outputXMLFile:
        if not expName:
            expName = list(files_dict.keys())[0]

        if not expNum:
            for num in list(files_dict[expName].keys()):
                experiment = br.ReadExperiment(files_dict, num, expName)
                fname = "{0}_{1}".format(num, outputXMLFile)
                bw.WriteToXMLFile(fname, experiment)

        else:
            experiment = br.ReadExperiment(files_dict, expNum, expName)
            bw.WriteToXMLFile(outputXMLFile, experiment)

    if outputDir:
        if not expName:
            expName = list(files_dict.keys())[0]

        if not expNum:
            for num in list(files_dict[expName].keys()):
                experiment = br.ReadExperiment(files_dict, num, expName)
                f_path = os.path.join(outputDir, "{0}_{1}".format(num,expName))
                bw.WriteToTextFile(f_path, experiment)

        else:
            experiment = br.ReadExperiment(files_dict, expNum, expName)
            bw.WriteToTextFile(outputDir, experiment)
            