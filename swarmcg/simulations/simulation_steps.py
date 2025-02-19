import os
import re

from swarmcg.shared import exceptions
from swarmcg.shared.utils import parse_string_args


class BaseSimulationConfig:
    REQUIRED_FIELDS = []

    def __init__(self, filename):
        if not os.path.isfile(filename):
            raise exceptions.MissingMdpFile(filename)
        else:
            self.sim_setup = BaseSimulationConfig.read_mdp(filename)

        self._validate_init()
        self.base_name = os.path.basename(filename)

    @staticmethod
    def read_mdp(filename):
        with open(filename, "r") as f:
            raw_content = f.readlines()
        SUB_PATTERN = r"[\n\t\s]*"
        SPLIT_PATTER = r"(.*)=(.*)"
        KEEP_PATTERN = r"^[^;]*"
        f_clean = lambda x: re.sub(SUB_PATTERN, "", x)
        f_split = lambda x: (
            re.match(SPLIT_PATTER, x).groups()
            if re.match(SPLIT_PATTER, x)
            else (None, None)
        )
        f_keep = lambda x: (
            re.match(KEEP_PATTERN, x).group() if re.match(KEEP_PATTERN, x) else None
        )
        cleaned = filter(None, map(f_clean, raw_content))
        split = map(f_split, cleaned)
        sim_setup = {k: f_keep(v) for k, v in split if k is not None}
        return {k: parse_string_args(v) for k, v in sim_setup.items()}

    def to_string(self):
        output_string = ""
        for k, v in self.sim_setup.items():
            output_string += f"{k}".ljust(25, " ") + f"  = {str(v)}\n"
        return output_string

    def _validate_init(self):
        missing_args = ", ".join(
            [i for i in type(self).REQUIRED_FIELDS if i not in self.sim_setup.keys()]
        )
        if missing_args:
            msg = (
                f"The following arguments are missing form mdp file for {self.name}: {missing_args}. "
                "Please check you input."
            )
            raise exceptions.MissformattedFile(msg)

    def modify_mdp(
        self,
        sim_time=None,
        nb_frames=1500,
        log_write_freq=5000,
        energy_write_nb_frames_ratio=0.1,
    ):
        if self.edit_mpd:
            if sim_time is not None:
                new_nsteps = int(sim_time * 1000 / self.sim_setup["dt"])
            else:
                new_nsteps = int(self.sim_setup["nsteps"])

            self.sim_setup["nsteps"] = new_nsteps
            # self.sim_setup["nb_frames"] = nb_frames
            self.sim_setup["nstlog"] = log_write_freq
            self.sim_setup["nstvout"] = new_nsteps
            self.sim_setup["nstxout"] = new_nsteps
            self.sim_setup["nstfout"] = new_nsteps

            output_energy_freq = int(
                new_nsteps / nb_frames / energy_write_nb_frames_ratio
            )
            self.sim_setup["nstcalcenergy"] = output_energy_freq
            self.sim_setup["nstenergy"] = output_energy_freq
            self.sim_setup["nstxout-compressed"] = int(new_nsteps / nb_frames)

        return self

    def to_file(self, destination_path):
        with open(os.path.join(destination_path, self.base_name), "w") as fp:
            fp.writelines(self.to_string())


class Minimisation(BaseSimulationConfig):
    REQUIRED_FIELDS = ["nsteps", "nstlog"]
    swarmcg_flag = "cg_sim_mdp_mini"
    step_name = "minimisation"
    md_output = "mini"
    mdp_base_name = "mdp_minimization_basename"
    edit_mpd = False


class Equilibration(BaseSimulationConfig):
    REQUIRED_FIELDS = ["dt", "nsteps", "nstlog"]
    swarmcg_flag = "cg_sim_mdp_equi"
    step_name = "equilibration"
    md_output = "equi"
    mdp_base_name = "mdp_equi_basename"
    edit_mpd = False


class Production(BaseSimulationConfig):
    REQUIRED_FIELDS = ["dt", "nsteps", "nstlog"]
    swarmcg_flag = "cg_sim_mdp_md"
    step_name = "production"
    md_output = "md"
    mdp_base_name = "mdp_md_basename"
    edit_mpd = True


def select_class(flag, ns):
    filename = getattr(ns, flag)
    if "mdp_md_basename" == flag:
        return Production(filename)
    elif "mdp_equi_basename" == flag:
        return Equilibration(filename)
    elif "mdp_minimization_basename" == flag:
        return Minimisation(filename)
    else:
        ValueError(f"Flag {flag} does not correspond to any class.")
