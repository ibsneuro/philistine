#! /usr/bin/env python
#
# Copyright (C) 2018 Phillip Alday <phillip.alday@mpi.nl>

from __future__ import print_function, division

import mne
import numpy as np
import pandas as pd

from ..import __version__

# TODO: include boundaries in MNE annotation as segment markers in write_raw_brainvision
# TODO: expose support for different numeric formats
# TODO: support export to vectorized data
# TODO: allow arbitrary names for vmrk and eeg
# TODO: epochs exporter using segment markers
# TODO: epochs importer using segment markers (is there another epochs format)
# TODO: make helper dicts private
# binary_int_16, ascii as future formats?


supported_formats = {'binary_float32' : 'IEEE_FLOAT_32',
                     'binary_int16'   : 'INT_16'}

supported_orients = set(['multiplexed'])

def write_raw_brainvision(raw, vhdr_fname, events=True):
    """Write raw data to BrainVision format.

    Parameters
    ----------
    raw : instance of Raw
        The raw data to do these estimations on.
    vhdr_fname : str
        Path to the EEG header file.

    events : boolean or ndarray
        If ndarry, events to write in marker file. Otherwise, boolean indicator
        to extract and write events from raw.

    Notes
    -----
    The BrainVision format supports by-channel filter and measurement information and moreover distinguishes between hardware and software filters. MNE does neither.
    Currently, filter information is not exported.

    Moreover BrainVision also allows for more complex trigger codes than MNE's simple
    integers, e.g. distinguishing on supported hardware between stimulus codes (prefixed by
    an S) and responses codes (prefixed by an R). MNE's numeric events are all treated as
    'stimulus markers' and prefixed by an S on output.

    In other words, a round trip import-export is a lossy operation in terms of metadata.
    The actual EEG recording should be losslessly preserved within the realm of floating
    point precision.
    """

    vmrk_fname = vhdr_fname[:-4] + 'vmrk'
    eeg_fname = vhdr_fname[:-4] + 'eeg'

    if isinstance(events, np.ndarray):
        pass
    elif events == False:
        events = np.ndarray([0,3])
    elif events == True:
        events = mne.find_events(raw,verbose=False)
    else:
        raise ValueError('events must be boolean or 3 x n_events ndarray.')

    # eliminate the stim channel
    raw = raw.copy().pick_types(eeg=True, eog=True, meg=True, misc=True, stim=False)

    _write_vmrk_file(vmrk_fname, eeg_fname, events)
    _write_vhdr_file(vhdr_fname, vmrk_fname, eeg_fname, raw)
    _write_bveeg_file(eeg_fname, raw)


def _write_vmrk_file(vmrk_fname, eeg_fname, events):
    """ Write BrainvVision marker file)
    """

    with open(vmrk_fname, 'w', encoding='utf-8') as fout:
        print(r'Brain Vision Data Exchange Marker File, Version 1.0', file=fout)
        print(r';Exported from MNE-Python using philistine {}'.format(__version__), file=fout)
        print(r'', file=fout)
        print(r'[Common Infos]', file=fout)
        print(r'DataFile={}'.format(eeg_fname), file=fout)
        print(r'', file=fout)
        print(r'[Marker Infos]', file=fout)
        print(r'; Each entry: Mk<Marker number>=<Type>,<Description>,<Position in data points>,', file=fout)
        print(r'; <Size in data points>, <Channel number (0 = marker is related to all channels)>', file=fout)
        print(r'; Fields are delimited by commas, some fields might be omitted (empty).', file=fout)
        print(r'; Commas in type or description text are coded as "\1".', file=fout)
        print(r'Mk1=New Segment,,1,1,0,0', file=fout)

        twidth = int(np.ceil(np.log10(np.max(events[:,2]))))
        tformat = 'S{:>' + str(twidth) + '}'

        for i, r in enumerate(range(events.shape[0]), start=2):
            print(r'Mk{}=Stimulus,{},{},1,0'.format(i,
                                                   tformat.format(events[r,2]),
                                                   events[r, 0]), file=fout)

def _write_vhdr_file(vhdr_fname, vmrk_fname, eeg_fname, raw,
                     orientation='multiplexed', format='binary_float32'):
    """ Write BrainvVision marker file)
    """

    if orientation.lower() not in supported_orients:
        raise ValueError('Orientation {} not supported.'.format(orientation) +
                         'Currently only these orientations are supported: {}'.format(
                ', '.join(supported_formats)))

    if format.lower() not in supported_formats:
        raise ValueError('Data format {} not supported.'.format(format) +
            'Currently only these formats are supported: {}'.format(
                ', '.join(supported_formats)))

    with open(vhdr_fname, 'w', encoding='utf-8') as fout:
        print(r'Brain Vision Data Exchange Header File Version 1.0', file=fout)
        print(r';Exported from MNE-Python using philistine', file=fout)
        print(r'', file=fout)
        print(r'[Common Infos]', file=fout)
        print(r'DataFile={}'.format(eeg_fname), file=fout)
        print(r'MarkerFile={}'.format(vmrk_fname), file=fout)

        if 'binary' in format.lower():
            print(r'DataFormat=BINARY', file=fout)

        if 'multiplexed' == orientation.lower():
            print(r'Data orientation: MULTIPLEXED=ch1,pt1, ch2,pt1 ...', file=fout)
            print(r'DataOrientation=MULTIPLEXED', file=fout)

        print(r'NumberOfChannels={}'.format(len(raw.ch_names)), file=fout)
        print(r'; Sampling interval in microseconds', file=fout)
        print(r'SamplingInterval={}'.format(int(1e6/raw.info['sfreq'])), file=fout)
        print(r'', file=fout)


        if 'binary' in format.lower():
            print(r'[Binary Infos]', file=fout)
            print(r'BinaryFormat={}'.format(supported_formats[format]), file=fout)
            print(r'', file=fout)


        print(r'[Channel Infos]', file=fout)
        print(r'; Each entry: Ch<Channel number>=<Name>,<Reference channel name>,', file=fout)
        print(r'; <Resolution in microvolts>,<Future extensions..', file=fout)
        print(r'; Fields are delimited by commas, some fields might be omitted (empty).', file=fout)
        print(r'; Commas in channel names are coded as "\1".', file=fout)
        for i, ch in enumerate(raw.ch_names, start=1):
            # not sure 0.1 µV is a sensible default resolution or if there is a good
            # way to determine this based on the values in the array, but this is the
            # resolution in the BV files this is being tested on
            print(r'Ch{}={},,0.1'.format(i,ch), file=fout)

        print(r'', file=fout)
        print(r'[Comment]', file=fout)
        print(r'', file=fout)


def _write_bveeg_file(eeg_fname, raw,
                      orientation='multiplexed', format='binary_float32'):
    """ Write BrainvVision marker file)
    """

    if orientation.lower() not in supported_orients:
        raise ValueError('Orientation {} not supported.'.format(orientation) +
                         'Currently only these orientations are supported: {}'.format(
                ', '.join(supported_formats)))

    if format.lower() not in supported_formats:
        raise ValueError('Data format {} not supported.'.format(format) +
            'Currently only these formats are supported: {}'.format(
                ', '.join(supported_formats)))


    if format.lower()[:len('binary')] == 'binary':
        dtype = np.dtype(format.lower()[len('binary')+1:])
    else:
        raise ValueError('Cannot map data format {} to NumPy dtype'.format(format))

    # ndarry.tofile uses column-major order
    # the multiplicative factor here is dependent on resolution
    # for 0.1 µV, this works out to 1e7
    # multiplexed: channel changes fast and channel is first axis -> C order
    with open(eeg_fname,'wb') as fout:
        # skip the stim channel and scale
        data = raw._data * 1e7
        fout.write(data.astype(dtype=dtype).ravel(order='F').tobytes())

def _anonymize_bv(vmrk_fname):
    ''' anonymize brain vision marker files by stripping out time stamps '''
    pass

def _rename_bv(vhdr_fname):
    ''' rename a brainvision file, including updating internal links'''
    pass

def _extract_bv_segments(vmrk_fname):
    ''' Extract segments from BrainVision VMRK file)
    '''
    pass