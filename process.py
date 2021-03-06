import numpy as np
from scipy.ndimage.filters import uniform_filter1d
from scipy import optimize

def deltaf_up_fzero(vsdi_sign, n_frames_zero, deblank = False, blank_sign = None, outlier_tresh = 1000):
    '''F/F0 computation with -or without- demean of n_frames_zero and killing of outlier 
		----------
		vsdi_sign : np.array, with shape nframes, width, height
        n_frames_zero: int, the number of frames taken as zero, aka prestimulus
        demean: bool, switch for demeaning the signal: F-mean(F[0:n_frames_zero])/mean(F[0:n_frames_zero]) if True
                F/mean(F[0:n_frames_zero]) if False 
        outlier_tresh: int, 1000 by default, over this -absolute- threshold the pixel-value is put to 0  
		Returns
		-------
		df_fz : np.array, with shape nframes, width, height
    '''
    mean_frames_zero = np.mean(vsdi_sign[:n_frames_zero, :, :], axis = 0)
    # The case for precalculating the blank signal or not deblank at all
    if (deblank and (blank_sign is None)):
        df_fz= (vsdi_sign/mean_frames_zero) 
    # The case for calculating the signal deblanked
    elif deblank and (blank_sign is not None):
        df_fz = ((vsdi_sign/mean_frames_zero)/(blank_sign)) - 1
    # The case without deblank
    elif (not deblank):
        df_fz = (vsdi_sign/mean_frames_zero) -1
    # Conceptually problematic subtraction, if used in combination with first frame subtraction.         
    #df_fz = df_fz - df_fz[0, :, :] 
    df_fz[np.where(np.abs(df_fz)>outlier_tresh)] = 0
    return df_fz


def time_course_signal(df_fz, roi_mask):#, hand_made=False):
    """
    Computes the signal in ROI. 
    It recalls initially the mask_roi method, than it computes demeaning of the signal.
    Parameter
    -----------
        self Object
        bnnd_img: numpy.array (70, width of binning, height of binning), the binned signal
    Returns
    -----------
        self.roi_sign: numpy.array (70,1) the signal inside the ROI, represented as a 1D array
    """
    roi_sign = list()
    for i in df_fz:
    #	print(np.shape(i))
        roi_sign.append(np.ma.masked_array(i, mask = roi_mask).mean())
    return np.array(roi_sign)


def traject_designing():
    return

def gauss_1d(x, a, mean, stddev):
    return a*np.exp((-(x-mean)**2)/(2*stddev**2))
    #return a * np.exp(-((x - mean) / 4 / stddev)**2)
    #return a * np.exp(-(x - mean)**2 / (2 * stddev**2))

def gaussian_fitting(td_mat, ax_to_fit, perc_wind = 3):
    if len(np.shape(td_mat)) > 2:
        print('The matrix to fit has to be two or mono dimensional')
        return
    
    elif len(np.shape(td_mat)) == 2:
        dim = np.shape(td_mat)[ax_to_fit]
        if ax_to_fit == 0:
            proj = np.mean(td_mat, axis = 1)
        else:        
            proj = np.mean(td_mat, axis = 0)
    
    elif len(np.shape(td_mat)) == 1:
        dim = len(td_mat)
        proj = td_mat

    ax = np.linspace(0, 1, dim)
    #print(np.min(proj))
    #proj = proj-proj[0]
    proj = proj-np.min(proj)
    proj = uniform_filter1d(proj, size=(len(proj)//100)*perc_wind) # Moving Average Filter: check the result
    popt,pcov = optimize.curve_fit(gauss_1d, ax, proj)#, bounds=bounds) or ,maxfev = 5000)
    return ax, proj, popt, pcov 

def log_norm(y, mu, sigma):
    return 1/(np.sqrt(2.0*np.pi)*sigma*y)*np.exp(-(np.log(y)-mu)**2/(2.0*sigma*sigma))

def lognorm_fitting(array_to_fit, b= 50):
    # Normalization
    tmp = array_to_fit
    # Histogram computation
    h = np.histogram(tmp, bins=b)
    n = h[1]
    step = (n[1]-n[0])
    nrm = np.sum(h[0]*step)    
    fr = h[0]/nrm
    xx = n - 0.5*step
    ar = np.zeros((fr.shape[0]+1))
    ar[1:] = fr
    # lognormal Fitting
    params, _ = optimize.curve_fit(log_norm, xx, ar)
    mu = params[0]
    sigma = params[1]
    # Median + StdDev
    # Median + StdDev
    return ar, mu, sigma, xx

def lognorm_thresholding(array_to_fit, switch = 'median'):
    array_to_fit = array_to_fit/np.max(array_to_fit)
    tmp, mu, sigma, xx = lognorm_fitting(array_to_fit, b= 50)

    if switch == 'median':
        thresh = np.exp(mu)
    elif switch == 'mean':
        thresh = np.exp(mu + sigma*sigma/2.0)
    thresh_std = (thresh + 2*np.sqrt((np.exp(sigma*sigma)-1)*np.exp(mu+mu+sigma*sigma)))
    select_trials_id = np.where(((array_to_fit)<(thresh_std)))[0].tolist()
    return select_trials_id, (tmp, mu, sigma, xx), array_to_fit.tolist()
    
def zeta_score(sig_cond, sig_blank, zero_frames = 20):
    eps = 0.00000001
    # Blank mean and stder computation
    if sig_blank is None:
        mean_signblnk_overcond = np.mean(sig_cond[:zero_frames, :, :], axis = 0)
        stder_signblnk_overcond = np.std(sig_cond[:zero_frames, :, :], axis = 0)/np.sqrt(np.shape(sig_cond)[0])# Normalization of standard over all the frames, not only the zero_frames        
    else:
        mean_signblnk_overcond = np.mean(sig_blank[:, :, :], axis = 0)
        stder_signblnk_overcond = np.std(sig_blank[:, :, :], axis = 0)/np.sqrt(np.shape(sig_blank)[0])
    # Condition mean and stder computation
    #mean_sign_overcond = np.mean(sig_cond[bottomFOI:upperFOI, :, :], axis = 0)
    #stder_sign_overcond = np.std(sig_cond[bottomFOI:upperFOI, :, :], axis = 0)/np.sqrt(np.shape(sig_cond)[0])
    zscore = (sig_cond-mean_signblnk_overcond)/(stder_signblnk_overcond + eps)
    return zscore