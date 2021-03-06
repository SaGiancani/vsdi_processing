import argparse, datetime, os, utils
import ana_logs as al
import middle_process as md
import numpy as np

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

    parser.add_argument('--raw', 
                        dest='raw_switch',
                        action='store_true')
    parser.add_argument('--no-raw', 
                        dest='raw_switch', 
                        action='store_false')
    parser.set_defaults(raw_switch=True)
    
    parser.add_argument('--cid', 
                    action='append', 
                    dest='conditions_id',
                    default=None,
                    type=int,
                    help='Conditions to analyze: None by default -all the conditions-')

    parser.add_argument('--chunks', 
                        dest='chunks',
                        type=int,
                        default = 1,
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
    start_time = datetime.datetime.now().replace(microsecond=0)
    # Something weird with the original BaseReport: a modified BaseReport is used with bigger header
    report, tris = al.get_basereport(args.path_session, name_report = 'BaseReport_V2.csv', header_dimension = 21)
    report = report.dropna(subset=['BLK Names'])
    #lat_timing_df = report[['Onset Time_ Behav Correct', 'Onset Time_ Behav Stim']].applymap(al.toogle_from_object)
    #lat_timing_df['BLK Names'] = report[['BLK Names']]

    print(f'The number of all the BLK files for the session is {len(md.get_all_blks(args.path_session))}')
    filt_blks = report.loc[report['behav Correct'] == 1]
    filt_blks = filt_blks.dropna(subset=['BLK Names'])['BLK Names'].tolist()
    #filt_blks = sorted(filt_blks, key=lambda t: datetime.datetime.strptime(t.split('_')[2] + t.split('_')[3], '%d%m%y%H%M%S'))

    print(f'The number of correct behavior BLK files for the same session is {len(filt_blks)}')
    filt_blks_ = report.loc[report['behav Correct'] == 0]
    filt_blks_ = filt_blks_.dropna(subset=['BLK Names'])['BLK Names'].tolist()
    #filt_blks_ = sorted(filt_blks_, key=lambda t: datetime.datetime.strptime(t.split('_')[2] + t.split('_')[3], '%d%m%y%H%M%S'))

    print(f'The number of uncorrect behavior BLK files for the same session is {len(filt_blks_)}')    #Loading session
    session = md.Session(**vars(args))
    #np.save('all_blks.npy', np.array(session.all_blks))
    session.get_session()
    #Sorting the blks for date
    print(len(session.all_blks))
    print(len(session.session_blks))
    session.all_blks[:] = [x for x in session.all_blks if x != tris[2]]
    session.session_blks[:] = [x for x in session.session_blks if x != tris[2]]
    print(len(session.all_blks))
    print(len(session.session_blks))
    print(np.shape(session.raw_data))
    try:
        session.raw_data = np.delete(session.raw_data, session.session_blks.index(tris[2]),0)
    except:
        session.raw_data = session.raw_data 
    #raw = np.concatenate((session.raw_data[:tris[0]-1, :, :, :], session.raw_data[tris[0]:, :, :, :]))
    print(np.shape(session.raw_data))
    #all_blks = sorted(session.all_blks, key=lambda t: datetime.datetime.strptime(t.split('_')[2] + t.split('_')[3], '%d%m%y%H%M%S'))
    #Creating a storing folder
    folder_path = os.path.join(session.header['path_session'], 'derivatives/raw_data_matlab')  
    pos_blks = list(set(session.session_blks).intersection(set(filt_blks)))
    pos_blks = sorted(pos_blks, key=lambda t: datetime.datetime.strptime(t.split('_')[2] + t.split('_')[3], '%d%m%y%H%M%S'))
    pos_ids = [session.session_blks.index(i) for i in pos_blks]
    pos_ids_lat = [session.all_blks.index(i) for i in pos_blks]

    neg_blks = list(set(session.session_blks).intersection(set(filt_blks_)))
    neg_blks = sorted(neg_blks, key=lambda t: datetime.datetime.strptime(t.split('_')[2] + t.split('_')[3], '%d%m%y%H%M%S'))
    neg_ids = [session.session_blks.index(i) for i in neg_blks]    #pick_blks = np.array(session.all_blks)[[session.all_blks.index(i) for i in pos_blks]].tolist()
    if not os.path.exists(folder_path):
    #if not os.path.exists( path_session+'/'+session_name):
        os.makedirs(folder_path)
        #os.mkdirs(path_session+'/'+session_name)
    print(f'The number of all picked BLK indeces {len(session.session_blks)}')
    print(f'The number of selected indeces {len(pos_ids)}')
    latency = np.array((report[['Onset Time_ Behav Correct']].applymap(al.toogle_from_object)['Onset Time_ Behav Correct'] - report[['Onset Time_ Behav Stim']].applymap(al.toogle_from_object)['Onset Time_ Behav Stim'] -500))
    tk = np.array(session.session_blks)
    tk_ = np.array(session.all_blks)
    conditions = np.array([int(i.split('vsd_C')[1][0:2]) for i in session.session_blks])
    conditions_lat = np.array([int(i.split('vsd_C')[1][0:2]) for i in session.all_blks])
    #Storing a raw_data matrix per each condition
    for i in np.unique(session.conditions):
        print(f'Condition: {i}')
        ids = np.where(conditions == i)[0].tolist()
        ids_lat = np.where(conditions_lat == i)[0].tolist()
        common_ids = list(set(ids).intersection(set(pos_ids)))
        common_ids_lat = list(set(ids_lat).intersection(set(pos_ids_lat)))
        common_ids_ = list(set(ids).intersection(set(neg_ids)))
        # Only for positive behav computing latency
        #t = lat_timing_df.loc[lat_timing_df['BLK Names'].isin(all_blks[common_ids]), ['Onset Time_ Behav Correct', 'Onset Time_ Behav Stim']]
        print('Considered ids: \n')
        print(common_ids)
        print(tk[common_ids])
        print('\n')
        print(tk_[common_ids_lat])
        tmp_matrix = session.raw_data[common_ids]
        tmp_matrix_ = session.raw_data[common_ids_]
        lat_temp = latency[common_ids_lat]
        #np.save(os.path.join(folder_path, f'raw_data_cd{i}.npy'), tmp_matrix)
        try: 
            utils.socket_numpy2matlab(folder_path, tmp_matrix_, substring=f'neg_cd{i}')
            utils.socket_numpy2matlab(folder_path, tmp_matrix, substring=f'pos_cd{i}')

        except:
            shap = np.shape(tmp_matrix)
            shap_ = np.shape(tmp_matrix_)
            inds = np.int64(np.round(np.linspace(0, shap[0], 7)))
            inds_ = np.int64(np.round(np.linspace(0, shap_[0], 7)))
            utils.socket_numpy2matlab(folder_path, tmp_matrix[:inds[1], :, : ], substring=f'pos_cd{i}_1')
            utils.socket_numpy2matlab(folder_path, tmp_matrix[inds[1]:inds[2], :, : ], substring=f'pos_cd{i}_2')
            utils.socket_numpy2matlab(folder_path, tmp_matrix[inds[2]:inds[3], :, : ], substring=f'pos_cd{i}_3')
            utils.socket_numpy2matlab(folder_path, tmp_matrix[inds[3]:inds[4], :, : ], substring=f'pos_cd{i}_4')
            utils.socket_numpy2matlab(folder_path, tmp_matrix[inds[4]:inds[5], :, : ], substring=f'pos_cd{i}_5')
            utils.socket_numpy2matlab(folder_path, tmp_matrix[inds[5]:, :, : ], substring=f'pos_cd{i}_6')
            utils.socket_numpy2matlab(folder_path, tmp_matrix_[:inds_[1], :, : ], substring=f'neg_cd{i}_1')
            utils.socket_numpy2matlab(folder_path, tmp_matrix_[inds_[1]:inds_[2], :, : ], substring=f'neg_cd{i}_2')
            utils.socket_numpy2matlab(folder_path, tmp_matrix_[inds_[2]:inds_[3], :, : ], substring=f'neg_cd{i}_3')
            utils.socket_numpy2matlab(folder_path, tmp_matrix_[inds_[3]:inds_[4], :, : ], substring=f'neg_cd{i}_4')
            utils.socket_numpy2matlab(folder_path, tmp_matrix_[inds_[4]:inds_[5], :, : ], substring=f'neg_cd{i}_5')
            utils.socket_numpy2matlab(folder_path, tmp_matrix_[inds_[5]:, :, : ], substring=f'neg_cd{i}_6')

        utils.socket_numpy2matlab(folder_path, lat_temp, substring=f'latency_pos_cd{i}')

    print('Time for raw signal storing: ' +str(datetime.datetime.now().replace(microsecond=0)-start_time))
