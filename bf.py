## Library code
## Bayes factor functions
import numpy as np
import scipy.special as ss
import pandas as pd

## Use the Stirling approximation for large binomials
def stirling_binom(N,n2):
    return N*np.log(N) - n2*np.log(n2) - (N-n2) * np.log(N-n2) + 0.5 *(np.log(N) - np.log(n2) - np.log(N-n2) -np.log(2 * np.pi))

## Calculate the evidence that all reads came from the same ecotype
def evidenceH0(N,n2,a,b):
    ## Handle large binomials
    if ss.binom(N,n2) == np.inf:
        s_binom = stirling_binom(N,n2)
        return s_binom+ss.betaln(n2+a,N-n2+b)-ss.betaln(a,b)
    else:
        return np.log(ss.binom(N,n2))+ss.betaln(n2+a,N-n2+b)-ss.betaln(a,b)

## Function to calculate the evidence that n2 reads came from more than one ecotype
def evidenceHmob (N,n2,ne2,a1,b1,a2,b2):
    return np.log(ss.binom(N-ne2,n2-ne2))+ss.betaln(n2-ne2+a1,N-n2+b1)+ ss.betaln(ne2+a2,b2)-(ss.betaln(a1,b1)+ss.betaln(a2,b2))

## Function to apply evidenceHmob to the data
def calculateevidenceHmob(N,n2,a1,b1,a2,b2):
    if n2 > 0:
        n2_values = np.arange(1,n2+1) ## Careful here! This needs to include n2, hence the +1
        ## Deal with the infs
        ev = evidenceHmob(N,n2,n2_values,a1,b1,a2,b2)
        ev_inf = np.isinf(ev)
        s_binom = stirling_binom(N-n2_values[ev_inf],n2-n2_values[ev_inf])
        ev[ev_inf] = s_binom+ss.betaln(n2-n2_values[ev_inf]+a1,N-n2+b1)+ ss.betaln(n2_values[ev_inf]+a2,b2)-(ss.betaln(a1,b1)+ss.betaln(a2,b2))
        ## Get the maximum evidence
        best_ev = ev.max()
        ## Get the number of reads for which we see this evidence
        index_max = np.argmax(ev)
        best_n2 = n2_values[index_max]
        return [best_ev, best_n2]
    else:
        return [ss.betaln(a1,N-1+b1)+ss.betaln(a2,1+b2)-(ss.betaln(a1,b1)+ss.betaln(a2,b2)),0]

## Apply all the functions and calculate the BF
def calculate_evidence(df, other_ecotype):
    depth = df['N']
    reads = df[other_ecotype]
    a1 = df["a1_x"]
    b1 = df["b1_x"]
    a2 = df["b1_y"]
    b2 = df["a1_y"]
    ## Calculate the evidence for the null hypothesis
    df['evidenceH0'] = [evidenceH0(x, y, alpha, beta) for x, y, alpha, beta in zip(depth, reads, a1, b1)] 
    ## Calculate the evidence for mobility
    #df[['evidenceHmob','n2']]= [calculateevidenceHmob(x, y, alpha1, beta1, alpha2, beta2) for x, y, alpha1, beta1, alpha2, beta2 in zip(depth, reads, a1, b1, a2, b2)]
## The above code breaks for non-mac platforms, therefore we shall create a new dataframe and append it to our original
    df_results = pd.DataFrame([calculateevidenceHmob(x, y, alpha1, beta1, alpha2, beta2) for x, y, alpha1, beta1, alpha2, beta2 in zip(depth, reads, a1, b1, a2, b2)], columns=("evidenceHmob","n2"))
    df = pd.concat([df,df_results],sort=False, axis=1)
    ## Calculate Bayes Factor
    ## Functions output natural logs - convert to log10
    df["Bayes factor"] = (df["evidenceHmob"] - df["evidenceH0"]) / np.log(10)
    return df

## Data processing functions
def clean_up_file(data):
    df = pd.read_csv(data, low_memory = False)
    cols = df.columns.drop(['SNP'])
    df[cols] = df[cols].apply(pd.to_numeric, errors='coerce') 
    df.dropna(inplace=True)
    df = df[df["N"]>0]
    return df

def get_homograft_data(hom_file_eco1, hom_file_eco2):
    ## Get alpha and beta 
    ## StemLeaves heterograft data uses Stem homografts
    ## Add in the alpha and beta values
    print("Processing homograft files...")
    ## Two homograft files: eco1 and eco2
    df_hom_eco1 = clean_up_file(hom_file_eco1)
    df_hom_eco2 = clean_up_file(hom_file_eco2)
    df_hom_eco1["a1"] = 1 + df_hom_eco1["eco2"]
    df_hom_eco1["b1"] = 1 + df_hom_eco1["N"] - df_hom_eco1["eco2"]
    df_hom_eco2["a1"] = 1 + df_hom_eco2["eco2"]
    df_hom_eco2["b1"] = 1 + df_hom_eco2["N"] - df_hom_eco2["eco2"]       
    return(df_hom_eco1, df_hom_eco2)
    
def run_bayes_analysis(het_file, df_hom_eco1, df_hom_eco2):
    ## So, now we have a1, b1 for each homograft, we can perform the BF analysis
    het_file = clean_up_file(het_file)
    het_file_merged = pd.merge(het_file, df_hom_eco1[["SNP","a1","b1"]], on = "SNP")
    het_file_merged = pd.merge(het_file_merged, df_hom_eco2[["SNP","a1","b1"]], on = "SNP")
    df = calculate_evidence(het_file_merged, "eco2")
    return df

