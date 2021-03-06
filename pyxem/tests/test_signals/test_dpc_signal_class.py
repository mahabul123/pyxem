# -*- coding: utf-8 -*-
# Copyright 2016-2020 The pyXem developers
#
# This file is part of pyXem.
#
# pyXem is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyXem is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyXem.  If not, see <http://www.gnu.org/licenses/>.

import pytest
from pytest import approx
import numpy as np
from numpy.testing import assert_almost_equal, assert_allclose
from pyxem.signals.differential_phase_contrast import (
    DPCBaseSignal,
    DPCSignal1D,
    DPCSignal2D,
)
import pyxem.dummy_data.dummy_data as dd
import pyxem.utils.pixelated_stem_tools as pst
from pyxem.utils.dpc_utils import make_bivariate_histogram


class TestDpcBasesignalCreate:
    def test_create(self):
        data = np.ones(shape=(2))
        DPCBaseSignal(data)


class TestDpcSignal1dCreate:
    def test_create(self):
        data = np.ones(shape=(2, 10))
        DPCSignal1D(data)


class TestDpcSignal2dCreate:
    def test_create(self):
        data = np.ones(shape=(2, 10, 10))
        DPCSignal2D(data)
        with pytest.raises(ValueError):
            DPCSignal2D(np.zeros(10))


class TestDpcSignal2dCorrectRamp:
    def test_correct_ramp_flat(self):
        data0 = np.ones(shape=(2, 64, 64))
        s0 = DPCSignal2D(data0)
        s0_corr = s0.correct_ramp(corner_size=0.05)
        assert (s0.data == data0).all()
        assert_allclose(s0_corr.data, np.zeros_like(data0), atol=1e-8)

        s0.correct_ramp(corner_size=0.05, out=s0)
        assert_allclose(s0.data, np.zeros_like(data0), atol=1e-8)

    def test_correct_ramp_x_y(self):
        array_x, array_y = np.meshgrid(range(64), range(64))
        data_x = np.swapaxes(np.dstack((array_x, array_x)), 0, 2).astype("float64")
        data_y = np.swapaxes(np.dstack((array_y, array_y)), 0, 2).astype("float64")
        s_x = DPCSignal2D(data_x)
        s_y = DPCSignal2D(data_y)
        s_x_corr = s_x.correct_ramp(corner_size=0.05)
        s_y_corr = s_y.correct_ramp(corner_size=0.05)
        assert_allclose(s_x_corr.data, np.zeros_like(data_x), atol=1e-6)
        assert_allclose(s_y_corr.data, np.zeros_like(data_y), atol=1e-6)

        data_xy = np.swapaxes(np.dstack((array_x, array_y)), 0, 2).astype("float64")
        data_yx = np.swapaxes(np.dstack((array_y, array_x)), 0, 2).astype("float64")
        s_xy = DPCSignal2D(data_xy)
        s_yx = DPCSignal2D(data_yx)
        s_xy_corr = s_xy.correct_ramp(corner_size=0.05)
        s_yx_corr = s_yx.correct_ramp(corner_size=0.05)
        assert_allclose(s_xy_corr.data, np.zeros_like(data_xy), atol=1e-6)
        assert_allclose(s_yx_corr.data, np.zeros_like(data_yx), atol=1e-6)

        data_tilt = np.swapaxes(
            np.dstack((array_x + array_y, np.fliplr(array_x) + array_y)), 0, 2
        ).astype("float64")
        s_tilt = DPCSignal2D(data_tilt)
        s_tilt_corr = s_tilt.correct_ramp()
        assert_allclose(s_tilt_corr.data, np.zeros_like(data_tilt), atol=1e-6)
        s_tilt.correct_ramp(out=s_tilt)
        assert_allclose(s_tilt.data, np.zeros_like(data_tilt), atol=1e-6)

    def test_correct_ramp_random(self):
        array_x, array_y = np.meshgrid(range(64), range(64))
        data_tilt = np.swapaxes(
            np.dstack((array_x + array_y, np.fliplr(array_x) + array_y)), 0, 2
        ).astype("float64")
        data_random = data_tilt + np.random.random(size=(2, 64, 64)) * 10
        s_random = DPCSignal2D(data_random)
        s_random_corr = s_random.correct_ramp()
        assert_allclose(s_random_corr.data, np.zeros_like(data_random), atol=10)
        s_random.correct_ramp(out=s_random)
        assert_allclose(s_random.data, np.zeros_like(data_random), atol=10)

    def test_correct_ramp_one_large_value(self):
        array_x, array_y = np.meshgrid(range(64), range(64))
        data = np.swapaxes(
            np.dstack((array_x + array_y, np.fliplr(array_x) + array_y)), 0, 2
        ).astype("float64")
        data[:, 20:30, 30:40] += 1000
        s = DPCSignal2D(data)
        s_corr = s.correct_ramp()
        s_corr.data[:, 20:30, 30:40] -= 1000
        assert_allclose(s_corr.data, np.zeros_like(data), atol=1e-8)

    def test_correct_ramp_only_offset(self):
        data = np.ones((2, 50, 50))
        data[1, :, :] = -3
        s = DPCSignal2D(np.zeros((2, 50, 50)))
        s_corr1 = s.correct_ramp(only_offset=True)
        assert_allclose(s_corr1.data, np.zeros_like(data), atol=1e-8)

        data_ramp = np.mgrid[-5:5:50j, -5:5:50j]
        s.data += data_ramp
        s_corr2 = s.correct_ramp(only_offset=True)
        assert_allclose(s_corr2.data, data_ramp, atol=1e-8)

    def test_large_values_not_in_corners(self):
        s = DPCSignal2D(np.zeros((2, 100, 100)))
        s.inav[0].data[:5, :5], s.inav[0].data[:5, -5:] = 10, 10
        s.inav[0].data[-5:, :5], s.inav[0].data[-5:, -5:] = 10, 10
        s.inav[1].data[:5, :5], s.inav[1].data[:5, -5:] = 30, 30
        s.inav[1].data[-5:, :5], s.inav[1].data[-5:, -5:] = 30, 30

        cross_array = np.zeros((100, 100))
        cross_array[30:70, :], cross_array[:, 30:70] = 1000, 1000
        s.data = s.data + cross_array

        s1 = s.correct_ramp(corner_size=0.05)
        s1.data = s1.data - cross_array

        assert_allclose(s1.inav[0].data[5:95, :], np.ones((90, 100)) * -10)
        assert_allclose(s1.inav[0].data[:, 5:95], np.ones((100, 90)) * -10)
        assert_allclose(s1.inav[0].data[5:95, :], np.ones((90, 100)) * -10)
        assert_allclose(s1.inav[1].data[5:95, :], np.ones((90, 100)) * -30)
        assert_allclose(s1.inav[1].data[:, 5:95], np.ones((100, 90)) * -30)
        assert_allclose(s1.inav[1].data[5:95, :], np.ones((90, 100)) * -30)
        assert_allclose(s1.isig[:5, :5].data, np.zeros((2, 5, 5)), atol=1e-7)
        assert_allclose(s1.isig[-5:, :5].data, np.zeros((2, 5, 5)), atol=1e-7)
        assert_allclose(s1.isig[:5, -5:].data, np.zeros((2, 5, 5)), atol=1e-7)
        assert_allclose(s1.isig[-5:, -5:].data, np.zeros((2, 5, 5)), atol=1e-7)

    def test_random_negative_values(self):
        s = DPCSignal2D(np.zeros((2, 1000, 1000)))
        s.data[:, :300, :300] = np.random.random((300, 300)) * 10 - 5
        s.data[:, :300, -300:] = np.random.random((300, 300)) * 10 - 5
        s.data[:, -300:, :300] = np.random.random((300, 300)) * 10 - 5
        s.data[:, -300:, -300:] = np.random.random((300, 300)) * 10 - 5

        s_corr = s.correct_ramp(corner_size=0.3)
        assert approx(s_corr.data[:, 300:-300, :].mean(), abs=0.1) == 0.0
        assert approx(s_corr.data[:, :, 300:-300].mean(), abs=0.1) == 0.0

    def test_cropped_dpcsignal(self):
        s = DPCSignal2D(np.random.random((2, 200, 200)))
        s_crop = s.isig[50:150, 50:150]
        s_crop.correct_ramp()


class TestGetDpcSignal:
    def test_get_color_signal(self):
        array_x, array_y = np.meshgrid(range(64), range(64))
        data_tilt = np.swapaxes(
            np.dstack((array_x + array_y, np.fliplr(array_x) + array_y)), 0, 2
        ).astype("float64")
        data_random = data_tilt + np.random.random(size=(2, 64, 64)) * 10
        s_random = DPCSignal2D(data_random)
        s_random.get_color_signal()
        s_random.get_color_signal(rotation=45)

    def test_get_color_signal_zeros(self):
        s = DPCSignal2D(np.zeros((2, 100, 100)))
        s_color = s.get_color_signal()
        assert (s_color.data["R"] == 0).all()
        assert (s_color.data["G"] == 0).all()
        assert (s_color.data["B"] == 0).all()

    def test_get_magnitude_signal_zeros(self):
        s = DPCSignal2D(np.zeros((2, 100, 100)))
        s_magnitude = s.get_magnitude_signal()
        assert (s_magnitude.data == 0).all()

    def test_get_phase_signal(self):
        s = DPCSignal2D(np.zeros((2, 100, 100)))
        s.get_phase_signal()
        s.get_phase_signal(rotation=45)

    def test_get_color_image_with_indicator(self):
        s = DPCSignal2D(np.random.random(size=(2, 100, 100)))
        s.get_color_image_with_indicator()
        s.get_color_image_with_indicator(
            phase_rotation=45,
            indicator_rotation=10,
            autolim=True,
            autolim_sigma=1,
            scalebar_size=10,
        )
        s.get_color_image_with_indicator(only_phase=True)


class TestDpcSignal2dBivariateHistogram:
    def test_get_bivariate_histogram(self):
        array_x, array_y = np.meshgrid(range(64), range(64))
        data_tilt = np.swapaxes(
            np.dstack((array_x + array_y, np.fliplr(array_x) + array_y)), 0, 2
        ).astype("float64")
        data_random = data_tilt + np.random.random(size=(2, 64, 64)) * 10
        s_random = DPCSignal2D(data_random)
        s_random.get_bivariate_histogram()

    def test_make_bivariate_histogram(self):
        x, y = np.ones((100, 100)), np.ones((100, 100))
        make_bivariate_histogram(
            x_position=x,
            y_position=y,
            histogram_range=None,
            masked=None,
            bins=200,
            spatial_std=3,
        )


class TestRotateData:
    def test_clockwise(self):
        s = dd.get_simple_dpc_signal()
        s_rot = s.rotate_data(1)
        assert not (s_rot.data[0, 0, 0:10] == 0).all()
        assert (s_rot.data[0, 0, -10:] == 0).all()
        assert not (s_rot.data[0, -10:, 0] == 0).all()
        assert (s_rot.data[0, 0:10, 0] == 0).all()

    def test_counterclockwise(self):
        s = dd.get_simple_dpc_signal()
        s_rot = s.rotate_data(-1)
        assert (s_rot.data[0, 0, 0:10] == 0).all()
        assert not (s_rot.data[0, 0, -10:] == 0).all()
        assert (s_rot.data[0, -10:, 0] == 0).all()
        assert not (s_rot.data[0, 0:10, 0] == 0).all()


class TestRotateBeamShifts:
    def test_clockwise_90_degrees(self):
        s = DPCSignal2D((np.ones((90, 70)), np.zeros((90, 70))))
        s_rot = s.rotate_beam_shifts(90)
        data_x, data_y = s_rot.inav[0].data, s_rot.inav[1].data
        assert_almost_equal(data_x, np.zeros_like(data_x))
        assert_almost_equal(data_y, np.ones_like(data_y))

    def test_counterclockwise_90_degrees(self):
        s = DPCSignal2D((np.ones((90, 70)), np.zeros((90, 70))))
        s_rot = s.rotate_beam_shifts(-90)
        data_x, data_y = s_rot.inav[0].data, s_rot.inav[1].data
        assert_almost_equal(data_x, np.zeros_like(data_x))
        assert_almost_equal(data_y, -np.ones_like(data_y))

    def test_180_degrees(self):
        s = DPCSignal2D((np.ones((90, 70)), np.zeros((90, 70))))
        s_rot = s.rotate_beam_shifts(180)
        data_x, data_y = s_rot.inav[0].data, s_rot.inav[1].data
        assert_almost_equal(data_x, -np.ones_like(data_x))
        assert_almost_equal(data_y, np.zeros_like(data_y))

    def test_clockwise_45_degrees(self):
        s = DPCSignal2D((np.ones((90, 70)), np.zeros((90, 70))))
        sin_rad = np.sin(np.deg2rad(45))
        s_rot = s.rotate_beam_shifts(45)
        data_x, data_y = s_rot.inav[0].data, s_rot.inav[1].data
        assert_almost_equal(data_x, np.ones_like(data_x) * sin_rad)
        assert_almost_equal(data_y, np.ones_like(data_y) * sin_rad)

    def test_counterclockwise_45_degrees(self):
        s = DPCSignal2D((np.ones((90, 70)), np.zeros((90, 70))))
        sin_rad = np.sin(np.deg2rad(45))
        s_rot = s.rotate_beam_shifts(-45)
        data_x, data_y = s_rot.inav[0].data, s_rot.inav[1].data
        assert_almost_equal(data_x, np.ones_like(data_x) * sin_rad)
        assert_almost_equal(data_y, -np.ones_like(data_y) * sin_rad)


class TestFlipAxis90Degrees:
    def setup_method(self):
        data = np.zeros((2, 100, 50))
        for i in range(10, 90, 20):
            data[0, i : i + 10, 10:40] = 1.1
            data[0, i + 10 : i + 20, 10:40] = -1
        self.s = DPCSignal2D(data)
        self.s_shape = self.s.axes_manager.signal_shape

    def test_flip_once(self):
        s, s_shape = self.s, self.s_shape
        assert_allclose(s.inav[0].data.mean(), 0.024, atol=1e-7)
        assert_allclose(s.inav[1].data.mean(), 0.0, atol=1e-7)

        s_r = s.flip_axis_90_degrees()
        assert_allclose(s_r.inav[0].data.mean(), 0.0, atol=1e-7)
        assert_allclose(s_r.inav[1].data.mean(), 0.024, atol=1e-7)
        assert_allclose(s_r.axes_manager.signal_shape, s_shape[::-1])
        assert_allclose(s_r.axes_manager.navigation_shape, (2,))

    def test_flip_twice(self):
        s, s_shape = self.s, self.s_shape
        s_r = s.flip_axis_90_degrees(2)
        assert_allclose(s_r.inav[0].data.mean(), -0.024, atol=1e-7)
        assert_allclose(s_r.inav[1].data.mean(), 0.0, atol=1e-7)
        assert_allclose(s_r.axes_manager.signal_shape, s_shape)
        assert_allclose(s_r.axes_manager.navigation_shape, (2,))

    def test_flip_thrice(self):
        s, s_shape = self.s, self.s_shape
        s_r = s.flip_axis_90_degrees(3)
        assert_allclose(s_r.inav[0].data.mean(), 0.0, atol=1e-7)
        assert_allclose(s_r.inav[1].data.mean(), -0.024, atol=1e-7)
        assert_allclose(s_r.axes_manager.signal_shape, s_shape[::-1])
        assert_allclose(s_r.axes_manager.navigation_shape, (2,))

    def test_flip_four_times(self):
        s, s_shape = self.s, self.s_shape
        s_r = s.flip_axis_90_degrees(4)
        assert_allclose(s_r.inav[0].data.mean(), 0.024, atol=1e-7)
        assert_allclose(s_r.inav[1].data.mean(), 0.0, atol=1e-7)
        assert_allclose(s_r.axes_manager.signal_shape, s_shape)
        assert_allclose(s_r.axes_manager.navigation_shape, (2,))


class TestGaussianBlur:
    def setup_method(self):
        data = np.zeros((2, 25, 50))
        data[0, 10, 5] = 10
        data[1, 20, 15] = -10
        self.s = DPCSignal2D(data)

    def test_output1(self):
        s = self.s
        s_out = s.gaussian_blur(sigma=1.2)
        assert s.axes_manager.shape == s_out.axes_manager.shape
        assert s.data[0, 10, 5] == 10
        assert s.data[1, 20, 15] == -10
        s.data[0, 10, 5] = 0
        s.data[1, 20, 15] = 0
        assert not s.data.any()

        assert s_out.data[0, 10, 5] < 10
        assert s_out.data[0, 10, 5] > 0
        assert s_out.data[1, 20, 15] > -10
        assert s_out.data[1, 20, 15] < 0
        assert_almost_equal(10, s_out.data[0].sum())
        assert_almost_equal(-10, s_out.data[1].sum())

    def test_output2(self):
        s = self.s
        s_copy = s.deepcopy()
        s.gaussian_blur(output=s, sigma=1.2)
        assert s.axes_manager.shape == s_copy.axes_manager.shape
        assert s.data[0, 10, 5] != 10
        assert s.data[1, 20, 15] != -10
        assert s.data[0, 10, 5] < 10
        assert s.data[0, 10, 5] > 0
        assert s.data[1, 20, 15] > -10
        assert s.data[1, 20, 15] < 0
        assert_almost_equal(10, s.data[0].sum())
        assert_almost_equal(-10, s.data[1].sum())
