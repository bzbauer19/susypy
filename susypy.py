import os
import subprocess
import typing as tt
import shutil
import datetime as dt
import matplotlib.pyplot as plt
import numpy as np

class SLHA:
    def __init__(self, slha: str, softpoint_dir: str, in_dir: str | None=None, out_dir: str | None=None):
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

   
    def gen_output(self, suppress: bool=True) -> SLHA:

        command = (self.softpoint + " leshouches < " + self.slha + " > " + self.out_dir + "/Output_" + self.slha_name)
        process = subprocess.run(command, shell=True, capture_output=True)

        if not suppress:
            print(process.stdout)
            print(process.stderr)

        if process.returncode != 0:
            raise RuntimeError("Softsusy failure")
        
        return SLHA(self.out_dir + "/Output_" + self.slha_name, self.softpoint, in_dir=self.in_dir, out_dir=self.out_dir)


    def _parse(self):

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


    def _clean_data(self, dirty: tt.List) -> dict:
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


    def to_numeric_cell(self, cell: tt.List) -> tt.List:
        ## ASSUMES INPUT CELL IS NUMERIC WITH COMMENTS
        numeric_cell = []
        for row in cell:
            print(row[-1] + " " + " ".join(row[:-1])) # Displays comment and associated data
            cast_row = [float(i) for i in row[:-1]]

            numeric_cell.append(cast_row)

        return numeric_cell


    def set_param(self, param: tt.Tuple, value: str, loc: int=1):
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


    def create_copy(self, name: str, suppress: bool=True, new_dir_name: str=None) -> SLHA:

        next_in_dir = self.in_dir
        next_out_dir = self.out_dir

        if new_dir_name is not None:
            if not os.path.exists(self.in_dir + "/" + new_dir_name) : os.makedirs(self.in_dir + "/" + new_dir_name)
            if not os.path.exists(self.out_dir + "/" + new_dir_name) : os.makedirs(self.out_dir + "/" + new_dir_name)

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
        
        return SLHA(direc + "/" + name, self.softpoint, in_dir=next_in_dir, out_dir=next_out_dir)
    
    def get_data(self, param: str, line: str) -> tt.List[str]:
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
    def gen_resum(self, particle1: str, particle2: str, collider_type: str="proton-proton", com: int=13000):

        if not self.check_particle(particle1) or not self.check_particle(particle2):
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
    
    
    def check_particle(self, particle):
        valid_resum_particles = ["11", "12", "13", "14", "15", "16",
                                 "1000011", "1000013", "1000015", "1000012", "1000014", "1000016",
                                 "2000011", "2000013", "2000015",
                                 "1000022", "1000023", "1000024", "1000025", "1000035", "1000037",
                                 "1000001", "1000002", "1000003", "1000004", "1000005", "1000006",
                                 "2000001", "2000002", "2000003", "2000004", "2000005", "2000006",
                                 "1000021"]
        
        return True if str(np.abs(int(particle))) in valid_resum_particles else False

    
    def cross_section(self, particle1: str, particle2: str, order: str="lo", suppress=True):

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
                





def scan_params(base_slha: SLHA, params: tt.List[str], param_values: tt.List[str], purge: bool=False):
    orig_name = base_slha.slha_name
    scans = []

    dtime = dt.datetime.now()
    date_string = dtime.date().isoformat() + "_" + str(dtime.time().hour) + "-" + str(dtime.time().minute) + "-" + f"{dtime.time().second:.0f}"

    for i in range(len(params)):
        if params[i][0] not in base_slha.block_list and params[i][0] not in base_slha.decay_list:
            raise RuntimeError(f"Cannot set {params[i]}, parameter does not exist.")
        
        for value in param_values[i]:
            new_name = params[i][0] + "_" + str(params[i][1]) + "_" + str(int(float(value))) + "_" + orig_name
            new_slha = base_slha.create_copy(new_name, new_dir_name=date_string)

            new_slha.set_param(params[i], value)
            new_out_slha = new_slha.gen_output()
            scans.append(new_out_slha)

    if purge:
        shutil.rmtree(new_slha.in_dir)
        shutil.rmtree(new_slha.out_dir)
    
    return scans

def gather_data(slha_list: tt.List[SLHA], param: str, line: str, col: int=1) -> tt.List[float]:
    data = []

    for slha in slha_list:
        point = slha.get_data(param, line)
        if col < len(point):
            data.append(float(point[col]))
        else:
            raise IndexError(f"This section only has {len(point)-1} values.")
    
    return data

def plot_scan(slha_list: tt.List[SLHA], 
              param_x: str, line_x: str, 
              param_y: str, lines_y: tt.List[str], 
              col_x: int=1, col_y: int=1,
              abs_val: bool=False, 
              fig=None, ax=None,
              label_list: tt.List[str]=None):
    
    if fig is None and ax is None:
        fig, ax = plt.subplots()

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

