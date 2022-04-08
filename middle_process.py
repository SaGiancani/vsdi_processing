import argparse, blk_file, datetime, random
import matplotlib.pyplot as plt
import numpy as np
import os
from scipy import signal
import utils

LABEL_CONDS_PATH = 'metadata/labelConds.txt' 

# Inserting inside the class variables and features useful for one session: we needs an object at this level for
# keeping track of conditions, filenames, selected or not flag for each trial.
class Session:
    def __init__(self, **kwargs):
        """
        Initializes attributes
        Default values for:
        *all_blks = all the .BLK files contained inside path_session/rawdata/. It is a list of strings
        *cond_names = list of conditions' names.  
        *header = a dictionary with the kwargs value. See get_session_header method for details
        *session_blks = all the .BLK, per condition, considered for the processing. It is a subset of all_blks. It is a list of strings
        *motion_indeces = unused
        *roi_signals = all the roi signals of the considered BLKs. It is a numpy array of shape n_session_blk, n_frames, 1
        *trials_name = the .BLKs' filename of each selected trial. It is a list of strings
        *df_fz = deltaF/F0 for each selected trial. It is a numpy array of shape selected_trials, width, height
        *auto_selected = list of integers: 0 for not selected trial, 1 for selected. 
        *conditions = list of integers: the integer corresponds to the number of condition.
        Parameters
        ----------
        filename : str
            The path of the external file, containing the raw image
        """
        self.cond_names = None
        self.header = self.get_session_header(**kwargs)
        self.all_blks = self.get_all_blks()
        self.cond_names = self.get_condition_name()
        self.blank_id = self.get_blank_id()
        
        # If considered conditions are not explicitly indicated, then all the conditions are considered      
        if self.header['conditions_id'] is None:
            self.header['conditions_id'] = self.get_condition_ids()
        else:
            self.header['conditions_id'] = list(set(self.header['conditions_id']+[self.blank_id]))

        self.session_blks = self.get_blks()

        if self.header['mov_switch']:
            self.motion_indeces = None
        
        self.roi_signals = None
        self.trials_name = None 
        self.df_fz = None
        self.auto_selected = None
        self.conditions = None
        self.counter_blank = 0        
        
        if self.header['deblank_switch']:
            # TO NOTICE: deblank_switch add roi_signals, df_fz, auto_selected, conditions, counter_blank and overwrites the session_blks
            self.time_course_blank, self.df_f0_blank = self.get_blank_signal()
            print(f'Time Course blank shape: {np.shape(self.time_course_blank)}')
            print(f'Time Course blank shape: {np.shape(self.df_f0_blank)}')
        else:
            self.time_course_blank, self.df_f0_blank = None, None



    def get_all_blks(self):
        '''
        All the .BLKs filenames, from the considered path_session, are picked.
        '''
        return [f.name for f in os.scandir(self.header['path_session'] + 'rawdata/') if (f.is_file()) and (f.name.endswith(".BLK"))]

    def get_blks(self):
        '''
        The .BLKs filenames corresponding to the choosen id conditions, from the considered path_session, are picked.        
        '''
#        if self.session_blks is None:
        #This condition check is an overkill
        if ((self.header['conditions_id'] is None) or (len(self.header['conditions_id']) == len(self.cond_names))): 
            return self.all_blks
        else:
            return [f for f in self.all_blks \
                if (int(f.split('vsd_C')[1][0:2]) in self.header['conditions_id'])]
        # else:
        #     print('Warning: session_blks was not None')
        #     id_check = list(set([f for f in self.all_blks if (int(f.split('vsd_C')[1][0:2]))]))
        #     if len(id_check) == 1 and self.blank_id in id_check:
        #         b = np.array(self.header['conditions_id']).tolist()
        #         return self.session_blks + [f for f in self.all_blks if (int(f.split('vsd_C')[1][0:2])) in b.remove(self.blank_id)]

    def get_session_header(self, path_session, spatial_bin, temporal_bin, zero_frames, detrend, tolerance, mov_switch, deblank_switch, conditions_id, chunks, strategy):
        header = {}
        header['path_session'] = path_session
        header['spatial_bin'] = spatial_bin
        header['temporal_bin'] = temporal_bin
        header['zero_frames'] = zero_frames
        header['detrend'] = detrend
        header['tolerance'] = tolerance
        header['mov_switch'] = mov_switch
        header['deblank_switch'] = deblank_switch
        header['conditions_id'] = conditions_id
        header['chunks'] = chunks
        header['strategy'] = strategy
        return header

    def get_condition_ids(self):
        '''
        The method returns a list of all the condition's ids, taken from the .BLK names.
        '''
        return list(set([int(i.split('vsd_C')[1][0:2]) for i in self.all_blks]))
        
    def get_condition_name(self):
        '''
        The method returns a list of condition's names: if a labelConds.txt exist inside metadata's folder, 
        than names are simply loaded. Otherwise a list of names with "Condition #" style is built.
        '''
        try:
            with open(self.header['path_session'] + LABEL_CONDS_PATH) as f:
                contents = f.readlines()
            return [i.split('\n')[0] for i in contents]
        except FileNotFoundError:
            print('Check the labelConds.txt presence inside the metadata subfolder')
            cds = self.get_condition_ids()
            return ['Condition ' + str(c) for c in cds]
        except NotADirectoryError:
            print(self.header['path_session'] + LABEL_CONDS_PATH +' path does not exist')
            cds = self.get_condition_ids()
            return ['Condition ' + str(c) for c in cds]

    def get_blank_id(self):
        '''
        The method returns the index of blank condition. It checks between the condition names: if labelConds.txt
        file exists, than the position of "blank" label is picked. Otherwise the position of last condition 
        is picked.
        '''
        try:
            tmp = [idx for idx, s in enumerate(self.cond_names) if 'blank' in s][0]+1
            print('Blank id: ' + str(tmp))
            return tmp
        except IndexError:
            print('No clear blank condition was identified: the last condition has picked')
            tmp = len(self.cond_names)
            print('Blank id: ' + str(tmp))
            return tmp

    def get_session(self):
        if self.counter_blank == 0:
            print('Trials loading starts:')
            roi_signals, delta_f, conditions= signal_extraction(self.header, self.session_blks, self.df_f0_blank, False)
            self.conditions = conditions
            self.df_fz = delta_f # This storing process is heavy. HAS TO BE TESTED AND CAN BE AVOIDED
            self.roi_signals = roi_signals
            #self.motion_indeces = motion_indeces
        else:
            blks = [f for f in self.all_blks \
                if (int(f.split('vsd_C')[1][0:2]) != self.blank_id) and (int(f.split('vsd_C')[1][0:2]) in self.header['conditions_id'])]
            print('Trials loading starts:')
            roi_signals, delta_f, conditions= signal_extraction(self.header, blks, self.df_f0_blank, self.header['deblank_switch'])
            self.session_blks = self.session_blks + blks
            shapes = np.shape(delta_f)
            
            df_f0 = np.zeros((len(self.session_blks), shapes[1], shapes[2], shapes[3]))
            time_course = np.zeros((len(self.session_blks), shapes[1]))
            
            df_f0[0:self.counter_blank, :, :, :] = self.df_fz
            df_f0[self.counter_blank:, :, :, :] = delta_f
            time_course[0:self.counter_blank, :] = self.roi_signals
            time_course[self.counter_blank:, :] = roi_signals

            self.conditions = self.conditions + conditions
            self.df_fz = df_f0
            self.roi_signals = time_course
            #self.motion_indeces = self.motion_indeces + motion_indeces
        return

    def autoselection(self):
        start_time = datetime.datetime.now().replace(microsecond=0)
        strategy = self.header['strategy']
        shapes = np.shape(self.df_fz)
        n_frames = shapes[1]

        if strategy in ['mse', 'mae'] and (n_frames%self.header['chunks']==0):
            self.get_session()
            tmp = overlap_strategy(self.roi_signals, n_chunks=self.header['chunks'], loss = strategy)
        
        elif strategy in ['mse', 'mae'] and not (n_frames%self.header['chunks']==0):
            print('Number of chunks incompatible with number of frames, roi strategy automatically picked')
            strategy = 'roi'

        if strategy in ['roi', 'roi_signals', 'ROI']:
            self.get_session()
            tmp = roi_strategy(self.roi_signals, self.header['tolerance'], self.header['zero_frames'])

        elif strategy in ['statistic', 'statistical', 'quartiles']:
            self.get_session()
            tmp = statistical_strategy(self.roi_signals)

        if self.auto_selected is None:
            self.auto_selected = tmp
        else:
            self.auto_selected = np.array(self.auto_selected.tolist() + tmp.tolist())

        print(str(sum(self.auto_selected)) + '/' + str(len(self.session_blks)) +' trials have been selected!')
        session_blks = np.array(self.session_blks)
        self.trials_name = session_blks[self.auto_selected]
        print('Autoselection loop time: ' +str(datetime.datetime.now().replace(microsecond=0)-start_time))
        return

    def deltaf_visualization(self, start_frame, n_frames_showed, end_frame):
        start_time = datetime.datetime.now().replace(microsecond=0)
        indeces_select = np.where(self.auto_selected==1)
        indeces_select = indeces_select[0].tolist()
        session_name = self.header['path_session'].split('/')[-2]+'-'+self.header['path_session'].split('/')[-3].split('-')[1]
        # Array with indeces of considered frames: it starts from the last considerd zero_frames
        considered_frames = np.round(np.linspace(start_frame-1, end_frame-1, n_frames_showed))
        print(considered_frames)
        conditions = np.unique(self.conditions)
        for cd_i in conditions:
            indeces_cdi = np.where(self.conditions == cd_i)
            indeces_cdi = indeces_cdi[0].tolist()
            cdi_select = list(set(indeces_select).intersection(set(indeces_cdi)))
            fig = plt.figure(constrained_layout=True, figsize = (n_frames_showed-2, len(cdi_select)), dpi = 80)
            fig.suptitle(f'Session {session_name}')# Session name
            subfigs = fig.subfigures(nrows=len(cdi_select), ncols=1)
            for row, subfig in enumerate(subfigs):
                subfig.suptitle(f'Trial # {cdi_select[row]}')
                axs = subfig.subplots(nrows=1, ncols=n_frames_showed)
                for df_id, ax in zip(considered_frames, axs):
                    Y = self.df_fz[cdi_select[row], int(df_id), :, :]
                    ax.axis('off')
                    pc = ax.pcolormesh(Y, vmin=-0.007, vmax=0.001)
                subfig.colorbar(pc, shrink=1, ax=axs)#, location='bottom')
            
            tmp = self.set_md_folder()
            if not os.path.exists(tmp+'/activity_maps/'):
                os.makedirs(tmp+'/activity_maps/')
            plt.savefig(tmp+'/activity_maps/'+ session_name+'_0'+str(cd_i)+'.png')
        print('Plotting heatmaps time: ' +str(datetime.datetime.now().replace(microsecond=0)-start_time))
        return 
    
    def get_blank_signal(self):
        
        if (self.auto_selected is not None) and (self.conditions is not None):
            print('Already loaded blank blks are used.')
            indeces_select = np.where(self.auto_selected==1)
            indeces_select = indeces_select[0].tolist()        
            blank_cdi = np.where(np.array(self.conditions) == self.blank_id)
            blank_cdi = blank_cdi[0].tolist()
            blank_cdi = list(set(indeces_select).intersection(set(blank_cdi)))
            blank_sig = np.mean(self.roi_signals[blank_cdi, :], axis=0)
            blank_df = np.mean(self.df_fz[blank_cdi, :], axis=0)
            return blank_sig, blank_df

        elif (self.auto_selected is None) and (self.conditions is None):
            print('Loaded blks were not found: blank blks will be loaded.')
            # All the blank blks
            blks = [f for f in self.all_blks \
            if (int(f.split('vsd_C')[1][0:2])==self.blank_id)]
            # Blank signal extraction
            print('Blank trials loading starts:')
            blank_sig, blank_df_f0, blank_conditions= signal_extraction(self.header, blks, None, False)
            size_df_f0 = np.shape(blank_df_f0)
            
            blank_autoselect = overlap_strategy(blank_sig, n_chunks=1, loss = 'mse', up=85, bottom=15)

            self.df_fz = blank_df_f0
            self.roi_signals = blank_sig
            self.conditions = blank_conditions
            self.counter_blank = size_df_f0[0] # Countercheck this value
            self.auto_selected = blank_autoselect

            self.session_blks = blks

            blank_sig = np.mean(blank_sig, axis=0)
            blank_df = np.mean(blank_df_f0, axis=0)
            return blank_sig, blank_df
        else:
            print('Something weird: one between auto_selected and conditions is an empty set')

    def roi_plots(self):
        sig = self.roi_signals
        indeces_select = np.where(self.auto_selected==1)
        indeces_select = indeces_select[0].tolist()
        
        session_name = self.header['path_session'].split('/')[-2]+'-'+self.header['path_session'].split('/')[-3].split('-')[1]
        conditions = np.unique(self.conditions)
        blank_sign = self.time_course_blank

        for cd_i in conditions:
            indeces_cdi = np.where(np.array(self.conditions) == cd_i)
            indeces_cdi = indeces_cdi[0].tolist()
            cdi_select = list(set(indeces_select).intersection(set(indeces_cdi)))
            # Number of possible columns
            b = [4,5,6]
            a = [len(indeces_cdi)%i for i in b]
            columns = b[a.index(min(a))]

            fig = plt.figure(constrained_layout=True, figsize = (columns*4, int(np.ceil(len(indeces_cdi)/columns)+1)*2), dpi = 80)
            title = f'Condition #{cd_i}' 
            try:
                if self.cond_names is not None:
                    title = title + ': ' + self.cond_names[cd_i-1]
            except:
                None
            fig.suptitle(title)# Session name
            # Countercheck this height_ratios logic implementation
            rat = [1]*(int(np.ceil(len(indeces_cdi)/columns))+1)
            rat[-1] = 3
            subfigs = fig.subfigures(nrows=int(np.ceil(len(indeces_cdi)/columns))+1, ncols=1, height_ratios=rat)

            #if int(np.ceil(len(indeces_cdi)/columns)) >1:
            for row, subfig in enumerate(subfigs):
                #subfig.suptitle('Bottom title')
                axs = subfig.subplots(nrows=1, ncols=columns, sharex=True)#, sharey=True)
                for i, ax in enumerate(axs):
                    count = row*columns + i
                    color = 'r'
                    if count < len(indeces_cdi):
                        if indeces_cdi[count] in cdi_select:
                            color = 'b'
                        ax.plot(sig[indeces_cdi[count], :], color)
                        ax.errorbar([i for i in range(np.shape(sig[cdi_select, :])[1])], np.mean(sig[cdi_select, :], axis = 0), yerr=(np.std(sig[cdi_select, :], axis = 0)/np.sqrt(len(cdi_select))), fmt='--', color = 'k', elinewidth = 0.5)
                        ax.ticklabel_format(axis='both', style='sci', scilimits=(-3,3))
                        #ax.set_ylim(-0.002,0.002)
                    if row<len(subfigs)-2:
                        ax.get_xaxis().set_visible(False)
                    elif row<len(subfigs)-1:
                        ax.get_xaxis().set_visible(True)
                    elif row == len(subfigs)-1:
                        ax.axis('off')
                        ax_ = subfig.subplots(1, 1)
                        for id_trial in cdi_select:
                            ax_.plot(list(range(0,np.shape(sig)[1])), sig[id_trial, :], 'lightsteelblue')
                        ax_.plot(list(range(0,np.shape(sig)[1])), np.mean(sig[cdi_select, :], axis=0), 'k', label = 'Average Condition Signal', linewidth = 5)
                        ax_.plot(list(range(0,np.shape(sig)[1])), blank_sign, color='m', label = 'Average Blank Signal' ,linewidth = 5)
                        ax_.ticklabel_format(axis='both', style='sci', scilimits=(-3,3))
                    
            tmp = self.set_md_folder()
            if not os.path.exists(tmp+'/time_course/'):
                os.makedirs(tmp+'/time_course/')
            plt.savefig(tmp +'/time_course/'+ session_name+'_tc_0'+str(cd_i)+'.png')
            #plt.savefig((path_session+'/'session_name +'/'+ session_name+'_roi_0'+str(cd_i)+'.png')
        return

    def set_md_folder(self):
        session_path = self.header['path_session']
        folder_name = 'spcbin' + str(self.header['spatial_bin']) \
            + '_timebin' + str(self.header['temporal_bin']) \
            + '_zerofrms' + str(self.header['zero_frames']) \
            + '_dtrnd' + str(self.header['detrend'])\
            + '_tol' + str(self.header['tolerance'])\
            + '_mov' + str(self.header['mov_switch'])\
            + '_deblank' + str(self.header['deblank_switch'])\
            + '_strategy' + str(self.header['strategy'])
        folder_path = session_path + 'derivatives/'+folder_name              
        if not os.path.exists(folder_path):
        #if not os.path.exists( path_session+'/'+session_name):
            os.makedirs(folder_path)
            #os.mkdirs(path_session+'/'+session_name)
        return folder_path


def signal_extraction(header, blks, blank_s, blnk_switch):
    #motion_indeces, conditions = [], []
    conditions = []
    path_rawdata = header['path_session'] + 'rawdata/'
    for i, blk_name in enumerate(blks):
        start_time = datetime.datetime.now().replace(microsecond=0)
        # If first BLK file, than the header is stored
        if i == 0:
            BLK = blk_file.BlkFile(
                path_rawdata+blk_name,
                header['spatial_bin'],
                header['temporal_bin'],
                header['zero_frames'],
                header['detrend'], 
                motion_switch = header['mov_switch'],
                dblnk = blnk_switch,
                blank_signal= blank_s)

            header_blk = BLK.header
            delta_f = np.zeros((len(blks), header_blk['nframesperstim'], header_blk['frameheight']//header['spatial_bin'], header_blk['framewidth']//header['spatial_bin']))
            sig = np.zeros((len(blks), header_blk['nframesperstim']))
            roi_mask = blk_file.mask_roi(header_blk['framewidth']//header['spatial_bin'], header_blk['frameheight']//header['spatial_bin'])
        else:
            BLK = blk_file.BlkFile(
                path_rawdata+blk_name, 
                header['spatial_bin'], 
                header['temporal_bin'], 
                header['zero_frames'],
                header['detrend'], 
                header = header_blk, 
                motion_switch = header['mov_switch'], 
                roi_mask = roi_mask,
                dblnk = blnk_switch,
                blank_signal= blank_s)
        # if header['mov_switch']:
        #     motion_indeces.append(BLK.motion_ind)#at the end something like (nblks, 1) 
        conditions.append(BLK.condition)
        sig[i, :] = BLK.roi_sign
        #at the end something like (nblks, 70, 1)
        # The deltaF computing could be avoidable, since ROI signal at the end is plotted
        delta_f[i, :, :, :] = BLK.df_fz
        print('Trial n. '+str(i+1)+'/'+ str(len(blks))+' loaded in ' + str(datetime.datetime.now().replace(microsecond=0)-start_time)+'!')
    return sig, delta_f, conditions#, motion_indeces


def roi_strategy(matrix, tolerance, zero_frames):
    '''
    The method works.
    '''
    # framesOK=abs(signalROI-mat_meanSigROI)>toleranceLevel*mat_semSigROI;
    size = np.shape(matrix)
    tmp = np.zeros(size)
    for i, roi in enumerate(matrix):
        tmp[i, :] = signal.detrend(roi)
    # Blank subtraction on tmp -no demean if blank subt-
    # Mean ROI signal over trials -70, shape output-
    # The 0 shape is the number of trials
    selected_frames_mask = np.abs(tmp - np.mean(tmp, axis=0))>\
        tolerance*(np.std(tmp, axis=0)/np.sqrt(np.shape(tmp)[0]))
    #This could be tricky: not on all the frames.
    autoselect = np.sum(selected_frames_mask, axis=1)<((size[1]-zero_frames)/2)
    return autoselect

def overlap_strategy(matrix, n_chunks=1, loss = 'mae', up=75, bottom=25):
    size = np.shape(matrix)
    if  size[1] % n_chunks == 0:
        matrix_ = matrix.reshape(size[0], n_chunks, -1)
        tmp_m_ = np.zeros((n_chunks, size[0], size[0]))
        
        for m in range(n_chunks):
            tmp_m = np.zeros((size[0], size[0]))
            
            for n, i in enumerate(matrix_):
                tmp = []

                for j in matrix_:    
                    if loss == 'mae':
                        tmp.append(np.abs(np.subtract(i[m, :], j[m, :])).mean())
                    elif loss == 'mse':
                        tmp.append(np.square(np.subtract(i[m, :], j[m, :])).mean())

                tmp_m[n, :] = np.asarray(tmp)    
            tmp_m_[m, :, :] = tmp_m
            
        m = np.sum(tmp_m_, axis=1)
        t_whol = np.where((np.percentile(m, q=bottom, axis=1)<np.transpose(m)) & (np.percentile(m, q=up, axis=1)>np.transpose(m)))
        util = list(t_whol[0])
        set_a = list(set(util))
        dict_a = [(k, util.count(k)) for k in set_a] # List of tuples: first element the index of trial, second element number of chunks with the mae/mse value inside the range
        tmp = list(zip(*dict_a))
        lk = np.array(tmp[0])
        #consider only the trials with value of mae/mse inside the quartiles for at least half of the chunks
        autoselect = lk[np.where(np.array(tmp[1])>= np.ceil(n_chunks*0.5))[0]]
        # For combatibility with other methods, conversion in mask
        mask_array = np.zeros(size[0], dtype=int)
        mask_array[autoselect] = 1
        return mask_array
    else:
        # This check has to be done before running the script
        print('Use a proper number of chunks: exact division for the number of frames required')
        return

def statistical_strategy(matrix, up=75, bottom=25):
    size = np.shape(matrix)
    stds = np.std(matrix, axis = 1)
    autoselect = np.where((np.percentile(stds, q=bottom)<stds) & (np.percentile(stds, q=up)>stds))[0]
    # For combatibility with other methods, conversion in mask
    mask_array = np.zeros(size[0], dtype=int)
    mask_array[autoselect] = 1
    return mask_array


        
if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Launching autoselection pipeline')
    
    parser.add_argument('--path', 
                        dest='path_session',
                        type=str,
                        required=True,
                        help='The session path')
    
    parser.add_argument('--s_bin', 
                        dest='spatial_bin',
                        default= 3,
                        type=int,
                        help='The spatial bin value')

    parser.add_argument('--t_bin', 
                        dest='temporal_bin',
                        default= 1,
                        type=int,
                        required=False,
                        help='The time bin value')
    
    parser.add_argument('--zero',
                        dest='zero_frames',
                        type=int,
                        default = 20,
                        required=False,
                        help='The first frames considered zero')    

    parser.add_argument('--dtrn', 
                        dest='detrend',
                        action='store_true')
    parser.add_argument('--no-dtrn', 
                        dest='detrend', 
                        action='store_false')
    parser.set_defaults(detrend=False)

    parser.add_argument('--tol', 
                        dest='tolerance',
                        type=int,
                        default = 20,
                        required=False,
                        help='Tolerance value for autoselection') 

    parser.add_argument('--mov', 
                        dest='mov_switch',
                        action='store_true')
    parser.add_argument('--no-mov', 
                        dest='mov_switch', 
                        action='store_false')
    parser.set_defaults(mov_switch=False)

    parser.add_argument('--dblnk', 
                        dest='deblank_switch',
                        action='store_true')
    parser.add_argument('--no-dblnk', 
                        dest='deblank_switch', 
                        action='store_false')
    parser.set_defaults(deblank_switch=False)

    parser.add_argument('--cid', 
                    action='append', 
                    dest='conditions_id',
                    default=None,
                    type=int,
                    help='Conditions to analyze: None by default -all the conditions-')

    parser.add_argument('--chunks', 
                        dest='chunks',
                        type=int,
                        default = 5,
                        required=False,
                        help='Number of elements value for autoselection') 

    parser.add_argument('--strategy', 
                        dest='strategy',
                        type=str,
                        default = 'mae',
                        required=False,
                        help='Strategy for the autoselection: choose between mse/mae, statistical, roi -kevin equation-')     

    args = parser.parse_args()
    print(args)
    
    # Check on quality of inserted data
    assert args.spatial_bin > 0, "Insert a value greater than 0"    
    assert args.temporal_bin > 0, "Insert a value greater than 0"    
    assert args.zero_frames > 0, "Insert a value greater than 0"    
    assert args.strategy in ['mse', 'mae', 'roi', 'roi_signals', 'ROI', 'statistic', 'statistical', 'quartiles'], "Insert a valid name strategy: 'mse', 'mae', 'roi', 'roi_signals', 'ROI', 'statistic', 'statistical', 'quartiles'"    
    start_time = datetime.datetime.now().replace(microsecond=0)
    session = Session(**vars(args))
    session.autoselection()
    print('Time for blks autoselection: ' +str(datetime.datetime.now().replace(microsecond=0)-start_time))
    utils.inputs_save(session, 'session_prova')
    print(np.shape(session.df_fz))
    print(session.session_blks)
    print(session.conditions)
    session.roi_plots()
    session.deltaf_visualization(session.header['zero_frames'], 20, 60)
    #print(session.trials_name)

# 38, 18, 38