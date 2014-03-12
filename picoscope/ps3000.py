# This is the instrument-specific file for the PS3000 series of instruments.
#
# pico-python is Copyright (c) 2013-2014 By:
# Colin O'Flynn <coflynn@newae.com>
# Mark Harfouche <mark.harfouche@gmail.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
This is the low level driver file for a specific Picoscope.

By this, I mean if parameters want to get passed as strings, they should be
handled by PSBase
All functions here should take things as close to integers as possible, the
only exception here is for array parameters. Array parameters should be passed
in a pythonic way through numpy since the PSBase class should not be aware of
the specifics behind how the clib is called.

The functions should not have any default values as these should be handled
by PSBase.
"""

from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import math

# to load the proper dll
import platform

# Do not import or use ill definied data types
# such as short int or long
# use the values specified in the h file
# float is always defined as 32 bits
# double is defined as 64 bits
from ctypes import byref, POINTER, create_string_buffer, c_float, \
    c_int16, c_int32, c_uint32, c_void_p
from ctypes import c_int32 as c_enum

from picoscope.picobase import _PicoscopeBase


class PS3000(_PicoscopeBase):
    """The following are low-level functions for the PS3000"""

    LIBNAME = "ps3000"

    NUM_CHANNELS = 4
    CHANNELS     =  {"A": 0, "B": 1, "C": 2, "D": 3,
                     "External": 4, "MaxChannels": 4, "TriggerAux": 5}

    ADC_RESOLUTIONS = {"8":0, "12":1, "14":2, "15":3, "16":4};

    CHANNEL_RANGE = [{"rangeV":10E-3, "apivalue":0, "rangeStr":"10 mV"},
                     {"rangeV":20E-3, "apivalue":1, "rangeStr":"20 mV"},
                     {"rangeV":50E-3, "apivalue":2, "rangeStr":"50 mV"},
                     {"rangeV":100E-3, "apivalue":3, "rangeStr":"100 mV"},
                     {"rangeV":200E-3, "apivalue":4, "rangeStr":"200 mV"},
                     {"rangeV":500E-3, "apivalue":5, "rangeStr":"500 mV"},
                     {"rangeV":1.0, "apivalue":6, "rangeStr":"1 V"},
                     {"rangeV":2.0, "apivalue":7, "rangeStr":"2 V"},
                     {"rangeV":5.0, "apivalue":8, "rangeStr":"5 V"},
                     {"rangeV":10.0, "apivalue":9, "rangeStr":"10 V"},
                     {"rangeV":20.0, "apivalue":10, "rangeStr":"20 V"},
                     {"rangeV":50.0, "apivalue":11, "rangeStr":"50 V"},
                     ]

    CHANNEL_COUPLINGS = {"DC":1, "AC":0}

    #has_sig_gen = True
    WAVE_TYPES = {"Sine": 0, "Square": 1, "Triangle": 2,
                  "RampUp": 3, "RampDown": 4,
                  "Sinc": 5, "Gaussian": 6, "HalfSine": 7, "DCVoltage": 8,
                  "WhiteNoise": 9}

    SIGGEN_TRIGGER_TYPES = {"Rising": 0, "Falling": 1,
                            "GateHigh": 2, "GateLow": 3}
    SIGGEN_TRIGGER_SOURCES = {"None": 0, "ScopeTrig": 1, "AuxIn": 2,
                              "ExtIn": 3, "SoftTrig": 4, "TriggerRaw": 5}

    # This is actually different depending on the AB/CD models
    # I wonder how we could detect the difference between the oscilloscopes
    # I believe we can obtain this information from the setInfo function
    # by readign the hardware version
    # for the PS6403B version, the hardware version is "1 1",
    # an other possibility is that the PS6403B shows up as 6403 when using
    # VARIANT_INFO and others show up as PS6403X where X = A,C or D

    AWGPhaseAccumulatorSize = 32
    AWGBufferAddressWidth   = 14
    AWGMaxSamples           = 2 ** AWGBufferAddressWidth

    AWGDACInterval          = 5E-9  # in seconds
    AWGDACFrequency         = 1 / AWGDACInterval

    # Note this is NOT what is written in the Programming guide as of version
    # 10_5_0_28
    # This issue was acknowledged in this thread
    # http://www.picotech.com/support/topic13217.html
    AWGMaxVal               = 0x0FFF
    AWGMinVal               = 0x0000

    AWG_INDEX_MODES = {"Single": 0, "Dual": 1, "Quad": 2}

    MAX_VALUE_8BIT = 32512
    MIN_VALUE_8BIT = -32512
    MAX_VALUE_OTHER = 32767
    MIN_VALUE_OTHER = -32767

    EXT_RANGE_VOLTS = 5

    def __init__(self, serialNumber=None, connect=True):
        """Load DLL etc"""
        if platform.system() == 'Linux':
            from ctypes import cdll
            self.lib = cdll.LoadLibrary("lib" + self.LIBNAME + ".so")
        else:
            from ctypes import windll
            self.lib = windll.LoadLibrary(self.LIBNAME + ".dll")

        self.resolution = self.ADC_RESOLUTIONS["8"]

        super(PS3000, self).__init__(serialNumber, connect)

    def _lowLevelOpenUnit(self, sn):
        c_handle = c_int16()
        if sn is not None:
            serialNullTermStr = create_string_buffer(sn)
        else:
            serialNullTermStr = None
        # Passing None is the same as passing NULL
        m = self.lib.ps3000_open_unit(byref(c_handle), serialNullTermStr, self.resolution)
        self.checkResult(m)
        self.handle = c_handle.value

    def _lowLevelCloseUnit(self):
        m = self.lib.ps3000_close_unit(c_int16(self.handle))
        self.checkResult(m)

    def _lowLevelSetChannel(self, chNum, enabled, coupling, VRange, VOffset,
                            BWLimited):
        m = self.lib.ps3000_set_channel(c_int16(self.handle), c_enum(chNum),
                                      c_int16(enabled), c_enum(coupling),
                                      c_enum(VRange), c_float(VOffset))
        self.checkResult(m)

    def _lowLevelStop(self):
        m = self.lib.ps3000_stop(c_int16(self.handle))
        self.checkResult(m)

    def _lowLevelGetUnitInfo(self, info):
        s = create_string_buffer(256)
        requiredSize = c_int16(0)

        m = self.lib.ps3000_get_unit_info(c_int16(self.handle), byref(s),
                                       c_int16(len(s)), byref(requiredSize),
                                       c_enum(info))
        self.checkResult(m)
        if requiredSize.value > len(s):
            s = create_string_buffer(requiredSize.value + 1)
            m = self.lib.ps3000_get_unit_info(c_int16(self.handle), byref(s),
                                           c_int16(len(s)),
                                           byref(requiredSize), c_enum(info))
            self.checkResult(m)

        # should this bee ascii instead?
        # I think they are equivalent...
        return s.value.decode('utf-8')

    def _lowLevelFlashLed(self, times):
        m = self.lib.ps3000_flash_led(c_int16(self.handle), c_int16(times))
        self.checkResult(m)

    def _lowLevelSetSimpleTrigger(self, enabled, trigsrc, threshold_adc,
                                  direction, timeout_ms, auto):
        m = self.lib.ps3000_set_simple_trigger(
            c_int16(self.handle), c_int16(enabled),
            c_enum(trigsrc), c_int16(threshold_adc),
            c_enum(direction), c_uint32(timeout_ms), c_int16(auto))
        self.checkResult(m)

    def _lowLevelRunBlock(self, numPreTrigSamples, numPostTrigSamples,
                          timebase, oversample, segmentIndex):
        #NOT: Oversample is NOT used!
        timeIndisposedMs = c_int32()
        m = self.lib.ps3000_run_block(
            c_int16(self.handle), c_uint32(numPreTrigSamples),
            c_uint32(numPostTrigSamples), c_uint32(timebase),
            byref(timeIndisposedMs), c_uint32(segmentIndex),
            c_void_p(), c_void_p())
        self.checkResult(m)
        return timeIndisposedMs.value

    def _lowLevelIsReady(self):
        ready = c_int16()
        m = self.lib.ps3000_is_ready(c_int16(self.handle), byref(ready))
        self.checkResult(m)
        if ready.value:
            return True
        else:
            return False

    def _lowLevelGetTimebase(self, tb, noSamples, oversample, segmentIndex):
        """ returns (timeIntervalSeconds, maxSamples) """
        maxSamples = c_int32()
        sampleRate = c_float()

        m = self.lib.ps3000_get_timebase(c_int16(self.handle), c_uint32(tb),
                                        c_uint32(noSamples), byref(sampleRate),
                                       byref(maxSamples), c_uint32(segmentIndex))
        self.checkResult(m)

        return (sampleRate.value / 1.0E9, maxSamples.value)

    def getTimeBaseNum(self, sampleTimeS):
        """Convert sample time in S to something to pass to API Call"""

        if self.resolution == self.ADC_RESOLUTIONS["8"]:
            maxSampleTime = (((2 ** 32 - 1) - 2) / 125000000)
            if sampleTimeS < 8.0E-9:
                st = math.floor(math.log(sampleTimeS * 1E9, 2))
                st = max(st, 0)
            else:
                if sampleTimeS > maxSampleTime:
                    sampleTimeS = maxSampleTime
                st = math.floor((sampleTimeS * 125000000) + 2)

        elif self.resolution == self.ADC_RESOLUTIONS["12"]:
            maxSampleTime = (((2 ** 32 - 1) - 3) / 62500000)
            if sampleTimeS < 16.0E-9:
                st = math.floor(math.log(sampleTimeS * 5E8, 2)) + 1
                st = max(st, 1)
            else:
                if sampleTimeS > maxSampleTime:
                    sampleTimeS = maxSampleTime
                st = math.floor((sampleTimeS * 62500000) + 3)

        elif (self.resolution == self.ADC_RESOLUTIONS["14"]) or (self.resolution == self.ADC_RESOLUTIONS["15"]):
            maxSampleTime = (((2 ** 32 - 1) - 2) / 125000000)
            if sampleTimeS > maxSampleTime:
                sampleTimeS = maxSampleTime
            st = math.floor((sampleTimeS * 125000000) + 2)
            st = max(st, 3)

        elif self.resolution == self.ADC_RESOLUTIONS["16"]:
            maxSampleTime = (((2 ** 32 - 1) - 3) / 62500000)
            if sampleTimeS > maxSampleTime:
                sampleTimeS = maxSampleTime
            st = math.floor((sampleTimeS * 62500000) + 3)
            st = max(st, 3)

        else:
            raise ValueError("Invalid Resolution for Device?")

        # is this cast needed?
        st = int(st)
        return st

    def getTimestepFromTimebase(self, timebase):

        if self.resolution == self.ADC_RESOLUTIONS["8"]:
            if timebase < 3:
                dt = 2. ** timebase / 1.0E9
            else:
                dt = (timebase - 2.0) / 125000000.
        elif self.resolution == self.ADC_RESOLUTIONS["12"]:
            if timebase < 4:
                dt = 2. ** (timebase-1) / 5.0E8
            else:
                dt = (timebase - 3.0) / 62500000.
        elif (self.resolution == self.ADC_RESOLUTIONS["14"]) or (self.resolution == self.ADC_RESOLUTIONS["15"]):
            dt = (timebase - 2.0) / 125000000.
        elif self.resolution == self.ADC_RESOLUTIONS["16"]:
            dt = (timebase - 3.0) / 62500000.
        return dt

    def _lowLevelSetAWGSimpleDeltaPhase(self, waveform, deltaPhase,
                                        offsetVoltage, pkToPk, indexMode,
                                        shots, triggerType, triggerSource):
        """ waveform should be an array of shorts """

        waveformPtr = waveform.ctypes.data_as(POINTER(c_int16))

        m = self.lib.ps3000_set_siggen(
            c_int16(self.handle),
            c_uint32(int(offsetVoltage * 1E6)),  # offset voltage in microvolts
            c_uint32(int(pkToPk * 1E6)),         # pkToPk in microvolts
            c_uint32(int(deltaPhase)),           # startDeltaPhase
            c_uint32(int(deltaPhase)),           # stopDeltaPhase
            c_uint32(0),                         # deltaPhaseIncrement
            c_uint32(0),                         # dwellCount
            waveformPtr,                         # arbitraryWaveform
            c_int32(len(waveform)),              # arbitraryWaveformSize
            c_enum(0),                           # sweepType for deltaPhase
            c_enum(0),            # operation (adding random noise and whatnot)
            c_enum(indexMode),                   # single, dual, quad
            c_uint32(shots),
            c_uint32(0),                         # sweeps
            c_uint32(triggerType),
            c_uint32(triggerSource),
            c_int16(0))                          # extInThreshold
        self.checkResult(m)

    # def _lowLevelSetDataBuffer(self, channel, data, downSampleMode, segmentIndex):
    #     """
    #     data should be a numpy array

    #     Be sure to call _lowLevelClearDataBuffer
    #     when you are done with the data array
    #     or else subsequent calls to GetValue will still use the same array.
    #     """
    #     dataPtr = data.ctypes.data_as(POINTER(c_int16))
    #     numSamples = len(data)

    #     m = self.lib.ps3000SetDataBuffer(c_int16(self.handle), c_enum(channel),
    #                                      dataPtr, c_int32(numSamples),
    #                                      c_uint32(segmentIndex),
    #                                      c_enum(downSampleMode))
    #     self.checkResult(m)

    # def _lowLevelClearDataBuffer(self, channel, segmentIndex):
    #     """ data should be a numpy array"""
    #     m = self.lib.ps3000SetDataBuffer(c_int16(self.handle), c_enum(channel),
    #                                      c_void_p(), c_uint32(0), c_uint32(segmentIndex),
    #                                       c_enum(0))
    #     self.checkResult(m)

    def _lowLevelGetValues(self, numSamples, startIndex, downSampleRatio,
                           downSampleMode, segmentIndex):
        numSamplesReturned = c_uint32()
        numSamplesReturned.value = numSamples
        overflow = c_int16()
        m = self.lib.ps3000_get_values(
            c_int16(self.handle), c_uint32(startIndex),
            byref(numSamplesReturned), c_uint32(downSampleRatio),
            c_enum(downSampleMode), c_uint32(segmentIndex),
            byref(overflow))
        self.checkResult(m)
        return (numSamplesReturned.value, overflow.value)

    # def _lowLevelSetSigGenBuiltInSimple(self, offsetVoltage, pkToPk, waveType,
    #                                     frequency, shots, triggerType,
    #                                     triggerSource):
    #     # TODO, I just noticed that V2 exists
    #     # Maybe change to V2 in the future
    #     m = self.lib.ps3000SetSigGenBuiltIn(
    #         c_int16(self.handle),
    #         c_int32(int(offsetVoltage * 1000000)),
    #         c_int32(int(pkToPk        * 1000000)),
    #         c_int16(waveType),
    #         c_float(frequency), c_float(frequency),
    #         c_float(0), c_float(0), c_enum(0), c_enum(0),
    #         c_uint32(shots), c_uint32(0),
    #         c_enum(triggerType), c_enum(triggerSource),
    #         c_int16(0))
    #     self.checkResult(m)

    def _lowLevelSetDeviceResolution(self, resolution):
        self.resolution = resolution
        m = self.lib.ps3000SetDeviceResolution(
            c_int16(self.handle),
            c_enum(resolution))
        self.checkResult(m)
