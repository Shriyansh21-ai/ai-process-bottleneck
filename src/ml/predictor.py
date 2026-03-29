def predict_future_risk(model, X):
    probabilities = model.predict_proba(X)[:, 1]
    return probabilities
