from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
from numpy.testing import assert_allclose, assert_array_equal

from pymatgen.io.lammps.outputs import LammpsDump, parse_lammps_dumps, parse_lammps_log
from pymatgen.util.testing import TEST_FILES_DIR

TEST_DIR = f"{TEST_FILES_DIR}/io/lammps"


class TestLammpsDump:
    @classmethod
    def setup_class(cls):
        with open(f"{TEST_DIR}/dump.rdx_wc.100", encoding="utf-8") as file:
            rdx_str = file.read()
        cls.rdx = LammpsDump.from_str(string=rdx_str)
        with open(f"{TEST_DIR}/dump.tatb", encoding="utf-8") as file:
            tatb_str = file.read()
        cls.tatb = LammpsDump.from_str(string=tatb_str)

    def test_from_str(self):
        assert self.rdx.timestep == 100
        assert self.rdx.natoms == 21
        assert_array_equal(self.rdx.box.bounds, np.array([(35, 48)] * 3))
        assert list(self.rdx.data.columns) == ["id", "type", "xs", "ys", "zs"]
        rdx_data = self.rdx.data.iloc[-1]
        rdx_data_target = [19, 2, 0.42369, 0.47347, 0.555425]
        assert_allclose(rdx_data, rdx_data_target)

        assert self.tatb.timestep == 0
        assert self.tatb.natoms == 384
        bounds = [[0, 13.624], [0, 17.1149153805], [0, 15.1826391451]]
        assert_allclose(self.tatb.box.bounds, bounds)
        tilt = [-5.75315630927, -6.325466, 7.4257288]
        assert_allclose(self.tatb.box.tilt, tilt)
        assert list(self.tatb.data.columns) == ["id", "type", "q", "x", "y", "z"]
        tatb_data = self.tatb.data.iloc[-1]
        tatb_data_target = [356, 3, -0.482096, 2.58647, 12.9577, 14.3143]
        assert_allclose(tatb_data, tatb_data_target)

    def test_json_dict(self):
        encoded = json.dumps(self.rdx.as_dict())
        decoded = json.loads(encoded)
        rdx = LammpsDump.from_dict(decoded)
        assert rdx.timestep == 100
        assert rdx.natoms == 21
        assert_array_equal(rdx.box.bounds, np.array([(35, 48)] * 3))
        pd.testing.assert_frame_equal(rdx.data, self.rdx.data)


class TestFunc:
    def test_parse_lammps_dumps(self):
        # gzipped
        rdx_10_pattern = f"{TEST_DIR}/dump.rdx.gz"
        rdx_10 = list(parse_lammps_dumps(file_pattern=rdx_10_pattern))
        time_steps_10 = [d.timestep for d in rdx_10]
        assert_array_equal(time_steps_10, np.arange(0, 101, 10))
        assert rdx_10[-1].data.shape == (21, 5)
        # wildcard
        rdx_25_pattern = f"{TEST_DIR}{os.path.sep}dump.rdx_wc.*"
        rdx_25 = list(parse_lammps_dumps(file_pattern=rdx_25_pattern))
        time_steps_25 = [d.timestep for d in rdx_25]
        assert_array_equal(time_steps_25, np.arange(0, 101, 25))
        assert rdx_25[-1].data.shape == (21, 5)

    def test_parse_lammps_log(self):
        comb_file = "log.5Oct16.comb.Si.elastic.g++.1.gz"
        comb = parse_lammps_log(filename=f"{TEST_DIR}/{comb_file}")
        assert len(comb) == 6
        # first comb run
        comb0 = comb[0]
        assert list(comb0.columns) == ["Step", "Temp", "TotEng", "PotEng", "E_vdwl", "E_coul"]
        assert len(comb0) == 6
        comb0_data = [
            [0, 1, -4.6295947, -4.6297237, -4.6297237, 0],
            [5, 1, -4.6295965, -4.6297255, -4.6297255, 0],
        ]
        assert_allclose(comb0.iloc[[0, -1]], comb0_data)
        # final comb run
        comb_1 = comb[-1]
        assert list(comb_1.columns) == [
            "Step",
            "Lx",
            "Ly",
            "Lz",
            "Xy",
            "Xz",
            "Yz",
            "c_fxy[1]",
            "c_fxy[2]",
            "c_fxy[3]",
            "c_fxy[4]",
            "c_fxy[5]",
            "c_fxy[6]",
        ]
        assert len(comb_1) == 11
        comb_1_data = [[36, 5.1293854e-06], [46, 2192.8256]]
        assert_allclose(comb_1.iloc[[0, -1], [0, -3]], comb_1_data)

        ehex_file = "log.13Oct16.ehex.g++.8.gz"
        ehex = parse_lammps_log(filename=f"{TEST_DIR}/{ehex_file}")
        assert len(ehex) == 3
        ehex0, ehex1, ehex2 = ehex
        # ehex run #1
        assert list(ehex0.columns) == ["Step", "Temp", "E_pair", "E_mol", "TotEng", "Press"]
        assert len(ehex0) == 11
        ehex0_data = [
            [0, 1.35, -4.1241917, 0, -2.0994448, -3.1961612],
            [1000, 1.3732017, -3.7100044, 0, -1.6504594, 0.83982701],
        ]
        assert_allclose(ehex0.iloc[[0, -1]], ehex0_data)
        # ehex run #2
        assert list(ehex1.columns) == ["Step", "Temp", "c_Thot", "c_Tcold"]
        assert len(ehex1) == 11
        ehex1_data = [
            [1000, 1.35, 1.431295, 1.2955644],
            [11000, 1.3794051, 1.692299, 1.0515688],
        ]
        assert_allclose(ehex1.iloc[[0, -1]], ehex1_data)
        # ehex run #3
        assert list(ehex2.columns) == ["Step", "Temp", "c_Thot", "c_Tcold", "v_tdiff", "f_ave"]
        assert len(ehex2) == 21
        ehex2_data = [
            [11000, 1.3794051, 1.6903393, 1.0515688, 0, 0],
            [31000, 1.3822489, 1.8220413, 1.0322271, -0.7550338, -0.76999077],
        ]
        assert_allclose(ehex2.iloc[[0, -1]], ehex2_data)

        peptide_file = "log.5Oct16.peptide.g++.1.gz"
        peptide = parse_lammps_log(filename=f"{TEST_DIR}/{peptide_file}")
        peptide0 = peptide[0]
        assert list(peptide0.columns) == [
            "Step",
            "TotEng",
            "KinEng",
            "Temp",
            "PotEng",
            "E_bond",
            "E_angle",
            "E_dihed",
            "E_impro",
            "E_vdwl",
            "E_coul",
            "E_long",
            "Press",
        ]

        assert len(peptide0) == 7
        peptide0_select = peptide0.loc[[0, 6], ["Step", "TotEng", "Press"]]
        peptide0_data = [[0, -5237.4580, -837.0112], [300, -5251.3637, -471.5505]]
        assert_allclose(peptide0_select, peptide0_data)
