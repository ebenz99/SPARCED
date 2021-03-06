import numpy as np
import scipy.stats
from random import *
import pandas as pd

def SGEmodule(flagD,ts,genedata,spdata,Vn,Vc,kTCmaxs,kTCleak,kTCd,AllGenesVec,GenePositionMatrix,TAs0,TRs0,kGin_1,kGac_1,tcnas, \
        tck50as,tcnrs,tck50rs):
    # Inputs:
    # flagD = deterministic (1) or stochastic (0) simulation
    # ts = time step
    # genedata = 1D array of latest gene-expression module concentrations
    # spdata = 1D array of latest species concentrations
    # Vn = nuclear volume
    # Vc = cytoplasmic volume
    # kTCmaxs = Maximal transcription rates
    # kTCleak = Transcription leakage rates
    # kTCd = mRNA degradation rates
    # AllGenesVec = Number of active genes
    # GenePositionMatrix = matrix showing which genes are active
    # TAs0 = Genes x Transcriptional activators
    # TRs0 = Genes x Transcriptional repressors
    # kGin_1 = rate of gene inactivation
    # kGac_1 = rate of gene activation
    # tcnas = Hill coefficients for transcriptional activators
    # tck50as = K50 values for transcriptional activators
    # tcnrs = Hill coefficients for transcriptional repressors
    # tck50rs = K50 values for transcriptional repressors
   
    # Outputs:
    # genedataNew = new active genes and inactive genes
    # xmN = new mRNA mpc (or xmN_nM = new mRNA in nM)
    # AllGenesVecNew = New array of all genes
    
    mpc2nmcf_Vn = 1.0E9/(Vn*6.023E+23)
    mpc2nmcf_Vc = 1.0E9/(Vc*6.023E+23)
    numberofgenes = int(len(kTCleak))

    # gm species
    ix = 0
    xgac = genedata[ix:ix+numberofgenes]
    ix = ix+numberofgenes
    xgin = genedata[ix:ix+numberofgenes]
    xm = np.divide(spdata[773:],mpc2nmcf_Vc)
    
    # Get the latest concentrations of TARs
    pcFos_cJun = spdata[684] #1
    cMyc = spdata[685] #2
    p53ac = spdata[2] #3
    FOXOnuc = spdata[766] #4
    ppERKnuc = spdata[675] #5
    pRSKnuc = spdata[678] #6
    bCATENINnuc = spdata[686] #7

    cc = np.multiply(TAs0,np.array([pcFos_cJun, cMyc, p53ac, FOXOnuc, ppERKnuc, pRSKnuc, bCATENINnuc]))
    dd = cc*(1/mpc2nmcf_Vn) # convert to mpc from nM
    TAs = dd
    TAs.flatten()
    ee = np.multiply(TRs0,np.array([pcFos_cJun, 1, 1, 1, 1, 1, 1]))
    ff = ee*(1/mpc2nmcf_Vn)   
    TRs = ff
    TRs.flatten()
    
    # make hills
    aa = np.divide(TAs,tck50as)
    TFa = np.power(aa,tcnas)
    TFa[np.isnan(TFa)] = 0.0
    bb = np.divide(TRs,tck50rs)
    TFr = np.power(bb,tcnrs)
    TFr[np.isnan(TFr)] = 0.0
    hills = np.sum(TFa,axis=1)/(1 + np.sum(TFa,axis=1) + np.sum(TFr,axis=1))
    # With AP1*cMYC exception:
    hills[9:12] = np.multiply((TFa[9:12,0]/(1+TFa[9:12,0])),(TFa[9:12,1]/(1+TFa[9:12,1])))
    
    # vTC
    hills = np.matrix(hills)
    # hills = np.matrix.transpose(hills)
    induced = np.multiply(np.multiply(xgac,kTCmaxs),hills)
    induced = induced.flatten()
    leak = np.multiply(xgac,kTCleak)
    vTC = np.add(leak,induced)
    vTC.flatten()
    vTC = np.squeeze(np.asarray(vTC))

    # vTCd
    vTCd= np.transpose(np.multiply(kTCd,xm));
    vTCd = np.squeeze(np.asarray(vTCd))
    
    # If deterministic simulation:
    if flagD: 
        Nb = vTC*ts;
        Nd = vTCd*ts;
        xgacN = genedata[0:numberofgenes]
        xginN = genedata[numberofgenes:numberofgenes*2]
        AllGenesVecN = []
    else:
        # Poisson Stuff
        poff = scipy.stats.poisson.pmf(0,kGin_1*ts)
        pon = scipy.stats.poisson.pmf(0,kGac_1*ts)

        # Generating random numbers and deciding which genes should turn off and on
        RandomNumbers = np.random.uniform(0,1,len(AllGenesVec))
        geneson = AllGenesVec.astype(bool).astype(int)
        genesoff = np.logical_not(geneson).astype(int)
        ac2in = np.logical_and(np.transpose(geneson.flatten()),RandomNumbers>=poff)
        in2ac = np.logical_and(np.transpose(genesoff.flatten()),RandomNumbers>=pon)

        # Generating new AllGenesVec and allocating active and inactive genes
        AllGenesVecN = AllGenesVec
        AllGenesVecN[ac2in] = 0.0
        AllGenesVecN[in2ac] = 1.0

        xgacN = np.dot(GenePositionMatrix,AllGenesVecN)
        xgacN = xgacN.ravel()
        xginN = np.subtract(np.add(xgac,xgin),xgacN.flatten())
        xginN = xginN.ravel()

        # mRNA
        Nb = np.random.poisson(np.float64(vTC*ts))
        Nb = Nb.ravel()
        Nd = np.random.poisson(np.float64(vTCd*ts))
        Nd = Nd.ravel()
        # These genes and mRNAs we don't allow to fluctuate
        indsD = np.array([5,6,7,8,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29])
        Nb[indsD] = vTC[indsD]*ts
        Nd[indsD] = vTCd[indsD]*ts
        xgacN[indsD] = genedata[indsD]
        xginN[indsD] = genedata[indsD+numberofgenes]

    # Finish mRNA
    xmN = xm+Nb-Nd
    xmN[xmN<0.0] = 0.0
    xmN_nM = np.dot(xmN,mpc2nmcf_Vc)

    genedataNew = []
    genedataNew = np.concatenate((xgacN, xginN), axis=None)

    return genedataNew, xmN_nM, AllGenesVecN