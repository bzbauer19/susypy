import os
import subprocess
import typing as tt
import shutil
import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.colors as cplt
import numpy as np


class SLHA:
    """
    Class for handling SLHA (SUSY Les Houches Accord) format files
    and running softsusy on the file.
    """
    def __init__(self, slha: str, 
                softpoint_dir: str, 
                in_dir: str | None = None, 
                out_dir: str | None = None):
        
        """
        Class initialization for SLHA files.

        Parameters:
        slha (str): File name for the SLHA file including file extension.
        softpoint_dir (str): Directory path of SOFTSUSY softpoint.x
        in_dir (str | None, optional): Directory path for the input SLHA file. Default is None.
        out_dir (str | None, optional): Directory path for the output SLHA file after softpoint is run. Default is None.

        Returns:
        No return.
        """

        self.slha_name = slha.split("/")[-1]
        self.softpoint = softpoint_dir
        if in_dir is None:
            if not os.path.exists(os.getcwd()+'/input/'):
                os.makedirs(os.getcwd()+'/input/')
            self.in_dir = os.getcwd()+'/input/'
        else:
            self.in_dir = in_dir

        if out_dir is None:
            if not os.path.exists(os.getcwd()+'/output/'):
                os.makedirs(os.getcwd()+'/output/')
            self.out_dir = os.getcwd()+'/output/'
        else:
            self.out_dir = out_dir

        if os.path.exists(slha):
            self.slha = slha
        elif os.path.exists(self.in_dir + "/" + slha):
            self.slha = self.in_dir + "/" + slha
        else:
            raise ValueError("SLHA file not found.")
        
        self._parse()

    def gen_output(self, suppress: bool = True) -> SLHA:
        """
        Runs the SOFTSUSY softpoint.x program on the SLHA instance.
        A new SLHA file is generated based on the existing parameters
        within the SLHA file.

        Parameters:
        suppress (bool, optional): Option to suppress the subprocess stdout and stderr. Default is True.

        Returns:
        SLHA: The output SLHA from running softpoint.x. Returns a new SLHA object.
        """

        command = (self.softpoint 
                   + " leshouches < " 
                   + self.slha + " > " 
                   + self.out_dir 
                   + "/Output_" 
                   + self.slha_name)
        process = subprocess.run(command, shell=True, capture_output=True)

        if not suppress:
            print(process.stdout)
            print(process.stderr)

        if process.returncode != 0:
            raise RuntimeError("Softsusy failure")
        
        return SLHA(self.out_dir 
                    + "/Output_" 
                    + self.slha_name, 
                    self.softpoint, 
                    in_dir=self.in_dir, 
                    out_dir=self.out_dir)

    def _parse(self):
        # Reads the SLHA file and compiles the blocks and decays into two dictionaries for data reference.

        do_block = False
        do_decay = False
        block_list = []
        decay_list = []
        temp = []

        with open(self.slha) as slha_file:
            for line in slha_file:
                if line[0] == "#":
                    continue

                if "block" in line.lower():
                    if do_block:
                        block_list.append(temp)
                    
                    if do_decay:
                        decay_list.append(temp)

                    do_decay = False
                    do_block = True
                    
                    temp = []

                elif "decay" in line.lower():
                    if do_block:
                        block_list.append(temp)
                    
                    if do_decay:
                        decay_list.append(temp)

                    do_block = False
                    do_decay = True

                    temp = []

                temp.append(line.split())
        
        self.block_list = self._clean_data(block_list)
        self.decay_list = self._clean_data(decay_list)

    def _clean_data(self, dirty: list) -> dict:
        # Takes in a 2D list of data from _parse and removes unncessary information and assembles a dictionary with headers as keys.

        temp_cell = []
        clean = {}
        for cell in dirty:
            temp_cell = []
            dict_key = ''
            for row in cell:
                rlow = [s.lower() for s in row]
                if "block" in rlow or "decay" in rlow:
                    dict_key = row[1]
                    continue
                try:
                    comment_start = row.index('#')
                    comment = " ".join(row[comment_start+1:])
                    temp_row = row[:comment_start]
                    temp_row.append(comment)
                except:
                    temp_row = row
                temp_cell.append(temp_row)
            clean[dict_key] = temp_cell
        return clean

    def to_floats(self, cell: list[str]) -> list[float]:
        """
        Converts a set of Block values or Decay values to floats from strings.
        This function assumes that the input list is 1D and only contains numbers and comments.

        Parameters:
        cell (list[str]): 1D list of strings to be converted to floats, comments are allowed.

        Returns:
        list[float]: 2D list of floats from cell strings, comments are removed.
        """

        floats = []
        for row in cell:
            print(row[-1] + " " + " ".join(row[:-1])) # Displays comment and associated data
            cast_row = [float(i) for i in row[:-1]]

            floats.append(cast_row)

        return floats

    def set_param(self, param: tuple[str, int], value: str, loc: int = 1):
        """
        Overwrites the SLHA file to replace the specified Block parameter with a new value.

        Parameters:
        param (tuple[str, int]): (Block name, line number) to be assigned a new value.
        value (str): String value that will overwrite the specified parameter.
        loc (int, optional): Optionally select a column in the file. Default is column 1.

        Returns:
        No returns.
        *Note that the values in SLHA files are typically numeric and the columns are zero-indexed.*
        """

        search_block = False
        temp_lines = []

        with open(self.slha) as slha:
            for line in slha:
                if not search_block:
                    if param[0] in line:
                        search_block = True
                else:
                    if str(param[1]) == str(line.split()[0]):
                        temp = line.split()
                        temp[loc] = value
                        line = " ".join(temp) + "\n"

                        search_block = False
                
                temp_lines.append(line)
        
        with open(self.slha, "w") as slha:
            for line in temp_lines:
                slha.write(line)

    def create_copy(self, name: str, 
                    suppress: bool = True, 
                    new_dir_name: str | None = None) -> SLHA:
        """
        Creates a copy of the SLHA file this instance references.

        Parameters:
        name (str): The new name for the copy being created.
        suppress (bool, optional): Option to suppress the subprocess stdout and stderr. Default is True.
        new_dir_name (str | None, optional): New absolute path to a directory for the file to be copied to. Default is None.

        Returns:
        SLHA: Copy of this SLHA instance. This is a separate SLHA object.
        """

        next_in_dir = self.in_dir
        next_out_dir = self.out_dir

        if new_dir_name is not None:
            if not os.path.exists(self.in_dir + "/" + new_dir_name):
                os.makedirs(self.in_dir + "/" + new_dir_name)
            if not os.path.exists(self.out_dir + "/" + new_dir_name):
                os.makedirs(self.out_dir + "/" + new_dir_name)

            next_in_dir = self.in_dir + "/" + new_dir_name
            next_out_dir = self.out_dir + "/" + new_dir_name
        
        direc = "/".join(self.slha.split('/')[:-1])
        if new_dir_name is not None:
            direc = next_in_dir
        command = "cp " + self.slha + " " + direc + "/" + name
        process = subprocess.run(command, shell=True, capture_output=True)

        if not suppress:
            print(process.stdout)
            print(process.stderr)

        if process.returncode != 0:
            raise RuntimeError("Copy failure")
        
        return SLHA(direc + "/" + name,
                    self.softpoint, 
                    in_dir=next_in_dir, 
                    out_dir=next_out_dir)
    
    def get_data(self, param: str, line: str) -> list[str]:
        """
        Grabs data row from specified block/decay at a line given.

        Parameters:
        param (str): The intended parameter whose data to extract.
        line (str): Line number within a block/decay to extract data from.

        Returns:
        list[str]: Data at specified location. Note that the data has not been cast yet.
        """

        if param in self.block_list.keys():
            block = self.block_list[param]
            for row in block:
                if line in row:
                    value = row
        elif param in self.decay_list.keys():
            decay = self.block_list[param]
            for row in decay:
                if line in row:
                    value = row
        else:
            raise ValueError(f"{param} is not a valid parameter.")

        return value
    
    #maybe change to kwargs in the future if other options are necessary
    def gen_resum(self, 
                  particle1: str, 
                  particle2: str, 
                  collider_type: str = "proton-proton", 
                  com: int = 13000) -> str:
        """
        Generates an input file for the Resummino program based on specified inputs.
        Resummino can only handle electroweak SUSY productions and this function is limited
        to two-body cross sections.

        Parameters:
        particle1 (str): PDG identifier for particle 1 in a SUSY two-body production.
        particle2 (str): PDG identifier for particle 2 in a SUSY two-body production.
        collider_type (str, optional): Type of collider considered. Either proton-proton or proton-antiproton. Default is proton-proton.
        com (int, optional): Center of mass energy of the collider in GeV. Default is 13 TeV.

        Returns:
        str: File path for the generated Resummino input.
        """

        if not self._check_particle(particle1) or not self._check_particle(particle2):
            raise ValueError("One or both particles provided are not allowed or do not exist.")
        
        resum_name = self.slha.split(".txt")[0] + "_RESUM.txt"
        with open(resum_name, "w") as rsum:
            rsum.write(f"collider_type = {collider_type}\n")
            rsum.write(f"center_of_mass_energy = {com}\n")
            rsum.write(f"particle1 = {particle1}\n")
            rsum.write(f"particle2 = {particle2}\n")
            rsum.write(f"result = total\n")
            rsum.write(f"M = auto\n")
            rsum.write(f"pt = auto\n")
            rsum.write(f"slha = {self.slha}\n")
            rsum.write(f"zpwp = 0\n")
            rsum.write(f"pdf_format = lhgrid\n")
            rsum.write(f"pdf_lo = CT14lo\n")
            rsum.write(f"pdfset_lo = 0\n")
            rsum.write(f"pdf_nlo = CT14nlo\n")
            rsum.write(f"pdfset_nlo = 0\n")
            rsum.write(f"mu_f = 1.0\n")
            rsum.write(f"mu_r = 1.0\n")
            rsum.write(f"precision = 0.01\n")
            rsum.write(f"max_iters = 5\n")
            rsum.write(f"Minv_min = auto\n")
            rsum.write(f"Minv_max = auto\n")
            rsum.write(f"weight_valence = -1.6\n")
            rsum.write(f"weight_sea = -1.6\n")
            rsum.write(f"weight_gluon = -1.6\n")
            rsum.write(f"xmin = auto\n")

        return resum_name
    
    def _check_particle(self, particle):
        # Function to check whether the particle is acceptable for Resummino

        valid_resum_particles = ["11", "12", "13", "14", "15", "16",
                                 "1000011", "1000013", "1000015", "1000012", "1000014", "1000016",
                                 "2000011", "2000013", "2000015",
                                 "1000022", "1000023", "1000024", "1000025", "1000035", "1000037",
                                 "1000001", "1000002", "1000003", "1000004", "1000005", "1000006",
                                 "2000001", "2000002", "2000003", "2000004", "2000005", "2000006",
                                 "1000021"]
        
        return True if str(np.abs(int(particle))) in valid_resum_particles else False

    def cross_section(self, 
                      particle1: str, 
                      particle2: str, 
                      order: str = "lo", 
                      suppress: bool = True) -> tuple[float, float]:
        """
        Computes cross section in pb to specified order in perturbation theory
        for two specified particles using Resummino.

        Parameters:
        particle1 (str): PDG identifier for particle 1 in a SUSY two-body production.
        particle2 (str): PDG identifier for particle 2 in a SUSY two-body production.
        order (str, optional): Order in perturbation theory to compute to. Can be lo, nlo, nlo+nll. Default is lo.
        suppress (bool, optional): Option to suppress the subprocess stdout and stderr. Default is True.

        Returns:
        tuple[float, float]: Tuple of (cross-section, uncertainty) in units of pb.
        """

        self.resum = self.gen_resum(particle1, particle2)

        self.resum_out = f"{self.slha.split(".txt")[0]}_CrossSection_{particle1}_{particle2}.txt"

        command = f"resummino --{order} {self.resum} > {self.resum_out}"

        process = subprocess.run(command, shell=True, capture_output=True)

        if not suppress:
            print(process.stdout)
            print(process.stderr)

        if process.returncode != 0:
            raise RuntimeError("Resummino failure.")
        
        lo_result = ""
        nlo_result = ""
        nlo_nll_result = ""

        with open(self.resum_out) as s_file:
            result_reached = False
            for line in s_file:
                if result_reached == True:

                    if "NLL" in line:
                        print(line)
                        nlo_nll_result = line

                    elif "NLO" in line and "NLL" not in line:
                        print(line)
                        nlo_result = line

                    elif "LO" in line:
                        print(line)
                        lo_result = line

                else:
                    if "Results:" in line:
                        result_reached = True

        self.lo_sigma = float(lo_result.split()[2][1:])
        self.lo_uncty = float(lo_result.split()[4][:-1])

        self.nlo_sigma = float(nlo_result.split()[2][1:])
        self.nlo_uncty = float(nlo_result.split()[4][:-1])

        self.nlo_nll_sigma = float(nlo_nll_result.split()[2][1:])
        self.nlo_nll_uncty = float(nlo_nll_result.split()[4][:-1])

        match order:
            case "lo":
                return (self.lo_sigma, self.lo_uncty)
            
            case "nlo":
                return (self.nlo_sigma, self.nlo_uncty)
            
            case "nlo+nll":
                return (self.nlo_nll_sigma, self.nlo_nll_uncty)
                

# Plotting palette definition

color_palette = ["#648FFF", "#785EF0", "#DC267F",
                "#FE6100", "#FFB000"]
                
cmap_linear = cplt.LinearSegmentedColormap.from_list(
    name="colorblind-ibm", colors=color_palette
)


def scan_params(base_slha: SLHA, 
                params: list[str], 
                param_values: list[str], 
                purge: bool = False) -> list[SLHA]:
    """
    Given an input SLHA, generates output SLHAs for a range of parameters
    and a range of values for each parameter.

    Parameters:
    base_slha (SLHA): The initial SLHA object to reference for all outputs.
    params (list[str]): List of parameter names to scan over.
    param_values (list[str]): 2D list of values. There should be a list of values for each parameter in params.
    purge (bool, optional): Option to delete the generated folders of files after running. Default is False.

    Returns:
    list[SLHA]: List of generated SLHA objects from each parameter in params with each value in param_values. 
    """

    orig_name = base_slha.slha_name
    scans = []

    dtime = dt.datetime.now()
    date_string = (dtime.date().isoformat() 
        + "_" + str(dtime.time().hour) 
        + "-" + str(dtime.time().minute) 
        + "-" + f"{dtime.time().second:.0f}")

    for i in range(len(params)):
        if params[i][0] not in base_slha.block_list and params[i][0] not in base_slha.decay_list:
            raise RuntimeError(f"Cannot set {params[i]}, parameter does not exist.")
        
        for value in param_values[i]:
            new_name = (params[i][0] 
                + "_" + str(params[i][1]) 
                + "_" + str(int(float(value))) 
                + "_" + orig_name)
            new_slha = base_slha.create_copy(new_name, 
                                             new_dir_name=date_string)

            new_slha.set_param(params[i], value)
            new_out_slha = new_slha.gen_output()
            scans.append(new_out_slha)

    # purge should be changed to a separate function
    if purge:
        shutil.rmtree(new_slha.in_dir)
        shutil.rmtree(new_slha.out_dir)
    
    return scans


def gather_data(slha_list: list[SLHA], 
                param: str, 
                line: str, 
                col: int = 1) -> list[float]:
    """
    Gathers data from a specified parameter block/decay and line over
    a list of SLHA files.

    Parameters:
    slha_list (list[SLHA]): List of SLHA files to grab data from.
    param (str): The block/decay header name from which to grab data.
    line (str): The line number in the given block/decay as a string.
    col (int, optional): The column to extract data from within the specified line. Default is column 1.

    Returns:
    list[float]: Returns list of the requested data from each SLHA file.
    """

    data = []

    for slha in slha_list:
        point = slha.get_data(param, line)
        if col < len(point):
            data.append(float(point[col]))
        else:
            raise IndexError(f"This section only has {len(point)-1} values.")
    
    return data


def plot_scan(slha_list: list[SLHA], 
              param_x: str, line_x: str, 
              param_y: str, lines_y: list[str], 
              col_x: int = 1, col_y: int = 1,
              abs_val: bool = False, 
              fig: plt.Figure | None = None, ax: plt.Axes | None = None,
              label_list: list[str] = None) -> tuple[plt.Figure, plt.Axes]:
    """
    Create a plot with data collected from a list of SLHAs for a specified parameter

    Parameters:
    slha_list (list[SLHA]): List of SLHA files to gather data from.
    param_x (str): Block/Decay header to use as the horizontal axis.
    line_x (str): Line number within specified header for the horizontal variable.
    param_y (str): Block/Decay header to use as the vertical axis.
    lines_y (list[str]): Line number within specified header for the vertical variable.
    col_x (int, optional): Column of desired data within line for horizontal variable. Default is column 1.
    col_y (int, optional): Column of desired data within line for vertical variable. Default is column 1.
    abs_val (bool, optional): Boolean for whether the absolute value of the data set should be taken. Default is False.
    fig (Figure | None, optional): Optional parameter to supply a matplotlib Figure object. Default is None.
    ax (Axes | None, optional): Optional parameter to supply a matplotlib Axes object. Default is None.
    label_list (list[str]): Optional parameter to supply a list of labels for a legend. Default is None.

    Returns:
    tuple[Figure, Axes]: Returns the matplotlib Figure and Axes objects that have been plotted on.
    """
    
    if fig is None and ax is None:
        fig, ax = plt.subplots()

    ax.set_prop_cycle('color', color_palette)

    data_x = np.array(gather_data(slha_list, param_x, line_x, col=col_x))
    if abs_val:
        data_x = np.abs(data_x)

    if label_list is not None:
        for line, label in zip(lines_y, label_list):
            data_y = np.array(gather_data(slha_list, param_y, line, col=col_y))
            if abs_val:
                data_y = np.abs(data_y)
            
            ax.plot(data_x, data_y, label=label)

    else:
        for line in lines_y:
            data_y = np.array(gather_data(slha_list, param_y, line, col=col_y))
            if abs_val:
                data_y = np.abs(data_y)
            
            ax.plot(data_x, data_y)

    return (fig, ax)
