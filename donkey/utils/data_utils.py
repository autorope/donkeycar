import random 

def split_data(X, Y, test_frac=.8):
    count = len(X)
    assert len(X) == len(Y)
    
    cutoff = int((count * test_frac) // 1)
    
    X_train = X[:cutoff]
    Y_train = Y[:cutoff]
    
    X_test = X[cutoff:]
    Y_test = Y[cutoff:]
    
    return X_train, Y_train, X_test, Y_test


def split_list(L, sequential=False, test_frac=.8):

    count = len(L)
    cutoff = int((count * test_frac) // 1)
    
    if sequential == False:
        random.shuffle(L)

    L_train = L[:cutoff]
    L_test =  L[cutoff:]

    return L_train, L_test